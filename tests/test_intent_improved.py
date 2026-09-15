"""Contract tests for Phase 5 intent-classification ablations."""

from __future__ import annotations

import json
import unittest

import joblib
import pandas as pd

from src.intent_improved import (
    CHANGES_PATH,
    COMPARISON_PATH,
    CONFUSION_FIGURE_PATH,
    CONFUSION_PAIRS_PATH,
    ERRORS_PATH,
    FUSION_CHANGES_PATH,
    MANUAL_REVIEW_PATH,
    METRICS_PATH,
    MODEL_PATH,
    PER_CLASS_PATH,
    PREDICTIONS_PATH,
    SLICE_METRICS_PATH,
    TOP_FEATURES_PATH,
    entity_feature_dict,
)


class IntentImprovedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        cls.comparison = pd.read_csv(COMPARISON_PATH)
        cls.predictions = pd.read_csv(PREDICTIONS_PATH)

    def test_all_required_ablation_protocols_exist(self) -> None:
        expected_experiments = {
            "T1-P0",
            "T1-B0",
            "T1-E1",
            "T1-E2",
            "T1-E3",
            "T1-E4",
        }
        self.assertEqual(set(self.comparison["experiment"]), expected_experiments)
        self.assertEqual(
            set(self.comparison["protocol"]), {"row_stratified", "template_grouped"}
        )
        self.assertEqual(len(self.comparison), 12)

    def test_phase4_baseline_is_reproduced_exactly(self) -> None:
        baseline = self.comparison[self.comparison["experiment"].eq("T1-B0")].set_index(
            "protocol"
        )
        self.assertAlmostEqual(
            float(baseline.loc["row_stratified", "macro_f1"]),
            0.9807645756436333,
        )
        self.assertAlmostEqual(
            float(baseline.loc["template_grouped", "macro_f1"]),
            0.509102690880679,
        )
        self.assertTrue(baseline["macro_f1_delta_vs_phase4"].eq(0).all())

    def test_every_experiment_predicts_the_same_protocol_rows(self) -> None:
        counts = self.predictions.groupby(["protocol", "experiment"])["query_id"].nunique()
        self.assertTrue(counts.loc["row_stratified"].eq(362).all())
        self.assertTrue(counts.loc["template_grouped"].eq(354).all())
        grouped = self.predictions[self.predictions["protocol"].eq("template_grouped")]
        self.assertTrue(grouped.groupby(["experiment", "query_id"])["fold"].nunique().eq(1).all())

    def test_selected_model_uses_unseen_template_primary_metric(self) -> None:
        self.assertEqual(self.metrics["selected_experiment"], "T1-E4")
        selected = self.comparison[
            self.comparison["protocol"].eq("template_grouped")
            & self.comparison["experiment"].eq("T1-E4")
        ].iloc[0]
        embedding_only = self.comparison[
            self.comparison["protocol"].eq("template_grouped")
            & self.comparison["experiment"].eq("T1-E3")
        ].iloc[0]
        self.assertGreater(float(selected["macro_f1"]), float(embedding_only["macro_f1"]))
        artifact = joblib.load(MODEL_PATH)
        self.assertEqual(artifact["experiment"], "T1-E4")
        self.assertIn("independently L2-normalized", artifact["block_normalization"])
        self.assertIn("384-dimensional", artifact["input_contract"])
        self.assertEqual(len(artifact["classifier"].classes_), 11)

    def test_entity_features_avoid_identity_shortcuts(self) -> None:
        row = pd.Series(
            {
                "disease_entity": "Hypertension",
                "molecule_entity": "Aspirin; Warfarin",
                "drug_class_entity": "Antiplatelet; Anticoagulant",
            }
        )
        features = entity_feature_dict(row)
        self.assertEqual(features["has::multiple_molecules"], 1.0)
        self.assertEqual(features["count::all_supplied_entities"], 5.0)
        self.assertFalse(any("hypertension" in name for name in features))
        self.assertFalse(any(name.startswith("value::") for name in features))

    def test_failure_analysis_outputs_are_populated(self) -> None:
        for path in (
            PER_CLASS_PATH,
            CHANGES_PATH,
            FUSION_CHANGES_PATH,
            ERRORS_PATH,
            CONFUSION_PAIRS_PATH,
            SLICE_METRICS_PATH,
            MANUAL_REVIEW_PATH,
            TOP_FEATURES_PATH,
        ):
            self.assertTrue(path.exists())
            self.assertGreater(len(pd.read_csv(path)), 0)
        review = pd.read_csv(MANUAL_REVIEW_PATH)
        self.assertFalse(review["manual_review_note"].isna().any())
        self.assertTrue(CONFUSION_FIGURE_PATH.exists())


if __name__ == "__main__":
    unittest.main()
