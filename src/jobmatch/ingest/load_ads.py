"""Load the downloaded ads into Postgres. Safe to run many times: no duplicates."""
import json
from pathlib import Path

import psycopg

from jobmatch.ingest.clean import clean_text, detect_language

DB_URL = "postgresql://jobmatch:jobmatch@localhost:5432/jobmatch"
IN_FILE = Path("data/raw/ads.jsonl")

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS ads (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    employer   TEXT,
    city       TEXT,
    deadline   TIMESTAMPTZ,
    url        TEXT,
    text       TEXT NOT NULL,
    language   TEXT NOT NULL,
    loaded_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

UPSERT = """
INSERT INTO ads (id, title, employer, city, deadline, url, text, language)
VALUES (%(id)s, %(title)s, %(employer)s, %(city)s, %(deadline)s, %(url)s, %(text)s, %(language)s)
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    employer = EXCLUDED.employer,
    city = EXCLUDED.city,
    deadline = EXCLUDED.deadline,
    url = EXCLUDED.url,
    text = EXCLUDED.text,
    language = EXCLUDED.language,
    loaded_at = now();
"""


def read_ads(path: Path) -> list[dict]:
    """Read the JSON lines file, clean each ad, and skip broken ones."""
    ads = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            ad = json.loads(line)
            if not ad.get("id") or not ad.get("title"):
                continue
            ad["text"] = clean_text(ad.get("text"))
            ad["language"] = detect_language(ad["text"])
            ads.append(ad)
    return ads


def main() -> None:
    ads = read_ads(IN_FILE)
    print(f"read {len(ads)} ads from {IN_FILE}")
    with psycopg.connect(DB_URL) as conn:
        conn.execute(CREATE_TABLE)
        with conn.cursor() as cur:
            cur.executemany(UPSERT, ads)
        total = conn.execute("SELECT count(*) FROM ads").fetchone()[0]
    print(f"the ads table now has {total} rows")


if __name__ == "__main__":
    main()