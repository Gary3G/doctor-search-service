"""Phase 1 data audit for the medical search assessment.

The audit is intentionally lightweight and CPU-only. It produces a reviewer
friendly Markdown summary plus CSV artifacts that can be loaded by the
notebook or cited in the write-up.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import CONFIG, OUTPUT_DIR, set_random_seed
from src.data import load_all_raw


AUDIT_DIR = OUTPUT_DIR / "audits"
ENTITY_COLUMNS = ["disease_entity", "molecule_entity", "drug_class_entity"]


@dataclass(frozen=True)
class AuditPaths:
    report: Path
    metrics: Path
    query_manual_review: Path
    query_near_duplicates: Path
    content_near_duplicates: Path
    suspicious_behavior: Path
    table_dir: Path


def normalize_text(value: Any) -> str:
    text = "" if pd.isna(value) else str(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_entities(value: Any) -> list[str]:
    if pd.isna(value) or str(value).strip() == "":
        return []
    return sorted({part.strip() for part in str(value).split(";") if part.strip()})


def count_entities(row: pd.Series) -> int:
    entities: set[str] = set()
    for column in ENTITY_COLUMNS:
        entities.update(split_entities(row[column]))
    return len(entities)


def word_count(text: Any) -> int:
    return len(normalize_text(text).split())


def table_from_counts(series: pd.Series, name: str, top_n: int = 20) -> pd.DataFrame:
    counts = series.fillna("<MISSING>").value_counts(dropna=False).head(top_n)
    return counts.rename_axis(name).reset_index(name="count")


def describe_numeric(series: pd.Series, name: str) -> pd.DataFrame:
    percentiles = [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]
    described = series.describe(percentiles=percentiles)
    return described.rename(name).reset_index().rename(columns={"index": "statistic"})


def missing_value_table(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.isna()
        .sum()
        .rename("missing_count")
        .reset_index()
        .rename(columns={"index": "column"})
    )


def save_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
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


def find_near_duplicates(
    df: pd.DataFrame,
    id_col: str,
    text_col: str,
    threshold: float = 0.82,
    limit: int = 100,
) -> pd.DataFrame:
    if len(df) < 2:
        return pd.DataFrame(columns=[f"{id_col}_a", f"{id_col}_b", "similarity"])

    texts = df[text_col].fillna("").map(normalize_text)
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
    matrix = vectorizer.fit_transform(texts)
    similarities = cosine_similarity(matrix)
    rows: list[dict[str, Any]] = []

    for i in range(len(df)):
        for j in range(i + 1, len(df)):
            score = float(similarities[i, j])
            if score >= threshold:
                rows.append(
                    {
                        f"{id_col}_a": df.iloc[i][id_col],
                        f"{id_col}_b": df.iloc[j][id_col],
                        "similarity": round(score, 4),
                        f"{text_col}_a": df.iloc[i][text_col],
                        f"{text_col}_b": df.iloc[j][text_col],
                    }
                )

    return (
        pd.DataFrame(rows)
        .sort_values("similarity", ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )


def infer_apparent_intent_cue(query: str) -> str:
    """Assign a provisional, rule-based intent cue for Phase 1 review only.

    Final intent taxonomy and labeling happen in later phases. This helper is
    meant to make the manual audit sample easier to scan, not to create labels.
    """
    text = normalize_text(query)
    patterns = [
        (r"\b(interaksi|interaction|kombinasi)\b", "Pharmacotherapy - interaction"),
        (r"\b(vs|versus|compare|comparison|dibanding)\b", "Pharmacotherapy - comparison"),
        (r"\b(dose|dosing|dosis|titrasi|egfr|crcl|renal dose)\b", "Pharmacotherapy - dosing/administration"),
        (r"\b(safe|safety|aman|adverse|side effect|efek samping|kontraindikasi|contraindication|hepatic impairment)\b", "Pharmacotherapy - safety/precaution"),
        (r"\b(indication|indikasi|prophylaxis|profilaksis)\b", "Pharmacotherapy - indication/prophylaxis"),
        (r"\b(efficacy|outcome|clinical outcome|trial|data)\b", "Evidence / outcomes"),
        (r"\b(guideline|panduan|latest|terbaru|esc|aha)\b", "Evidence / guideline lookup"),
        (r"\b(diagnosis|screening|differential)\b", "Diagnosis / differential diagnosis"),
        (r"\b(workup|work up|which test|imaging|laboratory|lab test)\b", "Work-up / test selection"),
        (r"\b(interpret|interpretation|arti|makna|result|hasil)\b", "Test / clinical data interpretation"),
        (r"\b(tatalaksana|management|treatment|terapi|algoritma|step up|add on)\b", "Management / treatment"),
        (r"\b(prognosis|mortality|survival|risk)\b", "Epidemiology / prognosis"),
        (r"\b(pathophysiology|role|etiology|aetiology|cause|penyebab)\b", "Disease description / mechanism"),
    ]
    for pattern, intent in patterns:
        if re.search(pattern, text):
            return intent
    return "Other / ambiguous"


def extract_missing_structure(query: str) -> list[str]:
    text = normalize_text(query)
    slots: list[str] = []

    age_match = re.search(r"\b(?:age|umur)?\s*(\d{1,3})\s*(?:year old|years old|yo|y o|tahun)\b", text)
    if age_match:
        age = int(age_match.group(1))
        if age < 12:
            age_group = "pediatric"
        elif age < 18:
            age_group = "adolescent"
        elif age >= 65:
            age_group = "elderly"
        else:
            age_group = "adult"
        slots.append(f"age={age}")
        slots.append(f"age_group={age_group}")
    elif re.search(r"\b(anak|child|children|pediatric|paediatric)\b", text):
        slots.append("age_group=pediatric")
    elif re.search(r"\b(elderly|geriatric|lansia)\b", text):
        slots.append("age_group=elderly")

    if re.search(r"\b(pregnan\w*|hamil|preeclampsia|pre eclampsia)\b", text):
        slots.append("pregnancy_related=true")

    years = sorted(set(re.findall(r"\b(20[2-3][0-9])\b", text)))
    slots.extend(f"year={year}" for year in years)

    if re.search(r"\b(egfr|crcl|renal impairment|ckd|chronic kidney|kidney disease)\b", text):
        slots.append("renal_function_constraint=true")
    if re.search(r"\b(hepatic impairment|liver disease|cirrhosis|hepatik)\b", text):
        slots.append("hepatic_function_constraint=true")

    dose_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(mg|mcg|g|iu|unit|units|ml)\b", text)
    if dose_match:
        slots.append(f"dose_value={dose_match.group(1)}")
        slots.append(f"dose_unit={dose_match.group(2)}")
    elif re.search(r"\b(dose|dosing|dosis|titrasi)\b", text):
        slots.append("dose_context=true")

    duration_match = re.search(
        r"\b(\d+)\s*(day|days|week|weeks|month|months|hari|minggu|bulan)\b",
        text,
    )
    if duration_match:
        slots.append(f"duration={duration_match.group(1)} {duration_match.group(2)}")

    if re.search(r"\b(oral|iv|intravenous|inhaled|topical|subcutaneous|sc|im)\b", text):
        slots.append("route_mentioned=true")

    if re.search(r"\b(male|female|pria|wanita|laki laki|perempuan)\b", text):
        slots.append("sex_mentioned=true")

    if re.search(r"\b(mild|moderate|severe|berat|ringan)\b", text):
        slots.append("severity_mentioned=true")

    if re.search(r"\b(vs|versus|compare|comparison|dibanding)\b", text):
        slots.append("comparison_flag=true")

    if re.search(r"\b(no|without|bukan|tidak)\b", text):
        slots.append("negation_flag=true")

    if re.search(r"\b(after .* failure|gagal|resistant|refractory)\b", text):
        slots.append("prior_treatment_failure=true")

    return slots


def difficulty_label(query: str, language: str, missing_structure: Iterable[str]) -> str:
    intent = infer_apparent_intent_cue(query)
    slots = list(missing_structure)
    if (
        language == "MIXED"
        or intent in {"Pharmacotherapy - comparison", "Pharmacotherapy - interaction"}
        or len(slots) >= 3
    ):
        return "high"
    if len(slots) >= 1 or intent in {
        "Pharmacotherapy - safety/precaution",
        "Pharmacotherapy - dosing/administration",
        "Evidence / outcomes",
    }:
        return "medium"
    return "low"


def is_ambiguous(query: str, missing_structure: Iterable[str]) -> bool:
    text = normalize_text(query)
    intent = infer_apparent_intent_cue(query)
    return (
        intent == "Other / ambiguous"
        or word_count(text) <= 4
        or ("latest" in text or "terbaru" in text) and not re.search(r"\b20[2-3][0-9]\b", text)
        or ("dose" in text or "dosis" in text) and not any(slot.startswith("dose_value=") for slot in missing_structure)
    )


def supplied_entities(row: pd.Series) -> str:
    parts = []
    for column in ENTITY_COLUMNS:
        entities = split_entities(row[column])
        if entities:
            parts.append(f"{column.replace('_entity', '')}: {', '.join(entities)}")
    return " | ".join(parts)


def build_manual_query_review(queries: pd.DataFrame, sample_size: int = 120) -> pd.DataFrame:
    sample_frames = []
    for _, frame in queries.groupby(["language", "therapeutic_area"]):
        sample_frames.append(
            frame.sample(
                min(len(frame), max(1, round(sample_size * len(frame) / len(queries)))),
                random_state=CONFIG.random_seed,
            )
        )
    sample = pd.concat(sample_frames, ignore_index=True).drop_duplicates("query_id")
    if len(sample) < sample_size:
        remainder = queries[~queries["query_id"].isin(sample["query_id"])]
        sample = pd.concat(
            [
                sample,
                remainder.sample(sample_size - len(sample), random_state=CONFIG.random_seed),
            ],
            ignore_index=True,
        )
    sample = sample.sample(sample_size, random_state=CONFIG.random_seed).sort_values("query_id")

    rows = []
    for _, row in sample.iterrows():
        slots = extract_missing_structure(row["query_text"])
        rows.append(
            {
                "query_id": row["query_id"],
                "query": row["query_text"],
                "language": row["language"],
                "supplied_entities": supplied_entities(row),
                "missing_structure": "; ".join(slots) if slots else "none obvious",
                "apparent_intent_cue": infer_apparent_intent_cue(row["query_text"]),
                "likely_retrieval_difficulty": difficulty_label(
                    row["query_text"],
                    row["language"],
                    slots,
                ),
                "ambiguous_or_underspecified": is_ambiguous(row["query_text"], slots),
            }
        )
    return pd.DataFrame(rows)


def build_language_examples(queries: pd.DataFrame, examples_per_language: int = 5) -> pd.DataFrame:
    examples = (
        queries.sort_values(["language", "query_id"])
        .groupby("language", group_keys=False)
        .head(examples_per_language)
        .loc[:, ["language", "query_id", "query_text"]]
        .reset_index(drop=True)
    )
    return examples


def summarize_group_sizes(df: pd.DataFrame, group_col: str, metric_name: str) -> pd.DataFrame:
    grouped = df.groupby(group_col).size()
    described = grouped.describe(percentiles=[0.25, 0.5, 0.75, 0.95, 0.99])
    return described.rename(metric_name).reset_index().rename(columns={"index": "statistic"})


def audit_queries(queries: pd.DataFrame, paths: AuditPaths) -> dict[str, Any]:
    query_profile = queries.copy()
    query_profile["normalized_query"] = query_profile["query_text"].map(normalize_text)
    query_profile["query_word_count"] = query_profile["query_text"].map(word_count)
    query_profile["entity_count"] = query_profile.apply(count_entities, axis=1)

    table_dir = paths.table_dir / "queries"
    save_table(
        pd.DataFrame(
            [
                {"metric": "rows", "value": len(queries)},
                {"metric": "unique_query_ids", "value": queries["query_id"].nunique()},
                {"metric": "duplicate_query_ids", "value": int(queries["query_id"].duplicated().sum())},
                {
                    "metric": "duplicate_normalized_query_texts",
                    "value": int(query_profile["normalized_query"].duplicated().sum()),
                },
                {
                    "metric": "queries_without_recognized_entities",
                    "value": int((query_profile["entity_count"] == 0).sum()),
                },
                {
                    "metric": "pct_without_recognized_entities",
                    "value": round(float((query_profile["entity_count"] == 0).mean()), 4),
                },
            ]
        ),
        table_dir / "query_core_metrics.csv",
    )
    save_table(missing_value_table(queries), table_dir / "missing_values.csv")
    save_table(table_from_counts(queries["language"], "language"), table_dir / "language_distribution.csv")
    language_examples = build_language_examples(queries)
    save_table(language_examples, table_dir / "language_examples.csv")
    save_table(describe_numeric(query_profile["query_word_count"], "query_word_count"), table_dir / "query_length_distribution.csv")
    save_table(table_from_counts(queries["therapeutic_area"], "therapeutic_area"), table_dir / "therapeutic_area_distribution.csv")
    save_table(table_from_counts(queries["disease_entity"], "disease_entity"), table_dir / "disease_frequency.csv")
    save_table(table_from_counts(queries["molecule_entity"], "molecule_entity"), table_dir / "molecule_frequency.csv")
    save_table(table_from_counts(queries["drug_class_entity"], "drug_class_entity"), table_dir / "drug_class_frequency.csv")
    save_table(table_from_counts(query_profile["entity_count"], "entity_count"), table_dir / "entity_count_distribution.csv")

    near_duplicates = find_near_duplicates(queries, "query_id", "query_text")
    save_table(near_duplicates, paths.query_near_duplicates)

    manual_review = build_manual_query_review(queries)
    save_table(manual_review, paths.query_manual_review)

    return {
        "rows": len(queries),
        "unique_query_ids": queries["query_id"].nunique(),
        "duplicate_query_ids": int(queries["query_id"].duplicated().sum()),
        "missing_values": int(queries.isna().sum().sum()),
        "queries_without_entities": int((query_profile["entity_count"] == 0).sum()),
        "pct_without_entities": float((query_profile["entity_count"] == 0).mean()),
        "median_query_words": float(query_profile["query_word_count"].median()),
        "near_duplicate_pairs": len(near_duplicates),
        "manual_review_rows": len(manual_review),
        "top_languages": table_from_counts(queries["language"], "language").to_dict("records"),
        "language_examples": language_examples.to_dict("records"),
        "top_therapeutic_areas": table_from_counts(queries["therapeutic_area"], "therapeutic_area", 10).to_dict("records"),
    }


def audit_content(content: pd.DataFrame, paths: AuditPaths) -> dict[str, Any]:
    content_profile = content.copy()
    content_profile["entity_count"] = content_profile.apply(count_entities, axis=1)

    table_dir = paths.table_dir / "content"
    save_table(
        pd.DataFrame(
            [
                {"metric": "rows", "value": len(content)},
                {"metric": "unique_content_ids", "value": content["content_id"].nunique()},
                {"metric": "duplicate_content_ids", "value": int(content["content_id"].duplicated().sum())},
                {
                    "metric": "duplicate_normalized_titles",
                    "value": int(content["title"].map(normalize_text).duplicated().sum()),
                },
                {
                    "metric": "content_without_recognized_entities",
                    "value": int((content_profile["entity_count"] == 0).sum()),
                },
            ]
        ),
        table_dir / "content_core_metrics.csv",
    )
    save_table(missing_value_table(content), table_dir / "missing_values.csv")
    for column in [
        "content_type",
        "source_type",
        "language",
        "publication_year",
        "therapeutic_area",
        "disease_entity",
        "molecule_entity",
        "drug_class_entity",
    ]:
        save_table(table_from_counts(content[column], column), table_dir / f"{column}_distribution.csv")
    save_table(describe_numeric(content["word_count"], "word_count"), table_dir / "word_count_distribution.csv")
    save_table(table_from_counts(content_profile["entity_count"], "entity_count"), table_dir / "entity_count_distribution.csv")

    near_duplicates = find_near_duplicates(content, "content_id", "title", threshold=0.86)
    save_table(near_duplicates, paths.content_near_duplicates)

    matchable_dimensions = pd.DataFrame(
        [
            {"dimension": "language", "query_side": "available", "content_side": "available"},
            {"dimension": "therapeutic_area", "query_side": "available", "content_side": "available"},
            {"dimension": "disease_entity/icd10_code", "query_side": "available", "content_side": "available"},
            {"dimension": "molecule_entity/atc_code", "query_side": "available", "content_side": "available"},
            {"dimension": "drug_class_entity/atc_class", "query_side": "available", "content_side": "available"},
            {"dimension": "publication_year", "query_side": "extractable from text", "content_side": "available"},
            {"dimension": "age/pregnancy/renal/dose/etc.", "query_side": "extractable from text", "content_side": "title text only in raw file"},
            {"dimension": "content_type/source_type", "query_side": "inferable intent proxy", "content_side": "available"},
            {"dimension": "rank/position", "query_side": "not applicable", "content_side": "not in content; impression order can be inferred per session-query"},
        ]
    )
    save_table(matchable_dimensions, table_dir / "matchable_dimensions.csv")

    return {
        "rows": len(content),
        "unique_content_ids": content["content_id"].nunique(),
        "duplicate_content_ids": int(content["content_id"].duplicated().sum()),
        "missing_values": int(content.isna().sum().sum()),
        "median_word_count": float(content["word_count"].median()),
        "near_duplicate_pairs": len(near_duplicates),
        "content_type_distribution": table_from_counts(content["content_type"], "content_type").to_dict("records"),
        "source_type_distribution": table_from_counts(content["source_type"], "source_type", 12).to_dict("records"),
    }


def audit_behavioral_signals(behavioral: pd.DataFrame, paths: AuditPaths) -> dict[str, Any]:
    table_dir = paths.table_dir / "behavioral_signals"
    save_table(missing_value_table(behavioral), table_dir / "missing_values.csv")
    save_table(table_from_counts(behavioral["event_type"], "event_type"), table_dir / "event_type_frequency.csv")
    save_table(describe_numeric(behavioral["dwell_seconds"], "dwell_seconds"), table_dir / "dwell_time_distribution.csv")

    for column in ["query_id", "content_id", "doctor_id", "session_id"]:
        save_table(
            summarize_group_sizes(behavioral, column, f"events_per_{column.replace('_id', '')}"),
            table_dir / f"events_per_{column.replace('_id', '')}.csv",
        )

    event_dwell = (
        behavioral.groupby("event_type")["dwell_seconds"]
        .agg(["count", "mean", "median", "min", "max"])
        .round(2)
        .reset_index()
    )
    save_table(event_dwell, table_dir / "event_type_dwell_relationship.csv")

    repeated = (
        behavioral.groupby(["doctor_id", "query_id", "content_id"])
        .agg(event_count=("signal_id", "count"), event_types=("event_type", lambda values: "; ".join(sorted(set(values)))))
        .query("event_count > 1")
        .sort_values("event_count", ascending=False)
        .reset_index()
    )
    save_table(repeated, table_dir / "repeated_engagement.csv")

    suspicious = pd.concat(
        [
            behavioral[behavioral["dwell_seconds"] == 0].assign(reason="zero_dwell"),
            behavioral[behavioral["dwell_seconds"] > behavioral["dwell_seconds"].quantile(0.99)].assign(reason="above_p99_dwell"),
        ],
        ignore_index=True,
    )
    session_volume = behavioral.groupby("session_id").size()
    high_volume_sessions = set(session_volume[session_volume > session_volume.quantile(0.99)].index)
    suspicious = pd.concat(
        [
            suspicious,
            behavioral[behavioral["session_id"].isin(high_volume_sessions)].assign(reason="session_event_volume_above_p99"),
        ],
        ignore_index=True,
    ).drop_duplicates(["signal_id", "reason"])
    save_table(suspicious, paths.suspicious_behavior)

    duplicate_events = int(
        behavioral.duplicated(
            ["session_id", "doctor_id", "query_id", "content_id", "event_type", "event_timestamp"]
        ).sum()
    )

    return {
        "rows": len(behavioral),
        "missing_values": int(behavioral.isna().sum().sum()),
        "unique_sessions": behavioral["session_id"].nunique(),
        "unique_doctors": behavioral["doctor_id"].nunique(),
        "unique_queries": behavioral["query_id"].nunique(),
        "unique_content": behavioral["content_id"].nunique(),
        "duplicate_events": duplicate_events,
        "zero_dwell_events": int((behavioral["dwell_seconds"] == 0).sum()),
        "max_dwell_seconds": int(behavioral["dwell_seconds"].max()),
        "median_dwell_seconds": float(behavioral["dwell_seconds"].median()),
        "repeated_engagement_rows": len(repeated),
        "suspicious_rows": len(suspicious),
        "event_type_distribution": table_from_counts(behavioral["event_type"], "event_type").to_dict("records"),
    }


def audit_impressions(impressions: pd.DataFrame, behavioral: pd.DataFrame, paths: AuditPaths) -> dict[str, Any]:
    table_dir = paths.table_dir / "impressions"
    impressions_profile = impressions.sort_values(["session_id", "query_id", "timestamp_served"]).copy()
    impressions_profile["inferred_rank"] = impressions_profile.groupby(["session_id", "query_id"]).cumcount() + 1

    event_keys = ["session_id", "doctor_id", "query_id", "content_id"]
    engaged_keys = behavioral[event_keys].drop_duplicates().assign(has_engagement=True)
    joined = impressions_profile.merge(engaged_keys, on=event_keys, how="left")
    joined["has_engagement"] = joined["has_engagement"].eq(True)

    save_table(missing_value_table(impressions), table_dir / "missing_values.csv")
    for column in ["query_id", "session_id", "content_id"]:
        save_table(
            summarize_group_sizes(impressions, column, f"impressions_per_{column.replace('_id', '')}"),
            table_dir / f"impressions_per_{column.replace('_id', '')}.csv",
        )
    save_table(
        impressions["content_id"].value_counts().rename_axis("content_id").reset_index(name="impressions"),
        table_dir / "content_exposure_frequency.csv",
    )
    save_table(
        joined.groupby("inferred_rank")["has_engagement"]
        .agg(["count", "sum", "mean"])
        .rename(columns={"sum": "engaged_count", "mean": "engagement_rate"})
        .round(4)
        .reset_index(),
        table_dir / "engagement_by_inferred_rank.csv",
    )
    save_table(
        pd.DataFrame(
            [
                {"metric": "impressions", "value": len(impressions)},
                {"metric": "unique_impression_ids", "value": impressions["impression_id"].nunique()},
                {"metric": "duplicate_impression_ids", "value": int(impressions["impression_id"].duplicated().sum())},
                {"metric": "engaged_impressions", "value": int(joined["has_engagement"].sum())},
                {"metric": "unengaged_impressions", "value": int((~joined["has_engagement"]).sum())},
                {"metric": "pct_engaged", "value": round(float(joined["has_engagement"].mean()), 4)},
                {"metric": "pct_unengaged", "value": round(float((~joined["has_engagement"]).mean()), 4)},
                {"metric": "explicit_rank_column_available", "value": False},
            ]
        ),
        table_dir / "impression_core_metrics.csv",
    )

    return {
        "rows": len(impressions),
        "missing_values": int(impressions.isna().sum().sum()),
        "unique_sessions": impressions["session_id"].nunique(),
        "unique_queries": impressions["query_id"].nunique(),
        "unique_content": impressions["content_id"].nunique(),
        "duplicate_impression_ids": int(impressions["impression_id"].duplicated().sum()),
        "engaged_impressions": int(joined["has_engagement"].sum()),
        "unengaged_impressions": int((~joined["has_engagement"]).sum()),
        "pct_engaged": float(joined["has_engagement"].mean()),
        "pct_unengaged": float((~joined["has_engagement"]).mean()),
        "explicit_rank_column_available": False,
    }


def write_report(paths: AuditPaths, metrics: dict[str, Any]) -> None:
    query_language = pd.DataFrame(metrics["queries"]["top_languages"])
    query_language_examples = pd.DataFrame(metrics["queries"]["language_examples"])
    query_areas = pd.DataFrame(metrics["queries"]["top_therapeutic_areas"])
    content_types = pd.DataFrame(metrics["content"]["content_type_distribution"])
    event_types = pd.DataFrame(metrics["behavioral_signals"]["event_type_distribution"])

    lines = [
        "# Phase 1 Data Audit",
        "",
        "This audit profiles the four supplied raw datasets before label construction or modeling.",
        "",
        "## Dataset Inventory",
        "",
        markdown_table(
            pd.DataFrame(
                [
                    {"dataset": "queries.csv", **{k: metrics["queries"][k] for k in ["rows", "missing_values"]}},
                    {"dataset": "content.csv", **{k: metrics["content"][k] for k in ["rows", "missing_values"]}},
                    {
                        "dataset": "behavioral_signals.csv",
                        **{k: metrics["behavioral_signals"][k] for k in ["rows", "missing_values"]},
                    },
                    {
                        "dataset": "impressions.csv",
                        **{k: metrics["impressions"][k] for k in ["rows", "missing_values"]},
                    },
                ]
            )
        ),
        "",
        "## Queries",
        "",
        f"- Rows: {metrics['queries']['rows']}",
        f"- Unique query IDs: {metrics['queries']['unique_query_ids']}",
        f"- Duplicate query IDs: {metrics['queries']['duplicate_query_ids']}",
        f"- Missing values: {metrics['queries']['missing_values']}",
        f"- Median query length: {metrics['queries']['median_query_words']:.1f} words",
        f"- Queries without recognized disease/molecule/drug-class entities: {metrics['queries']['queries_without_entities']} ({metrics['queries']['pct_without_entities']:.1%})",
        f"- Near-duplicate/paraphrase candidate pairs at threshold: {metrics['queries']['near_duplicate_pairs']}",
        f"- Manual review sample rows: {metrics['queries']['manual_review_rows']}",
        "",
        "Language distribution:",
        "",
        markdown_table(query_language),
        "",
        "Language examples from supplied labels:",
        "",
        markdown_table(query_language_examples, max_rows=15),
        "",
        "Top therapeutic areas:",
        "",
        markdown_table(query_areas),
        "",
        "## Content",
        "",
        f"- Rows: {metrics['content']['rows']}",
        f"- Unique content IDs: {metrics['content']['unique_content_ids']}",
        f"- Duplicate content IDs: {metrics['content']['duplicate_content_ids']}",
        f"- Missing values: {metrics['content']['missing_values']}",
        f"- Median word count: {metrics['content']['median_word_count']:.1f}",
        f"- Near-duplicate title candidate pairs at threshold: {metrics['content']['near_duplicate_pairs']}",
        "",
        "Content-type distribution:",
        "",
        markdown_table(content_types),
        "",
        "Content-side dimensions that can support matching are saved in `tables/content/matchable_dimensions.csv`.",
        "",
        "## Behavioral Signals",
        "",
        f"- Events: {metrics['behavioral_signals']['rows']}",
        f"- Unique sessions/doctors/queries/content: {metrics['behavioral_signals']['unique_sessions']} / {metrics['behavioral_signals']['unique_doctors']} / {metrics['behavioral_signals']['unique_queries']} / {metrics['behavioral_signals']['unique_content']}",
        f"- Duplicate events on session-doctor-query-content-event-timestamp key: {metrics['behavioral_signals']['duplicate_events']}",
        f"- Median dwell seconds: {metrics['behavioral_signals']['median_dwell_seconds']:.1f}",
        f"- Max dwell seconds: {metrics['behavioral_signals']['max_dwell_seconds']}",
        f"- Zero-dwell events: {metrics['behavioral_signals']['zero_dwell_events']}",
        f"- Repeated doctor-query-content engagement rows: {metrics['behavioral_signals']['repeated_engagement_rows']}",
        f"- Suspicious pattern rows written: {metrics['behavioral_signals']['suspicious_rows']}",
        "",
        "Event-type distribution:",
        "",
        markdown_table(event_types),
        "",
        "## Impressions",
        "",
        f"- Impressions: {metrics['impressions']['rows']}",
        f"- Unique sessions/queries/content: {metrics['impressions']['unique_sessions']} / {metrics['impressions']['unique_queries']} / {metrics['impressions']['unique_content']}",
        f"- Duplicate impression IDs: {metrics['impressions']['duplicate_impression_ids']}",
        f"- Engaged impressions: {metrics['impressions']['engaged_impressions']} ({metrics['impressions']['pct_engaged']:.1%})",
        f"- Unengaged impressions: {metrics['impressions']['unengaged_impressions']} ({metrics['impressions']['pct_unengaged']:.1%})",
        "- No explicit rank/position column is present; rank-like position is inferred by timestamp within each session-query group for exploratory bias checks.",
        "",
        "Important label caveat: an unengaged impression should not be treated as automatically irrelevant because position bias, examination bias, answer satisfaction without click, competing relevant results, and limited session time can all produce non-engagement.",
        "",
        "## Phase 1 Takeaways",
        "",
        "- The raw files are complete by missing-value checks and have unique primary IDs.",
        "- Query and content both expose disease, molecule, drug class, therapeutic area, and language, so structured matching is feasible.",
        "- Query text contains contextual constraints such as age/pediatric, pregnancy, year, renal/hepatic function, dosing, comparisons, and prior treatment failure that are not represented in the supplied NER columns.",
        "- Behavioral labels should use graded evidence from event type and dwell time rather than binary clicked/not-clicked labels.",
        "- Impression order can support bias-aware analysis, but only via inferred rank from serving timestamps.",
        "",
        "## Artifacts",
        "",
        f"- Metrics JSON: `{paths.metrics}`",
        f"- Manual query review sample: `{paths.query_manual_review}`",
        f"- Query near duplicates: `{paths.query_near_duplicates}`",
        f"- Content near duplicates: `{paths.content_near_duplicates}`",
        f"- Suspicious behavioral rows: `{paths.suspicious_behavior}`",
        f"- Detailed tables: `{paths.table_dir}`",
        "",
    ]

    paths.report.parent.mkdir(parents=True, exist_ok=True)
    paths.report.write_text("\n".join(lines), encoding="utf-8")


def run_phase1_audit() -> AuditPaths:
    set_random_seed()
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    paths = AuditPaths(
        report=AUDIT_DIR / "phase1_data_audit.md",
        metrics=AUDIT_DIR / "phase1_metrics.json",
        query_manual_review=AUDIT_DIR / "phase1_query_manual_review.csv",
        query_near_duplicates=AUDIT_DIR / "phase1_query_near_duplicates.csv",
        content_near_duplicates=AUDIT_DIR / "phase1_content_near_duplicates.csv",
        suspicious_behavior=AUDIT_DIR / "phase1_suspicious_behavior.csv",
        table_dir=AUDIT_DIR / "tables",
    )
    data = load_all_raw()
    metrics = {
        "queries": audit_queries(data["queries"], paths),
        "content": audit_content(data["content"], paths),
        "behavioral_signals": audit_behavioral_signals(data["behavioral_signals"], paths),
        "impressions": audit_impressions(data["impressions"], data["behavioral_signals"], paths),
    }
    paths.metrics.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    write_report(paths, metrics)
    return paths


def main() -> None:
    paths = run_phase1_audit()
    print(f"Wrote Phase 1 audit report: {paths.report}")
    print(f"Wrote Phase 1 metrics: {paths.metrics}")
    print(f"Wrote manual query review: {paths.query_manual_review}")


if __name__ == "__main__":
    main()
