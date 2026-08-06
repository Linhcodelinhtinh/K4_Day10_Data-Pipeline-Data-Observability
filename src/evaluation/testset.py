from __future__ import annotations

from typing import Any

import pandas as pd


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """TODO(student): tao bo evaluation set tu cleaned dataframe.

    Pseudo-code:
    1. Kiem tra so luong document toi thieu.
    2. Chon mot so paper dai dien.
    3. Tao nhieu loai cau hoi:
       - summary
       - authors
       - date
       - categories
    4. Moi row can co:
       - id
       - question_type
       - question
       - ground_truth
       - ground_truth_doc_ids
    5. Ghi file JSON vao output_path.
    """
    test_set: list[dict[str, Any]] = []
    question_counter = 1
   
    raise NotImplementedError("Student task: implement test set builder.")
