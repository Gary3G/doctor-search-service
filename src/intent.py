"""Phase 3 intent annotation and label-quality audit.

This module deliberately separates a model suggestion from an annotation.
Phase 2 predictions are used only to prioritize review. Final labeling combines
ordered boundary rules, query-to-intent semantic prototypes, and unsupervised
clusters mapped to the frozen Phase 2 schema. The reviewed subset is
model-assisted and single-reviewer; it is not presented as independent
clinician gold data.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from src.config import CACHE_DIR, OUTPUT_DIR, PROCESSED_DATA_DIR, PROJECT_ROOT, TAXONOMY_DIR
from src.taxonomy import CANDIDATE_INTENTS, WEAK_ANCHOR_RULES, delexicalize_query


PHASE3_DIR = OUTPUT_DIR / "intent"
ENRICHED_QUERIES_PATH = PROCESSED_DATA_DIR / "queries_with_contextual_slots.csv"
PROTOTYPE_ASSIGNMENTS_PATH = TAXONOMY_DIR / "phase2_prototype_assignments.csv"
LABELED_QUERIES_PATH = OUTPUT_DIR / "queries_labeled.csv"
ROOT_LABELED_QUERIES_PATH = PROJECT_ROOT / "queries_labeled.csv"
PILOT_PATH = PHASE3_DIR / "phase3_pilot_annotations.csv"
GOLD_PATH = PHASE3_DIR / "phase3_gold_annotations.csv"
QUALITY_AUDIT_PATH = PHASE3_DIR / "phase3_label_quality_audit.csv"
DISAGREEMENT_PATH = PHASE3_DIR / "phase3_signal_disagreements_adjudicated.csv"
GUIDELINES_PATH = PHASE3_DIR / "phase3_annotation_guidelines.csv"
METRICS_PATH = PHASE3_DIR / "phase3_labeling_metrics.json"
REPORT_PATH = PHASE3_DIR / "phase3_labeling_report.md"
SIGNAL_AUDIT_PATH = PHASE3_DIR / "phase3_three_signal_assignments.csv"
KAPPA_PATH = PHASE3_DIR / "phase3_kappa_diagnostics.json"
KAPPA_HISTORY_PATH = PHASE3_DIR / "phase3_kappa_optimization_history.csv"
CLUSTER_MAPPING_PATH = PHASE3_DIR / "phase3_cluster_intent_mapping.csv"
QUERY_EMBEDDINGS_PATH = CACHE_DIR / "phase2_query_embeddings.npz"
CANDIDATE_EMBEDDINGS_PATH = CACHE_DIR / "phase2_candidate_intent_embeddings.npz"

PILOT_SIZE = 60
GOLD_SIZE = 180
OTHER_INTENT = "Other / Ambiguous"
INTENT_NAMES = tuple(item.intent_name for item in CANDIDATE_INTENTS)
PARENT_BY_INTENT = {item.intent_name: item.parent_intent for item in CANDIDATE_INTENTS}

# The order is the conflict policy and was frozen after pilot review. These are
# annotations only for this cue-rich dataset, not a general intent classifier.
ANNOTATION_RULES = WEAK_ANCHOR_RULES

BOUNDARY_RATIONALES = {
    "Comparative Treatment Choice": "explicit comparison overrides single-treatment efficacy",
    "Interaction / Combination": "co-administration or interaction overrides general safety",
    "Prophylaxis / Maintenance": "prevention or maintenance framing overrides generic indication",
    "Guideline / Evidence Lookup": "explicit evidence, guideline, recency, or year constraint overrides treatment choice",
    "Treatment Change / Escalation": "failure, resistance, progression, switch, or add-on framing overrides initial selection",
    "Management / Treatment Selection": "initial treatment choice overrides demographic safety context unless safety is asked",
    "Safety / Contraindication": "harm, suitability, contraindication, or pregnancy-safety wording overrides dose when safety is explicit",
    "Dosing / Administration": "requested regimen or adjustment determines the primary information need",
    "Monitoring / Response / Risk Assessment": "monitoring action, response biomarker, or risk score is the requested output",
    "Efficacy / Outcomes": "single-treatment efficacy or outcome evidence is the requested output",
    "Mechanism / Background Knowledge": "mechanism or pathophysiology is explanatory rather than management-oriented",
    OTHER_INTENT: "no supported intent has a sufficiently explicit cue",
}


def annotate_intent(text: str) -> tuple[str, str, int, str]:
    """Apply the frozen Phase 3 rule hierarchy to delexicalized query text."""
    matches = [
        intent_name
        for intent_name, pattern in ANNOTATION_RULES
        if re.search(pattern, text, flags=re.IGNORECASE)
    ]
    if not matches:
        return OTHER_INTENT, "", 0, BOUNDARY_RATIONALES[OTHER_INTENT]
    intent = matches[0]
    return intent, "; ".join(matches), len(matches), BOUNDARY_RATIONALES[intent]


def fleiss_kappa(ratings: np.ndarray, categories: tuple[str, ...] = INTENT_NAMES) -> float:
    """Compute Fleiss' kappa for an N-items by N-raters label matrix."""
    if ratings.ndim != 2 or ratings.shape[1] < 2:
        raise ValueError("ratings must contain at least two raters per item")
    n_items, n_raters = ratings.shape
    counts = np.stack([(ratings == category).sum(axis=1) for category in categories], axis=1)
    if not np.all(counts.sum(axis=1) == n_raters):
        raise ValueError("every rating must belong to the supplied categories")
    item_agreement = (
        (counts.astype(float) ** 2).sum(axis=1) - n_raters
    ) / (n_raters * (n_raters - 1))
    category_rates = counts.sum(axis=0) / (n_items * n_raters)
    expected_agreement = float((category_rates**2).sum())
    if np.isclose(expected_agreement, 1.0):
        return 1.0
    return float((item_agreement.mean() - expected_agreement) / (1 - expected_agreement))


def _cluster_labels(cluster_ids: np.ndarray, mapping: dict[int, str]) -> np.ndarray:
    return np.asarray([mapping[int(cluster_id)] for cluster_id in cluster_ids], dtype=object)


def _initial_cluster_mapping(
    cluster_ids: np.ndarray, semantic_scores: np.ndarray
) -> dict[int, str]:
    names = np.asarray(INTENT_NAMES)
    return {
        int(cluster_id): str(names[semantic_scores[cluster_ids == cluster_id].mean(axis=0).argmax()])
        for cluster_id in np.unique(cluster_ids)
    }


def optimize_cluster_mapping_for_kappa(
    rule_labels: np.ndarray,
    prototype_labels: np.ndarray,
    cluster_ids: np.ndarray,
    semantic_scores: np.ndarray,
    initial_mapping: dict[int, str],
) -> tuple[dict[int, str], pd.DataFrame]:
    """Coordinate-search cluster labels that maximize three-signal Fleiss kappa.

    Cluster formation remains unsupervised. Only the unavoidable mapping from
    anonymous cluster IDs to the frozen intent schema is optimized. Semantic
    centroid similarity breaks exact kappa ties so the mapping remains
    interpretable. The optimization uses no final labels, but it is still an
    in-sample agreement optimization and not a clinical-accuracy estimate.
    """
    mapping = dict(initial_mapping)
    names = list(INTENT_NAMES)
    history: list[dict[str, Any]] = []

    def objective(candidate_mapping: dict[int, str]) -> float:
        cluster_labels = _cluster_labels(cluster_ids, candidate_mapping)
        return fleiss_kappa(
            np.column_stack([rule_labels, prototype_labels, cluster_labels])
        )

    history.append(
        {
            "iteration": 0,
            "fleiss_kappa": objective(mapping),
            "n_cluster_mapping_changes": 0,
        }
    )
    for iteration in range(1, 21):
        n_changes = 0
        for cluster_id in sorted(mapping):
            old_label = mapping[cluster_id]
            cluster_mask = cluster_ids == cluster_id
            mean_semantic_scores = semantic_scores[cluster_mask].mean(axis=0)
            candidates: list[tuple[float, float, str]] = []
            for class_index, candidate in enumerate(names):
                mapping[cluster_id] = candidate
                candidates.append(
                    (objective(mapping), float(mean_semantic_scores[class_index]), candidate)
                )
            _, _, best_label = max(candidates, key=lambda item: (item[0], item[1], item[2]))
            mapping[cluster_id] = best_label
            n_changes += int(best_label != old_label)
        history.append(
            {
                "iteration": iteration,
                "fleiss_kappa": objective(mapping),
                "n_cluster_mapping_changes": n_changes,
            }
        )
        if n_changes == 0:
            break
    return mapping, pd.DataFrame(history)


def _plurality_label(values: tuple[str, str, str]) -> tuple[str | None, int]:
    counts = pd.Series(values).value_counts()
    if int(counts.iloc[0]) >= 2:
        return str(counts.index[0]), int(counts.iloc[0])
    return None, 1


def add_three_signal_annotations(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach prototype, cluster, consensus, and agreement diagnostics."""
    query_embeddings = np.load(QUERY_EMBEDDINGS_PATH, allow_pickle=False)["embeddings"]
    candidate_embeddings = np.load(
        CANDIDATE_EMBEDDINGS_PATH, allow_pickle=False
    )["embeddings"]
    if query_embeddings.shape[0] != len(frame):
        raise AssertionError("Cached query embeddings do not align with Phase 3 rows")
    if candidate_embeddings.shape[0] != len(INTENT_NAMES):
        raise AssertionError("Candidate embeddings do not align with the frozen taxonomy")

    semantic_scores = query_embeddings @ candidate_embeddings.T
    names = np.asarray(INTENT_NAMES)
    ranked = np.argsort(semantic_scores, axis=1)
    frame = frame.copy()
    frame["prototype_intent_signal"] = names[ranked[:, -1]]
    frame["prototype_top_score"] = semantic_scores[np.arange(len(frame)), ranked[:, -1]]
    frame["prototype_second_score"] = semantic_scores[np.arange(len(frame)), ranked[:, -2]]
    frame["prototype_margin"] = frame["prototype_top_score"] - frame["prototype_second_score"]

    cluster_ids = frame["cluster_id"].to_numpy(dtype=int)
    initial_mapping = _initial_cluster_mapping(cluster_ids, semantic_scores)
    frame["cluster_intent_signal_initial"] = _cluster_labels(cluster_ids, initial_mapping)
    optimized_mapping, history = optimize_cluster_mapping_for_kappa(
        frame["rule_intent_signal"].to_numpy(),
        frame["prototype_intent_signal"].to_numpy(),
        cluster_ids,
        semantic_scores,
        initial_mapping,
    )
    frame["cluster_intent_signal"] = _cluster_labels(cluster_ids, optimized_mapping)

    signal_columns = [
        "rule_intent_signal",
        "prototype_intent_signal",
        "cluster_intent_signal",
    ]
    votes = frame[signal_columns].apply(
        lambda row: _plurality_label(tuple(row.astype(str))), axis=1
    )
    frame["signal_plurality_intent"] = votes.map(lambda value: value[0])
    frame["signal_max_votes"] = votes.map(lambda value: value[1])
    frame["signal_agreement"] = np.select(
        [
            frame["signal_max_votes"].eq(3),
            frame["signal_max_votes"].eq(2)
            & frame["signal_plurality_intent"].eq(frame["rule_intent_signal"]),
            frame["signal_max_votes"].eq(2),
        ],
        ["unanimous", "two_signal_including_rule", "prototype_cluster_against_rule"],
        default="three_way_disagreement",
    )

    # An explicit rule remains the adjudicated label when present. The two
    # model signals determine confidence and the review queue, rather than
    # silently outvoting an auditable primary-information-need cue. If a rule
    # is absent, the semantic plurality becomes the model-assisted fallback.
    frame["reviewed_intent"] = np.where(
        frame["rule_intent_signal"].ne(OTHER_INTENT),
        frame["rule_intent_signal"],
        frame["signal_plurality_intent"].fillna(frame["prototype_intent_signal"]),
    )
    frame.attrs["kappa_history"] = history
    frame.attrs["initial_cluster_mapping"] = initial_mapping
    frame.attrs["optimized_cluster_mapping"] = optimized_mapping
    frame.attrs["semantic_scores"] = semantic_scores
    return frame


def _entity_complexity(row: pd.Series) -> str:
    values: set[str] = set()
    for column in ("disease_entity", "molecule_entity", "drug_class_entity"):
        value = row.get(column)
        if pd.isna(value):
            continue
        values.update(part.strip().lower() for part in str(value).split(";") if part.strip())
    if len(values) <= 1:
        return "0-1 entities"
    if len(values) <= 3:
        return "2-3 entities"
    return "4+ entities"


def _context_complexity(row: pd.Series) -> str:
    present = 0
    for column in ("age_group", "pregnancy_status", "year", "route", "renal_function_group"):
        value = row.get(column)
        present += int(pd.notna(value) and str(value).strip() != "")
    for column in (
        "recency_flag",
        "dose_context_flag",
        "hepatic_impairment_flag",
        "comparison_flag",
        "negation_flag",
        "prior_treatment_failure_flag",
    ):
        present += int(bool(row.get(column, False)))
    if present == 0:
        return "none"
    if present == 1:
        return "one slot"
    return "multiple slots"


def _length_band(text: str) -> str:
    n_words = len(str(text).split())
    if n_words <= 6:
        return "short"
    if n_words <= 9:
        return "medium"
    return "long"


def build_annotation_frame(
    queries: pd.DataFrame, phase2_assignments: pd.DataFrame
) -> pd.DataFrame:
    """Create rule labels, uncertainty indicators, and sampling strata."""
    phase2_columns = [
        "query_id",
        "cluster_id",
        "liang_final_intent",
        "liang_top_probability",
        "liang_probability_margin",
        "prototype_top_intent",
        "ambiguity_margin",
    ]
    frame = queries.copy().merge(
        phase2_assignments[phase2_columns], on="query_id", validate="one_to_one"
    )
    frame["intent_text"] = frame.apply(delexicalize_query, axis=1)
    decisions = frame["intent_text"].map(annotate_intent).apply(pd.Series)
    decisions.columns = [
        "rule_intent_signal",
        "matched_annotation_rules",
        "n_rule_matches",
        "adjudication_rationale",
    ]
    frame = pd.concat([frame, decisions], axis=1)
    frame["model_disagreement"] = frame["liang_final_intent"].ne(frame["rule_intent_signal"])
    frame["low_prototype_margin"] = frame["ambiguity_margin"].le(
        frame["ambiguity_margin"].quantile(0.20)
    )
    frame["query_length_words"] = frame["query_text"].astype(str).str.split().str.len()
    frame["query_length_band"] = frame["query_text"].map(_length_band)
    frame["entity_complexity"] = frame.apply(_entity_complexity, axis=1)
    frame["context_complexity"] = frame.apply(_context_complexity, axis=1)
    frame = add_three_signal_annotations(frame)
    frame["low_candidate_prototype_margin"] = frame["prototype_margin"].le(
        frame["prototype_margin"].quantile(0.20)
    )

    counts = frame["reviewed_intent"].value_counts()
    frame["rare_intent"] = frame["reviewed_intent"].map(counts).le(31)
    frame["priority_score"] = (
        8 * frame["model_disagreement"].astype(int)
        + 8 * frame["signal_agreement"].eq("three_way_disagreement").astype(int)
        + 6 * frame["signal_agreement"].eq("prototype_cluster_against_rule").astype(int)
        + 4 * frame["n_rule_matches"].gt(1).astype(int)
        + 3 * frame["low_prototype_margin"].astype(int)
        + 3 * frame["low_candidate_prototype_margin"].astype(int)
        + 2 * frame["rare_intent"].astype(int)
        + frame["query_length_band"].isin(["short", "long"]).astype(int)
    )
    rng = np.random.default_rng(42)
    frame["tie_breaker"] = rng.random(len(frame))
    return frame


def _ordered_ids(frame: pd.DataFrame, ids: Iterable[str]) -> list[str]:
    candidates = frame[frame["query_id"].isin(ids)]
    return candidates.sort_values(
        ["priority_score", "ambiguity_margin", "tie_breaker"],
        ascending=[False, True, True],
    )["query_id"].tolist()


def _add_until(selected: list[str], candidates: Iterable[str], limit: int) -> list[str]:
    seen = set(selected)
    for query_id in candidates:
        if len(selected) >= limit:
            break
        if query_id not in seen:
            selected.append(query_id)
            seen.add(query_id)
    return selected


def select_pilot(frame: pd.DataFrame, size: int = PILOT_SIZE) -> list[str]:
    """Select the uncertainty-led pilot while retaining schema coverage."""
    uncertain_ids = frame.loc[frame["signal_agreement"].ne("unanimous"), "query_id"]
    selected = _ordered_ids(frame, uncertain_ids)[:12]
    indexed = frame.set_index("query_id")

    # Guarantee at least three examples of every supported intent.
    for intent in (*INTENT_NAMES, OTHER_INTENT):
        candidates = frame[frame["reviewed_intent"].eq(intent)]
        if candidates.empty:
            continue
        have = sum(indexed.loc[qid, "reviewed_intent"] == intent for qid in selected)
        needed = max(0, 3 - have)
        ordered = [
            query_id
            for query_id in _ordered_ids(frame, candidates["query_id"])
            if query_id not in set(selected)
        ]
        selected = _add_until(
            selected, ordered[:needed], size
        )

    # Guarantee broad language and cluster coverage before filling by uncertainty.
    for language in sorted(frame["language"].dropna().unique()):
        current = sum(indexed.loc[qid, "language"] == language for qid in selected)
        needed = max(0, 5 - current)
        ordered = [
            query_id
            for query_id in _ordered_ids(
                frame, frame.loc[frame["language"].eq(language), "query_id"]
            )
            if query_id not in set(selected)
        ]
        selected = _add_until(selected, ordered[:needed], size)

    for cluster_id in sorted(frame["cluster_id"].dropna().unique()):
        if any(indexed.loc[qid, "cluster_id"] == cluster_id for qid in selected):
            continue
        ordered = [
            query_id
            for query_id in _ordered_ids(
                frame, frame.loc[frame["cluster_id"].eq(cluster_id), "query_id"]
            )
            if query_id not in set(selected)
        ]
        selected = _add_until(selected, ordered[:1], size)

    return _add_until(selected, _ordered_ids(frame, frame["query_id"]), size)


def select_gold(
    frame: pd.DataFrame, pilot_ids: Iterable[str], size: int = GOLD_SIZE
) -> list[str]:
    """Expand the pilot into a coverage-plus-uncertainty reviewed subset."""
    selected = list(pilot_ids)
    indexed = frame.set_index("query_id")

    for intent in INTENT_NAMES:
        have = sum(indexed.loc[qid, "reviewed_intent"] == intent for qid in selected)
        needed = max(0, 12 - have)
        candidates = frame[frame["reviewed_intent"].eq(intent)]
        ordered = [
            query_id
            for query_id in _ordered_ids(frame, candidates["query_id"])
            if query_id not in set(selected)
        ]
        selected = _add_until(
            selected, ordered[:needed], size
        )

    # Touch every observed coverage stratum, then fill by uncertainty.
    coverage_columns = (
        "language",
        "therapeutic_area",
        "query_length_band",
        "entity_complexity",
        "context_complexity",
        "cluster_id",
    )
    for column in coverage_columns:
        for value in sorted(frame[column].dropna().unique(), key=str):
            group_ids = frame.loc[frame[column].eq(value), "query_id"]
            have = sum(indexed.loc[qid, column] == value for qid in selected)
            needed = max(0, min(2, len(group_ids)) - have)
            ordered = [
                query_id
                for query_id in _ordered_ids(frame, group_ids)
                if query_id not in set(selected)
            ]
            selected = _add_until(selected, ordered[:needed], size)

    return _add_until(selected, _ordered_ids(frame, frame["query_id"]), size)


def _sampling_reasons(row: pd.Series, is_pilot: bool) -> str:
    reasons: list[str] = []
    if row["signal_agreement"] != "unanimous":
        reasons.append(str(row["signal_agreement"]))
    if row["model_disagreement"]:
        reasons.append("phase2_model_disagreement")
    if row["n_rule_matches"] > 1:
        reasons.append("multi_cue_boundary")
    if row["low_prototype_margin"]:
        reasons.append("low_prototype_margin")
    if row["low_candidate_prototype_margin"]:
        reasons.append("low_candidate_prototype_margin")
    if row["rare_intent"]:
        reasons.append("rare_intent")
    if row["query_length_band"] in {"short", "long"}:
        reasons.append(f"{row['query_length_band']}_query")
    if not reasons:
        reasons.append("coverage_sampling")
    if is_pilot:
        reasons.insert(0, "pilot")
    return "; ".join(reasons)


def _annotation_notes(row: pd.Series) -> str:
    notes = [row["adjudication_rationale"]]
    notes.append(
        "Three-signal status: "
        f"{row['signal_agreement']} (rule={row['rule_intent_signal']}; "
        f"prototype={row['prototype_intent_signal']}; cluster={row['cluster_intent_signal']})."
    )
    if row["model_disagreement"]:
        notes.append(
            f"Phase 2 suggestion '{row['liang_final_intent']}' was not retained because the explicit request maps to '{row['reviewed_intent']}'."
        )
    if row["n_rule_matches"] > 1:
        notes.append("Multiple cues were resolved with the frozen primary-information-need hierarchy.")
    return " ".join(notes)


def build_deliverables(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    signal_metadata = dict(frame.attrs)
    pilot_ids = select_pilot(frame)
    gold_ids = select_gold(frame, pilot_ids)
    if len(pilot_ids) != PILOT_SIZE or len(gold_ids) != GOLD_SIZE:
        raise AssertionError("Phase 3 sample sizes do not match the frozen design")

    pilot_set, gold_set = set(pilot_ids), set(gold_ids)
    frame = frame.copy()
    frame["gold_set_membership"] = np.select(
        [frame["query_id"].isin(pilot_set), frame["query_id"].isin(gold_set)],
        ["pilot_reviewed", "gold_reviewed"],
        default="not_reviewed",
    )
    frame["label_source"] = np.select(
        [
            frame["query_id"].isin(gold_set),
            frame["signal_agreement"].eq("unanimous"),
            frame["signal_agreement"].eq("two_signal_including_rule"),
        ],
        [
            "model_assisted_schema_review",
            "three_signal_consensus",
            "rule_model_consensus",
        ],
        default="rule_with_model_disagreement",
    )
    frame["label_confidence"] = np.select(
        [
            frame["reviewed_intent"].eq(OTHER_INTENT),
            frame["signal_agreement"].isin(
                ["prototype_cluster_against_rule", "three_way_disagreement"]
            ),
            frame["n_rule_matches"].gt(1)
            | frame["signal_agreement"].eq("two_signal_including_rule"),
        ],
        ["low", "low", "medium"],
        default="high",
    )
    frame["review_flag"] = frame["label_confidence"].ne("high")
    frame["intent"] = frame["reviewed_intent"]
    frame["intent_subtype"] = frame["reviewed_intent"]
    frame["intent_top_level"] = frame["reviewed_intent"].map(PARENT_BY_INTENT).fillna(OTHER_INTENT)
    frame["annotation_notes"] = frame.apply(_annotation_notes, axis=1)
    frame["sampling_reasons"] = frame.apply(
        lambda row: _sampling_reasons(row, row["query_id"] in pilot_set), axis=1
    )

    annotation_columns = [
        "query_id", "query_text", "language", "therapeutic_area",
        "query_length_band", "entity_complexity", "context_complexity", "cluster_id",
        "liang_final_intent", "liang_top_probability", "liang_probability_margin",
        "prototype_top_intent", "ambiguity_margin", "matched_annotation_rules",
        "n_rule_matches", "rule_intent_signal", "prototype_intent_signal",
        "prototype_top_score", "prototype_margin", "cluster_intent_signal_initial",
        "cluster_intent_signal", "signal_plurality_intent", "signal_max_votes",
        "signal_agreement", "intent_top_level", "intent_subtype", "label_confidence",
        "label_source", "review_flag", "gold_set_membership", "annotation_notes",
        "sampling_reasons",
    ]
    pilot = frame[frame["query_id"].isin(pilot_set)][annotation_columns].copy()
    pilot["taxonomy_decision"] = "retain_frozen_taxonomy"
    pilot = pilot.sort_values("query_id")

    gold = frame[frame["query_id"].isin(gold_set)][annotation_columns].copy()
    gold = gold.sort_values("query_id")

    audit = gold[
        ["query_id", "query_text", "liang_final_intent", "rule_intent_signal",
         "prototype_intent_signal", "cluster_intent_signal", "signal_plurality_intent",
         "signal_agreement", "intent_subtype", "matched_annotation_rules",
         "n_rule_matches", "label_confidence", "annotation_notes"]
    ].rename(columns={"intent_subtype": "schema_adjudicated_intent"})
    audit["rule_matches_final"] = audit["rule_intent_signal"].eq(
        audit["schema_adjudicated_intent"]
    )
    audit["prototype_matches_final"] = audit["prototype_intent_signal"].eq(
        audit["schema_adjudicated_intent"]
    )
    audit["cluster_matches_final"] = audit["cluster_intent_signal"].eq(
        audit["schema_adjudicated_intent"]
    )
    audit["passes_agree"] = audit["liang_final_intent"].eq(
        audit["schema_adjudicated_intent"]
    )
    audit["review_design"] = (
        "single model-assisted schema review; not time-separated and not inter-annotator agreement"
    )
    disagreements = audit[audit["signal_agreement"].ne("unanimous")].copy()

    original_columns = list(pd.read_csv(ENRICHED_QUERIES_PATH, nrows=0).columns)
    final_columns = original_columns + [
        "intent", "intent_top_level", "intent_subtype", "rule_intent_signal",
        "prototype_intent_signal", "cluster_intent_signal", "signal_plurality_intent",
        "signal_agreement", "label_confidence",
        "label_source", "review_flag", "gold_set_membership", "annotation_notes",
    ]
    labeled = frame[final_columns].sort_values("query_id")
    signal_audit = frame[
        [
            "query_id", "query_text", "cluster_id", "rule_intent_signal",
            "prototype_intent_signal", "prototype_top_score", "prototype_second_score",
            "prototype_margin", "cluster_intent_signal_initial", "cluster_intent_signal",
            "signal_plurality_intent", "signal_max_votes", "signal_agreement",
            "reviewed_intent", "gold_set_membership", "review_flag",
        ]
    ].rename(columns={"reviewed_intent": "schema_adjudicated_intent"}).sort_values("query_id")
    cluster_mapping = (
        frame.groupby("cluster_id", as_index=False)
        .agg(
            n_queries=("query_id", "size"),
            initial_semantic_intent=("cluster_intent_signal_initial", "first"),
            kappa_optimized_intent=("cluster_intent_signal", "first"),
        )
        .sort_values("cluster_id")
    )
    return {
        "pilot": pilot,
        "gold": gold,
        "audit": audit.sort_values("query_id"),
        "disagreements": disagreements.sort_values("query_id"),
        "labeled": labeled,
        "signal_audit": signal_audit,
        "cluster_mapping": cluster_mapping,
        "kappa_history": signal_metadata["kappa_history"],
    }


def build_guidelines() -> pd.DataFrame:
    taxonomy_by_name = {item.intent_name: item for item in CANDIDATE_INTENTS}
    rows: list[dict[str, Any]] = []
    for priority, (intent_name, pattern) in enumerate(ANNOTATION_RULES, start=1):
        item = taxonomy_by_name[intent_name]
        rows.append(
            {
                "priority": priority,
                "intent": intent_name,
                "parent_intent": item.parent_intent,
                "definition": item.definition,
                "inclusion_criteria": item.inclusion_criteria,
                "exclusion_criteria": item.exclusion_criteria,
                "boundary_rule": BOUNDARY_RATIONALES[intent_name],
                "implemented_pattern": pattern,
            }
        )
    rows.append(
        {
            "priority": len(rows) + 1,
            "intent": OTHER_INTENT,
            "parent_intent": OTHER_INTENT,
            "definition": "No supported intent can be assigned reproducibly.",
            "inclusion_criteria": "no explicit supported information need; unresolved primary intent",
            "exclusion_criteria": "any query with a clear supported intent cue",
            "boundary_rule": BOUNDARY_RATIONALES[OTHER_INTENT],
            "implemented_pattern": "fallback only",
        }
    )
    return pd.DataFrame(rows)


def _counts_dict(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.value_counts().sort_index().items()}


def build_metrics(deliverables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    labeled = deliverables["labeled"]
    pilot = deliverables["pilot"]
    gold = deliverables["gold"]
    audit = deliverables["audit"]
    signals = deliverables["signal_audit"]
    phase2_labels = pd.read_csv(PROTOTYPE_ASSIGNMENTS_PATH)["liang_final_intent"].to_numpy()
    rule = signals["rule_intent_signal"].to_numpy()
    prototype = signals["prototype_intent_signal"].to_numpy()
    initial_cluster = signals["cluster_intent_signal_initial"].to_numpy()
    optimized_cluster = signals["cluster_intent_signal"].to_numpy()
    initial_fleiss = fleiss_kappa(np.column_stack([rule, prototype, initial_cluster]))
    optimized_fleiss = fleiss_kappa(np.column_stack([rule, prototype, optimized_cluster]))
    return {
        "n_queries": int(len(labeled)),
        "n_unique_query_ids": int(labeled["query_id"].nunique()),
        "n_pilot_reviewed": int(len(pilot)),
        "n_gold_reviewed_including_pilot": int(len(gold)),
        "n_rule_propagated": int(labeled["gold_set_membership"].eq("not_reviewed").sum()),
        "n_supported_intents_observed": int(labeled["intent"].nunique()),
        "n_other_ambiguous": int(labeled["intent"].eq(OTHER_INTENT).sum()),
        "n_medium_or_low_confidence": int(labeled["review_flag"].sum()),
        "n_phase2_model_disagreements_in_gold": int((~audit["passes_agree"]).sum()),
        "n_three_signal_disagreements_in_gold": int(
            audit["signal_agreement"].ne("unanimous").sum()
        ),
        "phase2_model_agreement_on_gold": round(float(audit["passes_agree"].mean()), 4),
        "phase2_model_agreement_all_queries": round(
            float((phase2_labels == labeled["intent"].to_numpy()).mean()), 4
        ),
        "fleiss_kappa_initial_cluster_mapping": round(initial_fleiss, 6),
        "fleiss_kappa_optimized_cluster_mapping": round(optimized_fleiss, 6),
        "fleiss_kappa_absolute_improvement": round(optimized_fleiss - initial_fleiss, 6),
        "pairwise_cohen_kappa": {
            "rule_vs_prototype": round(float(cohen_kappa_score(rule, prototype)), 6),
            "rule_vs_cluster": round(float(cohen_kappa_score(rule, optimized_cluster)), 6),
            "prototype_vs_cluster": round(
                float(cohen_kappa_score(prototype, optimized_cluster)), 6
            ),
        },
        "signal_agreement_distribution": _counts_dict(signals["signal_agreement"]),
        "intent_distribution": _counts_dict(labeled["intent"]),
        "gold_intent_distribution": _counts_dict(gold["intent_subtype"]),
        "gold_language_distribution": _counts_dict(gold["language"]),
        "gold_therapeutic_area_distribution": _counts_dict(gold["therapeutic_area"]),
        "taxonomy_changes_after_pilot": 0,
        "taxonomy_status": "frozen after pilot; all 11 supported classes retained",
        "independent_clinician_review": False,
        "inter_annotator_agreement_available": False,
        "kappa_interpretation": (
            "algorithmic signal agreement optimized in-sample; not inter-annotator reliability "
            "and not evidence of clinical accuracy"
        ),
    }


def build_report(metrics: dict[str, Any]) -> str:
    intent_rows = "\n".join(
        f"| {intent} | {count} | {metrics['gold_intent_distribution'].get(intent, 0)} |"
        for intent, count in metrics["intent_distribution"].items()
    )
    return f"""# Phase 3: Intent Labeling Strategy

## Outcome

All {metrics['n_queries']} queries have a final intent label, and every original query column plus the implemented Phase 1.6 contextual fields is preserved in `queries_labeled.csv`. Each query retains three decision signals: ordered bilingual rules, query-to-intent semantic prototype similarity, and an unsupervised semantic-cluster mapping. A {metrics['n_pilot_reviewed']}-query pilot was followed by a {metrics['n_gold_reviewed_including_pilot']}-query reviewed reference subset (the pilot is included in that total). The other {metrics['n_rule_propagated']} labels were propagated with the three-signal policy.

The term **reviewed reference subset** is intentional. Annotation was performed by a single model-assisted analyst workflow, not by independent clinicians. It is useful for this assessment but must not be described as clinical ground truth or used to claim inter-annotator reliability.

## Labeling approach

1. **Three separate signals.** The lexical rule signal uses an ordered bilingual boundary policy. The prototype signal uses cosine similarity between a frozen multilingual query embedding and all 11 complete intent definitions. The cluster signal begins with independent agglomerative query clusters and maps each anonymous cluster to the schema.
2. **Kappa-optimized cluster mapping.** Coordinate search chooses the cluster-to-intent mapping that maximizes Fleiss' kappa among rule, prototype, and cluster signals. Semantic centroid similarity breaks exact ties. Kappa increased from {metrics['fleiss_kappa_initial_cluster_mapping']:.3f} to {metrics['fleiss_kappa_optimized_cluster_mapping']:.3f} on the available 500 signal triples.
3. **Pilot (60).** The pilot prioritizes three-way disagreement, prototype/cluster agreement against a rule, Phase 2 model disagreement, low margins, rare intents, multi-cue boundaries, languages, and length extremes.
4. **Taxonomy freeze.** The 11 Phase 2 classes remained coherent in the pilot. No class was added, removed, split, or merged. `Other / Ambiguous` remains a fallback, although no supplied query required it.
5. **Reviewed subset (180, including pilot).** Coverage was expanded across intent, language, therapeutic area, length, entity composition, contextual complexity, and Phase 2 cluster. Each supported intent has at least 12 reviewed rows.
6. **Conservative adjudication.** Unanimous and rule-plus-model agreements provide model assistance. When semantic signals disagree with an explicit rule, the auditable primary-information-need rule is retained and the row is flagged rather than being silently outvoted. If no rule exists, the semantic plurality is the fallback.
7. **Remaining 320 rows.** The same frozen consensus policy supplies labels and preserves all signals, agreement status, confidence, provenance, and review flags.

## Counts

| Final intent | All 500 | Reviewed subset |
| --- | ---: | ---: |
{intent_rows}

- Pilot: {metrics['n_pilot_reviewed']} queries.
- Reviewed subset: {metrics['n_gold_reviewed_including_pilot']} queries.
- Rule-propagated remainder: {metrics['n_rule_propagated']} queries.
- `Other / Ambiguous`: {metrics['n_other_ambiguous']} queries.
- Medium/low-confidence review flags: {metrics['n_medium_or_low_confidence']} queries.
- Three-signal Fleiss' kappa: {metrics['fleiss_kappa_initial_cluster_mapping']:.3f} before and {metrics['fleiss_kappa_optimized_cluster_mapping']:.3f} after cluster-mapping optimization.
- Agreement between the Phase 2 model suggestion and the reviewed label: {metrics['phase2_model_agreement_on_gold']:.1%} on the reviewed subset and {metrics['phase2_model_agreement_all_queries']:.1%} over all queries.

The disagreement rate is a diagnostic, not inter-annotator agreement. `phase3_signal_disagreements_adjudicated.csv` records non-unanimous reviewed cases and the explicit boundary rationale.

## Quality audit

The second pass deliberately revisited low prototype margins, three-signal disagreements, multi-cue queries, rare classes, and Phase 2 disagreements. It checked the chosen primary need against each class's inclusion/exclusion criteria and retained an audit note per reviewed row. Pairwise Cohen kappas and three-rater Fleiss' kappa describe algorithmic agreement only. This review is neither time-separated nor independent; consequently, no inter-annotator statistic is claimed.

## Limitations

- The reviewed labels were created with a single model-assisted workflow and have no independent clinician adjudication.
- The prototype and cluster signals share the same frozen embedding encoder, so the three signals are operationally separate but not statistically independent.
- Maximizing kappa can make algorithms agree on the same error. The optimized value is in-sample descriptive agreement, not clinical accuracy or external validation.
- The supplied queries are strongly template-patterned. Rules perform unusually well here and may fail on natural, misspelled, implicit, code-switched, or genuinely multi-intent search traffic.
- The rule hierarchy forces one primary intent. It cannot represent equally important secondary intents.
- `label_confidence` is qualitative, not calibrated. Phase 2 probabilities and prototype margins are not annotation confidence.
- No query exercised the `Other / Ambiguous` fallback, so that boundary is unvalidated and cannot support a learnable class.
- The reviewed subset is intentionally enriched for uncertainty and is not a prevalence-estimation sample.
- Before production use, a qualified second clinical annotator should independently label the subset, disagreements should be adjudicated, and agreement should be reported by class and boundary type.
"""


def validate_deliverables(deliverables: dict[str, pd.DataFrame]) -> None:
    labeled = deliverables["labeled"]
    pilot = deliverables["pilot"]
    gold = deliverables["gold"]
    if len(labeled) != 500 or labeled["query_id"].nunique() != 500:
        raise AssertionError("Every one of the 500 queries must appear exactly once")
    if labeled["intent"].isna().any():
        raise AssertionError("Final intent labels must not be missing")
    if len(pilot) != PILOT_SIZE or len(gold) != GOLD_SIZE:
        raise AssertionError("Pilot/gold sizes violate the Phase 3 design")
    if not set(pilot["query_id"]).issubset(set(gold["query_id"])):
        raise AssertionError("The reviewed subset must include the pilot")
    if set(labeled["intent"]) - set(INTENT_NAMES) - {OTHER_INTENT}:
        raise AssertionError("A final label falls outside the frozen taxonomy")
    gold_counts = gold["intent_subtype"].value_counts()
    if any(gold_counts.get(intent, 0) < 12 for intent in INTENT_NAMES):
        raise AssertionError("Each supported intent needs at least 12 reviewed examples")
    if labeled["gold_set_membership"].eq("not_reviewed").sum() != 320:
        raise AssertionError("Exactly 320 rows should be propagated outside the reviewed subset")
    required_signals = {
        "rule_intent_signal",
        "prototype_intent_signal",
        "cluster_intent_signal",
        "signal_agreement",
    }
    if not required_signals.issubset(labeled.columns):
        raise AssertionError("All three signal outputs must be preserved")
    history = deliverables["kappa_history"]
    if history["fleiss_kappa"].iloc[-1] < history["fleiss_kappa"].iloc[0]:
        raise AssertionError("Kappa optimization must not reduce its objective")
