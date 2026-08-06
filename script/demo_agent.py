from __future__ import annotations

from pathlib import Path
import sys

# Dam bao import duoc src module
root_dir = Path(__file__).resolve().parents[1]
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def main() -> None:
    settings = load_settings()

    # Load baseline vector store index
    manifest_path = settings.paths.embeddings_json
    if not manifest_path.exists():
        print(f"Index manifest not found at {manifest_path}. Please run `script/run_phase1.py` first!")
        return

    index = LocalEmbeddingIndex.load(settings, manifest_path)
    print(f"Successfully loaded Chroma collection '{index.collection_name}' ({len(index.documents)} documents).\n")

    # Sample questions to test
    sample_questions = [
        "What is SafeRAG?",
        "Who are the authors of the paper 'SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation'?",
        "What categories does the paper 'SafeRAG' belong to?",
    ]

    print("=" * 70)
    print("RAG AGENT & RETRIEVAL DEMO TEST")
    print("=" * 70)

    for i, question in enumerate(sample_questions, 1):
        print(f"\n[Test Question {i}]: {question}")
        res = answer_question(question, settings=settings, index=index, use_agent=False)

        print(f"  Answer: {res.answer}")
        print(f"  Retrieved Paper IDs: {res.retrieved_doc_ids}")
        print(f"  Retrieved Titles: {res.retrieved_titles[:2]}")
        print(f"  Response Time: {res.latency_ms:.2f} ms")

        print("-" * 70)


if __name__ == "__main__":
    main()
