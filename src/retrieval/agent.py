from __future__ import annotations

from typing import Any

try:
    from langchain.agents import create_agent
    from langchain.tools import tool
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    create_agent = None
    tool = lambda fn: fn


from core.config import Settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.llm import build_llm


RAG_SYSTEM_PROMPT = """
You answer questions only from the currently selected scholarly-paper collection.

Rules:
1. Always use a retrieval tool before answering factual questions.
2. Use only facts present in the retrieved documents; do not add outside knowledge.
3. Never use or request documents from another collection.
4. Prefer evidence with higher similarity scores.
5. Cite every supporting paper with its paper_id.
6. If evidence is insufficient, say: "Insufficient evidence in the indexed corpus."

Return exactly this structure:
Answer: <concise answer>

Evidence:
- paper_id: <supporting paper id>
""".strip()


def _format_search_results(index: LocalEmbeddingIndex, query: str, top_k: int) -> str:
    results = index.search(query, top_k=top_k)
    if not results:
        return f"collection: {index.collection_name}\nNo relevant papers found."
    lines = []
    for result in results:
        lines.append(
            f"collection: {index.collection_name}\n"
            f"rank: {result.rank}\n"
            f"paper_id: {result.paper_id}\n"
            f"title: {result.title}\n"
            f"score: {result.score:.4f}\n"
            f"content: {result.content}"
        )
    return "\n\n".join(lines)


def build_agent(settings: Settings, index: LocalEmbeddingIndex):
    @tool
    def semantic_search_papers(query: str, top_k: int = 4) -> str:
        """Search the local paper corpus with embeddings and return the most relevant papers."""
        return _format_search_results(index, query=query, top_k=top_k)

    @tool
    def lookup_paper(paper_id_or_title: str) -> str:
        """Look up a paper by exact paper_id or normalized title in the selected collection."""
        record = index.lookup(paper_id_or_title)
        if not record:
            return f"collection: {index.collection_name}\nNo exact paper match found."
        return (
            f"collection: {index.collection_name}\n"
            f"paper_id: {record['paper_id']}\n"
            f"title: {record['title']}\n"
            f"content: {record['content']}"
        )

    llm = build_llm(settings=settings, temperature=0.0)
    return create_agent(
        model=llm,
        tools=[semantic_search_papers, lookup_paper],
        system_prompt=RAG_SYSTEM_PROMPT,
        name="paper_corpus_agent",
    )


def run_agent_question(agent: Any, question: str) -> str:
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    messages = result.get("messages", [])
    if not messages:
        return ""
    final_message = messages[-1]
    content = getattr(final_message, "content", str(final_message))
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(item.get("text", "")) if isinstance(item, dict) else str(item)
            for item in content
        ).strip()
    return str(content)
