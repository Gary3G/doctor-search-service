"""Contract tests for the Phase 3 labeling deliverables."""

from __future__ import annotations

import json
import unittest

import pandas as pd

from src.intent import (
    GOLD_PATH,
    GOLD_SIZE,
    GUIDELINES_PATH,
    INTENT_NAMES,
    KAPPA_PATH,
    LABELED_QUERIES_PATH,
    METRICS_PATH,
    OTHER_INTENT,
    PILOT_PATH,
    PILOT_SIZE,
    QUALITY_AUDIT_PATH,
    ROOT_LABELED_QUERIES_PATH,
    annotate_intent,
)


class IntentLabelingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.labeled = pd.read_csv(LABELED_QUERIES_PATH)
        cls.pilot = pd.read_csv(PILOT_PATH)
        cls.gold = pd.read_csv(GOLD_PATH)
        cls.audit = pd.read_csv(QUALITY_AUDIT_PATH)
        cls.metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    def test_final_file_preserves_all_queries_and_required_labels(self) -> None:
        self.assertEqual(len(self.labeled), 500)
        self.assertEqual(self.labeled["query_id"].nunique(), 500)
        self.assertFalse(self.labeled["intent"].isna().any())
        required = {
            "intent",
            "intent_top_level",
            "intent_subtype",
            "label_confidence",
            "label_source",
            "review_flag",
            "gold_set_membership",
            "rule_intent_signal",
            "prototype_intent_signal",
            "cluster_intent_signal",
            "signal_agreement",
        }
        self.assertTrue(required.issubset(self.labeled.columns))
        self.assertTrue(ROOT_LABELED_QUERIES_PATH.exists())

    def test_review_sample_sizes_and_nesting(self) -> None:
        self.assertEqual(len(self.pilot), PILOT_SIZE)
        self.assertEqual(len(self.gold), GOLD_SIZE)
        self.assertTrue(set(self.pilot["query_id"]).issubset(set(self.gold["query_id"])))
        self.assertEqual(int(self.labeled["gold_set_membership"].eq("not_reviewed").sum()), 320)

    def test_reviewed_subset_covers_every_supported_intent(self) -> None:
        counts = self.gold["intent_subtype"].value_counts()
        self.assertEqual(set(counts.index), set(INTENT_NAMES))
        self.assertGreaterEqual(int(counts.min()), 12)
        self.assertEqual(set(self.gold["language"]), {"EN", "ID", "MIXED"})
        self.assertEqual(self.pilot["cluster_id"].nunique(), 15)

    def test_labels_stay_inside_frozen_taxonomy(self) -> None:
        allowed = set(INTENT_NAMES) | {OTHER_INTENT}
        self.assertFalse(set(self.labeled["intent"]) - allowed)
        self.assertEqual(self.metrics["n_other_ambiguous"], 0)
        self.assertEqual(self.metrics["taxonomy_changes_after_pilot"], 0)

    def test_boundary_hierarchy_is_explicit(self) -> None:
        comparison = annotate_intent("medicine vs medicine efficacy in disease")
        interaction = annotate_intent("kombinasi medicine dan medicine aman atau tidak")
        guideline = annotate_intent("first line evidence terbaru 2025")
        safety = annotate_intent("dosis medicine aman tidak")
        self.assertEqual(comparison[0], "Comparative Treatment Choice")
        self.assertEqual(interaction[0], "Interaction / Combination")
        self.assertEqual(guideline[0], "Guideline / Evidence Lookup")
        self.assertEqual(safety[0], "Safety / Contraindication")
        self.assertTrue(GUIDELINES_PATH.exists())

    def test_quality_audit_is_honest_about_reviewer_design(self) -> None:
        self.assertEqual(len(self.audit), GOLD_SIZE)
        self.assertFalse(self.metrics["independent_clinician_review"])
        self.assertFalse(self.metrics["inter_annotator_agreement_available"])
        self.assertGreater(int((~self.audit["passes_agree"]).sum()), 0)
        self.assertTrue(self.audit["review_design"].str.contains("not inter-annotator").all())

    def test_three_signal_kappa_optimization_is_auditable(self) -> None:
        diagnostics = json.loads(KAPPA_PATH.read_text(encoding="utf-8"))
        self.assertGreaterEqual(
            diagnostics["fleiss_kappa_optimized_cluster_mapping"],
            diagnostics["fleiss_kappa_initial_cluster_mapping"],
        )
        self.assertEqual(
            set(diagnostics["pairwise_cohen_kappa"]),
            {"rule_vs_prototype", "rule_vs_cluster", "prototype_vs_cluster"},
        )
        self.assertIn("not evidence of clinical accuracy", diagnostics["kappa_interpretation"])


if __name__ == "__main__":
    unittest.main()
