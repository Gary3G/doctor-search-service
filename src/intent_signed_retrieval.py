"""Hybrid retrieval with signed entity/context evidence and an intent prior.

Run ``python -m src.intent_signed_retrieval``. All weight selection uses only
the temporal validation partition. The temporal test partition is reported
after configurations are frozen and remains exploratory after prior inspection.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import CONTENT_PATH, EXPERIMENT_LOG_PATH, QUERIES_PATH
from src.context_repair_experiment import OUTPUT as REPAIR_OUTPUT
from src.evaluation import evaluate_rankings, summarize_metrics
from src.evaluation_split import SPLIT_DIR
from src.incremental_retrieval import PHASE11_DIR, build_signals, paired_delta, rank_scores
from src.repaired_signed_retrieval import make_repaired_signals
from src.signed_retrieval import make_signals
from src.topic_boost_retrieval import table


OUTPUT = PHASE11_DIR.parent / "intent_signed_boost"
REPAIRED_QUERIES = REPAIR_OUTPUT / "queries_repaired.csv"
REPAIRED_CONTENT = REPAIR_OUTPUT / "content_repaired.csv"
REPAIRED_MATRIX = REPAIR_OUTPUT / "compatibility_repaired.csv.gz"
SIGNED_GRID = (0.0, 0.05, 0.2)
INTENT_GRID = (0.0, 0.05, 0.1, 0.2, 0.5)
WEIGHTS = (
    "entity_bonus",
    "entity_penalty",
    "context_bonus",
    "context_penalty",
    "intent_bonus",
)


def intent_signed_scores(
    hybrid: np.ndarray,
    signals: dict[str, np.ndarray],
    intent: np.ndarray,
    weights: tuple[float, ...],
) -> np.ndarray:
    """Apply signed structured evidence and a nonnegative intent bonus."""
    if len(weights) != 5 or any(weight < 0 for weight in weights):
        raise ValueError("Expected five nonnegative weights")
    entity_bonus, entity_penalty, context_bonus, context_penalty, intent_bonus = weights
    return (
        hybrid
        + entity_bonus * signals["entity_bonus"]
        - entity_penalty * signals["entity_penalty"]
        + context_bonus * signals["context_bonus"]
        - context_penalty * signals["context_penalty"]
        + intent_bonus * intent
    )


def select_trial(trials: pd.DataFrame) -> pd.Series:
    """Maximize validation NDCG, preferring the smallest total weight on ties."""
    if trials.empty:
        raise ValueError("Cannot select from an empty validation grid")
    return (
        trials.assign(total_weight=trials[list(WEIGHTS)].sum(axis=1))
        .sort_values(
            ["ndcg@10", "total_weight", *WEIGHTS],
            ascending=[False, True, True, True, True, True, True],
        )
        .iloc[0]
    )


def row_weights(row: pd.Series) -> tuple[float, ...]:
    return tuple(float(row[column]) for column in WEIGHTS)


def build_configurations(trials: pd.DataFrame) -> dict[str, tuple[float, ...]]:
    """Select controlled families from one mode's validation grid."""
    zero_signed = np.logical_and.reduce([trials[column].eq(0) for column in WEIGHTS[:4]])
    all_signed_nonzero = np.logical_and.reduce([trials[column].gt(0) for column in WEIGHTS[:4]])
    prior_signed = (
        trials["entity_bonus"].eq(0.2)
        & trials["entity_penalty"].eq(0.2)
        & trials["context_bonus"].eq(0.2)
        & trials["context_penalty"].eq(0.0)
    )
    families = {
        "intent_only": trials[zero_signed & trials["intent_bonus"].gt(0)],
        "signed_only": trials[trials["intent_bonus"].eq(0)],
        "signed_plus_intent": trials[trials["intent_bonus"].gt(0) & ~zero_signed],
        "all_terms_nonzero": trials[all_signed_nonzero & trials["intent_bonus"].gt(0)],
        "prior_signed_plus_intent": trials[prior_signed & trials["intent_bonus"].gt(0)],
    }
    configurations = {
        "hybrid": (0.0, 0.0, 0.0, 0.0, 0.0),
        **{name: row_weights(select_trial(frame)) for name, frame in families.items()},
        "fixed_all_005_intent_020": (0.05, 0.05, 0.05, 0.05, 0.2),
        # Multiplying a score by a positive constant preserves ranking. This is
        # 2.5 times (BM25+dense+entity+context+intent)/5 because hybrid=(B+D)/2.
        "r_e7_equivalent": (0.5, 0.0, 0.5, 0.0, 0.5),
    }
    selected = configurations["all_terms_nonzero"]
    for index, weight_name in enumerate(WEIGHTS):
        removed = list(selected)
        removed[index] = 0.0
        configurations[f"all_terms_minus_{weight_name}"] = tuple(removed)
    return configurations


def validation_grid(
    hybrid: np.ndarray,
    signals: dict[str, np.ndarray],
    intent: np.ndarray,
    queries: pd.DataFrame,
    content: pd.DataFrame,
    validation: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    grid = itertools.product(SIGNED_GRID, SIGNED_GRID, SIGNED_GRID, SIGNED_GRID, INTENT_GRID)
    for weights in grid:
        scores = intent_signed_scores(hybrid, signals, intent, weights)
        ranks = rank_scores(scores, queries["query_id"], content["content_id"])
        metrics = summarize_metrics(evaluate_rankings(ranks, validation))
        rows.append(dict(zip(WEIGHTS, weights)) | metrics)
    return pd.DataFrame(rows)


def run(output_dir: Path = OUTPUT) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    queries = pd.read_csv(QUERIES_PATH).sort_values("query_id").reset_index(drop=True)
    content = pd.read_csv(CONTENT_PATH).sort_values("content_id").reset_index(drop=True)
    base, legacy_pairs, runtime, caches = build_signals(queries, content)
    hybrid = (base["bm25"] + base["dense"]) / 2
    intent = base["intent"]
    legacy_signals, legacy_audit = make_signals(base, legacy_pairs, hybrid.shape)

    repaired_queries = pd.read_csv(REPAIRED_QUERIES).sort_values("query_id").reset_index(drop=True)
    repaired_content = pd.read_csv(REPAIRED_CONTENT).sort_values("content_id").reset_index(drop=True)
    repaired_pairs = pd.read_csv(REPAIRED_MATRIX)
    expected = pd.MultiIndex.from_product(
        [queries["query_id"], content["content_id"]], names=["query_id", "content_id"]
    )
    repaired_pairs = repaired_pairs.set_index(["query_id", "content_id"]).reindex(expected).reset_index()
    repaired_signals, repaired_audit = make_repaired_signals(
        base, repaired_pairs, repaired_queries, repaired_content, hybrid.shape
    )
    modes = {"legacy": legacy_signals, "repaired": repaired_signals}
    pd.concat(
        [legacy_audit.assign(mode="legacy"), repaired_audit.assign(mode="repaired")],
        ignore_index=True,
    ).to_csv(output_dir / "feature_audit.csv", index=False)

    validation_path = SPLIT_DIR / "temporal_validation_judgments.csv"
    validation = pd.read_csv(validation_path)
    configurations: dict[str, tuple[float, ...]] = {}
    trial_frames = []
    for mode, signals in modes.items():
        trials = validation_grid(hybrid, signals, intent, queries, content, validation)
        trial_frames.append(trials.assign(mode=mode))
        configurations.update(
            {f"{mode}:{name}": weights for name, weights in build_configurations(trials).items()}
        )
    pd.concat(trial_frames, ignore_index=True).to_csv(output_dir / "validation_grid.csv", index=False)
    pd.DataFrame(
        [
            {"experiment": name, **dict(zip(WEIGHTS, weights))}
            for name, weights in configurations.items()
        ]
    ).to_csv(output_dir / "configurations.csv", index=False)

    rankings: dict[str, pd.DataFrame] = {}
    for name, weights in configurations.items():
        mode = name.split(":", 1)[0]
        scores = intent_signed_scores(hybrid, modes[mode], intent, weights)
        rankings[name] = rank_scores(scores, queries["query_id"], content["content_id"])

    phase11 = pd.read_csv(PHASE11_DIR / "rankings.csv.gz")
    columns = ["query_id", "content_id", "rank"]
    pd.testing.assert_frame_equal(
        rankings["legacy:hybrid"][columns],
        phase11[phase11["experiment"].eq("R-E4")][columns].reset_index(drop=True),
    )
    pd.testing.assert_frame_equal(
        rankings["legacy:r_e7_equivalent"][columns],
        phase11[phase11["experiment"].eq("R-E7")][columns].reset_index(drop=True),
    )
    pd.concat(
        [frame.assign(experiment=name) for name, frame in rankings.items()], ignore_index=True
    ).to_csv(output_dir / "rankings.csv.gz", index=False)

    metadata = legacy_pairs.groupby("query_id", sort=True).first()[
        ["query_language", "query_intent", "context_constraint_count"]
    ].reset_index()
    metadata["has_context"] = metadata["context_constraint_count"].gt(0)
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
        validation_path,
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
                    tags = {
                        "protocol": protocol,
                        "split": split,
                        "experiment": name,
                        "scheme": scheme,
                        "threshold": threshold,
                    }
                    per_query = evaluate_rankings(ranks, judgments, scheme, threshold)
                    summaries.append(tags | summarize_metrics(per_query))
                    if scheme == "relevance_grade" and threshold == 1:
                        primary[name] = per_query
                        details.append(per_query.assign(**tags))
                        enriched = per_query.merge(metadata, on="query_id", validate="one_to_one")
                        for dimension in ("query_language", "query_intent", "has_context"):
                            for value, group in enriched.groupby(dimension, dropna=False):
                                slices.append(
                                    tags
                                    | {"dimension": dimension, "value": value}
                                    | summarize_metrics(group)
                                )
            for mode in modes:
                reference = f"{mode}:hybrid"
                signed_reference = f"{mode}:signed_only"
                for candidate in configurations:
                    if not candidate.startswith(f"{mode}:") or candidate == reference:
                        continue
                    for comparison_reference in (
                        reference,
                        signed_reference,
                        f"{mode}:r_e7_equivalent",
                    ):
                        if candidate == comparison_reference:
                            continue
                        delta = paired_delta(primary[comparison_reference], primary[candidate])
                        difference = (
                            primary[candidate].set_index("query_id")["ndcg@10"]
                            - primary[comparison_reference].set_index("query_id")["ndcg@10"]
                        )
                        comparisons.append(
                            {
                                "protocol": protocol,
                                "split": split,
                                "candidate": candidate,
                                "reference": comparison_reference,
                                "delta_ndcg": delta["delta_vs_full"],
                                "lower": delta["lower"],
                                "upper": delta["upper"],
                                "positive_queries": delta["positive_queries"],
                                "improved": int((difference > 0).sum()),
                                "worsened": int((difference < 0).sum()),
                                "unchanged": int((difference == 0).sum()),
                            }
                        )

    summary = pd.DataFrame(summaries)
    comparison = pd.DataFrame(comparisons)
    summary.to_csv(output_dir / "metrics.csv", index=False)
    comparison.to_csv(output_dir / "paired_comparisons.csv", index=False)
    pd.concat(details, ignore_index=True).to_csv(output_dir / "per_query_metrics.csv.gz", index=False)
    pd.DataFrame(slices).to_csv(output_dir / "slices.csv", index=False)

    manifest = {
        "formula": (
            "hybrid + entity_bonus*entity_coverage - entity_penalty*entity_conflict_rate "
            "+ context_bonus*context_coverage - context_penalty*explicit_context_conflict_rate "
            "+ intent_bonus*intent_content_type_match"
        ),
        "signed_grid": SIGNED_GRID,
        "intent_grid": INTENT_GRID,
        "validation_trials_per_mode": len(trial_frames[0]),
        "configurations": configurations,
        "selection": (
            "temporal-validation NDCG@10; ties prefer the smallest total weight then "
            "lexicographic weights; all_terms_nonzero requires all five terms > 0"
        ),
        "modes": {
            "legacy": "Phase 11 entity/context evidence",
            "repaired": "v2 query cues plus explicit-only dosing/comparison title evidence",
        },
        "missing": "missing evidence receives zero bonus and zero penalty",
        "limitations": [
            "intent is an assisted query label plus a coarse rule-based content-type prior",
            "entity penalty duplicates match ordering when metadata is fully populated",
            "behavioral labels are sparse and sometimes off-topic",
            "exploratory after prior test inspection",
            "bootstrap intervals are descriptive and not multiplicity corrected",
        ],
        **runtime,
        "sha256": {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in inputs
            + [
                Path(__file__),
                Path("src/incremental_retrieval.py"),
                Path("src/signed_retrieval.py"),
                Path("src/repaired_signed_retrieval.py"),
                Path("src/evaluation.py"),
            ]
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
            "# Signed entity/context evidence with intent",
            "Run `.venv/bin/python -m src.intent_signed_retrieval`. This is the first experiment that combines the BM25+dense hybrid, entity and context match bonuses, explicit mismatch penalties, and the intent/content-type prior in one additive score.",
            manifest["formula"],
            "Signed weights use {0, 0.05, 0.2}; intent uses {0, 0.05, 0.1, 0.2, 0.5}, for 405 validation trials per evidence mode. No test metric enters weight selection. The unconstrained signed-plus-intent family requires a nonzero intent weight and at least one signed term. The all-terms family requires all five terms to be nonzero.",
            "## Selected and controlled configurations",
            table(pd.read_csv(output_dir / "configurations.csv")),
            "## Temporal validation and test",
            table(view.reset_index().round(5)),
            "## Paired temporal-test comparisons",
            "Delta is candidate minus reference. Intervals use 2,000 paired query bootstrap resamples with seed 42 and are descriptive.",
            table(
                comparison.query("protocol == 'temporal' and split == 'test'")
                .drop(columns=["protocol", "split"])
                .round(5)
            ),
            "## Interpretation boundary",
            "R-E7 equivalence is verified for legacy evidence: hybrid + 0.5*entity + 0.5*context + 0.5*intent has exactly the same ordering as the original equal five-signal mean. The repaired mode changes only query/context evidence; hybrid, entities, intent labels, content types, and behavioral judgments remain frozen. Reported test results are exploratory because the test partition has been inspected in earlier work and the behavioral labels are sparse.",
        ]
    ) + "\n"
    # Narrative findings are consolidated in write_up/phase11_summary.md.

    log = pd.read_csv(EXPERIMENT_LOG_PATH)
    for mode in modes:
        for family in ("signed_plus_intent", "all_terms_nonzero"):
            name = f"{mode}:{family}"
            values = primary[primary["experiment"].eq(name)].set_index("split")["ndcg@10"]
            row = {
                "experiment": f"R-INTENT-SIGNED-{mode}-{family}",
                "hypothesis": "intent improves hybrid retrieval with signed entity/context evidence",
                "method": str(dict(zip(WEIGHTS, configurations[name]))),
                "primary_metric": "NDCG@10",
                "result": f"Validation={values['validation']:.5f}; test={values['test']:.5f}",
                "decision": "exploratory validation-selected configuration; test previously inspected",
            }
            log = pd.concat(
                [log[~log["experiment"].eq(row["experiment"])], pd.DataFrame([row])],
                ignore_index=True,
            )
    log.to_csv(EXPERIMENT_LOG_PATH, index=False)
    return {
        "output_dir": str(output_dir),
        "legacy_selected": configurations["legacy:signed_plus_intent"],
        "legacy_all_terms": configurations["legacy:all_terms_nonzero"],
        "repaired_selected": configurations["repaired:signed_plus_intent"],
        "repaired_all_terms": configurations["repaired:all_terms_nonzero"],
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
