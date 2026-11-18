"""Measure search quality on the hand-labelled test set and write eval/results.md.

Run:  python -m jobmatch.evaluation.run_eval
"""
import statistics
import time
from collections import defaultdict
from pathlib import Path

from jobmatch.evaluation.data import load_labels, load_queries
from jobmatch.evaluation.metrics import ndcg_at_k, recall_at_k, reciprocal_rank
from jobmatch.search.engine import search

MODES = ["keyword", "vector", "hybrid"]
RESULTS_FILE = Path("eval/results.md")


def main() -> None:
    queries = load_queries()
    labels = load_labels()
    scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    by_type: dict[tuple[str, str], list[float]] = defaultdict(list)
    used = 0
    for query in queries:
        relevant = {ad_id for ad_id, rel in labels.get(query["id"], {}).items() if rel == 1}
        if not relevant:
            continue  # not labelled yet, or no relevant ads at all
        used += 1
        for mode in MODES:
            start = time.perf_counter()
            results = search(query["query"], mode, query.get("city"), query.get("language"), k=10)
            scores[mode]["latency_ms"].append((time.perf_counter() - start) * 1000)
            ranked = [ad["id"] for ad in results]
            scores[mode]["recall@10"].append(recall_at_k(ranked, relevant))
            scores[mode]["mrr"].append(reciprocal_rank(ranked, relevant))
            scores[mode]["ndcg@10"].append(ndcg_at_k(ranked, relevant))
            by_type[(mode, query.get("type", "other"))].append(ndcg_at_k(ranked, relevant))

    if used == 0:
        print("No labelled queries yet. Run: python -m jobmatch.evaluation.label")
        return

    lines = [f"# Search evaluation\n\n{used} labelled queries, top 10 results.\n",
             "| Method | Recall@10 | MRR | nDCG@10 | Median latency (ms) |",
             "| --- | --- | --- | --- | --- |"]
    for mode in MODES:
        s = scores[mode]
        lines.append(
            f"| {mode} | {statistics.mean(s['recall@10']):.3f} | {statistics.mean(s['mrr']):.3f} | "
            f"{statistics.mean(s['ndcg@10']):.3f} | {statistics.median(s['latency_ms']):.0f} |"
        )
    types = sorted({t for _, t in by_type})
    lines += ["\n## nDCG@10 by query type\n", "| Method | " + " | ".join(types) + " |",
              "| --- |" + " --- |" * len(types)]
    for mode in MODES:
        cells = [f"{statistics.mean(by_type[(mode, t)]):.3f}" if by_type[(mode, t)] else "-" for t in types]
        lines.append(f"| {mode} | " + " | ".join(cells) + " |")
    report = "\n".join(lines) + "\n"
    RESULTS_FILE.write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()