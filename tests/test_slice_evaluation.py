import numpy as np
import pandas as pd
import pytest

from src.slice_evaluation import (
    build_query_profiles,
    build_slice_tables,
    paired_slice_delta,
)


def _queries() -> pd.DataFrame:
    defaults = {
        "age_group": np.nan,
        "pregnancy_status": np.nan,
        "year": np.nan,
        "recency_flag": False,
        "dose_context_flag": False,
        "route": np.nan,
        "renal_function_group": np.nan,
        "hepatic_impairment_flag": False,
        "comparison_flag": False,
        "negation_flag": False,
        "prior_treatment_failure_flag": False,
    }
    rows = [
        {
            **defaults, "query_id": "Q1", "language": "EN", "disease_entity": "D1",
            "molecule_entity": "M1", "drug_class_entity": "C1",
            "intent_top_level": "Pharmacotherapy", "intent_subtype": "Dosing / Administration",
        },
        {
            **defaults, "query_id": "Q2", "language": "ID", "disease_entity": np.nan,
            "molecule_entity": "M1; M2; M1", "drug_class_entity": np.nan,
            "intent_top_level": "Evidence / Guideline Lookup", "intent_subtype": "Guideline / Evidence Lookup",
            "pregnancy_status": "pregnant", "year": 2025, "recency_flag": True,
        },
    ]
    return pd.DataFrame(rows)


def test_profiles_count_distinct_entities_and_conceptual_context_groups():
    profile = build_query_profiles(_queries()).set_index("query_id")
    assert profile.loc["Q1", "entity_count"] == 3
    assert profile.loc["Q2", "molecule_count"] == 2
    assert profile.loc["Q2", "entity_count"] == 2
    # Year and recency are one temporal group; pregnancy is one demographic group.
    assert profile.loc["Q2", "context_constraint_count"] == 2


def test_slice_catalog_keeps_empty_required_slices():
    membership, catalog = build_slice_tables(_queries())
    counts = catalog.set_index(["slice_family", "slice_name"])["global_queries"]
    assert counts.loc[("entity_count", "Zero recognized entities")] == 0
    assert counts.loc[("entity_count", "Two or more recognized entities")] == 2
    assert counts.loc[("entity_composition", "Multiple molecules")] == 1
    assert not membership.duplicated().any()


def test_paired_slice_delta_aligns_ids_and_ignores_ineligible_nan():
    baseline = pd.DataFrame({"query_id": ["A", "B", "C"], "ndcg@10": [0.0, 0.2, np.nan]})
    candidate = pd.DataFrame({"query_id": ["C", "A", "B"], "ndcg@10": [np.nan, 0.1, 0.1]})
    result = paired_slice_delta(baseline, candidate, {"A", "B", "C"})
    assert result["eligible_queries"] == 2
    assert result["mean_delta_ndcg@10"] == pytest.approx(0.0)
    assert result["improved_queries"] == 1
    assert result["worsened_queries"] == 1
