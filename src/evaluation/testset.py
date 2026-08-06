from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def build_test_set(df: pd.DataFrame, output_path: str | Path) -> list[dict[str, Any]]:
    """Tạo bộ evaluation set từ cleaned dataframe.

    Pseudo-code:
    1. Kiểm tra số lượng document tối thiểu.
    2. Chọn một số paper đại diện.
    3. Tạo nhiều loại câu hỏi: summary, authors, date, categories.
    4. Mỗi row có id, question_type, question, ground_truth, ground_truth_doc_ids.
    5. Ghi file JSON vào output_path.
    """
    if df is None or df.empty:
        raise ValueError("DataFrame is empty or None, cannot build evaluation test set.")

    test_set: list[dict[str, Any]] = []
    question_counter = 1

    # Take up to 10 representative papers or all if fewer
    sample_df = df.head(15)

    for _, row in sample_df.iterrows():
        paper_id = str(row.get("paper_id", "")).strip()
        title = str(row.get("title", "")).strip()
        summary = str(row.get("summary", "")).strip()

        authors = row.get("authors_joined") or row.get("authors", "")
        if isinstance(authors, list):
            authors = ", ".join(authors)
        authors = str(authors).strip()

        categories = row.get("categories_joined") or row.get("categories", "")
        if isinstance(categories, list):
            categories = ", ".join(categories)
        categories = str(categories).strip()

        published = str(row.get("published", "")).strip()

        if not paper_id or not title:
            continue

        # 1. Question type: summary
        if summary:
            test_set.append(
                {
                    "id": f"q_{question_counter:03d}",
                    "question_type": "summary",
                    "question": f"What is the summary or main finding of the paper '{title}'?",
                    "ground_truth": summary,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            question_counter += 1

        # 2. Question type: authors
        if authors:
            test_set.append(
                {
                    "id": f"q_{question_counter:03d}",
                    "question_type": "authors",
                    "question": f"Who are the authors of the paper '{title}'?",
                    "ground_truth": authors,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            question_counter += 1

        # 3. Question type: date
        if published:
            test_set.append(
                {
                    "id": f"q_{question_counter:03d}",
                    "question_type": "date",
                    "question": f"When was the paper '{title}' published?",
                    "ground_truth": published,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            question_counter += 1

        # 4. Question type: categories
        if categories:
            test_set.append(
                {
                    "id": f"q_{question_counter:03d}",
                    "question_type": "categories",
                    "question": f"What categories or subjects does the paper '{title}' belong to?",
                    "ground_truth": categories,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            question_counter += 1

    path_obj = Path(output_path)
    write_json(path_obj, test_set)
    return test_set


if __name__ == "__main__":
    from core.config import load_settings

    settings = load_settings()
    clean_csv = settings.paths.clean_csv
    clean_json = settings.paths.clean_json

    if clean_csv.exists():
        print(f"Loading cleaned dataset from {clean_csv}...")
        cleaned_df = pd.read_csv(clean_csv)
    elif clean_json.exists():
        print(f"Loading cleaned dataset from {clean_json}...")
        cleaned_df = pd.read_json(clean_json)
    else:
        raise FileNotFoundError(f"Cleaned dataset not found at {clean_csv} or {clean_json}. Run TV3 cleaning first!")

    result = build_test_set(cleaned_df, settings.paths.eval_testset)
    print(f"Successfully generated {len(result)} test questions at {settings.paths.eval_testset}!")


