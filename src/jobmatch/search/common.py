"""Pieces shared by all search methods."""

# Optional filters. "%(city)s::text IS NULL" means: if no city was given, skip this filter.
FILTERS = """
    (%(city)s::text IS NULL OR lower(a.city) = lower(%(city)s))
    AND (%(language)s::text IS NULL OR a.language = %(language)s)
"""


def best_per_ad(rows: list[tuple[str, float]], k: int) -> list[tuple[str, float]]:
    """Rows are (ad_id, score), best first. Keep only the first (best) row per ad."""
    seen: set[str] = set()
    results = []
    for ad_id, score in rows:
        if ad_id not in seen:
            seen.add(ad_id)
            results.append((ad_id, float(score)))
            if len(results) == k:
                break
    return results