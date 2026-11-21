"""The web API. Start it with: uvicorn jobmatch.api.main:app --reload"""
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from jobmatch.match.profile import read_pdf_text
from jobmatch.match.service import match_cv_text
from jobmatch.search.engine import search

app = FastAPI(title="JobMatch SE", description="Search Swedish IT job ads by meaning and keywords")


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
    cv: UploadFile,
    city: str | None = None,
    language: Literal["sv", "en"] | None = None,
    top: int = Query(5, ge=1, le=10),
) -> dict:
    """Upload a CV (PDF) and get the best matching jobs, scored with reasons."""
    if cv.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Please upload a PDF file")
    text = read_pdf_text(cv.file.read())
    if not text:
        raise HTTPException(status_code=400, detail="No readable text in this PDF")
    return match_cv_text(text, city=city, language=language, top=top)


# The website (web/index.html and friends). Mounted last, so the API routes above win.
WEB_DIR = Path(__file__).resolve().parents[3] / "web"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
