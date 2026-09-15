"""Phase 1.5 extended query schema design.

This module decides which contextual query slots are worth carrying forward.
It does not populate the final enriched query table; that belongs to Phase 1.6.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any
import warnings

import pandas as pd

from src.config import OUTPUT_DIR
from src.data import load_content, load_queries


SCHEMA_DIR = OUTPUT_DIR / "schema"


@dataclass(frozen=True)
class SlotPattern:
    slot: str
    query_pattern: str
    content_pattern: str | None
    candidate_columns: tuple[str, ...]
    status: str
    selected_columns: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class SchemaColumn:
    column: str
    dtype: str
    nullable: bool
    allowed_values: str
    extraction_strategy: str
    content_matchability: str
    rationale: str
    priority: str


SLOT_PATTERNS: tuple[SlotPattern, ...] = (
    SlotPattern(
        slot="age",
        query_pattern=r"\b(?:age|umur)?\s*\d{1,3}\s*(?:year old|years old|yo|y o|tahun)\b",
        content_pattern=None,
        candidate_columns=("age",),
        status="defer",
        selected_columns=(),
        rationale="No explicit numeric ages appear in the 500 supplied queries; keep age_group instead.",
    ),
    SlotPattern(
        slot="age_group",
        query_pattern=r"\b(anak|child|children|pediatric|paediatric|elderly|geriatric|lansia)\b",
        content_pattern=r"\b(anak|child|children|pediatric|paediatric|elderly|geriatric|lansia)\b",
        candidate_columns=("age_group",),
        status="selected",
        selected_columns=("age_group",),
        rationale="Pediatric and elderly constraints recur and materially change clinical relevance.",
    ),
    SlotPattern(
        slot="sex",
        query_pattern=r"\b(male|female|pria|wanita|laki laki|perempuan)\b",
        content_pattern=r"\b(male|female|pria|wanita|laki laki|perempuan)\b",
        candidate_columns=("sex",),
        status="defer",
        selected_columns=(),
        rationale="No sex-specific query constraints were observed.",
    ),
    SlotPattern(
        slot="pregnancy",
        query_pattern=r"\b(pregnan\w*|hamil|preeclampsia|pre eclampsia)\b",
        content_pattern=r"\b(pregnan\w*|hamil|preeclampsia|pre eclampsia)\b",
        candidate_columns=("pregnancy_status",),
        status="selected",
        selected_columns=("pregnancy_status",),
        rationale="Pregnancy-related context is frequent and strongly affects medication safety and management relevance.",
    ),
    SlotPattern(
        slot="year_or_recency",
        query_pattern=r"\b20[2-3][0-9]\b|\b(latest|terbaru)\b",
        content_pattern=r"\b20[2-3][0-9]\b|\b(latest|terbaru)\b",
        candidate_columns=("year",),
        status="selected",
        selected_columns=("year", "recency_flag"),
        rationale="Year and latest/terbaru constraints recur and can match content.publication_year.",
    ),
    SlotPattern(
        slot="dose_context",
        query_pattern=r"\b(dose|dosing|dosis|titrasi|adjustment|penyesuaian)\b",
        content_pattern=r"\b(dose|dosing|dosis|titrasi|adjustment|penyesuaian)\b",
        candidate_columns=("dose_value", "dose_unit"),
        status="selected_partial",
        selected_columns=("dose_context_flag",),
        rationale="Dosing information need is common, but explicit dose values/units are absent in query text.",
    ),
    SlotPattern(
        slot="dose_value",
        query_pattern=r"\b\d+(?:\.\d+)?\s*(mg|mcg|g|iu|unit|units|ml)\b",
        content_pattern=r"\b\d+(?:\.\d+)?\s*(mg|mcg|g|iu|unit|units|ml)\b",
        candidate_columns=("dose_value", "dose_unit"),
        status="defer",
        selected_columns=(),
        rationale="No explicit numeric dose values are observed; extracting empty columns would add noise.",
    ),
    SlotPattern(
        slot="route",
        query_pattern=r"\b(oral|po|iv|intravenous|inhaled|topical|subcutaneous|sc|im)\b",
        content_pattern=r"\b(oral|po|iv|intravenous|inhaled|topical|subcutaneous|sc|im)\b",
        candidate_columns=("route",),
        status="selected_low_support",
        selected_columns=("route",),
        rationale="Route is sparse but deterministic and clinically meaningful when present.",
    ),
    SlotPattern(
        slot="duration",
        query_pattern=r"\b\d+\s*(day|days|week|weeks|month|months|hari|minggu|bulan)\b",
        content_pattern=r"\b\d+\s*(day|days|week|weeks|month|months|hari|minggu|bulan)\b",
        candidate_columns=("duration_value", "duration_unit"),
        status="defer",
        selected_columns=(),
        rationale="No explicit duration constraints are observed.",
    ),
    SlotPattern(
        slot="renal_function",
        query_pattern=r"\b(egfr|crcl|ckd stage\s*\d|renal impairment|renal dose|renal adjustment|penyesuaian dosis.*renal|renal.*penyesuaian dosis)\b",
        content_pattern=r"\b(egfr|crcl|ckd stage\s*\d|renal impairment|renal dose|renal adjustment|renal and hepatic impairment)\b",
        candidate_columns=("egfr", "renal_function_group"),
        status="selected_partial",
        selected_columns=("renal_function_group",),
        rationale="Renal dose/impairment context recurs, while broad CKD disease mentions remain covered by supplied disease NER.",
    ),
    SlotPattern(
        slot="hepatic_function",
        query_pattern=r"\b(hepatic impairment|liver disease|cirrhosis|hepatik)\b",
        content_pattern=r"\b(hepatic impairment|liver disease|cirrhosis|hepatik)\b",
        candidate_columns=(),
        status="selected",
        selected_columns=("hepatic_impairment_flag",),
        rationale="Hepatic impairment is not in the initial candidate list but recurs and affects medication safety/dosing.",
    ),
    SlotPattern(
        slot="lab_values",
        query_pattern=r"\b(hba1c|creatinine|crp|esr|alt|ast|hemoglobin|anaemia|anemia|platelet|wbc)\b|\b\d+(?:\.\d+)?\s*(mmol/l|mg/dl|g/dl)\b",
        content_pattern=r"\b(hba1c|creatinine|crp|esr|alt|ast|hemoglobin|anaemia|anemia|platelet|wbc)\b|\b\d+(?:\.\d+)?\s*(mmol/l|mg/dl|g/dl)\b",
        candidate_columns=("lab_name", "lab_value", "lab_unit"),
        status="defer",
        selected_columns=(),
        rationale="Observed terms are mostly diagnoses/entities such as anaemia, not extractable lab value constraints.",
    ),
    SlotPattern(
        slot="severity",
        query_pattern=r"\b(mild|moderate|severe|berat|ringan)\b",
        content_pattern=r"\b(mild|moderate|severe|berat|ringan)\b",
        candidate_columns=("severity",),
        status="defer",
        selected_columns=(),
        rationale="No clear severity constraints are observed in query text.",
    ),
    SlotPattern(
        slot="comparison",
        query_pattern=r"\b(vs|versus|compare|comparison|dibanding)\b",
        content_pattern=r"\b(vs|versus|compare|comparison|dibanding)\b",
        candidate_columns=("comparison_flag",),
        status="selected",
        selected_columns=("comparison_flag",),
        rationale="Comparison requests recur and imply different content preferences.",
    ),
    SlotPattern(
        slot="negation",
        query_pattern=r"\b(no|without|bukan|tidak)\b",
        content_pattern=None,
        candidate_columns=("negation_flag",),
        status="selected_flag_only",
        selected_columns=("negation_flag",),
        rationale="Negation appears repeatedly; entity-level negation is deferred because it requires safer parsing.",
    ),
    SlotPattern(
        slot="prior_treatment_failure",
        query_pattern=r"\b(after .* failure|gagal|resistant|resistance|refractory|resistensi)\b",
        content_pattern=r"\b(after .* failure|gagal|resistant|resistance|refractory|resistensi)\b",
        candidate_columns=(),
        status="selected",
        selected_columns=("prior_treatment_failure_flag",),
        rationale="Prior failure/resistance changes relevance toward add-on, alternative, or refractory-case content.",
    ),
)


SCHEMA_COLUMNS: tuple[SchemaColumn, ...] = (
    SchemaColumn(
        column="age_group",
        dtype="category",
        nullable=True,
        allowed_values="pediatric; adolescent; adult; elderly",
        extraction_strategy="Rule-based lexical cues; derive from explicit age only if later present.",
        content_matchability="Textual title/content matching for pediatric, child, elderly, geriatric.",
        rationale="Selected instead of numeric age because only age-group cues recur in this dataset.",
        priority="high",
    ),
    SchemaColumn(
        column="pregnancy_status",
        dtype="category",
        nullable=True,
        allowed_values="pregnant; pregnancy_related",
        extraction_strategy="Regex over pregnancy, pregnant, hamil, preeclampsia variants.",
        content_matchability="Textual match against title/content pregnancy terms.",
        rationale="Material for medication safety and obstetric management.",
        priority="high",
    ),
    SchemaColumn(
        column="year",
        dtype="integer",
        nullable=True,
        allowed_values="2020-2039 observed pattern",
        extraction_strategy="Regex for four-digit years.",
        content_matchability="Direct match to content.publication_year metadata.",
        rationale="Supports guideline/evidence recency constraints.",
        priority="high",
    ),
    SchemaColumn(
        column="recency_flag",
        dtype="boolean",
        nullable=False,
        allowed_values="true; false",
        extraction_strategy="Detect latest, terbaru, guideline update without requiring a numeric year.",
        content_matchability="Can boost newer publication_year when no exact year is supplied.",
        rationale="Captures recency intent that year alone misses.",
        priority="high",
    ),
    SchemaColumn(
        column="dose_context_flag",
        dtype="boolean",
        nullable=False,
        allowed_values="true; false",
        extraction_strategy="Detect dose, dosing, dosis, titrasi, adjustment, penyesuaian.",
        content_matchability="Textual match to dosing/reference content and drug_profile content_type.",
        rationale="Dosing requests are common even without explicit values.",
        priority="high",
    ),
    SchemaColumn(
        column="route",
        dtype="category",
        nullable=True,
        allowed_values="oral; iv; im; subcutaneous; inhaled; topical",
        extraction_strategy="Normalize route synonyms such as PO->oral, intravenous->iv, SC->subcutaneous.",
        content_matchability="Textual match against route mentions in titles/content.",
        rationale="Sparse but high-precision and clinically meaningful when present.",
        priority="medium",
    ),
    SchemaColumn(
        column="renal_function_group",
        dtype="category",
        nullable=True,
        allowed_values="renal_impairment; severe_impairment if CKD stage/eGFR supports it",
        extraction_strategy="Detect renal impairment, renal dose/adjustment, CKD stage, eGFR/CrCl.",
        content_matchability="Textual match against renal impairment/dose content; numeric matching if eGFR appears later.",
        rationale="Renal dose/impairment context materially changes drug dosing and safety relevance.",
        priority="high",
    ),
    SchemaColumn(
        column="hepatic_impairment_flag",
        dtype="boolean",
        nullable=False,
        allowed_values="true; false",
        extraction_strategy="Detect hepatic impairment, liver disease, cirrhosis, hepatik.",
        content_matchability="Textual match against hepatic/liver content.",
        rationale="Dataset-specific recurring safety/dosing context absent from the initial candidate list.",
        priority="medium",
    ),
    SchemaColumn(
        column="comparison_flag",
        dtype="boolean",
        nullable=False,
        allowed_values="true; false",
        extraction_strategy="Detect vs, versus, compare, comparison, dibanding.",
        content_matchability="Textual match to versus/comparison/meta-analysis titles; useful for reranking.",
        rationale="Comparison changes preferred content type and ranking signals.",
        priority="high",
    ),
    SchemaColumn(
        column="negation_flag",
        dtype="boolean",
        nullable=False,
        allowed_values="true; false",
        extraction_strategy="Detect no, without, bukan, tidak.",
        content_matchability="Mostly query-side guardrail; do not use as positive content match.",
        rationale="Useful for ambiguity/failure analysis; negated entity extraction is deferred.",
        priority="medium",
    ),
    SchemaColumn(
        column="prior_treatment_failure_flag",
        dtype="boolean",
        nullable=False,
        allowed_values="true; false",
        extraction_strategy="Detect failure, gagal, resistant, resistance, refractory, resistensi.",
        content_matchability="Textual match to resistant/resistance/refractory/case-report content.",
        rationale="Signals need for alternatives, escalation, or refractory disease evidence.",
        priority="medium",
    ),
)


def count_pattern(df: pd.DataFrame, text_column: str, pattern: str | None) -> tuple[int, float]:
    if not pattern:
        return 0, 0.0
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="This pattern is interpreted as a regular expression",
            category=UserWarning,
        )
        mask = df[text_column].fillna("").str.lower().str.contains(
            pattern,
            regex=True,
            flags=re.IGNORECASE,
        )
    count = int(mask.sum())
    return count, count / len(df) if len(df) else 0.0


def build_candidate_profile(queries: pd.DataFrame, content: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for slot in SLOT_PATTERNS:
        query_count, query_pct = count_pattern(queries, "query_text", slot.query_pattern)
        content_count, content_pct = count_pattern(content, "title", slot.content_pattern)
        rows.append(
            {
                "slot": slot.slot,
                "candidate_columns": "; ".join(slot.candidate_columns) or "none",
                "status": slot.status,
                "selected_columns": "; ".join(slot.selected_columns) or "none",
                "query_matches": query_count,
                "query_pct": round(query_pct, 4),
                "content_title_matches": content_count,
                "content_title_pct": round(content_pct, 4),
                "rationale": slot.rationale,
            }
        )
    return pd.DataFrame(rows)


def build_schema_table() -> pd.DataFrame:
    return pd.DataFrame(asdict(column) for column in SCHEMA_COLUMNS)


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
        "| " + " | ".join(row[index].ljust(widths[index]) for index in range(len(headers))) + " |"
        for row in rows
    ]
    return "\n".join([header_line, sep_line, *body])


def write_schema_report(
    report_path: Path,
    candidate_profile: pd.DataFrame,
    schema_table: pd.DataFrame,
) -> None:
    selected = candidate_profile[candidate_profile["status"].str.startswith("selected")]
    deferred = candidate_profile[candidate_profile["status"] == "defer"]

    lines = [
        "# Phase 1.5 Extended Query Schema",
        "",
        "This phase defines the contextual clinical slots to carry into Phase 1.6 extraction.",
        "It intentionally keeps supplied NER, contextual slots, and intent labels separate.",
        "",
        "## Selection Criteria",
        "",
        "A slot is selected when it occurs repeatedly, can materially affect relevance, can be extracted reliably, and can be matched against content text or metadata.",
        "",
        "## Selected Schema",
        "",
        markdown_table(
            schema_table[
                [
                    "column",
                    "dtype",
                    "allowed_values",
                    "extraction_strategy",
                    "content_matchability",
                    "priority",
                ]
            ],
            max_rows=20,
        ),
        "",
        "## Candidate Slot Profile",
        "",
        markdown_table(
            candidate_profile[
                [
                    "slot",
                    "status",
                    "selected_columns",
                    "query_matches",
                    "query_pct",
                    "content_title_matches",
                    "content_title_pct",
                ]
            ],
            max_rows=30,
        ),
        "",
        "## Selected Slot Rationale",
        "",
        markdown_table(selected[["slot", "selected_columns", "rationale"]], max_rows=30),
        "",
        "## Deferred Slot Rationale",
        "",
        markdown_table(deferred[["slot", "candidate_columns", "rationale"]], max_rows=30),
        "",
        "## Conceptual Separation",
        "",
        "- Existing NER columns answer what medical concepts are mentioned: disease, molecule, drug class, therapeutic area.",
        "- Contextual slots answer under what clinical constraints the information is requested: pregnancy, renal function, recency, dosing context, comparison.",
        "- Intent classification answers what the doctor wants to know and is handled in later phases.",
        "",
        "## Phase 1.6 Contract",
        "",
        "Phase 1.6 should populate the selected schema columns for all 500 queries and preserve the original raw query columns.",
        "Deferred fields should not be added unless later manual review finds enough reliable evidence.",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")

