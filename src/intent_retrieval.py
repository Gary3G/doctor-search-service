"""Phase 12: connect predicted query intent to retrieval.

The Phase 11 R-E6 score is frozen as the no-intent starting point.  Only the
coefficient on intent compatibility is selected with temporal validation
judgments.  Test judgments are loaded after that selection and are descriptive
because earlier project phases already inspected the test split.

Run with ``.venv/bin/python -m src.intent_retrieval``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
import warnings

import joblib
import numpy as np
import pandas as pd
import sklearn
from scipy.sparse import csr_matrix, hstack
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.preprocessing import normalize

from src.config import (
    CONFIG,
    CONTENT_PATH,
    EXPERIMENT_LOG_PATH,
    OUTPUT_DIR,
)
from src.evaluation import evaluate_rankings, summarize_metrics
from src.evaluation_split import SPLIT_DIR
from src.incremental_retrieval import build_signals, combine, rank_scores
from src.intent import ENRICHED_QUERIES_PATH, INTENT_METADATA_QUERIES_PATH
from src.intent_improved import (
    MODEL_PATH as INTENT_MODEL_PATH,
    QUERY_EMBEDDINGS_PATH,
    combined_structured_records,
)
from src.structured_compatibility import INTENT_CONTENT_TYPES


PHASE12_DIR = OUTPUT_DIR / "retrieval" / "phase12"
INTENT_WEIGHTS = (0.0, 0.025, 0.05, 0.1, 0.2, 0.25, 0.5, 1.0)
INTENT_SOURCES = ("assisted", "predicted_hard", "predicted_soft")


def intent_compatibility(
    probabilities: np.ndarray,
    classes: np.ndarray,
    content_types: pd.Series,
) -> np.ndarray:
    """Return expected compatibility for every query-content pair.

    One-hot probabilities produce the ordinary hard-label rule.  Calibrated
    class probabilities preserve uncertainty by summing probability mass over
    every intent compatible with a content type.
    """
    probabilities = np.asarray(probabilities, dtype=float)
    classes = np.asarray(classes, dtype=object)
    if probabilities.ndim != 2 or probabilities.shape[1] != len(classes):
        raise ValueError("probabilities must be query-by-class")
    if not np.isfinite(probabilities).all() or (probabilities < 0).any():
        raise ValueError("intent probabilities must be finite and non-negative")
    if not np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-6):
        raise ValueError("intent probabilities must sum to one")
    policy = np.asarray(
        [
            [content_type in INTENT_CONTENT_TYPES.get(str(intent), set()) for content_type in content_types]
            for intent in classes
        ],
        dtype=float,
    )
    result = probabilities @ policy
    if not np.isfinite(result).all() or not ((0 <= result) & (result <= 1)).all():
        raise AssertionError("compatibility must be bounded in [0, 1]")
    return result


def score_with_intent(
    phase11_without_intent: np.ndarray,
    intent_score: np.ndarray,
    intent_weight: float,
) -> np.ndarray:
    """Add intent without changing the frozen Phase 11 base components."""
    if intent_weight < 0:
        raise ValueError("intent_weight must be non-negative")
    if phase11_without_intent.shape != intent_score.shape:
        raise ValueError("base and intent matrices must have the same shape")
    return phase11_without_intent + intent_weight * intent_score


def select_intent_weight(validation_grid: pd.DataFrame, source: str) -> float:
    """Select by validation NDCG@10, breaking exact ties toward less intent."""
    candidates = validation_grid[validation_grid["intent_source"].eq(source)]
    if candidates.empty:
        raise ValueError(f"No validation candidates for {source}")
    selected = candidates.sort_values(
        ["ndcg@10", "intent_weight"], ascending=[False, True]
    ).iloc[0]
    return float(selected["intent_weight"])


def paired_bootstrap(
    baseline: pd.DataFrame,
    candidate: pd.DataFrame,
    metric: str = "ndcg@10",
) -> dict[str, float | int]:
    """Paired candidate-minus-baseline mean and deterministic query bootstrap."""
    joined = baseline[["query_id", metric]].merge(
        candidate[["query_id", metric]],
        on="query_id",
        suffixes=("_baseline", "_candidate"),
        validate="one_to_one",
    ).dropna()
    delta = joined[f"{metric}_candidate"] - joined[f"{metric}_baseline"]
    if joined.empty:
        return {
            "eligible_queries": 0,
            "mean_delta": np.nan,
            "lower_95": np.nan,
            "upper_95": np.nan,
            "improved_queries": 0,
            "worsened_queries": 0,
            "unchanged_queries": 0,
        }
    rng = np.random.default_rng(CONFIG.random_seed)
    samples = rng.choice(delta.to_numpy(), (2000, len(delta)), replace=True).mean(axis=1)
    lower, upper = np.quantile(samples, [0.025, 0.975])
    return {
        "eligible_queries": len(delta),
        "mean_delta": float(delta.mean()),
        "lower_95": float(lower),
        "upper_95": float(upper),
        "improved_queries": int(delta.gt(0).sum()),
        "worsened_queries": int(delta.lt(0).sum()),
        "unchanged_queries": int(delta.eq(0).sum()),
    }


def _predict_intents(
    queries: pd.DataFrame,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, list[str]]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", InconsistentVersionWarning)
        artifact = joblib.load(INTENT_MODEL_PATH)
    version_warnings = [
        str(item.message)
        for item in caught
        if issubclass(item.category, InconsistentVersionWarning)
    ]
    if artifact.get("experiment") != "T1-E4":
        raise ValueError("Phase 12 expects the Phase 5 T1-E4 selected model")
    embedding_source = pd.read_csv(ENRICHED_QUERIES_PATH, usecols=["query_id"])
    archive = np.load(QUERY_EMBEDDINGS_PATH, allow_pickle=False)
    vectors = archive["embeddings"]
    if len(vectors) != len(embedding_source) or embedding_source["query_id"].duplicated().any():
        raise ValueError("Phase 2 embeddings do not align with their source")
    vector_map = dict(zip(embedding_source["query_id"], vectors, strict=True))
    query_vectors = np.stack([vector_map[query_id] for query_id in queries["query_id"]])
    structured = normalize(
        artifact["structured_vectorizer"].transform(combined_structured_records(queries)),
        norm="l2",
    )
    design = hstack([csr_matrix(query_vectors), structured], format="csr")
    classifier = artifact["classifier"]
    probabilities = classifier.predict_proba(design)
    classes = classifier.classes_
    order = np.argsort(probabilities, axis=1)
    top = order[:, -1]
    second = order[:, -2]
    predictions = queries[["query_id", "intent"]].rename(
        columns={"intent": "assisted_intent"}
    )
    predictions["predicted_intent"] = classes[top]
    predictions["predicted_probability"] = probabilities[np.arange(len(queries)), top]
    predictions["second_intent"] = classes[second]
    predictions["probability_margin"] = (
        probabilities[np.arange(len(queries)), top]
        - probabilities[np.arange(len(queries)), second]
    )
    predictions["agrees_with_assisted"] = predictions["predicted_intent"].eq(
        predictions["assisted_intent"]
    )
    return predictions, probabilities, classes, version_warnings


def _intent_slice_rows(
    baseline: pd.DataFrame,
    candidate: pd.DataFrame,
    query_metadata: pd.DataFrame,
    configuration: str,
) -> list[dict[str, Any]]:
    joined = baseline[["query_id", "ndcg@10"]].merge(
        candidate[["query_id", "ndcg@10"]],
        on="query_id",
        suffixes=("_baseline", "_candidate"),
        validate="one_to_one",
    ).merge(query_metadata, on="query_id", validate="one_to_one")
    rows: list[dict[str, Any]] = []
    for intent, group in joined.groupby("assisted_intent", sort=True):
        eligible = group.dropna(subset=["ndcg@10_baseline", "ndcg@10_candidate"])
        delta = eligible["ndcg@10_candidate"] - eligible["ndcg@10_baseline"]
        rows.append(
            {
                "configuration": configuration,
                "assisted_intent": intent,
                "queries": len(group),
                "eligible_queries": len(eligible),
                "baseline_ndcg@10": eligible["ndcg@10_baseline"].mean(),
                "candidate_ndcg@10": eligible["ndcg@10_candidate"].mean(),
                "delta_ndcg@10": delta.mean(),
                "improved_queries": int(delta.gt(0).sum()),
                "worsened_queries": int(delta.lt(0).sum()),
                "unchanged_queries": int(delta.eq(0).sum()),
                "classifier_agreement": group["agrees_with_assisted"].mean(),
                "mean_predicted_probability": group["predicted_probability"].mean(),
            }
        )
    return rows


def _sha256(paths: list[Path]) -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _update_experiment_log(
    selected_weights: dict[str, float], metrics: pd.DataFrame
) -> None:
    log = pd.read_csv(EXPERIMENT_LOG_PATH)
    primary = metrics[
        metrics["protocol"].eq("temporal")
        & metrics["scheme"].eq("relevance_grade")
        & metrics["threshold"].eq(1)
    ].set_index(["split", "configuration"])
    additions = [
        {
            "experiment": "R-I0",
            "hypothesis": "Phase 11 structured hybrid is a stable no-intent comparator",
            "method": "Frozen R-E6 mean(BM25, dense, entities, context)",
            "primary_metric": "NDCG@10",
            "result": (
                f"Validation={primary.loc[('validation', 'without_intent'), 'ndcg@10']:.5f}; "
                f"test={primary.loc[('test', 'without_intent'), 'ndcg@10']:.5f}"
            ),
            "decision": "Phase 12 baseline; no retuning",
        },
        {
            "experiment": "R-I1",
            "hypothesis": "runtime predicted intent improves ranking",
            "method": f"R-I0 + {selected_weights['predicted_hard']:.3f} * predicted hard intent compatibility",
            "primary_metric": "NDCG@10",
            "result": (
                f"Validation={primary.loc[('validation', 'with_predicted_hard_intent'), 'ndcg@10']:.5f}; "
                f"test={primary.loc[('test', 'with_predicted_hard_intent'), 'ndcg@10']:.5f}"
            ),
            "decision": "primary deployable comparison; weight selected on validation; test descriptive",
        },
        {
            "experiment": "R-I1-SOFT",
            "hypothesis": "intent uncertainty improves ranking robustness",
            "method": f"R-I0 + {selected_weights['predicted_soft']:.3f} * probability-weighted intent compatibility",
            "primary_metric": "NDCG@10",
            "result": (
                f"Validation={primary.loc[('validation', 'with_predicted_soft_intent'), 'ndcg@10']:.5f}; "
                f"test={primary.loc[('test', 'with_predicted_soft_intent'), 'ndcg@10']:.5f}"
            ),
            "decision": "uncertainty-aware diagnostic; weaker validation result",
        },
        {
            "experiment": "R-I2",
            "hypothesis": "assisted reference intent improves ranking",
            "method": f"R-I0 + {selected_weights['assisted']:.3f} * assisted intent compatibility",
            "primary_metric": "NDCG@10",
            "result": (
                f"Validation={primary.loc[('validation', 'with_assisted_intent'), 'ndcg@10']:.5f}; "
                f"test={primary.loc[('test', 'with_assisted_intent'), 'ndcg@10']:.5f}"
            ),
            "decision": "reference-label ceiling diagnostic; not deployable",
        },
    ]
    for row in additions:
        log = log[~log["experiment"].eq(row["experiment"])]
        log = pd.concat([log, pd.DataFrame([row])], ignore_index=True)
    log.to_csv(EXPERIMENT_LOG_PATH, index=False)


def build_phase12_artifacts(output_dir: Path = PHASE12_DIR) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    queries = pd.read_csv(INTENT_METADATA_QUERIES_PATH).sort_values("query_id").reset_index(drop=True)
    content = pd.read_csv(CONTENT_PATH).sort_values("content_id").reset_index(drop=True)
    signals, pairs, runtime, caches = build_signals(queries, content)
    base = combine(signals, ("bm25", "dense", "entities", "context"))

    predictions, probabilities, classes, version_warnings = _predict_intents(queries)
    assisted = signals["intent"]
    predicted_soft = intent_compatibility(probabilities, classes, content["content_type"])
    hard = np.zeros_like(probabilities)
    hard[np.arange(len(hard)), probabilities.argmax(axis=1)] = 1.0
    predicted_hard = intent_compatibility(hard, classes, content["content_type"])
    intent_matrices = {
        "assisted": assisted,
        "predicted_hard": predicted_hard,
        "predicted_soft": predicted_soft,
    }

    validation = pd.read_csv(SPLIT_DIR / "temporal_validation_judgments.csv")
    grid_rows: list[dict[str, Any]] = []
    grid_rankings: dict[tuple[str, float], pd.DataFrame] = {}
    for source, matrix in intent_matrices.items():
        for weight in INTENT_WEIGHTS:
            ranking = rank_scores(
                score_with_intent(base, matrix, weight),
                queries["query_id"],
                content["content_id"],
            )
            grid_rankings[(source, weight)] = ranking
            grid_rows.append(
                {
                    "intent_source": source,
                    "intent_weight": weight,
                    **summarize_metrics(evaluate_rankings(ranking, validation)),
                }
            )
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(output_dir / "validation_grid.csv", index=False)
    selected_weights = {source: select_intent_weight(grid, source) for source in INTENT_SOURCES}

    configurations = {
        "without_intent": rank_scores(base, queries["query_id"], content["content_id"]),
        "with_assisted_intent": grid_rankings[("assisted", selected_weights["assisted"])],
        "with_predicted_hard_intent": grid_rankings[("predicted_hard", selected_weights["predicted_hard"])],
        "with_predicted_soft_intent": grid_rankings[("predicted_soft", selected_weights["predicted_soft"])],
        "phase11_R-E7": grid_rankings[("assisted", 0.25)],
    }
    phase11_rankings_path = OUTPUT_DIR / "retrieval" / "phase11" / "rankings.csv.gz"
    phase11_r_e7 = pd.read_csv(phase11_rankings_path).query("experiment == 'R-E7'")
    pd.testing.assert_frame_equal(
        configurations["phase11_R-E7"][["query_id", "content_id", "rank"]].reset_index(drop=True),
        phase11_r_e7[["query_id", "content_id", "rank"]].reset_index(drop=True),
    )
    config_table = pd.DataFrame(
        [
            {"configuration": "without_intent", "intent_source": "none", "intent_weight": 0.0},
            {"configuration": "with_assisted_intent", "intent_source": "assisted", "intent_weight": selected_weights["assisted"]},
            {"configuration": "with_predicted_hard_intent", "intent_source": "predicted_hard", "intent_weight": selected_weights["predicted_hard"]},
            {"configuration": "with_predicted_soft_intent", "intent_source": "predicted_soft", "intent_weight": selected_weights["predicted_soft"]},
            {"configuration": "phase11_R-E7", "intent_source": "assisted", "intent_weight": 0.25},
        ]
    )
    config_table.to_csv(output_dir / "configurations.csv", index=False)
    pd.concat(
        [ranking.assign(configuration=name) for name, ranking in configurations.items()],
        ignore_index=True,
    ).to_csv(output_dir / "rankings.csv.gz", index=False)
    predictions.to_csv(output_dir / "intent_predictions.csv", index=False)

    metric_rows: list[dict[str, Any]] = []
    detail_rows: list[pd.DataFrame] = []
    comparisons: list[dict[str, Any]] = []
    slice_rows: list[dict[str, Any]] = []
    for protocol in ("temporal", "query", "query_dedup"):
        for split in ("validation", "test"):
            judgments = pd.read_csv(SPLIT_DIR / f"{protocol}_{split}_judgments.csv")
            primary: dict[str, pd.DataFrame] = {}
            for name, ranking in configurations.items():
                for scheme, threshold in (
                    ("relevance_grade", 1),
                    ("conservative_relevance_grade", 1),
                    ("event_hierarchy_relevance_grade", 1),
                    ("relevance_grade", 2),
                ):
                    tags = {
                        "protocol": protocol,
                        "split": split,
                        "configuration": name,
                        "scheme": scheme,
                        "threshold": threshold,
                    }
                    per_query = evaluate_rankings(ranking, judgments, scheme, threshold)
                    metric_rows.append({**tags, **summarize_metrics(per_query)})
                    if scheme == "relevance_grade" and threshold == 1:
                        primary[name] = per_query
                        detail_rows.append(per_query.assign(**tags))
            for name in (
                "with_assisted_intent",
                "with_predicted_hard_intent",
                "with_predicted_soft_intent",
                "phase11_R-E7",
            ):
                comparisons.append(
                    {
                        "protocol": protocol,
                        "split": split,
                        "configuration": name,
                        **paired_bootstrap(primary["without_intent"], primary[name]),
                    }
                )
            if protocol == "temporal" and split == "test":
                for name in (
                    "with_assisted_intent",
                    "with_predicted_hard_intent",
                    "with_predicted_soft_intent",
                ):
                    slice_rows.extend(
                        _intent_slice_rows(
                            primary["without_intent"], primary[name], predictions, name
                        )
                    )

    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(output_dir / "metrics.csv", index=False)
    pd.concat(detail_rows, ignore_index=True).to_csv(
        output_dir / "per_query_metrics.csv.gz", index=False
    )
    comparison_table = pd.DataFrame(comparisons)
    comparison_table.to_csv(output_dir / "paired_comparisons.csv", index=False)
    pd.DataFrame(slice_rows).to_csv(output_dir / "intent_slices.csv", index=False)

    primary_comparison = comparison_table[
        comparison_table["protocol"].eq("temporal")
        & comparison_table["split"].eq("test")
        & comparison_table["configuration"].eq("with_predicted_hard_intent")
    ].iloc[0]
    effect = "negligible"
    if selected_weights["predicted_hard"] > 0 and primary_comparison["mean_delta"] > 0:
        effect = (
            "global"
            if primary_comparison["lower_95"] > 0
            else "intent-specific"
        )
    input_paths = [
        CONTENT_PATH,
        INTENT_METADATA_QUERIES_PATH,
        ENRICHED_QUERIES_PATH,
        QUERY_EMBEDDINGS_PATH,
        INTENT_MODEL_PATH,
        SPLIT_DIR / "temporal_validation_judgments.csv",
        SPLIT_DIR / "temporal_test_judgments.csv",
        phase11_rankings_path,
        Path(__file__),
        Path("src/incremental_retrieval.py"),
        Path("src/structured_compatibility.py"),
    ] + caches
    manifest = {
        "phase11_starting_point": "R-E6 equal mean of BM25, dense, entity coverage, and context coverage",
        "primary_runtime_configuration": "with_predicted_hard_intent",
        "intent_weight_grid": list(INTENT_WEIGHTS),
        "selected_weights": selected_weights,
        "selection_metric": "temporal validation NDCG@10; ties choose smaller intent weight",
        "effect_classification": effect,
        "intent_classifier": {
            "artifact": str(INTENT_MODEL_PATH),
            "experiment": "T1-E4",
            "training_labels": "362 retained Phase 3 weak labels; refit model",
            "hard": "argmax predicted intent mapped through the shared compatibility policy",
            "soft": "sum of class probability assigned to intents compatible with each content type",
            "runtime_sklearn_version": sklearn.__version__,
            "serialization_warnings": version_warnings,
        },
        "assisted_intent_role": "reference-label ceiling diagnostic, not an oracle or deployable input",
        "content_policy": {key: sorted(value) for key, value in INTENT_CONTENT_TYPES.items()},
        "queries": len(queries),
        "content_items": len(content),
        "ranking_depth": 20,
        "tie_break": "ascending content_id",
        "test_status": "descriptive; already inspected in earlier phases",
        "limitations": [
            "Behavior-derived relevance is exposure- and position-biased and is not clinician-adjudicated relevance.",
            "The refit intent classifier was trained on assisted weak labels for 362 of these queries; this is a runtime simulation, not an independent intent test.",
            f"The saved Phase 5 model was serialized with scikit-learn 1.5.2 and emits a version warning under the current {sklearn.__version__} environment; predictions succeeded, but exact-version regeneration is preferred.",
            "Content compatibility is a coarse content-type prior and cannot see body sections.",
            "Bootstrap intervals are paired by query, uncorrected for multiplicity, and not cluster-robust.",
        ],
        **runtime,
        "sha256": _sha256(input_paths),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    _update_experiment_log(selected_weights, metrics)
    write_report(output_dir)
    return {
        "output_dir": str(output_dir),
        "selected_weights": selected_weights,
        "effect_classification": effect,
        **runtime,
    }


def _markdown_table(frame: pd.DataFrame) -> str:
    headers = [str(column) for column in frame.columns]
    rows = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    rows.extend(
        "| " + " | ".join(str(value) for value in values) + " |"
        for values in frame.itertuples(index=False, name=None)
    )
    return "\n".join(rows)


def write_report(output_dir: Path = PHASE12_DIR) -> None:
    # The checked-in Phase 12 narrative is curated around the four required
    # assessment headings.  Experiment reruns refresh machine-readable outputs
    # but must not replace that reviewed interpretation with generated prose.
    report_path = Path("write_up") / "phase12_summary.md"
    if report_path.exists():
        return
    manifest = json.loads((output_dir / "manifest.json").read_text())
    metrics = pd.read_csv(output_dir / "metrics.csv")
    comparisons = pd.read_csv(output_dir / "paired_comparisons.csv")
    slices = pd.read_csv(output_dir / "intent_slices.csv")
    predictions = pd.read_csv(output_dir / "intent_predictions.csv")
    primary = metrics[
        metrics["protocol"].eq("temporal")
        & metrics["scheme"].eq("relevance_grade")
        & metrics["threshold"].eq(1)
    ]
    table = primary.pivot(
        index="configuration", columns="split", values=["ndcg@10", "recall@10", "mrr@10"]
    )
    table.columns = [f"{split}_{metric}" for metric, split in table.columns]
    table = table.reset_index()[
        [
            "configuration",
            "validation_ndcg@10",
            "test_ndcg@10",
            "validation_recall@10",
            "test_recall@10",
            "validation_mrr@10",
            "test_mrr@10",
        ]
    ].round(5)
    paired = comparisons[
        comparisons["protocol"].eq("temporal")
        & comparisons["split"].eq("test")
    ][
        [
            "configuration",
            "eligible_queries",
            "mean_delta",
            "lower_95",
            "upper_95",
            "improved_queries",
            "worsened_queries",
            "unchanged_queries",
        ]
    ].round(5)
    primary_slices = slices[slices["configuration"].eq("with_predicted_hard_intent")].copy()
    primary_slices = primary_slices.sort_values("delta_ndcg@10", ascending=False).round(5)
    agreement = float(predictions["agrees_with_assisted"].mean())
    weights = manifest["selected_weights"]
    text = "\n\n".join(
        [
            "# Phase 12 — Connecting Intent to Retrieval",
            "Phase 12 starts from Phase 11 R-E6, the equal mean of normalized BM25, frozen dense similarity, entity coverage, and contextual coverage. Those four components are frozen. Only a non-negative intent coefficient is selected using temporal validation NDCG@10; the test split is opened after selection and remains descriptive because earlier phases already inspected it.",
            "## Intent inputs and scoring",
            "The assisted Phase 3 label is retained only as a reference-label ceiling diagnostic. The runtime path uses the saved Phase 5 T1-E4 classifier. Hard compatibility maps its argmax class to allowed content types and is the primary deployable comparison because it had the strongest validation result. Soft compatibility sums predicted probability across all intents compatible with each content type and is retained as an uncertainty-aware diagnostic. Both paths reuse the exact Phase 7.5 intent/content policy. The ranker is `R-E6 + epsilon * intent_compatibility`; epsilon candidates were 0, 0.025, 0.05, 0.10, 0.20, 0.25, 0.50, and 1.00.",
            f"Validation selected epsilon={weights['assisted']:.3f} for assisted intent, {weights['predicted_hard']:.3f} for predicted hard intent, and {weights['predicted_soft']:.3f} for predicted soft intent. The classifier argmax agrees with the assisted label on {agreement:.1%} of all 500 queries. This agreement is descriptive: the refit classifier was trained on retained assisted weak labels for 362 queries.",
            "## Global results",
            _markdown_table(table),
            "Candidate-minus-no-intent paired test deltas use a 2,000-resample query bootstrap (seed 42). Intervals are descriptive, uncorrected for multiplicity, and not cluster-robust.",
            _markdown_table(paired),
            f"The runtime conclusion is **{manifest['effect_classification']}**, not global. The predicted-hard point estimate is positive, but its interval spans zero and only a small subset of eligible queries changes; the intent slices below show where that movement is concentrated.",
            "## Runtime predicted-hard effect by assisted intent",
            _markdown_table(
                primary_slices[
                    [
                        "assisted_intent",
                        "eligible_queries",
                        "baseline_ndcg@10",
                        "candidate_ndcg@10",
                        "delta_ndcg@10",
                        "improved_queries",
                        "worsened_queries",
                        "classifier_agreement",
                    ]
                ]
            ),
            "## Interpretation and limitations",
            "This experiment connects an actual saved intent classifier to retrieval rather than treating assisted intent as a deployable feature. It also reproduces Phase 11 R-E7 exactly at assisted epsilon=0.25, providing a parity check on the starting point. The assisted comparison is not called oracle performance: the labels are model-assisted, single-reviewer weak references.",
            "The compatibility policy is intentionally coarse. A content type may contain the requested answer in a body section even when its type is not on the allow-list, and binary hard compatibility can demote such useful material. The probability-weighted diagnostic used a much smaller validation-selected coefficient and barely moved test rankings; uncertainty smoothing did not provide a global solution. Absolute metrics remain low because judgments cover only exposed documents and inherit exposure, position, and engagement bias. Unjudged items receive zero computational gain, not a clinical-negative label.",
            f"The saved Phase 5 estimator was serialized under scikit-learn 1.5.2 and emitted compatibility warnings under the current {sklearn.__version__} environment. Inference and parity checks completed, but a submission environment should reproduce the original library version or regenerate the model and revalidate its predictions.",
            "Artifacts: validation_grid.csv, configurations.csv, rankings.csv.gz, metrics.csv, per_query_metrics.csv.gz, paired_comparisons.csv, intent_slices.csv, intent_predictions.csv, and manifest.json. The notebook exposes a compact reproducible Phase 12 entry point.",
        ]
    ) + "\n"
    report_path.write_text(text)


if __name__ == "__main__":
    print(json.dumps(build_phase12_artifacts(), indent=2))
