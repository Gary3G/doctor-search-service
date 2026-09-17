"""Phase 13: slice-based retrieval evaluation.

This phase does not tune another ranker.  It reuses frozen per-query metrics
from Phases 11 and 12, attaches transparent query-slice membership, and tests
the two Phase 13 hypotheses with paired query-level differences.

Run with ``.venv/bin/python -m src.slice_evaluation``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter, MaxNLocator
import numpy as np
import pandas as pd

from src.config import CONFIG, EXPERIMENT_LOG_PATH, FIGURES_DIR, OUTPUT_DIR
from src.intent import INTENT_METADATA_QUERIES_PATH


PHASE11_DIR = OUTPUT_DIR / "retrieval" / "phase11"
PHASE12_DIR = OUTPUT_DIR / "retrieval" / "phase12"
PHASE13_DIR = OUTPUT_DIR / "retrieval" / "phase13"
PRIMARY_METRICS = (
    "judged_fraction@10",
    "recall@10",
    "hit_rate@10",
    "mrr@10",
    "ndcg@10",
)
SYSTEM_LABELS = {
    "bm25": "BM25",
    "bm25_structured": "BM25 + structure",
    "hybrid": "Hybrid without intent",
    "hybrid_intent": "Hybrid + predicted intent",
}
SYSTEM_ORDER = tuple(SYSTEM_LABELS)
COMPARISONS = (
    ("structured_vs_bm25", "bm25", "bm25_structured"),
    ("hybrid_vs_bm25", "bm25", "hybrid"),
    ("intent_vs_hybrid", "hybrid", "hybrid_intent"),
)


def _values(value: object) -> frozenset[str]:
    """Return distinct semicolon-delimited values; repeated labels count once."""
    if pd.isna(value):
        return frozenset()
    return frozenset(
        item.strip().casefold() for item in str(value).split(";") if item.strip()
    )


def _present(series: pd.Series) -> pd.Series:
    return series.notna() & series.astype(str).str.strip().ne("")


def build_query_profiles(queries: pd.DataFrame) -> pd.DataFrame:
    """Build the auditable query-side features used to define slices."""
    required = {
        "query_id", "language", "disease_entity", "molecule_entity",
        "drug_class_entity", "intent_top_level", "intent_subtype",
        "age_group", "pregnancy_status", "year", "recency_flag",
        "dose_context_flag", "route", "renal_function_group",
        "hepatic_impairment_flag", "comparison_flag", "negation_flag",
        "prior_treatment_failure_flag",
    }
    missing = sorted(required - set(queries.columns))
    if missing:
        raise ValueError(f"Missing query columns: {missing}")
    if queries["query_id"].duplicated().any():
        raise ValueError("query_id must be unique")

    result = queries[["query_id", "language", "intent_top_level", "intent_subtype"]].copy()
    disease = queries["disease_entity"].map(_values)
    molecule = queries["molecule_entity"].map(_values)
    drug_class = queries["drug_class_entity"].map(_values)
    result["disease_count"] = disease.map(len)
    result["molecule_count"] = molecule.map(len)
    result["drug_class_count"] = drug_class.map(len)
    result["entity_count"] = [len(d | m | c) for d, m, c in zip(disease, molecule, drug_class)]
    result["has_disease"] = result["disease_count"].gt(0)
    result["has_drug"] = result["molecule_count"].gt(0) | result["drug_class_count"].gt(0)
    result["multiple_molecules"] = result["molecule_count"].gt(1)

    demographic = _present(queries["age_group"]) | _present(queries["pregnancy_status"])
    temporal = queries["year"].notna() | queries["recency_flag"].fillna(False).astype(bool)
    renal_lab = _present(queries["renal_function_group"])
    context_groups = pd.DataFrame(
        {
            "demographic_constraint": demographic,
            "year_constraint": temporal,
            "renal_lab_constraint": renal_lab,
            "dose_constraint": queries["dose_context_flag"].fillna(False).astype(bool),
            "route_constraint": _present(queries["route"]),
            "hepatic_constraint": queries["hepatic_impairment_flag"].fillna(False).astype(bool),
            "comparison_constraint": queries["comparison_flag"].fillna(False).astype(bool),
            "negation_constraint": queries["negation_flag"].fillna(False).astype(bool),
            "prior_failure_constraint": queries["prior_treatment_failure_flag"].fillna(False).astype(bool),
        },
        index=queries.index,
    )
    result["demographic_constraint"] = demographic.to_numpy()
    result["year_constraint"] = temporal.to_numpy()
    result["renal_lab_constraint"] = renal_lab.to_numpy()
    result["context_constraint_count"] = context_groups.sum(axis=1).astype(int).to_numpy()
    return result


def build_slice_tables(queries: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return long membership and a catalog that retains zero-support slices."""
    profile = build_query_profiles(queries)
    members: list[dict[str, str]] = []
    catalog: list[dict[str, Any]] = []

    def add(family: str, name: str, mask: Iterable[bool], definition: str,
            overlapping: bool = False) -> None:
        boolean = pd.Series(mask, index=profile.index).fillna(False).astype(bool)
        query_ids = profile.loc[boolean, "query_id"]
        catalog.append(
            {
                "slice_family": family,
                "slice_name": name,
                "definition": definition,
                "overlapping_within_family": overlapping,
                "global_queries": int(boolean.sum()),
            }
        )
        members.extend(
            {"query_id": query_id, "slice_family": family, "slice_name": name}
            for query_id in query_ids
        )

    add("overall", "All queries", np.ones(len(profile), dtype=bool), "All supplied queries.")
    language_labels = {"EN": "English", "ID": "Bahasa Indonesia", "MIXED": "Mixed language"}
    for code, label in language_labels.items():
        add("language", label, profile["language"].eq(code), f"language == {code}")

    add("entity_count", "Zero recognized entities", profile["entity_count"].eq(0),
        "No distinct supplied disease, molecule, or drug-class value.")
    add("entity_count", "One recognized entity", profile["entity_count"].eq(1),
        "One distinct supplied disease, molecule, or drug-class value.")
    add("entity_count", "Two or more recognized entities", profile["entity_count"].ge(2),
        "At least two distinct supplied disease, molecule, or drug-class values.")

    add("entity_composition", "Disease only", profile["has_disease"] & ~profile["has_drug"],
        "Disease metadata present and molecule/drug-class metadata absent.", True)
    add("entity_composition", "Drug only", ~profile["has_disease"] & profile["has_drug"],
        "Molecule or drug-class metadata present and disease metadata absent.", True)
    add("entity_composition", "Disease + drug", profile["has_disease"] & profile["has_drug"],
        "Both disease and molecule/drug-class metadata present.", True)
    add("entity_composition", "Multiple molecules", profile["multiple_molecules"],
        "At least two distinct semicolon-delimited molecule values; duplicates collapse.", True)
    add("entity_composition", "Single molecule", profile["molecule_count"].eq(1),
        "Exactly one distinct molecule value (diagnostic complement).", True)

    no_context = profile["context_constraint_count"].eq(0)
    multiple_context = profile["context_constraint_count"].ge(2)
    add("contextual_complexity", "No extra contextual slot", no_context,
        "No selected demographic, temporal, renal/lab, dose, route, hepatic, comparison, negation, or prior-failure constraint.", True)
    add("contextual_complexity", "Demographic constraint", profile["demographic_constraint"],
        "Age-group or pregnancy constraint.", True)
    add("contextual_complexity", "Year constraint", profile["year_constraint"],
        "Explicit year or recency flag.", True)
    add("contextual_complexity", "Renal/lab constraint", profile["renal_lab_constraint"],
        "Extracted renal-function constraint; lab-value extraction was deferred because no supported numeric lab constraints were found.", True)
    add("contextual_complexity", "Multiple constraints", multiple_context,
        "At least two selected contextual constraint groups.", True)

    add("context_constraint_count", "No constraints", no_context,
        "Exactly zero selected contextual constraint groups.")
    add("context_constraint_count", "One constraint", profile["context_constraint_count"].eq(1),
        "Exactly one selected contextual constraint group.")
    add("context_constraint_count", "Multiple constraints", multiple_context,
        "At least two selected contextual constraint groups.")

    for intent in sorted(profile["intent_top_level"].dropna().unique()):
        add("intent_top_level", str(intent), profile["intent_top_level"].eq(intent),
            f"Final Phase 3 top-level intent == {intent}")

    pharma = profile["intent_top_level"].fillna("").str.startswith("Pharmacotherapy")
    for subtype in sorted(profile.loc[pharma, "intent_subtype"].dropna().unique()):
        add("pharmacotherapy_sub_intent", str(subtype), pharma & profile["intent_subtype"].eq(subtype),
            f"Pharmacotherapy top-level intent with subtype == {subtype}")

    preferred = (
        profile["intent_top_level"].fillna("").str.startswith("Pharmacotherapy")
        | profile["intent_top_level"].eq("Evidence / Guideline Lookup")
    )
    add("intent_hypothesis_group", "Available preferred-content-type intents", preferred,
        "Available prespecified targets: Pharmacotherapy and Evidence / Guideline; Work-up and Test Interpretation are absent from the final taxonomy.")
    add("intent_hypothesis_group", "Other observed intents", ~preferred,
        "Observed intents outside the available prespecified target group.")

    membership = pd.DataFrame(members, columns=["query_id", "slice_family", "slice_name"])
    catalog_frame = pd.DataFrame(catalog)
    if membership.duplicated().any():
        raise AssertionError("Duplicate query/slice membership")
    return membership, catalog_frame


def load_primary_per_query() -> pd.DataFrame:
    """Load the frozen primary temporal validation/test per-query metrics."""
    phase11 = pd.read_csv(PHASE11_DIR / "per_query_metrics.csv.gz")
    phase12 = pd.read_csv(PHASE12_DIR / "per_query_metrics.csv.gz")
    common11 = (
        phase11["protocol"].eq("temporal")
        & phase11["split"].isin(["validation", "test"])
        & phase11["scheme"].eq("relevance_grade")
        & phase11["threshold"].eq(1)
    )
    common12 = (
        phase12["protocol"].eq("temporal")
        & phase12["split"].isin(["validation", "test"])
        & phase12["scheme"].eq("relevance_grade")
        & phase12["threshold"].eq(1)
    )
    p11 = phase11.loc[common11 & phase11["experiment"].isin(["R-B0", "R-E2", "R-E6"])].copy()
    p12 = phase12.loc[
        common12 & phase12["configuration"].isin(["without_intent", "with_predicted_hard_intent"])
    ].copy()

    parity = p11[p11["experiment"].eq("R-E6")][["query_id", "split", "ndcg@10"]].merge(
        p12[p12["configuration"].eq("without_intent")][["query_id", "split", "ndcg@10"]],
        on=["query_id", "split"], suffixes=("_phase11", "_phase12"), validate="one_to_one",
    )
    if not np.allclose(parity["ndcg@10_phase11"], parity["ndcg@10_phase12"], equal_nan=True):
        raise AssertionError("Phase 11 R-E6 and Phase 12 without-intent metrics diverge")

    mapping11 = {"R-B0": "bm25", "R-E2": "bm25_structured"}
    mapping12 = {"without_intent": "hybrid", "with_predicted_hard_intent": "hybrid_intent"}
    selected11 = p11[p11["experiment"].isin(mapping11)].assign(
        system=lambda frame: frame["experiment"].map(mapping11)
    )
    selected12 = p12.assign(system=lambda frame: frame["configuration"].map(mapping12))
    columns = ["query_id", "split", "system", "positive_pairs", "judged_pairs", "eligible", *PRIMARY_METRICS]
    result = pd.concat([selected11[columns], selected12[columns]], ignore_index=True)
    if result.duplicated(["query_id", "split", "system"]).any():
        raise AssertionError("Duplicate per-query system metrics")
    return result


def _support_flag(query_count: int, eligible_queries: int) -> str:
    if query_count == 0:
        return "empty"
    if eligible_queries == 0:
        return "no_positive_queries"
    if eligible_queries < 5:
        return "very_sparse"
    if eligible_queries < 20:
        return "sparse"
    return "adequate"


def summarize_slices(per_query: pd.DataFrame, membership: pd.DataFrame,
                     catalog: pd.DataFrame) -> pd.DataFrame:
    """Macro-average each frozen system within every declared slice."""
    rows: list[dict[str, Any]] = []
    for spec in catalog.itertuples(index=False):
        query_ids = set(
            membership.loc[
                membership["slice_family"].eq(spec.slice_family)
                & membership["slice_name"].eq(spec.slice_name), "query_id"
            ]
        )
        for split in ("validation", "test"):
            for system in SYSTEM_ORDER:
                group = per_query[
                    per_query["split"].eq(split)
                    & per_query["system"].eq(system)
                    & per_query["query_id"].isin(query_ids)
                ]
                eligible = int(group["eligible"].sum()) if len(group) else 0
                row = {
                    "slice_family": spec.slice_family,
                    "slice_name": spec.slice_name,
                    "split": split,
                    "system": system,
                    "system_label": SYSTEM_LABELS[system],
                    "global_queries": spec.global_queries,
                    "queries": len(group),
                    "eligible_queries": eligible,
                    "no_positive_queries": int(len(group) - eligible),
                    "support_flag": _support_flag(len(group), eligible),
                }
                row.update({metric: group[metric].mean() for metric in PRIMARY_METRICS})
                rows.append(row)
    return pd.DataFrame(rows)


def paired_slice_delta(baseline: pd.DataFrame, candidate: pd.DataFrame,
                       query_ids: set[str]) -> dict[str, Any]:
    """Compute a deterministic paired NDCG@10 delta inside one slice."""
    joined = baseline[baseline["query_id"].isin(query_ids)][["query_id", "ndcg@10"]].merge(
        candidate[candidate["query_id"].isin(query_ids)][["query_id", "ndcg@10"]],
        on="query_id", suffixes=("_baseline", "_candidate"), validate="one_to_one",
    ).dropna()
    if joined.empty:
        return {
            "eligible_queries": 0, "baseline_ndcg@10": np.nan,
            "candidate_ndcg@10": np.nan, "mean_delta_ndcg@10": np.nan,
            "lower_95": np.nan, "upper_95": np.nan, "improved_queries": 0,
            "worsened_queries": 0, "unchanged_queries": 0,
        }
    delta = joined["ndcg@10_candidate"] - joined["ndcg@10_baseline"]
    rng = np.random.default_rng(CONFIG.random_seed)
    samples = rng.choice(delta.to_numpy(), size=(2000, len(delta)), replace=True).mean(axis=1)
    lower, upper = np.quantile(samples, [0.025, 0.975])
    return {
        "eligible_queries": len(delta),
        "baseline_ndcg@10": joined["ndcg@10_baseline"].mean(),
        "candidate_ndcg@10": joined["ndcg@10_candidate"].mean(),
        "mean_delta_ndcg@10": delta.mean(),
        "lower_95": float(lower),
        "upper_95": float(upper),
        "improved_queries": int(delta.gt(0).sum()),
        "worsened_queries": int(delta.lt(0).sum()),
        "unchanged_queries": int(delta.eq(0).sum()),
    }


def compare_slices(per_query: pd.DataFrame, membership: pd.DataFrame,
                   catalog: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for spec in catalog.itertuples(index=False):
        query_ids = set(
            membership.loc[
                membership["slice_family"].eq(spec.slice_family)
                & membership["slice_name"].eq(spec.slice_name), "query_id"
            ]
        )
        for split in ("validation", "test"):
            split_data = per_query[per_query["split"].eq(split)]
            for comparison, baseline_name, candidate_name in COMPARISONS:
                result = paired_slice_delta(
                    split_data[split_data["system"].eq(baseline_name)],
                    split_data[split_data["system"].eq(candidate_name)],
                    query_ids,
                )
                rows.append(
                    {
                        "slice_family": spec.slice_family,
                        "slice_name": spec.slice_name,
                        "split": split,
                        "comparison": comparison,
                        "baseline": baseline_name,
                        "candidate": candidate_name,
                        "global_queries": spec.global_queries,
                        **result,
                    }
                )
    return pd.DataFrame(rows)


def build_hypothesis_table(comparisons: pd.DataFrame) -> pd.DataFrame:
    """Extract the prespecified Phase 13 hypothesis contrasts."""
    specs = [
        ("structure_vs_context_complexity", "structured_vs_bm25", "context_constraint_count",
         ["No constraints", "One constraint", "Multiple constraints"]),
        ("structure_for_multiple_molecules", "structured_vs_bm25", "entity_composition",
         ["Single molecule", "Multiple molecules"]),
        ("intent_for_preferred_content_types", "intent_vs_hybrid", "intent_hypothesis_group",
         ["Available preferred-content-type intents", "Other observed intents"]),
    ]
    rows: list[pd.DataFrame] = []
    test = comparisons[comparisons["split"].eq("test")]
    for hypothesis, comparison, family, names in specs:
        selected = test[
            test["comparison"].eq(comparison)
            & test["slice_family"].eq(family)
            & test["slice_name"].isin(names)
        ].copy()
        selected.insert(0, "hypothesis", hypothesis)
        selected["direction_positive"] = selected["mean_delta_ndcg@10"].gt(0)
        selected["interval_excludes_zero"] = (
            selected["lower_95"].gt(0) | selected["upper_95"].lt(0)
        )
        rows.append(selected)
    return pd.concat(rows, ignore_index=True)


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    view = frame.fillna("—").astype(str)
    header = "| " + " | ".join(view.columns) + " |"
    divider = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    body = ["| " + " | ".join(row) + " |" for row in view.to_numpy()]
    return "\n".join([header, divider, *body])


def _report_table(metrics: pd.DataFrame, family: str) -> pd.DataFrame:
    subset = metrics[metrics["split"].eq("test") & metrics["slice_family"].eq(family)]
    support = subset[subset["system"].eq("bm25")][
        ["slice_name", "queries", "eligible_queries", "support_flag"]
    ]
    values = subset.pivot(index="slice_name", columns="system", values="ndcg@10").reset_index()
    result = support.merge(values, on="slice_name", how="left")
    for system in SYSTEM_ORDER:
        if system not in result:
            result[system] = np.nan
    result = result[["slice_name", "queries", "eligible_queries", "support_flag", *SYSTEM_ORDER]]
    result = result.rename(columns={system: SYSTEM_LABELS[system] for system in SYSTEM_ORDER})
    for label in SYSTEM_LABELS.values():
        result[label] = result[label].map(lambda value: "—" if pd.isna(value) else f"{value:.5f}")
    return result


def _make_figure(comparisons: pd.DataFrame, path: Path) -> None:
    test = comparisons[comparisons["split"].eq("test")]
    context = test[
        test["comparison"].eq("structured_vs_bm25")
        & test["slice_family"].eq("context_constraint_count")
    ]
    intent = test[
        test["comparison"].eq("intent_vs_hybrid")
        & test["slice_family"].eq("intent_top_level")
    ].sort_values("mean_delta_ndcg@10").copy()
    intent["figure_label"] = intent["slice_name"].replace(
        {
            "Management / Treatment; Epidemiology / Prognosis": "Management + epidemiology",
            "Pharmacotherapy; Epidemiology / Prognosis": "Pharmacotherapy + epidemiology",
            "Evidence / Guideline Lookup": "Evidence / guideline",
            "New dataset-specific class": "Mechanism / background",
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    axes[0].bar(context["slice_name"], context["mean_delta_ndcg@10"], color="#4472C4")
    axes[0].axhline(0, color="black", linewidth=0.8)
    axes[0].set_title("Structure − BM25 by context count")
    axes[0].set_ylabel("Mean paired Δ NDCG@10")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].barh(intent["figure_label"], intent["mean_delta_ndcg@10"], color="#70AD47")
    axes[1].axvline(0, color="black", linewidth=0.8)
    axes[1].set_title("Predicted intent − no intent")
    axes[1].set_xlabel("Mean paired Δ NDCG@10")
    axes[1].xaxis.set_major_locator(MaxNLocator(nbins=5))
    axes[1].xaxis.set_major_formatter(FormatStrFormatter("%+.3f"))
    fig.suptitle("Phase 13 temporal-test slice effects (behavior-derived judgments)")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_report(output_dir: Path = PHASE13_DIR) -> None:
    metrics = pd.read_csv(output_dir / "slice_metrics.csv")
    comparisons = pd.read_csv(output_dir / "slice_comparisons.csv")
    hypotheses = pd.read_csv(output_dir / "hypothesis_tests.csv")
    catalog = pd.read_csv(output_dir / "slice_catalog.csv")

    context_h = hypotheses[hypotheses["hypothesis"].eq("structure_vs_context_complexity")]
    context_delta = dict(zip(context_h["slice_name"], context_h["mean_delta_ndcg@10"]))
    intent_h = hypotheses[hypotheses["hypothesis"].eq("intent_for_preferred_content_types")]
    intent_delta = dict(zip(intent_h["slice_name"], intent_h["mean_delta_ndcg@10"]))
    entity_empty = catalog[
        catalog["slice_family"].isin(["entity_count", "entity_composition"])
        & catalog["global_queries"].eq(0)
    ]["slice_name"].tolist()
    interval_count = int(hypotheses["interval_excludes_zero"].sum())

    systems = pd.DataFrame(
        [
            ["BM25", "R-B0", "BM25 only"],
            ["BM25 + structure", "R-E2", "BM25 + entity compatibility + contextual compatibility"],
            ["Hybrid without intent", "R-E6", "BM25 + dense similarity + entity compatibility + contextual compatibility"],
            ["Hybrid + predicted intent", "Phase 12 runtime model", "R-E6 + 0.25 × predicted intent/content-type compatibility"],
        ],
        columns=["Phase 13 label", "Frozen source", "Scoring components"],
    )
    sections = [
        "# Phase 13 — Slice-Based Evaluation",
        "## Approach",
        (
            "Phase 13 is a diagnostic evaluation of frozen Phase 11 and Phase 12 rankings; no model is trained, retuned, "
            "or selected here. The primary analysis uses the temporal test split and behavior-derived "
            "`relevance_grade >= 1`. Results are macro-averaged across eligible queries, and unjudged documents receive "
            "zero computational gain without being interpreted as clinically irrelevant."
        ),
        _markdown_table(systems),
        (
            "The analysis covers language, entity count and composition, contextual complexity, top-level intent, and "
            "Pharmacotherapy sub-intent. Required overlapping context slices are reported directly; an additional exclusive "
            "zero/one/multiple-constraint view supports the complexity trend test. The structure hypothesis uses R-E2 minus "
            "R-B0, which isolates entity/context structure without adding dense retrieval. The intent hypothesis uses the "
            "predicted-intent model minus R-E6. Paired differences use 2,000 deterministic query bootstrap resamples."
        ),
        "## Key Findings",
        (
            "The central result is heterogeneity: improvements occur in particular slices rather than across all queries. "
            "Structured retrieval does not improve monotonically with contextual complexity. R-E2 minus BM25 changes test "
            f"NDCG@10 by {context_delta.get('No constraints', np.nan):+.5f} for no constraints, "
            f"{context_delta.get('One constraint', np.nan):+.5f} for one, and "
            f"{context_delta.get('Multiple constraints', np.nan):+.5f} for multiple constraints. The high-complexity point "
            "estimate is positive but is based on only 12 eligible queries."
        ),
        (
            "Predicted intent is most useful where intent implies a preferred content type. It changes test NDCG@10 by "
            f"{intent_delta.get('Available preferred-content-type intents', np.nan):+.5f} for the available prespecified "
            "Pharmacotherapy and Evidence / Guideline group, versus "
            f"{intent_delta.get('Other observed intents', np.nan):+.5f} for other observed intents. Pharmacotherapy drives "
            "this result: its NDCG@10 rises from 0.00516 to 0.02318, but only 5 of 48 eligible queries improve. The largest "
            "sub-intent movement is Interaction / Combination, followed by Dosing / Administration."
        ),
        "**Language slices**",
        _markdown_table(_report_table(metrics, "language")),
        "**Entity-complexity slices**",
        _markdown_table(_report_table(metrics, "entity_count")),
        _markdown_table(_report_table(metrics, "entity_composition")),
        "**Contextual-complexity slices**",
        _markdown_table(_report_table(metrics, "contextual_complexity")),
        "The exclusive context-count view used for the trend test is:",
        _markdown_table(_report_table(metrics, "context_constraint_count")),
        "**Top-level intent slices**",
        _markdown_table(_report_table(metrics, "intent_top_level")),
        "**Pharmacotherapy sub-intents**",
        _markdown_table(_report_table(metrics, "pharmacotherapy_sub_intent")),
        "## Honest Evaluation",
        (
            "These results do not establish a globally superior retrieval model. Across the prespecified hypothesis rows, "
            f"only {interval_count} of {len(hypotheses)} paired bootstrap intervals exclude zero. The intervals are "
            "uncorrected for multiple slice comparisons and are not cluster-robust. Many apparent gains come from one or "
            "two changed queries, while most eligible queries have identical NDCG@10 under both systems."
        ),
        (
            "The entity analysis is not identifiable from this sample: every query has supplied disease and drug metadata, "
            "so the following required slices are empty: " + ", ".join(entity_empty) + ". The multiple-molecule slice has "
            "only nine eligible test queries. Context categories overlap, the renal/lab slice contains only three eligible "
            "queries and represents renal constraints rather than numeric lab values, and Work-up and Test Interpretation "
            "are absent from the frozen intent taxonomy."
        ),
        (
            "Relevance is inferred from exposed-item behavior rather than clinician judgments, so the evaluation inherits "
            "exposure, position, and engagement bias. Slice membership inherits supplied metadata and deterministic extraction "
            "errors. Top-level intents are assisted weak references even though runtime retrieval uses predicted intent. The "
            "test split was inspected in earlier phases, making all test results descriptive rather than pristine confirmation. "
            "The defensible decision is to retain predicted intent as an intent-specific research signal, not to claim a "
            "universal ranking improvement."
        ),
        "## What I Would Do Differently",
        (
            "1. Build clinician-adjudicated pooled judgments from the top results of all four systems, including explicit "
            "irrelevance and graded clinical usefulness, rather than treating unexposed content as zero gain.\n"
            "2. Create a genuinely untouched confirmation set and preregister the slice definitions, primary contrasts, and "
            "multiplicity correction before examining results.\n"
            "3. Collect or construct more queries with zero, one, disease-only, drug-only, multi-entity, renal/lab, and multiple "
            "contextual constraints so the required complexity hypotheses are actually identifiable.\n"
            "4. Evaluate intent and structure with calibrated, provenance-aware features and document-section evidence instead "
            "of coarse title and content-type compatibility.\n"
            "5. Report hierarchical or cluster-robust uncertainty and require both a minimum slice size and a minimum number of "
            "changed queries before interpreting a slice effect."
        ),
        (
            "Artifacts: `query_slice_membership.csv`, `slice_catalog.csv`, `slice_metrics.csv`, "
            "`slice_comparisons.csv`, `hypothesis_tests.csv`, `manifest.json`, and "
            "`outputs/figures/phase13_slice_effects.png`."
        ),
    ]
    (Path("write_up") / "phase13_summary.md").write_text("\n\n".join(sections) + "\n")


def _sha256(paths: list[Path]) -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _update_experiment_log(hypotheses: pd.DataFrame) -> None:
    log = pd.read_csv(EXPERIMENT_LOG_PATH)
    context = hypotheses[hypotheses["hypothesis"].eq("structure_vs_context_complexity")]
    context_result = "; ".join(
        f"{row['slice_name']}={row['mean_delta_ndcg@10']:+.5f} (n={row['eligible_queries']})"
        for _, row in context.iterrows()
    )
    intent = hypotheses[hypotheses["hypothesis"].eq("intent_for_preferred_content_types")]
    intent_result = "; ".join(
        f"{row['slice_name']}={row['mean_delta_ndcg@10']:+.5f} (n={row['eligible_queries']})"
        for _, row in intent.iterrows()
    )
    additions = [
        {
            "experiment": "R-SLICE-STRUCTURE",
            "hypothesis": "structured query decomposition helps more as compositional complexity increases",
            "method": "paired R-E2 minus R-B0 temporal-test NDCG@10 by exclusive context-count slice",
            "primary_metric": "slice delta NDCG@10",
            "result": context_result,
            "decision": "not supported; no monotonic gain and sparse high-complexity slice",
        },
        {
            "experiment": "R-SLICE-INTENT",
            "hypothesis": "intent helps most where information need implies a preferred content type",
            "method": "paired predicted-intent minus R-E6 temporal-test NDCG@10 by intent group",
            "primary_metric": "slice delta NDCG@10",
            "result": intent_result,
            "decision": "directionally consistent but intent-specific; not a global claim",
        },
    ]
    for row in additions:
        log = log[~log["experiment"].eq(row["experiment"])]
        log = pd.concat([log, pd.DataFrame([row])], ignore_index=True)
    log.to_csv(EXPERIMENT_LOG_PATH, index=False)


def build_phase13_artifacts(output_dir: Path = PHASE13_DIR,
                            update_experiment_log: bool = True) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    queries = pd.read_csv(INTENT_METADATA_QUERIES_PATH).sort_values("query_id").reset_index(drop=True)
    membership, catalog = build_slice_tables(queries)
    per_query = load_primary_per_query()
    metrics = summarize_slices(per_query, membership, catalog)
    comparisons = compare_slices(per_query, membership, catalog)
    hypotheses = build_hypothesis_table(comparisons)

    membership.to_csv(output_dir / "query_slice_membership.csv", index=False)
    catalog.to_csv(output_dir / "slice_catalog.csv", index=False)
    metrics.to_csv(output_dir / "slice_metrics.csv", index=False)
    comparisons.to_csv(output_dir / "slice_comparisons.csv", index=False)
    hypotheses.to_csv(output_dir / "hypothesis_tests.csv", index=False)
    figure_path = FIGURES_DIR / "phase13_slice_effects.png"
    _make_figure(comparisons, figure_path)

    context = hypotheses[hypotheses["hypothesis"].eq("structure_vs_context_complexity")]
    ordered = context.set_index("slice_name")["mean_delta_ndcg@10"].reindex(
        ["No constraints", "One constraint", "Multiple constraints"]
    )
    complexity_supported = bool(ordered.notna().all() and ordered.is_monotonic_increasing)
    manifest = {
        "phase": 13,
        "analysis_type": "diagnostic slice evaluation; no model tuning or selection",
        "primary_protocol": "temporal test; relevance_grade >= 1",
        "systems": SYSTEM_LABELS,
        "hypotheses": {
            "complexity_benefit_supported": complexity_supported,
            "intent_effect_interpretation": "intent-specific, not global",
        },
        "entity_slice_warning": "All supplied queries contain disease and drug metadata; zero/one and disease-only/drug-only slices have zero support.",
        "context_definition": "Counts nine selected conceptual groups; year and recency share one temporal group, and age/pregnancy share one demographic group.",
        "bootstrap": {"resamples": 2000, "seed": CONFIG.random_seed, "unit": "query"},
        "test_status": "descriptive; test data were inspected in earlier phases",
        "limitations": [
            "Behavior-derived relevance is exposure- and position-biased and is not clinician adjudication.",
            "Unjudged documents receive zero computational gain but are not clinical negatives.",
            "Slice labels inherit supplied metadata and deterministic extraction errors.",
            "Intervals are uncorrected for multiple comparisons and are not cluster-robust.",
            "Sparse and overlapping slices limit between-slice inference.",
        ],
        "sha256": _sha256([
            INTENT_METADATA_QUERIES_PATH,
            PHASE11_DIR / "per_query_metrics.csv.gz",
            PHASE12_DIR / "per_query_metrics.csv.gz",
            Path(__file__),
        ]),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if update_experiment_log:
        _update_experiment_log(hypotheses)
    write_report(output_dir)
    return {
        "output_dir": str(output_dir),
        "slice_definitions": len(catalog),
        "membership_rows": len(membership),
        "complexity_benefit_supported": complexity_supported,
        "figure": str(figure_path),
    }


if __name__ == "__main__":
    print(json.dumps(build_phase13_artifacts(), indent=2))
