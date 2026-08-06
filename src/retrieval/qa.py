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
    if not top_result or not top_result.metadata:
        return "Insufficient evidence in the indexed corpus."
    lowered = question.lower()
    metadata = top_result.metadata
    if "who authored" in lowered or "list the authors" in lowered:
        val = metadata.get("authors_joined") or metadata.get("authors")
        return str(val) if val else "Insufficient evidence in the indexed corpus."
    if "when was" in lowered or "publication date" in lowered or "published on" in lowered:
        val = metadata.get("published")
        return str(val) if val else "Insufficient evidence in the indexed corpus."
    if "what categories" in lowered:
        val = metadata.get("categories_joined") or metadata.get("categories")
        return str(val) if val else "Insufficient evidence in the indexed corpus."
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


def _detect_data_issue(answer: str, retrieved: list[SearchResult]) -> tuple[bool, str]:
    if not retrieved:
        return True, "Không tìm thấy tài liệu liên quan trong collection hiện tại"
    
    # Check paper_id corruption
    for res in retrieved:
        if "INVALID_CORRUPTED_ID" in res.paper_id:
            return True, f"Mã định danh paper_id bị hỏng format ('{res.paper_id}')"

    # Check summary retraction / noise / empty
    if "[RETRACTED/INVALID STATEMENT]" in answer:
        return True, "Dữ liệu bị chèn câu lệnh sai lệch/rút bài ([RETRACTED/INVALID STATEMENT])"
    if "<jats:" in answer or "CORRUPTED_XML" in answer or "NOISE_GARBAGE" in answer:
        return True, "Dữ liệu bị chèn nhiễu thẻ XML/HTML rác"
    if answer == "Insufficient evidence in the indexed corpus." or not answer.strip():
        return True, "Thiếu thông tin / Tóm tắt bị xoá rỗng trong index"

    return False, ""


def _fallback_retrieve_from_raw(question: str, settings: Settings) -> tuple[str, str, str]:
    raw_path = settings.paths.raw_records_json
    if not raw_path.exists():
        return "", "", ""

    from ingestion.crossref import load_raw_records
    try:
        records = load_raw_records(raw_path)
    except Exception:
        return "", "", ""

    # Try title match in single quotes
    title_match = re.search(r"'([^']+)'", question)
    target_title = title_match.group(1).lower().strip() if title_match else ""

    lowered_q = question.lower()
    matched_record = None

    for rec in records:
        rec_title = rec.title.lower().strip()
        rec_id = rec.paper_id.lower().strip()

        if target_title and (target_title in rec_title or rec_title in target_title):
            matched_record = rec
            break

        # Match keywords in question (e.g. paper name like SafeRAG)
        words = [w for w in re.findall(r"\b[a-zA-Z0-9]{4,}\b", question) if w.lower() not in {"what", "who", "when", "where", "which", "paper", "authors", "summary", "published"}]
        if words and any(w.lower() in rec_title or w.lower() in rec.summary.lower() for w in words):
            matched_record = rec
            break

    if not matched_record:
        matched_record = records[0] if records else None

    if not matched_record:
        return "", "", ""

    # Extract answer based on question type
    if "who authored" in lowered_q or "authors" in lowered_q:
        ans_text = ", ".join(matched_record.authors) if matched_record.authors else matched_record.summary
    elif "published" in lowered_q or "date" in lowered_q:
        ans_text = matched_record.published
    elif "categories" in lowered_q:
        ans_text = ", ".join(matched_record.categories)
    else:
        ans_text = first_sentence(matched_record.summary) or matched_record.summary

    return ans_text, matched_record.paper_id, matched_record.title


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

    # Check if data corruption or missing evidence issue is detected
    is_issue, issue_desc = _detect_data_issue(answer, retrieved)
    if is_issue:
        raw_ans, raw_doi, raw_title = _fallback_retrieve_from_raw(question, settings)
        if raw_ans:
            answer = (
                f"[CẢNH BÁO DỮ LIỆU LỖI]: Phát hiện vấn đề dữ liệu trong collection '{index.collection_name}' "
                f"({issue_desc}).\n"
                f"👉 Tự động chuyển sang truy xuất từ nguồn dữ liệu thô (Raw Data Snapshot).\n\n"
                f"Answer: {raw_ans}\n\n"
                f"Nguồn truy xuất: Raw Data Snapshot [data/raw/crossref_records.json] (DOI: {raw_doi})"
            )
            provider = "raw_snapshot_fallback"

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

