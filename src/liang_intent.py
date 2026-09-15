"""Weakly supervised adaptation of Liang et al.'s three-branch intent model.

Liang et al. (2025) train a supervised architecture with three inputs:

1. a contextual Transformer representation,
2. sentence-level TF-IDF, and
3. class-centroid TF-IDF.

The branches are projected to a shared space, combined with sample-wise
attention, and passed to a classification head. The original model requires
gold labels and fine-tunes a Chinese RoBERTa encoder. Phase 2 has neither gold
intent labels nor a GPU, so this module makes the minimum explicit adaptation:

* multilingual sentence embeddings are frozen;
* high-precision lexical rules provide weak anchor labels, never final output;
* class centroids are learned from anchors and refreshed with previous-round
  soft predictions, mirroring the paper's leakage-avoiding soft prototype;
* only the small projection, attention, and classification layers are trained;
* final assignments come from the hybrid model, not the anchor rules.

This is a Liang-style weak-supervision adaptation, not an exact reproduction of
the paper's supervised RoBERTa experiment. The distinction is exported with
every run.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.metrics import accuracy_score, f1_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import normalize
import torch
from torch import nn


LIANG_PAPER_URL = "https://doi.org/10.1038/s41598-025-25783-x"


@dataclass(frozen=True)
class LiangAdaptationConfig:
    random_seed: int = 42
    tfidf_max_features: int = 200
    hidden_dim: int = 64
    dropout: float = 0.20
    learning_rate: float = 0.01
    weight_decay: float = 1e-4
    max_epochs: int = 250
    patience: int = 30
    validation_size: float = 0.20
    soft_refinement_rounds: int = 2
    anchor_weight_in_soft_centroid: float = 0.90


@dataclass
class LiangHybridResult:
    assignments: pd.DataFrame
    branch_metrics: pd.DataFrame
    training_history: pd.DataFrame
    tfidf_matrix: csr_matrix
    tfidf_vectorizer: TfidfVectorizer
    selected_tfidf_features: list[str]
    class_centroids: np.ndarray
    methodology: dict[str, object]


class ThreeBranchAttentionClassifier(nn.Module):
    """Small Liang-style projection, inter-branch attention, and classifier."""

    def __init__(self, n_classes: int, hidden_dim: int, dropout: float) -> None:
        super().__init__()
        self.projections = nn.ModuleList(
            [nn.Linear(n_classes, hidden_dim) for _ in range(3)]
        )
        self.attention = nn.Linear(hidden_dim, 1, bias=False)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, n_classes),
        )

    def forward(self, branches: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        projected = torch.stack(
            [torch.tanh(layer(branches[:, index, :])) for index, layer in enumerate(self.projections)],
            dim=1,
        )
        attention_weights = torch.softmax(self.attention(projected).squeeze(-1), dim=1)
        fused = (projected * attention_weights.unsqueeze(-1)).sum(dim=1)
        return self.classifier(fused), attention_weights


def candidate_document(candidate: object) -> str:
    """Create a lexical/semantic prototype from a candidate intent schema row."""
    return (
        f"{candidate.intent_name}. {candidate.definition} "
        f"Include: {candidate.inclusion_criteria}. "
        f"Exclude: {candidate.exclusion_criteria}. "
        f"Examples: {candidate.positive_examples}. "
        f"Boundary: {candidate.boundary_examples}."
    )


def _row_standardize(values: np.ndarray) -> np.ndarray:
    mean = values.mean(axis=1, keepdims=True)
    std = values.std(axis=1, keepdims=True)
    return ((values - mean) / np.maximum(std, 1e-6)).astype(np.float32)


def _build_centroids(
    query_tfidf: csr_matrix,
    class_weights: np.ndarray,
) -> np.ndarray:
    weighted_sum = np.asarray(class_weights.T @ query_tfidf)
    denominators = np.maximum(class_weights.sum(axis=0, keepdims=True).T, 1e-8)
    return normalize(weighted_sum / denominators).astype(np.float32)


def _branch_tensor(
    query_embeddings: np.ndarray,
    candidate_embeddings: np.ndarray,
    query_tfidf: csr_matrix,
    candidate_tfidf: csr_matrix,
    centroids: np.ndarray,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    scores = {
        "semantic": cosine_similarity(query_embeddings, candidate_embeddings),
        "sentence_tfidf": cosine_similarity(query_tfidf, candidate_tfidf),
        "class_centroid_tfidf": cosine_similarity(query_tfidf, centroids),
    }
    branches = np.stack([_row_standardize(scores[name]) for name in scores], axis=1)
    return branches.astype(np.float32), scores


def _class_weights(labels: np.ndarray, n_classes: int) -> torch.Tensor:
    counts = np.bincount(labels, minlength=n_classes).astype(np.float32)
    weights = counts.sum() / np.maximum(counts * n_classes, 1.0)
    return torch.tensor(weights, dtype=torch.float32)


def _fit_attention_model(
    branches: np.ndarray,
    labels: np.ndarray,
    train_indices: np.ndarray,
    validation_indices: np.ndarray | None,
    config: LiangAdaptationConfig,
    round_index: int,
    fixed_epochs: int | None = None,
) -> tuple[ThreeBranchAttentionClassifier, pd.DataFrame, int]:
    torch.manual_seed(config.random_seed + round_index)
    np.random.seed(config.random_seed + round_index)
    model = ThreeBranchAttentionClassifier(
        n_classes=branches.shape[2],
        hidden_dim=config.hidden_dim,
        dropout=config.dropout,
    )
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
    )
    loss_function = nn.CrossEntropyLoss(
        weight=_class_weights(labels[train_indices], branches.shape[2])
    )
    x = torch.tensor(branches, dtype=torch.float32)
    y = torch.tensor(labels, dtype=torch.long)
    best_state = deepcopy(model.state_dict())
    best_epoch = 1
    best_metric = -np.inf
    stale_epochs = 0
    history: list[dict[str, float | int | str]] = []
    epoch_limit = fixed_epochs or config.max_epochs

    for epoch in range(1, epoch_limit + 1):
        model.train()
        optimizer.zero_grad()
        logits, attention = model(x[train_indices])
        loss = loss_function(logits, y[train_indices])
        loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            train_logits, train_attention = model(x[train_indices])
            train_predictions = train_logits.argmax(dim=1).cpu().numpy()
            train_macro_f1 = f1_score(
                labels[train_indices], train_predictions, average="macro", zero_division=0
            )
            if validation_indices is not None:
                validation_logits, _ = model(x[validation_indices])
                validation_predictions = validation_logits.argmax(dim=1).cpu().numpy()
                selection_metric = f1_score(
                    labels[validation_indices],
                    validation_predictions,
                    average="macro",
                    zero_division=0,
                )
            else:
                selection_metric = train_macro_f1
        history.append(
            {
                "round": round_index,
                "stage": "validation_selection" if validation_indices is not None else "full_anchor_fit",
                "epoch": epoch,
                "loss": float(loss.item()),
                "train_macro_f1": float(train_macro_f1),
                "selection_macro_f1": float(selection_metric),
                "mean_semantic_attention": float(train_attention[:, 0].mean()),
                "mean_sentence_tfidf_attention": float(train_attention[:, 1].mean()),
                "mean_class_centroid_attention": float(train_attention[:, 2].mean()),
            }
        )
        if selection_metric > best_metric + 1e-6:
            best_metric = selection_metric
            best_epoch = epoch
            best_state = deepcopy(model.state_dict())
            stale_epochs = 0
        else:
            stale_epochs += 1
        if fixed_epochs is None and stale_epochs >= config.patience:
            break

    model.load_state_dict(best_state)
    return model, pd.DataFrame(history), best_epoch


def _predict(
    model: ThreeBranchAttentionClassifier, branches: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    with torch.no_grad():
        logits, attention = model(torch.tensor(branches, dtype=torch.float32))
        probabilities = torch.softmax(logits, dim=1).cpu().numpy()
    return probabilities, attention.cpu().numpy()


def _branch_metrics(
    raw_scores: dict[str, np.ndarray],
    labels: np.ndarray,
    validation_indices: np.ndarray,
    hybrid_probabilities: np.ndarray,
) -> pd.DataFrame:
    rows: list[dict[str, float | str | int]] = []
    for name, scores in raw_scores.items():
        predictions = scores[validation_indices].argmax(axis=1)
        rows.append(
            {
                "model": name,
                "validation_rows": len(validation_indices),
                "accuracy_vs_weak_anchor": accuracy_score(labels[validation_indices], predictions),
                "macro_f1_vs_weak_anchor": f1_score(
                    labels[validation_indices], predictions, average="macro", zero_division=0
                ),
            }
        )
    hybrid_predictions = hybrid_probabilities[validation_indices].argmax(axis=1)
    rows.append(
        {
            "model": "liang_three_branch_attention",
            "validation_rows": len(validation_indices),
            "accuracy_vs_weak_anchor": accuracy_score(labels[validation_indices], hybrid_predictions),
            "macro_f1_vs_weak_anchor": f1_score(
                labels[validation_indices], hybrid_predictions, average="macro", zero_division=0
            ),
        }
    )
    return pd.DataFrame(rows)


def fit_liang_hybrid_intent_model(
    query_ids: Sequence[str],
    query_texts: Sequence[str],
    query_embeddings: np.ndarray,
    candidates: Sequence[object],
    candidate_embeddings: np.ndarray,
    anchor_labels: Sequence[str | None],
    stop_words: Sequence[str],
    config: LiangAdaptationConfig | None = None,
) -> LiangHybridResult:
    """Fit the weakly supervised Liang-style hybrid and return final assignments."""
    config = config or LiangAdaptationConfig()
    class_names = [candidate.intent_name for candidate in candidates]
    class_to_index = {name: index for index, name in enumerate(class_names)}
    anchor_indices = np.array(
        [index for index, label in enumerate(anchor_labels) if label in class_to_index], dtype=int
    )
    labels = np.full(len(query_texts), -1, dtype=int)
    labels[anchor_indices] = [class_to_index[str(anchor_labels[index])] for index in anchor_indices]
    if len(anchor_indices) == 0 or len(np.unique(labels[anchor_indices])) != len(class_names):
        raise ValueError("Weak anchors must cover every candidate intent class.")

    candidate_documents = [candidate_document(candidate) for candidate in candidates]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True,
        stop_words=list(stop_words),
        token_pattern=r"(?u)\b\w[\w+-]+\b",
    )
    # Liang retains 200 sentence TF-IDF features ranked by chi-squared
    # discrimination. Here chi2 is fit only on weak-anchor rows; candidate
    # prototype documents never influence vocabulary or feature selection.
    full_query_tfidf = vectorizer.fit_transform(query_texts)
    full_candidate_tfidf = vectorizer.transform(candidate_documents)
    n_selected = min(config.tfidf_max_features, full_query_tfidf.shape[1])
    selector = SelectKBest(score_func=chi2, k=n_selected)
    selector.fit(full_query_tfidf[anchor_indices], labels[anchor_indices])
    query_tfidf = selector.transform(full_query_tfidf).tocsr()
    candidate_tfidf = selector.transform(full_candidate_tfidf).tocsr()
    selected_feature_names = vectorizer.get_feature_names_out()[selector.get_support()].tolist()

    train_anchor_indices, validation_indices = train_test_split(
        anchor_indices,
        test_size=config.validation_size,
        random_state=config.random_seed,
        stratify=labels[anchor_indices],
    )
    train_weights = np.zeros((len(query_texts), len(class_names)), dtype=np.float32)
    train_weights[train_anchor_indices, labels[train_anchor_indices]] = 1.0
    validation_centroids = _build_centroids(query_tfidf, train_weights)
    validation_branches, validation_raw_scores = _branch_tensor(
        query_embeddings,
        candidate_embeddings,
        query_tfidf,
        candidate_tfidf,
        validation_centroids,
    )
    validation_model, selection_history, selected_epochs = _fit_attention_model(
        validation_branches,
        labels,
        train_anchor_indices,
        validation_indices,
        config,
        round_index=0,
    )
    validation_probabilities, _ = _predict(validation_model, validation_branches)
    metrics = _branch_metrics(
        validation_raw_scores,
        labels,
        validation_indices,
        validation_probabilities,
    )

    hard_anchor_weights = np.zeros((len(query_texts), len(class_names)), dtype=np.float32)
    hard_anchor_weights[anchor_indices, labels[anchor_indices]] = 1.0
    class_weights = hard_anchor_weights.copy()
    all_history = [selection_history]
    final_probabilities: np.ndarray | None = None
    final_attention: np.ndarray | None = None
    final_centroids: np.ndarray | None = None

    for round_index in range(1, config.soft_refinement_rounds + 2):
        final_centroids = _build_centroids(query_tfidf, class_weights)
        branches, _ = _branch_tensor(
            query_embeddings,
            candidate_embeddings,
            query_tfidf,
            candidate_tfidf,
            final_centroids,
        )
        model, history, _ = _fit_attention_model(
            branches,
            labels,
            anchor_indices,
            validation_indices=None,
            config=config,
            round_index=round_index,
            fixed_epochs=selected_epochs,
        )
        final_probabilities, final_attention = _predict(model, branches)
        all_history.append(history)
        if round_index <= config.soft_refinement_rounds:
            class_weights = final_probabilities.copy()
            class_weights[anchor_indices] = (
                config.anchor_weight_in_soft_centroid * hard_anchor_weights[anchor_indices]
                + (1.0 - config.anchor_weight_in_soft_centroid)
                * final_probabilities[anchor_indices]
            )

    assert final_probabilities is not None
    assert final_attention is not None
    assert final_centroids is not None
    order = np.argsort(final_probabilities, axis=1)[:, ::-1]
    assignments = pd.DataFrame(
        {
            "query_id": list(query_ids),
            "liang_final_intent": [class_names[index] for index in order[:, 0]],
            "liang_top_probability": final_probabilities[np.arange(len(query_texts)), order[:, 0]],
            "liang_second_intent": [class_names[index] for index in order[:, 1]],
            "liang_second_probability": final_probabilities[np.arange(len(query_texts)), order[:, 1]],
            "liang_probability_margin": (
                final_probabilities[np.arange(len(query_texts)), order[:, 0]]
                - final_probabilities[np.arange(len(query_texts)), order[:, 1]]
            ),
            "attention_semantic": final_attention[:, 0],
            "attention_sentence_tfidf": final_attention[:, 1],
            "attention_class_centroid_tfidf": final_attention[:, 2],
            "weak_anchor_label": [label if label in class_to_index else "" for label in anchor_labels],
            "used_as_weak_anchor": [index in set(anchor_indices.tolist()) for index in range(len(query_texts))],
        }
    )
    for class_index, class_name in enumerate(class_names):
        safe_name = "".join(character if character.isalnum() else "_" for character in class_name.lower()).strip("_")
        assignments[f"probability_{safe_name}"] = final_probabilities[:, class_index]

    methodology = {
        "paper": LIANG_PAPER_URL,
        "status": "weakly supervised CPU adaptation; not an exact reproduction",
        "published_branches": ["RoBERTa-wwm-ext", "sentence TF-IDF", "class-centroid TF-IDF"],
        "implemented_branches": [
            "frozen multilingual candidate-prototype semantic similarity",
            "sentence/candidate TF-IDF similarity",
            "weak-anchor and soft-prediction class-centroid TF-IDF similarity",
        ],
        "attention": "learned sample-wise inter-branch attention",
        "classification_head": "64-dimensional nonlinear head with dropout and weighted cross-entropy",
        "gold_labels_used": False,
        "weak_anchor_rows": int(len(anchor_indices)),
        "validation_rows": int(len(validation_indices)),
        "selected_epochs": int(selected_epochs),
        "soft_refinement_rounds": int(config.soft_refinement_rounds),
        "tfidf_max_features": int(config.tfidf_max_features),
        "tfidf_feature_selection": "chi-squared ranking on weak-anchor rows",
        "candidate_intents": class_names,
        "config": asdict(config),
        "limitations": [
            "The original paper uses gold labels; this adaptation uses high-precision weak anchors.",
            "The original paper fine-tunes Chinese RoBERTa; this adaptation freezes multilingual MiniLM.",
            "Validation metrics measure agreement with held-out weak anchors, not clinical gold accuracy.",
            "Candidate intent names and definitions remain analyst hypotheses; the model estimates support and assignments.",
        ],
    }
    return LiangHybridResult(
        assignments=assignments,
        branch_metrics=metrics,
        training_history=pd.concat(all_history, ignore_index=True),
        tfidf_matrix=query_tfidf,
        tfidf_vectorizer=vectorizer,
        selected_tfidf_features=selected_feature_names,
        class_centroids=final_centroids,
        methodology=methodology,
    )
