from __future__ import annotations

from datetime import UTC, datetime
import logging

import pandas as pd

from core.config import ensure_directories, load_settings
from core.utils import write_csv, write_json
from ingestion.crossref import fetch_source_records, load_raw_records
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Baseline pipeline end-to-end (Phase 1)."""
    settings = load_settings()
    ensure_directories(settings)
    logger.info(f"Loaded settings for project: {settings.paths.project_dir}")

    # 1. Load hoac fetch raw records (Uu tien dung file raw da co)
    if settings.paths.raw_records_json.exists() and not settings.refresh_source:
        logger.info(f"Loading existing raw records from {settings.paths.raw_records_json}")
        raw_records = load_raw_records(settings.paths.raw_records_json)
    else:
        logger.info("Fetching raw records from Crossref API...")
        try:
            raw_records = fetch_source_records(settings)
        except Exception as e:
            if settings.paths.raw_records_json.exists():
                logger.warning(f"Fetch failed ({e}). Fallback to existing raw records.")
                raw_records = load_raw_records(settings.paths.raw_records_json)
            else:
                raise

    logger.info(f"Loaded {len(raw_records)} raw records.")

    # 2. Clean data
    run_date = datetime.now(UTC)
    try:
        from ingestion.cleaning import build_clean_dataframe

        clean_df = build_clean_dataframe(raw_records, run_date)
        logger.info(f"Cleaned dataframe created with {len(clean_df)} records.")
    except (NotImplementedError, ImportError):
        logger.warning(
            "`build_clean_dataframe` chua duoc implement hoan chinh. Su dung fallback dataframe tu raw records."
        )
        rows = []
        for r in raw_records:
            rows.append(
                {
                    "paper_id": r.paper_id,
                    "title": r.title,
                    "summary": r.summary,
                    "authors_joined": ", ".join(r.authors),
                    "categories_joined": ", ".join(r.categories),
                    "published": r.published,
                    "updated": r.updated,
                    "abs_url": r.abs_url,
                    "pdf_url": r.pdf_url,
                    "text_for_embedding": f"Title: {r.title}\nSummary: {r.summary}",
                    "age_days": 0,
                    "summary_chars": len(r.summary),
                }
            )
        clean_df = pd.DataFrame(rows)

    # 3. Save clean CSV/JSON
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))
    logger.info(f"Saved clean dataset to {settings.paths.clean_csv} and {settings.paths.clean_json}")

    # 4. Build Chroma index
    logger.info(f"Building ChromaDB index '{settings.baseline_collection_name}'...")
    index = LocalEmbeddingIndex.build(
        clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    logger.info(f"Index built successfully with {len(index.documents)} documents.")

    # 5. Evaluation (Optional - Tam thoi bo qua neu chua lam eval)
    try:
        if settings.paths.eval_testset.exists():
            from evaluation.metrics import evaluate_pipeline

            logger.info("Evaluating baseline pipeline on test set...")
            evaluate_pipeline(
                settings=settings,
                index=index,
                test_set_path=settings.paths.eval_testset,
                metrics_output_path=settings.paths.baseline_metrics,
                answers_output_path=settings.paths.baseline_answers,
            )
        else:
            logger.info("Tam thoi chua lam data/eval. Bo qua buoc evaluation.")
    except Exception as e:
        logger.warning(f"Bo qua evaluation: {e}")

    # 6. Observability & Reporting (Optional - Tam thoi bo qua neu chua làm)
    try:
        from observability.quality import build_freshness_report, run_data_quality_checks

        run_data_quality_checks(clean_df, settings, "quality_baseline")
        build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    except (NotImplementedError, ImportError, Exception):
        logger.info("Tam thoi chua lam data observability. Bo qua buoc quality checks.")

    logger.info("Phase 1 baseline pipeline finished successfully!")
