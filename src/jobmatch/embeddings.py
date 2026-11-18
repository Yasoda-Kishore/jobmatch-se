"""Turn text into vectors with a multilingual model (Swedish and English)."""
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"
DIMENSIONS = 384


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load the model once and reuse it (the first call downloads it)."""
    return SentenceTransformer(MODEL_NAME)


def embed_passages(texts: list[str]) -> np.ndarray:
    """Embed document chunks. e5 models expect the prefix 'passage: '."""
    return get_model().encode(
        [f"passage: {t}" for t in texts], batch_size=32, normalize_embeddings=True
    )


def embed_query(text: str) -> np.ndarray:
    """Embed a search question. e5 models expect the prefix 'query: '."""
    return get_model().encode(f"query: {text}", normalize_embeddings=True)