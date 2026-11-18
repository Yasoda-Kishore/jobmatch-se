"""Label the test set by hand: for each query, judge the ads that any search method returns.

Run:  python -m jobmatch.evaluation.label
Keys: y = relevant, n = not relevant, s = skip for now, q = quit (progress is saved)
"""
import random

from jobmatch.db import connect
from jobmatch.evaluation.data import load_labels, load_queries, save_label
from jobmatch.search.engine import search

POOL_DEPTH = 10  # judge the top 10 from each search method


def candidate_pool(query: dict) -> list[str]:
    """All ads that vector, keyword or hybrid search put in their top 10, in random order."""
    pool: set[str] = set()
    for mode in ("vector", "keyword", "hybrid"):
        results = search(query["query"], mode, query.get("city"), query.get("language"), POOL_DEPTH)
        pool.update(ad["id"] for ad in results)
    ordered = sorted(pool)
    random.Random(query["id"]).shuffle(ordered)  # random order, so you can't tell which method found it
    return ordered


def main() -> None:
    queries = load_queries()
    labels = load_labels()
    with connect() as conn:
        for number, query in enumerate(queries, start=1):
            done = labels.get(query["id"], {})
            todo = [ad_id for ad_id in candidate_pool(query) if ad_id not in done]
            if not todo:
                continue
            filters = ", ".join(f"{k}={query[k]}" for k in ("city", "language") if query.get(k))
            print(f"\n=== Query {number}/{len(queries)}: {query['query']!r} {filters} ===")
            print(f"    {len(todo)} ads to judge")
            for i, ad_id in enumerate(todo, start=1):
                title, employer, city, text = conn.execute(
                    "SELECT title, employer, city, text FROM ads WHERE id = %s", (ad_id,)
                ).fetchone()
                print(f"\n[{i}/{len(todo)}] {title}  |  {employer}, {city}")
                print(f"    {text[:350]}...")
                while True:
                    answer = input("    relevant? (y/n/s/q): ").strip().lower()
                    if answer in {"y", "n", "s", "q"}:
                        break
                if answer == "q":
                    print("Saved. Run the same command again to continue.")
                    return
                if answer in {"y", "n"}:
                    save_label(query["id"], ad_id, 1 if answer == "y" else 0)
    print("\nAll queries are labelled.")


if __name__ == "__main__":
    main()