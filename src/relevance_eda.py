"""Descriptive EDA to inform, but not define, Phase 7 relevance labels."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.config import CACHE_DIR, FIGURES_DIR, OUTPUT_DIR

os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.relevance import BEHAVIORAL_TABLE_PATH, EVENT_TYPES, UNIT_KEYS


EDA_DIR = OUTPUT_DIR / "relevance" / "eda"
EDA_METRICS_PATH = EDA_DIR / "phase6_relevance_eda_metrics.json"
EDA_REPORT_PATH = EDA_DIR / "phase6_relevance_eda_report.md"
DWELL_DISTRIBUTION_PATH = EDA_DIR / "dwell_distribution_by_event.csv"
THRESHOLD_SENSITIVITY_PATH = EDA_DIR / "dwell_threshold_sensitivity.csv"
POSITION_PATH = EDA_DIR / "engagement_by_inferred_rank.csv"
SLICE_PATH = EDA_DIR / "engagement_slices.csv"
SESSION_PATH = EDA_DIR / "session_engagement_distribution.csv"
REPEATABILITY_PATH = EDA_DIR / "query_content_repeatability.csv"
COMPATIBILITY_PATH = EDA_DIR / "structured_compatibility_sanity_check.csv"
CANDIDATE_SCHEMES_PATH = EDA_DIR / "candidate_grade_sensitivity.csv"
EDA_FIGURE_PATH = FIGURES_DIR / "phase6_relevance_eda.png"

QUANTILES = (0.0, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 1.0)
EVENT_COLUMN = {
    "click": "clicked",
    "scroll_deep": "scroll_deep",
    "return_visit": "return_visit",
    "save_bookmark": "save_bookmark",
}


def load_behavioral_table() -> pd.DataFrame:
    table = pd.read_csv(
        BEHAVIORAL_TABLE_PATH,
        parse_dates=[
            "timestamp",
            "last_timestamp_served",
            "first_event_timestamp",
            "last_event_timestamp",
        ],
    )
    if table.duplicated(UNIT_KEYS).any():
        raise ValueError("Phase 6 behavioral table is not unique at its declared grain")
    return table


def wilson_interval(successes: int, observations: int, z: float = 1.96) -> tuple[float, float]:
    """Return a 95% Wilson interval for a binomial rate."""
    if observations == 0:
        return 0.0, 0.0
    rate = successes / observations
    denominator = 1 + z**2 / observations
    center = (rate + z**2 / (2 * observations)) / denominator
    half_width = (
        z
        * np.sqrt(rate * (1 - rate) / observations + z**2 / (4 * observations**2))
        / denominator
    )
    return float(center - half_width), float(center + half_width)


def dwell_distribution(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for event_type in EVENT_TYPES:
        dwell = table.loc[table[EVENT_COLUMN[event_type]], "dwell_time"]
        quantiles = dwell.quantile(QUANTILES)
        row: dict[str, Any] = {
            "event_type": event_type,
            "rows": int(len(dwell)),
            "zero_dwell_rows": int(dwell.eq(0).sum()),
            "mean_seconds": float(dwell.mean()),
        }
        row.update({f"p{int(q * 100):02d}": float(quantiles.loc[q]) for q in QUANTILES})
        rows.append(row)
    return pd.DataFrame(rows)


def dwell_threshold_sensitivity(table: pd.DataFrame) -> pd.DataFrame:
    """Show support retained at plausible, round dwell thresholds."""
    candidate_thresholds = {
        "click": (5, 10, 20, 30),
        "scroll_deep": (90, 120, 150, 180),
    }
    rows: list[dict[str, Any]] = []
    for event_type, thresholds in candidate_thresholds.items():
        dwell = table.loc[table[EVENT_COLUMN[event_type]], "dwell_time"]
        for threshold in thresholds:
            retained = int(dwell.ge(threshold).sum())
            rows.append(
                {
                    "event_type": event_type,
                    "threshold_seconds": threshold,
                    "below_threshold": int(dwell.lt(threshold).sum()),
                    "at_or_above_threshold": retained,
                    "share_at_or_above": float(retained / len(dwell)),
                }
            )
    return pd.DataFrame(rows)


def _rate_row(frame: pd.DataFrame, slice_type: str, slice_value: str) -> dict[str, Any]:
    observations = len(frame)
    engaged = int(frame["has_engagement"].sum())
    lower, upper = wilson_interval(engaged, observations)
    engaged_dwell = frame.loc[frame["has_engagement"], "dwell_time"]
    return {
        "slice_type": slice_type,
        "slice_value": slice_value,
        "impressions": observations,
        "engaged": engaged,
        "engagement_rate": float(engaged / observations) if observations else 0.0,
        "engagement_ci95_low": lower,
        "engagement_ci95_high": upper,
        "click_rate": float(frame["clicked"].mean()) if observations else 0.0,
        "scroll_deep_rate": float(frame["scroll_deep"].mean()) if observations else 0.0,
        "save_bookmark_rate": float(frame["save_bookmark"].mean()) if observations else 0.0,
        "return_visit_rate": float(frame["return_visit"].mean()) if observations else 0.0,
        "median_dwell_engaged": (
            float(engaged_dwell.median()) if len(engaged_dwell) else 0.0
        ),
    }


def engagement_by_position(table: pd.DataFrame) -> pd.DataFrame:
    rows = [
        _rate_row(group, "inferred_rank", str(int(rank)))
        for rank, group in table.groupby("inferred_rank", sort=True)
    ]
    result = pd.DataFrame(rows).rename(columns={"slice_value": "inferred_rank"})
    result["inferred_rank"] = result["inferred_rank"].astype(int)
    return result.drop(columns="slice_type")


def engagement_slices(table: pd.DataFrame) -> pd.DataFrame:
    working = table.copy()
    working["language_pair"] = (
        working["query_language"].astype(str) + " -> " + working["content_language"].astype(str)
    )
    rows: list[dict[str, Any]] = []
    for column in ("query_intent", "query_language", "content_type", "language_pair"):
        for value, group in working.groupby(column, dropna=False, sort=True):
            rows.append(_rate_row(group, column, str(value)))
    return pd.DataFrame(rows)


def session_engagement_distribution(table: pd.DataFrame) -> pd.DataFrame:
    sessions = (
        table.groupby("session_id", as_index=False)
        .agg(
            impressions=("content_id", "size"),
            engaged_results=("has_engagement", "sum"),
        )
    )
    return (
        sessions.groupby("engaged_results", as_index=False)
        .agg(sessions=("session_id", "size"), median_impressions=("impressions", "median"))
        .assign(share_of_sessions=lambda x: x["sessions"] / len(sessions))
    )


def query_content_repeatability(table: pd.DataFrame) -> pd.DataFrame:
    pairs = (
        table.groupby(["query_id", "content_id"], as_index=False)
        .agg(exposures=("session_id", "size"), engaged_exposures=("has_engagement", "sum"))
    )
    conditions = [
        pairs["exposures"].eq(1),
        pairs["engaged_exposures"].eq(0),
        pairs["engaged_exposures"].eq(pairs["exposures"]),
    ]
    choices = ["single_exposure", "repeated_never_engaged", "repeated_always_engaged"]
    pairs["repeatability"] = np.select(conditions, choices, default="repeated_mixed_engagement")
    return (
        pairs.groupby("repeatability", as_index=False)
        .agg(
            query_content_pairs=("query_id", "size"),
            total_exposures=("exposures", "sum"),
            total_engaged_exposures=("engaged_exposures", "sum"),
        )
        .assign(
            share_of_pairs=lambda x: x["query_content_pairs"] / len(pairs),
            engagement_rate=lambda x: x["total_engaged_exposures"] / x["total_exposures"],
        )
        .sort_values("repeatability")
        .reset_index(drop=True)
    )


def _normalized_values(value: Any) -> set[str]:
    if pd.isna(value):
        return set()
    return {part.strip().casefold() for part in str(value).split(";") if part.strip()}


def _overlap(left: pd.Series, right: pd.Series) -> pd.Series:
    return pd.Series(
        [bool(_normalized_values(a) & _normalized_values(b)) for a, b in zip(left, right)],
        index=left.index,
        dtype=bool,
    )


def structured_compatibility_sanity_check(table: pd.DataFrame) -> pd.DataFrame:
    """Check whether supplied exact matches align with behavior at all.

    This is construct-validity EDA only. Full structured feature design and
    relevance-independent matching belong to Phase 7.5.
    """
    dimensions = {
        "icd10_code": _overlap(table["query_icd10_code"], table["content_icd10_code"]),
        "atc_code": _overlap(table["query_atc_code"], table["content_atc_code"]),
        "atc_class": _overlap(table["query_atc_class"], table["content_atc_class"]),
        "therapeutic_area": _overlap(
            table["query_therapeutic_area"], table["content_therapeutic_area"]
        ),
        "language_exact": table["query_language"].eq(table["content_language"]),
    }
    rows: list[dict[str, Any]] = []
    for dimension, matches in dimensions.items():
        for matched in (False, True):
            subset = table[matches.eq(matched)]
            row = _rate_row(subset, dimension, str(matched).lower())
            row["matched"] = matched
            rows.append(row)
    return pd.DataFrame(rows).rename(columns={"slice_type": "dimension"}).drop(
        columns="slice_value"
    )


def candidate_grade_sensitivity(table: pd.DataFrame) -> pd.DataFrame:
    """Compare illustrative schemes without attaching grades to the Phase 6 table."""
    schemes: dict[str, tuple[str, np.ndarray]] = {
        "event_hierarchy": (
            "3=bookmark/return; 2=deep scroll; 1=click; 0=no observed engagement",
            np.select(
                [table["save_bookmark"] | table["return_visit"], table["scroll_deep"], table["clicked"]],
                [3, 2, 1],
                default=0,
            ),
        ),
        "median_dwell_split": (
            "3=bookmark/return or deep scroll >=150s; 2=other deep scroll or click >=10s; 1=other click; 0=no engagement",
            np.select(
                [
                    table["save_bookmark"] | table["return_visit"] | (table["scroll_deep"] & table["dwell_time"].ge(150)),
                    table["scroll_deep"] | (table["clicked"] & table["dwell_time"].ge(10)),
                    table["clicked"],
                ],
                [3, 2, 1],
                default=0,
            ),
        ),
        "conservative_dwell": (
            "3=bookmark/return or deep scroll >=180s; 2=other deep scroll or click >=30s; 1=other click; 0=no engagement",
            np.select(
                [
                    table["save_bookmark"] | table["return_visit"] | (table["scroll_deep"] & table["dwell_time"].ge(180)),
                    table["scroll_deep"] | (table["clicked"] & table["dwell_time"].ge(30)),
                    table["clicked"],
                ],
                [3, 2, 1],
                default=0,
            ),
        ),
    }
    rows: list[dict[str, Any]] = []
    for scheme, (definition, grades) in schemes.items():
        counts = pd.Series(grades).value_counts().reindex(range(4), fill_value=0)
        for grade, count in counts.items():
            rows.append(
                {
                    "scheme": scheme,
                    "definition": definition,
                    "grade": int(grade),
                    "rows": int(count),
                    "share_all_rows": float(count / len(table)),
                    "share_engaged_rows": float(count / table["has_engagement"].sum()) if grade else 0.0,
                }
            )
    return pd.DataFrame(rows)


def _plot_eda(
    table: pd.DataFrame,
    position: pd.DataFrame,
    schemes: pd.DataFrame,
) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))

    error = np.vstack(
        [
            position["engagement_rate"] - position["engagement_ci95_low"],
            position["engagement_ci95_high"] - position["engagement_rate"],
        ]
    )
    axes[0].errorbar(
        position["inferred_rank"], position["engagement_rate"], yerr=error,
        marker="o", capsize=3, color="#2463A6",
    )
    axes[0].set(title="Engagement by inferred rank", xlabel="Inferred rank", ylabel="Engagement rate")
    axes[0].set_ylim(0, max(0.32, float(position["engagement_ci95_high"].max() + 0.02)))
    axes[0].grid(alpha=0.2)

    dwell_groups = [
        table.loc[table[EVENT_COLUMN[event]], "dwell_time"].to_numpy()
        for event in EVENT_TYPES
    ]
    axes[1].boxplot(dwell_groups, tick_labels=EVENT_TYPES, showfliers=False)
    axes[1].tick_params(axis="x", rotation=25)
    axes[1].set(title="Dwell distributions by event", ylabel="Dwell seconds")
    axes[1].grid(axis="y", alpha=0.2)

    pivot = (
        schemes[schemes["grade"].gt(0)]
        .pivot(index="scheme", columns="grade", values="rows")
        .reindex(["event_hierarchy", "median_dwell_split", "conservative_dwell"])
    )
    pivot.plot(
        kind="bar",
        stacked=True,
        ax=axes[2],
        color=["#9ECAE1", "#4292C6", "#08519C"],
    )
    axes[2].set(
        title="Grades among engaged rows",
        xlabel="",
        ylabel="Engaged rows",
    )
    axes[2].tick_params(axis="x", rotation=20)
    axes[2].legend(title="Grade", ncol=4, loc="upper center")
    axes[2].grid(axis="y", alpha=0.2)

    fig.tight_layout()
    fig.savefig(EDA_FIGURE_PATH, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _markdown_table(frame: pd.DataFrame, max_rows: int = 30) -> str:
    view = frame.head(max_rows).copy()
    headers = [str(column) for column in view.columns]
    body = [[str(value) for value in row] for row in view.to_numpy()]
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(row) + " |" for row in body),
        ]
    )


def build_report(
    metrics: dict[str, Any],
    dwell: pd.DataFrame,
    thresholds: pd.DataFrame,
    position: pd.DataFrame,
    repeatability: pd.DataFrame,
    compatibility: pd.DataFrame,
    schemes: pd.DataFrame,
) -> str:
    click = dwell.set_index("event_type").loc["click"]
    scroll = dwell.set_index("event_type").loc["scroll_deep"]
    return "\n".join(
        [
            "# Phase 6 Relevance-Focused EDA", "", "## What the behavior fields mean", "",
            f"All {metrics['engaged_rows']:,} engaged rows have exactly one event type. There are no "
            "click-plus-scroll or click-plus-bookmark rows at the Phase 6 grain. The safest reading is "
            "that the file stores mutually exclusive terminal outcomes, not a complete event funnel. "
            "Phase 7 rules should therefore use event alternatives rather than require event conjunctions.", "",
            "## Dwell-time evidence", "",
            f"Click dwell is short and right-skewed: median {click['p50']:.1f}s, p75 {click['p75']:.1f}s, "
            f"p90 {click['p90']:.1f}s, with {int(click['zero_dwell_rows'])} zero-dwell clicks. Deep-scroll "
            f"dwell is separated from clicks (minimum {scroll['p00']:.0f}s, median {scroll['p50']:.0f}s). "
            "Bookmarks and return visits are rare but intentional actions and should remain strong signals "
            "without an extra dwell requirement.", "", _markdown_table(thresholds.round(3)), "",
            "A 30-second meaningful-click threshold retains only 133 of 944 clicks (14.1%); 20 seconds "
            "retains 241 (25.5%), and 10 seconds retains 500 (53.0%). These cutoffs should be compared in "
            "sensitivity analysis rather than presenting one as clinically validated.", "",
            "## Position and missing-positive bias", "",
            f"Rank 1 engagement is {metrics['rank1_engagement_rate']:.1%} versus "
            f"{metrics['later_rank_engagement_rate']:.1%} for later ranks, a "
            f"{metrics['rank1_absolute_lift']:.1%} absolute difference. Rates are not monotonically decreasing "
            "after rank 1, but inferred position is still a confounder and should be retained for propensity-aware "
            "sensitivity checks.", "",
            f"There are {metrics['sessions_without_engagement']:,} of {metrics['sessions']:,} sessions and "
            f"{metrics['queries_without_engagement']:,} of {metrics['queries']:,} queries with no observed engagement. "
            "Those queries have no behavior-derived positive for retrieval metrics such as Recall or NDCG; report "
            "their coverage separately rather than silently treating all shown content as negative.", "",
            "## Repeatability and construct validity", "", _markdown_table(repeatability.round(3)), "",
            f"Only {metrics['repeated_query_content_pairs']:,} query-content pairs repeat across sessions, and "
            f"{metrics['mixed_repeat_pairs']:,} of them switch between engaged and unengaged outcomes. Preserve the "
            "session-level labels; if Phase 7 also creates a query-content aggregate, include exposure count and a "
            "conflict indicator rather than using a single event as immutable truth.", "", _markdown_table(
                compatibility[["dimension", "matched", "impressions", "engagement_rate", "engagement_ci95_low", "engagement_ci95_high"]].round(3)
            ), "",
            "Exact ICD-10, ATC-code, and ATC-class matches have somewhat higher observed engagement than nonmatches, "
            "while therapeutic-area and exact-language matches show little separation. Match groups are small and "
            "behavior is confounded by the existing ranker, so this is a sanity check—not evidence for relevance labels.", "",
            "## Illustrative Phase 7 sensitivity schemes", "", _markdown_table(
                schemes[["scheme", "grade", "rows", "share_all_rows", "share_engaged_rows"]].round(3)
            ), "",
            "The schemes above are diagnostic only and are not written back to the behavioral table. They show how "
            "strong-positive support changes when dwell thresholds are introduced. Phase 7 should freeze one primary "
            "scheme, retain at least one sensitivity scheme, and report label coverage and ranking metrics under both.", "",
            "## Recommended Phase 7 design constraints", "",
            "- Treat bookmark and return visit as alternative strong-positive outcomes.",
            "- Treat deep scroll as stronger evidence than a bare click; do not require a separate click flag.",
            "- Split clicks by observed dwell quantiles and test at least two thresholds (for example 10s and 20s or 30s).",
            "- Call grade 0 `exposed without observed engagement`, not `irrelevant`.",
            "- Keep inferred rank, doctor, and session identifiers available for bias and robustness analyses.",
            "- Exclude or separately report queries with no positive grade when computing positive-dependent retrieval metrics.",
            "- Report results by intent, language, and content type, but do not encode their raw engagement rates into labels.", "",
        ]
    )


def build_relevance_eda_artifacts() -> dict[str, Path]:
    table = load_behavioral_table()
    dwell = dwell_distribution(table)
    thresholds = dwell_threshold_sensitivity(table)
    position = engagement_by_position(table)
    slices = engagement_slices(table)
    sessions = session_engagement_distribution(table)
    repeatability = query_content_repeatability(table)
    compatibility = structured_compatibility_sanity_check(table)
    schemes = candidate_grade_sensitivity(table)

    event_sum = table[[EVENT_COLUMN[event] for event in EVENT_TYPES]].sum(axis=1)
    if not event_sum.eq(table["has_engagement"].astype(int)).all():
        raise AssertionError("Event types are expected to be mutually exclusive in the supplied data")

    rank1 = table["inferred_rank"].eq(1)
    query_engagement = table.groupby("query_id")["has_engagement"].any()
    session_engagement = table.groupby("session_id")["has_engagement"].any()
    repeated = repeatability.set_index("repeatability")
    metrics: dict[str, Any] = {
        "analytical_rows": int(len(table)),
        "engaged_rows": int(table["has_engagement"].sum()),
        "event_types_mutually_exclusive": True,
        "rows_with_multiple_event_types": int(event_sum.gt(1).sum()),
        "click_zero_dwell_rows": int(table.loc[table["clicked"], "dwell_time"].eq(0).sum()),
        "click_dwell_median": float(table.loc[table["clicked"], "dwell_time"].median()),
        "click_dwell_p75": float(table.loc[table["clicked"], "dwell_time"].quantile(0.75)),
        "scroll_dwell_min": int(table.loc[table["scroll_deep"], "dwell_time"].min()),
        "scroll_dwell_median": float(table.loc[table["scroll_deep"], "dwell_time"].median()),
        "rank1_engagement_rate": float(table.loc[rank1, "has_engagement"].mean()),
        "later_rank_engagement_rate": float(table.loc[~rank1, "has_engagement"].mean()),
        "rank1_absolute_lift": float(
            table.loc[rank1, "has_engagement"].mean() - table.loc[~rank1, "has_engagement"].mean()
        ),
        "sessions": int(table["session_id"].nunique()),
        "sessions_without_engagement": int((~session_engagement).sum()),
        "queries": int(table["query_id"].nunique()),
        "queries_without_engagement": int((~query_engagement).sum()),
        "unique_query_content_pairs": int(table[["query_id", "content_id"]].drop_duplicates().shape[0]),
        "repeated_query_content_pairs": int(
            repeated.loc[
                [index for index in repeated.index if index.startswith("repeated_")],
                "query_content_pairs",
            ].sum()
        ),
        "mixed_repeat_pairs": int(repeated.loc["repeated_mixed_engagement", "query_content_pairs"]),
        "candidate_grades_written_to_behavioral_table": False,
        "eda_is_descriptive_not_causal": True,
    }

    EDA_DIR.mkdir(parents=True, exist_ok=True)
    dwell.to_csv(DWELL_DISTRIBUTION_PATH, index=False)
    thresholds.to_csv(THRESHOLD_SENSITIVITY_PATH, index=False)
    position.to_csv(POSITION_PATH, index=False)
    slices.to_csv(SLICE_PATH, index=False)
    sessions.to_csv(SESSION_PATH, index=False)
    repeatability.to_csv(REPEATABILITY_PATH, index=False)
    compatibility.to_csv(COMPATIBILITY_PATH, index=False)
    schemes.to_csv(CANDIDATE_SCHEMES_PATH, index=False)
    EDA_METRICS_PATH.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    EDA_REPORT_PATH.write_text(
        build_report(metrics, dwell, thresholds, position, repeatability, compatibility, schemes),
        encoding="utf-8",
    )
    _plot_eda(table, position, schemes)

    return {
        "metrics": EDA_METRICS_PATH,
        "report": EDA_REPORT_PATH,
        "dwell_distribution": DWELL_DISTRIBUTION_PATH,
        "threshold_sensitivity": THRESHOLD_SENSITIVITY_PATH,
        "position": POSITION_PATH,
        "slices": SLICE_PATH,
        "session_distribution": SESSION_PATH,
        "repeatability": REPEATABILITY_PATH,
        "compatibility": COMPATIBILITY_PATH,
        "candidate_schemes": CANDIDATE_SCHEMES_PATH,
        "figure": EDA_FIGURE_PATH,
    }


if __name__ == "__main__":
    for artifact, path in build_relevance_eda_artifacts().items():
        print(f"{artifact}: {path}")
