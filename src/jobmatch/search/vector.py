"""Vector search: find the ads whose chunks are closest in meaning to a question."""
import sys

from jobmatch.db import connect
from jobmatch.embeddings import embed_query

SEARCH = """
SELECT a.id, a.title, a.employer, a.city, a.url,
       1 - (c.embedding <=> %(q)s) AS similarity
FROM chunks c
JOIN ads a ON a.id = c.ad_id
ORDER BY c.embedding <=> %(q)s
LIMIT 50;
"""


def search(question: str, k: int = 10) -> list[dict]:
    """Return the top k ads. One ad can have many chunks, so keep only its best chunk."""
    query_vector = embed_query(question)
    with connect() as conn:
        rows = conn.execute(SEARCH, {"q": query_vector}).fetchall()
    results, seen = [], set()
    for ad_id, title, employer, city, url, similarity in rows:
        if ad_id in seen:
            continue
        seen.add(ad_id)
        results.append(
            {"id": ad_id, "title": title, "employer": employer, "city": city,
             "url": url, "similarity": round(float(similarity), 3)}
        )
        if len(results) == k:
            break
    return results


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "python developer"
    for rank, ad in enumerate(search(question), start=1):
        print(f"{rank:2}. {ad['similarity']:.3f}  {ad['title']}  |  {ad['employer']}, {ad['city']}")