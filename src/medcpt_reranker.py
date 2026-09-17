"""Frozen NCBI MedCPT cross-encoder reranking experiment.

This deliberately mirrors ``src.cross_encoder_reranker`` so the only material
experimental change is the pretrained checkpoint.

Run with ``.venv/bin/python -m src.medcpt_reranker``.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sentence_transformers import CrossEncoder

from src.config import CACHE_DIR, CONTENT_PATH, EXPERIMENT_LOG_PATH, OUTPUT_DIR
from src.cross_encoder_reranker import (
    BLEND_WEIGHTS,
    CANDIDATE_DEPTHS,
    MAX_CANDIDATE_DEPTH,
    baseline_candidate_indices,
    rerank_candidate_pool,
    select_configuration,
)
from src.evaluation import evaluate_rankings, summarize_metrics
from src.evaluation_split import SPLIT_DIR
from src.incremental_retrieval import build_signals, combine, rank_scores
from src.intent import LABELED_QUERIES_PATH
from src.intent_retrieval import PHASE12_DIR, paired_bootstrap
from src.learned_reranker import predicted_intent_compatibility


OUTPUT = OUTPUT_DIR / "retrieval" / "phase15_medcpt"
MODEL_ID = "ncbi/MedCPT-Cross-Encoder"
MODEL_REVISION = "c92e08d007b2625aca1227cd991f28935e55f2fd"
SCORE_CACHE = CACHE_DIR / "phase15_medcpt_cross_encoder_scores.npz"


def _fingerprint(
    queries: pd.DataFrame,
    content: pd.DataFrame,
    candidate_indices: np.ndarray,
) -> str:
    digest = hashlib.sha256()
    digest.update(MODEL_ID.encode())
    digest.update(MODEL_REVISION.encode())
    digest.update("\n".join(queries["query_text"].astype(str)).encode())
    digest.update("\n".join(content["title"].fillna("").astype(str)).encode())
    digest.update(candidate_indices.tobytes())
    return digest.hexdigest()


def load_or_score(
    queries: pd.DataFrame,
    content: pd.DataFrame,
    candidate_indices: np.ndarray,
    cache_path: Path = SCORE_CACHE,
) -> tuple[np.ndarray, float, bool]:
    """Load fingerprinted scores or run frozen MedCPT locally on CPU."""
    fingerprint = _fingerprint(queries, content, candidate_indices)
    if cache_path.exists():
        archive = np.load(cache_path, allow_pickle=False)
        if str(archive["fingerprint"].item()) == fingerprint:
            scores = archive["scores"]
            if scores.shape == candidate_indices.shape and np.isfinite(scores).all():
                return scores, float(archive["inference_seconds"].item()), True

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    model = CrossEncoder(
        MODEL_ID,
        revision=MODEL_REVISION,
        device="cpu",
        local_files_only=True,
    )
    pairs = [
        (query, title)
        for query, indices in zip(
            queries["query_text"].astype(str), candidate_indices, strict=True
        )
        for title in content.iloc[indices]["title"].fillna("").astype(str)
    ]
    start = time.perf_counter()
    # Short query-title pairs amortize CPU overhead best at 128 on the target
    # laptop; this changes throughput only, not logits or candidate selection.
    values = model.predict(pairs, batch_size=128, show_progress_bar=True)
    seconds = time.perf_counter() - start
    scores = np.asarray(values, dtype=float).reshape(candidate_indices.shape)
    if not np.isfinite(scores).all():
        raise ValueError("MedCPT returned invalid scores")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        cache_path,
        scores=scores,
        fingerprint=np.asarray(fingerprint),
        inference_seconds=np.asarray(seconds),
        model_id=np.asarray(MODEL_ID),
        model_revision=np.asarray(MODEL_REVISION),
    )
    return scores, seconds, False


def _sha256(paths: list[Path]) -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _update_experiment_log(metrics: pd.DataFrame, depth: int, weight: float) -> None:
    primary = metrics.query(
        "scheme == 'relevance_grade' and threshold == 1"
    ).set_index(["split", "configuration"])
    base_validation = primary.loc[("validation", "phase12_baseline"), "ndcg@10"]
    model_validation = primary.loc[("validation", "selected_medcpt"), "ndcg@10"]
    base_test = primary.loc[("test", "phase12_baseline"), "ndcg@10"]
    model_test = primary.loc[("test", "selected_medcpt"), "ndcg@10"]
    row = {
        "experiment": "R-MEDCPT",
        "hypothesis": "a PubMed-trained cross-encoder improves clinical title reranking",
        "method": f"{MODEL_ID}; Phase 12 top-{depth}; validation-selected blend={weight:g}",
        "primary_metric": "NDCG@10",
        "result": (
            f"Validation {base_validation:.5f}->{model_validation:.5f}; "
            f"test {base_test:.5f}->{model_test:.5f}"
        ),
        "decision": (
            "retain MedCPT challenger; descriptive test gain"
            if model_test > base_test
            else "not selected; no temporal-test improvement"
        ),
    }
    log = pd.read_csv(EXPERIMENT_LOG_PATH)
    log = pd.concat(
        [log[~log["experiment"].eq(row["experiment"])], pd.DataFrame([row])],
        ignore_index=True,
    )
    log.to_csv(EXPERIMENT_LOG_PATH, index=False)


def build_medcpt_artifacts(output_dir: Path = OUTPUT) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    queries = pd.read_csv(LABELED_QUERIES_PATH).sort_values("query_id").reset_index(drop=True)
    content = pd.read_csv(CONTENT_PATH).sort_values("content_id").reset_index(drop=True)
    predictions_path = PHASE12_DIR / "intent_predictions.csv"
    configuration_path = PHASE12_DIR / "configurations.csv"
    phase12_rankings_path = PHASE12_DIR / "rankings.csv.gz"
    predictions = pd.read_csv(predictions_path)
    configurations = pd.read_csv(configuration_path)
    intent_weight = float(
        configurations.loc[
            configurations["configuration"].eq("with_predicted_hard_intent"),
            "intent_weight",
        ].iloc[0]
    )
    signals, _, runtime, caches = build_signals(queries, content)
    predicted_intent = predicted_intent_compatibility(predictions, queries, content)
    baseline_scores = combine(signals, ("bm25", "dense", "entities", "context"))
    baseline_scores += intent_weight * predicted_intent
    baseline_ranking = rank_scores(
        baseline_scores, queries["query_id"], content["content_id"]
    )
    saved_baseline = pd.read_csv(phase12_rankings_path).query(
        "configuration == 'with_predicted_hard_intent'"
    )
    pd.testing.assert_frame_equal(
        baseline_ranking[["query_id", "content_id", "rank"]].reset_index(drop=True),
        saved_baseline[["query_id", "content_id", "rank"]].reset_index(drop=True),
    )

    candidate_indices = baseline_candidate_indices(
        baseline_scores, content["content_id"], MAX_CANDIDATE_DEPTH
    )
    model_scores, inference_seconds, cache_hit = load_or_score(
        queries, content, candidate_indices
    )
    validation_path = SPLIT_DIR / "temporal_validation_judgments.csv"
    test_path = SPLIT_DIR / "temporal_test_judgments.csv"
    validation = pd.read_csv(validation_path)
    grid_rows: list[dict[str, Any]] = []
    grid_rankings: dict[tuple[int, float], pd.DataFrame] = {}
    for depth in CANDIDATE_DEPTHS:
        for weight in BLEND_WEIGHTS:
            ranking = rerank_candidate_pool(
                baseline_scores,
                candidate_indices,
                model_scores,
                queries["query_id"],
                content["content_id"],
                depth,
                weight,
            )
            grid_rankings[(depth, weight)] = ranking
            grid_rows.append(
                {
                    "candidate_depth": depth,
                    "medcpt_weight": weight,
                    **summarize_metrics(evaluate_rankings(ranking, validation)),
                }
            )
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(output_dir / "validation_grid.csv", index=False)
    selection_view = grid.rename(columns={"medcpt_weight": "cross_weight"})
    selected_depth, selected_weight = select_configuration(selection_view)
    selected_ranking = grid_rankings[(selected_depth, selected_weight)]
    pd.DataFrame(
        [
            {
                "configuration": "phase12_baseline",
                "candidate_depth": 0,
                "medcpt_weight": 0.0,
            },
            {
                "configuration": "selected_medcpt",
                "candidate_depth": selected_depth,
                "medcpt_weight": selected_weight,
            },
        ]
    ).to_csv(output_dir / "configurations.csv", index=False)
    rankings = {
        "phase12_baseline": baseline_ranking,
        "selected_medcpt": selected_ranking,
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
                "candidate": "selected_medcpt",
                "reference": "phase12_baseline",
                **paired_bootstrap(
                    primary["phase12_baseline"], primary["selected_medcpt"]
                ),
            }
        )
    metrics = pd.DataFrame(metric_rows)
    comparisons = pd.DataFrame(comparison_rows)
    metrics.to_csv(output_dir / "metrics.csv", index=False)
    comparisons.to_csv(output_dir / "paired_comparisons.csv", index=False)
    pd.concat(details, ignore_index=True).to_csv(
        output_dir / "per_query_metrics.csv.gz", index=False
    )

    test_comparison = comparisons[comparisons["split"].eq("test")].iloc[0]
    input_paths = [
        CONTENT_PATH,
        LABELED_QUERIES_PATH,
        predictions_path,
        configuration_path,
        phase12_rankings_path,
        validation_path,
        test_path,
        SCORE_CACHE,
        *caches,
        Path(__file__),
        Path("src/cross_encoder_reranker.py"),
        Path("src/evaluation.py"),
    ]
    manifest = {
        "model": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_role": "frozen PubMed-trained query-title cross-encoder",
        "training_on_project_labels": False,
        "starting_point": "Phase 12 with_predicted_hard_intent",
        "candidate_depths": list(CANDIDATE_DEPTHS),
        "blend_weights": list(BLEND_WEIGHTS),
        "selection": "temporal-validation NDCG@10; ties prefer shallower pool then lower MedCPT weight",
        "selected_candidate_depth": selected_depth,
        "selected_medcpt_weight": selected_weight,
        "inference_seconds": inference_seconds,
        "score_cache_hit": cache_hit,
        "scored_pairs": int(candidate_indices.size),
        "test_delta_ndcg@10": float(test_comparison["mean_delta"]),
        "test_status": "descriptive because earlier phases inspected the split",
        "limitations": [
            "MedCPT was trained from PubMed search behavior, not clinician-adjudicated bedside relevance.",
            "The English-focused checkpoint may not transfer reliably to Indonesian and mixed-language queries.",
            "Only titles are available; body-section evidence cannot influence scores.",
            "The Phase 12 candidate generator bounds recall.",
            "Behavior-derived evaluation grades are sparse engagement proxies.",
        ],
        **runtime,
        "sha256": _sha256(input_paths),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    _update_experiment_log(metrics, selected_depth, selected_weight)
    return {
        "output_dir": str(output_dir),
        "selected_candidate_depth": selected_depth,
        "selected_medcpt_weight": selected_weight,
        "test_delta_ndcg@10": float(test_comparison["mean_delta"]),
        "score_cache_hit": cache_hit,
        "inference_seconds": inference_seconds,
    }


if __name__ == "__main__":
    print(json.dumps(build_medcpt_artifacts(), indent=2))
