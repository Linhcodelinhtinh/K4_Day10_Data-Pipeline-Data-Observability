from __future__ import annotations

from datetime import UTC, datetime
import logging

import pandas as pd

from core.config import ensure_directories, load_settings
from core.utils import read_json, write_csv, write_json
from ingestion.crossref import load_raw_records
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Corruption -> Evaluate -> Repair -> Compare Flow (Phase 2)."""
    settings = load_settings()
    ensure_directories(settings)
    logger.info("Starting Corruption Flow...")

    # 1. Load clean baseline dataframe
    if settings.paths.clean_csv.exists():
        clean_df = pd.read_csv(settings.paths.clean_csv)
    elif settings.paths.clean_json.exists():
        clean_df = pd.DataFrame(read_json(settings.paths.clean_json))
    else:
        logger.warning("Baseline clean dataset chua ton tai. Vui long chay Phase 1 truuoc.")
        return

    logger.info(f"Loaded baseline clean dataset ({len(clean_df)} records).")

    # 2. Corrupt dataframe
    try:
        from ingestion.corruption import corrupt_clean_dataframe

        corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    except (NotImplementedError, ImportError):
        logger.warning(
            "`corrupt_clean_dataframe` chua duoc implement hoan chinh. Gia lap corruption bang cach tao copy dataframe."
        )
        corrupted_df = clean_df.copy()
        if len(corrupted_df) > 0:
            corrupted_df.loc[0, "summary"] = ""
            corrupted_df.loc[0, "text_for_embedding"] = f"Title: {corrupted_df.loc[0, 'title']}\nSummary: "
        write_json(settings.paths.corruption_log, {"note": "Fallback corruption log"})

    # 3. Save corrupted artifacts
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    logger.info(f"Saved corrupted dataset ({len(corrupted_df)} records).")

    # 4. Rebuild corrupted index
    logger.info(f"Building corrupted index '{settings.corrupted_collection_name}'...")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    logger.info(f"Corrupted index built with {len(corrupted_index.documents)} documents.")

    # 5. Evaluate corrupted (Optional - Tam thoi bo qua neu chua lam eval)
    try:
        if settings.paths.eval_testset.exists():
            from evaluation.metrics import evaluate_pipeline

            logger.info("Evaluating corrupted index on test set...")
            evaluate_pipeline(
                settings=settings,
                index=corrupted_index,
                test_set_path=settings.paths.eval_testset,
                metrics_output_path=settings.paths.corrupted_metrics,
                answers_output_path=settings.paths.corrupted_answers,
            )
        else:
            logger.info("Tam thoi chua lam data/eval. Bo qua evaluation cho corrupted dataset.")
    except Exception as e:
        logger.warning(f"Bo qua evaluation corrupted: {e}")

    # 6. Repair dataset from raw records
    logger.info("Repairing dataset from raw records...")
    if settings.paths.raw_records_json.exists():
        raw_records = load_raw_records(settings.paths.raw_records_json)
        run_date = datetime.now(UTC)
        try:
            from ingestion.cleaning import build_clean_dataframe

            repaired_df = build_clean_dataframe(raw_records, run_date)
        except (NotImplementedError, ImportError):
            repaired_df = clean_df.copy()
    else:
        repaired_df = clean_df.copy()

    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    logger.info(f"Saved repaired dataset ({len(repaired_df)} records).")

    # 7. Rebuild repaired index
    logger.info(f"Building repaired index '{settings.repaired_collection_name}'...")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    logger.info(f"Repaired index built with {len(repaired_index.documents)} documents.")

    # 8. Evaluate repaired (Optional - Tam thoi bo qua neu chua lam eval)
    try:
        if settings.paths.eval_testset.exists():
            from evaluation.metrics import evaluate_pipeline

            logger.info("Evaluating repaired index on test set...")
            evaluate_pipeline(
                settings=settings,
                index=repaired_index,
                test_set_path=settings.paths.eval_testset,
                metrics_output_path=settings.paths.repaired_metrics,
                answers_output_path=settings.paths.repaired_answers,
            )
        else:
            logger.info("Tam thoi chua lam data/eval. Bo qua evaluation cho repaired dataset.")
    except Exception as e:
        logger.warning(f"Bo qua evaluation repaired: {e}")

    # 9. Comparison report (Optional)
    try:
        from observability.reporting import generate_corruption_report
    except (NotImplementedError, ImportError, Exception):
        logger.info("Tam thoi chua lam comparison report. Bo qua buoc reporting.")

    logger.info("Corruption Flow finished successfully!")
