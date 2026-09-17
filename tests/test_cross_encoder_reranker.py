import numpy as np
import pandas as pd

from src.cross_encoder_reranker import (
    baseline_candidate_indices,
    minmax,
    rerank_candidate_pool,
    select_configuration,
)


def test_minmax_handles_constant_values():
    np.testing.assert_allclose(minmax(np.array([2.0, 4.0, 6.0])), [0.0, 0.5, 1.0])
    np.testing.assert_allclose(minmax(np.array([3.0, 3.0])), [0.0, 0.0])


def test_cross_encoder_can_promote_a_deeper_candidate():
    content_ids = pd.Series(["C1", "C2", "C3"])
    baseline = np.array([[3.0, 2.0, 1.0]])
    candidates = baseline_candidate_indices(baseline, content_ids, depth=3)
    cross_scores = np.array([[0.0, 0.5, 1.0]])
    ranking = rerank_candidate_pool(
        baseline,
        candidates,
        cross_scores,
        pd.Series(["Q1"]),
        content_ids,
        depth=3,
        cross_weight=1.0,
        ranking_depth=2,
    )
    assert ranking["content_id"].tolist() == ["C3", "C2"]
    assert ranking["rank"].tolist() == [1, 2]


def test_validation_selection_prefers_shallower_and_lower_weight_on_ties():
    grid = pd.DataFrame(
        {
            "candidate_depth": [100, 20, 20],
            "cross_weight": [0.25, 0.5, 0.25],
            "ndcg@10": [0.2, 0.2, 0.2],
        }
    )
    assert select_configuration(grid) == (20, 0.25)
