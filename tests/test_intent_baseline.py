"""Contract tests for the Phase 4 intent-classification baseline."""

from __future__ import annotations

import json
import unittest

import joblib
import pandas as pd

from src.intent import INTENT_NAMES
from src.intent_baseline import (
    CLASS_CHECKS_PATH,
    CONFUSION_FIGURE_PATH,
    CONFUSION_MATRIX_PATH,
    CV_PREDICTIONS_PATH,
    FOLD_METRICS_PATH,
    GROUPED_SENSITIVITY_PATH,
    METRICS_PATH,
    MODEL_PATH,
    PER_CLASS_METRICS_PATH,
    TOP_LEVEL_PER_CLASS_PATH,
)


class IntentBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        cls.predictions = pd.read_csv(CV_PREDICTIONS_PATH)
        cls.fold_metrics = pd.read_csv(FOLD_METRICS_PATH)
        cls.per_class = pd.read_csv(PER_CLASS_METRICS_PATH)
        cls.class_checks = pd.read_csv(CLASS_CHECKS_PATH)

    def test_retained_weak_label_oof_predictions_are_complete(self) -> None:
        self.assertEqual(len(self.predictions), 362)
        self.assertEqual(self.predictions["query_id"].nunique(), 362)
        self.assertEqual(self.metrics["n_excluded_three_way_disagreements"], 138)
        self.assertEqual(
            self.metrics["included_signal_agreement_counts"],
            {
                "unanimous": 151,
                "two_signal_including_rule": 127,
                "prototype_cluster_against_rule": 84,
            },
        )
        self.assertFalse(self.predictions["true_intent"].isna().any())
        self.assertFalse(self.predictions["predicted_intent"].isna().any())

    def test_primary_cv_documents_template_reuse_and_sensitivity_has_no_leakage(self) -> None:
        self.assertGreater(int(self.predictions.groupby("template_id")["fold"].nunique().max()), 1)
        self.assertTrue(self.fold_metrics["template_overlap"].gt(0).all())
        self.assertEqual(
            len(self.metrics["cv_design"]["train_test_template_overlap_each_fold"]), 5
        )
        grouped = pd.read_csv(GROUPED_SENSITIVITY_PATH)
        self.assertEqual(int(grouped.groupby("template_id")["fold"].nunique().max()), 1)
        self.assertEqual(
            self.metrics["template_grouped_sensitivity"]["template_overlap_each_fold"],
            [0, 0],
        )
        self.assertEqual(
            self.metrics["template_grouped_sensitivity"]["excluded_classes"],
            ["Monitoring / Response / Risk Assessment"],
        )

    def test_every_fold_contains_every_subtype(self) -> None:
        counts = self.predictions.groupby("fold")["true_intent"].nunique()
        self.assertTrue(counts.eq(len(INTENT_NAMES)).all())
        self.assertEqual(set(self.predictions["predicted_intent"]), set(INTENT_NAMES))

    def test_required_metrics_are_reported(self) -> None:
        required = {"macro_f1", "macro_precision", "macro_recall", "weighted_f1", "accuracy"}
        self.assertEqual(set(self.metrics["out_of_fold_metrics"]), required)
        self.assertEqual(set(self.per_class["label"]), set(INTENT_NAMES))
        self.assertTrue({"precision", "recall", "f1", "support"}.issubset(self.per_class.columns))
        self.assertTrue(TOP_LEVEL_PER_CLASS_PATH.exists())
        self.assertTrue(CONFUSION_MATRIX_PATH.exists())
        self.assertTrue(CONFUSION_FIGURE_PATH.exists())

    def test_taxonomy_sanity_checks_flag_unlearnable_other(self) -> None:
        other = self.class_checks[self.class_checks["intent"].eq("Other / Ambiguous")].iloc[0]
        self.assertEqual(int(other["all_query_count"]), 0)
        self.assertFalse(bool(other["cv_evaluable"]))
        supported = self.class_checks[self.class_checks["intent"].isin(INTENT_NAMES)]
        self.assertTrue(supported["cv_evaluable"].all())
        self.assertGreaterEqual(int(supported["weak_label_count"].min()), 5)

    def test_saved_model_is_a_text_only_pipeline(self) -> None:
        model = joblib.load(MODEL_PATH)
        self.assertEqual(list(model.named_steps), ["tfidf", "classifier"])
        prediction = model.predict(["latest guideline for hypertension treatment"])
        self.assertEqual(len(prediction), 1)


if __name__ == "__main__":
    unittest.main()
