from __future__ import annotations

from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """TODO(student): clean raw records thanh dataframe san sang de embed.

    Pseudo-code:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    # Normalize title, summary, authors, categories.
    titles = [r.title for r in records]
    summaries = [r.summary for r in records]
    authors = [r.authors for r in records]
    categories = [r.categories for r in records]
    published_dates = [r.published_date for r in records]
    updated_dates = [r.updated_date for r in records]

    # Parse published/updated date.
    published = pd.to_datetime(published_dates)
    updated = pd.to_datetime(updated_dates)

    # Tinh age_days.
    age_days = (run_date - published.dt.date).dt.days

    # Tao cot helper:
    # - authors_joined
    # - categories_joined
    # - summary_chars
    # - text_for_embedding
    authors_joined = [", ".join(a) for a in authors]
    categories_joined = [", ".join(c) for c in categories]
    summary_chars = [len(s) for s in summaries]
    text_for_embedding = [f"{t}\n\n{s}" for t, s in zip(titles, summaries)]

    # Drop duplicates va filter row xau.
    df = pd.DataFrame(
        {
            "title": titles,
            "summary": summaries,
            "authors": authors,
            "categories": categories,
            "published": published,
            "updated": updated,
            "age_days": age_days,
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "summary_chars": summary_chars,
            "text_for_embedding": text_for_embedding,
        }
    )
    df.drop_duplicates(subset=["title"], keep="first", inplace=True)
    df = df[df["summary_chars"] > 100]

    # Sort dataframe va return.
    df.sort_values(by="published", ascending=False, inplace=True)
    return df


