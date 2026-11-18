"""Vector search: ads whose chunks are closest in meaning to the question."""
import psycopg

from jobmatch.embeddings import embed_query
from jobmatch.search.common import FILTERS, best_per_ad

VECTOR_SQL = f"""
SELECT a.id, 1 - (c.embedding <=> %(q)s) AS score
FROM chunks c
JOIN ads a ON a.id = c.ad_id
WHERE {FILTERS}
ORDER BY c.embedding <=> %(q)s
LIMIT %(limit)s;
"""


def vector_search(
    conn: psycopg.Connection, question: str, city: str | None = None,
    language: str | None = None, k: int = 50,
) -> list[tuple[str, float]]:
    """Return up to k (ad_id, similarity) pairs, best first."""
    # The HNSW index normally looks at about 40 candidates. Look at more, and keep
    # searching when filters remove results (a pgvector 0.8 feature).
    conn.execute("SET hnsw.ef_search = 200")
    conn.execute("SET hnsw.iterative_scan = strict_order")
    params = {"q": embed_query(question), "city": city, "language": language, "limit": k * 5}
    rows = conn.execute(VECTOR_SQL, params).fetchall()
    return best_per_ad(rows, k)