"""Evaluate repaired explicit context with match bonuses and mismatch penalties.

Run ``python -m src.repaired_signed_retrieval``. Weight selection uses only the
temporal validation partition. Missing evidence is neutral by construction.
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
from src.signed_retrieval import (
    GRID,
    OUTPUT as LEGACY_SIGNED_OUTPUT,
    WEIGHTS,
    explicit_conflict,
    select,
    signed_scores,
)
from src.topic_boost_retrieval import table


OUTPUT = PHASE11_DIR.parent / "repaired_signed_boost"
REPAIRED_QUERIES = REPAIR_OUTPUT / "queries_repaired.csv"
REPAIRED_CONTENT = REPAIR_OUTPUT / "content_repaired.csv"
REPAIRED_MATRIX = REPAIR_OUTPUT / "compatibility_repaired.csv.gz"


def make_repaired_signals(
    base: dict[str, np.ndarray],
    pairs: pd.DataFrame,
    queries: pd.DataFrame,
    content: pd.DataFrame,
    shape: tuple[int, int],
) -> tuple[dict[str, np.ndarray], pd.DataFrame]:
    """Use repaired explicit matches and explicit, missing-neutral conflicts."""
    query_lookup = queries.set_index("query_id")
    content_lookup = content.set_index("content_id")
    conflicts: dict[str, pd.Series] = {}
    for name, query_column, content_column in (
        ("age", "age_group", "content_age_group"),
        ("route", "route", "content_route"),
        ("year", "year", "publication_year"),
    ):
        left = pairs["query_id"].map(query_lookup[query_column])
        right = pairs["content_id"].map(content_lookup[content_column])
        if name == "year":
            left = pd.to_numeric(left, errors="coerce")
            right = pd.to_numeric(right, errors="coerce")
        conflicts[name] = explicit_conflict(left, right)

    denominator = pairs["context_constraint_count"].replace(0, np.nan)
    context_penalty = (
        sum(value.astype(int) for value in conflicts.values()) / denominator
    ).fillna(0.0).to_numpy().reshape(shape)
    signals = {
        "entity_bonus": pairs["entity_coverage"].to_numpy(float).reshape(shape),
        "entity_penalty": pairs["entity_conflict_rate"].to_numpy(float).reshape(shape),
        "context_bonus": pairs["context_coverage"].to_numpy(float).reshape(shape),
        "context_penalty": context_penalty,
    }
    if any(not np.isfinite(signal).all() for signal in signals.values()):
        raise ValueError("Repaired signed features must be finite")
    audit = [
        {
            "feature": name,
            "nonzero_pairs": int(np.count_nonzero(signal)),
            "mean": float(signal.mean()),
        }
        for name, signal in signals.items()
    ]
    audit.extend(
        {
            "feature": f"explicit_{name}_conflict",
            "nonzero_pairs": int(value.sum()),
            "mean": float(value.mean()),
        }
        for name, value in conflicts.items()
    )
    return signals, pd.DataFrame(audit)


def run(output_dir: Path = OUTPUT) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_queries = pd.read_csv(QUERIES_PATH).sort_values("query_id").reset_index(drop=True)
    content = pd.read_csv(CONTENT_PATH).sort_values("content_id").reset_index(drop=True)
    repaired_queries = pd.read_csv(REPAIRED_QUERIES).sort_values("query_id").reset_index(drop=True)
    repaired_content = pd.read_csv(REPAIRED_CONTENT).sort_values("content_id").reset_index(drop=True)
    pairs = pd.read_csv(REPAIRED_MATRIX)
    base, legacy_pairs, runtime, caches = build_signals(raw_queries, content)
    expected_index = pd.MultiIndex.from_product(
        [raw_queries["query_id"], content["content_id"]],
        names=["query_id", "content_id"],
    )
    pairs = pairs.set_index(["query_id", "content_id"]).reindex(expected_index).reset_index()
    pd.testing.assert_frame_equal(
        pairs[["query_id", "content_id"]], legacy_pairs[["query_id", "content_id"]]
    )
    hybrid = (base["bm25"] + base["dense"]) / 2
    signals, audit = make_repaired_signals(
        base, pairs, repaired_queries, repaired_content, hybrid.shape
    )
    audit.to_csv(output_dir / "feature_audit.csv", index=False)
    complement_error = float(
        np.max(np.abs(signals["entity_bonus"] + signals["entity_penalty"] - 1))
    )

    validation_path = SPLIT_DIR / "temporal_validation_judgments.csv"
    validation = pd.read_csv(validation_path)
    ranking_cache: dict[tuple[float, ...], pd.DataFrame] = {}

    def ranking(weights: tuple[float, ...]) -> pd.DataFrame:
        weights = tuple(weights)
        if weights not in ranking_cache:
            scores = signed_scores(hybrid, signals, weights)
            ranking_cache[weights] = rank_scores(
                scores, raw_queries["query_id"], content["content_id"]
            )
        return ranking_cache[weights]

    trials = []
    for weights in itertools.product(GRID, repeat=4):
        metrics = evaluate_rankings(ranking(weights), validation)
        trials.append(dict(zip(WEIGHTS, weights)) | summarize_metrics(metrics))
    trials = pd.DataFrame(trials)
    trials.to_csv(output_dir / "validation_grid.csv", index=False)

    configurations: dict[str, tuple[float, ...]] = {"hybrid": (0.0, 0.0, 0.0, 0.0)}
    families = {
        "repaired_bonuses_only": trials[
            (trials["entity_penalty"] == 0) & (trials["context_penalty"] == 0)
        ],
        "repaired_penalties_only": trials[
            (trials["entity_bonus"] == 0) & (trials["context_bonus"] == 0)
        ],
        "repaired_both": trials,
    }
    for name, candidates in families.items():
        chosen = select(candidates)
        configurations[name] = tuple(float(chosen[column]) for column in WEIGHTS)
    for index, weight_name in enumerate(WEIGHTS):
        removed = list(configurations["repaired_both"])
        removed[index] = 0.0
        configurations[f"repaired_both_minus_{weight_name}"] = tuple(removed)
    configurations.update(
        repaired_fixed_bonuses=(0.05, 0.0, 0.05, 0.0),
        repaired_fixed_penalties=(0.0, 0.05, 0.0, 0.05),
        repaired_fixed_both=(0.05, 0.05, 0.05, 0.05),
    )
    pd.DataFrame(
        [dict(experiment=name, **dict(zip(WEIGHTS, weights))) for name, weights in configurations.items()]
    ).to_csv(output_dir / "configurations.csv", index=False)
    rankings = {name: ranking(weights) for name, weights in configurations.items()}

    phase11 = pd.read_csv(PHASE11_DIR / "rankings.csv.gz")
    columns = ["query_id", "content_id", "rank"]
    pd.testing.assert_frame_equal(
        rankings["hybrid"][columns],
        phase11[phase11["experiment"].eq("R-E4")][columns].reset_index(drop=True),
    )
    pd.concat(
        [frame.assign(experiment=name) for name, frame in rankings.items()], ignore_index=True
    ).to_csv(output_dir / "rankings.csv.gz", index=False)
    legacy_signed = pd.read_csv(LEGACY_SIGNED_OUTPUT / "rankings.csv.gz")
    legacy_comparison = []
    for repaired_name, legacy_name in (
        ("repaired_bonuses_only", "bonuses_only"),
        ("repaired_penalties_only", "penalties_only"),
        ("repaired_both", "both"),
        ("repaired_fixed_bonuses", "fixed_bonuses"),
        ("repaired_fixed_penalties", "fixed_penalties"),
        ("repaired_fixed_both", "fixed_both"),
    ):
        repaired_top = (
            rankings[repaired_name].query("rank <= 10").groupby("query_id")["content_id"].agg(tuple)
        )
        legacy_top = (
            legacy_signed[legacy_signed["experiment"].eq(legacy_name)]
            .query("rank <= 10")
            .groupby("query_id")["content_id"]
            .agg(tuple)
        )
        legacy_comparison.append(
            {
                "repaired_experiment": repaired_name,
                "legacy_experiment": legacy_name,
                "top10_order_changes": int((repaired_top != legacy_top).sum()),
                "top10_membership_changes": int(
                    sum(set(left) != set(right) for left, right in zip(repaired_top, legacy_top))
                ),
            }
        )
    legacy_comparison = pd.DataFrame(legacy_comparison)
    legacy_comparison.to_csv(output_dir / "legacy_signed_ranking_comparison.csv", index=False)

    summaries: list[dict[str, object]] = []
    details: list[pd.DataFrame] = []
    comparisons: list[dict[str, object]] = []
    slices: list[dict[str, object]] = []
    metadata = pairs.groupby("query_id", sort=True).first()[
        ["query_language", "query_intent", "context_constraint_count"]
    ].reset_index()
    metadata["has_context"] = metadata["context_constraint_count"].gt(0)
    inputs = [
        CONTENT_PATH,
        QUERIES_PATH,
        REPAIRED_QUERIES,
        REPAIRED_CONTENT,
        REPAIRED_MATRIX,
        LEGACY_SIGNED_OUTPUT / "rankings.csv.gz",
        LEGACY_SIGNED_OUTPUT / "metrics.csv",
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
                        for dimension in ("query_language", "query_intent", "has_context"):
                            for value, group in enriched.groupby(dimension, dropna=False):
                                slices.append(
                                    tags
                                    | {"dimension": dimension, "value": value}
                                    | summarize_metrics(group)
                                )
            contrasts = [(name, "hybrid") for name in configurations if name != "hybrid"]
            contrasts.extend(
                (name, "repaired_both")
                for name in configurations
                if name.startswith("repaired_both_minus_")
            )
            contrasts.append(("repaired_fixed_both", "repaired_fixed_bonuses"))
            for candidate, reference in contrasts:
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
    pd.concat(details, ignore_index=True).to_csv(
        output_dir / "per_query_metrics.csv.gz", index=False
    )
    pd.DataFrame(slices).to_csv(output_dir / "slices.csv", index=False)

    manifest = {
        "formula": (
            "hybrid + entity_bonus*entity_coverage - entity_penalty*entity_conflict_rate "
            "+ context_bonus*repaired_explicit_context_coverage "
            "- context_penalty*explicit_context_conflict_rate"
        ),
        "grid": GRID,
        "configurations": configurations,
        "selection": "81 temporal-validation trials; maximize NDCG@10; prefer smaller weights on ties",
        "repair_data": {
            "query_extractor": "query_extraction_v2",
            "context_policy": "explicit",
            "dosing_comparison_type_proxies": False,
            "compatibility_path": str(REPAIRED_MATRIX),
        },
        "missing": "zero bonus and zero penalty when required evidence is absent",
        "context_penalty": "explicit age, route, or year conflict only; no renal/dosing/pregnancy absence penalty",
        "entity_complement_max_error": complement_error,
        "limitations": [
            "entity conflict remains the complement of entity match in this fully populated metadata",
            "exploratory after prior test inspection",
            "behavioral labels are sparse and sometimes off-topic",
            "bootstrap intervals are not cluster robust or multiplicity adjusted",
        ],
        **runtime,
        "sha256": {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in inputs
            + [
                Path(__file__),
                Path("src/query_extraction_v2.py"),
                Path("src/structured_compatibility.py"),
                Path("src/signed_retrieval.py"),
                Path("src/evaluation.py"),
            ]
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    primary = summary.query(
        "protocol == 'temporal' and scheme == 'relevance_grade' and threshold == 1"
    )
    legacy_primary = pd.read_csv(LEGACY_SIGNED_OUTPUT / "metrics.csv").query(
        "protocol == 'temporal' and scheme == 'relevance_grade' and threshold == 1"
    )
    metric_comparison_rows = []
    for repaired_name, legacy_name in (
        ("repaired_bonuses_only", "bonuses_only"),
        ("repaired_penalties_only", "penalties_only"),
        ("repaired_both", "both"),
        ("repaired_fixed_bonuses", "fixed_bonuses"),
        ("repaired_fixed_penalties", "fixed_penalties"),
        ("repaired_fixed_both", "fixed_both"),
    ):
        for split in ("validation", "test"):
            repaired_value = primary[
                primary["experiment"].eq(repaired_name) & primary["split"].eq(split)
            ].iloc[0]
            legacy_value = legacy_primary[
                legacy_primary["experiment"].eq(legacy_name)
                & legacy_primary["split"].eq(split)
            ].iloc[0]
            metric_comparison_rows.append(
                {
                    "split": split,
                    "repaired_experiment": repaired_name,
                    "legacy_experiment": legacy_name,
                    "legacy_ndcg@10": legacy_value["ndcg@10"],
                    "repaired_ndcg@10": repaired_value["ndcg@10"],
                    "delta_ndcg@10": repaired_value["ndcg@10"] - legacy_value["ndcg@10"],
                }
            )
    metric_comparison = pd.DataFrame(metric_comparison_rows)
    metric_comparison.to_csv(output_dir / "legacy_signed_metric_comparison.csv", index=False)
    view = primary.pivot(
        index="experiment", columns="split", values=["ndcg@10", "recall@10", "mrr@10"]
    )
    view.columns = [" ".join(column) for column in view.columns]
    report = "\n\n".join(
        [
            "# Repaired context with match bonuses and mismatch penalties",
            "Run `.venv/bin/python -m src.repaired_signed_retrieval`. This combines the v2 extraction repairs and explicit-only dosing/comparison evidence with signed scoring. Entity data, hybrid scores, intent labels, and behavioral judgments are unchanged.",
            manifest["formula"],
            "Missing evidence remains neutral. Entity conflicts require populated but nonmatching disease, molecule, class, or area metadata. Context penalties require explicit incompatible age, route, or year evidence. No penalty is assigned for absent renal, pregnancy, dosing, comparison, or other title evidence.",
            "The four weights independently use {0, 0.05, 0.2}. Bonuses-only, penalties-only, and combined configurations are selected using temporal-validation NDCG@10. Controlled removals preserve the remaining selected weights. Fixed 0.05 configurations ensure nonzero signed terms are compared even if validation selects zero.",
            table(pd.read_csv(output_dir / "configurations.csv")),
            "## Temporal validation and test",
            table(view.reset_index().round(5)),
            "## Feature audit",
            table(audit.round(5)),
            "## Ranking changes versus the legacy signed experiment",
            table(legacy_comparison),
            "The repaired explicit context changes rankings, but every compared aggregate temporal NDCG@10 value is unchanged at stored precision:",
            table(metric_comparison.round(6)),
            "## Paired temporal-test comparisons",
            "Delta is candidate minus reference. Intervals use 2,000 paired query bootstrap resamples with seed 42; they are descriptive and not corrected for selection or multiple comparisons.",
            table(
                comparison.query("protocol == 'temporal' and split == 'test'")
                .drop(columns=["protocol", "split"])
                .round(5)
            ),
            "## Interpretation boundary",
            f"Validation selects weights {configurations['repaired_both']} for entity bonus, entity penalty, context bonus, and context penalty respectively. The zero context-penalty weight means explicit context mismatches are not supported by validation. Entity match plus entity conflict differs from one by at most {complement_error:.8f}; therefore the entity penalty still duplicates the ordering information in the match bonus, up to a query-constant shift. The selected combined model improves validation NDCG@10 over hybrid but lowers test NDCG@10, and its paired interval includes zero. Retrieval metrics use incomplete behavioral proxies and cannot establish clinical superiority. All alternate grades, protocols, per-query metrics, slices, rankings, validation trials, and fingerprints are saved with the report.",
        ]
    ) + "\n"
    # Narrative findings are consolidated in write_up/phase11_summary.md.

    log = pd.read_csv(EXPERIMENT_LOG_PATH)
    for name in ("repaired_bonuses_only", "repaired_penalties_only", "repaired_both"):
        experiment = "R-REPAIRED-SIGNED-" + name.removeprefix("repaired_")
        values = primary[primary["experiment"].eq(name)].set_index("split")["ndcg@10"]
        row = {
            "experiment": experiment,
            "hypothesis": "repaired explicit context plus signed scoring improves hybrid retrieval",
            "method": str(dict(zip(WEIGHTS, configurations[name]))),
            "primary_metric": "NDCG@10",
            "result": f"Validation={values['validation']:.5f}; test={values['test']:.5f}",
            "decision": "exploratory validation-selected repaired signed configuration",
        }
        log = pd.concat([log[~log["experiment"].eq(experiment)], pd.DataFrame([row])], ignore_index=True)
    log.to_csv(EXPERIMENT_LOG_PATH, index=False)
    return {"output_dir": str(output_dir), "selected_both": configurations["repaired_both"]}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
