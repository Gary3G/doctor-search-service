"""Contracts for Phase 7.5 CLEAR-inspired structured compatibility."""

from __future__ import annotations

import json
import unittest

import pandas as pd

from src.structured_compatibility import (
    CLEAR_MAPPING_PATH,
    COMPATIBILITY_MATRIX_PATH,
    CONTENT_CONTEXT_PATH,
    EXAMPLES_PATH,
    FEATURE_DICTIONARY_PATH,
    FEATURE_SUMMARY_PATH,
    FIGURE_PATH,
    METRICS_PATH,
    OBSERVED_DIAGNOSTICS_PATH,
    REPORT_PATH,
    build_compatibility_matrix,
    normalized_values,
)


class StructuredCompatibilityUnitTests(unittest.TestCase):
    def test_semicolon_entities_are_normalized(self) -> None:
        self.assertEqual(
            normalized_values(" Warfarin ; APIXABAN "),
            frozenset({"warfarin", "apixaban"}),
        )

    def test_exact_hierarchical_conflict_and_context_are_distinct(self) -> None:
        query = pd.DataFrame([{
            "query_id": "Q1", "query_text": "apixaban dose in renal impairment",
            "language": "EN", "intent": "Dosing / Administration",
            "disease_entity": "Persistent Atrial Fibrillation", "icd10_code": "I48.0",
            "molecule_entity": "Apixaban", "atc_code": "B01AF02",
            "drug_class_entity": "Direct factor Xa inhibitors", "atc_class": "B01AF",
            "therapeutic_area": "Cardiology", "age_group": pd.NA,
            "pregnancy_status": pd.NA, "year": pd.NA, "recency_flag": False,
            "dose_context_flag": True, "route": pd.NA,
            "renal_function_group": "renal_impairment",
            "hepatic_impairment_flag": False, "comparison_flag": False,
            "negation_flag": False, "prior_treatment_failure_flag": False,
        }])
        content = pd.DataFrame([{
            "content_id": "C1", "title": "Renal dose adjustment for rivaroxaban",
            "content_type": "drug_profile", "source_type": "reference",
            "language": "EN", "publication_year": 2025, "word_count": 100,
            "disease_entity": "Atrial Fibrillation", "icd10_code": "I48",
            "molecule_entity": "Rivaroxaban", "atc_code": "B01AF01",
            "drug_class_entity": "Direct factor Xa inhibitors", "atc_class": "B01AF",
            "therapeutic_area": "Cardiology",
        }])
        row = build_compatibility_matrix(query, content).iloc[0]
        self.assertTrue(bool(row["disease_hierarchical_match"]))
        self.assertFalse(bool(row["molecule_match"]))
        self.assertTrue(bool(row["molecule_hierarchical_match"]))
        self.assertTrue(bool(row["molecule_conflict"]))
        self.assertTrue(bool(row["dose_context_match"]))
        self.assertTrue(bool(row["renal_context_match"]))
        self.assertGreater(float(row["structured_score"]), 0)


class StructuredCompatibilityArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = pd.read_csv(COMPATIBILITY_MATRIX_PATH)
        cls.metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    def test_full_corpus_cross_product_is_complete(self) -> None:
        self.assertEqual(len(self.matrix), 172_500)
        self.assertFalse(self.matrix.duplicated(["query_id", "content_id"]).any())
        self.assertEqual(self.matrix["query_id"].nunique(), 500)
        self.assertEqual(self.matrix["content_id"].nunique(), 345)

    def test_features_are_behavior_independent(self) -> None:
        forbidden_fragments = (
            "relevance", "clicked", "scroll", "bookmark", "return_visit",
            "doctor_id", "session_id", "inferred_rank", "dwell",
        )
        self.assertFalse(
            any(fragment in column for column in self.matrix.columns for fragment in forbidden_fragments)
        )
        self.assertFalse(self.metrics["behavior_used_to_construct_features"])
        self.assertFalse(self.metrics["behavior_used_to_choose_weights"])

    def test_required_features_and_score_contract(self) -> None:
        required = {
            "disease_match", "molecule_match", "drug_class_match",
            "therapeutic_area_match", "entity_coverage",
            "entity_augmented_coverage", "molecule_hierarchical_match",
            "entity_conflict_rate", "age_group_match", "pregnancy_match",
            "year_match", "recency_match", "dose_context_match", "route_match",
            "renal_context_match", "hepatic_context_match",
            "comparison_context_match", "context_coverage",
            "context_conflict_rate", "intent_content_type_match",
            "structured_score", "structured_conflict_rate",
        }
        self.assertTrue(required.issubset(self.matrix.columns))
        self.assertTrue(self.matrix["structured_score"].between(0, 1).all())
        self.assertTrue(self.matrix["structured_conflict_rate"].between(0, 1).all())

    def test_clear_adaptation_is_explicitly_bounded(self) -> None:
        mapping = pd.read_csv(CLEAR_MAPPING_PATH)
        self.assertGreaterEqual(len(mapping), 5)
        self.assertFalse(self.metrics["original_clear_task_reproduced"])
        report = REPORT_PATH.read_text(encoding="utf-8")
        self.assertIn("methodological pattern", report)
        self.assertIn("No neural NER", report)
        self.assertIn("Missing title context", report)

    def test_all_phase75_artifacts_exist(self) -> None:
        for path in (
            CONTENT_CONTEXT_PATH, FEATURE_DICTIONARY_PATH, FEATURE_SUMMARY_PATH,
            CLEAR_MAPPING_PATH, OBSERVED_DIAGNOSTICS_PATH, EXAMPLES_PATH,
        ):
            self.assertTrue(path.exists())
            self.assertGreater(len(pd.read_csv(path)), 0)
        self.assertTrue(REPORT_PATH.exists())
        self.assertTrue(FIGURE_PATH.exists())


if __name__ == "__main__":
    unittest.main()
