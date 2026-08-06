from __future__ import annotations

from dataclasses import replace
import importlib
from types import SimpleNamespace

import pytest

from core.config import load_settings
import retrieval.agent as agent_module
import retrieval.llm as llm_module
from retrieval.index import SearchResult


class FakeIndex:
    collection_name = "papers-baseline"

    def search(self, query, top_k=4):
        return [
            SearchResult(
                paper_id="paper-1",
                title="Machine Learning Retrieval",
                score=0.95,
                content="Evidence from the selected collection.",
                metadata={"paper_id": "paper-1", "title": "Machine Learning Retrieval"},
                rank=1,
                distance=0.05,
            )
        ]

    def lookup(self, value):
        if value.casefold() not in {"paper-1", "machine learning retrieval"}:
            return None
        return {
            "paper_id": "paper-1",
            "title": "Machine Learning Retrieval",
            "content": "Evidence from the selected collection.",
        }


def test_agent_tools_are_bound_to_selected_collection(monkeypatch, tmp_path):
    captured = {}

    monkeypatch.setattr(agent_module, "build_llm", lambda **kwargs: object())

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return "agent"

    monkeypatch.setattr(agent_module, "create_agent", fake_create_agent)

    result = agent_module.build_agent(load_settings(tmp_path), FakeIndex())
    search_output = captured["tools"][0].invoke({"query": "machine learning", "top_k": 1})
    lookup_output = captured["tools"][1].invoke({"paper_id_or_title": "paper-1"})

    assert result == "agent"
    assert "collection: papers-baseline" in search_output
    assert "paper_id: paper-1" in search_output
    assert "collection: papers-baseline" in lookup_output
    assert "Cite every supporting paper" in captured["system_prompt"]


def test_missing_gemini_key_has_clear_error(tmp_path):
    settings = replace(
        load_settings(tmp_path),
        llm_provider="gemini",
        google_api_key=None,
    )

    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY is required"):
        llm_module.build_llm(settings)


@pytest.mark.parametrize(
    ("provider", "credential_updates", "module_name", "constructor_name"),
    [
        (
            "gemini",
            {"google_api_key": "test"},
            "langchain_google_genai",
            "ChatGoogleGenerativeAI",
        ),
        ("openai", {"openai_api_key": "test"}, "langchain_openai", "ChatOpenAI"),
        (
            "anthropic",
            {"anthropic_api_key": "test"},
            "langchain_anthropic",
            "ChatAnthropic",
        ),
        (
            "openrouter",
            {"openrouter_api_key": "test"},
            "langchain_openai",
            "ChatOpenAI",
        ),
        ("ollama", {}, "langchain_ollama", "ChatOllama"),
        (
            "custom",
            {"custom_llm_base_url": "http://localhost:9999/v1"},
            "langchain_openai",
            "ChatOpenAI",
        ),
    ],
)
def test_all_provider_mappings(
    monkeypatch,
    tmp_path,
    provider,
    credential_updates,
    module_name,
    constructor_name,
):
    calls = []

    def fake_constructor(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(provider=provider)

    monkeypatch.setattr(importlib.import_module(module_name), constructor_name, fake_constructor)
    settings = replace(
        load_settings(tmp_path),
        llm_provider=provider,
        **credential_updates,
    )

    model = llm_module.build_llm(
        settings,
        temperature=0.1,
        max_tokens=123,
        timeout_seconds=7,
    )

    assert model.provider == provider
    assert calls and calls[0]


def test_generate_uses_common_facade(monkeypatch, tmp_path):
    settings = replace(load_settings(tmp_path), llm_provider="ollama")

    class FakeLLM:
        def invoke(self, messages):
            assert messages[-1].content == "Question"
            return SimpleNamespace(content="Answer")

    monkeypatch.setattr(llm_module, "build_llm", lambda *args, **kwargs: FakeLLM())

    assert llm_module.generate(settings, "Question", system_prompt="Use evidence") == "Answer"
