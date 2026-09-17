"""Frozen S-PubMedBERT dense-embedding experiment.

This keeps every Phase 12 runtime signal fixed and changes only the dense
similarity matrix. Run with
``.venv/bin/python -m src.pubmedbert_embedding_experiment``.
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
from sentence_transformers import SentenceTransformer

from src.config import CACHE_DIR, CONTENT_PATH, EXPERIMENT_LOG_PATH, OUTPUT_DIR
from src.evaluation import evaluate_rankings, summarize_metrics
from src.evaluation_split import SPLIT_DIR
from src.incremental_retrieval import build_signals, combine, rank_scores
from src.intent import LABELED_QUERIES_PATH
from src.intent_retrieval import PHASE12_DIR, paired_bootstrap
from src.learned_reranker import predicted_intent_compatibility


OUTPUT = OUTPUT_DIR / "retrieval" / "phase15_pubmedbert_embeddings"
MODEL_ID = "pritamdeka/S-PubMedBert-MS-MARCO"
MODEL_REVISION = "96786c7024f95c5aac7f2b9a18086c7b97b23036"
QUERY_CACHE = CACHE_DIR / "phase15_pubmedbert_query_embeddings.npz"
CONTENT_CACHE = CACHE_DIR / "phase15_pubmedbert_content_embeddings.npz"
PUBMEDBERT_WEIGHTS = (0.0, 0.25, 0.5, 0.75, 1.0)


def blend_dense(
    multilingual_dense: np.ndarray,
    pubmedbert_dense: np.ndarray,
    pubmedbert_weight: float,
) -> np.ndarray:
    """Blend aligned bounded dense matrices without touching other signals."""
    if multilingual_dense.shape != pubmedbert_dense.shape:
        raise ValueError("Dense matrices must have the same shape")
    if not 0 <= pubmedbert_weight <= 1:
        raise ValueError("pubmedbert_weight must be in [0, 1]")
    if not np.isfinite(multilingual_dense).all() or not np.isfinite(pubmedbert_dense).all():
        raise ValueError("Dense matrices must be finite")
    return (
        (1 - pubmedbert_weight) * multilingual_dense
        + pubmedbert_weight * pubmedbert_dense
    )


def select_pubmedbert_weight(validation_grid: pd.DataFrame) -> float:
    """Maximize validation NDCG@10, breaking ties toward the frozen baseline."""
    if validation_grid.empty:
        raise ValueError("Validation grid is empty")
    selected = validation_grid.sort_values(
        ["ndcg@10", "pubmedbert_weight"], ascending=[False, True]
    ).iloc[0]
    return float(selected["pubmedbert_weight"])


def _embedding_fingerprint(texts: list[str], role: str) -> str:
    payload = json.dumps(
        {
            "model": MODEL_ID,
            "revision": MODEL_REVISION,
            "role": role,
            "texts": texts,
            "normalized": True,
        },
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _load_embedding_cache(path: Path, fingerprint: str) -> np.ndarray | None:
    if not path.exists():
        return None
    archive = np.load(path, allow_pickle=False)
    if str(archive["fingerprint"].item()) != fingerprint:
        return None
    embeddings = archive["embeddings"]
    if embeddings.ndim != 2 or not np.isfinite(embeddings).all():
        return None
    return embeddings


def _save_embedding_cache(path: Path, embeddings: np.ndarray, fingerprint: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        embeddings=np.asarray(embeddings, dtype=np.float32),
        fingerprint=np.asarray(fingerprint),
        model_id=np.asarray(MODEL_ID),
        model_revision=np.asarray(MODEL_REVISION),
    )


def load_or_encode(
    queries: pd.DataFrame,
    content: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, float, bool]:
    """Load fingerprinted vectors or encode raw queries and titles on CPU."""
    query_texts = queries["query_text"].astype(str).tolist()
    content_texts = content["title"].fillna("").astype(str).tolist()
    query_fingerprint = _embedding_fingerprint(query_texts, "query")
    content_fingerprint = _embedding_fingerprint(content_texts, "content_title")
    query_vectors = _load_embedding_cache(QUERY_CACHE, query_fingerprint)
    content_vectors = _load_embedding_cache(CONTENT_CACHE, content_fingerprint)
    cache_hit = query_vectors is not None and content_vectors is not None
    start = time.perf_counter()
    if not cache_hit:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        model = SentenceTransformer(
            MODEL_ID,
            revision=MODEL_REVISION,
            device="cpu",
            local_files_only=True,
        )
        if query_vectors is None:
            query_vectors = model.encode(
                query_texts,
                batch_size=32,
                show_progress_bar=True,
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).astype(np.float32)
            _save_embedding_cache(QUERY_CACHE, query_vectors, query_fingerprint)
        if content_vectors is None:
            content_vectors = model.encode(
                content_texts,
                batch_size=32,
                show_progress_bar=True,
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).astype(np.float32)
            _save_embedding_cache(CONTENT_CACHE, content_vectors, content_fingerprint)
    seconds = time.perf_counter() - start
    if query_vectors is None or content_vectors is None:
        raise AssertionError("Embedding cache resolution failed")
    if query_vectors.shape[1] != content_vectors.shape[1]:
        raise ValueError("Query and content embedding dimensions differ")
    return query_vectors, content_vectors, seconds, cache_hit


def _language_slice_rows(
    baseline: pd.DataFrame,
    candidate: pd.DataFrame,
    query_metadata: pd.DataFrame,
    split: str,
    configuration: str,
) -> list[dict[str, Any]]:
    joined = baseline[["query_id", "ndcg@10"]].merge(
        candidate[["query_id", "ndcg@10"]],
        on="query_id",
        suffixes=("_baseline", "_candidate"),
        validate="one_to_one",
    ).merge(query_metadata, on="query_id", validate="one_to_one")
    rows: list[dict[str, Any]] = []
    for language, group in joined.groupby("language", sort=True):
        eligible = group.dropna(subset=["ndcg@10_baseline", "ndcg@10_candidate"])
        delta = eligible["ndcg@10_candidate"] - eligible["ndcg@10_baseline"]
        rows.append(
            {
                "split": split,
                "configuration": configuration,
                "language": language,
                "queries": len(group),
                "eligible_queries": len(eligible),
                "baseline_ndcg@10": eligible["ndcg@10_baseline"].mean(),
                "candidate_ndcg@10": eligible["ndcg@10_candidate"].mean(),
                "delta_ndcg@10": delta.mean(),
                "improved_queries": int(delta.gt(0).sum()),
                "worsened_queries": int(delta.lt(0).sum()),
                "unchanged_queries": int(delta.eq(0).sum()),
            }
        )
    return rows


def _sha256(paths: list[Path]) -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _update_experiment_log(
    metrics: pd.DataFrame, selected_weight: float
) -> None:
    primary = metrics.query(
        "scheme == 'relevance_grade' and threshold == 1"
    ).set_index(["split", "configuration"])
    base_validation = primary.loc[("validation", "phase12_baseline"), "ndcg@10"]
    selected_validation = primary.loc[
        ("validation", "selected_pubmedbert_blend"), "ndcg@10"
    ]
    base_test = primary.loc[("test", "phase12_baseline"), "ndcg@10"]
    selected_test = primary.loc[("test", "selected_pubmedbert_blend"), "ndcg@10"]
    replacement_test = primary.loc[
        ("test", "pubmedbert_full_replacement"), "ndcg@10"
    ]
    row = {
        "experiment": "R-PUBMED-EMB",
        "hypothesis": "a PubMedBERT MS-MARCO embedding improves dense clinical retrieval",
        "method": (
            f"{MODEL_ID}; full-corpus query-title cosine; validation-selected "
            f"dense blend={selected_weight:g}"
        ),
        "primary_metric": "NDCG@10",
        "result": (
            f"Selected validation {base_validation:.5f}->{selected_validation:.5f}; "
            f"test {base_test:.5f}->{selected_test:.5f}; "
            f"full replacement test={replacement_test:.5f}"
        ),
        "decision": (
            "selected; descriptive test gain"
            if selected_weight > 0 and selected_test > base_test
            else "not selected; no validation-supported improvement"
        ),
    }
    log = pd.read_csv(EXPERIMENT_LOG_PATH)
    log = pd.concat(
        [log[~log["experiment"].eq(row["experiment"])], pd.DataFrame([row])],
        ignore_index=True,
    )
    log.to_csv(EXPERIMENT_LOG_PATH, index=False)


def build_pubmedbert_embedding_artifacts(output_dir: Path = OUTPUT) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    queries = pd.read_csv(LABELED_QUERIES_PATH).sort_values("query_id").reset_index(drop=True)
    content = pd.read_csv(CONTENT_PATH).sort_values("content_id").reset_index(drop=True)
    signals, _, baseline_runtime, baseline_caches = build_signals(queries, content)
    query_vectors, content_vectors, embedding_seconds, cache_hit = load_or_encode(
        queries, content
    )
    pubmedbert_dense = np.clip(
        (query_vectors @ content_vectors.T + 1) / 2, 0, 1
    )

    predictions_path = PHASE12_DIR / "intent_predictions.csv"
    configurations_path = PHASE12_DIR / "configurations.csv"
    phase12_rankings_path = PHASE12_DIR / "rankings.csv.gz"
    predictions = pd.read_csv(predictions_path)
    phase12_configurations = pd.read_csv(configurations_path)
    intent_weight = float(
        phase12_configurations.loc[
            phase12_configurations["configuration"].eq("with_predicted_hard_intent"),
            "intent_weight",
        ].iloc[0]
    )
    predicted_intent = predicted_intent_compatibility(predictions, queries, content)

    def runtime_scores(dense: np.ndarray) -> np.ndarray:
        replaced = dict(signals)
        replaced["dense"] = dense
        return combine(replaced, ("bm25", "dense", "entities", "context")) + (
            intent_weight * predicted_intent
        )

    baseline_scores = runtime_scores(signals["dense"])
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

    validation_path = SPLIT_DIR / "temporal_validation_judgments.csv"
    test_path = SPLIT_DIR / "temporal_test_judgments.csv"
    validation = pd.read_csv(validation_path)
    grid_rows: list[dict[str, Any]] = []
    grid_rankings: dict[float, pd.DataFrame] = {}
    for weight in PUBMEDBERT_WEIGHTS:
        dense = blend_dense(signals["dense"], pubmedbert_dense, weight)
        ranking = rank_scores(runtime_scores(dense), queries["query_id"], content["content_id"])
        grid_rankings[weight] = ranking
        grid_rows.append(
            {
                "pubmedbert_weight": weight,
                **summarize_metrics(evaluate_rankings(ranking, validation)),
            }
        )
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(output_dir / "validation_grid.csv", index=False)
    selected_weight = select_pubmedbert_weight(grid)

    rankings = {
        "phase12_baseline": baseline_ranking,
        "selected_pubmedbert_blend": grid_rankings[selected_weight],
        "pubmedbert_full_replacement": grid_rankings[1.0],
        "multilingual_dense_only": rank_scores(
            signals["dense"], queries["query_id"], content["content_id"]
        ),
        "pubmedbert_dense_only": rank_scores(
            pubmedbert_dense, queries["query_id"], content["content_id"]
        ),
    }
    pd.DataFrame(
        [
            {
                "configuration": name,
                "pubmedbert_weight": (
                    selected_weight
                    if name == "selected_pubmedbert_blend"
                    else 1.0
                    if name in {"pubmedbert_full_replacement", "pubmedbert_dense_only"}
                    else 0.0
                ),
            }
            for name in rankings
        ]
    ).to_csv(output_dir / "configurations.csv", index=False)
    pd.concat(
        [ranking.assign(configuration=name) for name, ranking in rankings.items()],
        ignore_index=True,
    ).to_csv(output_dir / "rankings.csv.gz", index=False)

    metric_rows: list[dict[str, Any]] = []
    detail_rows: list[pd.DataFrame] = []
    comparison_rows: list[dict[str, Any]] = []
    language_rows: list[dict[str, Any]] = []
    query_metadata = queries[["query_id", "language"]]
    comparison_pairs = (
        ("selected_pubmedbert_blend", "phase12_baseline"),
        ("pubmedbert_full_replacement", "phase12_baseline"),
        ("pubmedbert_dense_only", "multilingual_dense_only"),
    )
    for split, judgments in (
        ("validation", validation),
        ("test", pd.read_csv(test_path)),
    ):
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
                    detail_rows.append(per_query.assign(**tags))
        for candidate, reference in comparison_pairs:
            comparison_rows.append(
                {
                    "protocol": "temporal",
                    "split": split,
                    "candidate": candidate,
                    "reference": reference,
                    **paired_bootstrap(primary[reference], primary[candidate]),
                }
            )
            language_rows.extend(
                _language_slice_rows(
                    primary[reference],
                    primary[candidate],
                    query_metadata,
                    split,
                    candidate,
                )
            )

    metrics = pd.DataFrame(metric_rows)
    comparisons = pd.DataFrame(comparison_rows)
    metrics.to_csv(output_dir / "metrics.csv", index=False)
    comparisons.to_csv(output_dir / "paired_comparisons.csv", index=False)
    pd.concat(detail_rows, ignore_index=True).to_csv(
        output_dir / "per_query_metrics.csv.gz", index=False
    )
    pd.DataFrame(language_rows).to_csv(output_dir / "language_slices.csv", index=False)

    input_paths = [
        CONTENT_PATH,
        LABELED_QUERIES_PATH,
        predictions_path,
        configurations_path,
        phase12_rankings_path,
        validation_path,
        test_path,
        QUERY_CACHE,
        CONTENT_CACHE,
        *baseline_caches,
        Path(__file__),
        Path("src/incremental_retrieval.py"),
        Path("src/evaluation.py"),
    ]
    selected_test = comparisons[
        comparisons["split"].eq("test")
        & comparisons["candidate"].eq("selected_pubmedbert_blend")
    ].iloc[0]
    manifest = {
        "model": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_role": "frozen symmetric biomedical sentence embedding",
        "license": "cc-by-nc-2.0",
        "training_on_project_labels": False,
        "starting_point": "Phase 12 with_predicted_hard_intent",
        "controlled_change": "replace or blend only the frozen dense similarity signal",
        "pubmedbert_weights": list(PUBMEDBERT_WEIGHTS),
        "selected_pubmedbert_weight": selected_weight,
        "selection": "temporal-validation NDCG@10; ties prefer less PubMedBERT",
        "pubmedbert_embedding_dimensions": int(query_vectors.shape[1]),
        "pubmedbert_embedding_seconds": embedding_seconds,
        "pubmedbert_embedding_cache_hit": cache_hit,
        "baseline_dense_runtime": baseline_runtime,
        "representation": "raw query and raw content title; L2-normalized cosine",
        "test_delta_ndcg@10": float(selected_test["mean_delta"]),
        "test_status": "descriptive because earlier phases inspected the split",
        "limitations": [
            "The model is English-focused while the corpus includes Indonesian and mixed-language text.",
            "The model was fine-tuned on general MS MARCO retrieval, not clinician-adjudicated relevance.",
            "Only titles are available; body-section evidence cannot influence embeddings.",
            "Behavior-derived evaluation grades are sparse engagement proxies.",
            "The CC BY-NC 2.0 license may preclude commercial deployment.",
        ],
        "sha256": _sha256(input_paths),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    _update_experiment_log(metrics, selected_weight)
    return {
        "output_dir": str(output_dir),
        "selected_pubmedbert_weight": selected_weight,
        "test_delta_ndcg@10": float(selected_test["mean_delta"]),
        "embedding_cache_hit": cache_hit,
        "embedding_seconds": embedding_seconds,
    }


if __name__ == "__main__":
    print(json.dumps(build_pubmedbert_embedding_artifacts(), indent=2))
