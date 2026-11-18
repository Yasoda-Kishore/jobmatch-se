"""Chunk every ad that has no chunks yet, embed the chunks, and store them in pgvector."""
from jobmatch.db import connect
from jobmatch.embeddings import DIMENSIONS, embed_passages
from jobmatch.ingest.chunk import chunk_text

ADS_PER_BATCH = 50

CREATE_CHUNKS = f"""
CREATE TABLE IF NOT EXISTS chunks (
    id           BIGSERIAL PRIMARY KEY,
    ad_id        TEXT NOT NULL REFERENCES ads(id) ON DELETE CASCADE,
    chunk_index  INT NOT NULL,
    text         TEXT NOT NULL,
    embedding    vector({DIMENSIONS}) NOT NULL,
    UNIQUE (ad_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);
"""

ADS_WITHOUT_CHUNKS = """
SELECT a.id, a.title, a.text
FROM ads a
WHERE NOT EXISTS (SELECT 1 FROM chunks c WHERE c.ad_id = a.id)
ORDER BY a.id
LIMIT %s;
"""

INSERT_CHUNK = """
INSERT INTO chunks (ad_id, chunk_index, text, embedding)
VALUES (%s, %s, %s, %s)
ON CONFLICT (ad_id, chunk_index) DO NOTHING;
"""


def main() -> None:
    with connect() as conn:
        conn.execute(CREATE_CHUNKS)
        conn.commit()
        done_ads = 0
        while True:
            ads = conn.execute(ADS_WITHOUT_CHUNKS, (ADS_PER_BATCH,)).fetchall()
            if not ads:
                break
            rows = []
            for ad_id, title, text in ads:
                for i, chunk in enumerate(chunk_text(text)):
                    # Put the job title in front, so every chunk knows which job it is about
                    rows.append((ad_id, i, f"{title}. {chunk}"))
            vectors = embed_passages([r[2] for r in rows])
            with conn.cursor() as cur:
                cur.executemany(
                    INSERT_CHUNK, [(a, i, t, v) for (a, i, t), v in zip(rows, vectors)]
                )
            conn.commit()  # save after every batch, so a crash loses at most one batch
            done_ads += len(ads)
            print(f"embedded {done_ads} ads ({len(rows)} chunks in this batch)")
        total = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
    print(f"done: the chunks table has {total} rows")


if __name__ == "__main__":
    main()