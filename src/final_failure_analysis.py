"""Phase 14: interpretable review of residual errors in the final ranker.

The review targets the frozen Phase 12 runtime configuration on temporal test
queries.  It does not change rankings, labels, or weights.  Authored semantic
assessments live in ``data/processed/phase14_failure_reviews.csv`` so rerunning
this module rebuilds the evidence tables and report without making an LLM call.

Run with ``.venv/bin/python -m src.final_failure_analysis``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import CONTENT_PATH, EXPERIMENT_LOG_PATH, OUTPUT_DIR, PROJECT_ROOT
from src.evaluation_split import SPLIT_DIR
from src.intent import INTENT_METADATA_QUERIES_PATH


PHASE12_DIR = OUTPUT_DIR / "retrieval" / "phase12"
PHASE14_DIR = OUTPUT_DIR / "retrieval" / "phase14"
REVIEWS_PATH = PROJECT_ROOT / "data" / "processed" / "phase14_failure_reviews.csv"
FINAL_CONFIGURATION = "with_predicted_hard_intent"
CASE_IDS = (
    "Q019", "Q051", "Q061", "Q066", "Q101", "Q129",
    "Q146", "Q180", "Q224", "Q393", "Q409", "Q435",
)
ALLOWED_CATEGORIES = {
    "apparent_metric_false_failure", "comparison_intent_mismatch",
    "content_type_mismatch", "context_template_over_entity",
    "corpus_coverage_gap", "demographic_constraint_underrepresented",
    "entity_underweighted", "intent_template_mismatch",
    "low_confidence_intent_error", "monitoring_intent_mismatch",
    "multi_entity_conjunction_failure", "prior_failure_underrepresented",
    "proxy_sensitive_intent_effect", "weak_behavioral_ground_truth",
    "wrong_molecule",
}
SLOT_COLUMNS = (
    "age_group", "pregnancy_status", "year", "recency_flag",
    "dose_context_flag", "route", "renal_function_group",
    "hepatic_impairment_flag", "comparison_flag", "negation_flag",
    "prior_treatment_failure_flag",
)


def select_residual_cases(metrics: pd.DataFrame, reviews: pd.DataFrame) -> pd.DataFrame:
    """Validate the fixed, authored sample against frozen test-set misses."""
    if tuple(reviews["query_id"]) != CASE_IDS:
        raise ValueError("Phase 14 reviews must use the frozen case order")
    if reviews["query_id"].duplicated().any():
        raise ValueError("Phase 14 review query IDs must be unique")
    selected = metrics[
        metrics["protocol"].eq("temporal")
        & metrics["split"].eq("test")
        & metrics["configuration"].eq(FINAL_CONFIGURATION)
        & metrics["scheme"].eq("relevance_grade")
        & metrics["threshold"].eq(1)
        & metrics["query_id"].isin(CASE_IDS)
    ].copy()
    if set(selected["query_id"]) != set(CASE_IDS):
        raise ValueError("Every frozen Phase 14 case must occur in temporal test metrics")
    if not selected["eligible"].all() or not selected["recall@10"].eq(0).all():
        raise ValueError("Every Phase 14 case must be an eligible top-10 proxy miss")
    return reviews.merge(selected, on="query_id", validate="one_to_one")


def _decomposition(row: pd.Series) -> dict[str, Any]:
    fields = (
        "disease_entity", "molecule_entity", "drug_class_entity",
        "predicted_intent", *SLOT_COLUMNS,
    )
    result: dict[str, Any] = {}
    for field in fields:
        value = row[field]
        if pd.isna(value) or value == "" or value is False:
            continue
        if hasattr(value, "item"):
            value = value.item()
        result[field] = value
    return result


def _rank_text(rows: pd.DataFrame) -> str:
    return " | ".join(
        f"#{int(row['rank'])} {row['content_id']}: {row['title']}"
        for _, row in rows.sort_values("rank").iterrows()
    )


def _update_experiment_log(cases: pd.DataFrame) -> None:
    log = pd.read_csv(EXPERIMENT_LOG_PATH)
    proxy = int(cases["assessment_status"].str.contains("proxy_label").sum())
    addition = {
        "experiment": "R-FAIL-FINAL",
        "hypothesis": "remaining final-ranker errors have interpretable and distinct causes",
        "method": "12-case authored review of frozen Phase 12 predicted-intent temporal-test misses",
        "primary_metric": "qualitative failure evidence",
        "result": f"12 reviewed proxy misses; {proxy} explicitly expose proxy-label failure",
        "decision": "use for diagnosis only; prioritize adjudication, conjunction-aware scoring, and corpus coverage",
    }
    log = log[~log["experiment"].eq(addition["experiment"])]
    pd.concat([log, pd.DataFrame([addition])], ignore_index=True).to_csv(
        EXPERIMENT_LOG_PATH, index=False
    )


def build_phase14_artifacts(output_dir: Path = PHASE14_DIR) -> dict[str, str]:
    """Build case, evidence, coverage, report, and provenance artifacts."""
    source_paths = [
        PHASE12_DIR / "per_query_metrics.csv.gz",
        PHASE12_DIR / "rankings.csv.gz",
        PHASE12_DIR / "intent_predictions.csv",
        SPLIT_DIR / "temporal_test_judgments.csv",
        INTENT_METADATA_QUERIES_PATH,
        CONTENT_PATH,
        REVIEWS_PATH,
    ]
    metrics = pd.read_csv(source_paths[0])
    rankings = pd.read_csv(source_paths[1])
    predictions = pd.read_csv(source_paths[2])
    judgments = pd.read_csv(source_paths[3])
    queries = pd.read_csv(source_paths[4])
    content = pd.read_csv(source_paths[5])
    reviews = pd.read_csv(source_paths[6]).fillna("")
    cases = select_residual_cases(metrics, reviews)

    categories = set(
        cases["failure_categories"].str.split(";").explode().loc[lambda x: x.ne("")]
    )
    unknown = categories - ALLOWED_CATEGORIES
    if unknown:
        raise ValueError(f"Unknown Phase 14 categories: {sorted(unknown)}")

    cases = cases.merge(queries, on="query_id", validate="one_to_one")
    cases = cases.merge(predictions, on="query_id", validate="one_to_one")
    final_rankings = rankings[rankings["configuration"].eq(FINAL_CONFIGURATION)].copy()
    assisted_rankings = rankings[rankings["configuration"].eq("with_assisted_intent")]
    docs = content.set_index("content_id")
    test_judgments = judgments.set_index(["query_id", "content_id"])

    records: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    report = [
        "# Phase 14: detailed residual failure analysis", "",
        "This is a purposive review of 12 eligible temporal-test top-10 misses from the frozen "
        "Phase 12 runtime ranker (`with_predicted_hard_intent`). Cases cover compositional, "
        "contextual, intent, corpus-coverage, and evaluation-proxy failures; their frequencies "
        "are not prevalence estimates. Titles and supplied metadata are available, not article "
        "bodies. Codex authored the semantic assessments; no clinician adjudication occurred. "
        "Unjudged means unobserved in the behavior logs, not irrelevant. No model or label was changed.", "",
    ]

    for _, row in cases.iterrows():
        qid = row["query_id"]
        ranked = final_rankings[final_rankings["query_id"].eq(qid)].sort_values("rank")
        top3 = ranked.head(3).merge(content, on="content_id", validate="many_to_one")
        candidate_id = row["expected_candidate_id"]
        candidate = ranked[ranked["content_id"].eq(candidate_id)]
        candidate_rank = int(candidate.iloc[0]["rank"]) if not candidate.empty else None
        positive = judgments[
            judgments["query_id"].eq(qid) & judgments["relevance_grade"].gt(0)
        ].sort_values(["relevance_grade", "content_id"], ascending=[False, True])
        strongest_id = positive.iloc[0]["content_id"]
        strongest_grade = int(positive.iloc[0]["relevance_grade"])
        strongest_rank_row = ranked[ranked["content_id"].eq(strongest_id)]
        strongest_rank = int(strongest_rank_row.iloc[0]["rank"]) if not strongest_rank_row.empty else None
        assisted_positive = assisted_rankings[
            assisted_rankings["query_id"].eq(qid)
            & assisted_rankings["content_id"].eq(strongest_id)
        ]
        assisted_positive_rank = (
            int(assisted_positive.iloc[0]["rank"]) if not assisted_positive.empty else None
        )
        positive_ids = set(positive["content_id"])
        assisted_top_positive = assisted_rankings[
            assisted_rankings["query_id"].eq(qid)
            & assisted_rankings["content_id"].isin(positive_ids)
        ].sort_values("rank")
        assisted_top_positive_id = (
            assisted_top_positive.iloc[0]["content_id"] if not assisted_top_positive.empty else None
        )
        assisted_top_positive_rank = (
            int(assisted_top_positive.iloc[0]["rank"]) if not assisted_top_positive.empty else None
        )
        final_assisted_positive = ranked[ranked["content_id"].eq(assisted_top_positive_id)]
        assisted_top_positive_final_rank = (
            int(final_assisted_positive.iloc[0]["rank"])
            if not final_assisted_positive.empty else None
        )
        decomposition = _decomposition(row)
        record = {
            "query_id": qid,
            "query": row["query_text"],
            "language": row["language"],
            "expected_relevant_content": row["expected_relevant_content"],
            "expected_candidate_id": candidate_id,
            "expected_candidate_rank": candidate_rank,
            "retrieved_content": _rank_text(top3),
            "query_decomposition": json.dumps(decomposition, ensure_ascii=False, sort_keys=True),
            "assisted_intent": row["assisted_intent"],
            "predicted_intent": row["predicted_intent"],
            "predicted_probability": row["predicted_probability"],
            "probability_margin": row["probability_margin"],
            "why_retrieval_failed": row["why_retrieval_failed"],
            "what_could_improve_it": row["what_could_improve_it"],
            "failure_categories": row["failure_categories"],
            "assessment_status": row["assessment_status"],
            "proxy_positive_id": strongest_id,
            "proxy_positive_grade": strongest_grade,
            "proxy_positive_final_rank": strongest_rank,
            "proxy_positive_assisted_rank": assisted_positive_rank,
            "assisted_top_positive_id": assisted_top_positive_id,
            "assisted_top_positive_rank": assisted_top_positive_rank,
            "assisted_top_positive_final_rank": assisted_top_positive_final_rank,
            "reviewer": row["reviewer"],
        }
        records.append(record)

        roles = [(item, "retrieved_top_3") for item in top3["content_id"]]
        roles += [(candidate_id, "expected_title_candidate"), (strongest_id, "strongest_observed_positive")]
        if assisted_top_positive_id:
            roles.append((assisted_top_positive_id, "assisted_intent_top_positive"))
        seen: set[tuple[str, str]] = set()
        for content_id, role in roles:
            if (content_id, role) in seen:
                continue
            seen.add((content_id, role))
            rank_row = ranked[ranked["content_id"].eq(content_id)]
            rank = int(rank_row.iloc[0]["rank"]) if not rank_row.empty else None
            key = (qid, content_id)
            grade = int(test_judgments.loc[key, "relevance_grade"]) if key in test_judgments.index else "unjudged"
            evidence.append({
                "query_id": qid, "role": role, "content_id": content_id,
                "rank": rank, "grade": grade, **docs.loc[content_id].fillna("").to_dict(),
            })

        report += [
            f"## {qid}: {row['query_text']}", "",
            f"**Expected relevant content:** {row['expected_relevant_content']}", "",
            f"**Retrieved content:** {record['retrieved_content']}", "",
            f"**Query decomposition:** `{record['query_decomposition']}`", "",
            f"**Why retrieval failed:** {row['why_retrieval_failed']}", "",
            f"**What could improve it:** {row['what_could_improve_it']}", "",
            f"**Evidence status:** {row['assessment_status']}. The strongest observed behavioral "
            f"positive is {strongest_id} (grade {strongest_grade}; final rank "
            f"{strongest_rank if strongest_rank is not None else '>20'}).", "",
        ]

    case_frame = pd.DataFrame(records)
    evidence_frame = pd.DataFrame(evidence)
    category_counts = case_frame["failure_categories"].str.split(";").explode().value_counts()
    coverage = pd.DataFrame(
        {
            "category": sorted(ALLOWED_CATEGORIES),
            "reviewed_query_count": [int(category_counts.get(c, 0)) for c in sorted(ALLOWED_CATEGORIES)],
        }
    )
    coverage["interpretation"] = "purposive-case count; not prevalence"

    output_dir.mkdir(parents=True, exist_ok=True)
    case_frame.to_csv(output_dir / "failure_cases.csv", index=False)
    evidence_frame.to_csv(output_dir / "failure_evidence.csv", index=False)
    coverage.to_csv(output_dir / "category_coverage.csv", index=False)
    (output_dir / "failure_cases.md").write_text("\n".join(report).rstrip() + "\n")
    manifest = {
        "phase": 14,
        "configuration": FINAL_CONFIGURATION,
        "protocol": "temporal",
        "split": "test",
        "target": "relevance_grade >= 1",
        "case_ids": list(CASE_IDS),
        "selection": "purposive authored sample of frozen final-ranker eligible top-10 proxy misses",
        "reviewer": "Codex title/metadata review; not clinician adjudication",
        "mutations": "none to rankings, labels, weights, or test judgments",
        "limitations": [
            "purposive examples are not prevalence estimates",
            "article body text unavailable",
            "behavior-derived positives are not clinical gold",
            "test set had been inspected in earlier phases",
            "single LLM reviewer without clinician agreement measurement",
        ],
        "sha256": {
            str(path.relative_to(PROJECT_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [*source_paths, Path(__file__)]
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    _update_experiment_log(case_frame)
    return {
        "cases": str(output_dir / "failure_cases.csv"),
        "evidence": str(output_dir / "failure_evidence.csv"),
        "coverage": str(output_dir / "category_coverage.csv"),
        "report": str(output_dir / "failure_cases.md"),
        "manifest": str(output_dir / "manifest.json"),
    }


if __name__ == "__main__":
    print(json.dumps(build_phase14_artifacts(), indent=2))
