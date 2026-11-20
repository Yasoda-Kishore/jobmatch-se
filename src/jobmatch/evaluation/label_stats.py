"""Show how many ads you marked y and n for each query, to check your labels.

Run:  python -m jobmatch.evaluation.label_stats
"""
from jobmatch.evaluation.data import load_labels, load_queries


def main() -> None:
    labels = load_labels()
    print(f"{'id':<5} {'type':<7} {'y':>3} {'n':>3}  {'y%':>4}  query")
    for query in load_queries():
        judged = labels.get(query["id"])
        if not judged:
            continue
        yes = sum(judged.values())
        no = len(judged) - yes
        share = round(100 * yes / len(judged))
        warning = "   <-- check: all y" if no == 0 else ""
        print(f"{query['id']:<5} {query.get('type', ''):<7} {yes:>3} {no:>3}  {share:>3}%  {query['query']}{warning}")


if __name__ == "__main__":
    main()