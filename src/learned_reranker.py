"""Phase 15: CPU-friendly learned reranking experiment.

The frozen Phase 12 predicted-intent ranker is the comparator.  Logistic
rerankers are trained only on temporal-train behavioral judgments, selected on
temporal-validation NDCG@10, and evaluated on the temporal test split after
selection.

Run with ``.venv/bin/python -m src.learned_reranker``.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import CONFIG, CONTENT_PATH, EXPERIMENT_LOG_PATH, OUTPUT_DIR
from src.evaluation import evaluate_rankings, summarize_metrics
from src.evaluation_split import SPLIT_DIR
from src.incremental_retrieval import build_signals, combine, rank_scores
from src.intent import LABELED_QUERIES_PATH
from src.intent_retrieval import PHASE12_DIR, paired_bootstrap
from src.structured_compatibility import INTENT_CONTENT_TYPES


PHASE15_DIR = OUTPUT_DIR / "retrieval" / "phase15"
POINTWISE_C = (0.001, 0.01, 0.1, 1.0, 10.0, 100.0)
PAIRWISE_C = (0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0)
PAIR_FEATURES = (
    "disease_match",
    "disease_hierarchical_match",
    "molecule_match",
    "drug_class_match",
    "molecule_hierarchical_match",
    "therapeutic_area_match",
    "entity_query_count",
    "entity_exact_match_count",
    "entity_augmented_match_count",
    "entity_conflict_count",
    "entity_coverage",
    "entity_augmented_coverage",
    "entity_conflict_rate",
    "age_group_match",
    "age_group_conflict",
    "pregnancy_match",
    "pregnancy_conflict",
    "year_match",
    "year_distance",
    "year_conflict",
    "recency_match",
    "recency_conflict",
    "dose_context_match",
    "route_match",
    "route_conflict",
    "renal_context_match",
    "renal_exact_match",
    "renal_context_conflict",
    "hepatic_context_match",
    "comparison_context_match",
    "prior_failure_context_match",
    "context_constraint_count",
    "context_match_count",
    "context_conflict_count",
    "context_coverage",
    "context_conflict_rate",
    "structured_score",
    "structured_conflict_rate",
)


def predicted_intent_compatibility(
    predictions: pd.DataFrame, queries: pd.DataFrame, content: pd.DataFrame
) -> np.ndarray:
    """Map saved Phase 12 hard intent predictions to content-type compatibility."""
    if predictions["query_id"].duplicated().any():
        raise ValueError("Intent predictions must have unique query IDs")
    predicted = predictions.set_index("query_id")["predicted_intent"].reindex(
        queries["query_id"]
    )
    if predicted.isna().any():
        raise ValueError("Missing predicted intent for at least one query")
    return np.asarray(
        [
            [
                content_type in INTENT_CONTENT_TYPES.get(str(intent), set())
                for content_type in content["content_type"]
            ]
            for intent in predicted
        ],
        dtype=float,
    )


def build_feature_matrix(
    signals: dict[str, np.ndarray],
    pairs: pd.DataFrame,
    queries: pd.DataFrame,
    content: pd.DataFrame,
    predicted_intent: np.ndarray,
    baseline_score: np.ndarray,
) -> tuple[np.ndarray, list[str]]:
    """Build finite full-corpus pointwise features in query-major order."""
    expected_shape = (len(queries), len(content))
    for name in ("bm25", "dense", "entities", "context"):
        if signals[name].shape != expected_shape:
            raise ValueError(f"Unexpected {name} shape")
    if predicted_intent.shape != expected_shape or baseline_score.shape != expected_shape:
        raise ValueError("Intent and baseline matrices must be query by content")
    expected_pairs = pd.MultiIndex.from_product(
        [queries["query_id"], content["content_id"]], names=["query_id", "content_id"]
    )
    actual_pairs = pd.MultiIndex.from_frame(pairs[["query_id", "content_id"]])
    if not actual_pairs.equals(expected_pairs):
        raise ValueError("Compatibility rows are not in query-major full-corpus order")

    core_names = [
        "bm25_score",
        "dense_similarity",
        "predicted_intent_compatibility",
        "phase12_baseline_score",
        *PAIR_FEATURES,
    ]
    core = np.column_stack(
        [
            signals["bm25"].ravel(),
            signals["dense"].ravel(),
            predicted_intent.ravel(),
            baseline_score.ravel(),
            pairs.loc[:, PAIR_FEATURES].fillna(0).astype(float).to_numpy(),
        ]
    )
    position = {name: index for index, name in enumerate(core_names)}
    interaction_names = [
        "bm25_x_entity_coverage",
        "dense_x_entity_coverage",
        "entity_x_context_coverage",
        "entity_x_predicted_intent",
    ]
    interactions = np.column_stack(
        [
            core[:, position["bm25_score"]] * core[:, position["entity_coverage"]],
            core[:, position["dense_similarity"]]
            * core[:, position["entity_coverage"]],
            core[:, position["entity_coverage"]]
            * core[:, position["context_coverage"]],
            core[:, position["entity_coverage"]]
            * core[:, position["predicted_intent_compatibility"]],
        ]
    )

    content_types = pd.get_dummies(
        content["content_type"], prefix="content_type", dtype=float
    )
    repeated_types = np.tile(content_types.to_numpy(), (len(queries), 1))
    publication_year = np.tile(
        (content["publication_year"] - content["publication_year"].mean())
        .fillna(0)
        .to_numpy(),
        len(queries),
    )[:, None]
    word_count = np.tile(
        np.log1p(content["word_count"].fillna(0).to_numpy()), len(queries)
    )[:, None]
    language_compatible = (
        pairs["query_language"].eq(pairs["content_language"])
        | pairs["query_language"].eq("MIXED")
        | pairs["content_language"].eq("MIXED")
    ).astype(float).to_numpy()[:, None]
    names = [
        *core_names,
        *interaction_names,
        *content_types.columns.tolist(),
        "publication_year_centered",
        "log_word_count",
        "language_compatible",
    ]
    matrix = np.column_stack(
        [core, interactions, repeated_types, publication_year, word_count, language_compatible]
    )
    if matrix.shape != (len(pairs), len(names)) or not np.isfinite(matrix).all():
        raise AssertionError("Learned-reranker feature matrix is invalid")
    return matrix, names


def pair_indices(pairs: pd.DataFrame, judgments: pd.DataFrame) -> np.ndarray:
    """Locate judged pairs in the full-corpus feature matrix."""
    index = pd.MultiIndex.from_frame(pairs[["query_id", "content_id"]])
    positions = index.get_indexer(
        pd.MultiIndex.from_frame(judgments[["query_id", "content_id"]])
    )
    if (positions < 0).any():
        raise ValueError("A judged pair is absent from the feature matrix")
    return positions


def build_pairwise_training(
    features: np.ndarray, judgments: pd.DataFrame, indices: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create balanced within-query feature differences with equal query mass."""
    if len(judgments) != len(indices):
        raise ValueError("Judgments and indices must align")
    working = judgments[["query_id", "relevance_grade"]].copy()
    working["feature_index"] = indices
    differences: list[np.ndarray] = []
    labels: list[int] = []
    weights: list[float] = []
    for _, group in working.groupby("query_id", sort=True):
        rows = group[["feature_index", "relevance_grade"]].to_numpy(dtype=int)
        ordered_pairs: list[tuple[int, int, int]] = []
        for left in range(len(rows)):
            for right in range(left + 1, len(rows)):
                if rows[left, 1] == rows[right, 1]:
                    continue
                high, low = (
                    (rows[left], rows[right])
                    if rows[left, 1] > rows[right, 1]
                    else (rows[right], rows[left])
                )
                ordered_pairs.append(
                    (int(high[0]), int(low[0]), int(high[1] - low[1]))
                )
        if not ordered_pairs:
            continue
        grade_gap_total = sum(grade_gap for _, _, grade_gap in ordered_pairs)
        for high, low, grade_gap in ordered_pairs:
            difference = features[high] - features[low]
            differences.extend((difference, -difference))
            labels.extend((1, 0))
            weight = grade_gap / grade_gap_total
            weights.extend((weight, weight))
    if not differences:
        raise ValueError("No unequal-grade pairs available for pairwise training")
    return np.asarray(differences), np.asarray(labels), np.asarray(weights)


def select_candidate(validation_grid: pd.DataFrame) -> str:
    """Select validation NDCG@10; prefer pointwise, balanced, then smaller C on ties."""
    candidates = validation_grid[validation_grid["family"].ne("baseline")].copy()
    if candidates.empty:
        raise ValueError("No learned candidate rows")
    candidates["family_order"] = candidates["family"].map(
        {"pointwise": 0, "pairwise": 1}
    )
    candidates["balance_order"] = candidates["class_weight"].map(
        {"balanced": 0, "none": 1, "not_applicable": 2}
    )
    return str(
        candidates.sort_values(
            ["ndcg@10", "family_order", "balance_order", "C", "configuration"],
            ascending=[False, True, True, True, True],
        ).iloc[0]["configuration"]
    )


def fit_candidates(
    features: np.ndarray,
    pairs: pd.DataFrame,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    queries: pd.DataFrame,
    content: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Pipeline], dict[str, np.ndarray]]:
    """Fit the predefined pointwise and pairwise grids on temporal train only."""
    train_indices = pair_indices(pairs, train)
    binary_labels = train["relevance_grade"].ge(1).astype(int).to_numpy()
    difference, pair_labels, pair_weights = build_pairwise_training(
        features, train, train_indices
    )
    rows: list[dict[str, Any]] = []
    models: dict[str, Pipeline] = {}
    scores: dict[str, np.ndarray] = {}

    os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")
    for class_weight in (None, "balanced"):
        for c_value in POINTWISE_C:
            name = f"pointwise_{class_weight or 'none'}_C{c_value:g}"
            model = make_pipeline(
                StandardScaler(),
                LogisticRegression(
                    C=c_value,
                    class_weight=class_weight,
                    max_iter=3000,
                    random_state=CONFIG.random_seed,
                ),
            )
            model.fit(features[train_indices], binary_labels)
            score = model.decision_function(features)
            ranking = rank_scores(
                score.reshape(len(queries), len(content)),
                queries["query_id"],
                content["content_id"],
            )
            rows.append(
                {
                    "configuration": name,
                    "family": "pointwise",
                    "class_weight": class_weight or "none",
                    "C": c_value,
                    **summarize_metrics(evaluate_rankings(ranking, validation)),
                }
            )
            models[name], scores[name] = model, score

    for c_value in PAIRWISE_C:
        name = f"pairwise_C{c_value:g}"
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=c_value,
                fit_intercept=False,
                max_iter=3000,
                random_state=CONFIG.random_seed,
            ),
        )
        model.fit(
            difference,
            pair_labels,
            logisticregression__sample_weight=pair_weights,
        )
        score = model.decision_function(features)
        ranking = rank_scores(
            score.reshape(len(queries), len(content)),
            queries["query_id"],
            content["content_id"],
        )
        rows.append(
            {
                "configuration": name,
                "family": "pairwise",
                "class_weight": "not_applicable",
                "C": c_value,
                **summarize_metrics(evaluate_rankings(ranking, validation)),
            }
        )
        models[name], scores[name] = model, score
    return pd.DataFrame(rows), models, scores


def _coefficient_table(model: Pipeline, feature_names: list[str]) -> pd.DataFrame:
    coefficients = model.named_steps["logisticregression"].coef_[0]
    result = pd.DataFrame(
        {"feature": feature_names, "standardized_coefficient": coefficients}
    )
    result["absolute_coefficient"] = result["standardized_coefficient"].abs()
    return result.sort_values(
        ["absolute_coefficient", "feature"], ascending=[False, True]
    ).reset_index(drop=True)


def _sha256(paths: list[Path]) -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _update_experiment_log(metrics: pd.DataFrame, selected: str) -> None:
    primary = metrics.query(
        "scheme == 'relevance_grade' and threshold == 1"
    ).set_index(["split", "configuration"])
    baseline_validation = primary.loc[("validation", "phase12_baseline"), "ndcg@10"]
    learned_validation = primary.loc[("validation", "selected_learned_reranker"), "ndcg@10"]
    baseline_test = primary.loc[("test", "phase12_baseline"), "ndcg@10"]
    learned_test = primary.loc[("test", "selected_learned_reranker"), "ndcg@10"]
    row = {
        "experiment": "R-LTR",
        "hypothesis": "a CPU-friendly learned reranker improves the frozen runtime ranker",
        "method": f"temporal-train logistic reranker; validation selected {selected}",
        "primary_metric": "NDCG@10",
        "result": (
            f"Validation {baseline_validation:.5f}->{learned_validation:.5f}; "
            f"test {baseline_test:.5f}->{learned_test:.5f}"
        ),
        "decision": "not selected; validation gain did not generalize to temporal test",
    }
    log = pd.read_csv(EXPERIMENT_LOG_PATH)
    log = pd.concat(
        [log[~log["experiment"].eq(row["experiment"])], pd.DataFrame([row])],
        ignore_index=True,
    )
    log.to_csv(EXPERIMENT_LOG_PATH, index=False)


def build_phase15_artifacts(output_dir: Path = PHASE15_DIR) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    queries = pd.read_csv(LABELED_QUERIES_PATH).sort_values("query_id").reset_index(drop=True)
    content = pd.read_csv(CONTENT_PATH).sort_values("content_id").reset_index(drop=True)
    predictions_path = PHASE12_DIR / "intent_predictions.csv"
    phase12_config_path = PHASE12_DIR / "configurations.csv"
    phase12_rankings_path = PHASE12_DIR / "rankings.csv.gz"
    predictions = pd.read_csv(predictions_path)
    phase12_config = pd.read_csv(phase12_config_path)
    intent_weight = float(
        phase12_config.loc[
            phase12_config["configuration"].eq("with_predicted_hard_intent"),
            "intent_weight",
        ].iloc[0]
    )
    signals, pairs, runtime, caches = build_signals(queries, content)
    predicted_intent = predicted_intent_compatibility(predictions, queries, content)
    baseline_score = combine(signals, ("bm25", "dense", "entities", "context"))
    baseline_score = baseline_score + intent_weight * predicted_intent
    baseline_ranking = rank_scores(
        baseline_score, queries["query_id"], content["content_id"]
    )
    saved_baseline = pd.read_csv(phase12_rankings_path).query(
        "configuration == 'with_predicted_hard_intent'"
    )
    pd.testing.assert_frame_equal(
        baseline_ranking[["query_id", "content_id", "rank"]].reset_index(drop=True),
        saved_baseline[["query_id", "content_id", "rank"]].reset_index(drop=True),
    )

    features, feature_names = build_feature_matrix(
        signals, pairs, queries, content, predicted_intent, baseline_score
    )
    train_path = SPLIT_DIR / "temporal_train_judgments.csv"
    validation_path = SPLIT_DIR / "temporal_validation_judgments.csv"
    test_path = SPLIT_DIR / "temporal_test_judgments.csv"
    train = pd.read_csv(train_path)
    validation = pd.read_csv(validation_path)
    grid, models, scores = fit_candidates(
        features, pairs, train, validation, queries, content
    )
    baseline_validation = summarize_metrics(
        evaluate_rankings(baseline_ranking, validation)
    )
    grid = pd.concat(
        [
            pd.DataFrame(
                [
                    {
                        "configuration": "phase12_baseline",
                        "family": "baseline",
                        "class_weight": "not_applicable",
                        "C": np.nan,
                        **baseline_validation,
                    }
                ]
            ),
            grid,
        ],
        ignore_index=True,
    )
    grid.to_csv(output_dir / "validation_grid.csv", index=False)
    selected = select_candidate(grid)
    selected_model = models[selected]
    selected_ranking = rank_scores(
        scores[selected].reshape(len(queries), len(content)),
        queries["query_id"],
        content["content_id"],
    )
    joblib.dump(selected_model, output_dir / "selected_model.joblib")
    _coefficient_table(selected_model, feature_names).to_csv(
        output_dir / "feature_coefficients.csv", index=False
    )
    configurations = pd.DataFrame(
        [
            {
                "configuration": "phase12_baseline",
                "source": "frozen Phase 12 predicted-hard ranker",
                "selected_candidate": False,
            },
            {
                "configuration": "selected_learned_reranker",
                "source": selected,
                "selected_candidate": True,
            },
        ]
    )
    configurations.to_csv(output_dir / "configurations.csv", index=False)
    rankings = {
        "phase12_baseline": baseline_ranking,
        "selected_learned_reranker": selected_ranking,
    }
    pd.concat(
        [ranking.assign(configuration=name) for name, ranking in rankings.items()],
        ignore_index=True,
    ).to_csv(output_dir / "rankings.csv.gz", index=False)

    metric_rows: list[dict[str, Any]] = []
    details: list[pd.DataFrame] = []
    comparison_rows: list[dict[str, Any]] = []
    for split, judgments in (("validation", validation), ("test", pd.read_csv(test_path))):
        primary: dict[str, pd.DataFrame] = {}
        for name, ranking in rankings.items():
            for scheme, threshold in (
                ("relevance_grade", 1),
                ("conservative_relevance_grade", 1),
                ("event_hierarchy_relevance_grade", 1),
                ("relevance_grade", 2),
            ):
                tags = {
                    "protocol": "temporal",
                    "split": split,
                    "configuration": name,
                    "scheme": scheme,
                    "threshold": threshold,
                }
                per_query = evaluate_rankings(ranking, judgments, scheme, threshold)
                metric_rows.append({**tags, **summarize_metrics(per_query)})
                if scheme == "relevance_grade" and threshold == 1:
                    primary[name] = per_query
                    details.append(per_query.assign(**tags))
        comparison_rows.append(
            {
                "protocol": "temporal",
                "split": split,
                "candidate": "selected_learned_reranker",
                "reference": "phase12_baseline",
                **paired_bootstrap(
                    primary["phase12_baseline"],
                    primary["selected_learned_reranker"],
                ),
            }
        )
    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(output_dir / "metrics.csv", index=False)
    pd.concat(details, ignore_index=True).to_csv(
        output_dir / "per_query_metrics.csv.gz", index=False
    )
    comparisons = pd.DataFrame(comparison_rows)
    comparisons.to_csv(output_dir / "paired_comparisons.csv", index=False)

    train_indices = pair_indices(pairs, train)
    training_summary = pd.DataFrame(
        [
            {
                "training_judgments": len(train),
                "training_queries": train["query_id"].nunique(),
                "positive_judgments": int(train["relevance_grade"].ge(1).sum()),
                "nonpositive_judgments": int(train["relevance_grade"].eq(0).sum()),
                "feature_count": len(feature_names),
                "candidate_models": len(models),
                "selected_candidate": selected,
                "all_training_pairs_found": bool((train_indices >= 0).all()),
            }
        ]
    )
    training_summary.to_csv(output_dir / "training_summary.csv", index=False)

    test_comparison = comparisons[comparisons["split"].eq("test")].iloc[0]
    selected_grid = grid[grid["configuration"].eq(selected)].iloc[0]
    input_paths = [
        CONTENT_PATH,
        LABELED_QUERIES_PATH,
        predictions_path,
        phase12_config_path,
        phase12_rankings_path,
        train_path,
        validation_path,
        test_path,
        *caches,
        Path(__file__),
        Path("src/incremental_retrieval.py"),
        Path("src/evaluation.py"),
    ]
    manifest = {
        "objective": "test the planned CPU-friendly learned-reranker extension",
        "starting_point": "frozen Phase 12 with_predicted_hard_intent",
        "training_split": "temporal train only",
        "selection": "maximum temporal-validation NDCG@10; deterministic tie rules",
        "selected_candidate": selected,
        "selected_validation_ndcg@10": float(selected_grid["ndcg@10"]),
        "pointwise_C": list(POINTWISE_C),
        "pairwise_C": list(PAIRWISE_C),
        "label": "relevance_grade >= 1 for pointwise; ordered grades for pairwise",
        "features": feature_names,
        "queries": len(queries),
        "content_items": len(content),
        "ranking_depth": 20,
        "test_outcome": (
            "improved"
            if test_comparison["mean_delta"] > 0
            else "not improved"
        ),
        "test_status": "descriptive because previous phases inspected this split",
        "limitations": [
            "Behavior-derived grades are sparse, exposure- and position-biased proxies rather than clinician judgments.",
            "Only exposed temporal-train pairs supervise the pointwise and pairwise objectives.",
            "A pointwise logistic objective does not directly optimize NDCG; pairwise logistic is retained as a validation diagnostic.",
            "Query and query-deduplicated protocols are not reported because this model was trained against the temporal split.",
            "Titles and metadata cannot establish answer completeness or clinical correctness.",
        ],
        **runtime,
        "selected_model_sha256": hashlib.sha256(
            (output_dir / "selected_model.joblib").read_bytes()
        ).hexdigest(),
        "sha256": _sha256(input_paths),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    _update_experiment_log(metrics, selected)
    return {
        "output_dir": str(output_dir),
        "selected_candidate": selected,
        "validation_ndcg@10": float(selected_grid["ndcg@10"]),
        "test_delta_ndcg@10": float(test_comparison["mean_delta"]),
        "test_outcome": manifest["test_outcome"],
    }


if __name__ == "__main__":
    print(json.dumps(build_phase15_artifacts(), indent=2))
