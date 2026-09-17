"""Per-value entity and exact tri-state context retrieval experiment.

This replaces dimension-level ``any overlap`` with per-value coverage while
preserving unknown-neutral penalties. Weight selection uses temporal validation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import CONTENT_PATH, EXPERIMENT_LOG_PATH, QUERIES_PATH
from src.context_repair_experiment import OUTPUT as REPAIR_OUTPUT
from src.evaluation import evaluate_rankings, summarize_metrics
from src.evaluation_split import SPLIT_DIR
from src.incremental_retrieval import PHASE11_DIR, build_signals, paired_delta, rank_scores
from src.intent_signed_retrieval import (
    WEIGHTS,
    intent_signed_scores,
    select_trial,
    validation_grid,
)
from src.repaired_signed_retrieval import make_repaired_signals
from src.structured_compatibility import normalized_values
from src.topic_boost_retrieval import table


OUTPUT = PHASE11_DIR.parent / "value_aware_retrieval"
REPAIRED_QUERIES = REPAIR_OUTPUT / "queries_repaired.csv"
REPAIRED_CONTENT = REPAIR_OUTPUT / "content_repaired.csv"
REPAIRED_MATRIX = REPAIR_OUTPUT / "compatibility_repaired.csv.gz"
ENTITY_DIMENSIONS = (
    ("disease", "icd10_code", True),
    ("molecule", "atc_code", True),
    ("drug_class", "atc_class", True),
    ("therapeutic_area", "therapeutic_area", False),
)


def canonical_values(value: object, code: bool) -> frozenset[str]:
    values = normalized_values(value)
    if code:
        return frozenset(item.upper().replace(" ", "") for item in values)
    return values


def build_value_entity_signals(
    queries: pd.DataFrame, content: pd.DataFrame
) -> tuple[dict[str, np.ndarray], pd.DataFrame]:
    """Compute macro per-dimension value recall, precision, and disagreement.

    A populated document dimension makes unmatched requested values explicit
    missing evidence. An empty document dimension is unknown and receives no
    penalty. Symmetric disagreement is one minus Jaccard similarity.
    """
    shape = (len(queries), len(content))
    names = (
        "requested_recall",
        "requested_missing",
        "document_precision",
        "document_extra",
        "symmetric_f1",
        "symmetric_disagreement",
        "unknown_rate",
    )
    arrays = {name: np.zeros(shape, dtype=float) for name in names}
    query_sets = {
        dimension: [canonical_values(value, code) for value in queries[column]]
        for dimension, column, code in ENTITY_DIMENSIONS
    }
    content_sets = {
        dimension: [canonical_values(value, code) for value in content[column]]
        for dimension, column, code in ENTITY_DIMENSIONS
    }
    for query_index in range(shape[0]):
        for content_index in range(shape[1]):
            values = {name: [] for name in names}
            for dimension, _, _ in ENTITY_DIMENSIONS:
                requested = query_sets[dimension][query_index]
                if not requested:
                    continue
                observed = content_sets[dimension][content_index]
                intersection = len(requested & observed)
                recall = intersection / len(requested)
                values["requested_recall"].append(recall)
                if observed:
                    precision = intersection / len(observed)
                    union = len(requested | observed)
                    f1 = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
                    values["requested_missing"].append(1 - recall)
                    values["document_precision"].append(precision)
                    values["document_extra"].append(1 - precision)
                    values["symmetric_f1"].append(f1)
                    values["symmetric_disagreement"].append(1 - intersection / union)
                    values["unknown_rate"].append(0.0)
                else:
                    values["requested_missing"].append(0.0)
                    values["document_precision"].append(0.0)
                    values["document_extra"].append(0.0)
                    values["symmetric_f1"].append(0.0)
                    values["symmetric_disagreement"].append(0.0)
                    values["unknown_rate"].append(1.0)
            for name in names:
                arrays[name][query_index, content_index] = (
                    float(np.mean(values[name])) if values[name] else 0.0
                )
    audit = pd.DataFrame(
        [
            {
                "feature": name,
                "nonzero_pairs": int(np.count_nonzero(values)),
                "mean": float(values.mean()),
                "maximum": float(values.max()),
            }
            for name, values in arrays.items()
        ]
    )
    return arrays, audit


def build_exact_context_signals(
    queries: pd.DataFrame, content: pd.DataFrame
) -> tuple[dict[str, np.ndarray], pd.DataFrame]:
    """Compare context slots as match, explicit conflict, or unknown."""
    shape = (len(queries), len(content))
    match = np.zeros(shape, dtype=float)
    conflict = np.zeros(shape, dtype=float)
    unknown = np.zeros(shape, dtype=float)
    latest_year = int(content["publication_year"].max())
    scalar_specs = (
        ("age_group", "content_age_group"),
        ("pregnancy_status", "content_pregnancy_status"),
        ("route", "content_route"),
        ("renal_function_group", "content_renal_function_group"),
    )
    flag_specs = (
        ("dose_context_flag", "content_dose_context"),
        ("hepatic_impairment_flag", "content_hepatic_context"),
        ("comparison_flag", "content_comparison_context"),
        ("prior_treatment_failure_flag", "content_prior_failure_context"),
    )
    for query_index, query in queries.iterrows():
        for content_index, document in content.iterrows():
            outcomes: list[str] = []
            for query_column, content_column in scalar_specs:
                query_value = query[query_column]
                if pd.isna(query_value):
                    continue
                content_value = document[content_column]
                if pd.isna(content_value):
                    outcomes.append("unknown")
                elif query_value == content_value:
                    outcomes.append("match")
                else:
                    outcomes.append("conflict")
            if pd.notna(query["year"]):
                outcomes.append(
                    "match"
                    if float(query["year"]) == float(document["publication_year"])
                    else "conflict"
                )
            if bool(query["recency_flag"]):
                year = int(document["publication_year"])
                if year >= latest_year - 1:
                    outcomes.append("match")
                elif year < latest_year - 2:
                    outcomes.append("conflict")
                else:
                    outcomes.append("unknown")
            for query_column, content_column in flag_specs:
                if bool(query[query_column]):
                    outcomes.append("match" if bool(document[content_column]) else "unknown")
            if outcomes:
                denominator = len(outcomes)
                match[query_index, content_index] = outcomes.count("match") / denominator
                conflict[query_index, content_index] = outcomes.count("conflict") / denominator
                unknown[query_index, content_index] = outcomes.count("unknown") / denominator
    signals = {"context_bonus": match, "context_penalty": conflict, "context_unknown": unknown}
    audit = pd.DataFrame(
        [
            {
                "feature": name,
                "nonzero_pairs": int(np.count_nonzero(values)),
                "mean": float(values.mean()),
                "maximum": float(values.max()),
            }
            for name, values in signals.items()
        ]
    )
    return signals, audit


def selected_configurations(trials: pd.DataFrame) -> dict[str, tuple[float, ...]]:
    zero_signed = np.logical_and.reduce([trials[column].eq(0) for column in WEIGHTS[:4]])
    all_nonzero = np.logical_and.reduce([trials[column].gt(0) for column in WEIGHTS])
    signed_intent = trials[trials["intent_bonus"].gt(0) & ~zero_signed]
    return {
        "hybrid": (0.0, 0.0, 0.0, 0.0, 0.0),
        "selected_signed_intent": tuple(float(select_trial(signed_intent)[column]) for column in WEIGHTS),
        "selected_all_terms": tuple(float(select_trial(trials[all_nonzero])[column]) for column in WEIGHTS),
        "frozen_all_terms": (0.2, 0.2, 0.05, 0.05, 0.5),
        "r_e7_style": (0.5, 0.0, 0.5, 0.0, 0.5),
    }


def run(output_dir: Path = OUTPUT) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    queries = pd.read_csv(QUERIES_PATH).sort_values("query_id").reset_index(drop=True)
    content = pd.read_csv(CONTENT_PATH).sort_values("content_id").reset_index(drop=True)
    repaired_queries = pd.read_csv(REPAIRED_QUERIES).sort_values("query_id").reset_index(drop=True)
    repaired_content = pd.read_csv(REPAIRED_CONTENT).sort_values("content_id").reset_index(drop=True)
    repaired_pairs = pd.read_csv(REPAIRED_MATRIX)
    base, legacy_pairs, runtime, caches = build_signals(queries, content)
    hybrid = (base["bm25"] + base["dense"]) / 2
    intent = base["intent"]
    expected = pd.MultiIndex.from_product(
        [queries["query_id"], content["content_id"]], names=["query_id", "content_id"]
    )
    repaired_pairs = repaired_pairs.set_index(["query_id", "content_id"]).reindex(expected).reset_index()
    current_signed, current_audit = make_repaired_signals(
        base, repaired_pairs, repaired_queries, repaired_content, hybrid.shape
    )
    entity, entity_audit = build_value_entity_signals(queries, content)
    exact_context, context_audit = build_exact_context_signals(repaired_queries, repaired_content)
    modes = {
        "requested_exact": {
            "entity_bonus": entity["requested_recall"],
            "entity_penalty": entity["requested_missing"],
            "context_bonus": exact_context["context_bonus"],
            "context_penalty": exact_context["context_penalty"],
        },
        "symmetric_exact": {
            "entity_bonus": entity["symmetric_f1"],
            "entity_penalty": entity["symmetric_disagreement"],
            "context_bonus": exact_context["context_bonus"],
            "context_penalty": exact_context["context_penalty"],
        },
    }
    audits = pd.concat(
        [
            current_audit.assign(group="current_repaired"),
            entity_audit.assign(group="value_entity"),
            context_audit.assign(group="exact_context"),
        ],
        ignore_index=True,
    )
    audits.to_csv(output_dir / "feature_audit.csv", index=False)
    changed = pd.DataFrame(
        [
            {
                "comparison": "requested_recall_vs_dimension_coverage",
                "changed_pairs": int(
                    np.count_nonzero(
                        np.abs(entity["requested_recall"] - current_signed["entity_bonus"]) > 1e-12
                    )
                ),
                "maximum_absolute_change": float(
                    np.max(np.abs(entity["requested_recall"] - current_signed["entity_bonus"]))
                ),
            },
            {
                "comparison": "exact_context_vs_repaired_context",
                "changed_pairs": int(
                    np.count_nonzero(
                        np.abs(exact_context["context_bonus"] - current_signed["context_bonus"]) > 1e-12
                    )
                ),
                "maximum_absolute_change": float(
                    np.max(np.abs(exact_context["context_bonus"] - current_signed["context_bonus"]))
                ),
            },
        ]
    )
    changed.to_csv(output_dir / "feature_changes.csv", index=False)

    validation_path = SPLIT_DIR / "temporal_validation_judgments.csv"
    validation = pd.read_csv(validation_path)
    configurations: dict[str, tuple[float, ...]] = {}
    trial_frames = []
    for mode, signals in modes.items():
        trials = validation_grid(hybrid, signals, intent, queries, content, validation)
        trial_frames.append(trials.assign(mode=mode))
        configurations.update(
            {f"{mode}:{name}": weights for name, weights in selected_configurations(trials).items()}
        )
    # Frozen controls isolate representation changes without retuning.
    controls = {
        "current:frozen_all_terms": (0.2, 0.2, 0.05, 0.05, 0.5),
        "current:r_e7_equivalent": (0.5, 0.0, 0.5, 0.0, 0.5),
    }
    configurations.update(controls)
    pd.concat(trial_frames, ignore_index=True).to_csv(output_dir / "validation_grid.csv", index=False)
    pd.DataFrame(
        [{"experiment": name, **dict(zip(WEIGHTS, weights))} for name, weights in configurations.items()]
    ).to_csv(output_dir / "configurations.csv", index=False)

    rankings: dict[str, pd.DataFrame] = {}
    for name, weights in configurations.items():
        mode = name.split(":", 1)[0]
        signals = current_signed if mode == "current" else modes[mode]
        scores = intent_signed_scores(hybrid, signals, intent, weights)
        rankings[name] = rank_scores(scores, queries["query_id"], content["content_id"])
    frozen_weights = (0.2, 0.2, 0.05, 0.05, 0.5)
    representation_ablations = {
        "ablation:requested_current_context": {
            "entity_bonus": entity["requested_recall"],
            "entity_penalty": entity["requested_missing"],
            "context_bonus": current_signed["context_bonus"],
            "context_penalty": current_signed["context_penalty"],
        },
        "ablation:symmetric_current_context": {
            "entity_bonus": entity["symmetric_f1"],
            "entity_penalty": entity["symmetric_disagreement"],
            "context_bonus": current_signed["context_bonus"],
            "context_penalty": current_signed["context_penalty"],
        },
        "ablation:dimension_exact_context": {
            "entity_bonus": current_signed["entity_bonus"],
            "entity_penalty": current_signed["entity_penalty"],
            "context_bonus": exact_context["context_bonus"],
            "context_penalty": exact_context["context_penalty"],
        },
    }
    for name, signals in representation_ablations.items():
        scores = intent_signed_scores(hybrid, signals, intent, frozen_weights)
        rankings[name] = rank_scores(scores, queries["query_id"], content["content_id"])
    phase11_rankings_path = PHASE11_DIR / "rankings.csv.gz"
    phase11_rankings = pd.read_csv(phase11_rankings_path)
    for source, target in (("R-E4", "baseline:hybrid"), ("R-E7", "baseline:r_e7")):
        rankings[target] = phase11_rankings[
            phase11_rankings["experiment"].eq(source)
        ][["query_id", "content_id", "rank", "score"]].reset_index(drop=True)
    pd.concat(
        [frame.assign(experiment=name) for name, frame in rankings.items()], ignore_index=True
    ).to_csv(output_dir / "rankings.csv.gz", index=False)

    metadata = legacy_pairs.groupby("query_id", sort=True).first()[
        ["query_language", "query_intent", "context_constraint_count"]
    ].reset_index()
    metadata["has_context"] = metadata["context_constraint_count"].gt(0)
    multiple_values = np.logical_or.reduce(
        [
            queries[column].fillna("").astype(str).str.split(";").map(len).gt(1)
            for _, column, _ in ENTITY_DIMENSIONS
        ]
    )
    metadata["multiple_entity_values"] = metadata["query_id"].map(
        dict(zip(queries["query_id"], multiple_values))
    )
    summaries: list[dict[str, object]] = []
    details: list[pd.DataFrame] = []
    comparisons: list[dict[str, object]] = []
    slices: list[dict[str, object]] = []
    inputs = [
        CONTENT_PATH,
        QUERIES_PATH,
        REPAIRED_QUERIES,
        REPAIRED_CONTENT,
        REPAIRED_MATRIX,
        phase11_rankings_path,
        *caches,
    ]
    for protocol in ("temporal", "query", "query_dedup"):
        for split in ("validation", "test"):
            path = SPLIT_DIR / f"{protocol}_{split}_judgments.csv"
            inputs.append(path)
            judgments = pd.read_csv(path)
            primary: dict[str, pd.DataFrame] = {}
            for name, ranks in rankings.items():
                for scheme, threshold in (
                    ("relevance_grade", 1),
                    ("conservative_relevance_grade", 1),
                    ("event_hierarchy_relevance_grade", 1),
                    ("relevance_grade", 2),
                ):
                    tags = dict(
                        protocol=protocol,
                        split=split,
                        experiment=name,
                        scheme=scheme,
                        threshold=threshold,
                    )
                    per_query = evaluate_rankings(ranks, judgments, scheme, threshold)
                    summaries.append(tags | summarize_metrics(per_query))
                    if scheme == "relevance_grade" and threshold == 1:
                        primary[name] = per_query
                        details.append(per_query.assign(**tags))
                        enriched = per_query.merge(metadata, on="query_id", validate="one_to_one")
                        for dimension in (
                            "query_language",
                            "query_intent",
                            "has_context",
                            "multiple_entity_values",
                        ):
                            for value, group in enriched.groupby(dimension, dropna=False):
                                slices.append(
                                    tags
                                    | {"dimension": dimension, "value": value}
                                    | summarize_metrics(group)
                                )
            references = (
                "baseline:hybrid",
                "baseline:r_e7",
                "current:frozen_all_terms",
                "current:r_e7_equivalent",
            )
            for candidate in rankings:
                if candidate.startswith(("current:", "baseline:")):
                    continue
                for reference in references:
                    delta = paired_delta(primary[reference], primary[candidate])
                    difference = (
                        primary[candidate].set_index("query_id")["ndcg@10"]
                        - primary[reference].set_index("query_id")["ndcg@10"]
                    )
                    comparisons.append(
                        dict(
                            protocol=protocol,
                            split=split,
                            candidate=candidate,
                            reference=reference,
                            delta_ndcg=delta["delta_vs_full"],
                            lower=delta["lower"],
                            upper=delta["upper"],
                            positive_queries=delta["positive_queries"],
                            improved=int((difference > 0).sum()),
                            worsened=int((difference < 0).sum()),
                            unchanged=int((difference == 0).sum()),
                        )
                    )
    summary = pd.DataFrame(summaries)
    comparison = pd.DataFrame(comparisons)
    summary.to_csv(output_dir / "metrics.csv", index=False)
    comparison.to_csv(output_dir / "paired_comparisons.csv", index=False)
    pd.concat(details, ignore_index=True).to_csv(output_dir / "per_query_metrics.csv.gz", index=False)
    pd.DataFrame(slices).to_csv(output_dir / "slices.csv", index=False)

    manifest = {
        "entity_representation": {
            "requested_exact": "macro mean of per-dimension requested-value recall; unmatched requested values penalized only when document dimension is populated",
            "symmetric_exact": "macro mean of per-dimension entity F1; penalty is one minus Jaccard when document dimension is populated",
            "canonical_fields": [column for _, column, _ in ENTITY_DIMENSIONS],
            "unknown": "empty document dimension gives zero bonus and zero penalty",
        },
        "context_representation": "exact tri-state match/conflict/unknown for scalar slots; absence of Boolean title evidence remains unknown",
        "formula": "hybrid + entity_bonus*value_match - entity_penalty*value_disagreement + context_bonus*exact_context_match - context_penalty*explicit_context_conflict + intent_bonus*intent_match",
        "validation_trials_per_mode": len(trial_frames[0]),
        "configurations": configurations,
        "feature_changes": changed.to_dict(orient="records"),
        "limitations": [
            "codes are canonicalized but no new synonym ontology or fuzzy matching is introduced",
            "molecule and drug-class evidence remain correlated",
            "context has no native multi-value fields and title absence remains unknown",
            "behavioral labels are sparse and sometimes off-topic",
            "test results are exploratory after previous inspection",
        ],
        **runtime,
        "sha256": {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in inputs
            + [Path(__file__), Path("src/intent_signed_retrieval.py"), Path("src/evaluation.py")]
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    primary = summary.query(
        "protocol == 'temporal' and scheme == 'relevance_grade' and threshold == 1"
    )
    view = primary.pivot(
        index="experiment", columns="split", values=["ndcg@10", "recall@10", "mrr@10"]
    )
    view.columns = [" ".join(column) for column in view.columns]
    report = "\n\n".join(
        [
            "# Per-value entity and exact-context retrieval",
            "Run `.venv/bin/python -m src.value_aware_retrieval`. This experiment distinguishes partial multi-entity matches from complete matches. It also compares exact tri-state context evidence: match, explicit conflict, and unknown.",
            "For a query requesting Losartan and Empagliflozin, a Losartan-only document now receives molecule recall 0.5 instead of a full molecule-dimension match. Empty document evidence stays unknown and receives no penalty. The symmetric variant also uses document precision through per-dimension F1 and one-minus-Jaccard disagreement.",
            "## Feature changes",
            table(changed),
            "## Configurations",
            table(pd.read_csv(output_dir / "configurations.csv")),
            "## Temporal validation and test",
            table(view.reset_index().round(5)),
            "## Paired temporal-test comparisons",
            "Delta is candidate minus reference; 95% intervals use 2,000 paired query-bootstrap resamples with seed 42.",
            table(
                comparison.query("protocol == 'temporal' and split == 'test'")
                .drop(columns=["protocol", "split"])
                .round(5)
            ),
            "## Interpretation boundary",
            "Weights are selected only on temporal validation. Frozen configurations isolate representation changes from retuning. Because the behavioral judgments cover few top-ranked pairs and prior work inspected the test split, test differences are exploratory rather than confirmation of clinical improvement.",
        ]
    ) + "\n"
    # Narrative findings are consolidated in write_up/phase11_summary.md.

    log = pd.read_csv(EXPERIMENT_LOG_PATH)
    for mode in modes:
        for family in ("selected_signed_intent", "selected_all_terms"):
            name = f"{mode}:{family}"
            values = primary[primary["experiment"].eq(name)].set_index("split")["ndcg@10"]
            row = {
                "experiment": f"R-VALUE-{mode}-{family}",
                "hypothesis": "per-value entities and tri-state context improve signed intent retrieval",
                "method": str(dict(zip(WEIGHTS, configurations[name]))),
                "primary_metric": "NDCG@10",
                "result": f"Validation={values['validation']:.5f}; test={values['test']:.5f}",
                "decision": "exploratory validation-selected value-aware configuration",
            }
            log = pd.concat(
                [log[~log["experiment"].eq(row["experiment"])], pd.DataFrame([row])],
                ignore_index=True,
            )
    log.to_csv(EXPERIMENT_LOG_PATH, index=False)
    return {
        "output_dir": str(output_dir),
        "feature_changes": changed.to_dict(orient="records"),
        "selected": {
            name: weights
            for name, weights in configurations.items()
            if "selected" in name
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
