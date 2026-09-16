"""Phase 7.5 CLEAR-inspired query-content compatibility features.

The original CLEAR methodology retrieves entity-relevant context from clinical
notes by extracting, selecting, augmenting, and matching clinical entities. This
module transfers that pattern to doctor search without reproducing CLEAR's task
or model: supplied query/content entities are normalized and expanded through
ICD/ATC hierarchy, contextual constraints are extracted from content titles,
and transparent pairwise features are computed for CPU-friendly reranking.

Behavioral relevance is never used to construct or weight these features.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import unicodedata
from typing import Any

from src.config import CACHE_DIR, FIGURES_DIR, OUTPUT_DIR, PROCESSED_DATA_DIR

os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.data import load_content
from src.intent import LABELED_QUERIES_PATH
from src.query_extraction import extract_slots
from src.relevance_labels import JUDGMENTS_PATH


PHASE75_DIR = OUTPUT_DIR / "compatibility"
COMPATIBILITY_MATRIX_PATH = PROCESSED_DATA_DIR / "query_content_compatibility.csv.gz"
CONTENT_CONTEXT_PATH = PROCESSED_DATA_DIR / "content_with_contextual_slots.csv"
FEATURE_DICTIONARY_PATH = PHASE75_DIR / "phase75_feature_dictionary.csv"
FEATURE_SUMMARY_PATH = PHASE75_DIR / "phase75_feature_summary.csv"
CLEAR_MAPPING_PATH = PHASE75_DIR / "phase75_clear_methodology_mapping.csv"
OBSERVED_DIAGNOSTICS_PATH = PHASE75_DIR / "phase75_observed_relevance_diagnostics.csv"
EXAMPLES_PATH = PHASE75_DIR / "phase75_compatibility_examples.csv"
METRICS_PATH = PHASE75_DIR / "phase75_compatibility_metrics.json"
REPORT_PATH = PHASE75_DIR / "phase75_compatibility_report.md"
FIGURE_PATH = FIGURES_DIR / "phase75_structured_compatibility.png"

QUERY_ENTITY_COLUMNS = {
    "disease": ("disease_entity", "icd10_code"),
    "molecule": ("molecule_entity", "atc_code"),
    "drug_class": ("drug_class_entity", "atc_class"),
    "therapeutic_area": ("therapeutic_area",),
}
CONTENT_ENTITY_COLUMNS = {
    "disease": ("disease_entity", "icd10_code"),
    "molecule": ("molecule_entity", "atc_code"),
    "drug_class": ("drug_class_entity", "atc_class"),
    "therapeutic_area": ("therapeutic_area",),
}


def _normalize_term(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold().strip()
    text = re.sub(r"[^\w.+-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalized_values(value: Any) -> frozenset[str]:
    """Normalize semicolon-delimited metadata into an exact-match set."""
    if pd.isna(value):
        return frozenset()
    return frozenset(
        normalized
        for part in str(value).split(";")
        if (normalized := _normalize_term(part))
    )


def _code_values(value: Any) -> frozenset[str]:
    return frozenset(
        re.sub(r"[^A-Z0-9.]", "", part.upper())
        for part in normalized_values(value)
        if part
    )


def _icd_parents(codes: frozenset[str]) -> frozenset[str]:
    return frozenset(re.sub(r"[^A-Z0-9]", "", code)[:3] for code in codes if len(code) >= 3)


def _atc_classes(codes: frozenset[str]) -> frozenset[str]:
    return frozenset(re.sub(r"[^A-Z0-9]", "", code)[:5] for code in codes if len(code) >= 5)


def _overlap(left: pd.Series, right: pd.Series) -> pd.Series:
    return pd.Series(
        [bool(a & b) for a, b in zip(left, right)], index=left.index, dtype=bool
    )


def _both_present(left: pd.Series, right: pd.Series) -> pd.Series:
    return left.map(bool) & right.map(bool)


def prepare_content_context(content: pd.DataFrame) -> pd.DataFrame:
    """Extract query-compatible contextual evidence from available titles.

    The supplied corpus has metadata and titles but no body text. Title-derived
    absence is therefore unknown, never an explicit conflict.
    """
    required = {
        "content_id", "title", "content_type", "publication_year", "language",
        "disease_entity", "icd10_code", "molecule_entity", "atc_code",
        "drug_class_entity", "atc_class", "therapeutic_area",
    }
    missing = sorted(required - set(content.columns))
    if missing:
        raise ValueError(f"Content is missing required columns: {missing}")
    if content["content_id"].duplicated().any():
        raise ValueError("content_id must be unique")

    slot_frame = pd.DataFrame(
        [extract_slots(title).__dict__ for title in content["title"]],
        index=content.index,
    ).add_prefix("title_")
    prepared = pd.concat([content.reset_index(drop=True), slot_frame.reset_index(drop=True)], axis=1)
    prepared["content_age_group"] = prepared["title_age_group"]
    prepared["content_pregnancy_status"] = prepared["title_pregnancy_status"]
    prepared["content_route"] = prepared["title_route"]
    prepared["content_renal_function_group"] = prepared["title_renal_function_group"]
    prepared["content_recency_evidence"] = prepared["title_recency_flag"].astype(bool)
    prepared["content_dose_context"] = (
        prepared["title_dose_context_flag"].astype(bool)
        | prepared["content_type"].eq("drug_profile")
    )
    prepared["content_hepatic_context"] = prepared[
        "title_hepatic_impairment_flag"
    ].astype(bool)
    prepared["content_comparison_context"] = (
        prepared["title_comparison_flag"].astype(bool)
        | prepared["content_type"].eq("review")
    )
    prepared["content_prior_failure_context"] = prepared[
        "title_prior_treatment_failure_flag"
    ].astype(bool)
    return prepared


def _validate_queries(queries: pd.DataFrame) -> None:
    required = {
        "query_id", "query_text", "language", "intent", "age_group",
        "pregnancy_status", "year", "recency_flag", "dose_context_flag",
        "route", "renal_function_group", "hepatic_impairment_flag",
        "comparison_flag", "negation_flag", "prior_treatment_failure_flag",
        *(column for columns in QUERY_ENTITY_COLUMNS.values() for column in columns),
    }
    missing = sorted(required - set(queries.columns))
    if missing:
        raise ValueError(f"Queries are missing required columns: {missing}")
    if queries["query_id"].duplicated().any():
        raise ValueError("query_id must be unique")


def _prepare_pair_frame(queries: pd.DataFrame, content: pd.DataFrame) -> pd.DataFrame:
    query_columns = [
        "query_id", "query_text", "language", "intent", "age_group",
        "pregnancy_status", "year", "recency_flag", "dose_context_flag",
        "route", "renal_function_group", "hepatic_impairment_flag",
        "comparison_flag", "negation_flag", "prior_treatment_failure_flag",
        *(column for columns in QUERY_ENTITY_COLUMNS.values() for column in columns),
    ]
    content_columns = [
        "content_id", "title", "content_type", "language", "publication_year",
        "content_age_group", "content_pregnancy_status", "content_route",
        "content_renal_function_group", "content_recency_evidence",
        "content_dose_context", "content_hepatic_context",
        "content_comparison_context", "content_prior_failure_context",
        *(column for columns in CONTENT_ENTITY_COLUMNS.values() for column in columns),
    ]
    query_view = queries[query_columns].rename(
        columns={
            **{column: f"query_{column}" for column in query_columns if column != "query_id"},
        }
    )
    content_view = content[content_columns].rename(
        columns={
            **{column: f"content_{column}" for column in content_columns if column != "content_id" and not column.startswith("content_")},
        }
    )
    return query_view.merge(content_view, how="cross")


def build_compatibility_matrix(
    queries: pd.DataFrame, content: pd.DataFrame
) -> pd.DataFrame:
    """Compute behavior-independent structured features for every query-content pair."""
    _validate_queries(queries)
    prepared_content = prepare_content_context(content)
    pairs = _prepare_pair_frame(queries, prepared_content)

    set_columns = {
        "query_disease_name": (pairs["query_disease_entity"], normalized_values),
        "content_disease_name": (pairs["content_disease_entity"], normalized_values),
        "query_icd": (pairs["query_icd10_code"], _code_values),
        "content_icd": (pairs["content_icd10_code"], _code_values),
        "query_molecule_name": (pairs["query_molecule_entity"], normalized_values),
        "content_molecule_name": (pairs["content_molecule_entity"], normalized_values),
        "query_atc": (pairs["query_atc_code"], _code_values),
        "content_atc": (pairs["content_atc_code"], _code_values),
        "query_class_name": (pairs["query_drug_class_entity"], normalized_values),
        "content_class_name": (pairs["content_drug_class_entity"], normalized_values),
        "query_atc_class": (pairs["query_atc_class"], _code_values),
        "content_atc_class": (pairs["content_atc_class"], _code_values),
        "query_area": (pairs["query_therapeutic_area"], normalized_values),
        "content_area": (pairs["content_therapeutic_area"], normalized_values),
    }
    sets = {
        name: series.map(normalizer)
        for name, (series, normalizer) in set_columns.items()
    }
    sets["query_icd_parent"] = sets["query_icd"].map(_icd_parents)
    sets["content_icd_parent"] = sets["content_icd"].map(_icd_parents)
    sets["query_atc_augmented_class"] = pd.Series(
        [explicit | _atc_classes(codes) for explicit, codes in zip(sets["query_atc_class"], sets["query_atc"])],
        index=pairs.index,
    )
    sets["content_atc_augmented_class"] = pd.Series(
        [explicit | _atc_classes(codes) for explicit, codes in zip(sets["content_atc_class"], sets["content_atc"])],
        index=pairs.index,
    )

    result = pairs[["query_id", "content_id"]].copy()
    result["disease_name_match"] = _overlap(sets["query_disease_name"], sets["content_disease_name"])
    result["icd10_exact_match"] = _overlap(sets["query_icd"], sets["content_icd"])
    result["icd10_parent_match"] = _overlap(sets["query_icd_parent"], sets["content_icd_parent"])
    result["disease_match"] = result["disease_name_match"] | result["icd10_exact_match"]
    result["disease_hierarchical_match"] = result["icd10_parent_match"] & ~result["disease_match"]

    result["molecule_name_match"] = _overlap(sets["query_molecule_name"], sets["content_molecule_name"])
    result["atc_code_exact_match"] = _overlap(sets["query_atc"], sets["content_atc"])
    result["molecule_match"] = result["molecule_name_match"] | result["atc_code_exact_match"]
    result["drug_class_name_match"] = _overlap(sets["query_class_name"], sets["content_class_name"])
    result["atc_class_match"] = _overlap(
        sets["query_atc_augmented_class"], sets["content_atc_augmented_class"]
    )
    result["drug_class_match"] = result["drug_class_name_match"] | result["atc_class_match"]
    result["molecule_hierarchical_match"] = ~result["molecule_match"] & result["drug_class_match"]
    result["therapeutic_area_match"] = _overlap(sets["query_area"], sets["content_area"])

    query_present = {
        "disease": sets["query_disease_name"].map(bool) | sets["query_icd"].map(bool),
        "molecule": sets["query_molecule_name"].map(bool) | sets["query_atc"].map(bool),
        "drug_class": sets["query_class_name"].map(bool) | sets["query_atc_augmented_class"].map(bool),
        "therapeutic_area": sets["query_area"].map(bool),
    }
    content_present = {
        "disease": sets["content_disease_name"].map(bool) | sets["content_icd"].map(bool),
        "molecule": sets["content_molecule_name"].map(bool) | sets["content_atc"].map(bool),
        "drug_class": sets["content_class_name"].map(bool) | sets["content_atc_augmented_class"].map(bool),
        "therapeutic_area": sets["content_area"].map(bool),
    }
    exact_matches = {
        "disease": result["disease_match"],
        "molecule": result["molecule_match"],
        "drug_class": result["drug_class_match"],
        "therapeutic_area": result["therapeutic_area_match"],
    }
    augmented_matches = {
        **exact_matches,
        "disease": result["disease_match"] | result["disease_hierarchical_match"],
        "molecule": result["molecule_match"] | result["molecule_hierarchical_match"],
    }
    for dimension in ("disease", "molecule", "drug_class", "therapeutic_area"):
        result[f"{dimension}_query_present"] = query_present[dimension]
        result[f"{dimension}_conflict"] = (
            query_present[dimension]
            & content_present[dimension]
            & ~exact_matches[dimension]
        )

    result["entity_query_count"] = sum(
        result[f"{dimension}_query_present"].astype(int)
        for dimension in ("disease", "molecule", "drug_class", "therapeutic_area")
    )
    result["entity_exact_match_count"] = sum(
        (query_present[dimension] & exact_matches[dimension]).astype(int)
        for dimension in exact_matches
    )
    result["entity_augmented_match_count"] = sum(
        (query_present[dimension] & augmented_matches[dimension]).astype(int)
        for dimension in augmented_matches
    )
    result["entity_conflict_count"] = sum(
        result[f"{dimension}_conflict"].astype(int)
        for dimension in ("disease", "molecule", "drug_class", "therapeutic_area")
    )
    denominator = result["entity_query_count"].replace(0, np.nan)
    result["entity_coverage"] = (result["entity_exact_match_count"] / denominator).fillna(0.0)
    result["entity_augmented_coverage"] = (
        result["entity_augmented_match_count"] / denominator
    ).fillna(0.0)
    result["entity_conflict_rate"] = (result["entity_conflict_count"] / denominator).fillna(0.0)

    query_age = pairs["query_age_group"].notna()
    content_age = pairs["content_age_group"].notna()
    result["age_group_match"] = query_age & content_age & pairs["query_age_group"].eq(pairs["content_age_group"])
    result["age_group_conflict"] = query_age & content_age & ~result["age_group_match"]

    query_pregnancy = pairs["query_pregnancy_status"].notna()
    content_pregnancy = pairs["content_pregnancy_status"].notna()
    result["pregnancy_match"] = query_pregnancy & content_pregnancy
    result["pregnancy_conflict"] = False

    numeric_query_year = pd.to_numeric(pairs["query_year"], errors="coerce")
    numeric_content_year = pd.to_numeric(
        pairs["content_publication_year"], errors="coerce"
    )
    query_year = numeric_query_year.notna()
    result["year_match"] = (
        query_year & numeric_query_year.eq(numeric_content_year).fillna(False)
    )
    result["year_distance"] = np.where(
        query_year,
        (numeric_query_year - numeric_content_year).abs(),
        np.nan,
    )
    result["year_conflict"] = query_year & ~result["year_match"]

    latest_year = int(prepared_content["publication_year"].max())
    query_recency = pairs["query_recency_flag"].astype(bool)
    result["recency_match"] = query_recency & pairs["content_publication_year"].ge(latest_year - 1)
    result["recency_conflict"] = query_recency & pairs["content_publication_year"].lt(latest_year - 2)

    query_dose = pairs["query_dose_context_flag"].astype(bool)
    result["dose_context_match"] = query_dose & pairs["content_dose_context"].astype(bool)

    query_route = pairs["query_route"].notna()
    content_route = pairs["content_route"].notna()
    result["route_match"] = query_route & content_route & pairs["query_route"].eq(pairs["content_route"])
    result["route_conflict"] = query_route & content_route & ~result["route_match"]

    query_renal = pairs["query_renal_function_group"].notna()
    content_renal = pairs["content_renal_function_group"].notna()
    result["renal_context_match"] = query_renal & content_renal
    result["renal_exact_match"] = result["renal_context_match"] & pairs[
        "query_renal_function_group"
    ].eq(pairs["content_renal_function_group"])
    result["renal_context_conflict"] = False

    query_hepatic = pairs["query_hepatic_impairment_flag"].astype(bool)
    result["hepatic_context_match"] = query_hepatic & pairs["content_hepatic_context"].astype(bool)
    query_comparison = pairs["query_comparison_flag"].astype(bool)
    result["comparison_context_match"] = query_comparison & pairs[
        "content_comparison_context"
    ].astype(bool)
    query_failure = pairs["query_prior_treatment_failure_flag"].astype(bool)
    result["prior_failure_context_match"] = query_failure & pairs[
        "content_prior_failure_context"
    ].astype(bool)
    result["query_negation_flag"] = pairs["query_negation_flag"].astype(bool)

    context_specs = [
        (query_age, result["age_group_match"], result["age_group_conflict"]),
        (query_pregnancy, result["pregnancy_match"], result["pregnancy_conflict"]),
        (query_year, result["year_match"], result["year_conflict"]),
        (query_recency, result["recency_match"], result["recency_conflict"]),
        (query_dose, result["dose_context_match"], pd.Series(False, index=pairs.index)),
        (query_route, result["route_match"], result["route_conflict"]),
        (query_renal, result["renal_context_match"], result["renal_context_conflict"]),
        (query_hepatic, result["hepatic_context_match"], pd.Series(False, index=pairs.index)),
        (query_comparison, result["comparison_context_match"], pd.Series(False, index=pairs.index)),
        (query_failure, result["prior_failure_context_match"], pd.Series(False, index=pairs.index)),
    ]
    result["context_constraint_count"] = sum(active.astype(int) for active, _, _ in context_specs)
    result["context_match_count"] = sum((active & match).astype(int) for active, match, _ in context_specs)
    result["context_conflict_count"] = sum((active & conflict).astype(int) for active, _, conflict in context_specs)
    context_denominator = result["context_constraint_count"].replace(0, np.nan)
    result["context_coverage"] = (result["context_match_count"] / context_denominator).fillna(0.0)
    result["context_conflict_rate"] = (
        result["context_conflict_count"] / context_denominator
    ).fillna(0.0)

    intent_content_types = {
        "Dosing / Administration": {"drug_profile", "clinical_summary", "guideline"},
        "Safety / Contraindication": {"drug_profile", "clinical_summary", "guideline"},
        "Guideline / Evidence Lookup": {"guideline", "review", "article"},
        "Management / Treatment Selection": {"guideline", "clinical_summary", "review"},
        "Treatment Change / Escalation": {"guideline", "clinical_summary", "case_report"},
        "Monitoring / Response / Risk Assessment": {"guideline", "clinical_summary"},
        "Prophylaxis / Maintenance": {"guideline", "clinical_summary"},
        "Mechanism / Background Knowledge": {"article", "review", "drug_profile"},
        "Comparative Treatment Choice": {"review", "article", "guideline"},
        "Interaction / Combination": {"drug_profile", "clinical_summary", "review"},
        "Efficacy / Outcomes": {"article", "review", "guideline"},
    }
    result["intent_content_type_match"] = pd.Series(
        [content_type in intent_content_types.get(intent, set()) for intent, content_type in zip(pairs["query_intent"], pairs["content_type"])],
        index=pairs.index,
        dtype=bool,
    )

    has_context = result["context_constraint_count"].gt(0)
    result["entity_score"] = result["entity_augmented_coverage"]
    result["context_score"] = result["context_coverage"]
    result["structured_score"] = np.where(
        has_context,
        (result["entity_score"] + result["context_score"]) / 2.0,
        result["entity_score"],
    )
    result["structured_conflict_rate"] = np.where(
        has_context,
        (result["entity_conflict_rate"] + result["context_conflict_rate"]) / 2.0,
        result["entity_conflict_rate"],
    )

    result.insert(2, "query_text", pairs["query_query_text"])
    result.insert(3, "content_title", pairs["content_title"])
    result.insert(4, "query_intent", pairs["query_intent"])
    result.insert(5, "content_type", pairs["content_type"])
    result.insert(6, "query_language", pairs["query_language"])
    result.insert(7, "content_language", pairs["content_language"])
    result["feature_version"] = "clear_inspired_v1"

    expected_rows = len(queries) * len(content)
    if len(result) != expected_rows or result.duplicated(["query_id", "content_id"]).any():
        raise AssertionError("Compatibility matrix must contain one row per corpus pair")
    if not result["structured_score"].between(0, 1).all():
        raise AssertionError("structured_score must be bounded in [0, 1]")
    return result


def build_feature_dictionary() -> pd.DataFrame:
    rows = [
        ("disease_match", "entity_exact", "Exact normalized disease name or ICD-10 code overlap."),
        ("molecule_match", "entity_exact", "Exact normalized molecule name or ATC code overlap."),
        ("drug_class_match", "entity_hierarchy", "Drug-class name or ATC-class overlap, including class derived from ATC code."),
        ("therapeutic_area_match", "entity_broad", "Exact normalized therapeutic-area overlap."),
        ("entity_coverage", "entity_aggregate", "Exact matched query entity dimensions divided by populated query dimensions."),
        ("entity_augmented_coverage", "entity_aggregate", "Exact or hierarchy-related entity dimensions divided by populated query dimensions."),
        ("entity_conflict_rate", "entity_conflict", "Populated but nonmatching content dimensions divided by populated query dimensions."),
        ("age_group_match", "context", "Query and title-derived content age groups match."),
        ("pregnancy_match", "context", "Query and content title both contain normalized pregnancy context."),
        ("year_match", "context", "Requested year equals content publication year."),
        ("recency_match", "context", "Recency query matched content published within one year of corpus maximum."),
        ("dose_context_match", "context", "Dose query matched title dosing cue or drug-profile content."),
        ("route_match", "context", "Normalized query and title-derived administration routes match."),
        ("renal_context_match", "context", "Query and title both express renal-function context."),
        ("hepatic_context_match", "context", "Hepatic query matched title-derived hepatic context."),
        ("comparison_context_match", "context", "Comparison query matched title cue or review content type."),
        ("prior_failure_context_match", "context", "Prior-failure query matched refractory/failure title evidence."),
        ("context_coverage", "context_aggregate", "Matched active query constraints divided by active contextual constraints."),
        ("context_conflict_rate", "context_conflict", "Explicit contextual conflicts divided by active contextual constraints."),
        ("intent_content_type_match", "intent_prior", "Rule-defined compatibility between query intent and content type; not included in structured score."),
        ("structured_score", "aggregate", "Equal mean of entity and context coverage when context exists; otherwise entity coverage."),
        ("structured_conflict_rate", "aggregate", "Equal mean of entity and context conflict rates when context exists."),
    ]
    return pd.DataFrame(rows, columns=["feature", "group", "definition"]).assign(
        behavior_used=False,
        initial_weighting="equal_component_average",
    )


def build_clear_mapping() -> pd.DataFrame:
    rows = [
        ("Clinical entity extraction", "Use supplied disease/molecule/class/area labels plus Phase 1.6 contextual slots.", "Preserves clinically meaningful query structure instead of treating the query as undifferentiated text.", "No new neural NER is trained."),
        ("Entity relevance selection", "Separate exact entities, hierarchy, context, intent prior, and conflicts.", "Not every extracted field should have equal semantic meaning or become a hard filter.", "Selection is transparent and rule-based."),
        ("Entity augmentation", "Normalize names; use ICD parent and ATC molecule-to-class relations.", "Recovers clinically related content when exact surface forms or molecule identity differ.", "No external synonym ontology; hierarchy is limited to supplied codes."),
        ("Target matching", "Compute exact overlap, coverage, hierarchy, context match, and conflict features for every pair.", "Makes NER operational as ranking evidence rather than descriptive metadata.", "Missing title evidence is unknown, not a negative."),
        ("Relevant context retrieval", "Expose an equal-weight structured score for later BM25/hybrid reranking.", "Provides a CPU-friendly signal that can be ablated in later retrieval experiments.", "Phase 7.5 does not tune weights or evaluate a ranker."),
        ("Component evaluation", "Audit extraction separately and retain feature groups for later ablation.", "Distinguishes extraction quality from downstream retrieval contribution.", "Existing slot QA is limited without independent clinician gold labels."),
    ]
    return pd.DataFrame(rows, columns=["clear_stage", "project_adaptation", "why_used", "boundary"])


def build_feature_summary(matrix: pd.DataFrame) -> pd.DataFrame:
    feature_columns = [
        column for column in matrix.columns
        if column.endswith(("_match", "_conflict"))
        or column in {
            "entity_coverage", "entity_augmented_coverage", "entity_conflict_rate",
            "context_coverage", "context_conflict_rate", "structured_score",
            "structured_conflict_rate",
        }
    ]
    rows = []
    for column in feature_columns:
        values = matrix[column].astype(float)
        rows.append(
            {
                "feature": column,
                "nonzero_pairs": int(values.ne(0).sum()),
                "nonzero_share": float(values.ne(0).mean()),
                "mean": float(values.mean()),
                "median": float(values.median()),
                "maximum": float(values.max()),
            }
        )
    return pd.DataFrame(rows).sort_values(["nonzero_share", "feature"], ascending=[False, True])


def build_observed_diagnostics(
    matrix: pd.DataFrame, judgments: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, float]]:
    observed = matrix.merge(
        judgments[["query_id", "content_id", "relevance_grade"]],
        on=["query_id", "content_id"],
        how="inner",
        validate="one_to_one",
    )
    metrics = [
        "entity_coverage", "entity_augmented_coverage", "entity_conflict_rate",
        "context_coverage", "context_conflict_rate", "structured_score",
        "structured_conflict_rate", "intent_content_type_match",
    ]
    diagnostics = (
        observed.groupby("relevance_grade", as_index=False)
        .agg(rows=("query_id", "size"), **{f"mean_{metric}": (metric, "mean") for metric in metrics})
    )
    correlation = observed[["structured_score", "relevance_grade"]].corr(
        method="spearman"
    ).iloc[0, 1]
    return diagnostics, {
        "observed_pairs": int(len(observed)),
        "structured_score_relevance_spearman": float(correlation),
    }


def build_examples(matrix: pd.DataFrame, rows_per_group: int = 10) -> pd.DataFrame:
    specifications = {
        "highest_structured_score": matrix.sort_values(
            ["structured_score", "structured_conflict_rate", "query_id", "content_id"],
            ascending=[False, True, True, True],
        ),
        "entity_conflict": matrix[matrix["entity_conflict_count"].gt(0)].sort_values(
            ["entity_conflict_count", "structured_score", "query_id", "content_id"],
            ascending=[False, True, True, True],
        ),
        "context_match": matrix[matrix["context_match_count"].gt(0)].sort_values(
            ["context_coverage", "entity_augmented_coverage", "query_id", "content_id"],
            ascending=[False, False, True, True],
        ),
    }
    columns = [
        "query_id", "content_id", "query_text", "content_title",
        "entity_coverage", "entity_augmented_coverage", "entity_conflict_count",
        "context_constraint_count", "context_match_count", "context_conflict_count",
        "structured_score", "structured_conflict_rate",
    ]
    return pd.concat(
        [frame.head(rows_per_group)[columns].assign(example_group=name) for name, frame in specifications.items()],
        ignore_index=True,
    )[["example_group", *columns]]


def _markdown_table(frame: pd.DataFrame, max_rows: int = 40) -> str:
    view = frame.head(max_rows)
    headers = [str(column) for column in view.columns]
    body = [
        [str(value) for value in row]
        for row in view.itertuples(index=False, name=None)
    ]
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(row) + " |" for row in body),
        ]
    )


def _plot(matrix: pd.DataFrame, observed: pd.DataFrame) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    axes[0].hist(matrix["structured_score"], bins=np.linspace(0, 1, 21), color="#4292C6")
    axes[0].set_yscale("log")
    axes[0].set(
        title="Structured score across full corpus",
        xlabel="Structured score",
        ylabel="Query-content pairs (log scale)",
    )
    axes[0].grid(axis="y", alpha=0.2)
    score_columns = [column for column in observed.columns if column.startswith("mean_")]
    selected = ["mean_entity_augmented_coverage", "mean_context_coverage", "mean_structured_score"]
    observed.set_index("relevance_grade")[[column for column in selected if column in score_columns]].plot(
        kind="bar", ax=axes[1], color=["#9ECAE1", "#4292C6", "#08519C"]
    )
    axes[1].set(title="Compatibility by weak relevance grade", xlabel="Relevance grade", ylabel="Mean feature value")
    axes[1].tick_params(axis="x", rotation=0)
    axes[1].grid(axis="y", alpha=0.2)
    axes[1].legend(["Entity augmented coverage", "Context coverage", "Structured score"])
    fig.tight_layout()
    fig.savefig(FIGURE_PATH, dpi=180, bbox_inches="tight")
    plt.close(fig)


def build_report(
    metrics: dict[str, Any], clear_mapping: pd.DataFrame,
    summary: pd.DataFrame, diagnostics: pd.DataFrame,
) -> str:
    return "\n".join(
        [
            "# Phase 7.5: CLEAR-Inspired Structured Compatibility", "",
            "## How and why CLEAR is used", "",
            "CLEAR (Lopez et al., npj Digital Medicine, 2025) is used as a methodological pattern, not copied "
            "as a model. The original task retrieves "
            "entity-relevant context from long clinical notes for downstream extraction. This project ranks "
            "independent medical content for doctor queries. The transferable idea is that extracted clinical "
            "entities should be selected, normalized/augmented, and actively matched—not left as descriptive metadata.", "",
            _markdown_table(clear_mapping), "",
            "The adaptation is CPU-first. Supplied disease, molecule, drug-class, and therapeutic-area labels are "
            "normalized; ICD parent and ATC class relationships provide bounded hierarchy expansion; Phase 1.6 "
            "constraints are matched against content metadata and title-derived evidence. No neural NER, external "
            "ontology expansion, encoder fine-tuning, or CLEAR model reproduction is claimed.", "",
            "## Pairwise feature contract", "",
            f"The matrix contains all {metrics['matrix_rows']:,} combinations of {metrics['queries']:,} queries and "
            f"{metrics['content_items']:,} content items. It contains no relevance grade, behavior, doctor, session, "
            "rank, popularity, or exposure feature. This prevents label leakage before evaluation splitting.", "",
            "Exact entity matches, hierarchy matches, and conflicts are separate. Missing title context is treated as "
            "unknown rather than conflicting. This distinction preserves recall and avoids unsafe hard filtering.", "",
            "## Initial structured score", "",
            "`entity_score` is augmented entity coverage. `context_score` is coverage of active query constraints. "
            "When context exists, `structured_score` is their equal mean; otherwise it equals entity score. "
            "`structured_conflict_rate` is retained separately rather than applying an arbitrary penalty. Intent-to-content-type "
            "compatibility is also separate and is not included in the score. No weight was selected using behavior.", "",
            f"Mean structured score is {metrics['mean_structured_score']:.3f}; "
            f"{metrics['pairs_with_any_entity_match']:,} pairs have an augmented entity match and "
            f"{metrics['pairs_with_any_context_match']:,} have a context match.", "",
            "## Descriptive construct check", "",
            _markdown_table(diagnostics.round(4)), "",
            f"Across exposed pairs, Spearman correlation between structured score and Phase 7 weak grade is "
            f"{metrics['structured_score_relevance_spearman']:.3f}. This is descriptive only: exposures and behavior "
            "come from an existing ranker, so the association neither tunes the score nor establishes causal value.", "",
            "## Feature prevalence", "",
            _markdown_table(summary.round(4), max_rows=30), "",
            "## Boundaries and next evaluation", "",
            "- Content context is title-derived because body text and dedicated context fields are unavailable.",
            "- ICD/ATC expansion is bounded to supplied codes and deterministic parent/class derivation.",
            "- Negation is carried as a query guardrail but not converted into positive matching.",
            "- The intent prior is expert-rule-based and remains separate for ablation.",
            "- Extraction quality and retrieval contribution are separate questions, following CLEAR's component-evaluation principle.",
            "- Retrieval weights, temporal/query splits, BM25 integration, and ranking metrics belong to later phases.", "",
        ]
    )


def build_phase75_artifacts() -> dict[str, Path]:
    queries = pd.read_csv(LABELED_QUERIES_PATH)
    content = load_content()
    prepared_content = prepare_content_context(content)
    matrix = build_compatibility_matrix(queries, content)
    dictionary = build_feature_dictionary()
    clear_mapping = build_clear_mapping()
    summary = build_feature_summary(matrix)
    judgments = pd.read_csv(JUDGMENTS_PATH)
    diagnostics, diagnostic_metrics = build_observed_diagnostics(matrix, judgments)
    examples = build_examples(matrix)

    metrics: dict[str, Any] = {
        "methodology": "CLEAR-inspired deterministic CPU-first adaptation",
        "original_clear_task_reproduced": False,
        "queries": int(queries["query_id"].nunique()),
        "content_items": int(content["content_id"].nunique()),
        "matrix_rows": int(len(matrix)),
        "unique_query_content_pairs": int(matrix[["query_id", "content_id"]].drop_duplicates().shape[0]),
        "feature_version": "clear_inspired_v1",
        "behavior_used_to_construct_features": False,
        "behavior_used_to_choose_weights": False,
        "initial_weighting": "equal entity/context component average",
        "structured_score_min": float(matrix["structured_score"].min()),
        "structured_score_max": float(matrix["structured_score"].max()),
        "mean_structured_score": float(matrix["structured_score"].mean()),
        "pairs_with_any_entity_match": int(matrix["entity_augmented_match_count"].gt(0).sum()),
        "pairs_with_any_context_match": int(matrix["context_match_count"].gt(0).sum()),
        "pairs_with_entity_conflict": int(matrix["entity_conflict_count"].gt(0).sum()),
        "pairs_with_context_conflict": int(matrix["context_conflict_count"].gt(0).sum()),
        "queries_with_context_constraints": int(
            matrix.groupby("query_id")["context_constraint_count"].first().gt(0).sum()
        ),
        "content_context_source": "title plus publication_year/content_type metadata",
        "unobserved_context_semantics": "unknown_not_conflict",
        **diagnostic_metrics,
    }

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PHASE75_DIR.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(COMPATIBILITY_MATRIX_PATH, index=False)
    prepared_content.to_csv(CONTENT_CONTEXT_PATH, index=False)
    dictionary.to_csv(FEATURE_DICTIONARY_PATH, index=False)
    summary.to_csv(FEATURE_SUMMARY_PATH, index=False)
    clear_mapping.to_csv(CLEAR_MAPPING_PATH, index=False)
    diagnostics.to_csv(OBSERVED_DIAGNOSTICS_PATH, index=False)
    examples.to_csv(EXAMPLES_PATH, index=False)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(
        build_report(metrics, clear_mapping, summary, diagnostics), encoding="utf-8"
    )
    _plot(matrix, diagnostics)
    return {
        "compatibility_matrix": COMPATIBILITY_MATRIX_PATH,
        "content_context": CONTENT_CONTEXT_PATH,
        "feature_dictionary": FEATURE_DICTIONARY_PATH,
        "feature_summary": FEATURE_SUMMARY_PATH,
        "clear_mapping": CLEAR_MAPPING_PATH,
        "observed_diagnostics": OBSERVED_DIAGNOSTICS_PATH,
        "examples": EXAMPLES_PATH,
        "metrics": METRICS_PATH,
        "report": REPORT_PATH,
        "figure": FIGURE_PATH,
    }


if __name__ == "__main__":
    for artifact, path in build_phase75_artifacts().items():
        print(f"{artifact}: {path}")
