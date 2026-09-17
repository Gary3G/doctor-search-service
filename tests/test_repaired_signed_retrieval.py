import numpy as np
import pandas as pd

from src.repaired_signed_retrieval import make_repaired_signals
from src.signed_retrieval import signed_scores


def test_repaired_context_bonus_and_missing_neutral_conflict():
    pairs = pd.DataFrame(
        {
            "query_id": ["Q1", "Q1", "Q1"],
            "content_id": ["C1", "C2", "C3"],
            "entity_coverage": [1.0, 0.0, 0.0],
            "entity_conflict_rate": [0.0, 1.0, 1.0],
            "context_coverage": [1.0, 0.0, 0.0],
            "context_constraint_count": [2, 2, 2],
        }
    )
    queries = pd.DataFrame(
        {"query_id": ["Q1"], "age_group": ["elderly"], "route": [pd.NA], "year": [2025]}
    )
    content = pd.DataFrame(
        {
            "content_id": ["C1", "C2", "C3"],
            "content_age_group": ["elderly", "pediatric", pd.NA],
            "content_route": [pd.NA, pd.NA, pd.NA],
            "publication_year": [2025, 2024, np.nan],
        }
    )
    base = {"entities": np.zeros((1, 3)), "context": np.zeros((1, 3))}
    signals, audit = make_repaired_signals(base, pairs, queries, content, (1, 3))
    np.testing.assert_allclose(signals["context_penalty"], [[0.0, 1.0, 0.0]])
    assert audit.set_index("feature").loc["explicit_age_conflict", "nonzero_pairs"] == 1
    assert audit.set_index("feature").loc["explicit_year_conflict", "nonzero_pairs"] == 1


def test_repaired_signed_score_rewards_matches_and_penalizes_only_conflicts():
    hybrid = np.array([[0.5, 0.5, 0.5]])
    signals = {
        "entity_bonus": np.array([[1.0, 0.0, 0.0]]),
        "entity_penalty": np.array([[0.0, 1.0, 0.0]]),
        "context_bonus": np.array([[1.0, 0.0, 0.0]]),
        "context_penalty": np.array([[0.0, 1.0, 0.0]]),
    }
    scores = signed_scores(hybrid, signals, (0.1, 0.1, 0.05, 0.05))
    np.testing.assert_allclose(scores, [[0.65, 0.35, 0.5]])
