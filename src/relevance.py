"""Phase 6 query-content behavioral table construction.

The canonical analytical unit is one served query-content pair within a
session. Impressions define the row universe; behavioral signals are left
joined so absence of engagement is retained without implying irrelevance.
Phase 7, rather than this module, assigns behavior-derived relevance grades.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import OUTPUT_DIR, PROCESSED_DATA_DIR
from src.data import load_all_raw
from src.intent import LABELED_QUERIES_PATH


PHASE6_DIR = OUTPUT_DIR / "relevance"
BEHAVIORAL_TABLE_PATH = PROCESSED_DATA_DIR / "query_content_behavioral.csv"
EVENT_SUMMARY_PATH = PHASE6_DIR / "phase6_behavioral_event_summary.csv"
METRICS_PATH = PHASE6_DIR / "phase6_behavioral_table_metrics.json"
REPORT_PATH = PHASE6_DIR / "phase6_behavioral_table_report.md"

UNIT_KEYS = ["query_id", "content_id", "session_id"]
EVENT_TYPES = ("click", "scroll_deep", "return_visit", "save_bookmark")

QUERY_COLUMN_MAP = {
    "query_text": "query_text",
    "language": "query_language",
    "disease_entity": "query_disease",
    "icd10_code": "query_icd10_code",
    "molecule_entity": "query_molecule",
    "atc_code": "query_atc_code",
    "drug_class_entity": "query_drug_class",
    "atc_class": "query_atc_class",
    "therapeutic_area": "query_therapeutic_area",
    "age_group": "query_age_group",
    "pregnancy_status": "query_pregnancy_status",
    "year": "query_year",
    "recency_flag": "query_recency_flag",
    "dose_context_flag": "query_dose_context_flag",
    "route": "query_route",
    "renal_function_group": "query_renal_function_group",
    "hepatic_impairment_flag": "query_hepatic_impairment_flag",
    "comparison_flag": "query_comparison_flag",
    "negation_flag": "query_negation_flag",
    "prior_treatment_failure_flag": "query_prior_treatment_failure_flag",
    "intent": "query_intent",
    "intent_top_level": "query_intent_top_level",
    "intent_subtype": "query_intent_subtype",
    "label_confidence": "query_intent_label_confidence",
    "label_source": "query_intent_label_source",
}

CONTENT_COLUMN_MAP = {
    "title": "content_title",
    "content_type": "content_type",
    "source_type": "content_source_type",
    "language": "content_language",
    "publication_year": "content_publication_year",
    "word_count": "content_word_count",
    "disease_entity": "content_disease",
    "icd10_code": "content_icd10_code",
    "molecule_entity": "content_molecule",
    "atc_code": "content_atc_code",
    "drug_class_entity": "content_drug_class",
    "atc_class": "content_atc_class",
    "therapeutic_area": "content_therapeutic_area",
}


def _require_columns(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def _require_unique(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    if frame.duplicated(columns).any():
        examples = frame.loc[frame.duplicated(columns, keep=False), columns].head(5)
        raise ValueError(
            f"{name} must be unique on {columns}; examples: "
            f"{examples.to_dict(orient='records')}"
        )


def _validate_inputs(
    queries: pd.DataFrame,
    content: pd.DataFrame,
    impressions: pd.DataFrame,
    signals: pd.DataFrame,
) -> dict[str, int]:
    """Validate join keys and return diagnostics that precede aggregation."""
    _require_columns(queries, ["query_id", *QUERY_COLUMN_MAP], "queries")
    _require_columns(content, ["content_id", *CONTENT_COLUMN_MAP], "content")
    _require_columns(
        impressions,
        ["impression_id", *UNIT_KEYS, "doctor_id", "timestamp_served"],
        "impressions",
    )
    _require_columns(
        signals,
        [
            "signal_id",
            *UNIT_KEYS,
            "doctor_id",
            "event_type",
            "event_timestamp",
            "dwell_seconds",
        ],
        "behavioral_signals",
    )
    _require_unique(queries, ["query_id"], "queries")
    _require_unique(content, ["content_id"], "content")
    _require_unique(impressions, ["impression_id"], "impressions")
    _require_unique(signals, ["signal_id"], "behavioral_signals")

    unknown_events = sorted(set(signals["event_type"].dropna()) - set(EVENT_TYPES))
    if unknown_events:
        raise ValueError(f"Unsupported behavioral event types: {unknown_events}")
    if (signals["dwell_seconds"] < 0).any():
        raise ValueError("dwell_seconds cannot be negative")

    orphan_impression_queries = int((~impressions["query_id"].isin(queries["query_id"])).sum())
    orphan_impression_content = int((~impressions["content_id"].isin(content["content_id"])).sum())
    if orphan_impression_queries or orphan_impression_content:
        raise ValueError("Every impression must resolve to a query and content record")

    impression_units = (
        impressions.groupby(UNIT_KEYS, as_index=False)
        .agg(
            doctor_id=("doctor_id", "first"),
            timestamp_served=("timestamp_served", "min"),
        )
    )
    signal_links = signals.merge(
        impression_units,
        on=UNIT_KEYS,
        how="left",
        suffixes=("_signal", "_impression"),
        indicator=True,
    )
    orphan_signals = int(signal_links["_merge"].eq("left_only").sum())
    if orphan_signals:
        raise ValueError("Every behavioral signal must resolve to an impression unit")
    doctor_mismatches = int(
        signal_links["doctor_id_signal"].ne(signal_links["doctor_id_impression"]).sum()
    )
    if doctor_mismatches:
        raise ValueError("Behavior and impression doctor_id values disagree")
    negative_event_latency = int(
        (signal_links["event_timestamp"] < signal_links["timestamp_served"]).sum()
    )
    if negative_event_latency:
        raise ValueError("Behavioral events cannot precede the matching impression")

    inconsistent_unit_doctors = int(
        (impressions.groupby(UNIT_KEYS)["doctor_id"].nunique() > 1).sum()
    )
    if inconsistent_unit_doctors:
        raise ValueError("An analytical unit cannot contain multiple doctor IDs")

    return {
        "orphan_impression_queries": orphan_impression_queries,
        "orphan_impression_content": orphan_impression_content,
        "orphan_behavioral_signals": orphan_signals,
        "doctor_id_mismatches": doctor_mismatches,
        "negative_event_latency": negative_event_latency,
        "duplicate_impression_units_collapsed": int(impressions.duplicated(UNIT_KEYS).sum()),
    }


def _aggregate_impressions(impressions: pd.DataFrame) -> pd.DataFrame:
    ordered = impressions.sort_values([*UNIT_KEYS, "timestamp_served", "impression_id"])
    units = (
        ordered.groupby(UNIT_KEYS, as_index=False, sort=False)
        .agg(
            impression_id=("impression_id", "first"),
            doctor_id=("doctor_id", "first"),
            timestamp=("timestamp_served", "min"),
            last_timestamp_served=("timestamp_served", "max"),
            impression_count=("impression_id", "nunique"),
        )
    )
    units["inferred_rank"] = (
        units.sort_values(["session_id", "query_id", "timestamp", "impression_id"])
        .groupby(["session_id", "query_id"])
        .cumcount()
        .add(1)
        .sort_index()
        .astype("int16")
    )
    units["impressed"] = True
    return units


def _aggregate_behavior(signals: pd.DataFrame) -> pd.DataFrame:
    if signals.empty:
        return pd.DataFrame(
            columns=[
                *UNIT_KEYS,
                "behavioral_event_count",
                "first_event_timestamp",
                "last_event_timestamp",
                "dwell_time",
                "max_event_dwell_seconds",
                "clicked",
                "scroll_deep",
                "return_visit",
                "save_bookmark",
            ]
        )

    working = signals.copy()
    for event_type in EVENT_TYPES:
        working[event_type] = working["event_type"].eq(event_type)
    return (
        working.groupby(UNIT_KEYS, as_index=False, sort=False)
        .agg(
            behavioral_event_count=("signal_id", "nunique"),
            first_event_timestamp=("event_timestamp", "min"),
            last_event_timestamp=("event_timestamp", "max"),
            dwell_time=("dwell_seconds", "sum"),
            max_event_dwell_seconds=("dwell_seconds", "max"),
            click=("click", "max"),
            scroll_deep=("scroll_deep", "max"),
            return_visit=("return_visit", "max"),
            save_bookmark=("save_bookmark", "max"),
        )
        .rename(columns={"click": "clicked"})
    )


def build_behavioral_table(
    queries: pd.DataFrame,
    content: pd.DataFrame,
    impressions: pd.DataFrame,
    signals: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build and validate the one-row-per-impression-unit analytical table."""
    diagnostics = _validate_inputs(queries, content, impressions, signals)
    impression_units = _aggregate_impressions(impressions)
    behavior = _aggregate_behavior(signals)

    query_view = queries[["query_id", *QUERY_COLUMN_MAP]].rename(columns=QUERY_COLUMN_MAP)
    content_view = content[["content_id", *CONTENT_COLUMN_MAP]].rename(
        columns=CONTENT_COLUMN_MAP
    )
    table = (
        impression_units.merge(behavior, on=UNIT_KEYS, how="left", validate="one_to_one")
        .merge(query_view, on="query_id", how="left", validate="many_to_one")
        .merge(content_view, on="content_id", how="left", validate="many_to_one")
    )

    integer_zero_columns = ["behavioral_event_count", "dwell_time", "max_event_dwell_seconds"]
    flag_columns = ["clicked", "scroll_deep", "return_visit", "save_bookmark"]
    for column in integer_zero_columns:
        table[column] = table[column].fillna(0).astype("int64")
    for column in flag_columns:
        table[column] = table[column].eq(True)
    table["has_engagement"] = table[flag_columns].any(axis=1)

    preferred_order = [
        "query_id", "content_id", "session_id", "impression_id", "doctor_id",
        "timestamp", "last_timestamp_served", "inferred_rank", "impression_count",
        "impressed", "query_text", "query_language", "query_intent",
        "query_intent_top_level", "query_intent_subtype",
        "query_intent_label_confidence", "query_intent_label_source",
        "query_disease", "query_icd10_code", "query_molecule", "query_atc_code",
        "query_drug_class", "query_atc_class", "query_therapeutic_area",
        "query_age_group", "query_pregnancy_status", "query_year",
        "query_recency_flag", "query_dose_context_flag", "query_route",
        "query_renal_function_group", "query_hepatic_impairment_flag",
        "query_comparison_flag", "query_negation_flag",
        "query_prior_treatment_failure_flag", "content_title", "content_language",
        "content_type", "content_source_type", "content_publication_year",
        "content_word_count", "content_disease", "content_icd10_code",
        "content_molecule", "content_atc_code", "content_drug_class",
        "content_atc_class", "content_therapeutic_area", "behavioral_event_count",
        "first_event_timestamp", "last_event_timestamp", "clicked", "scroll_deep",
        "return_visit", "save_bookmark", "dwell_time", "max_event_dwell_seconds",
        "has_engagement",
    ]
    table = table[preferred_order].sort_values(
        ["timestamp", "session_id", "inferred_rank", "content_id"]
    ).reset_index(drop=True)

    _require_unique(table, UNIT_KEYS, "behavioral table")
    if len(table) != impressions[UNIT_KEYS].drop_duplicates().shape[0]:
        raise AssertionError("The behavioral table did not preserve every impression unit")
    if not table["impressed"].all():
        raise AssertionError("The Phase 6 row universe must consist only of impressions")
    if table["query_intent"].isna().any():
        raise AssertionError("Every row must inherit a query intent")
    if table["content_title"].isna().any():
        raise AssertionError("Every row must inherit content metadata")

    engaged = int(table["has_engagement"].sum())
    diagnostics.update(
        {
            "source_rows": {
                "queries": int(len(queries)),
                "content": int(len(content)),
                "impressions": int(len(impressions)),
                "behavioral_signals": int(len(signals)),
            },
            "analytical_rows": int(len(table)),
            "unique_analytical_units": int(table[UNIT_KEYS].drop_duplicates().shape[0]),
            "queries_represented": int(table["query_id"].nunique()),
            "content_represented": int(table["content_id"].nunique()),
            "sessions_represented": int(table["session_id"].nunique()),
            "doctors_represented": int(table["doctor_id"].nunique()),
            "engaged_rows": engaged,
            "unengaged_rows": int(len(table) - engaged),
            "engagement_rate": float(engaged / len(table)) if len(table) else 0.0,
            "behavioral_events_linked": int(table["behavioral_event_count"].sum()),
            "event_flag_counts": {
                event: int(table["clicked" if event == "click" else event].sum())
                for event in EVENT_TYPES
            },
            "dwell_seconds_total": int(table["dwell_time"].sum()),
            "dwell_seconds_median_engaged": (
                float(table.loc[table["has_engagement"], "dwell_time"].median())
                if engaged else 0.0
            ),
            "relevance_labels_assigned": False,
        }
    )
    return table, diagnostics


def build_event_summary(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for event_type in EVENT_TYPES:
        column = "clicked" if event_type == "click" else event_type
        mask = table[column]
        dwell = table.loc[mask, "dwell_time"]
        rows.append(
            {
                "event_type": event_type,
                "analytical_rows": int(mask.sum()),
                "share_of_all_rows": float(mask.mean()),
                "median_dwell_seconds": float(dwell.median()) if len(dwell) else 0.0,
                "mean_dwell_seconds": float(dwell.mean()) if len(dwell) else 0.0,
                "max_dwell_seconds": int(dwell.max()) if len(dwell) else 0,
            }
        )
    rows.append(
        {
            "event_type": "no_observed_engagement",
            "analytical_rows": int((~table["has_engagement"]).sum()),
            "share_of_all_rows": float((~table["has_engagement"]).mean()),
            "median_dwell_seconds": 0.0,
            "mean_dwell_seconds": 0.0,
            "max_dwell_seconds": 0,
        }
    )
    return pd.DataFrame(rows)


def _markdown_table(frame: pd.DataFrame) -> str:
    headers = [str(column) for column in frame.columns]
    body = [[str(value) for value in row] for row in frame.to_numpy()]
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(row) + " |" for row in body),
        ]
    )


def build_report(metrics: dict[str, Any], event_summary: pd.DataFrame) -> str:
    return "\n".join(
        [
            "# Phase 6: Query-Content Behavioral Table", "", "## Result", "",
            f"The impression-defined table contains {metrics['analytical_rows']:,} unique "
            "`(query_id, content_id, session_id)` rows. All behavioral signals resolve to "
            "one of these rows, and every impression unit is retained.", "",
            f"- Engaged rows: {metrics['engaged_rows']:,} ({metrics['engagement_rate']:.1%})",
            f"- Rows with no observed engagement: {metrics['unengaged_rows']:,}",
            f"- Linked behavioral events: {metrics['behavioral_events_linked']:,}",
            f"- Queries / content / sessions: {metrics['queries_represented']:,} / "
            f"{metrics['content_represented']:,} / {metrics['sessions_represented']:,}", "",
            "## Event Coverage", "", _markdown_table(event_summary.round(3)), "",
            "## Join and Aggregation Contract", "",
            "- Impressions define the row universe; signals use a left join.",
            "- Query attributes come from the Phase 3 labeled query file, including Phase 1.6 slots.",
            "- Content attributes come from the supplied content file.",
            "- Event flags indicate whether an event type occurred; `dwell_time` sums event dwell seconds within the analytical unit.",
            "- `inferred_rank` is deterministic serving order within a session-query and is not a supplied rank field.",
            "- The builder validates foreign keys, doctor consistency, nonnegative dwell, and event-after-impression timing.", "",
            "## Interpretation Boundary", "",
            "Phase 6 assigns no relevance label. A row with no click or downstream event means only "
            "that no engagement was observed. It can reflect non-examination, position bias, competing "
            "results, or answer satisfaction and must not automatically be treated as irrelevant. Phase 7 "
            "will define graded relevance from these behavior features.", "",
            "## Known Schema Limits", "",
            "- Exact age, eGFR, and disease severity are absent because Phase 1.6 did not extract them; the table includes age group and renal-function group instead.",
            "- Query intent is a Phase 3 model-assisted weak label, not independent clinician annotation.",
            "- The raw data has no explicit position field, so only inferred serving order is available for later bias analysis.", "",
            "## Artifacts", "",
            f"- Behavioral table: `{BEHAVIORAL_TABLE_PATH}`",
            f"- Metrics: `{METRICS_PATH}`",
            f"- Event summary: `{EVENT_SUMMARY_PATH}`", "",
        ]
    )


def build_phase6_artifacts() -> dict[str, Path]:
    """Load project data, build Phase 6 outputs, and persist diagnostics."""
    raw = load_all_raw()
    labeled_queries = pd.read_csv(LABELED_QUERIES_PATH)
    table, metrics = build_behavioral_table(
        queries=labeled_queries,
        content=raw["content"],
        impressions=raw["impressions"],
        signals=raw["behavioral_signals"],
    )
    event_summary = build_event_summary(table)

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PHASE6_DIR.mkdir(parents=True, exist_ok=True)
    table.to_csv(BEHAVIORAL_TABLE_PATH, index=False)
    event_summary.to_csv(EVENT_SUMMARY_PATH, index=False)
    METRICS_PATH.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    REPORT_PATH.write_text(build_report(metrics, event_summary), encoding="utf-8")
    return {
        "behavioral_table": BEHAVIORAL_TABLE_PATH,
        "event_summary": EVENT_SUMMARY_PATH,
        "metrics": METRICS_PATH,
        "report": REPORT_PATH,
    }


if __name__ == "__main__":
    for artifact, path in build_phase6_artifacts().items():
        print(f"{artifact}: {path}")
