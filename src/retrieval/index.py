from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.errors import NotFoundError
import pandas as pd

from core.config import Settings
from core.utils import normalize_whitespace, read_json, safe_slug, write_json
from retrieval.embeddings import MiniLMEmbeddings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    paper_id: str
    title: str
    score: float
    content: str
    metadata: dict[str, Any]
    rank: int = 0
    distance: float = 0.0


class LocalEmbeddingIndex:
    def __init__(
        self,
        settings: Settings,
        collection_name: str,
        documents: list[dict[str, Any]],
        persist_path: Path,
    ):
        self.settings = settings
        self.collection_name = collection_name
        self.documents = documents
        self.persist_path = persist_path
        self.embedding_backend = "chroma"
        self.embedding_model = MiniLMEmbeddings(settings.embedding_model)
        self.client = chromadb.PersistentClient(path=str(persist_path))
        self.collection = self.client.get_collection(name=collection_name)
        self.documents_by_paper_id = {
            self._normalize_lookup(document["paper_id"]): document for document in documents
        }
        self.documents_by_title = {
            self._normalize_lookup(document["title"]): document for document in documents
        }

    @staticmethod
    def _normalize_lookup(value: Any) -> str:
        return normalize_whitespace(str(value or "")).casefold()

    @staticmethod
    def _metadata_string(value: Any) -> str:
        if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
            return ""
        return str(value)

    @staticmethod
    def _metadata_int(value: Any) -> int:
        if value is None or pd.isna(value):
            return 0
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _build_documents(df: pd.DataFrame) -> list[dict[str, Any]]:
        records = df.to_dict(orient="records")
        documents: list[dict[str, Any]] = []
        for index, row in enumerate(records):
            paper_id = LocalEmbeddingIndex._metadata_string(row.get("paper_id")).strip()
            title = LocalEmbeddingIndex._metadata_string(row.get("title")).strip()
            content = LocalEmbeddingIndex._metadata_string(row.get("text_for_embedding")).strip()
            if not content:
                content = title
                if content:
                    logger.warning(
                        "text_for_embedding is empty for paper_id=%s; using title fallback",
                        paper_id or "<missing>",
                    )
            if not content:
                logger.warning("Skipping row=%d because it has no embeddable text", index)
                continue
            if not paper_id:
                logger.warning("Skipping row=%d because paper_id is empty", index)
                continue

            documents.append(
                {
                    "record_id": f"{paper_id}::{index}",
                    "paper_id": paper_id,
                    "title": title,
                    "content": content,
                    "metadata": {
                        "paper_id": paper_id,
                        "title": title,
                        "published": LocalEmbeddingIndex._metadata_string(row.get("published")),
                        "age_days": LocalEmbeddingIndex._metadata_int(row.get("age_days")),
                        "authors_joined": LocalEmbeddingIndex._metadata_string(row.get("authors_joined")),
                        "categories_joined": LocalEmbeddingIndex._metadata_string(row.get("categories_joined")),
                        "summary": LocalEmbeddingIndex._metadata_string(row.get("summary")),
                        "abs_url": LocalEmbeddingIndex._metadata_string(row.get("abs_url")),
                        "pdf_url": LocalEmbeddingIndex._metadata_string(row.get("pdf_url")),
                    },
                }
            )
        return documents

    @staticmethod
    def _derive_collection_name(settings: Settings, embeddings_output_path: Path | None) -> str:
        if embeddings_output_path is None:
            return settings.baseline_collection_name

        name_map = {
            settings.paths.embeddings_json.resolve(): settings.baseline_collection_name,
            settings.paths.corrupted_embeddings_json.resolve(): settings.corrupted_collection_name,
            settings.paths.repaired_embeddings_json.resolve(): settings.repaired_collection_name,
        }
        resolved_path = embeddings_output_path.resolve()
        if resolved_path in name_map:
            return name_map[resolved_path]
        return safe_slug(embeddings_output_path.stem)

    @classmethod
    def build(
        cls,
        df: pd.DataFrame,
        settings: Settings,
        embeddings_output_path: Path | None = None,
        collection_name: str | None = None,
        reset: bool = False,
    ) -> "LocalEmbeddingIndex":
        resolved_collection_name = collection_name or cls._derive_collection_name(
            settings, embeddings_output_path
        )
        if not resolved_collection_name.strip():
            raise ValueError("collection_name must not be empty.")
        documents = cls._build_documents(df)
        if not documents:
            raise ValueError("No valid documents are available to build the embedding index.")
        persist_path = settings.paths.chroma_dir
        persist_path.mkdir(parents=True, exist_ok=True)

        embedding_model = MiniLMEmbeddings(settings.embedding_model)
        client = chromadb.PersistentClient(path=str(persist_path))
        try:
            client.get_collection(name=resolved_collection_name)
            collection_exists = True
        except NotFoundError:
            collection_exists = False

        if collection_exists and not reset:
            raise ValueError(
                f"Collection '{resolved_collection_name}' already exists; pass reset=True to rebuild it."
            )
        if collection_exists:
            client.delete_collection(name=resolved_collection_name)

        collection = client.create_collection(
            name=resolved_collection_name,
            configuration={"hnsw": {"space": "cosine"}},
        )
        embeddings = embedding_model.embed_documents([document["content"] for document in documents])
        collection.add(
            ids=[document["record_id"] for document in documents],
            embeddings=embeddings,
            documents=[document["content"] for document in documents],
            metadatas=[document["metadata"] for document in documents],
        )

        manifest_path = embeddings_output_path or settings.paths.embeddings_json
        write_json(
            manifest_path,
            {
                "backend": "chroma",
                "embedding_model": settings.embedding_model,
                "persist_path": str(persist_path),
                "collection_name": resolved_collection_name,
                "document_count": collection.count(),
                "documents": documents,
            },
        )
        logger.info(
            "Indexed %d documents into collection=%s",
            collection.count(),
            resolved_collection_name,
        )
        return cls(
            settings=settings,
            collection_name=resolved_collection_name,
            documents=documents,
            persist_path=persist_path,
        )

    @classmethod
    def load(cls, settings: Settings, embeddings_path: Path | None = None) -> "LocalEmbeddingIndex":
        payload = read_json(embeddings_path or settings.paths.embeddings_json)
        return cls(
            settings=settings,
            collection_name=payload["collection_name"],
            documents=payload["documents"],
            persist_path=Path(payload["persist_path"]),
        )

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        if not query.strip():
            return []
        collection_count = self.collection.count()
        if collection_count == 0:
            return []
        requested_top_k = self.settings.top_k if top_k is None else top_k
        if requested_top_k < 1:
            raise ValueError("top_k must be at least 1.")

        query_embedding = self.embedding_model.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(requested_top_k, collection_count),
            include=["documents", "metadatas", "distances"],
        )
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        scored: list[SearchResult] = []
        for rank, (record_id, content, metadata, distance) in enumerate(
            zip(ids, documents, metadatas, distances, strict=False), start=1
        ):
            if not record_id or not metadata or not content:
                continue
            resolved_distance = float(distance) if distance is not None else 0.0
            scored.append(
                SearchResult(
                    paper_id=str(metadata["paper_id"]),
                    title=str(metadata["title"]),
                    score=min(1.0, max(0.0, 1.0 - resolved_distance)),
                    content=str(content),
                    metadata=dict(metadata),
                    rank=rank,
                    distance=resolved_distance,
                )
            )
        return scored

    def semantic_search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        return self.search(query=query, top_k=top_k)

    def lookup_by_paper_id(self, paper_id: str) -> dict[str, Any] | None:
        return self.documents_by_paper_id.get(self._normalize_lookup(paper_id))

    def lookup_by_title(
        self,
        title: str,
        *,
        semantic_fallback: bool = False,
    ) -> dict[str, Any] | None:
        normalized_title = self._normalize_lookup(title)
        exact = self.documents_by_title.get(normalized_title)
        if exact or not semantic_fallback or not normalized_title:
            return exact
        results = self.search(title, top_k=1)
        if not results:
            return None
        result = results[0]
        return {
            "record_id": result.paper_id,
            "paper_id": result.paper_id,
            "title": result.title,
            "content": result.content,
            "metadata": result.metadata,
        }

    def lookup(self, value: str) -> dict[str, Any] | None:
        return self.lookup_by_paper_id(value) or self.lookup_by_title(value)
