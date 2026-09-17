"""Guard Phase 14's frozen-system and evidence semantics."""
from pathlib import Path
import tempfile

import pandas as pd

from src.final_failure_analysis import (
    CASE_IDS,
    PHASE12_DIR,
    REVIEWS_PATH,
    build_phase14_artifacts,
    select_residual_cases,
)


def test_fixed_cases_are_eligible_temporal_test_misses():
    metrics = pd.read_csv(PHASE12_DIR / "per_query_metrics.csv.gz")
    reviews = pd.read_csv(REVIEWS_PATH).fillna("")
    selected = select_residual_cases(metrics, reviews)
    assert tuple(selected["query_id"]) == CASE_IDS
    assert set(selected["split"]) == {"test"}
    assert set(selected["protocol"]) == {"temporal"}
    assert selected["eligible"].all()
    assert selected["recall@10"].eq(0).all()


def test_artifacts_distinguish_proxy_failure_from_ranking_gap():
    with tempfile.TemporaryDirectory() as directory:
        paths = build_phase14_artifacts(Path(directory))
        cases = pd.read_csv(paths["cases"]).set_index("query_id")
        evidence = pd.read_csv(paths["evidence"])
        assert len(cases) == 12
        assert cases.loc["Q180", "assessment_status"] == "proxy_label_failure"
        assert cases.loc["Q180", "expected_candidate_id"] == "C013"
        assert cases.loc["Q180", "expected_candidate_rank"] == 1
        q180_positive = evidence.query(
            "query_id == 'Q180' and role == 'strongest_observed_positive'"
        ).iloc[0]
        assert q180_positive["content_id"] == "C196"
        assert str(q180_positive["grade"]) == "1"
        assert pd.isna(q180_positive["rank"])
        assert cases.loc["Q224", "expected_candidate_rank"] == 9


def test_classifier_sensitive_case_keeps_assisted_and_runtime_ranks():
    with tempfile.TemporaryDirectory() as directory:
        cases = pd.read_csv(build_phase14_artifacts(Path(directory))["cases"]).set_index("query_id")
        assert cases.loc["Q393", "predicted_intent"] == "Mechanism / Background Knowledge"
        assert cases.loc["Q393", "assisted_intent"] == "Monitoring / Response / Risk Assessment"
        assert cases.loc["Q393", "assisted_top_positive_id"] == "C203"
        assert pd.isna(cases.loc["Q393", "assisted_top_positive_final_rank"])
        assert cases.loc["Q393", "assisted_top_positive_rank"] == 10
