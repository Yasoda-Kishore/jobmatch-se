"""The web API. Start it with: uvicorn jobmatch.api.main:app --reload"""
from typing import Literal

from fastapi import FastAPI, Query
from pydantic import BaseModel

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
    mode: Literal["vector", "keyword", "hybrid"] = "hybrid",
    city: str | None = None,
    language: Literal["sv", "en"] | None = None,
    k: int = Query(10, ge=1, le=50),
) -> SearchResponse:
    """Find the best matching job ads."""
    results = search(q, mode=mode, city=city, language=language, k=k)
    return SearchResponse(query=q, mode=mode, results=results)