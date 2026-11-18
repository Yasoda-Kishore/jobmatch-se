"""Keyword search with Postgres full-text search: finds exact words like 'Kubernetes'."""
import re

import psycopg

from jobmatch.search.common import FILTERS, best_per_ad

KEYWORD_SQL = f"""
SELECT a.id, ts_rank_cd(c.tsv, to_tsquery('simple', %(tsq)s)) AS score
FROM chunks c
JOIN ads a ON a.id = c.ad_id
WHERE c.tsv @@ to_tsquery('simple', %(tsq)s) AND {FILTERS}
ORDER BY score DESC
LIMIT %(limit)s;
"""


def to_or_query(question: str) -> str | None:
    """'Python data engineer' -> 'python | data | engineer' (match any of the words).

    Only letters and digits are kept, so the user can't break the query syntax.
    """
    words = re.findall(r"[0-9a-zåäöéü]+", question.lower())
    words = [w for w in words if len(w) > 1]
    return " | ".join(words) if words else None


def keyword_search(
    conn: psycopg.Connection, question: str, city: str | None = None,
    language: str | None = None, k: int = 50,
) -> list[tuple[str, float]]:
    """Return up to k (ad_id, keyword score) pairs, best first."""
    tsq = to_or_query(question)
    if tsq is None:
        return []
    params = {"tsq": tsq, "city": city, "language": language, "limit": k * 5}
    rows = conn.execute(KEYWORD_SQL, params).fetchall()
    return best_per_ad(rows, k)