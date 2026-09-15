"""Phase 4 leakage-aware TF-IDF + Logistic Regression intent baseline.

Only the Phase 3 reviewed reference subset is used for evaluation and model
fitting. Entity-delexicalized query templates are kept within one fold so the
highly templated supplied data cannot produce optimistic train/test leakage.
"""

from __future__ import annotations

from hashlib import sha1
import os
import re
from typing import Any

from src.config import (
    CACHE_DIR,
    CONFIG,
    EXPERIMENT_LOG_PATH,
    FIGURES_DIR,
    METRICS_DIR,
)

os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline

from src.intent import (
    INTENT_NAMES,
    OTHER_INTENT,
    PARENT_BY_INTENT,
)
from src.taxonomy import delexicalize_query


PHASE4_PREFIX = "phase4_intent_baseline"
CLASS_CHECKS_PATH = METRICS_DIR / f"{PHASE4_PREFIX}_class_checks.csv"
CLUSTER_PURITY_PATH = METRICS_DIR / f"{PHASE4_PREFIX}_cluster_purity.csv"
NEAREST_PAIRS_PATH = METRICS_DIR / f"{PHASE4_PREFIX}_nearest_class_pairs.csv"
CV_PREDICTIONS_PATH = METRICS_DIR / f"{PHASE4_PREFIX}_cv_predictions.csv"
FOLD_METRICS_PATH = METRICS_DIR / f"{PHASE4_PREFIX}_fold_metrics.csv"
PER_CLASS_METRICS_PATH = METRICS_DIR / f"{PHASE4_PREFIX}_per_class_metrics.csv"
TOP_LEVEL_PER_CLASS_PATH = METRICS_DIR / f"{PHASE4_PREFIX}_top_level_per_class_metrics.csv"
CONFUSION_MATRIX_PATH = METRICS_DIR / f"{PHASE4_PREFIX}_confusion_matrix.csv"
ERROR_ANALYSIS_PATH = METRICS_DIR / f"{PHASE4_PREFIX}_errors.csv"
TOP_FEATURES_PATH = METRICS_DIR / f"{PHASE4_PREFIX}_top_features.csv"
GROUPED_SENSITIVITY_PATH = METRICS_DIR / f"{PHASE4_PREFIX}_grouped_sensitivity_predictions.csv"
METRICS_PATH = METRICS_DIR / f"{PHASE4_PREFIX}_metrics.json"
REPORT_PATH = METRICS_DIR / f"{PHASE4_PREFIX}_report.md"
MODEL_PATH = METRICS_DIR / f"{PHASE4_PREFIX}_model.joblib"
CONFUSION_FIGURE_PATH = FIGURES_DIR / f"{PHASE4_PREFIX}_confusion_matrix.png"

SHORT_LABELS = {
    "Management / Treatment Selection": "Management",
    "Dosing / Administration": "Dosing",
    "Safety / Contraindication": "Safety",
    "Interaction / Combination": "Interaction",
    "Comparative Treatment Choice": "Comparison",
    "Monitoring / Response / Risk Assessment": "Monitoring",
    "Efficacy / Outcomes": "Efficacy",
    "Guideline / Evidence Lookup": "Guideline",
    "Treatment Change / Escalation": "Escalation",
    "Prophylaxis / Maintenance": "Prophylaxis",
    "Mechanism / Background Knowledge": "Mechanism",
}


def normalize_template(row: pd.Series) -> str:
    """Return a conservative entity- and number-delexicalized template key."""
    text = delexicalize_query(row).lower()
    text = re.sub(r"\b\d+(?:\.\d+)?\b", " <num> ", text)
    text = re.sub(r"[^\w<>]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def template_id(template: str) -> str:
    return sha1(template.encode("utf-8")).hexdigest()[:12]


def build_pipeline() -> Pipeline:
    """Build the intentionally simple Phase 4 text-only baseline."""
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents="unicode",
                    ngram_range=CONFIG.intent_tfidf_ngram_range,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=CONFIG.intent_logreg_c,
                    class_weight="balanced",
                    max_iter=2_000,
                    random_state=CONFIG.random_seed,
                    solver="liblinear",
                ),
            ),
        ]
    )


def assign_stratified_group_folds(
    frame: pd.DataFrame, n_splits: int = 2
) -> np.ndarray:
    """Assign label-pure template groups to balanced, stratified folds.

    This helper supports the template-held-out sensitivity analysis. Classes
    with fewer than two templates must be removed before it is called.
    """
    group_label_counts = frame.groupby("template")["intent"].nunique()
    if int(group_label_counts.max()) != 1:
        raise ValueError("A delexicalized template maps to multiple intent labels")
    groups_per_class = frame.groupby("intent")["template"].nunique()
    if int(groups_per_class.min()) < n_splits:
        raise ValueError("Not enough independent templates per class for grouped CV")

    rng = np.random.default_rng(CONFIG.random_seed)
    fold_by_template: dict[str, int] = {}
    global_rows = np.zeros(n_splits, dtype=int)
    for intent in sorted(frame["intent"].unique()):
        subset = frame[frame["intent"].eq(intent)]
        sizes = subset.groupby("template").size().rename("n_rows").reset_index()
        sizes["tie"] = rng.random(len(sizes))
        sizes = sizes.sort_values(["n_rows", "tie"], ascending=[False, True])
        class_rows = np.zeros(n_splits, dtype=int)
        for row in sizes.itertuples(index=False):
            target = min(range(n_splits), key=lambda f: (class_rows[f], global_rows[f], f))
            fold_by_template[row.template] = target
            class_rows[target] += int(row.n_rows)
            global_rows[target] += int(row.n_rows)

    folds = frame["template"].map(fold_by_template).to_numpy(dtype=int)
    if np.any(folds < 0):
        raise AssertionError("Every row must receive a fold")
    return folds


def _aggregate_metrics(y_true: pd.Series | np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "macro_precision": float(
            precision_score(y_true, y_pred, average="macro", zero_division=0)
        ),
        "macro_recall": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(
            f1_score(y_true, y_pred, average="weighted", zero_division=0)
        ),
        "accuracy": float(accuracy_score(y_true, y_pred)),
    }


def _per_class_metrics(
    y_true: pd.Series,
    y_pred: pd.Series,
    labels: list[str],
    level: str,
    template_counts: dict[str, int] | None = None,
    minimum_fold_support: dict[str, int] | None = None,
) -> pd.DataFrame:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    rows = pd.DataFrame(
        {
            "label_level": level,
            "label": labels,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support.astype(int),
        }
    )
    if template_counts is not None:
        rows["independent_template_groups"] = rows["label"].map(template_counts).astype(int)
        rows["minimum_test_fold_support"] = rows["label"].map(minimum_fold_support).astype(int)
        rows["interpretation"] = np.where(
            rows["independent_template_groups"].ge(5),
            "reportable_with_small-sample_caution",
            "descriptive_only_low_template_diversity",
        )
    return rows


def build_taxonomy_checks(
    labeled: pd.DataFrame, weak_labeled: pd.DataFrame, signals: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build every sanity check requested before classifier training."""
    signal_columns = signals[
        ["query_id", "cluster_id", "prototype_intent_signal", "prototype_margin"]
    ]
    all_with_signals = labeled.merge(signal_columns, on="query_id", validate="one_to_one")
    weak_with_signals = weak_labeled[["query_id", "intent"]].merge(
        signal_columns, on="query_id", validate="one_to_one"
    )

    full_counts = labeled["intent"].value_counts()
    weak_counts = weak_labeled["intent"].value_counts()
    full_margin = all_with_signals.groupby("intent")["prototype_margin"].mean()
    weak_margin = weak_with_signals.groupby("intent")["prototype_margin"].mean()
    template_counts = weak_labeled.copy()
    template_counts["template"] = template_counts.apply(normalize_template, axis=1)
    template_counts = template_counts.groupby("intent")["template"].nunique()

    checks = pd.DataFrame({"intent": list(INTENT_NAMES) + [OTHER_INTENT]})
    checks["all_query_count"] = checks["intent"].map(full_counts).fillna(0).astype(int)
    checks["weak_label_count"] = checks["intent"].map(weak_counts).fillna(0).astype(int)
    checks["weak_label_template_groups"] = checks["intent"].map(template_counts).fillna(0).astype(int)
    checks["average_prototype_margin_all"] = checks["intent"].map(full_margin)
    checks["average_prototype_margin_weak_set"] = checks["intent"].map(weak_margin)
    checks["cv_evaluable"] = (
        checks["weak_label_count"].ge(CONFIG.intent_cv_splits)
    )
    checks["sparsity_note"] = np.select(
        [
            checks["weak_label_count"].eq(0),
            checks["weak_label_template_groups"].lt(5),
        ],
        ["not_observed", "limited_independent_template_diversity"],
        default="adequate_for_weak_label_cv",
    )

    cluster_counts = (
        weak_with_signals.groupby(["cluster_id", "intent"]).size().rename("n").reset_index()
    )
    cluster_rows: list[dict[str, Any]] = []
    for cluster_id, group in cluster_counts.groupby("cluster_id"):
        dominant = group.sort_values(["n", "intent"], ascending=[False, True]).iloc[0]
        total = int(group["n"].sum())
        probs = group["n"].to_numpy(dtype=float) / total
        cluster_rows.append(
            {
                "cluster_id": int(cluster_id),
                "weak_label_count": total,
                "n_intents": int(len(group)),
                "dominant_intent": str(dominant["intent"]),
                "dominant_count": int(dominant["n"]),
                "purity": float(dominant["n"] / total),
                "entropy_nats": float(-(probs * np.log(probs)).sum()),
            }
        )
    cluster_purity = pd.DataFrame(cluster_rows).sort_values("cluster_id")

    disagreements = weak_with_signals[
        weak_with_signals["prototype_intent_signal"].ne(weak_with_signals["intent"])
    ]
    nearest_pairs = (
        disagreements.groupby(["intent", "prototype_intent_signal"], as_index=False)
        .agg(n_queries=("query_id", "size"), average_prototype_margin=("prototype_margin", "mean"))
        .rename(columns={"intent": "weak_label_intent", "prototype_intent_signal": "nearest_prototype_intent"})
        .sort_values(["n_queries", "weak_label_intent"], ascending=[False, True])
    )

    summary = {
        "n_final_classes": int(labeled["intent"].nunique()),
        "other_ambiguous_count": int(labeled["intent"].eq(OTHER_INTENT).sum()),
        "other_ambiguous_proportion": float(labeled["intent"].eq(OTHER_INTENT).mean()),
        "weak_label_training_size": int(len(weak_labeled)),
        "minimum_weak_label_class_count": int(weak_counts.min()),
        "minimum_weak_label_template_groups": int(template_counts.min()),
        "classes_not_cv_evaluable": checks.loc[~checks["cv_evaluable"], "intent"].tolist(),
        "weighted_weak_label_cluster_purity": float(
            np.average(cluster_purity["purity"], weights=cluster_purity["weak_label_count"])
        ),
        "prototype_disagreements_on_weak_set": int(len(disagreements)),
    }
    return checks, cluster_purity, nearest_pairs, summary


def run_cross_validation(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    splitter = StratifiedKFold(
        n_splits=CONFIG.intent_cv_splits,
        shuffle=True,
        random_state=CONFIG.random_seed,
    )
    folds = np.full(len(frame), -1, dtype=int)
    for fold, (_, test_indices) in enumerate(
        splitter.split(frame["query_text"], frame["intent"])
    ):
        folds[test_indices] = fold
    records: list[dict[str, Any]] = []
    fold_metrics: list[dict[str, Any]] = []

    for fold in range(CONFIG.intent_cv_splits):
        train = frame[folds != fold]
        test = frame[folds == fold]
        train_templates = set(train["template"])
        test_templates = set(test["template"])
        overlap = train_templates & test_templates
        if set(train["intent"]) != set(INTENT_NAMES) or set(test["intent"]) != set(INTENT_NAMES):
            raise AssertionError("Every fold must contain every supported subtype")

        model = build_pipeline()
        model.fit(train["query_text"], train["intent"])
        predicted = model.predict(test["query_text"])
        probabilities = model.predict_proba(test["query_text"])
        classes = model.named_steps["classifier"].classes_
        order = np.argsort(probabilities, axis=1)

        subtype_metrics = _aggregate_metrics(test["intent"], predicted)
        true_top = test["intent_top_level"].to_numpy()
        predicted_top = np.asarray([PARENT_BY_INTENT[value] for value in predicted])
        top_metrics = _aggregate_metrics(true_top, predicted_top)
        for level, metric_values in (("subtype", subtype_metrics), ("top_level", top_metrics)):
            fold_metrics.append(
                {
                    "fold": fold + 1,
                    "label_level": level,
                    "n_train": int(len(train)),
                    "n_test": int(len(test)),
                    "n_train_templates": int(train["template"].nunique()),
                    "n_test_templates": int(test["template"].nunique()),
                    "template_overlap": int(len(overlap)),
                    **metric_values,
                }
            )

        for position, (index, row) in enumerate(test.iterrows()):
            top_index = int(order[position, -1])
            second_index = int(order[position, -2])
            records.append(
                {
                    "query_id": row["query_id"],
                    "query_text": row["query_text"],
                    "language": row["language"],
                    "fold": fold + 1,
                    "template_id": template_id(row["template"]),
                    "true_intent": row["intent"],
                    "predicted_intent": str(classes[top_index]),
                    "predicted_probability": float(probabilities[position, top_index]),
                    "second_intent": str(classes[second_index]),
                    "second_probability": float(probabilities[position, second_index]),
                    "probability_margin": float(
                        probabilities[position, top_index] - probabilities[position, second_index]
                    ),
                    "true_top_level": row["intent_top_level"],
                    "predicted_top_level": PARENT_BY_INTENT[str(classes[top_index])],
                    "correct_subtype": bool(row["intent"] == classes[top_index]),
                    "correct_top_level": bool(
                        row["intent_top_level"] == PARENT_BY_INTENT[str(classes[top_index])]
                    ),
                }
            )

    predictions = pd.DataFrame(records).sort_values("query_id")
    if len(predictions) != len(frame) or predictions["query_id"].nunique() != len(frame):
        raise AssertionError("Grouped CV must emit one prediction per reviewed query")
    return predictions, pd.DataFrame(fold_metrics)


def run_grouped_sensitivity(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Estimate transfer to unseen templates where grouped CV is feasible.

    Monitoring has a single template after the three-way disagreements are
    removed, so it cannot appear in both train and test without leakage. It is
    excluded only from this secondary diagnostic, not from the primary model.
    """
    template_counts = frame.groupby("intent")["template"].nunique()
    excluded = sorted(template_counts[template_counts.lt(2)].index.tolist())
    subset = frame[~frame["intent"].isin(excluded)].copy().reset_index(drop=True)
    folds = assign_stratified_group_folds(subset, n_splits=2)
    records: list[dict[str, Any]] = []
    for fold in range(2):
        train = subset[folds != fold]
        test = subset[folds == fold]
        if set(train["template"]) & set(test["template"]):
            raise AssertionError("Grouped sensitivity analysis leaked a template")
        model = build_pipeline()
        model.fit(train["query_text"], train["intent"])
        predicted = model.predict(test["query_text"])
        for position, (_, row) in enumerate(test.iterrows()):
            records.append(
                {
                    "query_id": row["query_id"],
                    "query_text": row["query_text"],
                    "fold": fold + 1,
                    "template_id": template_id(row["template"]),
                    "true_intent": row["intent"],
                    "predicted_intent": predicted[position],
                    "correct": bool(row["intent"] == predicted[position]),
                }
            )
    predictions = pd.DataFrame(records).sort_values("query_id")
    diagnostic = {
        "purpose": "secondary unseen-template transfer diagnostic",
        "n_queries": int(len(subset)),
        "n_classes": int(subset["intent"].nunique()),
        "excluded_classes": excluded,
        "excluded_reason": "fewer than two independent templates after weak-label filtering",
        "n_splits": 2,
        "template_overlap_each_fold": [0, 0],
        **_aggregate_metrics(
            predictions["true_intent"], predictions["predicted_intent"].to_numpy()
        ),
    }
    return predictions, diagnostic


def _fit_final_model(frame: pd.DataFrame) -> tuple[Pipeline, pd.DataFrame]:
    model = build_pipeline()
    model.fit(frame["query_text"], frame["intent"])
    vectorizer = model.named_steps["tfidf"]
    classifier = model.named_steps["classifier"]
    terms = np.asarray(vectorizer.get_feature_names_out())
    rows: list[dict[str, Any]] = []
    for class_index, intent in enumerate(classifier.classes_):
        coefficients = classifier.coef_[class_index]
        for rank, feature_index in enumerate(np.argsort(coefficients)[-15:][::-1], start=1):
            rows.append(
                {
                    "intent": intent,
                    "rank": rank,
                    "feature": terms[feature_index],
                    "coefficient": float(coefficients[feature_index]),
                }
            )
    return model, pd.DataFrame(rows)


def _plot_confusion(matrix: np.ndarray, labels: list[str]) -> None:
    row_totals = matrix.sum(axis=1, keepdims=True)
    normalized = np.divide(
        matrix,
        row_totals,
        out=np.zeros_like(matrix, dtype=float),
        where=row_totals != 0,
    )
    figure, axis = plt.subplots(figsize=(12, 10))
    image = axis.imshow(normalized, cmap="Blues", vmin=0, vmax=1)
    display_labels = [SHORT_LABELS[label] for label in labels]
    axis.set_xticks(range(len(labels)), display_labels, rotation=45, ha="right")
    axis.set_yticks(range(len(labels)), display_labels)
    axis.set_xlabel("Predicted intent")
    axis.set_ylabel("Reviewed intent")
    axis.set_title("Phase 4 weak-label CV confusion matrix (row normalized)")
    for i in range(len(labels)):
        for j in range(len(labels)):
            value = normalized[i, j]
            if value >= 0.01:
                axis.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=7,
                          color="white" if value > 0.55 else "black")
    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    figure.tight_layout()
    figure.savefig(CONFUSION_FIGURE_PATH, dpi=180, bbox_inches="tight")
    plt.close(figure)


def _update_experiment_log(macro_f1: float) -> None:
    log = pd.read_csv(EXPERIMENT_LOG_PATH)
    mask = log["experiment"].eq("T1-B0")
    if int(mask.sum()) != 1:
        raise AssertionError("Experiment log must contain exactly one T1-B0 row")
    log.loc[mask, "result"] = f"5-fold weak-label Macro F1={macro_f1:.3f}"
    log.loc[mask, "decision"] = "retain; audit template-transfer sensitivity"
    log.to_csv(EXPERIMENT_LOG_PATH, index=False)


def build_report(metrics: dict[str, Any], class_checks: pd.DataFrame) -> str:
    overall = metrics["out_of_fold_metrics"]
    top = metrics["top_level_out_of_fold_metrics"]
    sensitivity = metrics["template_grouped_sensitivity"]
    limited = class_checks.loc[
        class_checks["sparsity_note"].eq("limited_independent_template_diversity"), "intent"
    ].tolist()
    return f"""# Phase 4: Intent Classification Baseline

## Outcome

The text-only TF-IDF + Logistic Regression baseline reaches **{overall['macro_f1']:.3f} macro F1** in five-fold cross-validation over 362 Phase 3 weak labels after excluding the 138 three-way disagreements. Macro precision is {overall['macro_precision']:.3f}, macro recall is {overall['macro_recall']:.3f}, weighted F1 is {overall['weighted_f1']:.3f}, and accuracy is {overall['accuracy']:.3f}. These numbers measure agreement with the weak-label policy, not clinical accuracy. Accuracy is retained only as a secondary descriptive metric.

The broader top-level intent evaluation reaches {top['macro_f1']:.3f} macro F1. This top-level score uses the fixed Phase 2 subtype-to-parent mapping, including the two multi-parent labels retained by the taxonomy.

## Evaluation design

The training set contains 151 unanimous cases, 127 two-signal agreements that include the rule, and 84 prototype-plus-cluster agreements against the rule. The 138 three-way disagreements are excluded. For the 84 rule-versus-semantic conflicts, the target remains the frozen Phase 3 schema-adjudicated rule label; their conflict status remains in the source dataset and is not treated as independent consensus. The estimator is word unigram/bigram TF-IDF followed by class-balanced Logistic Regression (`liblinear`, C={CONFIG.intent_logreg_c}). No supplied entities, contextual slots, embeddings, rules, or Phase 2 signal columns are model inputs.

The weak-label set is highly templated: 362 queries collapse to {metrics['cv_design']['n_template_groups']} entity-delexicalized templates. Five-fold stratification is possible by row because every class has at least {metrics['taxonomy_sanity']['minimum_weak_label_class_count']} examples. It cannot also hold out every near-duplicate template while evaluating all 11 classes: Monitoring / Response / Risk Assessment has only one independent template after filtering. Near-identical entity-swapped phrasings therefore cross folds, and the primary score is explicitly a weak-label replication estimate.

As a sensitivity analysis, two-fold template-grouped CV is run on the {sensitivity['n_classes']} classes with at least two templates. It has zero template overlap and reaches {sensitivity['macro_f1']:.3f} macro F1 and {sensitivity['accuracy']:.3f} accuracy across {sensitivity['n_queries']} queries. Monitoring / Response / Risk Assessment is excluded from this diagnostic because unseen-template evaluation is mathematically impossible with one template. The gap between row-stratified and template-held-out results is direct evidence that the model relies heavily on recurring query forms.

## Taxonomy sanity checks

- Final supported classes: {metrics['taxonomy_sanity']['n_final_classes']}.
- `Other / Ambiguous`: {metrics['taxonomy_sanity']['other_ambiguous_count']} of 500 ({metrics['taxonomy_sanity']['other_ambiguous_proportion']:.1%}). It cannot be trained or evaluated because it is unobserved.
- Smallest retained weak-label class: {metrics['taxonomy_sanity']['minimum_weak_label_class_count']} rows.
- Weighted cluster purity against retained weak intent: {metrics['taxonomy_sanity']['weighted_weak_label_cluster_purity']:.3f}.
- Prototype disagreements against the retained schema label: {metrics['taxonomy_sanity']['prototype_disagreements_on_weak_set']}.

All 11 observed subtypes are evaluable in row-stratified weak-label CV. Per-class metrics remain descriptive. The following classes have fewer than five independent delexicalized templates and therefore especially limited evidence of linguistic generalization: {', '.join(limited)}.

## Interpretation and limitations

This is a transparent lexical baseline trained on deliberately retained weak supervision, not a clinical-validity estimate. The labels are not independently clinician-annotated, the prototype and cluster signals are correlated, and the cluster mapping was optimized in-sample. High row-stratified performance is expected when label rules and query templates share explicit lexical cues. The grouped sensitivity result, confusion matrix, and error table should guide later failure analysis; none should be used to claim production readiness.
"""
