import numpy as np
import pandas as pd

from src.value_aware_retrieval import (
    build_exact_context_signals,
    build_value_entity_signals,
)


def entity_frame(molecules):
    return pd.DataFrame(
        {
            "icd10_code": ["I10"] * len(molecules),
            "atc_code": molecules,
            "atc_class": ["C09CA"] * len(molecules),
            "therapeutic_area": ["Cardiology"] * len(molecules),
        }
    )


def test_partial_multi_molecule_match_is_not_full_coverage():
    queries = entity_frame(["C09CA01; A10BK03"])
    content = entity_frame(["C09CA01", "C09CA01; A10BK03", np.nan])
    signals, _ = build_value_entity_signals(queries, content)
    # Three of four dimensions are complete; molecule recall is one half.
    np.testing.assert_allclose(signals["requested_recall"], [[0.875, 1.0, 0.75]])
    np.testing.assert_allclose(signals["requested_missing"], [[0.125, 0.0, 0.0]])
    np.testing.assert_allclose(signals["unknown_rate"], [[0.0, 0.0, 0.25]])
    assert signals["document_precision"][0, 0] == 1.0


def test_symmetric_entity_signal_accounts_for_extra_document_values():
    queries = entity_frame(["C09CA01; A10BK03"])
    content = entity_frame(["C09CA01; C09CA03"])
    signals, _ = build_value_entity_signals(queries, content)
    assert signals["requested_recall"][0, 0] == 0.875
    assert signals["document_precision"][0, 0] == 0.875
    assert signals["symmetric_f1"][0, 0] == 0.875
    assert signals["symmetric_disagreement"][0, 0] > signals["requested_missing"][0, 0]


def test_context_distinguishes_exact_conflict_and_unknown():
    queries = pd.DataFrame(
        {
            "age_group": ["elderly"],
            "pregnancy_status": [pd.NA],
            "year": [pd.NA],
            "recency_flag": [False],
            "dose_context_flag": [False],
            "route": [pd.NA],
            "renal_function_group": ["severe_impairment"],
            "hepatic_impairment_flag": [False],
            "comparison_flag": [False],
            "prior_treatment_failure_flag": [False],
        }
    )
    content = pd.DataFrame(
        {
            "content_age_group": ["elderly", "pediatric", pd.NA],
            "content_pregnancy_status": [pd.NA] * 3,
            "publication_year": [2025, 2025, 2025],
            "content_recency_evidence": [False] * 3,
            "content_dose_context": [False] * 3,
            "content_route": [pd.NA] * 3,
            "content_renal_function_group": ["mild_impairment", "severe_impairment", pd.NA],
            "content_hepatic_context": [False] * 3,
            "content_comparison_context": [False] * 3,
            "content_prior_failure_context": [False] * 3,
        }
    )
    signals, _ = build_exact_context_signals(queries, content)
    np.testing.assert_allclose(signals["context_bonus"], [[0.5, 0.5, 0.0]])
    np.testing.assert_allclose(signals["context_penalty"], [[0.5, 0.5, 0.0]])
    np.testing.assert_allclose(signals["context_unknown"], [[0.0, 0.0, 1.0]])
