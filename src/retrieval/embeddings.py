from __future__ import annotations

from functools import lru_cache
import hashlib
import logging
from typing import Any

import numpy as np

try:
    from langchain_core.embeddings import Embeddings
except ImportError:  # pragma: no cover - project dependencies normally provide this
    class Embeddings:
        pass

try:
    from sentence_transformers import SentenceTransformer

    HAS_SENTENCE_TRANSFORMERS = True
except Exception:  # pragma: no cover - deterministic fallback supports offline runs
    HAS_SENTENCE_TRANSFORMERS = False


logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def _load_model(model_name: str):
    if not HAS_SENTENCE_TRANSFORMERS:
        logger.warning("sentence-transformers is unavailable; using deterministic fallback")
        return None
    try:
        logger.info("Loading sentence-transformer model=%s", model_name)
        return SentenceTransformer(model_name)
    except Exception as exc:  # pragma: no cover - depends on model/network availability
        logger.warning(
            "Could not load embedding model=%s (%s); using deterministic fallback",
            model_name,
            type(exc).__name__,
        )
        return None


def load_embedding_model(model_name: str):
    """Load and cache a sentence-transformer model for the current process."""
    normalized_name = model_name.strip()
    if not normalized_name:
        raise ValueError("Embedding model name must not be empty.")
    return _load_model(normalized_name)


def _validate_text(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")
    return value.strip()


def _as_vectors(encoded: Any) -> list[list[float]]:
    values = encoded.tolist() if hasattr(encoded, "tolist") else encoded
    return [[float(component) for component in vector] for vector in values]


def _fallback_embed(text: str) -> list[float]:
    values = [
        int(hashlib.sha256(f"{text}::{index}".encode("utf-8")).hexdigest()[:8], 16)
        / 0xFFFFFFFF
        - 0.5
        for index in range(384)
    ]
    vector = np.asarray(values, dtype=float)
    norm = np.linalg.norm(vector) or 1.0
    return (vector / norm).tolist()


def embed_texts(
    texts: list[str],
    model_name: str,
    batch_size: int = 32,
) -> list[list[float]]:
    """Embed a validated batch and verify a stable vector dimension."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1.")
    if not texts:
        return []

    validated = [_validate_text(text, label=f"texts[{index}]") for index, text in enumerate(texts)]
    model = load_embedding_model(model_name)
    vectors: list[list[float]]
    if model is None:
        vectors = [_fallback_embed(text) for text in validated]
    else:
        try:
            encoded = model.encode(
                validated,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            vectors = _as_vectors(encoded)
        except Exception as exc:  # pragma: no cover - backend-specific failure
            logger.warning(
                "Embedding failed for model=%s (%s); using deterministic fallback",
                model_name,
                type(exc).__name__,
            )
            vectors = [_fallback_embed(text) for text in validated]

    if len(vectors) != len(validated):
        raise RuntimeError(
            f"Embedding backend returned {len(vectors)} vectors for {len(validated)} texts."
        )
    dimensions = {len(vector) for vector in vectors}
    if len(dimensions) != 1 or 0 in dimensions:
        raise RuntimeError("Embedding backend returned inconsistent or empty vectors.")

    dimension = next(iter(dimensions))
    if model is not None:
        dimension_getter = getattr(model, "get_embedding_dimension", None)
        if dimension_getter is None:
            dimension_getter = model.get_sentence_embedding_dimension
        expected_dimension = dimension_getter()
        if expected_dimension is not None and dimension != expected_dimension:
            raise RuntimeError(
                f"Embedding dimension mismatch: expected {expected_dimension}, received {dimension}."
            )
    logger.info(
        "Embedded %d documents with model=%s batch_size=%d dimension=%d",
        len(validated),
        model_name,
        batch_size,
        dimension,
    )
    return vectors


def embed_query(query: str, model_name: str) -> list[float]:
    """Embed one non-empty query with the same validation as documents."""
    validated = _validate_text(query, label="query")
    return embed_texts([validated], model_name=model_name, batch_size=1)[0]


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str, batch_size: int = 32):
        self.model_name = model_name
        self.batch_size = batch_size
        self.model = load_embedding_model(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return embed_texts(texts, model_name=self.model_name, batch_size=self.batch_size)

    def embed_query(self, text: str) -> list[float]:
        return embed_query(text, model_name=self.model_name)
