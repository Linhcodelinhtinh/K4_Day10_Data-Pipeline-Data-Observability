from __future__ import annotations

import pytest

import retrieval.embeddings as embeddings


class FakeModel:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.calls: list[dict] = []

    def encode(self, texts, **kwargs):
        self.calls.append({"texts": list(texts), **kwargs})
        return [[float(len(text)), 1.0, 0.5] for text in texts]

    def get_sentence_embedding_dimension(self):
        return 3


def test_model_is_cached_and_batch_embedding_is_valid(monkeypatch):
    created: list[FakeModel] = []

    def factory(model_name: str):
        model = FakeModel(model_name)
        created.append(model)
        return model

    embeddings._load_model.cache_clear()
    monkeypatch.setattr(embeddings, "SentenceTransformer", factory)

    first = embeddings.load_embedding_model("test-model")
    second = embeddings.load_embedding_model("test-model")
    vectors = embeddings.embed_texts(["first", "second"], "test-model", batch_size=2)

    assert first is second
    assert len(created) == 1
    assert len(vectors) == 2
    assert all(len(vector) == 3 for vector in vectors)
    assert created[0].calls[-1]["batch_size"] == 2
    assert created[0].calls[-1]["normalize_embeddings"] is True
    assert created[0].calls[-1]["show_progress_bar"] is False
    embeddings._load_model.cache_clear()


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_query_is_rejected(value):
    with pytest.raises(ValueError, match="query must be a non-empty string"):
        embeddings.embed_query(value, "unused-model")


def test_empty_document_is_rejected_before_loading_model():
    with pytest.raises(ValueError, match=r"texts\[1\]"):
        embeddings.embed_texts(["valid", ""], "unused-model")


def test_empty_batch_returns_empty_list():
    assert embeddings.embed_texts([], "unused-model") == []
