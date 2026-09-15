"""Contract and edge-case tests for the Phase 6 behavioral table."""

from __future__ import annotations

import json
import unittest

import pandas as pd

from src.relevance import (
    BEHAVIORAL_TABLE_PATH, EVENT_SUMMARY_PATH, METRICS_PATH, REPORT_PATH,
    UNIT_KEYS, build_behavioral_table,
)
from src.relevance_eda import (
    CANDIDATE_SCHEMES_PATH,
    COMPATIBILITY_PATH,
    DWELL_DISTRIBUTION_PATH,
    EDA_FIGURE_PATH,
    EDA_METRICS_PATH,
    EDA_REPORT_PATH,
    POSITION_PATH,
    REPEATABILITY_PATH,
    SESSION_PATH,
    SLICE_PATH,
    THRESHOLD_SENSITIVITY_PATH,
    wilson_interval,
)
from src.relevance_bias_eda import (
    ASSOCIATION_PATH,
    BIAS_FIGURE_PATH,
    BIAS_METRICS_PATH,
    BIAS_REPORT_PATH,
    CONTENT_EXPOSURE_PATH,
    DOCTOR_PROPENSITY_PATH,
    JUDGMENT_COVERAGE_PATH,
    REPRESENTATION_PATH,
    SESSION_LENGTH_PATH,
    TEMPORAL_PATH,
    TIMESTAMP_TIES_PATH,
)


class BehavioralTableArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.table = pd.read_csv(BEHAVIORAL_TABLE_PATH)
        cls.metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    def test_target_grain_and_source_coverage(self) -> None:
        self.assertEqual(len(self.table), 7_190)
        self.assertFalse(self.table.duplicated(UNIT_KEYS).any())
        self.assertEqual(self.table["query_id"].nunique(), 500)
        self.assertEqual(self.table["content_id"].nunique(), 345)
        self.assertEqual(self.table["session_id"].nunique(), 813)
        self.assertTrue(self.table["impressed"].all())

    def test_behavior_is_left_joined_and_not_labeled_as_relevance(self) -> None:
        self.assertEqual(int(self.table["has_engagement"].sum()), 1_500)
        self.assertEqual(int((~self.table["has_engagement"]).sum()), 5_690)
        self.assertEqual(int(self.table["behavioral_event_count"].sum()), 1_500)
        self.assertFalse(any("relevance" in column for column in self.table.columns))
        self.assertFalse(self.metrics["relevance_labels_assigned"])

    def test_event_flags_match_source_counts(self) -> None:
        expected = {"clicked": 944, "scroll_deep": 436, "save_bookmark": 91, "return_visit": 29}
        for column, count in expected.items():
            self.assertEqual(int(self.table[column].sum()), count)
        self.assertEqual(int(self.table["dwell_time"].sum()), 95_140)

    def test_serving_order_and_event_timing_are_consistent(self) -> None:
        group_keys = ["session_id", "query_id"]
        grouped = self.table.groupby(group_keys)["inferred_rank"]
        self.assertTrue(grouped.min().eq(1).all())
        self.assertTrue(grouped.max().eq(grouped.size()).all())
        engaged = self.table[self.table["has_engagement"]].copy()
        served = pd.to_datetime(engaged["timestamp"])
        first_event = pd.to_datetime(engaged["first_event_timestamp"])
        self.assertTrue(first_event.ge(served).all())

    def test_query_and_content_features_are_present(self) -> None:
        expected = {
            "query_intent", "query_disease", "query_molecule", "query_drug_class",
            "query_therapeutic_area", "query_age_group", "query_year",
            "query_renal_function_group", "content_disease", "content_molecule",
            "content_drug_class", "content_therapeutic_area", "content_type",
            "content_publication_year",
        }
        self.assertTrue(expected.issubset(self.table.columns))
        self.assertFalse(self.table["query_intent"].isna().any())
        self.assertFalse(self.table["content_type"].isna().any())

    def test_diagnostics_and_reports_exist(self) -> None:
        self.assertEqual(self.metrics["orphan_behavioral_signals"], 0)
        self.assertEqual(self.metrics["doctor_id_mismatches"], 0)
        self.assertEqual(self.metrics["negative_event_latency"], 0)
        self.assertTrue(EVENT_SUMMARY_PATH.exists())
        self.assertTrue(REPORT_PATH.exists())


class BehavioralTableAggregationTests(unittest.TestCase):
    def test_multiple_events_aggregate_without_row_multiplication(self) -> None:
        query = pd.DataFrame([{
            "query_id": "Q1",
            **{column: "value" for column in (
                "query_text", "language", "disease_entity", "icd10_code",
                "molecule_entity", "atc_code", "drug_class_entity", "atc_class",
                "therapeutic_area", "age_group", "pregnancy_status", "route",
                "renal_function_group", "intent", "intent_top_level", "intent_subtype",
                "label_confidence", "label_source",
            )},
            "year": 2025, "recency_flag": False, "dose_context_flag": False,
            "hepatic_impairment_flag": False, "comparison_flag": False,
            "negation_flag": False, "prior_treatment_failure_flag": False,
        }])
        content = pd.DataFrame([{
            "content_id": "C1",
            **{column: "value" for column in (
                "title", "content_type", "source_type", "language", "disease_entity",
                "icd10_code", "molecule_entity", "atc_code", "drug_class_entity",
                "atc_class", "therapeutic_area",
            )},
            "publication_year": 2025, "word_count": 100,
        }])
        impressions = pd.DataFrame([{
            "impression_id": "I1", "session_id": "S1", "doctor_id": "D1",
            "query_id": "Q1", "content_id": "C1",
            "timestamp_served": pd.Timestamp("2025-01-01 00:00:00"),
        }])
        signals = pd.DataFrame([
            {
                "signal_id": "B1", "session_id": "S1", "doctor_id": "D1",
                "query_id": "Q1", "content_id": "C1", "event_type": "click",
                "event_timestamp": pd.Timestamp("2025-01-01 00:00:01"), "dwell_seconds": 5,
            },
            {
                "signal_id": "B2", "session_id": "S1", "doctor_id": "D1",
                "query_id": "Q1", "content_id": "C1", "event_type": "scroll_deep",
                "event_timestamp": pd.Timestamp("2025-01-01 00:00:02"), "dwell_seconds": 30,
            },
        ])
        table, _ = build_behavioral_table(query, content, impressions, signals)
        self.assertEqual(len(table), 1)
        self.assertEqual(int(table.loc[0, "behavioral_event_count"]), 2)
        self.assertEqual(int(table.loc[0, "dwell_time"]), 35)
        self.assertTrue(bool(table.loc[0, "clicked"]))
        self.assertTrue(bool(table.loc[0, "scroll_deep"]))


class RelevanceEdaArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.metrics = json.loads(EDA_METRICS_PATH.read_text(encoding="utf-8"))
        cls.schemes = pd.read_csv(CANDIDATE_SCHEMES_PATH)

    def test_eda_captures_terminal_event_semantics(self) -> None:
        self.assertTrue(self.metrics["event_types_mutually_exclusive"])
        self.assertEqual(self.metrics["rows_with_multiple_event_types"], 0)
        self.assertEqual(self.metrics["click_zero_dwell_rows"], 66)
        self.assertEqual(self.metrics["scroll_dwell_min"], 61)

    def test_eda_quantifies_bias_and_positive_coverage(self) -> None:
        self.assertEqual(self.metrics["sessions_without_engagement"], 150)
        self.assertEqual(self.metrics["queries_without_engagement"], 150)
        self.assertEqual(self.metrics["repeated_query_content_pairs"], 150)
        self.assertEqual(self.metrics["mixed_repeat_pairs"], 49)
        self.assertGreater(self.metrics["rank1_absolute_lift"], 0)

    def test_candidate_schemes_are_sensitivity_only_and_complete(self) -> None:
        self.assertFalse(self.metrics["candidate_grades_written_to_behavioral_table"])
        self.assertEqual(self.schemes["scheme"].nunique(), 3)
        self.assertTrue(self.schemes.groupby("scheme")["rows"].sum().eq(7_190).all())
        self.assertEqual(set(self.schemes["grade"]), {0, 1, 2, 3})

    def test_all_eda_artifacts_exist_and_are_populated(self) -> None:
        for path in (
            DWELL_DISTRIBUTION_PATH,
            THRESHOLD_SENSITIVITY_PATH,
            POSITION_PATH,
            SLICE_PATH,
            SESSION_PATH,
            REPEATABILITY_PATH,
            COMPATIBILITY_PATH,
        ):
            self.assertTrue(path.exists())
            self.assertGreater(len(pd.read_csv(path)), 0)
        self.assertTrue(EDA_REPORT_PATH.exists())
        self.assertTrue(EDA_FIGURE_PATH.exists())

    def test_wilson_interval_contains_observed_rate(self) -> None:
        lower, upper = wilson_interval(20, 100)
        self.assertLess(lower, 0.2)
        self.assertGreater(upper, 0.2)


class RelevanceBiasEdaArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.metrics = json.loads(BIAS_METRICS_PATH.read_text(encoding="utf-8"))

    def test_judgment_pool_is_explicitly_incomplete(self) -> None:
        self.assertEqual(self.metrics["possible_query_content_pairs"], 172_500)
        self.assertEqual(self.metrics["observed_query_content_pairs"], 7_037)
        self.assertAlmostEqual(self.metrics["global_judgment_coverage"], 0.0407942029)
        self.assertFalse(self.metrics["causal_claims_supported"])

    def test_outcome_conditioned_opportunity_is_detected(self) -> None:
        self.assertEqual(self.metrics["five_result_sessions"], 21)
        self.assertEqual(self.metrics["five_result_session_any_engagement_rate"], 0.0)
        self.assertEqual(
            self.metrics["eleven_twelve_result_session_any_engagement_rate"], 1.0
        )
        self.assertEqual(self.metrics["no_positive_queries_with_multiple_sessions"], 0)

    def test_propensity_and_measurement_bias_are_quantified(self) -> None:
        self.assertGreater(self.metrics["doctor_cramers_v"], 0.20)
        self.assertGreater(self.metrics["content_exposure_engagement_spearman"], 0.60)
        self.assertGreater(self.metrics["timestamp_tied_impression_share"], 0.20)

    def test_bias_artifacts_exist_and_are_populated(self) -> None:
        for path in (
            JUDGMENT_COVERAGE_PATH,
            SESSION_LENGTH_PATH,
            DOCTOR_PROPENSITY_PATH,
            CONTENT_EXPOSURE_PATH,
            REPRESENTATION_PATH,
            TEMPORAL_PATH,
            ASSOCIATION_PATH,
            TIMESTAMP_TIES_PATH,
        ):
            self.assertTrue(path.exists())
            self.assertGreater(len(pd.read_csv(path)), 0)
        self.assertTrue(BIAS_REPORT_PATH.exists())
        self.assertTrue(BIAS_FIGURE_PATH.exists())


if __name__ == "__main__":
    unittest.main()
