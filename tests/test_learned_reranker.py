import numpy as np
import pandas as pd

from src.learned_reranker import (
    build_pairwise_training,
    predicted_intent_compatibility,
    select_candidate,
)


def test_predicted_intent_uses_saved_runtime_label_policy():
    predictions = pd.DataFrame(
        {
            "query_id": ["Q2", "Q1"],
            "predicted_intent": [
                "Dosing / Administration",
                "Guideline / Evidence Lookup",
            ],
        }
    )
    queries = pd.DataFrame({"query_id": ["Q1", "Q2"]})
    content = pd.DataFrame(
        {"content_type": ["guideline", "drug_profile", "article"]}
    )
    actual = predicted_intent_compatibility(predictions, queries, content)
    np.testing.assert_allclose(actual, [[1.0, 0.0, 1.0], [1.0, 1.0, 0.0]])


def test_pairwise_training_is_symmetric_and_query_weighted():
    features = np.array([[3.0, 1.0], [1.0, 0.0], [4.0, 2.0], [0.0, 0.0]])
    judgments = pd.DataFrame(
        {
            "query_id": ["Q1", "Q1", "Q2", "Q2"],
            "relevance_grade": [3, 0, 1, 0],
        }
    )
    differences, labels, weights = build_pairwise_training(
        features, judgments, np.arange(4)
    )
    np.testing.assert_allclose(differences[0], -differences[1])
    np.testing.assert_allclose(differences[2], -differences[3])
    assert labels.tolist() == [1, 0, 1, 0]
    # Each query has equal total mass; both orientations match.
    assert weights.tolist() == [1.0, 1.0, 1.0, 1.0]


def test_candidate_selection_uses_validation_ndcg_and_tie_rules():
    grid = pd.DataFrame(
        {
            "configuration": ["base", "pair", "plain", "balanced"],
            "family": ["baseline", "pairwise", "pointwise", "pointwise"],
            "class_weight": [
                "not_applicable",
                "not_applicable",
                "none",
                "balanced",
            ],
            "C": [np.nan, 0.1, 0.1, 0.1],
            "ndcg@10": [0.9, 0.2, 0.2, 0.2],
        }
    )
    # The baseline is a comparator, not a learned candidate. Pointwise wins a
    # learned-model tie, and balanced wins the pointwise tie.
    assert select_candidate(grid) == "balanced"
