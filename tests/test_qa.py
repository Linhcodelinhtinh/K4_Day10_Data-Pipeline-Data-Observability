from __future__ import annotations

from core.config import load_settings
from retrieval.index import SearchResult
from retrieval.qa import answer_question


def _result(paper_id: str = "paper-1", summary: str = "A useful summary.") -> SearchResult:
    return SearchResult(
        paper_id=paper_id,
        title="Exact Paper Title",
        score=0.9,
        content=f"Title: Exact Paper Title | Summary: {summary}",
        metadata={
            "paper_id": paper_id,
            "title": "Exact Paper Title",
            "summary": summary,
            "authors_joined": "Alice, Bob",
            "categories_joined": "Machine Learning",
            "published": "2026-01-01",
        },
        rank=1,
        distance=0.1,
    )


class FakeIndex:
    collection_name = "papers-baseline"

    def __init__(self, results=None, exact=None):
        self.results = results or []
        self.exact = exact

    def search(self, question, top_k=None):
        return list(self.results)

    def lookup(self, value):
        return self.exact


def test_answer_question_keeps_evaluator_contract_and_deduplicates(tmp_path):
    result = _result()
    index = FakeIndex(results=[result, result])

    answer = answer_question("Summarize the paper", load_settings(tmp_path), index)

    assert answer.answer == "A useful summary."
    assert answer.retrieved_doc_ids == ["paper-1"]
    assert answer.contexts == answer.retrieved_contexts
    assert answer.provider == "deterministic"
    assert answer.collection_name == "papers-baseline"
    assert answer.latency_ms >= 0


def test_exact_title_is_prioritized(tmp_path):
    exact_result = _result("paper-exact")
    exact = {
        "paper_id": exact_result.paper_id,
        "title": exact_result.title,
        "content": exact_result.content,
        "metadata": exact_result.metadata,
    }
    other = _result("paper-other")
    index = FakeIndex(results=[other], exact=exact)

    answer = answer_question(
        "Who authored 'Exact Paper Title'?",
        load_settings(tmp_path),
        index,
    )

    assert answer.answer == "Alice, Bob"
    assert answer.retrieved_doc_ids[0] == "paper-exact"


def test_empty_results_and_blank_summary_are_safe(tmp_path):
    settings = load_settings(tmp_path)
    empty = answer_question("Unknown", settings, FakeIndex())
    blank = answer_question("Summarize", settings, FakeIndex(results=[_result(summary="")]))

    assert empty.answer == "Insufficient evidence in the indexed corpus."
    assert blank.answer == "Insufficient evidence in the indexed corpus."


def test_agent_mode_reports_provider(monkeypatch, tmp_path):
    monkeypatch.setattr("retrieval.agent.build_agent", lambda settings, index: object())
    monkeypatch.setattr(
        "retrieval.agent.run_agent_question",
        lambda agent, question: "Answer: Supported.\n\nEvidence:\n- paper_id: paper-1",
    )
    settings = load_settings(tmp_path)
    object.__setattr__(settings, "llm_provider", "gemini")

    answer = answer_question(
        "What is supported?",
        settings,
        FakeIndex(results=[_result()]),
        use_agent=True,
    )

    assert answer.provider == "gemini"
    assert "paper_id: paper-1" in answer.answer
