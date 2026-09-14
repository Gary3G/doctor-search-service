"""Phase 1.6 contextual query slot extraction.

Populates the extended query schema selected in Phase 1.5 using deterministic,
auditable rules. The output preserves every original query column and appends
only the approved contextual slot columns.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import pandas as pd

from src.config import OUTPUT_DIR, PROCESSED_DATA_DIR, set_random_seed
from src.data import load_queries


PHASE16_DIR = OUTPUT_DIR / "schema"
ENRICHED_QUERIES_PATH = PROCESSED_DATA_DIR / "queries_with_contextual_slots.csv"
EXTRACTION_SUMMARY_PATH = PHASE16_DIR / "phase16_extraction_summary.csv"
EXTRACTION_EXAMPLES_PATH = PHASE16_DIR / "phase16_extraction_examples.csv"
EXTRACTION_QA_PATH = PHASE16_DIR / "phase16_extraction_quality_review.csv"
EXTRACTION_REPORT_PATH = PHASE16_DIR / "phase16_contextual_extraction.md"


@dataclass(frozen=True)
class ExtractedSlots:
    age_group: str | None
    pregnancy_status: str | None
    year: int | None
    recency_flag: bool
    dose_context_flag: bool
    route: str | None
    renal_function_group: str | None
    hepatic_impairment_flag: bool
    comparison_flag: bool
    negation_flag: bool
    prior_treatment_failure_flag: bool


AGE_PATTERNS = (
    re.compile(r"\b(?:age|umur)?\s*(?P<age>\d{1,3})\s*(?:year old|years old|yo|y o|tahun)\b", re.I),
)
PEDIATRIC_PATTERN = re.compile(r"\b(anak|child|children|pediatric|paediatric)\b", re.I)
ELDERLY_PATTERN = re.compile(r"\b(elderly|geriatric|lansia)\b", re.I)
PREGNANCY_PATTERN = re.compile(r"\b(pregnan\w*|hamil|preeclampsia|pre eclampsia)\b", re.I)
YEAR_PATTERN = re.compile(r"\b(20[2-3][0-9])\b")
RECENCY_PATTERN = re.compile(r"\b(latest|terbaru|guideline update|update guideline)\b", re.I)
DOSE_CONTEXT_PATTERN = re.compile(
    r"\b(dose|dosing|dosis|titrasi|adjustment|penyesuaian)\b",
    re.I,
)
ROUTE_PATTERNS = (
    ("subcutaneous", re.compile(r"\b(subcutaneous|sc)\b", re.I)),
    ("iv", re.compile(r"\b(iv|intravenous)\b", re.I)),
    ("im", re.compile(r"\bim\b", re.I)),
    ("inhaled", re.compile(r"\b(inhaled|inhalasi)\b", re.I)),
    ("topical", re.compile(r"\b(topical|topikal)\b", re.I)),
    ("oral", re.compile(r"\b(oral|po)\b", re.I)),
)
RENAL_PATTERNS = (
    ("severe_impairment", re.compile(r"\b(egfr\s*[<≤]\s*30|crcl\s*[<≤]\s*30|ckd stage\s*[45])\b", re.I)),
    ("renal_impairment", re.compile(r"\b(renal impairment|renal dose|renal adjustment|penyesuaian dosis.*renal|renal.*penyesuaian dosis)\b", re.I)),
)
HEPATIC_PATTERN = re.compile(r"\b(hepatic impairment|liver disease|cirrhosis|hepatik)\b", re.I)
COMPARISON_PATTERN = re.compile(r"\b(vs|versus|compare|comparison|dibanding)\b", re.I)
NEGATION_PATTERN = re.compile(r"\b(no|without|bukan|tidak)\b", re.I)
PRIOR_FAILURE_PATTERN = re.compile(
    r"\b(after\b.*\bfailure|gagal|resistant|resistance|refractory|resistensi)\b",
    re.I,
)


def normalize_text(value: Any) -> str:
    return "" if pd.isna(value) else str(value)


def age_to_group(age: int) -> str:
    if age < 12:
        return "pediatric"
    if age < 18:
        return "adolescent"
    if age >= 65:
        return "elderly"
    return "adult"


def extract_age_group(text: str) -> str | None:
    for pattern in AGE_PATTERNS:
        match = pattern.search(text)
        if match:
            age = int(match.group("age"))
            if 0 <= age <= 120:
                return age_to_group(age)
    if PEDIATRIC_PATTERN.search(text):
        return "pediatric"
    if ELDERLY_PATTERN.search(text):
        return "elderly"
    return None


def extract_pregnancy_status(text: str) -> str | None:
    if PREGNANCY_PATTERN.search(text):
        if re.search(r"\b(pregnancy|pregnant|hamil)\b", text, re.I):
            return "pregnant"
        return "pregnancy_related"
    return None


def extract_year(text: str) -> int | None:
    years = [int(match) for match in YEAR_PATTERN.findall(text)]
    return max(years) if years else None


def extract_route(text: str) -> str | None:
    for route, pattern in ROUTE_PATTERNS:
        if pattern.search(text):
            return route
    return None


def extract_renal_function_group(text: str) -> str | None:
    for renal_group, pattern in RENAL_PATTERNS:
        if pattern.search(text):
            return renal_group
    return None


def extract_slots(query_text: Any) -> ExtractedSlots:
    text = normalize_text(query_text)
    return ExtractedSlots(
        age_group=extract_age_group(text),
        pregnancy_status=extract_pregnancy_status(text),
        year=extract_year(text),
        recency_flag=bool(RECENCY_PATTERN.search(text)),
        dose_context_flag=bool(DOSE_CONTEXT_PATTERN.search(text)),
        route=extract_route(text),
        renal_function_group=extract_renal_function_group(text),
        hepatic_impairment_flag=bool(HEPATIC_PATTERN.search(text)),
        comparison_flag=bool(COMPARISON_PATTERN.search(text)),
        negation_flag=bool(NEGATION_PATTERN.search(text)),
        prior_treatment_failure_flag=bool(PRIOR_FAILURE_PATTERN.search(text)),
    )


def enrich_queries(queries: pd.DataFrame) -> pd.DataFrame:
    slot_rows = [extract_slots(query_text).__dict__ for query_text in queries["query_text"]]
    slots = pd.DataFrame(slot_rows)
    enriched = pd.concat([queries.reset_index(drop=True), slots], axis=1)

    nullable_string_columns = [
        "age_group",
        "pregnancy_status",
        "route",
        "renal_function_group",
    ]
    for column in nullable_string_columns:
        enriched[column] = enriched[column].astype("string")
    enriched["year"] = enriched["year"].astype("Int64")

    bool_columns = [
        "recency_flag",
        "dose_context_flag",
        "hepatic_impairment_flag",
        "comparison_flag",
        "negation_flag",
        "prior_treatment_failure_flag",
    ]
    for column in bool_columns:
        enriched[column] = enriched[column].astype(bool)
    return enriched


def build_summary(enriched: pd.DataFrame) -> pd.DataFrame:
    slot_columns = [
        "age_group",
        "pregnancy_status",
        "year",
        "recency_flag",
        "dose_context_flag",
        "route",
        "renal_function_group",
        "hepatic_impairment_flag",
        "comparison_flag",
        "negation_flag",
        "prior_treatment_failure_flag",
    ]
    rows: list[dict[str, Any]] = []
    for column in slot_columns:
        if enriched[column].dtype == bool:
            populated = int(enriched[column].sum())
            top_values = "true" if populated else "none"
        else:
            populated = int(enriched[column].notna().sum())
            value_counts = enriched[column].dropna().value_counts().head(5)
            top_values = "; ".join(f"{key}={value}" for key, value in value_counts.items()) or "none"
        rows.append(
            {
                "column": column,
                "populated_rows": populated,
                "population_pct": round(populated / len(enriched), 4),
                "top_values": top_values,
            }
        )
    return pd.DataFrame(rows)


def build_examples(enriched: pd.DataFrame, examples_per_column: int = 8) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    slot_columns = [
        "age_group",
        "pregnancy_status",
        "year",
        "recency_flag",
        "dose_context_flag",
        "route",
        "renal_function_group",
        "hepatic_impairment_flag",
        "comparison_flag",
        "negation_flag",
        "prior_treatment_failure_flag",
    ]
    for column in slot_columns:
        if enriched[column].dtype == bool:
            subset = enriched[enriched[column]]
        else:
            subset = enriched[enriched[column].notna()]
        subset = subset.sort_values("query_id").head(examples_per_column)
        for _, row in subset.iterrows():
            rows.append(
                {
                    "column": column,
                    "query_id": row["query_id"],
                    "query_text": row["query_text"],
                    "extracted_value": row[column],
                }
            )
    return pd.DataFrame(rows)


def build_quality_review_sample(enriched: pd.DataFrame, sample_size: int = 60) -> pd.DataFrame:
    slot_columns = [
        "age_group",
        "pregnancy_status",
        "year",
        "recency_flag",
        "dose_context_flag",
        "route",
        "renal_function_group",
        "hepatic_impairment_flag",
        "comparison_flag",
        "negation_flag",
        "prior_treatment_failure_flag",
    ]
    populated_mask = pd.Series(False, index=enriched.index)
    for column in slot_columns:
        if enriched[column].dtype == bool:
            populated_mask |= enriched[column]
        else:
            populated_mask |= enriched[column].notna()

    populated = enriched[populated_mask].copy()
    empty = enriched[~populated_mask].copy()
    populated_sample_size = min(len(populated), round(sample_size * 0.75))
    empty_sample_size = min(len(empty), sample_size - populated_sample_size)

    samples = []
    if populated_sample_size:
        samples.append(populated.sample(populated_sample_size, random_state=42))
    if empty_sample_size:
        samples.append(empty.sample(empty_sample_size, random_state=42))
    if not samples:
        return pd.DataFrame()

    sample = pd.concat(samples).sample(frac=1, random_state=42).reset_index(drop=True)
    rows: list[dict[str, Any]] = []
    for _, row in sample.iterrows():
        populated_slots = []
        for column in slot_columns:
            value = row[column]
            if isinstance(value, (bool, pd.BooleanDtype)):
                if bool(value):
                    populated_slots.append(f"{column}=true")
            elif pd.notna(value):
                populated_slots.append(f"{column}={value}")
        rows.append(
            {
                "query_id": row["query_id"],
                "query_text": row["query_text"],
                "extracted_slots": "; ".join(populated_slots) if populated_slots else "none",
                "review_label": "",
                "error_type": "",
                "review_notes": "",
            }
        )
    return pd.DataFrame(rows)


def markdown_table(df: pd.DataFrame, max_rows: int = 50) -> str:
    if df.empty:
        return "_No rows._"
    view = df.head(max_rows).copy()
    headers = [str(column) for column in view.columns]
    rows = [[str(value) for value in row] for row in view.to_numpy()]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    header_line = "| " + " | ".join(
        headers[index].ljust(widths[index]) for index in range(len(headers))
    ) + " |"
    sep_line = "| " + " | ".join("-" * widths[index] for index in range(len(headers))) + " |"
    body = [
        "| " + " | ".join(row[index].ljust(widths[index]) for index in range(len(headers)))
        + " |"
        for row in rows
    ]
    return "\n".join([header_line, sep_line, *body])


def write_report(
    report_path: Path,
    enriched_path: Path,
    summary: pd.DataFrame,
    examples: pd.DataFrame,
    qa_sample: pd.DataFrame,
) -> None:
    any_slot_queries = len(
        qa_sample[qa_sample["extracted_slots"] != "none"]
    ) if not qa_sample.empty else 0
    lines = [
        "# Phase 1.6 Contextual Slot Extraction",
        "",
        "This phase populates the selected Phase 1.5 contextual query schema using deterministic rules.",
        "",
        "## Output",
        "",
        f"- Enriched queries: `{enriched_path}`",
        f"- Extraction summary: `{EXTRACTION_SUMMARY_PATH}`",
        f"- Extraction examples: `{EXTRACTION_EXAMPLES_PATH}`",
        f"- QA review sample: `{EXTRACTION_QA_PATH}`",
        "",
        "## Populated Slot Coverage",
        "",
        markdown_table(summary, max_rows=20),
        "",
        f"Queries with at least one extracted contextual slot: {int(summary.attrs.get('queries_with_any_slot', 0))}",
        "",
        "## Example Extractions",
        "",
        markdown_table(examples, max_rows=30),
        "",
        "## Quality Audit",
        "",
        f"- QA sample rows prepared for manual review: {len(qa_sample)}",
        f"- QA sample rows with at least one extracted slot: {any_slot_queries}",
        "- Precision/recall are not claimed as final metrics yet because no independent gold slot labels exist.",
        "- The QA CSV includes blank review fields so sampled rows can be manually marked as correct, false positive, false negative, or partial.",
        "- Likely error types to watch: negation scope, route abbreviations, pregnancy-related disease vs pregnancy status, and renal disease entity vs renal-context constraint.",
        "",
        "## Limitations",
        "",
        "- Entity-level negation is not extracted; only a query-level negation flag is populated.",
        "- Numeric dose, duration, sex, severity, lab values, and explicit eGFR are intentionally deferred based on Phase 1.5 evidence.",
        "- Boolean context flags should be used as interpretable ranking features, not as final relevance labels.",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")


def run_phase16_extraction() -> dict[str, Path]:
    set_random_seed()
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PHASE16_DIR.mkdir(parents=True, exist_ok=True)

    queries = load_queries()
    enriched = enrich_queries(queries)
    summary = build_summary(enriched)
    slot_columns = summary["column"].tolist()
    any_slot_mask = pd.Series(False, index=enriched.index)
    for column in slot_columns:
        if enriched[column].dtype == bool:
            any_slot_mask |= enriched[column]
        else:
            any_slot_mask |= enriched[column].notna()
    summary.attrs["queries_with_any_slot"] = int(any_slot_mask.sum())
    examples = build_examples(enriched)
    qa_sample = build_quality_review_sample(enriched)

    enriched.to_csv(ENRICHED_QUERIES_PATH, index=False)
    summary.to_csv(EXTRACTION_SUMMARY_PATH, index=False)
    examples.to_csv(EXTRACTION_EXAMPLES_PATH, index=False)
    qa_sample.to_csv(EXTRACTION_QA_PATH, index=False)
    write_report(EXTRACTION_REPORT_PATH, ENRICHED_QUERIES_PATH, summary, examples, qa_sample)

    return {
        "enriched_queries": ENRICHED_QUERIES_PATH,
        "summary": EXTRACTION_SUMMARY_PATH,
        "examples": EXTRACTION_EXAMPLES_PATH,
        "qa_sample": EXTRACTION_QA_PATH,
        "report": EXTRACTION_REPORT_PATH,
    }


def main() -> None:
    paths = run_phase16_extraction()
    print(f"Wrote enriched queries: {paths['enriched_queries']}")
    print(f"Wrote extraction report: {paths['report']}")
    print(f"Wrote extraction summary: {paths['summary']}")


if __name__ == "__main__":
    main()
