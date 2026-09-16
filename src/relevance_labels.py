"""Phase 7 behavior-derived weak relevance labels.

The labels describe evidence observed after an impression; they are not clinical
ground truth. The session-level table preserves every exposed result. A second
query-content table uses the maximum observed grade across sessions because an
absence of engagement is not reliable evidence against a positive interaction.
Unexposed query-content pairs are deliberately absent and remain unjudged.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

from src.config import CACHE_DIR, CONFIG, FIGURES_DIR, OUTPUT_DIR, PROCESSED_DATA_DIR

os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.relevance import BEHAVIORAL_TABLE_PATH, UNIT_KEYS


PHASE7_DIR = OUTPUT_DIR / "relevance"
LABELED_EXPOSURES_PATH = PROCESSED_DATA_DIR / "query_content_relevance.csv"
JUDGMENTS_PATH = PHASE7_DIR / "phase7_query_content_judgments.csv"
LABEL_DISTRIBUTION_PATH = PHASE7_DIR / "phase7_label_distribution.csv"
QUERY_COVERAGE_PATH = PHASE7_DIR / "phase7_query_coverage.csv"
SCHEME_TRANSITIONS_PATH = PHASE7_DIR / "phase7_scheme_transitions.csv"
METRICS_PATH = PHASE7_DIR / "phase7_relevance_metrics.json"
REPORT_PATH = PHASE7_DIR / "phase7_relevance_report.md"
FIGURE_PATH = FIGURES_DIR / "phase7_behavioral_relevance.png"

GRADE_DESCRIPTIONS = {
    0: "exposed without observed engagement",
    1: "weak engagement",
    2: "meaningful engagement",
    3: "strong positive engagement",
}


@dataclass(frozen=True)
class RelevanceScheme:
    """Thresholds for a transparent, monotonic relevance-grade rule."""

    name: str
    click_meaningful_seconds: int
    scroll_strong_seconds: int


_PHASE7_CONFIG_FIELDS = (
    "min_dwell_seconds_for_positive",
    "min_scroll_seconds_for_strong_positive",
    "conservative_min_dwell_seconds_for_positive",
    "conservative_min_scroll_seconds_for_strong_positive",
)
_CONFIG_HAS_PHASE7_THRESHOLDS = all(
    hasattr(CONFIG, field) for field in _PHASE7_CONFIG_FIELDS
)

# A notebook may still hold the pre-Phase-7 CONFIG instance after config.py has
# changed on disk. Fall back as one complete set so the old 30-second value is
# not accidentally mixed with the new primary thresholds.
if _CONFIG_HAS_PHASE7_THRESHOLDS:
    _PRIMARY_CLICK_SECONDS = CONFIG.min_dwell_seconds_for_positive
    _PRIMARY_SCROLL_SECONDS = CONFIG.min_scroll_seconds_for_strong_positive
    _CONSERVATIVE_CLICK_SECONDS = CONFIG.conservative_min_dwell_seconds_for_positive
    _CONSERVATIVE_SCROLL_SECONDS = (
        CONFIG.conservative_min_scroll_seconds_for_strong_positive
    )
else:
    _PRIMARY_CLICK_SECONDS = 10
    _PRIMARY_SCROLL_SECONDS = 150
    _CONSERVATIVE_CLICK_SECONDS = 30
    _CONSERVATIVE_SCROLL_SECONDS = 180

PRIMARY_SCHEME = RelevanceScheme(
    name="primary_median_dwell",
    click_meaningful_seconds=_PRIMARY_CLICK_SECONDS,
    scroll_strong_seconds=_PRIMARY_SCROLL_SECONDS,
)
CONSERVATIVE_SCHEME = RelevanceScheme(
    name="conservative_dwell",
    click_meaningful_seconds=_CONSERVATIVE_CLICK_SECONDS,
    scroll_strong_seconds=_CONSERVATIVE_SCROLL_SECONDS,
)

REQUIRED_COLUMNS = [
    *UNIT_KEYS,
    "timestamp",
    "inferred_rank",
    "clicked",
    "scroll_deep",
    "return_visit",
    "save_bookmark",
    "dwell_time",
    "has_engagement",
    "query_text",
    "query_language",
    "query_intent",
    "content_title",
    "content_type",
    "content_language",
]


def _validate_behavioral_table(table: pd.DataFrame) -> None:
    missing = sorted(set(REQUIRED_COLUMNS) - set(table.columns))
    if missing:
        raise ValueError(f"Behavioral table is missing required columns: {missing}")
    if table.duplicated(UNIT_KEYS).any():
        raise ValueError(f"Behavioral table must be unique on {UNIT_KEYS}")
    if (table["dwell_time"] < 0).any():
        raise ValueError("dwell_time cannot be negative")

    event_columns = ["clicked", "scroll_deep", "return_visit", "save_bookmark"]
    event_count = table[event_columns].astype(bool).sum(axis=1)
    if event_count.gt(1).any():
        raise ValueError(
            "Phase 7 expects mutually exclusive terminal outcomes in the supplied logs"
        )
    if not event_count.eq(table["has_engagement"].astype(bool).astype(int)).all():
        raise ValueError("has_engagement must agree with the terminal event flags")


def _grade_for_scheme(table: pd.DataFrame, scheme: RelevanceScheme) -> np.ndarray:
    """Return grades ordered by the strongest observed signal first."""
    strong = (
        table["save_bookmark"].astype(bool)
        | table["return_visit"].astype(bool)
        | (
            table["scroll_deep"].astype(bool)
            & table["dwell_time"].ge(scheme.scroll_strong_seconds)
        )
    )
    meaningful = (
        table["scroll_deep"].astype(bool)
        | (
            table["clicked"].astype(bool)
            & table["dwell_time"].ge(scheme.click_meaningful_seconds)
        )
    )
    weak = table["clicked"].astype(bool)
    return np.select([strong, meaningful, weak], [3, 2, 1], default=0).astype("int8")


def _evidence_type(table: pd.DataFrame, scheme: RelevanceScheme) -> pd.Series:
    conditions = [
        table["save_bookmark"].astype(bool),
        table["return_visit"].astype(bool),
        table["scroll_deep"].astype(bool)
        & table["dwell_time"].ge(scheme.scroll_strong_seconds),
        table["scroll_deep"].astype(bool),
        table["clicked"].astype(bool)
        & table["dwell_time"].ge(scheme.click_meaningful_seconds),
        table["clicked"].astype(bool),
    ]
    choices = [
        "save_bookmark",
        "return_visit",
        "high_dwell_deep_scroll",
        "deep_scroll",
        "meaningful_dwell_click",
        "short_dwell_click",
    ]
    return pd.Series(
        np.select(conditions, choices, default="exposed_no_observed_engagement"),
        index=table.index,
        dtype="string",
    )


def assign_relevance_labels(table: pd.DataFrame) -> pd.DataFrame:
    """Attach primary and sensitivity weak labels to exposed session-level rows."""
    _validate_behavioral_table(table)
    labeled = table.copy()
    labeled["relevance_grade"] = _grade_for_scheme(labeled, PRIMARY_SCHEME)
    labeled["conservative_relevance_grade"] = _grade_for_scheme(
        labeled, CONSERVATIVE_SCHEME
    )
    labeled["event_hierarchy_relevance_grade"] = np.select(
        [
            labeled["save_bookmark"].astype(bool)
            | labeled["return_visit"].astype(bool),
            labeled["scroll_deep"].astype(bool),
            labeled["clicked"].astype(bool),
        ],
        [3, 2, 1],
        default=0,
    ).astype("int8")
    labeled["relevance_evidence"] = _evidence_type(labeled, PRIMARY_SCHEME)
    labeled["relevance_grade_description"] = labeled["relevance_grade"].map(
        GRADE_DESCRIPTIONS
    )
    labeled["observed_positive"] = labeled["relevance_grade"].gt(0)
    labeled["meaningful_positive"] = labeled["relevance_grade"].ge(2)
    labeled["strong_positive"] = labeled["relevance_grade"].eq(3)
    labeled["relevance_label_scheme"] = PRIMARY_SCHEME.name
    labeled["relevance_label_source"] = "behavioral_weak_supervision_v1"

    if not labeled["observed_positive"].eq(labeled["has_engagement"]).all():
        raise AssertionError("Every and only observed engagements must receive a positive grade")
    if not labeled.loc[~labeled["has_engagement"], "relevance_grade"].eq(0).all():
        raise AssertionError("Unengaged impressions must receive grade 0")
    return labeled


def aggregate_query_content_judgments(labeled: pd.DataFrame) -> pd.DataFrame:
    """Create exposed-only query-content judgments for later retrieval evaluation.

    Maximum grade is intentional: a positive action is affirmative evidence while
    a non-action may be caused by non-examination. Counts and a conflict flag keep
    repeated-session uncertainty visible.
    """
    required = {
        "relevance_grade",
        "conservative_relevance_grade",
        "event_hierarchy_relevance_grade",
    }
    missing = sorted(required - set(labeled.columns))
    if missing:
        raise ValueError(f"Labeled exposures are missing columns: {missing}")

    working = labeled.copy()
    working["positive_exposure"] = working["relevance_grade"].gt(0)
    working["meaningful_exposure"] = working["relevance_grade"].ge(2)
    working["strong_exposure"] = working["relevance_grade"].eq(3)
    working["unengaged_exposure"] = working["relevance_grade"].eq(0)

    first_columns = [
        "query_text",
        "query_language",
        "query_intent",
        "content_title",
        "content_type",
        "content_language",
    ]
    named_aggregations: dict[str, tuple[str, str]] = {
        column: (column, "first") for column in first_columns
    }
    named_aggregations.update(
        {
            "first_observed_at": ("timestamp", "min"),
            "last_observed_at": ("timestamp", "max"),
            "exposure_count": ("session_id", "size"),
            "observed_sessions": ("session_id", "nunique"),
            "relevance_grade": ("relevance_grade", "max"),
            "mean_exposure_grade": ("relevance_grade", "mean"),
            "conservative_relevance_grade": (
                "conservative_relevance_grade",
                "max",
            ),
            "event_hierarchy_relevance_grade": (
                "event_hierarchy_relevance_grade",
                "max",
            ),
            "positive_exposures": ("positive_exposure", "sum"),
            "meaningful_exposures": ("meaningful_exposure", "sum"),
            "strong_exposures": ("strong_exposure", "sum"),
            "unengaged_exposures": ("unengaged_exposure", "sum"),
            "distinct_observed_grades": ("relevance_grade", "nunique"),
        }
    )
    judgments = (
        working.sort_values("timestamp")
        .groupby(["query_id", "content_id"], as_index=False, sort=True)
        .agg(**named_aggregations)
    )
    judgments["conflicting_observations"] = judgments[
        "distinct_observed_grades"
    ].gt(1)
    judgments["observed_judgment"] = True
    judgments["judgment_scope"] = "exposed_only"
    judgments["aggregation_rule"] = "maximum_observed_grade"
    judgments["grade_zero_semantics"] = "exposed_without_observed_engagement"
    judgments["relevance_grade_description"] = judgments["relevance_grade"].map(
        GRADE_DESCRIPTIONS
    )
    return judgments.sort_values(
        ["query_id", "relevance_grade", "content_id"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def label_distribution(labeled: pd.DataFrame, judgments: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    specifications = [
        ("session_exposure", "primary_median_dwell", labeled, "relevance_grade"),
        ("session_exposure", "conservative_dwell", labeled, "conservative_relevance_grade"),
        ("session_exposure", "event_hierarchy", labeled, "event_hierarchy_relevance_grade"),
        ("query_content", "primary_median_dwell", judgments, "relevance_grade"),
        ("query_content", "conservative_dwell", judgments, "conservative_relevance_grade"),
        ("query_content", "event_hierarchy", judgments, "event_hierarchy_relevance_grade"),
    ]
    for grain, scheme, frame, column in specifications:
        counts = frame[column].value_counts().reindex(range(4), fill_value=0)
        for grade, count in counts.items():
            rows.append(
                {
                    "grain": grain,
                    "scheme": scheme,
                    "grade": int(grade),
                    "grade_description": GRADE_DESCRIPTIONS[int(grade)],
                    "rows": int(count),
                    "share": float(count / len(frame)) if len(frame) else 0.0,
                }
            )
    return pd.DataFrame(rows)


def query_coverage(judgments: pd.DataFrame) -> pd.DataFrame:
    coverage = (
        judgments.groupby("query_id", as_index=False)
        .agg(
            query_text=("query_text", "first"),
            query_language=("query_language", "first"),
            query_intent=("query_intent", "first"),
            observed_content=("content_id", "size"),
            positive_content=("relevance_grade", lambda values: int(values.gt(0).sum())),
            meaningful_content=("relevance_grade", lambda values: int(values.ge(2).sum())),
            strong_content=("relevance_grade", lambda values: int(values.eq(3).sum())),
        )
    )
    coverage["has_observed_positive"] = coverage["positive_content"].gt(0)
    coverage["has_meaningful_positive"] = coverage["meaningful_content"].gt(0)
    coverage["has_strong_positive"] = coverage["strong_content"].gt(0)
    coverage["eligible_for_positive_dependent_metrics"] = coverage[
        "has_observed_positive"
    ]
    return coverage.sort_values(
        ["has_observed_positive", "positive_content", "query_id"],
        ascending=[True, True, True],
    ).reset_index(drop=True)


def scheme_transitions(labeled: pd.DataFrame) -> pd.DataFrame:
    return (
        labeled.groupby(
            ["relevance_grade", "conservative_relevance_grade"], as_index=False
        )
        .agg(rows=("query_id", "size"))
        .assign(share=lambda frame: frame["rows"] / len(labeled))
        .rename(
            columns={
                "relevance_grade": "primary_grade",
                "conservative_relevance_grade": "conservative_grade",
            }
        )
        .sort_values(["primary_grade", "conservative_grade"])
        .reset_index(drop=True)
    )


def _markdown_table(frame: pd.DataFrame) -> str:
    headers = [str(column) for column in frame.columns]
    body = [
        [str(value) for value in row]
        for row in frame.itertuples(index=False, name=None)
    ]
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(row) + " |" for row in body),
        ]
    )


def _plot(distribution: pd.DataFrame, coverage: pd.DataFrame) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))

    exposure = distribution[
        distribution["grain"].eq("session_exposure") & distribution["grade"].gt(0)
    ]
    pivot = exposure.pivot(index="scheme", columns="grade", values="rows").reindex(
        ["primary_median_dwell", "conservative_dwell", "event_hierarchy"]
    )
    pivot.plot(
        kind="bar",
        stacked=True,
        ax=axes[0],
        color=["#9ECAE1", "#4292C6", "#08519C"],
    )
    axes[0].set(
        title="Strength among engaged exposures",
        xlabel="",
        ylabel="Engaged results",
    )
    axes[0].tick_params(axis="x", rotation=18)
    axes[0].legend(title="Grade", ncol=4, loc="upper center")
    axes[0].grid(axis="y", alpha=0.2)

    coverage_counts = pd.Series(
        {
            "Grade ≥1": int(coverage["has_observed_positive"].sum()),
            "Grade ≥2": int(coverage["has_meaningful_positive"].sum()),
            "Grade 3": int(coverage["has_strong_positive"].sum()),
            "No positive": int((~coverage["has_observed_positive"]).sum()),
        }
    )
    coverage_counts.plot(kind="bar", ax=axes[1], color=["#4292C6", "#2171B5", "#08519C", "#D9E2EC"])
    axes[1].set(
        title="Queries with observed positive evidence",
        xlabel="",
        ylabel="Queries",
    )
    axes[1].tick_params(axis="x", rotation=18)
    axes[1].grid(axis="y", alpha=0.2)

    fig.tight_layout()
    fig.savefig(FIGURE_PATH, dpi=180, bbox_inches="tight")
    plt.close(fig)


def build_report(
    metrics: dict[str, Any], distribution: pd.DataFrame, transitions: pd.DataFrame
) -> str:
    primary = distribution[
        distribution["grain"].eq("session_exposure")
        & distribution["scheme"].eq(PRIMARY_SCHEME.name)
    ][["grade", "grade_description", "rows", "share"]].copy()
    primary["share"] = primary["share"].map(lambda value: f"{value:.1%}")
    changed = metrics["session_rows_changed_under_conservative_scheme"]
    return "\n".join(
        [
            "# Phase 7: Behavior-Derived Relevance Labels",
            "",
            "## Frozen primary rule",
            "",
            f"The primary rule uses a {PRIMARY_SCHEME.click_meaningful_seconds}-second click threshold "
            f"and a {PRIMARY_SCHEME.scroll_strong_seconds}-second deep-scroll threshold. These round "
            "cutoffs approximate the observed click and deep-scroll medians (10.5s and 152s). "
            "Bookmark and return visit are strong positives regardless of dwell because they are "
            "rare, intentional terminal outcomes in the supplied log.",
            "",
            "- Grade 3: bookmark, return visit, or deep scroll with at least 150 seconds dwell.",
            "- Grade 2: other deep scroll, or click with at least 10 seconds dwell.",
            "- Grade 1: click with less than 10 seconds dwell.",
            "- Grade 0: exposed without observed engagement; this does not mean clinically irrelevant.",
            "",
            _markdown_table(primary),
            "",
            "## Coverage and aggregation",
            "",
            f"The labels cover all {metrics['session_exposure_rows']:,} exposed session-level rows and "
            f"{metrics['observed_query_content_pairs']:,} observed query-content pairs. "
            f"{metrics['queries_with_positive']:,} of {metrics['queries']:,} queries have at least one "
            f"positive judgment; {metrics['queries_without_positive']:,} do not and must be excluded or "
            "reported separately for positive-dependent retrieval metrics.",
            "",
            "For repeated query-content pairs, the retrieval judgment is the maximum observed grade. "
            "This treats an affirmative action as stronger evidence than non-action, while retaining "
            "exposure counts, mean grade, and a conflict flag. Unexposed pairs are absent and remain unjudged.",
            "",
            f"There are {metrics['conflicting_query_content_pairs']:,} repeated pairs with conflicting "
            "grades. They remain in the artifact with `conflicting_observations=True` for sensitivity analysis.",
            "",
            "## Sensitivity scheme",
            "",
            f"A conservative scheme raises the click cutoff to {CONSERVATIVE_SCHEME.click_meaningful_seconds}s "
            f"and the strong-scroll cutoff to {CONSERVATIVE_SCHEME.scroll_strong_seconds}s. It changes "
            f"{changed:,} session rows ({metrics['session_rows_changed_share']:.1%}) but never changes "
            "whether engagement was observed. An event-only hierarchy is also retained as a no-dwell "
            "reference. Later retrieval results should report the primary and conservative schemes.",
            "",
            _markdown_table(transitions.round(4)),
            "",
            "## Interpretation boundary",
            "",
            "These are weak, exposure-conditioned labels—not clinician relevance judgments. A zero can "
            "reflect non-examination, position bias, snippet satisfaction, competing relevant results, or "
            "session abandonment. Doctor ID, content popularity, inferred rank, session length, intent, "
            "language, and content type are not used in the grade rule. This avoids directly baking the "
            "largest measured propensity and exposure biases into the target, but it does not remove them.",
            "",
            "## Artifacts",
            "",
            f"- Session-level labeled exposures: `{LABELED_EXPOSURES_PATH}`",
            f"- Exposed-only query-content judgments: `{JUDGMENTS_PATH}`",
            f"- Query coverage: `{QUERY_COVERAGE_PATH}`",
            f"- Metrics: `{METRICS_PATH}`",
            "",
        ]
    )


def build_phase7_artifacts() -> dict[str, Path]:
    table = pd.read_csv(BEHAVIORAL_TABLE_PATH)
    labeled = assign_relevance_labels(table)
    judgments = aggregate_query_content_judgments(labeled)
    distribution = label_distribution(labeled, judgments)
    coverage = query_coverage(judgments)
    transitions = scheme_transitions(labeled)

    changed = labeled["relevance_grade"].ne(
        labeled["conservative_relevance_grade"]
    )
    metrics: dict[str, Any] = {
        "primary_scheme": {
            "name": PRIMARY_SCHEME.name,
            "click_meaningful_seconds": PRIMARY_SCHEME.click_meaningful_seconds,
            "scroll_strong_seconds": PRIMARY_SCHEME.scroll_strong_seconds,
            "grade_zero_semantics": "exposed_without_observed_engagement",
        },
        "conservative_scheme": {
            "name": CONSERVATIVE_SCHEME.name,
            "click_meaningful_seconds": CONSERVATIVE_SCHEME.click_meaningful_seconds,
            "scroll_strong_seconds": CONSERVATIVE_SCHEME.scroll_strong_seconds,
        },
        "session_exposure_rows": int(len(labeled)),
        "observed_query_content_pairs": int(len(judgments)),
        "unexposed_pairs_are_unjudged": True,
        "query_content_aggregation_rule": "maximum_observed_grade",
        "queries": int(len(coverage)),
        "queries_with_positive": int(coverage["has_observed_positive"].sum()),
        "queries_without_positive": int((~coverage["has_observed_positive"]).sum()),
        "queries_with_meaningful_positive": int(coverage["has_meaningful_positive"].sum()),
        "queries_with_strong_positive": int(coverage["has_strong_positive"].sum()),
        "conflicting_query_content_pairs": int(judgments["conflicting_observations"].sum()),
        "primary_session_grade_counts": {
            str(grade): int(count)
            for grade, count in labeled["relevance_grade"]
            .value_counts()
            .reindex(range(4), fill_value=0)
            .items()
        },
        "primary_pair_grade_counts": {
            str(grade): int(count)
            for grade, count in judgments["relevance_grade"]
            .value_counts()
            .reindex(range(4), fill_value=0)
            .items()
        },
        "session_rows_changed_under_conservative_scheme": int(changed.sum()),
        "session_rows_changed_share": float(changed.mean()),
        "all_engaged_rows_positive": bool(
            labeled["observed_positive"].eq(labeled["has_engagement"]).all()
        ),
        "label_rule_uses_propensity_or_exposure_features": False,
        "labels_are_clinical_ground_truth": False,
    }

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PHASE7_DIR.mkdir(parents=True, exist_ok=True)
    labeled.to_csv(LABELED_EXPOSURES_PATH, index=False)
    judgments.to_csv(JUDGMENTS_PATH, index=False)
    distribution.to_csv(LABEL_DISTRIBUTION_PATH, index=False)
    coverage.to_csv(QUERY_COVERAGE_PATH, index=False)
    transitions.to_csv(SCHEME_TRANSITIONS_PATH, index=False)
    METRICS_PATH.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    REPORT_PATH.write_text(build_report(metrics, distribution, transitions), encoding="utf-8")
    _plot(distribution, coverage)
    return {
        "labeled_exposures": LABELED_EXPOSURES_PATH,
        "query_content_judgments": JUDGMENTS_PATH,
        "label_distribution": LABEL_DISTRIBUTION_PATH,
        "query_coverage": QUERY_COVERAGE_PATH,
        "scheme_transitions": SCHEME_TRANSITIONS_PATH,
        "metrics": METRICS_PATH,
        "report": REPORT_PATH,
        "figure": FIGURE_PATH,
    }


if __name__ == "__main__":
    for artifact, path in build_phase7_artifacts().items():
        print(f"{artifact}: {path}")
