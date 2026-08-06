import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.config import load_settings
from evaluation.testset import build_test_set
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report, generate_phase1_report


class TestTV5EvaluationAndObservability(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.project_root = Path(__file__).resolve().parents[1]
        self.settings = load_settings(self.project_root)

        # Sample valid cleaned DataFrame
        self.sample_df = pd.DataFrame(
            [
                {
                    "paper_id": "10.1000/paper1",
                    "title": "Agentic RAG Architecture Overview",
                    "summary": "This paper introduces agentic retrieval augmented generation for complex domain QA tasks.",
                    "authors": ["Alice Smith", "Bob Jones"],
                    "authors_joined": "Alice Smith, Bob Jones",
                    "categories": ["cs.AI", "cs.CL"],
                    "categories_joined": "cs.AI, cs.CL",
                    "published": "2026-01-15",
                    "age_days": 20,
                },
                {
                    "paper_id": "10.1000/paper2",
                    "title": "Data Observability in Machine Learning Pipelines",
                    "summary": "We study data quality checks, schema validation, and freshness monitoring for real-time AI systems.",
                    "authors": ["Charlie Brown"],
                    "authors_joined": "Charlie Brown",
                    "categories": ["cs.DB"],
                    "categories_joined": "cs.DB",
                    "published": "2026-02-01",
                    "age_days": 5,
                },
            ]
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_build_test_set_valid(self):
        output_file = self.temp_path / "test_set.json"
        test_set = build_test_set(self.sample_df, output_file)

        self.assertTrue(output_file.exists())
        self.assertIsInstance(test_set, list)
        self.assertGreater(len(test_set), 0)

        # Verify element structure
        first_item = test_set[0]
        self.assertIn("id", first_item)
        self.assertIn("question_type", first_item)
        self.assertIn("question", first_item)
        self.assertIn("ground_truth", first_item)
        self.assertIn("ground_truth_doc_ids", first_item)
        self.assertEqual(first_item["ground_truth_doc_ids"], ["10.1000/paper1"])

    def test_build_test_set_empty_df_raises(self):
        empty_df = pd.DataFrame()
        with self.assertRaises(ValueError):
            build_test_set(empty_df, self.temp_path / "empty.json")

    def test_run_data_quality_checks_passed(self):
        report = run_data_quality_checks(self.sample_df, self.settings, "test_baseline_quality")
        self.assertEqual(report["report_name"], "test_baseline_quality")
        self.assertEqual(report["total_rows"], 2)
        self.assertTrue(report["passed"])
        self.assertTrue(report["checks"]["paper_id_valid"])
        self.assertTrue(report["checks"]["title_valid"])
        self.assertTrue(report["checks"]["summary_valid"])

    def test_run_data_quality_checks_failed_due_to_null_and_dups(self):
        bad_df = pd.DataFrame(
            [
                {
                    "paper_id": "10.1000/paper1",
                    "title": "",  # Empty title
                    "summary": "Short",  # Too short summary
                    "age_days": 200,  # Stale
                },
                {
                    "paper_id": "10.1000/paper1",  # Duplicate paper_id
                    "title": "Paper 2",
                    "summary": "Valid summary content that is long enough.",
                    "age_days": 10,
                },
            ]
        )
        report = run_data_quality_checks(bad_df, self.settings, "test_corrupted_quality")
        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["paper_id_valid"])
        self.assertFalse(report["checks"]["title_valid"])
        self.assertFalse(report["checks"]["summary_valid"])

    def test_build_freshness_report(self):
        freshness_file = self.temp_path / "freshness.json"
        report = build_freshness_report(self.sample_df, self.settings, freshness_file)

        self.assertTrue(freshness_file.exists())
        self.assertEqual(report["total_rows"], 2)
        self.assertEqual(report["stale_rows"], 0)
        self.assertTrue(report["is_fresh"])
        self.assertEqual(report["latest_published"], "2026-02-01")
        self.assertEqual(report["oldest_published"], "2026-01-15")

    def test_generate_phase1_report(self):
        report_file = self.temp_path / "phase1_report.md"
        source_summary = {"source_api": "Crossref API", "raw_records_count": 2}
        metrics = {
            "samples": 8,
            "retrieval_hit_rate": 1.0,
            "mean_token_f1": 0.85,
            "judge_accuracy": 1.0,
            "mean_judge_score": 4.5,
        }
        quality = {"passed": True, "total_rows": 2, "checks": {"paper_id_valid": True, "title_valid": True, "summary_valid": True}}
        freshness = {"latest_published": "2026-02-01", "oldest_published": "2026-01-15", "stale_rows": 0, "is_fresh": True}

        generate_phase1_report(report_file, source_summary, metrics, quality, freshness)

        self.assertTrue(report_file.exists())
        content = report_file.read_text(encoding="utf-8")
        self.assertIn("# Phase 1 Baseline Report", content)
        self.assertIn("1.0000", content)
        self.assertIn("4.50 / 5.00", content)

    def test_generate_corruption_report(self):
        report_file = self.temp_path / "corruption_report.md"
        b_metrics = {"retrieval_hit_rate": 1.0, "mean_token_f1": 0.85, "judge_accuracy": 1.0, "mean_judge_score": 4.5}
        c_metrics = {"retrieval_hit_rate": 0.5, "mean_token_f1": 0.35, "judge_accuracy": 0.4, "mean_judge_score": 2.1}
        r_metrics = {"retrieval_hit_rate": 1.0, "mean_token_f1": 0.85, "judge_accuracy": 1.0, "mean_judge_score": 4.5}

        c_quality = {"passed": False, "total_rows": 2}
        r_quality = {"passed": True, "total_rows": 2}
        c_freshness = {"stale_rows": 1, "is_fresh": False}
        r_freshness = {"stale_rows": 0, "is_fresh": True}

        generate_corruption_report(
            report_file, b_metrics, c_metrics, r_metrics, c_quality, r_quality, c_freshness, r_freshness
        )

        self.assertTrue(report_file.exists())
        content = report_file.read_text(encoding="utf-8")
        self.assertIn("# Data Corruption & Repair Comparison Report", content)
        self.assertIn("-0.5000", content)  # Drop in hit rate
        self.assertIn("+0.5000", content)  # Recovery in hit rate


if __name__ == "__main__":
    unittest.main()
