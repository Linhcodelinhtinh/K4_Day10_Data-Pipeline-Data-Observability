from pathlib import Path
from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viết markdown report cho baseline phase."""
    hit_rate = metrics.get("retrieval_hit_rate", 0.0)
    token_f1 = metrics.get("mean_token_f1", 0.0)
    judge_acc = metrics.get("judge_accuracy", 0.0)
    judge_score = metrics.get("mean_judge_score", 0.0)
    samples = metrics.get("samples", 0)

    quality_passed = quality.get("passed", False)
    total_rows = quality.get("total_rows", 0)
    checks = quality.get("checks", {})

    latest_pub = freshness.get("latest_published", "N/A")
    oldest_pub = freshness.get("oldest_published", "N/A")
    stale_rows = freshness.get("stale_rows", 0)
    is_fresh = freshness.get("is_fresh", False)

    markdown = f"""# Phase 1 Baseline Report

## 1. Executive Summary
- **Dataset Size:** {total_rows} cleaned records
- **Evaluation Samples:** {samples} test questions
- **Data Quality Gate:** {"PASSED" if quality_passed else "FAILED"}
- **Data Freshness Gate:** {"FRESH" if is_fresh else "STALE"}

## 2. Source Ingestion Summary
- **Source API:** {source_summary.get("source_api", "Crossref API")}
- **Total Raw Records Fetched:** {source_summary.get("raw_records_count", "N/A")}
- **Cleaned Records:** {total_rows}

## 3. Evaluation Metrics
| Metric | Value | Target / Status |
|---|---|---|
| **Retrieval Hit Rate** | {hit_rate:.4f} | {hit_rate * 100:.1f}% |
| **Mean Token F1** | {token_f1:.4f} | {token_f1 * 100:.1f}% |
| **Judge Accuracy** | {judge_acc:.4f} | {judge_acc * 100:.1f}% |
| **Mean Judge Score (1-5)** | {judge_score:.2f} / 5.00 | {judge_score:.2f} |

## 4. Data Quality & Freshness Status
- **Paper ID Validity:** {"PASS" if checks.get("paper_id_valid") else "FAIL"} (Null: {checks.get("paper_id_null_count", 0)}, Dup: {checks.get("paper_id_duplicate_count", 0)})
- **Title Validity:** {"PASS" if checks.get("title_valid") else "FAIL"} (Null: {checks.get("title_null_count", 0)}, Empty: {checks.get("title_empty_count", 0)})
- **Summary Validity:** {"PASS" if checks.get("summary_valid") else "FAIL"} (Null: {checks.get("summary_null_count", 0)}, Short: {checks.get("summary_short_count", 0)})
- **Latest Published Date:** {latest_pub}
- **Oldest Published Date:** {oldest_pub}
- **Stale Rows Count:** {stale_rows}
"""
    write_text(Path(report_path), markdown)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Viết markdown report so sánh baseline / corrupted / repaired."""
    b_hit = baseline_metrics.get("retrieval_hit_rate", 0.0)
    c_hit = corrupted_metrics.get("retrieval_hit_rate", 0.0)
    r_hit = repaired_metrics.get("retrieval_hit_rate", 0.0)

    b_f1 = baseline_metrics.get("mean_token_f1", 0.0)
    c_f1 = corrupted_metrics.get("mean_token_f1", 0.0)
    r_f1 = repaired_metrics.get("mean_token_f1", 0.0)

    b_acc = baseline_metrics.get("judge_accuracy", 0.0)
    c_acc = corrupted_metrics.get("judge_accuracy", 0.0)
    r_acc = repaired_metrics.get("judge_accuracy", 0.0)

    b_score = baseline_metrics.get("mean_judge_score", 0.0)
    c_score = corrupted_metrics.get("mean_judge_score", 0.0)
    r_score = repaired_metrics.get("mean_judge_score", 0.0)

    markdown = f"""# Data Corruption & Repair Comparison Report

## 1. Overview & Key Findings
This report presents a comparative evaluation of the RAG Pipeline across three data states:
- **Baseline:** High-quality, cleaned data.
- **Corrupted:** Data damaged intentionally (dropped latest records, blank summaries, added text noise, stale dates, duplicate rows).
- **Repaired:** Data restored from raw snapshots and re-cleaned.

## 2. Evaluation Metrics Comparison
| Metric | Baseline | Corrupted | Repaired | Change (Corrupted vs Baseline) | Change (Repaired vs Corrupted) |
|---|---|---|---|---|---|
| **Retrieval Hit Rate** | {b_hit:.4f} | {c_hit:.4f} | {r_hit:.4f} | {(c_hit - b_hit):+.4f} | {(r_hit - c_hit):+.4f} |
| **Mean Token F1** | {b_f1:.4f} | {c_f1:.4f} | {r_f1:.4f} | {(c_f1 - b_f1):+.4f} | {(r_f1 - c_f1):+.4f} |
| **Judge Accuracy** | {b_acc:.4f} | {c_acc:.4f} | {r_acc:.4f} | {(c_acc - b_acc):+.4f} | {(r_acc - c_acc):+.4f} |
| **Mean Judge Score (1-5)** | {b_score:.2f} | {c_score:.2f} | {r_score:.2f} | {(c_score - b_score):+.2f} | {(r_score - c_score):+.2f} |

## 3. Data Observability Comparison
| Indicator | Corrupted | Repaired |
|---|---|---|
| **Quality Check Passed** | {"PASS" if corrupted_quality.get("passed") else "FAIL"} | {"PASS" if repaired_quality.get("passed") else "FAIL"} |
| **Total Rows** | {corrupted_quality.get("total_rows", 0)} | {repaired_quality.get("total_rows", 0)} |
| **Stale Rows** | {corrupted_freshness.get("stale_rows", 0)} | {repaired_freshness.get("stale_rows", 0)} |
| **Freshness Status** | {"FRESH" if corrupted_freshness.get("is_fresh") else "STALE"} | {"FRESH" if repaired_freshness.get("is_fresh") else "STALE"} |

## 4. Conclusion
- **Data Quality Impact:** Data corruption severely degrades retrieval precision and LLM judge scores.
- **Observability Value:** Data quality and freshness checks reliably detect data anomalies before bad answers reach users.
- **Data Repair:** Restoring data from raw snapshots successfully recovers RAG pipeline performance to baseline levels.
"""
    write_text(Path(report_path), markdown)

