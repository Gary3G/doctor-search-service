import numpy as np
import pandas as pd

from src.intent_signed_retrieval import (
    WEIGHTS,
    build_configurations,
    intent_signed_scores,
)


def test_intent_signed_score_combines_all_terms():
    hybrid = np.array([[0.5, 0.5, 0.5]])
    signals = {
        "entity_bonus": np.array([[1.0, 0.0, 0.0]]),
        "entity_penalty": np.array([[0.0, 1.0, 0.0]]),
        "context_bonus": np.array([[1.0, 0.0, 0.0]]),
        "context_penalty": np.array([[0.0, 1.0, 0.0]]),
    }
    intent = np.array([[1.0, 0.0, 0.0]])
    scores = intent_signed_scores(hybrid, signals, intent, (0.1, 0.1, 0.05, 0.05, 0.2))
    np.testing.assert_allclose(scores, [[0.85, 0.35, 0.5]])


def test_r_e7_additive_equivalence_preserves_scores_up_to_scale():
    hybrid = np.array([[0.2, 0.8]])
    entity = np.array([[0.4, 0.3]])
    context = np.array([[0.7, 0.1]])
    intent = np.array([[1.0, 0.0]])
    signals = {
        "entity_bonus": entity,
        "entity_penalty": np.zeros_like(entity),
        "context_bonus": context,
        "context_penalty": np.zeros_like(context),
    }
    additive = intent_signed_scores(hybrid, signals, intent, (0.5, 0.0, 0.5, 0.0, 0.5))
    equal_five_signal = (2 * hybrid + entity + context + intent) / 5
    np.testing.assert_allclose(additive, 2.5 * equal_five_signal)


def test_all_terms_configuration_requires_every_term_nonzero():
    rows = []
    for index, weights in enumerate(
        [
            (0.0, 0.0, 0.0, 0.0, 0.0),
            (0.2, 0.2, 0.2, 0.0, 0.0),
            (0.0, 0.0, 0.0, 0.0, 0.1),
            (0.2, 0.2, 0.2, 0.0, 0.2),
            (0.05, 0.05, 0.05, 0.05, 0.05),
            (0.2, 0.2, 0.2, 0.2, 0.2),
        ]
    ):
        rows.append(dict(zip(WEIGHTS, weights)) | {"ndcg@10": 0.1 + index * 0.01})
    configurations = build_configurations(pd.DataFrame(rows))
    assert all(weight > 0 for weight in configurations["all_terms_nonzero"])
    assert configurations["signed_plus_intent"][-1] > 0
