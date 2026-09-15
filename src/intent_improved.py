"""Phase 5 CPU-friendly intent-classification ablations.

Every supervised experiment reuses the exact Phase 4 row-stratified and
template-held-out fold assignments.  This makes representation changes the
only moving part in the comparison.  Targets remain Phase 3 weak labels and
must not be interpreted as independent clinical gold labels.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Iterable

from src.config import CACHE_DIR, CONFIG, EXPERIMENT_LOG_PATH, FIGURES_DIR, METRICS_DIR

os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR / "matplotlib"))

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import normalize

from src.intent import ENRICHED_QUERIES_PATH, INTENT_NAMES, LABELED_QUERIES_PATH
from src.intent_baseline import (
    CV_PREDICTIONS_PATH as PHASE4_CV_PREDICTIONS_PATH,
    GROUPED_SENSITIVITY_PATH as PHASE4_GROUPED_PREDICTIONS_PATH,
    METRICS_PATH as PHASE4_METRICS_PATH,
    SHORT_LABELS,
    _aggregate_metrics,
)


PHASE5_PREFIX = "phase5_intent_improved"
COMPARISON_PATH = METRICS_DIR / f"{PHASE5_PREFIX}_experiment_comparison.csv"
PREDICTIONS_PATH = METRICS_DIR / f"{PHASE5_PREFIX}_predictions.csv"
PER_CLASS_PATH = METRICS_DIR / f"{PHASE5_PREFIX}_per_class_metrics.csv"
CHANGES_PATH = METRICS_DIR / f"{PHASE5_PREFIX}_prediction_changes.csv"
FUSION_CHANGES_PATH = METRICS_DIR / f"{PHASE5_PREFIX}_fusion_vs_embedding_changes.csv"
ERRORS_PATH = METRICS_DIR / f"{PHASE5_PREFIX}_errors.csv"
CONFUSION_PATH = METRICS_DIR / f"{PHASE5_PREFIX}_confusion_matrix.csv"
CONFUSION_PAIRS_PATH = METRICS_DIR / f"{PHASE5_PREFIX}_confusion_pairs.csv"
SLICE_METRICS_PATH = METRICS_DIR / f"{PHASE5_PREFIX}_slice_metrics.csv"
MANUAL_REVIEW_PATH = METRICS_DIR / f"{PHASE5_PREFIX}_manual_error_review.csv"
TOP_FEATURES_PATH = METRICS_DIR / f"{PHASE5_PREFIX}_top_features.csv"
METRICS_PATH = METRICS_DIR / f"{PHASE5_PREFIX}_metrics.json"
REPORT_PATH = METRICS_DIR / f"{PHASE5_PREFIX}_report.md"
MODEL_PATH = METRICS_DIR / f"{PHASE5_PREFIX}_selected_model.joblib"
CONFUSION_FIGURE_PATH = FIGURES_DIR / f"{PHASE5_PREFIX}_confusion_matrix.png"
QUERY_EMBEDDINGS_PATH = CACHE_DIR / "phase2_query_embeddings.npz"

ENTITY_COLUMNS = (
    "disease_entity",
    "molecule_entity",
    "drug_class_entity",
)
CONTEXT_BOOLEAN_COLUMNS = (
    "recency_flag",
    "dose_context_flag",
    "hepatic_impairment_flag",
    "comparison_flag",
    "negation_flag",
    "prior_treatment_failure_flag",
)
CONTEXT_CATEGORY_COLUMNS = (
    "age_group",
    "pregnancy_status",
    "route",
    "renal_function_group",
)

EXPERIMENT_LABELS = {
    "T1-P0": "final-taxonomy prototype similarity",
    "T1-B0": "word TF-IDF",
    "T1-E1": "word TF-IDF + supplied entity indicators/counts",
    "T1-E2": "word TF-IDF + entity indicators/counts + contextual slots",
    "T1-E3": "frozen multilingual sentence embeddings",
    "T1-E4": "frozen embeddings + entity indicators/counts + contextual slots",
}
COMPLEXITY_ORDER = {
    "T1-B0": 0,
    "T1-E1": 1,
    "T1-E2": 2,
    "T1-E3": 3,
    "T1-E4": 4,
}


def _split_values(value: Any) -> list[str]:
    if pd.isna(value):
        return []
    return [part.strip().lower() for part in str(value).split(";") if part.strip()]


def entity_feature_dict(row: pd.Series) -> dict[str, float]:
    """Turn supplied NER columns into auditable indicators and counts.

    Exact entity identity is intentionally excluded: entity names already occur
    in query text, and adding hundreds of sparse identities made an exploratory
    run learn entity/intent shortcuts rather than information-need cues.
    """
    features: dict[str, float] = {}
    total = 0
    for column in ENTITY_COLUMNS:
        values = _split_values(row[column])
        total += len(values)
        features[f"has::{column}"] = float(bool(values))
        features[f"count::{column}"] = float(len(values))
    features["count::all_supplied_entities"] = float(total)
    features["has::multiple_molecules"] = float(
        len(_split_values(row["molecule_entity"])) > 1
    )
    return features


def context_feature_dict(row: pd.Series) -> dict[str, float]:
    """Represent only Phase 1.6 slots that were implemented and quality checked."""
    features: dict[str, float] = {
        f"context::{column}": float(bool(row[column]))
        for column in CONTEXT_BOOLEAN_COLUMNS
    }
    features["context::has_year"] = float(not pd.isna(row["year"]))
    for column in CONTEXT_CATEGORY_COLUMNS:
        value = row[column]
        features[f"context::has_{column}"] = float(not pd.isna(value))
        if not pd.isna(value):
            features[f"context::{column}::{str(value).strip().lower()}"] = 1.0
    return features


def combined_structured_records(frame: pd.DataFrame) -> list[dict[str, float]]:
    """Build the shared entity-plus-context records used by E2 and E4."""
    records: list[dict[str, float]] = []
    for _, row in frame.iterrows():
        features = entity_feature_dict(row)
        features.update(context_feature_dict(row))
        records.append(features)
    return records


class IntentFeatureTransformer(BaseEstimator, TransformerMixin):
    """Combine word TF-IDF with deterministic structured query features."""

    def __init__(self, include_context: bool = False):
        self.include_context = include_context

    def _records(self, frame: pd.DataFrame) -> list[dict[str, float]]:
        records: list[dict[str, float]] = []
        for _, row in frame.iterrows():
            features = entity_feature_dict(row)
            if self.include_context:
                features.update(context_feature_dict(row))
            records.append(features)
        return records

    def fit(self, X: pd.DataFrame, y: Iterable[str] | None = None) -> "IntentFeatureTransformer":
        self.text_vectorizer_ = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=CONFIG.intent_tfidf_ngram_range,
            sublinear_tf=True,
        )
        self.structured_vectorizer_ = DictVectorizer(sparse=True, sort=True)
        self.text_vectorizer_.fit(X["query_text"].fillna(""))
        self.structured_vectorizer_.fit(self._records(X))
        return self

    def transform(self, X: pd.DataFrame) -> csr_matrix:
        text = self.text_vectorizer_.transform(X["query_text"].fillna(""))
        structured = self.structured_vectorizer_.transform(self._records(X))
        return hstack([text, structured], format="csr")

    def get_feature_names_out(self) -> np.ndarray:
        text = np.asarray(
            [f"text::{value}" for value in self.text_vectorizer_.get_feature_names_out()],
            dtype=object,
        )
        structured = np.asarray(
            [
                f"structured::{value}"
                for value in self.structured_vectorizer_.get_feature_names_out()
            ],
            dtype=object,
        )
        return np.concatenate([text, structured])


def _classifier() -> LogisticRegression:
    return LogisticRegression(
        C=CONFIG.intent_logreg_c,
        class_weight="balanced",
        max_iter=2_000,
        random_state=CONFIG.random_seed,
        solver="liblinear",
    )


def build_structured_pipeline(include_context: bool) -> Pipeline:
    return Pipeline(
        [
            ("features", IntentFeatureTransformer(include_context=include_context)),
            ("classifier", _classifier()),
        ]
    )


def _load_embedding_map(labeled: pd.DataFrame) -> dict[str, np.ndarray]:
    archive = np.load(QUERY_EMBEDDINGS_PATH, allow_pickle=False)
    embeddings = archive["embeddings"]
    embedding_source = pd.read_csv(ENRICHED_QUERIES_PATH, usecols=["query_id"])
    if embeddings.shape != (len(embedding_source), 384):
        raise AssertionError("Phase 2 embedding cache does not match the 500 labeled rows")
    if labeled["query_id"].duplicated().any() or embedding_source["query_id"].duplicated().any():
        raise AssertionError("query_id must be unique before aligning cached embeddings")
    if set(labeled["query_id"]) != set(embedding_source["query_id"]):
        raise AssertionError("Labeled rows and the Phase 2 embedding source have different IDs")
    return dict(zip(embedding_source["query_id"], embeddings, strict=True))


def _matrix_for_ids(
    query_ids: pd.Series, embedding_map: dict[str, np.ndarray]
) -> np.ndarray:
    return np.stack([embedding_map[query_id] for query_id in query_ids])


def _run_supervised_cv(
    experiment: str,
    frame: pd.DataFrame,
    fold_assignments: pd.DataFrame,
    protocol: str,
    embedding_map: dict[str, np.ndarray],
) -> pd.DataFrame:
    data = frame.merge(
        fold_assignments[["query_id", "fold"]], on="query_id", validate="one_to_one"
    )
    records: list[dict[str, Any]] = []
    for fold in sorted(data["fold"].unique()):
        train = data[data["fold"].ne(fold)]
        test = data[data["fold"].eq(fold)]
        if experiment == "T1-E3":
            model: Any = _classifier()
            model.fit(_matrix_for_ids(train["query_id"], embedding_map), train["intent"])
            predicted = model.predict(_matrix_for_ids(test["query_id"], embedding_map))
            probabilities = model.predict_proba(
                _matrix_for_ids(test["query_id"], embedding_map)
            )
        elif experiment == "T1-E4":
            structured_vectorizer = DictVectorizer(sparse=True, sort=True)
            train_structured = normalize(
                structured_vectorizer.fit_transform(combined_structured_records(train)),
                norm="l2",
            )
            test_structured = normalize(
                structured_vectorizer.transform(combined_structured_records(test)),
                norm="l2",
            )
            train_matrix = hstack(
                [
                    csr_matrix(_matrix_for_ids(train["query_id"], embedding_map)),
                    train_structured,
                ],
                format="csr",
            )
            test_matrix = hstack(
                [
                    csr_matrix(_matrix_for_ids(test["query_id"], embedding_map)),
                    test_structured,
                ],
                format="csr",
            )
            model = _classifier()
            model.fit(train_matrix, train["intent"])
            predicted = model.predict(test_matrix)
            probabilities = model.predict_proba(test_matrix)
        else:
            model = build_structured_pipeline(include_context=experiment == "T1-E2")
            model.fit(train, train["intent"])
            predicted = model.predict(test)
            probabilities = model.predict_proba(test)
        classes = model.classes_
        ranked = np.argsort(probabilities, axis=1)
        for position, (_, row) in enumerate(test.iterrows()):
            top = int(ranked[position, -1])
            second = int(ranked[position, -2])
            records.append(
                {
                    "protocol": protocol,
                    "experiment": experiment,
                    "query_id": row["query_id"],
                    "query_text": row["query_text"],
                    "language": row["language"],
                    "signal_agreement": row["signal_agreement"],
                    "fold": int(fold),
                    "true_intent": row["intent"],
                    "predicted_intent": str(classes[top]),
                    "predicted_probability": float(probabilities[position, top]),
                    "second_intent": str(classes[second]),
                    "probability_margin": float(
                        probabilities[position, top] - probabilities[position, second]
                    ),
                    "correct": bool(row["intent"] == classes[top]),
                }
            )
    predictions = pd.DataFrame(records).sort_values("query_id").reset_index(drop=True)
    if len(predictions) != len(data) or predictions["query_id"].nunique() != len(data):
        raise AssertionError(f"{experiment} {protocol} did not predict every query once")
    return predictions


def _prototype_predictions(
    frame: pd.DataFrame, fold_assignments: pd.DataFrame, protocol: str
) -> pd.DataFrame:
    data = frame.merge(
        fold_assignments[["query_id", "fold"]], on="query_id", validate="one_to_one"
    )
    return pd.DataFrame(
        {
            "protocol": protocol,
            "experiment": "T1-P0",
            "query_id": data["query_id"],
            "query_text": data["query_text"],
            "language": data["language"],
            "signal_agreement": data["signal_agreement"],
            "fold": data["fold"].astype(int),
            "true_intent": data["intent"],
            "predicted_intent": data["prototype_intent_signal"],
            "predicted_probability": np.nan,
            "second_intent": "",
            "probability_margin": np.nan,
            "correct": data["intent"].eq(data["prototype_intent_signal"]),
        }
    ).sort_values("query_id").reset_index(drop=True)


def _baseline_predictions(
    source_path: Path, frame: pd.DataFrame, protocol: str
) -> pd.DataFrame:
    source = pd.read_csv(source_path)
    prediction_column = "predicted_intent"
    merged = source.merge(
        frame[["query_id", "language", "signal_agreement"]],
        on="query_id",
        validate="one_to_one",
        suffixes=("", "_label"),
    )
    return pd.DataFrame(
        {
            "protocol": protocol,
            "experiment": "T1-B0",
            "query_id": merged["query_id"],
            "query_text": merged["query_text"],
            "language": merged["language"],
            "signal_agreement": merged["signal_agreement"],
            "fold": merged["fold"].astype(int),
            "true_intent": merged["true_intent"],
            "predicted_intent": merged[prediction_column],
            "predicted_probability": merged.get("predicted_probability", np.nan),
            "second_intent": merged.get("second_intent", ""),
            "probability_margin": merged.get("probability_margin", np.nan),
            "correct": merged["true_intent"].eq(merged[prediction_column]),
        }
    ).sort_values("query_id").reset_index(drop=True)


def _comparison(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (protocol, experiment), group in predictions.groupby(
        ["protocol", "experiment"], sort=False
    ):
        metrics = _aggregate_metrics(
            group["true_intent"], group["predicted_intent"].to_numpy()
        )
        rows.append(
            {
                "protocol": protocol,
                "experiment": experiment,
                "representation": EXPERIMENT_LABELS[experiment],
                "n_queries": int(len(group)),
                "n_classes": int(group["true_intent"].nunique()),
                **metrics,
            }
        )
    result = pd.DataFrame(rows)
    baseline = result[result["experiment"].eq("T1-B0")].set_index("protocol")
    result["macro_f1_delta_vs_phase4"] = result.apply(
        lambda row: row["macro_f1"] - baseline.loc[row["protocol"], "macro_f1"], axis=1
    )
    return result.sort_values(["protocol", "macro_f1"], ascending=[True, False])


def _per_class(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (protocol, experiment), group in predictions.groupby(
        ["protocol", "experiment"], sort=False
    ):
        labels = [label for label in INTENT_NAMES if label in set(group["true_intent"])]
        precision, recall, f1, support = precision_recall_fscore_support(
            group["true_intent"],
            group["predicted_intent"],
            labels=labels,
            zero_division=0,
        )
        for index, label in enumerate(labels):
            rows.append(
                {
                    "protocol": protocol,
                    "experiment": experiment,
                    "intent": label,
                    "precision": float(precision[index]),
                    "recall": float(recall[index]),
                    "f1": float(f1[index]),
                    "support": int(support[index]),
                }
            )
    return pd.DataFrame(rows)


def _slice_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    working = predictions.copy()
    working["query_length_bucket"] = pd.cut(
        working["query_text"].fillna("").str.split().str.len(),
        bins=[-1, 3, 7, np.inf],
        labels=["1-3 tokens", "4-7 tokens", "8+ tokens"],
    ).astype(str)
    for (protocol, experiment), experiment_rows in working.groupby(
        ["protocol", "experiment"], sort=False
    ):
        for slice_type, column in (
            ("language", "language"),
            ("signal_agreement", "signal_agreement"),
            ("query_length", "query_length_bucket"),
        ):
            for slice_value, group in experiment_rows.groupby(column, dropna=False):
                values = _aggregate_metrics(
                    group["true_intent"], group["predicted_intent"].to_numpy()
                )
                rows.append(
                    {
                        "protocol": protocol,
                        "experiment": experiment,
                        "slice_type": slice_type,
                        "slice_value": slice_value,
                        "n_queries": int(len(group)),
                        "n_true_classes": int(group["true_intent"].nunique()),
                        **values,
                    }
                )
    return pd.DataFrame(rows)


def _choose_model(comparison: pd.DataFrame) -> tuple[str, str]:
    grouped = comparison[
        comparison["protocol"].eq("template_grouped")
        & comparison["experiment"].isin(COMPLEXITY_ORDER)
    ].copy()
    best_score = float(grouped["macro_f1"].max())
    competitive = grouped[grouped["macro_f1"].ge(best_score - 0.01)].copy()
    competitive["complexity"] = competitive["experiment"].map(COMPLEXITY_ORDER)
    selected = str(competitive.sort_values("complexity").iloc[0]["experiment"])
    reason = (
        "simplest supervised representation within 0.010 grouped Macro F1 of the best; "
        "selection uses the Phase 4 template-held-out stress test"
    )
    return selected, reason


def _prediction_changes(predictions: pd.DataFrame) -> pd.DataFrame:
    keys = ["protocol", "query_id"]
    base = predictions[predictions["experiment"].eq("T1-B0")][
        keys + ["predicted_intent", "correct"]
    ].rename(
        columns={"predicted_intent": "baseline_prediction", "correct": "baseline_correct"}
    )
    richer = predictions[predictions["experiment"].isin(["T1-E1", "T1-E2"])].merge(
        base, on=keys, validate="many_to_one"
    )
    changed = richer["predicted_intent"].ne(richer["baseline_prediction"])
    result = richer[changed].copy()
    result["change_outcome"] = np.select(
        [
            ~result["baseline_correct"] & result["correct"],
            result["baseline_correct"] & ~result["correct"],
        ],
        ["fixed_baseline_error", "introduced_error"],
        default="changed_but_both_wrong",
    )
    return result.sort_values(["protocol", "experiment", "change_outcome", "query_id"])


def _fusion_changes(predictions: pd.DataFrame) -> pd.DataFrame:
    keys = ["protocol", "query_id"]
    embedding = predictions[predictions["experiment"].eq("T1-E3")][
        keys + ["predicted_intent", "correct"]
    ].rename(
        columns={
            "predicted_intent": "embedding_prediction",
            "correct": "embedding_correct",
        }
    )
    fusion = predictions[predictions["experiment"].eq("T1-E4")].merge(
        embedding, on=keys, validate="one_to_one"
    )
    result = fusion[
        fusion["predicted_intent"].ne(fusion["embedding_prediction"])
    ].copy()
    result["change_outcome"] = np.select(
        [
            ~result["embedding_correct"] & result["correct"],
            result["embedding_correct"] & ~result["correct"],
        ],
        ["fixed_embedding_error", "introduced_error"],
        default="changed_but_both_wrong",
    )
    return result.sort_values(["protocol", "change_outcome", "query_id"])


def _top_features(model: Pipeline, experiment: str, n: int = 15) -> pd.DataFrame:
    names = model.named_steps["features"].get_feature_names_out()
    classifier = model.named_steps["classifier"]
    rows: list[dict[str, Any]] = []
    for class_index, intent in enumerate(classifier.classes_):
        coefficients = classifier.coef_[class_index]
        for rank, feature_index in enumerate(np.argsort(coefficients)[-n:][::-1], start=1):
            feature = str(names[feature_index])
            rows.append(
                {
                    "experiment": experiment,
                    "intent": intent,
                    "rank": rank,
                    "feature": feature,
                    "feature_family": (
                        "structured" if feature.startswith("structured::") else "text"
                    ),
                    "coefficient": float(coefficients[feature_index]),
                }
            )
    return pd.DataFrame(rows)


def _embedding_structured_top_features(
    classifier: LogisticRegression,
    structured_vectorizer: DictVectorizer,
    n: int = 15,
) -> pd.DataFrame:
    names = np.concatenate(
        [
            np.asarray([f"embedding::{index:03d}" for index in range(384)], dtype=object),
            np.asarray(
                [
                    f"structured::{value}"
                    for value in structured_vectorizer.get_feature_names_out()
                ],
                dtype=object,
            ),
        ]
    )
    rows: list[dict[str, Any]] = []
    for class_index, intent in enumerate(classifier.classes_):
        coefficients = classifier.coef_[class_index]
        for rank, feature_index in enumerate(np.argsort(coefficients)[-n:][::-1], start=1):
            feature = str(names[feature_index])
            rows.append(
                {
                    "experiment": "T1-E4",
                    "intent": intent,
                    "rank": rank,
                    "feature": feature,
                    "feature_family": (
                        "structured" if feature.startswith("structured::") else "embedding"
                    ),
                    "coefficient": float(coefficients[feature_index]),
                }
            )
    return pd.DataFrame(rows)


def _confusion_pairs(selected_grouped: pd.DataFrame) -> pd.DataFrame:
    errors = selected_grouped[~selected_grouped["correct"]]
    pairs = (
        errors.groupby(["true_intent", "predicted_intent"], as_index=False)
        .size()
        .rename(columns={"size": "n_errors"})
    )
    support = selected_grouped["true_intent"].value_counts()
    pairs["true_intent_support"] = pairs["true_intent"].map(support).astype(int)
    pairs["share_of_true_intent"] = pairs["n_errors"] / pairs["true_intent_support"]
    return pairs.sort_values(
        ["n_errors", "share_of_true_intent", "true_intent"],
        ascending=[False, False, True],
    )


def _manual_error_review(
    selected_grouped: pd.DataFrame, confusion_pairs: pd.DataFrame
) -> pd.DataFrame:
    notes = {
        ("Safety / Contraindication", "Interaction / Combination"): (
            "The repeated 'side effect ... apa saja' form is a safety request; the semantic "
            "representation over-associates medication harm language with interaction content."
        ),
        ("Dosing / Administration", "Safety / Contraindication"): (
            "Pediatric context pulls the embedding toward vulnerable-population safety even "
            "though the explicit requested output is a dose."
        ),
        ("Dosing / Administration", "Treatment Change / Escalation"): (
            "Dose adjustment is interpreted as changing therapy; the model misses that "
            "'adjustment' modifies the regimen rather than treatment selection."
        ),
        ("Management / Treatment Selection", "Comparative Treatment Choice"): (
            "A when-to-start question asks for initiation guidance without comparing two "
            "alternatives; treatment-choice semantics are too close to comparison."
        ),
        ("Management / Treatment Selection", "Treatment Change / Escalation"): (
            "Treatment initiation is confused with a transition in therapy despite no prior "
            "failure, switch, add-on, or escalation cue."
        ),
        ("Prophylaxis / Maintenance", "Management / Treatment Selection"): (
            "Maintenance after target attainment is longitudinal management, but the explicit "
            "maintenance cue should determine the subtype."
        ),
        ("Interaction / Combination", "Safety / Contraindication"): (
            "The explicit combination is primary, but 'aman atau tidak' pulls the prediction "
            "toward general safety."
        ),
        ("Management / Treatment Selection", "Safety / Contraindication"): (
            "Pregnancy or comorbidity context overwhelms the explicit first-line/treatment-choice request."
        ),
        ("Safety / Contraindication", "Dosing / Administration"): (
            "The fused model overweights dose/adjustment semantics or the frequent Dosing class; "
            "the explicit safety or adverse-effect request should determine the label."
        ),
        ("Management / Treatment Selection", "Prophylaxis / Maintenance"): (
            "Treatment initiation is incorrectly interpreted as longitudinal maintenance despite "
            "the absence of a prophylaxis or achieved-target cue."
        ),
        ("Interaction / Combination", "Comparative Treatment Choice"): (
            "Multiple-molecule structure identifies a multi-drug query but does not distinguish "
            "co-administration from comparison; the combination cue should determine the label."
        ),
        ("Interaction / Combination", "Management / Treatment Selection"): (
            "Combination therapy is interpreted as general treatment selection; explicit "
            "co-administration should retain the Interaction / Combination subtype."
        ),
        ("Management / Treatment Selection", "Mechanism / Background Knowledge"): (
            "The short 'target terapi' formulation is semantically underspecified, but the weak "
            "target treats it as a management objective rather than background knowledge."
        ),
        ("Safety / Contraindication", "Mechanism / Background Knowledge"): (
            "Bahasa adverse-effect wording is embedded as general drug information instead of a safety request."
        ),
    }
    top_pairs = confusion_pairs.head(8)[["true_intent", "predicted_intent"]]
    review = selected_grouped.merge(
        top_pairs, on=["true_intent", "predicted_intent"], how="inner"
    )
    review = review.groupby(["true_intent", "predicted_intent"], sort=False).head(3).copy()
    review["manual_review_note"] = review.apply(
        lambda row: notes.get(
            (row["true_intent"], row["predicted_intent"]),
            "Adjacent clinical intent boundary; review with independent clinical annotation.",
        ),
        axis=1,
    )
    return review.sort_values(["true_intent", "predicted_intent", "query_id"])


def _plot_confusion(matrix: np.ndarray, labels: list[str], selected: str) -> None:
    totals = matrix.sum(axis=1, keepdims=True)
    normalized = np.divide(
        matrix, totals, out=np.zeros_like(matrix, dtype=float), where=totals != 0
    )
    figure, axis = plt.subplots(figsize=(12, 10))
    image = axis.imshow(normalized, cmap="Blues", vmin=0, vmax=1)
    display = [SHORT_LABELS[label] for label in labels]
    axis.set_xticks(range(len(labels)), display, rotation=45, ha="right")
    axis.set_yticks(range(len(labels)), display)
    axis.set_xlabel("Predicted intent")
    axis.set_ylabel("Weak target intent")
    axis.set_title(f"Phase 5 {selected} template-held-out confusion matrix")
    for i in range(len(labels)):
        for j in range(len(labels)):
            if normalized[i, j] >= 0.01:
                axis.text(
                    j,
                    i,
                    f"{normalized[i, j]:.2f}",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white" if normalized[i, j] > 0.55 else "black",
                )
    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    figure.tight_layout()
    figure.savefig(CONFUSION_FIGURE_PATH, dpi=180, bbox_inches="tight")
    plt.close(figure)


def _update_experiment_log(comparison: pd.DataFrame, selected: str) -> None:
    log = pd.read_csv(EXPERIMENT_LOG_PATH)
    additions = {
        "T1-P0": (
            "intent definitions transfer without supervised fitting",
            "frozen candidate-prototype cosine similarity",
        ),
        "T1-E1": (
            "supplied entities improve unseen-template intent transfer",
            "TF-IDF + supplied entity indicators/counts + Logistic Regression",
        ),
        "T1-E2": (
            "contextual slots improve unseen-template intent transfer",
            "TF-IDF + entities + contextual slots + Logistic Regression",
        ),
        "T1-E3": (
            "frozen semantic embeddings improve unseen-template intent transfer",
            "frozen multilingual embeddings + Logistic Regression",
        ),
        "T1-E4": (
            "semantic and structured signals are complementary",
            "L2-normalized frozen embeddings + entity/context features + Logistic Regression",
        ),
    }
    for experiment, (hypothesis, method) in additions.items():
        row = comparison[
            comparison["protocol"].eq("template_grouped")
            & comparison["experiment"].eq(experiment)
        ].iloc[0]
        result = (
            f"template-held-out Macro F1={row['macro_f1']:.3f}; "
            f"delta vs T1-B0={row['macro_f1_delta_vs_phase4']:+.3f}"
        )
        decision = "selected" if experiment == selected else "not selected"
        values = {
            "experiment": experiment,
            "hypothesis": hypothesis,
            "method": method,
            "primary_metric": "Macro F1",
            "result": result,
            "decision": decision,
        }
        mask = log["experiment"].eq(experiment)
        if mask.any():
            for column, value in values.items():
                log.loc[mask, column] = value
        else:
            log = pd.concat([log, pd.DataFrame([values])], ignore_index=True)
    log.to_csv(EXPERIMENT_LOG_PATH, index=False)


def build_report(metrics: dict[str, Any], comparison: pd.DataFrame) -> str:
    grouped = comparison[comparison["protocol"].eq("template_grouped")].set_index(
        "experiment"
    )
    row = comparison[comparison["protocol"].eq("row_stratified")].set_index(
        "experiment"
    )
    selected = metrics["selected_experiment"]
    best = grouped.loc[selected]
    context_changes = metrics["structured_prediction_changes"]
    return f"""# Phase 5: Improved Intent Classification

## Outcome

Phase 5 keeps the Phase 4 labels and fold assignments fixed and changes only the query representation. The selected model is **{selected}: {EXPERIMENT_LABELS[selected]}**. It reaches **{best['macro_f1']:.3f} template-held-out Macro F1**, a {best['macro_f1_delta_vs_phase4']:+.3f} absolute change from the Phase 4 baseline ({grouped.loc['T1-B0', 'macro_f1']:.3f}). Its five-fold weak-label Macro F1 is {row.loc[selected, 'macro_f1']:.3f}, compared with {row.loc['T1-B0', 'macro_f1']:.3f} for Phase 4.

The selection rule is: {metrics['selection_reason']}. This prioritizes transfer to unseen query formulations rather than the nearly saturated row-stratified score.

## Experiment comparison

| Experiment | Representation | Row-CV Macro F1 | Template-held-out Macro F1 | Delta vs Phase 4 |
| --- | --- | ---: | ---: | ---: |
| T1-P0 | Final-taxonomy prototype similarity | {row.loc['T1-P0', 'macro_f1']:.3f} | {grouped.loc['T1-P0', 'macro_f1']:.3f} | {grouped.loc['T1-P0', 'macro_f1_delta_vs_phase4']:+.3f} |
| T1-B0 | Word TF-IDF | {row.loc['T1-B0', 'macro_f1']:.3f} | {grouped.loc['T1-B0', 'macro_f1']:.3f} | {grouped.loc['T1-B0', 'macro_f1_delta_vs_phase4']:+.3f} |
| T1-E1 | Text + supplied entities | {row.loc['T1-E1', 'macro_f1']:.3f} | {grouped.loc['T1-E1', 'macro_f1']:.3f} | {grouped.loc['T1-E1', 'macro_f1_delta_vs_phase4']:+.3f} |
| T1-E2 | Text + entities + contextual slots | {row.loc['T1-E2', 'macro_f1']:.3f} | {grouped.loc['T1-E2', 'macro_f1']:.3f} | {grouped.loc['T1-E2', 'macro_f1_delta_vs_phase4']:+.3f} |
| T1-E3 | Frozen sentence embeddings | {row.loc['T1-E3', 'macro_f1']:.3f} | {grouped.loc['T1-E3', 'macro_f1']:.3f} | {grouped.loc['T1-E3', 'macro_f1_delta_vs_phase4']:+.3f} |
| T1-E4 | Frozen embeddings + entities + contextual slots | {row.loc['T1-E4', 'macro_f1']:.3f} | {grouped.loc['T1-E4', 'macro_f1']:.3f} | {grouped.loc['T1-E4', 'macro_f1_delta_vs_phase4']:+.3f} |

T1-P0 uses the final 11 data-refined intent definitions because the original literature seed categories do not map one-to-one to the final subtype task. It is diagnostic only: prototype predictions helped form the Phase 3 agreement filter, so this score is selection-biased and not an independent zero-shot benchmark. T1-E3 and T1-E4 reuse the frozen Phase 2 multilingual embeddings; no encoder parameters are trained. Because the same embedding representation also contributed the prototype and cluster signals used by Phase 3 filtering, neither embedding experiment is fully independent of evaluation-set construction.

T1-E4 uses fixed early fusion rather than a held-out-scale sweep. The normalized embedding has unit L2 norm, the combined entity/context block is independently normalized to unit L2 norm, and the two blocks are concatenated with equal weight. This prevents raw boolean values from overwhelming individual embedding dimensions while avoiding hyperparameter selection on the outer evaluation folds.

Relative to T1-E3, T1-E4 changes {metrics['fusion_vs_embedding_changes']['total']} predictions across both protocols. It fixes {metrics['fusion_vs_embedding_changes']['fixed_embedding_errors']} embedding-only errors, introduces {metrics['fusion_vs_embedding_changes']['introduced_errors']} errors, and changes {metrics['fusion_vs_embedding_changes']['changed_but_both_wrong']} incorrect predictions to another incorrect class. The template-held-out protocol accounts for {metrics['fusion_vs_embedding_changes']['grouped_fixed_embedding_errors']} of the fixes and {metrics['fusion_vs_embedding_changes']['grouped_introduced_errors']} of the introduced errors.

## Structured-feature effects

Across both protocols and both structured experiments, there are {context_changes['total']} changed experiment-prediction instances relative to the baseline: {context_changes['fixed_baseline_errors']} fix a baseline error, {context_changes['introduced_errors']} introduce an error, and {context_changes['changed_but_both_wrong']} change one wrong prediction to another. These cases are exported for manual review. The supplied-entity branch deliberately uses only presence/count features; exact entity identities are excluded because they duplicate query text and invite disease/drug shortcuts. Extracted context can encode genuine clinical constraints, but it can also become a template shortcut; the E1/E2 coefficient audit therefore marks text versus structured feature families explicitly.

## Failure analysis

The selected-model confusion matrix and error table use the zero-template-overlap protocol, the more informative Phase 4 baseline comparison. Monitoring / Response / Risk Assessment remains excluded from this stress test because its retained weak labels contain only one independent template. Error rows retain language and signal-agreement fields, enabling review of mixed-language, rare-class, and low-confidence weak-label cases. A separate confusion-pair table and reviewed examples document the most common boundaries, while the language, label-agreement, and query-length slices remain descriptive because their class mixes differ.

## Limitations

- Targets are model-assisted weak labels, not clinician-adjudicated gold labels.
- The row-stratified protocol leaks recurring delexicalized templates by design; it measures weak-policy replication.
- The grouped protocol is a two-fold stress test over 10 classes, with several classes represented by only two to four templates.
- Prototype predictions are not independent of the retained evaluation subset.
- The E3/E4 embedding representation contributed Phase 3 prototype/cluster signals, although fold-specific classifiers never see test labels.
- `Other / Ambiguous` has no training examples, so none of the supervised models can learn abstention or novel intents.
- Feature extraction is deterministic and CPU-friendly, but structured features can amplify dataset-specific correlations.
"""


def run_phase5() -> dict[str, Path]:
    """Run Phase 5, persist ablations, select a model, and update the log."""
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    labeled = pd.read_csv(LABELED_QUERIES_PATH)
    frame = labeled[labeled["signal_agreement"].ne("three_way_disagreement")].copy()
    if len(frame) != 362:
        raise AssertionError("Phase 5 must use the same 362 weak labels as Phase 4")
    embedding_map = _load_embedding_map(labeled)

    phase4_row = pd.read_csv(PHASE4_CV_PREDICTIONS_PATH)
    phase4_grouped = pd.read_csv(PHASE4_GROUPED_PREDICTIONS_PATH)
    row_folds = phase4_row[["query_id", "fold"]]
    grouped_folds = phase4_grouped[["query_id", "fold"]]

    prediction_frames: list[pd.DataFrame] = [
        _baseline_predictions(PHASE4_CV_PREDICTIONS_PATH, frame, "row_stratified"),
        _baseline_predictions(
            PHASE4_GROUPED_PREDICTIONS_PATH, frame, "template_grouped"
        ),
        _prototype_predictions(frame, row_folds, "row_stratified"),
        _prototype_predictions(frame, grouped_folds, "template_grouped"),
    ]
    for experiment in ("T1-E1", "T1-E2", "T1-E3", "T1-E4"):
        prediction_frames.append(
            _run_supervised_cv(
                experiment, frame, row_folds, "row_stratified", embedding_map
            )
        )
        prediction_frames.append(
            _run_supervised_cv(
                experiment, frame, grouped_folds, "template_grouped", embedding_map
            )
        )
    predictions = pd.concat(prediction_frames, ignore_index=True)
    comparison = _comparison(predictions)

    phase4_metrics = json.loads(PHASE4_METRICS_PATH.read_text(encoding="utf-8"))
    expected_row = phase4_metrics["out_of_fold_metrics"]["macro_f1"]
    expected_grouped = phase4_metrics["template_grouped_sensitivity"]["macro_f1"]
    actual_row = comparison[
        comparison["protocol"].eq("row_stratified")
        & comparison["experiment"].eq("T1-B0")
    ]["macro_f1"].iloc[0]
    actual_grouped = comparison[
        comparison["protocol"].eq("template_grouped")
        & comparison["experiment"].eq("T1-B0")
    ]["macro_f1"].iloc[0]
    if not np.isclose(actual_row, expected_row) or not np.isclose(
        actual_grouped, expected_grouped
    ):
        raise AssertionError("Phase 5 baseline does not reproduce Phase 4 metrics")

    selected, selection_reason = _choose_model(comparison)
    selected_feature_table: pd.DataFrame | None = None
    if selected == "T1-E3":
        selected_model: Any = _classifier()
        selected_model.fit(
            _matrix_for_ids(frame["query_id"], embedding_map), frame["intent"]
        )
        model_artifact: Any = {
            "experiment": selected,
            "encoder_name": CONFIG.semantic_model_name,
            "classifier": selected_model,
            "input_contract": "384-dimensional normalized frozen sentence embedding",
        }
    elif selected == "T1-E4":
        structured_vectorizer = DictVectorizer(sparse=True, sort=True)
        structured_matrix = normalize(
            structured_vectorizer.fit_transform(combined_structured_records(frame)),
            norm="l2",
        )
        fusion_matrix = hstack(
            [
                csr_matrix(_matrix_for_ids(frame["query_id"], embedding_map)),
                structured_matrix,
            ],
            format="csr",
        )
        selected_model = _classifier()
        selected_model.fit(fusion_matrix, frame["intent"])
        model_artifact = {
            "experiment": selected,
            "encoder_name": CONFIG.semantic_model_name,
            "classifier": selected_model,
            "structured_vectorizer": structured_vectorizer,
            "structured_feature_contract": (
                "entity indicators/counts plus implemented Phase 1.6 contextual slots"
            ),
            "block_normalization": (
                "embedding and combined structured block are independently L2-normalized "
                "and concatenated with equal weight"
            ),
            "input_contract": (
                "384-dimensional normalized frozen embedding plus raw query row for "
                "deterministic structured feature extraction"
            ),
        }
        selected_feature_table = _embedding_structured_top_features(
            selected_model, structured_vectorizer
        )
    else:
        selected_model = build_structured_pipeline(include_context=selected == "T1-E2")
        selected_model.fit(frame, frame["intent"])
        model_artifact = selected_model

    # Fit both structured variants on all retained rows solely for a coefficient
    # audit, even when the selected deployable artifact is the embedding model.
    structured_feature_tables: list[pd.DataFrame] = []
    for experiment in ("T1-E1", "T1-E2"):
        audit_model = build_structured_pipeline(include_context=experiment == "T1-E2")
        audit_model.fit(frame, frame["intent"])
        structured_feature_tables.append(_top_features(audit_model, experiment))
    if selected_feature_table is not None:
        structured_feature_tables.append(selected_feature_table)
    top_features = pd.concat(structured_feature_tables, ignore_index=True)

    per_class = _per_class(predictions)
    changes = _prediction_changes(predictions)
    fusion_changes = _fusion_changes(predictions)
    selected_grouped = predictions[
        predictions["protocol"].eq("template_grouped")
        & predictions["experiment"].eq(selected)
    ].copy()
    errors = selected_grouped[~selected_grouped["correct"]].sort_values(
        ["true_intent", "probability_margin", "query_id"],
        ascending=[True, False, True],
    )
    grouped_labels = [
        label for label in INTENT_NAMES if label in set(selected_grouped["true_intent"])
    ]
    matrix = confusion_matrix(
        selected_grouped["true_intent"],
        selected_grouped["predicted_intent"],
        labels=grouped_labels,
    )
    matrix_frame = pd.DataFrame(matrix, index=grouped_labels, columns=grouped_labels)
    matrix_frame.index.name = "weak_target_intent"
    confusion_pairs = _confusion_pairs(selected_grouped)
    manual_review = _manual_error_review(selected_grouped, confusion_pairs)
    slice_metrics = _slice_metrics(predictions)

    change_counts = changes["change_outcome"].value_counts()
    fusion_change_counts = fusion_changes["change_outcome"].value_counts()
    grouped_fusion_change_counts = fusion_changes[
        fusion_changes["protocol"].eq("template_grouped")
    ]["change_outcome"].value_counts()
    metrics: dict[str, Any] = {
        "phase4_baseline_metrics_path": str(PHASE4_METRICS_PATH.relative_to(PHASE4_METRICS_PATH.parents[2])),
        "label_source": "Phase 3 weak labels excluding 138 three-way disagreements",
        "n_weak_labeled_queries": int(len(frame)),
        "evaluation_protocols": {
            "row_stratified": "exact Phase 4 five-fold assignments; template overlap retained",
            "template_grouped": "exact Phase 4 two-fold assignments; zero template overlap; Monitoring excluded",
        },
        "selected_experiment": selected,
        "selected_representation": EXPERIMENT_LABELS[selected],
        "selection_reason": selection_reason,
        "comparison": comparison.to_dict(orient="records"),
        "structured_prediction_changes": {
            "total": int(len(changes)),
            "fixed_baseline_errors": int(change_counts.get("fixed_baseline_error", 0)),
            "introduced_errors": int(change_counts.get("introduced_error", 0)),
            "changed_but_both_wrong": int(
                change_counts.get("changed_but_both_wrong", 0)
            ),
        },
        "fusion_vs_embedding_changes": {
            "total": int(len(fusion_changes)),
            "fixed_embedding_errors": int(
                fusion_change_counts.get("fixed_embedding_error", 0)
            ),
            "introduced_errors": int(fusion_change_counts.get("introduced_error", 0)),
            "changed_but_both_wrong": int(
                fusion_change_counts.get("changed_but_both_wrong", 0)
            ),
            "grouped_fixed_embedding_errors": int(
                grouped_fusion_change_counts.get("fixed_embedding_error", 0)
            ),
            "grouped_introduced_errors": int(
                grouped_fusion_change_counts.get("introduced_error", 0)
            ),
        },
        "prototype_caveat": (
            "final-taxonomy prototypes are used because literature seeds do not map one-to-one "
            "to final subtypes; prototype agreement influenced evaluation-row retention"
        ),
        "embedding_experiment": {
            "encoder": CONFIG.semantic_model_name,
            "embedding_dimension": 384,
            "fine_tuned": False,
            "cache_reused": str(QUERY_EMBEDDINGS_PATH),
            "selection_bias_note": (
                "the same frozen representation contributed prototype and cluster signals "
                "used by Phase 3 label-quality filtering"
            ),
        },
        "fusion_experiment": {
            "experiment": "T1-E4",
            "feature_blocks": [
                "384-dimensional normalized frozen embedding",
                "entity indicators/counts and contextual slots",
            ],
            "block_normalization": "independent L2 normalization; equal-weight concatenation",
            "outer_fold_tuning": False,
        },
        "most_common_selected_model_confusions": confusion_pairs.head(8).to_dict(
            orient="records"
        ),
        "limitations": [
            "weak labels are not independent clinician gold labels",
            "row-stratified CV permits template reuse",
            "grouped sensitivity excludes one class and has only two folds",
            "prototype evaluation is selection-biased",
            "Other / Ambiguous has zero examples",
            "structured features may encode dataset-specific shortcuts",
        ],
    }

    comparison.to_csv(COMPARISON_PATH, index=False)
    predictions.to_csv(PREDICTIONS_PATH, index=False)
    per_class.to_csv(PER_CLASS_PATH, index=False)
    changes.to_csv(CHANGES_PATH, index=False)
    fusion_changes.to_csv(FUSION_CHANGES_PATH, index=False)
    errors.to_csv(ERRORS_PATH, index=False)
    matrix_frame.to_csv(CONFUSION_PATH)
    confusion_pairs.to_csv(CONFUSION_PAIRS_PATH, index=False)
    slice_metrics.to_csv(SLICE_METRICS_PATH, index=False)
    manual_review.to_csv(MANUAL_REVIEW_PATH, index=False)
    top_features.to_csv(TOP_FEATURES_PATH, index=False)
    METRICS_PATH.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    REPORT_PATH.write_text(build_report(metrics, comparison), encoding="utf-8")
    joblib.dump(model_artifact, MODEL_PATH)
    _plot_confusion(matrix, grouped_labels, selected)
    _update_experiment_log(comparison, selected)

    return {
        "comparison": COMPARISON_PATH,
        "predictions": PREDICTIONS_PATH,
        "per_class_metrics": PER_CLASS_PATH,
        "prediction_changes": CHANGES_PATH,
        "fusion_vs_embedding_changes": FUSION_CHANGES_PATH,
        "errors": ERRORS_PATH,
        "confusion_matrix": CONFUSION_PATH,
        "confusion_pairs": CONFUSION_PAIRS_PATH,
        "confusion_figure": CONFUSION_FIGURE_PATH,
        "slice_metrics": SLICE_METRICS_PATH,
        "manual_error_review": MANUAL_REVIEW_PATH,
        "top_features": TOP_FEATURES_PATH,
        "metrics": METRICS_PATH,
        "report": REPORT_PATH,
        "selected_model": MODEL_PATH,
    }


if __name__ == "__main__":
    for name, path in run_phase5().items():
        print(f"{name}: {path}")
