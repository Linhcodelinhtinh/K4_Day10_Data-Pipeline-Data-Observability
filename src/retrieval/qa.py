from __future__ import annotations

from dataclasses import dataclass
import re
from time import perf_counter

from core.config import Settings, normalized_provider
from core.utils import first_sentence
from retrieval.index import LocalEmbeddingIndex, SearchResult


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    retrieved_doc_ids: list[str]
    retrieved_contexts: list[str]
    retrieved_titles: list[str]
    provider: str = "deterministic"
    latency_ms: float = 0.0
    collection_name: str = ""

    @property
    def contexts(self) -> list[str]:
        return self.retrieved_contexts


def _extract_answer(question: str, top_result: SearchResult) -> str:
    lowered = question.lower()
    metadata = top_result.metadata
    if "who authored" in lowered or "list the authors" in lowered:
        return str(metadata.get("authors_joined") or "Insufficient evidence in the indexed corpus.")
    if "when was" in lowered or "publication date" in lowered or "published on" in lowered:
        return str(metadata.get("published") or "Insufficient evidence in the indexed corpus.")
    if "what categories" in lowered:
        return str(metadata.get("categories_joined") or "Insufficient evidence in the indexed corpus.")
    summary = str(metadata.get("summary") or "").strip()
    return first_sentence(summary) if summary else "Insufficient evidence in the indexed corpus."


def _deduplicate_results(results: list[SearchResult]) -> list[SearchResult]:
    deduplicated: list[SearchResult] = []
    seen: set[str] = set()
    for result in results:
        normalized_id = result.paper_id.strip().casefold()
        if normalized_id in seen:
            continue
        seen.add(normalized_id)
        deduplicated.append(result)
    return deduplicated


def answer_question(
    question: str,
    settings: Settings,
    index: LocalEmbeddingIndex,
    top_k: int | None = None,
    use_agent: bool = False,
) -> AnswerResult:
    started = perf_counter()
    title_match = re.search(r"'([^']+)'", question)
    exact = index.lookup(title_match.group(1)) if title_match else None
    retrieved = index.search(question, top_k=top_k)
    if exact:
        exact_result = SearchResult(
            paper_id=exact["paper_id"],
            title=exact["title"],
            score=1.0,
            content=exact["content"],
            metadata=exact["metadata"],
        )
        retrieved = [exact_result] + retrieved
    retrieved = _deduplicate_results(retrieved)[: (top_k or settings.top_k)]

    if not retrieved:
        answer = "Insufficient evidence in the indexed corpus."
        provider = "deterministic"
    elif use_agent:
        from retrieval.agent import build_agent, run_agent_question

        agent = build_agent(settings=settings, index=index)
        answer = run_agent_question(agent, question)
        provider = normalized_provider(settings)
    else:
        answer = _extract_answer(question, retrieved[0])
        provider = "deterministic"

    latency_ms = (perf_counter() - started) * 1000.0
    return AnswerResult(
        question=question,
        answer=answer,
        retrieved_doc_ids=[item.paper_id for item in retrieved],
        retrieved_contexts=[item.content for item in retrieved],
        retrieved_titles=[item.title for item in retrieved],
        provider=provider,
        latency_ms=latency_ms,
        collection_name=index.collection_name,
    )
