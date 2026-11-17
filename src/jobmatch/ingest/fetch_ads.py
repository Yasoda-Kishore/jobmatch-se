"""Fetch Data/IT job ads from the JobTech JobSearch API and save them as JSON lines."""
import json
from pathlib import Path

import httpx

API_URL = "https://jobsearch.api.jobtechdev.se/search"
DATA_IT_FIELD = "apaJ_2ja_LuF"  # taxonomy id for the Data/IT occupation field
PAGE_SIZE = 100                 # the API returns at most 100 ads per call
OUT_FILE = Path("data/raw/ads.jsonl")


def fetch_page(client: httpx.Client, offset: int) -> list[dict]:
    params = {"occupation-field": DATA_IT_FIELD, "limit": PAGE_SIZE, "offset": offset}
    response = client.get(API_URL, params=params, headers={"accept": "application/json"})
    response.raise_for_status()
    return response.json().get("hits", [])


def simplify(ad: dict) -> dict:
    """Keep only the fields we need."""
    return {
        "id": ad.get("id"),
        "title": ad.get("headline"),
        "employer": (ad.get("employer") or {}).get("name"),
        "city": (ad.get("workplace_address") or {}).get("municipality"),
        "deadline": ad.get("application_deadline"),
        "url": ad.get("webpage_url"),
        "text": (ad.get("description") or {}).get("text", ""),
    }


def main(total: int = 2000) -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    ads = []
    with httpx.Client(timeout=30) as client:
        for offset in range(0, total, PAGE_SIZE):
            hits = fetch_page(client, offset)
            if not hits:
                break
            ads.extend(simplify(ad) for ad in hits)
            print(f"fetched {len(ads)} ads")
    with OUT_FILE.open("w", encoding="utf-8") as f:
        for ad in ads:
            f.write(json.dumps(ad, ensure_ascii=False) + "\n")
    print(f"saved {len(ads)} ads to {OUT_FILE}")


if __name__ == "__main__":
    main()