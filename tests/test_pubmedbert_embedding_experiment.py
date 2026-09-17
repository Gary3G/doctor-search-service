import numpy as np
import pandas as pd
import pytest

from src.pubmedbert_embedding_experiment import (
    blend_dense,
    select_pubmedbert_weight,
)


def test_blend_dense_preserves_endpoints_and_validates_inputs():
    multilingual = np.array([[0.0, 1.0]])
    pubmedbert = np.array([[1.0, 0.0]])
    np.testing.assert_allclose(blend_dense(multilingual, pubmedbert, 0.0), multilingual)
    np.testing.assert_allclose(blend_dense(multilingual, pubmedbert, 0.25), [[0.25, 0.75]])
    np.testing.assert_allclose(blend_dense(multilingual, pubmedbert, 1.0), pubmedbert)
    with pytest.raises(ValueError):
        blend_dense(multilingual, pubmedbert, 1.1)
    with pytest.raises(ValueError):
        blend_dense(multilingual, np.ones((2, 2)), 0.5)


def test_validation_selection_can_retain_baseline_on_tie():
    grid = pd.DataFrame(
        {
            "pubmedbert_weight": [0.5, 0.0, 1.0],
            "ndcg@10": [0.2, 0.2, 0.1],
        }
    )
    assert select_pubmedbert_weight(grid) == 0.0
