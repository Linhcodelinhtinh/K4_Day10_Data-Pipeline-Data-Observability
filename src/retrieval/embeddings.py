from __future__ import annotations

from functools import lru_cache
import hashlib
import numpy as np

try:
    from langchain_core.embeddings import Embeddings
except ImportError:
    class Embeddings:
        pass

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except Exception:
    HAS_SENTENCE_TRANSFORMERS = False


@lru_cache(maxsize=4)
def _load_model(model_name: str):
    if HAS_SENTENCE_TRANSFORMERS:
        try:
            return SentenceTransformer(model_name)
        except Exception:
            pass
    return None


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = _load_model(model_name)

    def _fallback_embed(self, text: str) -> list[float]:
        vec = []
        for i in range(384):
            h = hashlib.sha256(f"{text}::{i}".encode("utf-8")).hexdigest()
            vec.append(int(h[:8], 16) / 0xFFFFFFFF - 0.5)
        arr = np.array(vec, dtype=float)
        norm = np.linalg.norm(arr) or 1.0
        return (arr / norm).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.model is not None:
            try:
                embeddings = self.model.encode(texts, normalize_embeddings=True)
                return embeddings.tolist()
            except Exception:
                pass
        return [self._fallback_embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        if self.model is not None:
            try:
                embedding = self.model.encode([text], normalize_embeddings=True)
                return embedding[0].tolist()
            except Exception:
                pass
        return self._fallback_embed(text)

