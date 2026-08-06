from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Tạo bộ data quality checks.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null và unique.
    3. Check `title` not null.
    4. Check độ dài `summary`.
    5. Check freshness bằng `age_days`.
    6. Ghi kết quả vào `data/quality/`.
    """
    total_rows = len(df) if df is not None else 0

    if total_rows > 0:
        null_paper_ids = int(df["paper_id"].isna().sum()) if "paper_id" in df else total_rows
        duplicate_paper_ids = int(total_rows - df["paper_id"].nunique()) if "paper_id" in df else total_rows
        null_titles = int(df["title"].isna().sum()) if "title" in df else total_rows
        empty_titles = int((df["title"].astype(str).str.strip() == "").sum()) if "title" in df else total_rows
        null_summaries = int(df["summary"].isna().sum()) if "summary" in df else total_rows
        short_summaries = int((df["summary"].astype(str).str.strip().str.len() < 20).sum()) if "summary" in df else total_rows
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df else 0
    else:
        null_paper_ids = 0
        duplicate_paper_ids = 0
        null_titles = 0
        empty_titles = 0
        null_summaries = 0
        short_summaries = 0
        stale_rows = 0

    passed = (
        total_rows > 0
        and null_paper_ids == 0
        and duplicate_paper_ids == 0
        and null_titles == 0
        and empty_titles == 0
        and null_summaries == 0
        and short_summaries == 0
    )

    report = {
        "report_name": report_name,
        "total_rows": total_rows,
        "checks": {
            "row_count_valid": total_rows > 0,
            "paper_id_null_count": null_paper_ids,
            "paper_id_duplicate_count": duplicate_paper_ids,
            "paper_id_valid": null_paper_ids == 0 and duplicate_paper_ids == 0,
            "title_null_count": null_titles,
            "title_empty_count": empty_titles,
            "title_valid": null_titles == 0 and empty_titles == 0,
            "summary_null_count": null_summaries,
            "summary_short_count": short_summaries,
            "summary_valid": null_summaries == 0 and short_summaries == 0,
            "stale_rows_count": stale_rows,
        },
        "passed": passed,
    }

    output_file = settings.paths.quality_dir / f"{report_name}.json"
    write_json(output_file, report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tổng hợp freshness report.

    Pseudo-code:
    1. Tìm latest và oldest published date.
    2. Đếm số dòng stale.
    3. Tạo payload: latest_published, oldest_published, stale_rows, total_rows, is_fresh.
    4. Ghi JSON report.
    """
    total_rows = len(df) if df is not None else 0

    if total_rows > 0 and "published" in df:
        published_dates = df["published"].dropna().astype(str).tolist()
        latest_published = max(published_dates) if published_dates else "N/A"
        oldest_published = min(published_dates) if published_dates else "N/A"
    else:
        latest_published = "N/A"
        oldest_published = "N/A"

    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if (df is not None and "age_days" in df) else 0
    is_fresh = bool(total_rows > 0 and stale_rows == 0)

    payload = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": is_fresh,
    }

    path_obj = Path(report_path)
    write_json(path_obj, payload)
    return payload

