"""The web API. Start it with: uvicorn jobmatch.api.main:app --reload"""
import logging
import os
import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from jobmatch.api.limits import MATCHES_PER_HOUR, allow
from jobmatch.llm import LLM_MODEL, LLM_PROVIDER
from jobmatch.match.profile import read_pdf_text
from jobmatch.match.service import match_cv_text
from jobmatch.monitoring import finish_request, start_request, summary
from jobmatch.search.engine import search

app = FastAPI(title="JobMatch SE", description="Search Swedish IT job ads by meaning and keywords")
logging.basicConfig(level=logging.INFO, format="%(message)s")

API_PATHS = ("/search", "/match", "/health", "/metrics")
# On the public website there is no local LLM, so CV matching can be switched off there
MATCH_ENABLED = os.getenv("MATCH_ENABLED", "true").lower() == "true"


@app.middleware("http")
async def measure_requests(request: Request, call_next):
    """Time every API request, add the time as a header, and log it."""
    stats = start_request()
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Response-Time-ms"] = f"{duration_ms:.0f}"
    if request.url.path in API_PATHS:
        finish_request(stats, request.method, request.url.path, response.status_code, duration_ms)
    return response


class SearchResult(BaseModel):
    id: str
    title: str
    employer: str | None
    city: str | None
    language: str
    url: str | None
    score: float


class SearchResponse(BaseModel):
    query: str
    mode: str
    results: list[SearchResult]


@app.get("/health")
def health() -> dict:
    """A simple check that the server is running."""
    return {"status": "ok"}


@app.get("/config")
def config() -> dict:
    """Tells the website whether CVs are read by a local or a cloud LLM, so it can say so honestly."""
    return {
        "llm_location": "local" if LLM_PROVIDER == "ollama" else "cloud",
        "llm_model": LLM_MODEL,
        "match_enabled": MATCH_ENABLED,
    }


@app.get("/metrics")
def metrics() -> dict:
    """Speed and LLM usage per endpoint, over the last 500 requests."""
    return summary()


@app.get("/search", response_model=SearchResponse)
def search_ads(
    q: str = Query(min_length=2, description="What you are looking for"),
    mode: Literal["vector", "keyword", "hybrid", "rerank"] = "hybrid",
    city: str | None = None,
    language: Literal["sv", "en"] | None = None,
    k: int = Query(10, ge=1, le=50),
) -> SearchResponse:
    """Find the best matching job ads."""
    results = search(q, mode=mode, city=city, language=language, k=k)
    return SearchResponse(query=q, mode=mode, results=results)


@app.post("/match")
def match_cv(
    request: Request,
    cv: UploadFile,
    city: str | None = None,
    language: Literal["sv", "en"] | None = None,
    top: int = Query(5, ge=1, le=10),
) -> dict:
    """Upload a CV (PDF) and get the best matching jobs, scored with reasons."""
    if not MATCH_ENABLED:
        raise HTTPException(status_code=503, detail="CV matching is switched off on this server.")
    visitor = request.client.host if request.client else "unknown"
    if not allow(visitor):
        raise HTTPException(
            status_code=429,
            detail=f"You can match {MATCHES_PER_HOUR} CVs per hour. Please try again a little later.",
        )
    if cv.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Please upload a PDF file")
    text = read_pdf_text(cv.file.read())
    if not text:
        raise HTTPException(status_code=400, detail="No readable text in this PDF")
    try:
        return match_cv_text(text, city=city, language=language, top=top)
    except Exception as error:  # wrong model name, rate limit, provider down...
        raise HTTPException(status_code=502, detail=f"The AI model failed: {error}") from error


# The website (web/index.html and friends). Mounted last, so the API routes above win.
WEB_DIR = Path(__file__).resolve().parents[3] / "web"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
