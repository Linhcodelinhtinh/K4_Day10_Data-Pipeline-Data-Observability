# Data Corruption & Repair Comparison Report

## 1. Overview & Key Findings
This report presents a comparative evaluation of the RAG Pipeline across three data states:
- **Baseline:** High-quality, cleaned data.
- **Corrupted:** Data damaged intentionally (dropped latest records, blank summaries, added text noise, stale dates, duplicate rows).
- **Repaired:** Data restored from raw snapshots and re-cleaned.

## 2. Evaluation Metrics Comparison
| Metric | Baseline | Corrupted | Repaired | Change (Corrupted vs Baseline) | Change (Repaired vs Corrupted) |
|---|---|---|---|---|---|
| **Retrieval Hit Rate** | 1.0000 | 0.6667 | 1.0000 | -0.3333 | +0.3333 |
| **Mean Token F1** | 0.4257 | 0.2834 | 0.4257 | -0.1423 | +0.1423 |
| **Judge Accuracy** | 0.3556 | 0.2444 | 0.3556 | -0.1111 | +0.1111 |
| **Mean Judge Score (1-5)** | 2.38 | 1.93 | 2.38 | -0.44 | +0.44 |

## 3. Data Observability Comparison
| Indicator | Corrupted | Repaired |
|---|---|---|
| **Quality Check Passed** | FAIL | PASS |
| **Total Rows** | 23 | 24 |
| **Stale Rows** | 2 | 0 |
| **Freshness Status** | STALE | FRESH |

## 4. Conclusion
- **Data Quality Impact:** Data corruption severely degrades retrieval precision and LLM judge scores.
- **Observability Value:** Data quality and freshness checks reliably detect data anomalies before bad answers reach users.
- **Data Repair:** Restoring data from raw snapshots successfully recovers RAG pipeline performance to baseline levels.
