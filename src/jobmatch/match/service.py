"""The whole CV-matching flow, used by both the command line and the API."""
from jobmatch.db import connect
from jobmatch.match.fit import score_job
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


def match_profile(
    profile: CandidateProfile, city: str | None = None, language: str | None = None, top: int = 5
) -> dict:
    """Search for jobs that fit the profile, then let the LLM score the best `top` of them."""
    query = build_search_query(profile)
    candidates = unique_ads(search(query, "hybrid", city, language, k=20))[:top]
    with connect() as conn:
        texts = dict(conn.execute(
            "SELECT id, text FROM ads WHERE id = ANY(%s)", ([ad["id"] for ad in candidates],)
        ).fetchall())
    matches, quotes_kept, quotes_dropped = [], 0, 0
    for ad in candidates:
        fit, dropped = score_job(profile, ad["title"], texts[ad["id"]])
        quotes_kept += len(fit.reasons)
        quotes_dropped += dropped
        matches.append({**ad, **fit.model_dump()})
    matches.sort(key=lambda m: m["score"], reverse=True)
    total = quotes_kept + quotes_dropped
    return {
        "query": query,
        "profile": profile.model_dump(),
        "matches": matches,
        "quotes_verified": f"{quotes_kept}/{total}",
    }


def match_cv_text(cv_text: str, city: str | None = None, language: str | None = None, top: int = 5) -> dict:
    return match_profile(extract_profile(cv_text), city, language, top)