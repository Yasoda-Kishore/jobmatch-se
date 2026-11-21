"""The whole CV-matching flow, used by both the command line and the API."""
import contextvars
from concurrent.futures import ThreadPoolExecutor

from jobmatch.db import connect
from jobmatch.llm import LLM_PARALLEL, LLMError
from jobmatch.match import cache
from jobmatch.match.fit import AdRequirements, read_requirements, score_requirements
from jobmatch.match.profile import CandidateProfile, build_search_query, extract_profile
from jobmatch.search.engine import search


def unique_ads(results: list[dict]) -> list[dict]:
    """Employers often post the same ad twice. Keep the first ad per (title, employer)."""
    seen: set[tuple[str, str]] = set()
    unique = []
    for ad in results:
        key = (ad["title"].strip().lower(), (ad["employer"] or "").strip().lower())
        if key not in seen:
            seen.add(key)
            unique.append(ad)
    return unique


def read_many(ads: list[dict], texts: dict[str, str]) -> dict[str, AdRequirements]:
    """Ask the LLM to read several ads, LLM_PARALLEL at a time. Ads the LLM fails on are skipped."""

    def read_one(ad: dict) -> tuple[str, AdRequirements | None]:
        try:
            return ad["id"], read_requirements(ad["title"], texts[ad["id"]])
        except LLMError:
            return ad["id"], None

    with ThreadPoolExecutor(max_workers=LLM_PARALLEL) as pool:
        # copy_context() lets each thread add its LLM usage to the current request's stats
        futures = [pool.submit(contextvars.copy_context().run, read_one, ad) for ad in ads]
        results = [f.result() for f in futures]
    return {ad_id: req for ad_id, req in results if req is not None}


def match_profile(
    profile: CandidateProfile, city: str | None = None, language: str | None = None, top: int = 5
) -> dict:
    """Search for jobs that fit the profile, then score the best `top` of them."""
    query = build_search_query(profile)
    candidates = unique_ads(search(query, "hybrid", city, language, k=20))[:top]
    with connect() as conn:
        texts = dict(conn.execute(
            "SELECT id, text FROM ads WHERE id = ANY(%s)", ([ad["id"] for ad in candidates],)
        ).fetchall())
        requirements = cache.load_cached(conn, texts)
        new = read_many([ad for ad in candidates if ad["id"] not in requirements], texts)
        for ad_id, req in new.items():
            cache.save(conn, ad_id, texts[ad_id], req)
        conn.commit()
    requirements.update(new)

    matches, quotes_kept, quotes_dropped = [], 0, 0
    for ad in candidates:
        if ad["id"] not in requirements:
            continue  # the LLM could not read this ad
        fit, dropped = score_requirements(profile, requirements[ad["id"]], texts[ad["id"]])
        quotes_kept += len(fit["quotes"])
        quotes_dropped += dropped
        matches.append({**ad, **fit})
    matches.sort(key=lambda m: m["score"], reverse=True)
    return {
        "query": query,
        "profile": profile.model_dump(),
        "matches": matches,
        "quotes_verified": f"{quotes_kept}/{quotes_kept + quotes_dropped}",
        "ads_from_cache": len(candidates) - len(new),
    }


def match_cv_text(cv_text: str, city: str | None = None, language: str | None = None, top: int = 5) -> dict:
    return match_profile(extract_profile(cv_text), city, language, top)
