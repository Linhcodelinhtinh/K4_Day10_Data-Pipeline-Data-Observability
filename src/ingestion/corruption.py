from __future__ import annotations

import json
from pathlib import Path
import random

import pandas as pd



def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: str | Path) -> pd.DataFrame:
    """Simulate extensive forms of data corruption on a cleaned DataFrame.

    Corruption operations:
    1. Drop latest records (~20%).
    2. Blank summary on ~10% of remaining records.
    3. Inject HTML/XML noise into summary on ~10% of records.
    4. Inject misleading/contradictory statements into summary (~10%).
    5. Truncate title on ~10% of records.
    6. Make published date stale (old date) on ~10% of records.
    7. Corrupt authors list (~10%).
    8. Nullify metadata fields (URL/category) (~10%).
    9. Corrupt paper_id/DOI format (~10%).
    10. Add duplicate rows (~15%).
    11. Rebuild text_for_embedding and summary_chars.
    12. Write corruption log to output_log_path.
    """
    if df.empty:
        return df.copy()

    # Fixed seed for deterministic corruption results
    random.seed(42)

    corrupted_df = df.copy()
    corruption_log: dict[str, list] = {
        "dropped_latest_records": [],
        "blank_summary_paper_ids": [],
        "noise_injected_paper_ids": [],
        "misleading_injected_paper_ids": [],
        "truncated_title_paper_ids": [],
        "stale_date_paper_ids": [],
        "corrupted_authors_paper_ids": [],
        "null_metadata_paper_ids": [],
        "corrupted_paper_ids": [],
        "duplicated_paper_ids": [],
    }

    # 1. Drop latest records (~20% of records)
    if "published" in corrupted_df.columns:
        corrupted_df = corrupted_df.sort_values(by="published", ascending=False).reset_index(drop=True)
    n_drop = max(1, int(len(corrupted_df) * 0.20))
    dropped_ids = list(corrupted_df.iloc[:n_drop]["paper_id"])
    corruption_log["dropped_latest_records"] = dropped_ids
    corrupted_df = corrupted_df.iloc[n_drop:].reset_index(drop=True)

    n_rows = len(corrupted_df)
    if n_rows == 0:
        return corrupted_df

    # Shuffle indices to distribute corruption
    indices = list(range(n_rows))
    random.shuffle(indices)

    batch = max(1, int(n_rows * 0.10))

    # 2. Blank summary (~10%)
    blank_idx = indices[:batch]
    for idx in blank_idx:
        corrupted_df.at[idx, "summary"] = ""
        corruption_log["blank_summary_paper_ids"].append(corrupted_df.at[idx, "paper_id"])

    # 3. Inject HTML noise into summary (~10%)
    noise_idx = indices[batch : 2 * batch]
    for idx in noise_idx:
        original = corrupted_df.at[idx, "summary"]
        corrupted_df.at[idx, "summary"] = f"<jats:p><jats:title>CORRUPTED_XML</jats:title><b>NOISE_GARBAGE_12345</b></jats:p> {original}"
        corruption_log["noise_injected_paper_ids"].append(corrupted_df.at[idx, "paper_id"])

    # 4. Inject misleading statement into summary (~10%)
    misleading_idx = indices[2 * batch : 3 * batch]
    for idx in misleading_idx:
        original = corrupted_df.at[idx, "summary"]
        corrupted_df.at[idx, "summary"] = f"[RETRACTED/INVALID STATEMENT]: All findings in this study were proven false and revoked. {original}"
        corruption_log["misleading_injected_paper_ids"].append(corrupted_df.at[idx, "paper_id"])

    # 5. Truncate title (~10%)
    trunc_idx = indices[3 * batch : 4 * batch]
    for idx in trunc_idx:
        orig_title = str(corrupted_df.at[idx, "title"])
        corrupted_df.at[idx, "title"] = orig_title[:15] if len(orig_title) > 15 else orig_title
        corruption_log["truncated_title_paper_ids"].append(corrupted_df.at[idx, "paper_id"])

    # 6. Make published date stale (~10%)
    stale_idx = indices[4 * batch : 5 * batch]
    for idx in stale_idx:
        corrupted_df.at[idx, "published"] = "2010-01-01"
        if "age_days" in corrupted_df.columns:
            corrupted_df.at[idx, "age_days"] = int(corrupted_df.at[idx, "age_days"]) + 3650
        corruption_log["stale_date_paper_ids"].append(corrupted_df.at[idx, "paper_id"])

    # 7. Corrupt authors list (~10%)
    author_idx = indices[5 * batch : 6 * batch]
    for idx in author_idx:
        corrupted_df.at[idx, "authors"] = ["Unknown Author", "Anonymous Bot"]
        corrupted_df.at[idx, "authors_joined"] = "Unknown Author, Anonymous Bot"
        corruption_log["corrupted_authors_paper_ids"].append(corrupted_df.at[idx, "paper_id"])

    # 8. Nullify metadata fields (~10%)
    null_idx = indices[6 * batch : 7 * batch]
    for idx in null_idx:
        corrupted_df.at[idx, "primary_category"] = ""
        corrupted_df.at[idx, "abs_url"] = ""
        corrupted_df.at[idx, "pdf_url"] = ""
        corruption_log["null_metadata_paper_ids"].append(corrupted_df.at[idx, "paper_id"])

    # 9. Corrupt paper_id format (~10%)
    paper_id_idx = indices[7 * batch : 8 * batch]
    for idx in paper_id_idx:
        orig_id = str(corrupted_df.at[idx, "paper_id"])
        corrupted_df.at[idx, "paper_id"] = f"INVALID_CORRUPTED_ID/{orig_id}"
        corruption_log["corrupted_paper_ids"].append(corrupted_df.at[idx, "paper_id"])

    # 10. Add duplicate rows (~15%)
    dup_count = max(1, int(n_rows * 0.15))
    dup_rows = corrupted_df.iloc[:dup_count].copy()
    corruption_log["duplicated_paper_ids"] = list(dup_rows["paper_id"])
    corrupted_df = pd.concat([corrupted_df, dup_rows], ignore_index=True)

    # 11. Rebuild text_for_embedding & summary_chars
    for idx in range(len(corrupted_df)):
        title = corrupted_df.at[idx, "title"]
        authors = corrupted_df.at[idx, "authors_joined"]
        summary = corrupted_df.at[idx, "summary"]
        corrupted_df.at[idx, "summary_chars"] = len(str(summary))
        corrupted_df.at[idx, "text_for_embedding"] = f"Title: {title} | Authors: {authors} | Summary: {summary}"

    # 12. Write log file
    log_path = Path(output_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(corruption_log, ensure_ascii=False, indent=2), encoding="utf-8")

    return corrupted_df


def corrupt_by_single_type(df: pd.DataFrame, corruption_type: str) -> tuple[pd.DataFrame, list[str]]:
    """Apply a SINGLE specific corruption type to a copy of the cleaned DataFrame.

    Supported types:
    - 'drop_latest': Drop ~20% newest records.
    - 'blank_summary': Clear summary on ~20% of records.
    - 'text_noise': Inject XML/HTML noise into summary on ~20% of records.
    - 'misleading_summary': Inject misleading statement into summary on ~20% of records.
    - 'truncate_title': Truncate title on ~20% of records.
    - 'stale_date': Set published date to '2010-01-01' on ~20% of records.
    - 'corrupt_authors': Overwrite authors with 'Unknown Author, Anonymous Bot' on ~20% of records.
    - 'null_metadata': Clear metadata URLs/category on ~20% of records.
    - 'corrupt_paper_id': Prefix paper_id with 'INVALID_CORRUPTED_ID/' on ~20% of records.
    - 'duplicate_rows': Duplicate ~20% of rows.
    """
    if df.empty:
        return df.copy(), []

    random.seed(42)
    corrupted_df = df.copy()
    affected_ids: list[str] = []

    if corruption_type == "drop_latest":
        if "published" in corrupted_df.columns:
            corrupted_df = corrupted_df.sort_values(by="published", ascending=False).reset_index(drop=True)
        n_drop = max(1, int(len(corrupted_df) * 0.20))
        affected_ids = list(corrupted_df.iloc[:n_drop]["paper_id"])
        corrupted_df = corrupted_df.iloc[n_drop:].reset_index(drop=True)

    elif corruption_type == "blank_summary":
        n_count = max(1, int(len(corrupted_df) * 0.20))
        indices = list(range(len(corrupted_df)))
        random.shuffle(indices)
        for idx in indices[:n_count]:
            corrupted_df.at[idx, "summary"] = ""
            affected_ids.append(str(corrupted_df.at[idx, "paper_id"]))

    elif corruption_type == "text_noise":
        n_count = max(1, int(len(corrupted_df) * 0.20))
        indices = list(range(len(corrupted_df)))
        random.shuffle(indices)
        for idx in indices[:n_count]:
            orig = corrupted_df.at[idx, "summary"]
            corrupted_df.at[idx, "summary"] = f"<jats:p><jats:title>CORRUPTED_XML</jats:title><b>NOISE_GARBAGE_12345</b></jats:p> {orig}"
            affected_ids.append(str(corrupted_df.at[idx, "paper_id"]))

    elif corruption_type == "misleading_summary":
        n_count = max(1, int(len(corrupted_df) * 0.20))
        indices = list(range(len(corrupted_df)))
        random.shuffle(indices)
        for idx in indices[:n_count]:
            orig = corrupted_df.at[idx, "summary"]
            corrupted_df.at[idx, "summary"] = f"[RETRACTED/INVALID STATEMENT]: All findings in this study were proven false. {orig}"
            affected_ids.append(str(corrupted_df.at[idx, "paper_id"]))

    elif corruption_type == "truncate_title":
        n_count = max(1, int(len(corrupted_df) * 0.20))
        indices = list(range(len(corrupted_df)))
        random.shuffle(indices)
        for idx in indices[:n_count]:
            title = str(corrupted_df.at[idx, "title"])
            corrupted_df.at[idx, "title"] = title[:15] if len(title) > 15 else title
            affected_ids.append(str(corrupted_df.at[idx, "paper_id"]))

    elif corruption_type == "stale_date":
        n_count = max(1, int(len(corrupted_df) * 0.20))
        indices = list(range(len(corrupted_df)))
        random.shuffle(indices)
        for idx in indices[:n_count]:
            corrupted_df.at[idx, "published"] = "2010-01-01"
            if "age_days" in corrupted_df.columns:
                corrupted_df.at[idx, "age_days"] = int(corrupted_df.at[idx, "age_days"]) + 3650
            affected_ids.append(str(corrupted_df.at[idx, "paper_id"]))

    elif corruption_type == "corrupt_authors":
        n_count = max(1, int(len(corrupted_df) * 0.20))
        indices = list(range(len(corrupted_df)))
        random.shuffle(indices)
        for idx in indices[:n_count]:
            corrupted_df.at[idx, "authors"] = ["Unknown Author", "Anonymous Bot"]
            corrupted_df.at[idx, "authors_joined"] = "Unknown Author, Anonymous Bot"
            affected_ids.append(str(corrupted_df.at[idx, "paper_id"]))

    elif corruption_type == "null_metadata":
        n_count = max(1, int(len(corrupted_df) * 0.20))
        indices = list(range(len(corrupted_df)))
        random.shuffle(indices)
        for idx in indices[:n_count]:
            corrupted_df.at[idx, "primary_category"] = ""
            corrupted_df.at[idx, "abs_url"] = ""
            corrupted_df.at[idx, "pdf_url"] = ""
            affected_ids.append(str(corrupted_df.at[idx, "paper_id"]))

    elif corruption_type == "corrupt_paper_id":
        n_count = max(1, int(len(corrupted_df) * 0.20))
        indices = list(range(len(corrupted_df)))
        random.shuffle(indices)
        for idx in indices[:n_count]:
            orig_id = str(corrupted_df.at[idx, "paper_id"])
            corrupted_df.at[idx, "paper_id"] = f"INVALID_CORRUPTED_ID/{orig_id}"
            affected_ids.append(str(corrupted_df.at[idx, "paper_id"]))

    elif corruption_type == "duplicate_rows":
        dup_count = max(1, int(len(corrupted_df) * 0.20))
        dup_rows = corrupted_df.iloc[:dup_count].copy()
        affected_ids = list(dup_rows["paper_id"])
        corrupted_df = pd.concat([corrupted_df, dup_rows], ignore_index=True)

    else:
        raise ValueError(f"Unknown corruption type: {corruption_type}")

    # Rebuild text_for_embedding & summary_chars
    for idx in range(len(corrupted_df)):
        title = corrupted_df.at[idx, "title"]
        authors = corrupted_df.at[idx, "authors_joined"]
        summary = corrupted_df.at[idx, "summary"]
        corrupted_df.at[idx, "summary_chars"] = len(str(summary))
        corrupted_df.at[idx, "text_for_embedding"] = f"Title: {title} | Authors: {authors} | Summary: {summary}"

    return corrupted_df, affected_ids


def generate_separated_corrupted_datasets(df: pd.DataFrame, output_dir: str | Path) -> dict[str, Path]:
    """Generate SEPARATE corrupted CSV/JSON files for EACH individual error type.

    Saves separate datasets to `output_dir`:
    - papers_corrupted_{type}.csv
    - papers_corrupted_{type}.json
    - corruption_log_{type}.json
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    corruption_types = [
        "drop_latest",
        "blank_summary",
        "text_noise",
        "misleading_summary",
        "truncate_title",
        "stale_date",
        "corrupt_authors",
        "null_metadata",
        "corrupt_paper_id",
        "duplicate_rows",
    ]

    generated_files: dict[str, Path] = {}

    for c_type in corruption_types:
        single_df, affected_ids = corrupt_by_single_type(df, c_type)

        csv_path = out_dir / f"papers_corrupted_{c_type}.csv"
        json_path = out_dir / f"papers_corrupted_{c_type}.json"
        log_path = out_dir / f"corruption_log_{c_type}.json"

        single_df.to_csv(csv_path, index=False, encoding="utf-8")
        single_df.to_json(json_path, orient="records", indent=2, force_ascii=False)

        log_data = {
            "corruption_type": c_type,
            "total_rows": len(single_df),
            "affected_count": len(affected_ids),
            "affected_paper_ids": affected_ids,
        }
        log_path.write_text(json.dumps(log_data, ensure_ascii=False, indent=2), encoding="utf-8")

        generated_files[f"{c_type}_csv"] = csv_path
        generated_files[f"{c_type}_json"] = json_path
        generated_files[f"{c_type}_log"] = log_path

    return generated_files



