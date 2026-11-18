"""One entry point for all searches: vector, keyword, or hybrid (both combined)."""
import argparse
from collections import defaultdict

from jobmatch.db import connect
from jobmatch.search.keyword import keyword_search
from jobmatch.search.vector import vector_search

RRF_K = 60  # the usual constant for Reciprocal Rank Fusion


def reciprocal_rank_fusion(*rankings: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Combine ranked lists. Each ad gets 1 / (60 + rank) from every list it appears in.

    Only the rank is used, never the raw score, because vector and keyword
    scores are on completely different scales.
    """
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, (ad_id, _score) in enumerate(ranking, start=1):
            scores[ad_id] += 1 / (RRF_K + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def search(
    question: str, mode: str = "hybrid", city: str | None = None,
    language: str | None = None, k: int = 10,
) -> list[dict]:
    """Search ads and return the top k with their details."""
    with connect() as conn:
        if mode == "vector":
            ranked = vector_search(conn, question, city, language)
        elif mode == "keyword":
            ranked = keyword_search(conn, question, city, language)
        elif mode == "hybrid":
            ranked = reciprocal_rank_fusion(
                vector_search(conn, question, city, language),
                keyword_search(conn, question, city, language),
            )
        else:
            raise ValueError(f"unknown mode: {mode}")
        ranked = ranked[:k]
        ids = [ad_id for ad_id, _ in ranked]
        rows = conn.execute(
            "SELECT id, title, employer, city, language, url FROM ads WHERE id = ANY(%s)",
            (ids,),
        ).fetchall()
    details = {r[0]: r for r in rows}
    results = []
    for ad_id, score in ranked:
        _, title, employer, ad_city, ad_language, url = details[ad_id]
        results.append({
            "id": ad_id, "title": title, "employer": employer, "city": ad_city,
            "language": ad_language, "url": url, "score": round(score, 4),
        })
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the job ads")
    parser.add_argument("question")
    parser.add_argument("--mode", choices=["vector", "keyword", "hybrid"], default="hybrid")
    parser.add_argument("--city")
    parser.add_argument("--language", choices=["sv", "en"])
    args = parser.parse_args()
    results = search(args.question, args.mode, args.city, args.language)
    print(f"{args.mode} search: {args.question!r}  ({len(results)} results)")
    for rank, ad in enumerate(results, start=1):
        print(f"{rank:2}. {ad['score']:.4f}  [{ad['language']}] {ad['title']}  |  {ad['employer']}, {ad['city']}")


if __name__ == "__main__":
    main()