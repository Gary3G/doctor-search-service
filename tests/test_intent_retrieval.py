import numpy as np
import pandas as pd
import pytest

from src.intent_retrieval import (
    intent_compatibility,
    paired_bootstrap,
    score_with_intent,
    select_intent_weight,
)


def test_soft_compatibility_sums_probability_mass_for_allowed_intents():
    classes = np.array(["Dosing / Administration", "Guideline / Evidence Lookup"])
    probabilities = np.array([[0.75, 0.25], [0.0, 1.0]])
    content_types = pd.Series(["drug_profile", "article", "guideline"])
    actual = intent_compatibility(probabilities, classes, content_types)
    np.testing.assert_allclose(actual, [[0.75, 0.25, 1.0], [0.0, 1.0, 1.0]])


def test_compatibility_rejects_invalid_probabilities():
    with pytest.raises(ValueError):
        intent_compatibility(
            np.array([[0.2, 0.2]]),
            np.array(["Dosing / Administration", "Guideline / Evidence Lookup"]),
            pd.Series(["guideline"]),
        )


def test_phase11_equal_intent_is_weight_point_two_five_on_r_e6_base():
    bm25 = np.array([[0.2, 0.8]])
    dense = np.array([[0.4, 0.6]])
    entity = np.array([[0.6, 0.2]])
    context = np.array([[0.8, 0.4]])
    intent = np.array([[1.0, 0.0]])
    base = np.mean([bm25, dense, entity, context], axis=0)
    phase12 = score_with_intent(base, intent, 0.25)
    phase11 = np.mean([bm25, dense, entity, context, intent], axis=0)
    np.testing.assert_allclose(phase12, phase11 * 1.25)


def test_selection_uses_ndcg_then_smaller_weight():
    grid = pd.DataFrame(
        {
            "intent_source": ["soft", "soft", "soft", "hard"],
            "intent_weight": [0.5, 0.1, 0.2, 0.1],
            "ndcg@10": [0.3, 0.3, 0.2, 0.9],
        }
    )
    assert select_intent_weight(grid, "soft") == 0.1


def test_paired_bootstrap_aligns_query_ids_and_reports_direction():
    baseline = pd.DataFrame({"query_id": ["A", "B", "C"], "ndcg@10": [0.0, 0.2, np.nan]})
    candidate = pd.DataFrame({"query_id": ["C", "A", "B"], "ndcg@10": [np.nan, 0.1, 0.1]})
    result = paired_bootstrap(baseline, candidate)
    assert result["eligible_queries"] == 2
    assert result["mean_delta"] == pytest.approx(0.0)
    assert result["improved_queries"] == 1
    assert result["worsened_queries"] == 1
