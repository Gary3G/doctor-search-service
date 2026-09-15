"""Fast contract tests for the Phase 2 taxonomy pipeline."""

from __future__ import annotations

import unittest
import json

import numpy as np
import pandas as pd

from src.config import PROCESSED_DATA_DIR, TAXONOMY_DIR
from src.taxonomy import (
    FEATURE_COLUMNS,
    CANDIDATE_INTENTS,
    SEED_INTENTS,
    build_structured_features,
    delexicalize_query,
    weak_anchor_assignment,
)


class TaxonomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.queries = pd.read_csv(PROCESSED_DATA_DIR / "queries_with_contextual_slots.csv")
        cls.queries["intent_text"] = cls.queries.apply(delexicalize_query, axis=1)

    def test_seed_and_final_taxonomy_sizes(self) -> None:
        self.assertEqual(len(SEED_INTENTS), 10)
        self.assertEqual(len(CANDIDATE_INTENTS), 11)
        self.assertEqual(len({item.intent_name for item in CANDIDATE_INTENTS}), 11)

    def test_all_queries_receive_weak_anchor_class(self) -> None:
        assigned = self.queries["intent_text"].map(weak_anchor_assignment)
        labels = assigned.map(lambda values: values[0])
        self.assertEqual(len(labels), 500)
        self.assertFalse(labels.eq("Other / Ambiguous").any())
        self.assertGreaterEqual(labels.value_counts().min(), 20)

    def test_entity_delexicalization_prevents_intent_leakage(self) -> None:
        heart_failure = self.queries.loc[self.queries["query_id"].eq("Q222")].iloc[0]
        pregnancy = self.queries.loc[self.queries["query_id"].eq("Q183")].iloc[0]
        # Heart failure is an untagged comorbidity here. The scoped failure
        # rule must still avoid treating that disease phrase as escalation.
        self.assertEqual(
            weak_anchor_assignment(heart_failure["intent_text"])[0],
            "Management / Treatment Selection",
        )
        self.assertNotIn("hypertension in pregnancy", pregnancy["intent_text"])
        self.assertEqual(
            weak_anchor_assignment(pregnancy["intent_text"])[0],
            "Dosing / Administration",
        )

    def test_structured_feature_contract(self) -> None:
        features = build_structured_features(self.queries)
        self.assertEqual(features.shape, (500, 1 + len(FEATURE_COLUMNS)))
        self.assertEqual(tuple(features.columns[1:]), FEATURE_COLUMNS)
        self.assertTrue(features[list(FEATURE_COLUMNS)].notna().all().all())

    def test_required_artifacts_and_columns(self) -> None:
        expected = {
            "phase2_seed_taxonomy.csv": {"literature_intent", "definition", "source"},
            "phase2_nlp_taxonomy_analysis.csv": {
                "cluster_id",
                "n_queries",
                "nearest_seed_intent",
                "mean_prototype_similarity",
                "top_terms",
                "dominant_entity_pattern",
                "proposed_action",
            },
            "phase2_final_taxonomy.csv": {
                "intent_name",
                "parent_intent",
                "definition",
                "inclusion_criteria",
                "exclusion_criteria",
                "positive_examples",
                "boundary_examples",
                "likely_content_preference",
                "n_queries",
            },
            "phase2_tfidf_explanations.csv": {
                "top_unigrams",
                "top_bigrams",
                "representative_queries",
            },
            "phase2_liang_hybrid_assignments.csv": {
                "liang_final_intent",
                "liang_top_probability",
                "attention_semantic",
                "attention_sentence_tfidf",
                "attention_class_centroid_tfidf",
                "weak_anchor_label",
            },
            "phase2_seed_to_final_derivation.csv": {
                "seed_parent_intent",
                "liang_subintent_analogue",
                "candidate_final_intent",
                "liang_model_n_queries",
                "final_schema_status",
            },
        }
        for filename, columns in expected.items():
            path = TAXONOMY_DIR / filename
            self.assertTrue(path.exists(), filename)
            self.assertTrue(columns.issubset(pd.read_csv(path).columns), filename)

    def test_liang_model_drives_final_support(self) -> None:
        assignments = pd.read_csv(TAXONOMY_DIR / "phase2_liang_hybrid_assignments.csv")
        final_taxonomy = pd.read_csv(TAXONOMY_DIR / "phase2_final_taxonomy.csv")
        self.assertEqual(len(assignments), 500)
        attention_sum = assignments[
            [
                "attention_semantic",
                "attention_sentence_tfidf",
                "attention_class_centroid_tfidf",
            ]
        ].sum(axis=1)
        np.testing.assert_allclose(attention_sum, 1.0, atol=1e-5)
        model_counts = assignments["liang_final_intent"].value_counts().sort_index()
        table_counts = final_taxonomy.set_index("intent_name")["n_queries"].sort_index()
        pd.testing.assert_series_equal(model_counts, table_counts, check_names=False)
        self.assertGreaterEqual(int(table_counts.min()), 20)
        self.assertTrue(
            final_taxonomy["support_estimation_method"]
            .str.contains("Liang-style")
            .all()
        )

    def test_liang_methodology_is_explicit_about_weak_supervision(self) -> None:
        methodology = json.loads(
            (TAXONOMY_DIR / "phase2_liang_methodology.json").read_text(encoding="utf-8")
        )
        self.assertFalse(methodology["gold_labels_used"])
        self.assertEqual(methodology["tfidf_max_features"], 200)
        self.assertEqual(len(methodology["published_branches"]), 3)
        metrics = pd.read_csv(TAXONOMY_DIR / "phase2_liang_branch_metrics.csv")
        self.assertIn("liang_three_branch_attention", set(metrics["model"]))


if __name__ == "__main__":
    unittest.main()
