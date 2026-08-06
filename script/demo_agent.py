from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Dam bao import duoc src module
root_dir = Path(__file__).resolve().parents[1]
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def run_demo_for_index(index: LocalEmbeddingIndex, settings, questions: list[str], state_name: str) -> None:
    print("=" * 75)
    print(f"RAG AGENT & RETRIEVAL DEMO - STATE: [{state_name.upper()}] (Collection: {index.collection_name})")
    print(f"Total Indexed Documents: {len(index.documents)}")
    print("=" * 75)

    for i, question in enumerate(questions, 1):
        print(f"\n[Question {i}]: {question}")
        res = answer_question(question, settings=settings, index=index, use_agent=False)

        print(f"  Answer: {res.answer}")
        print(f"  Retrieved Doc IDs: {res.retrieved_doc_ids}")
        print(f"  Retrieved Titles: {res.retrieved_titles[:2]}")
        print(f"  Response Latency: {res.latency_ms:.2f} ms")
        print("-" * 75)


def run_comparison_demo(indices: dict[str, LocalEmbeddingIndex], settings, questions: list[str]) -> None:
    print("=" * 80)
    print("RAG AGENT 3-STATE COMPARISON DEMO (Baseline vs Corrupted vs Repaired)")
    print("=" * 80)

    for i, question in enumerate(questions, 1):
        print(f"\n[Question {i}]: {question}")
        print("-" * 80)
        for state_name, idx in indices.items():
            res = answer_question(question, settings=settings, index=idx, use_agent=False)
            print(f"  [{state_name.upper():<9}] Answer: {res.answer[:120]}...")
            print(f"               Docs  : {res.retrieved_doc_ids}")
        print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test RAG Agent and Retrieval on Baseline, Corrupted, or Repaired data.")
    parser.add_argument(
        "--state",
        "-s",
        choices=["baseline", "corrupted", "repaired", "all"],
        default="all",
        help="Target data state to run demo on (default: all for 3-state comparison)",
    )
    args = parser.parse_args()

    settings = load_settings()

    sample_questions = [
        "What is SafeRAG?",
        "Who are the authors of the paper 'SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation'?",
        "When was the paper 'SafeRAG' published?",
    ]

    state_manifests = {
        "baseline": settings.paths.embeddings_json,
        "corrupted": settings.paths.corrupted_embeddings_json,
        "repaired": settings.paths.repaired_embeddings_json,
    }

    if args.state in ["baseline", "corrupted", "repaired"]:
        manifest_path = state_manifests[args.state]
        if not manifest_path.exists():
            print(f"Manifest for state '{args.state}' not found at {manifest_path}.")
            print("Please run `script/run_phase1.py` or `script/run_corruption_flow.py` first!")
            return
        index = LocalEmbeddingIndex.load(settings, manifest_path)
        run_demo_for_index(index, settings, sample_questions, args.state)
    else:
        # State 'all': Compare across baseline, corrupted, and repaired
        loaded_indices: dict[str, LocalEmbeddingIndex] = {}
        for s_name, m_path in state_manifests.items():
            if m_path.exists():
                loaded_indices[s_name] = LocalEmbeddingIndex.load(settings, m_path)

        if not loaded_indices:
            print("No index manifests found. Please run `script/run_phase1.py` or `script/run_corruption_flow.py`!")
            return

        run_comparison_demo(loaded_indices, settings, sample_questions)


if __name__ == "__main__":
    main()
