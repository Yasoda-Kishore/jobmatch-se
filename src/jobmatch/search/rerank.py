"""Reranking: a cross-encoder reads the question and each candidate ad together, and scores them."""
from functools import lru_cache

import psycopg
from sentence_transformers import CrossEncoder

from jobmatch.embeddings import embed_query

RERANK_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"  # multilingual, small enough for a laptop

BEST_CHUNKS = """
SELECT DISTINCT ON (ad_id) ad_id, text
FROM chunks
WHERE ad_id = ANY(%(ids)s)
ORDER BY ad_id, embedding <=> %(q)s;
"""


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    """Load the reranker once (the first call downloads it)."""
    return CrossEncoder(RERANK_MODEL, max_length=512)


def rerank(
    conn: psycopg.Connection, question: str, candidates: list[tuple[str, float]]
) -> list[tuple[str, float]]:
    """Re-order candidate ads. Each ad is represented by its chunk closest to the question."""
    if not candidates:
        return []
    ids = [ad_id for ad_id, _ in candidates]
    rows = conn.execute(BEST_CHUNKS, {"ids": ids, "q": embed_query(question)}).fetchall()
    texts = dict(rows)
    pairs = [(question, texts[ad_id]) for ad_id in ids]
    scores = get_reranker().predict(pairs, batch_size=16)
    ranked = sorted(zip(ids, scores), key=lambda item: item[1], reverse=True)
    return [(ad_id, float(score)) for ad_id, score in ranked]