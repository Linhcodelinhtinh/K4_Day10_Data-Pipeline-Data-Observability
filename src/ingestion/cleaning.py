from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

import pandas as pd

from ingestion.crossref import PaperRecord




def _clean_text(text: str) -> str:
    if not text:
        return ""
    # Remove HTML/XML tags
    cleaned = re.sub(r"<[^>]+>", " ", text)
    # Collapse multiple spaces and newlines
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records to dataframe ready for embedding.

    1. Remove invalid records (missing title or summary < 100 chars).
    2. Normalize text fields (remove HTML/XML tags, whitespace).
    3. Format authors and categories into comma-separated strings.
    4. Compute age_days relative to run_date and normalize published date.
    5. Build semantic column text_for_embedding.
    6. Drop duplicates and sort dataframe.
    """
    rows = []
    run_date_obj = run_date.date() if isinstance(run_date, datetime) else run_date

    for rec in records:
        title_clean = _clean_text(rec.title)
        summary_clean = _clean_text(rec.summary)

        # Filter out junk records: empty title or summary under 100 characters
        if not title_clean or len(summary_clean) < 100:
            continue

        # Authors & categories formatting
        authors = rec.authors if isinstance(rec.authors, list) else []
        authors_clean = [_clean_text(a) for a in authors if _clean_text(a)]
        authors_joined = ", ".join(authors_clean)

        categories = rec.categories if isinstance(rec.categories, list) else []
        categories_clean = [_clean_text(c) for c in categories if _clean_text(c)]
        categories_joined = ", ".join(categories_clean)

        # Parse published date and calculate age_days
        published_str = (rec.published or "").strip()
        pub_date = None
        if published_str:
            try:
                pub_date = datetime.strptime(published_str[:10], "%Y-%m-%d").date()
            except ValueError:
                pass

        if pub_date:
            published_fmt = pub_date.strftime("%Y-%m-%d")
            age_days = max(0, (run_date_obj - pub_date).days)
        else:
            published_fmt = published_str
            age_days = 0

        summary_chars = len(summary_clean)
        text_for_embedding = f"Title: {title_clean} | Authors: {authors_joined} | Summary: {summary_clean}"

        rows.append({
            "paper_id": rec.paper_id,
            "title": title_clean,
            "summary": summary_clean,
            "authors": authors_clean,
            "categories": categories_clean,
            "primary_category": rec.primary_category or (categories_clean[0] if categories_clean else ""),
            "published": published_fmt,
            "updated": rec.updated or published_fmt,
            "abs_url": rec.abs_url,
            "pdf_url": rec.pdf_url,
            "comment": rec.comment,
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "summary_chars": summary_chars,
            "age_days": age_days,
            "text_for_embedding": text_for_embedding,
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    # Drop duplicate records based on paper_id and title
    df = df.drop_duplicates(subset=["paper_id"]).reset_index(drop=True)
    df = df.drop_duplicates(subset=["title"]).reset_index(drop=True)

    # Sort by published date descending
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)

    return df


def repair_dataframe_from_snapshot(raw_records_path: str | Path, run_date: datetime) -> pd.DataFrame:
    """Repair dataset by re-loading raw JSON records snapshot and applying build_clean_dataframe.

    This recovers full clean state from saved raw artifacts without requiring live external API calls.
    """
    from ingestion.crossref import load_raw_records
    records = load_raw_records(Path(raw_records_path))
    return build_clean_dataframe(records, run_date)


