"""Remember what the LLM extracted from each ad.

An ad's requirements are the same for every candidate, so we only need to read each ad once.
The cache entry is only used if the ad text and the LLM model are unchanged.
"""
import hashlib

import psycopg
from psycopg.types.json import Jsonb

from jobmatch.llm import LLM_MODEL
from jobmatch.match.fit import AdRequirements

CREATE_CACHE = """
CREATE TABLE IF NOT EXISTS ad_requirements (
    ad_id       TEXT PRIMARY KEY REFERENCES ads(id) ON DELETE CASCADE,
    text_hash   TEXT NOT NULL,
    model       TEXT NOT NULL,
    data        JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

SAVE = """
INSERT INTO ad_requirements (ad_id, text_hash, model, data)
VALUES (%s, %s, %s, %s)
ON CONFLICT (ad_id) DO UPDATE SET
    text_hash = EXCLUDED.text_hash, model = EXCLUDED.model, data = EXCLUDED.data, created_at = now();
"""


def text_hash(text: str) -> str:
    """A short fingerprint of the ad text. If the employer edits the ad, the fingerprint changes."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_cached(conn: psycopg.Connection, texts: dict[str, str]) -> dict[str, AdRequirements]:
    """Return the cached requirements for the given ads, if still valid. `texts` is {ad_id: ad text}."""
    conn.execute(CREATE_CACHE)
    rows = conn.execute(
        "SELECT ad_id, text_hash, model, data FROM ad_requirements WHERE ad_id = ANY(%s)", (list(texts),)
    ).fetchall()
    return {
        ad_id: AdRequirements.model_validate(data)
        for ad_id, saved_hash, model, data in rows
        if saved_hash == text_hash(texts[ad_id]) and model == LLM_MODEL
    }


def save(conn: psycopg.Connection, ad_id: str, text: str, req: AdRequirements) -> None:
    conn.execute(SAVE, (ad_id, text_hash(text), LLM_MODEL, Jsonb(req.model_dump())))
