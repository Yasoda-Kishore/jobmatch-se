"""Read and write the test set files in the eval/ folder."""
import json
from pathlib import Path

QUERIES_FILE = Path("eval/queries.jsonl")
LABELS_FILE = Path("eval/labels.jsonl")


def load_queries() -> list[dict]:
    with QUERIES_FILE.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_labels() -> dict[str, dict[str, int]]:
    """Return {query_id: {ad_id: 1 or 0}}. 1 = relevant, 0 = not relevant."""
    labels: dict[str, dict[str, int]] = {}
    if LABELS_FILE.exists():
        with LABELS_FILE.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    labels.setdefault(row["query_id"], {})[row["ad_id"]] = row["relevant"]
    return labels


def save_label(query_id: str, ad_id: str, relevant: int) -> None:
    """Append one judgement right away, so nothing is lost if you stop."""
    LABELS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LABELS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"query_id": query_id, "ad_id": ad_id, "relevant": relevant}) + "\n")