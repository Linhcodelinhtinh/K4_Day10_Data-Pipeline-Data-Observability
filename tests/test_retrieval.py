from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from core.config import load_settings
import retrieval.index as index_module


class FakeEmbeddings:
    def __init__(self, model_name: str, batch_size: int = 32):
        self.model_name = model_name

    @staticmethod
    def _vector(text: str) -> list[float]:
        lowered = text.casefold()
        return [
            float("machine" in lowered or "learning" in lowered),
            float("retrieval" in lowered or "search" in lowered),
            1.0,
        ]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@pytest.fixture(autouse=True)
def fake_embedding_backend(monkeypatch):
    monkeypatch.setattr(index_module, "MiniLMEmbeddings", FakeEmbeddings)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    rows = []
    for number, (title, summary) in enumerate(
        [
            ("Machine Learning Retrieval", "A study about machine learning and retrieval systems."),
            ("Database Search", "A study about database search and indexing."),
            ("Language Agents", "A study about language agents and tool use."),
        ],
        start=1,
    ):
        rows.append(
            {
                "paper_id": f"paper-{number}",
                "title": title,
                "summary": summary,
                "authors_joined": "Alice, Bob",
                "categories_joined": "Computer Science",
                "published": "2026-01-01",
                "age_days": 10,
                "abs_url": f"https://example.com/{number}",
                "pdf_url": "",
                "text_for_embedding": f"Title: {title} | Summary: {summary}",
            }
        )
    return pd.DataFrame(rows)


def _build(df, tmp_path: Path, collection_name: str):
    settings = load_settings(tmp_path)
    manifest = tmp_path / "data" / "embeddings" / f"{collection_name}.json"
    return index_module.LocalEmbeddingIndex.build(
        df,
        settings,
        embeddings_output_path=manifest,
        collection_name=collection_name,
        reset=True,
    )


def test_build_search_and_lookup(sample_df, tmp_path):
    index = _build(sample_df, tmp_path, "papers-test")

    assert index.collection.count() == 3
    results = index.semantic_search("machine learning", top_k=2)
    assert len(results) == 2
    assert results[0].rank == 1
    assert results[0].distance >= 0
    assert results[0].score <= 1
    assert index.lookup_by_paper_id(" PAPER-1 ")["title"] == "Machine Learning Retrieval"
    assert index.lookup_by_title("  machine   learning retrieval  ")["paper_id"] == "paper-1"
    assert index.search("   ") == []
    with pytest.raises(ValueError, match="top_k must be at least 1"):
        index.search("machine learning", top_k=0)


def test_title_fallback_and_null_metadata(sample_df, tmp_path):
    fallback = sample_df.iloc[[0]].copy()
    fallback.loc[:, "text_for_embedding"] = ""
    fallback.loc[:, "abs_url"] = None
    fallback["age_days"] = pd.Series([None], index=fallback.index, dtype="object")

    index = _build(fallback, tmp_path, "papers-fallback")
    stored = index.lookup_by_paper_id("paper-1")

    assert index.collection.count() == 1
    assert stored["content"] == "Machine Learning Retrieval"
    assert stored["metadata"]["abs_url"] == ""
    assert stored["metadata"]["age_days"] == 0


def test_reset_only_replaces_selected_collection(sample_df, tmp_path):
    settings = load_settings(tmp_path)
    for collection_name in ("papers-baseline", "papers-corrupted", "papers-repaired"):
        index_module.LocalEmbeddingIndex.build(
            sample_df,
            settings,
            embeddings_output_path=tmp_path / f"{collection_name}.json",
            collection_name=collection_name,
            reset=True,
        )

    smaller = sample_df.iloc[:1]
    rebuilt = index_module.LocalEmbeddingIndex.build(
        smaller,
        settings,
        embeddings_output_path=tmp_path / "papers-baseline.json",
        collection_name="papers-baseline",
        reset=True,
    )

    assert rebuilt.collection.count() == 1
    assert rebuilt.client.get_collection("papers-corrupted").count() == 3
    assert rebuilt.client.get_collection("papers-repaired").count() == 3
    with pytest.raises(ValueError, match="already exists"):
        index_module.LocalEmbeddingIndex.build(
            sample_df,
            settings,
            collection_name="papers-baseline",
            reset=False,
        )


@pytest.mark.parametrize(
    ("filename", "expected_count"),
    [
        ("papers_corrupted_blank_summary.csv", 24),
        ("papers_corrupted_corrupt_authors.csv", 24),
        ("papers_corrupted_corrupt_paper_id.csv", 24),
        ("papers_corrupted_drop_latest.csv", 20),
        ("papers_corrupted_duplicate_rows.csv", 28),
        ("papers_corrupted_misleading_summary.csv", 24),
        ("papers_corrupted_null_metadata.csv", 24),
        ("papers_corrupted_stale_date.csv", 24),
        ("papers_corrupted_text_noise.csv", 24),
        ("papers_corrupted_truncate_title.csv", 24),
    ],
)
def test_all_committed_corruption_scenarios_build(
    filename,
    expected_count,
    tmp_path,
):
    project_root = Path(__file__).resolve().parents[1]
    df = pd.read_csv(project_root / "data" / "clean" / "corrupted_by_type" / filename)
    collection_name = f"test-{filename.removesuffix('.csv').replace('_', '-')}"
    index = _build(df, tmp_path, collection_name)

    assert index.collection.count() == expected_count
    assert index.search("machine learning", top_k=2)
