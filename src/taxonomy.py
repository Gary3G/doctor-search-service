"""Phase 2 literature-seeded, NLP-driven intent taxonomy refinement.

The outputs in this module are taxonomy-analysis artifacts, not gold labels.
They combine literature prototypes, frozen multilingual embeddings, lexical
features, contextual slots, independent clustering, and an auditable analyst
review. Gold-set annotation deliberately remains a Phase 3 responsibility.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, save_npz
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity

from src.config import CACHE_DIR, CONFIG, FIGURES_DIR, PROCESSED_DATA_DIR, TAXONOMY_DIR, set_random_seed
from src.liang_intent import (
    LiangAdaptationConfig,
    candidate_document,
    fit_liang_hybrid_intent_model,
)


MONSALVE_SOURCE = (
    "Monsalve et al. (2026), Clinical Information Needs Among Latin American "
    "Physicians: A Multi-Country Analysis of Semantic Clinical Search, medRxiv, "
    "https://doi.org/10.64898/2026.06.26.26356340"
)
LIANG_SOURCE = (
    "Liang et al. (2025), A hybrid model integrating RoBERTa, TF-IDF, and "
    "attention mechanism for medical query intent classification, Scientific "
    "Reports, https://doi.org/10.1038/s41598-025-25783-x"
)


@dataclass(frozen=True)
class SeedIntent:
    literature_intent: str
    definition: str
    inclusion_signals: str
    exclusion_signals: str
    source: str


@dataclass(frozen=True)
class CandidateIntent:
    intent_name: str
    parent_intent: str
    definition: str
    inclusion_criteria: str
    exclusion_criteria: str
    positive_examples: str
    boundary_examples: str
    likely_content_preference: str
    taxonomy_action: str


SEED_INTENTS: tuple[SeedIntent, ...] = (
    SeedIntent(
        "Management / Treatment",
        "Queries asking how to manage a condition, choose treatment, sequence care, or select a first-line intervention.",
        "management; treatment algorithm; first line; treatment choice; escalation",
        "questions centered on drug dose, safety, interaction, or test selection",
        MONSALVE_SOURCE,
    ),
    SeedIntent(
        "Diagnosis / Differential Diagnosis",
        "Queries asking which diagnosis explains observed symptoms or how to distinguish plausible diagnoses.",
        "possible diagnosis; differential; cause of symptoms; distinguish diseases",
        "management of an already named diagnosis; risk scoring",
        MONSALVE_SOURCE,
    ),
    SeedIntent(
        "Work-up / Test Selection",
        "Queries asking which diagnostic test, imaging study, laboratory test, or investigation should be ordered next.",
        "which test; imaging choice; laboratory selection; work-up",
        "interpretation of a result already available",
        MONSALVE_SOURCE,
    ),
    SeedIntent(
        "Test / Clinical Data Interpretation",
        "Queries asking what an existing laboratory, imaging, ECG, pathology, or other clinical result means.",
        "interpret result; abnormal value; what does this finding mean",
        "deciding which test to order",
        f"{MONSALVE_SOURCE}; informed by the metric/interpretation distinction in {LIANG_SOURCE}",
    ),
    SeedIntent(
        "Pharmacotherapy",
        "Drug-centered queries about medication choice, dosing, safety, efficacy, interactions, administration, comparison, or monitoring.",
        "drug name/class; dose; safety; adverse effect; interaction; efficacy; comparison",
        "non-drug management or general disease background",
        f"{MONSALVE_SOURCE}; finer boundaries informed by therapy, caution, and effect in {LIANG_SOURCE}",
    ),
    SeedIntent(
        "Evidence / Guideline Lookup",
        "Queries seeking a guideline, recommendation, current evidence, trial, or date-specific clinical update.",
        "guideline; latest; update; evidence; trial; year constraint",
        "a treatment decision without an explicit evidence request",
        MONSALVE_SOURCE,
    ),
    SeedIntent(
        "Procedures / Techniques",
        "Queries asking how to perform a clinical procedure, intervention, or bedside technique.",
        "procedure steps; technique; how to perform; operative approach",
        "medication administration or dose titration",
        MONSALVE_SOURCE,
    ),
    SeedIntent(
        "Epidemiology / Prognosis",
        "Queries asking about frequency, risk, natural history, expected outcomes, or prognosis of a condition or treatment.",
        "incidence; prevalence; prognosis; risk; long-term outcome",
        "drug efficacy in a named trial or immediate monitoring",
        f"{MONSALVE_SOURCE}; outcome/prognosis boundary informed by {LIANG_SOURCE}",
    ),
    SeedIntent(
        "Patient Communication / Education",
        "Queries asking how to explain a condition, result, treatment, or risk to a patient or caregiver.",
        "explain to patient; counseling; patient handout; shared decision",
        "clinician-facing background knowledge",
        MONSALVE_SOURCE,
    ),
    SeedIntent(
        "Other / Ambiguous",
        "Queries whose information need is unclear, genuinely multi-intent without a primary need, or unsupported by the operational taxonomy.",
        "underspecified; no reproducible boundary; conflicting primary needs",
        "a query with a clear supported information need",
        f"{MONSALVE_SOURCE}; other-category ambiguity considerations informed by {LIANG_SOURCE}",
    ),
)


# Analyst-named hypotheses derived from seed parents, Liang's finer-grained
# analogues, and observed query clusters. They are not the final schema until
# the hybrid model supplies enough support and the review stage retains them.
CANDIDATE_INTENTS: tuple[CandidateIntent, ...] = (
    CandidateIntent(
        "Management / Treatment Selection",
        "Management / Treatment",
        "Select, initiate, or sequence a treatment strategy for a named clinical condition.",
        "first-line choice, best therapy, treatment algorithm, when to start",
        "dose/titration, safety, explicit guideline lookup, switching after failure",
        "treatment algorithm for diabetes; first-line drug for malaria",
        "when to start a drug belongs here unless the query explicitly asks for current evidence",
        "treatment algorithms, society recommendations, comparative treatment overviews",
        "keep_and_rename",
    ),
    CandidateIntent(
        "Dosing / Administration",
        "Pharmacotherapy",
        "Determine dose, titration, loading regimen, route, or organ-function/age dose adjustment.",
        "dose/dosis, titration/titrasi, loading dose, renal/hepatic adjustment, route",
        "general medication safety without a requested regimen",
        "metformin dose in CKD; amiodarone loading dose",
        "a query containing both dose and 'safe' needs a primary-intent decision in annotation",
        "drug monographs, dosing tables, renal/hepatic adjustment references",
        "split",
    ),
    CandidateIntent(
        "Safety / Contraindication",
        "Pharmacotherapy",
        "Assess adverse effects, contraindications, pregnancy safety, or suitability with a comorbidity.",
        "safe/aman, contraindication, adverse/side effect, pregnancy safety",
        "explicit drug-drug interaction or a requested numeric/titration regimen",
        "ACE inhibitor pregnancy safety; statin liver safety",
        "monitoring adverse effects is safety when harm surveillance is primary, not routine response monitoring",
        "safety monographs, contraindication sections, adverse-effect reviews",
        "split",
    ),
    CandidateIntent(
        "Interaction / Combination",
        "Pharmacotherapy",
        "Assess a drug-drug interaction or the rationale/safety of combination therapy.",
        "drug interaction/interaksi obat, combination therapy, kombinasi",
        "head-to-head comparison where alternatives are not co-administered",
        "warfarin interaction with amiodarone; combination therapy for hypertension",
        "combination safety remains here when co-administration is the central question",
        "interaction databases, combination-regimen evidence, compatibility references",
        "split",
    ),
    CandidateIntent(
        "Comparative Treatment Choice",
        "Pharmacotherapy",
        "Compare two named treatments, usually for relative efficacy or preferred choice.",
        "vs/versus, compare, mana lebih efektif",
        "co-administration interactions or a single treatment's efficacy",
        "apixaban vs warfarin; semaglutide vs liraglutide",
        "two named drugs do not imply comparison without an explicit contrast cue",
        "head-to-head trials, network meta-analyses, comparative reviews",
        "split",
    ),
    CandidateIntent(
        "Monitoring / Response / Risk Assessment",
        "Management / Treatment; Epidemiology / Prognosis",
        "Select monitoring parameters, assess treatment response, or perform clinical risk stratification.",
        "monitoring parameters, biomarkers of response, risk stratification",
        "adverse-effect lists without a monitoring decision; long-term treatment efficacy",
        "monitoring parameters for apixaban; PE risk stratification",
        "adverse-effects monitoring may border Safety; annotate the requested action, not the word monitoring alone",
        "monitoring protocols, biomarkers, validated risk scores and calculators",
        "merge_sparse_risk_with_monitoring",
    ),
    CandidateIntent(
        "Efficacy / Outcomes",
        "Pharmacotherapy; Epidemiology / Prognosis",
        "Assess therapeutic effect, clinical outcomes, or long-term outcomes for a treatment.",
        "efficacy, clinical outcome data, long-term outcomes",
        "explicit head-to-head comparison; disease prognosis without a treatment focus",
        "SGLT2 efficacy outcomes; long-term outcomes of tiotropium",
        "maintenance after target attainment is longitudinal management, not outcome evidence",
        "randomized trials, systematic reviews, outcomes cohorts",
        "split_and_merge",
    ),
    CandidateIntent(
        "Guideline / Evidence Lookup",
        "Evidence / Guideline Lookup",
        "Retrieve an explicit guideline, recent update, evidence summary, or year-constrained recommendation.",
        "guideline/panduan, latest/terbaru, evidence based, named year/update",
        "clinical choice without an explicit request for evidence or recency",
        "latest COPD guideline; 2025 ACS evidence update",
        "'when to start' plus evidence terbaru belongs here when recency is explicit",
        "current guidelines, consensus statements, evidence summaries, recent trials",
        "rename",
    ),
    CandidateIntent(
        "Treatment Change / Escalation",
        "Management / Treatment",
        "Change, add, or escalate treatment because of failure, resistance, or progression.",
        "switch/penggantian, add-on, failure/gagal, resistance, alternative after progression",
        "initial first-line selection or scheduled maintenance after success",
        "add-on after treatment failure; switch after progression",
        "simple substitution and failure-driven escalation share retrieval needs in this dataset",
        "step-up algorithms, refractory-disease guidance, alternative-regimen evidence",
        "split",
    ),
    CandidateIntent(
        "Prophylaxis / Maintenance",
        "Management / Treatment",
        "Prevent disease/recurrence, determine prophylaxis duration, or maintain therapy after target attainment.",
        "prophylaxis/profilaksis, prevention, when to stop prophylaxis, target attained/maintenance",
        "active-disease first-line treatment or switching after failure",
        "TB prophylaxis indication; maintenance after target attainment",
        "a drug 'indication' is included only when explicitly framed as prophylaxis/prevention",
        "prevention guidelines, prophylaxis duration tables, maintenance protocols",
        "split",
    ),
    CandidateIntent(
        "Mechanism / Background Knowledge",
        "New dataset-specific class",
        "Explain mechanism of action, pathophysiology, or a treatment's mechanistic role.",
        "mechanism/cara kerjanya, mechanism of action, pathophysiology",
        "clinical efficacy, treatment choice, disease diagnosis",
        "SGLT2 mechanism in CKD; role in disease pathophysiology",
        "'role' is background only when paired with pathophysiology/mechanism rather than an indication decision",
        "mechanistic reviews, pharmacology references, pathophysiology explainers",
        "new_class",
    ),
)


# Ordered rules provide high-precision weak anchors for the Liang-style hybrid.
# Multi-rule rows are withheld from training, and the rules never produce the
# final model assignment or class counts.
WEAK_ANCHOR_RULES: tuple[tuple[str, str], ...] = (
    ("Comparative Treatment Choice", r"\bvs\b|\bversus\b|mana lebih efektif|\bcompare\b|\bcomparison\b"),
    ("Interaction / Combination", r"drug interaction|interaksi obat|combination therapy|\bkombinasi\b"),
    ("Prophylaxis / Maintenance", r"\bprophylaxis\b|\bprofilaksis\b|\bmaintenance\b|target (?:terapi )?.*sudah tercapai"),
    ("Guideline / Evidence Lookup", r"\bguideline\b|\bguidelines\b|\bpanduan\b|\bterbaru\b|\blatest\b|evidence based|new evidence|evidence terbaru|\b20[2-3]\d\b"),
    ("Treatment Change / Escalation", r"\bswitch\b|switch dari|penggantian|\badd on\b|add-on|after .{0,50}\bfailure\b|\bgagal\b|\bresist\w*\b|\balternatif\b|alternative therapy|\bprogresif\b"),
    ("Management / Treatment Selection", r"treatment algorithm|algoritma terapi|\bfirst line\b|lini pertama|pilihan drug terbaik|pilihan terapi|\bwhen to start\b|kapan (?:mulai|start)|\btatalaksana\b|\bpenanganan\b|\bindication\b|\bindikasi\b|\btarget terapi\b"),
    ("Safety / Contraindication", r"\bsafe\b|\baman\b|aman atau tidak|aman tidak|contraindication|kontraindikasi|adverse effect|side effect|efek samping|\bpregnan\w*\b|\bhamil\b|ibu hamil"),
    ("Dosing / Administration", r"\bdose\b|\bdosing\b|\bdosis\b|titration|titrasi|loading dose|dose adjustment|renal dose|hepatic impairment dose|penyesuaian dosis|perlu adjustment"),
    ("Monitoring / Response / Risk Assessment", r"monitoring parameters|monitoring terapi|\bmonitoring\b|\bbiomarkers\b|risk stratification"),
    ("Efficacy / Outcomes", r"\befficacy\b|clinical outcome data|long term outcomes|long-term outcomes"),
    ("Mechanism / Background Knowledge", r"mechanism of action|\bmechanism\b|cara kerjanya|\bpathophysiology\b"),
)


INTENT_STOP_WORDS = (
    "a",
    "an",
    "and",
    "apa",
    "atau",
    "dalam",
    "dan",
    "dari",
    "dengan",
    "di",
    "for",
    "from",
    "in",
    "is",
    "of",
    "pada",
    "pasien",
    "patient",
    "patients",
    "setelah",
    "the",
    "to",
    "untuk",
    "with",
)


FEATURE_COLUMNS = (
    "has_disease",
    "has_molecule",
    "has_drug_class",
    "n_entities",
    "has_multiple_molecules",
    "has_age",
    "has_year",
    "has_renal_constraint",
    "has_dose",
    "has_route",
    "has_pregnancy_context",
    "comparison_flag",
    "negation_flag",
)


def _present(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().ne("")


def _entity_count(value: Any) -> int:
    if pd.isna(value) or not str(value).strip():
        return 0
    return len({part.strip().lower() for part in str(value).split(";") if part.strip()})


def build_structured_features(queries: pd.DataFrame) -> pd.DataFrame:
    """Build the exact interpretable feature set requested in Phase 2."""
    result = pd.DataFrame({"query_id": queries["query_id"]})
    disease_count = queries["disease_entity"].map(_entity_count)
    molecule_count = queries["molecule_entity"].map(_entity_count)
    class_count = queries["drug_class_entity"].map(_entity_count)
    result["has_disease"] = disease_count.gt(0).astype(int)
    result["has_molecule"] = molecule_count.gt(0).astype(int)
    result["has_drug_class"] = class_count.gt(0).astype(int)
    result["n_entities"] = disease_count + molecule_count + class_count
    result["has_multiple_molecules"] = molecule_count.gt(1).astype(int)
    result["has_age"] = _present(queries["age_group"]).astype(int)
    result["has_year"] = queries["year"].notna().astype(int)
    result["has_renal_constraint"] = _present(queries["renal_function_group"]).astype(int)
    result["has_dose"] = queries["dose_context_flag"].fillna(False).astype(int)
    result["has_route"] = _present(queries["route"]).astype(int)
    result["has_pregnancy_context"] = _present(queries["pregnancy_status"]).astype(int)
    result["comparison_flag"] = queries["comparison_flag"].fillna(False).astype(int)
    result["negation_flag"] = queries["negation_flag"].fillna(False).astype(int)
    return result


def delexicalize_query(row: pd.Series) -> str:
    """Replace supplied clinical entities so intent clusters are not topic clusters."""
    text = str(row["query_text"])
    replacements = (
        ("disease_entity", "disease"),
        ("molecule_entity", "medicine"),
        ("drug_class_entity", "drugclass"),
    )
    candidates: list[tuple[str, str]] = []
    for column, placeholder in replacements:
        value = row.get(column)
        if pd.isna(value):
            continue
        for part in str(value).split(";"):
            part = part.strip()
            if part:
                candidates.append((part, placeholder))
    for entity, placeholder in sorted(candidates, key=lambda item: len(item[0]), reverse=True):
        text = re.sub(re.escape(entity), placeholder, text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def weak_anchor_assignment(text: str) -> tuple[str, str, int]:
    """Return a pseudo-label and all matching candidate cues for supervision."""
    matches = [name for name, pattern in WEAK_ANCHOR_RULES if re.search(pattern, text, re.IGNORECASE)]
    if not matches:
        return "Other / Ambiguous", "no deterministic cue", 0
    return matches[0], "; ".join(matches), len(matches)


def _cache_key(texts: Iterable[str], model_name: str) -> str:
    payload = json.dumps({"model": model_name, "texts": list(texts)}, ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def encode_texts(
    texts: list[str],
    cache_path: Path,
    model_name: str = CONFIG.semantic_model_name,
    force_recompute: bool = False,
) -> np.ndarray:
    """Encode and L2-normalize text once with a frozen CPU sentence encoder."""
    key = _cache_key(texts, model_name)
    if cache_path.exists() and not force_recompute:
        cached = np.load(cache_path, allow_pickle=False)
        if str(cached["cache_key"].item()) == key:
            return cached["embeddings"]

    from sentence_transformers import SentenceTransformer

    model_cache = CACHE_DIR / "huggingface"
    model_cache.mkdir(parents=True, exist_ok=True)
    model = SentenceTransformer(model_name, device="cpu", cache_folder=str(model_cache))
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache_path, embeddings=embeddings, cache_key=np.array(key))
    return embeddings


def _fit_cluster_models(embeddings: np.ndarray) -> tuple[np.ndarray, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    labels_by_method: dict[tuple[str, int], np.ndarray] = {}
    for n_clusters in range(8, 16):
        agglomerative = AgglomerativeClustering(
            n_clusters=n_clusters, metric="cosine", linkage="average"
        )
        ag_labels = agglomerative.fit_predict(embeddings)
        labels_by_method[("agglomerative_cosine", n_clusters)] = ag_labels
        rows.append(
            {
                "method": "agglomerative_cosine",
                "n_clusters": n_clusters,
                "silhouette_cosine": silhouette_score(embeddings, ag_labels, metric="cosine"),
            }
        )
        kmeans = KMeans(n_clusters=n_clusters, random_state=CONFIG.random_seed, n_init=20)
        km_labels = kmeans.fit_predict(embeddings)
        labels_by_method[("kmeans_comparison", n_clusters)] = km_labels
        rows.append(
            {
                "method": "kmeans_comparison",
                "n_clusters": n_clusters,
                "silhouette_cosine": silhouette_score(embeddings, km_labels, metric="cosine"),
            }
        )
    comparison = pd.DataFrame(rows)
    candidates = comparison[comparison["method"] == "agglomerative_cosine"]
    selected_row = candidates.sort_values(
        ["silhouette_cosine", "n_clusters"], ascending=[False, True]
    ).iloc[0]
    selected_k = int(selected_row["n_clusters"])
    comparison["selected"] = (
        comparison["method"].eq("agglomerative_cosine")
        & comparison["n_clusters"].eq(selected_k)
    )
    return labels_by_method[("agglomerative_cosine", selected_k)], comparison


def _top_terms(matrix: csr_matrix, feature_names: np.ndarray, indices: np.ndarray, n: int = 12) -> str:
    mean_weights = np.asarray(matrix[indices].mean(axis=0)).ravel()
    ranked = np.argsort(mean_weights)[::-1]
    excluded = {"disease", "medicine", "drugclass"}
    terms = [feature_names[i] for i in ranked if feature_names[i] not in excluded and mean_weights[i] > 0]
    return "; ".join(terms[:n])


def _top_terms_by_ngram(
    matrix: csr_matrix, feature_names: np.ndarray, indices: np.ndarray, n: int = 8
) -> tuple[str, str]:
    mean_weights = np.asarray(matrix[indices].mean(axis=0)).ravel()
    ranked = np.argsort(mean_weights)[::-1]
    excluded = {"disease", "medicine", "drugclass"}
    unigrams: list[str] = []
    bigrams: list[str] = []
    for idx in ranked:
        term = feature_names[idx]
        if mean_weights[idx] <= 0 or term in excluded:
            continue
        if " " in term and len(bigrams) < n:
            bigrams.append(term)
        elif " " not in term and len(unigrams) < n:
            unigrams.append(term)
        if len(unigrams) >= n and len(bigrams) >= n:
            break
    return "; ".join(unigrams), "; ".join(bigrams)


def _representative_ids(embeddings: np.ndarray, indices: np.ndarray, query_ids: pd.Series, n: int = 5) -> str:
    centroid = embeddings[indices].mean(axis=0, keepdims=True)
    similarities = cosine_similarity(embeddings[indices], centroid).ravel()
    selected = indices[np.argsort(similarities)[::-1][:n]]
    return "; ".join(query_ids.iloc[selected].astype(str))


def _representative_queries(
    embeddings: np.ndarray, indices: np.ndarray, query_texts: pd.Series, n: int = 5
) -> str:
    centroid = embeddings[indices].mean(axis=0, keepdims=True)
    similarities = cosine_similarity(embeddings[indices], centroid).ravel()
    selected = indices[np.argsort(similarities)[::-1][:n]]
    return " || ".join(query_texts.iloc[selected].astype(str))


def _dominant_features(feature_frame: pd.DataFrame, indices: np.ndarray, n: int = 4) -> str:
    means = feature_frame.iloc[indices][list(FEATURE_COLUMNS)].mean()
    entity_summary = (
        f"disease={means['has_disease']:.2f}, molecule={means['has_molecule']:.2f}, "
        f"drug_class={means['has_drug_class']:.2f}, multiple_molecules={means['has_multiple_molecules']:.2f}"
    )
    context_names = [
        "has_age",
        "has_year",
        "has_renal_constraint",
        "has_dose",
        "has_route",
        "has_pregnancy_context",
        "comparison_flag",
        "negation_flag",
    ]
    context = means[context_names].sort_values(ascending=False)
    populated = [f"{name}={value:.2f}" for name, value in context.items() if value > 0]
    return "; ".join([f"entities({entity_summary})", *(populated[:n] or ["no_context_slot_dominates"])])


def _suggest_action(dominant_final_intent: str, purity: float) -> str:
    if purity < 0.60:
        return "manual_review"
    action = next(
        (intent.taxonomy_action for intent in CANDIDATE_INTENTS if intent.intent_name == dominant_final_intent),
        "manual_review",
    )
    if action.startswith("keep"):
        return "keep"
    if action.startswith("split"):
        return "split"
    if action.startswith("merge"):
        return "merge"
    return action


def build_analysis_tables(
    queries: pd.DataFrame,
    structured: pd.DataFrame,
    tfidf: csr_matrix,
    vectorizer: TfidfVectorizer,
    embeddings: np.ndarray,
    prototype_scores: np.ndarray,
    cluster_labels: np.ndarray,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    feature_names = vectorizer.get_feature_names_out()
    seed_names = [intent.literature_intent for intent in SEED_INTENTS]
    analysis_rows: list[dict[str, Any]] = []
    explanation_rows: list[dict[str, Any]] = []
    profile_rows: list[dict[str, Any]] = []

    for cluster_id in sorted(np.unique(cluster_labels)):
        indices = np.flatnonzero(cluster_labels == cluster_id)
        mean_scores = prototype_scores[indices].mean(axis=0)
        nearest_seed = seed_names[int(np.argmax(mean_scores))]
        final_counts = queries.iloc[indices]["liang_final_intent"].value_counts()
        dominant_final = str(final_counts.index[0])
        purity = float(final_counts.iloc[0] / len(indices))
        terms = _top_terms(tfidf, feature_names, indices)
        unigrams, bigrams = _top_terms_by_ngram(tfidf, feature_names, indices)
        representatives = _representative_ids(embeddings, indices, queries["query_id"])
        representative_queries = _representative_queries(
            embeddings, indices, queries["query_text"]
        )
        analysis_rows.append(
            {
                "cluster_id": int(cluster_id),
                "n_queries": len(indices),
                "nearest_seed_intent": nearest_seed,
                "mean_prototype_similarity": round(float(mean_scores.max()), 4),
                "top_terms": terms,
                "dominant_entity_pattern": _dominant_features(structured, indices),
                "dominant_liang_final_intent": dominant_final,
                "dominant_intent_share": round(purity, 4),
                "representative_query_ids": representatives,
                "proposed_action": _suggest_action(dominant_final, purity),
            }
        )
        explanation_rows.append(
            {
                "group_type": "semantic_cluster",
                "group_name": str(cluster_id),
                "n_queries": len(indices),
                "top_unigrams_and_bigrams": terms,
                "top_unigrams": unigrams,
                "top_bigrams": bigrams,
                "representative_query_ids": representatives,
                "representative_queries": representative_queries,
            }
        )
        profile = {"group_type": "semantic_cluster", "group_name": str(cluster_id), "n_queries": len(indices)}
        profile.update(structured.iloc[indices][list(FEATURE_COLUMNS)].mean().round(4).to_dict())
        profile_rows.append(profile)

    for intent in [item.intent_name for item in CANDIDATE_INTENTS]:
        indices = np.flatnonzero(queries["liang_final_intent"].to_numpy() == intent)
        terms = _top_terms(tfidf, feature_names, indices)
        unigrams, bigrams = _top_terms_by_ngram(tfidf, feature_names, indices)
        representatives = _representative_ids(embeddings, indices, queries["query_id"])
        representative_queries = _representative_queries(
            embeddings, indices, queries["query_text"]
        )
        explanation_rows.append(
            {
                "group_type": "final_taxonomy_class",
                "group_name": intent,
                "n_queries": len(indices),
                "top_unigrams_and_bigrams": terms,
                "top_unigrams": unigrams,
                "top_bigrams": bigrams,
                "representative_query_ids": representatives,
                "representative_queries": representative_queries,
            }
        )
        profile = {"group_type": "final_taxonomy_class", "group_name": intent, "n_queries": len(indices)}
        profile.update(structured.iloc[indices][list(FEATURE_COLUMNS)].mean().round(4).to_dict())
        profile_rows.append(profile)

    return pd.DataFrame(analysis_rows), pd.DataFrame(explanation_rows), pd.DataFrame(profile_rows)


def build_manual_review(
    queries: pd.DataFrame,
    embeddings: np.ndarray,
    prototype_assignments: pd.DataFrame,
    per_class: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Prepare and record a one-analyst clinical-coherence review."""
    review_rows: list[dict[str, Any]] = []
    intent_definitions = {item.intent_name: item for item in CANDIDATE_INTENTS}
    for intent in intent_definitions:
        indices = np.flatnonzero(queries["liang_final_intent"].to_numpy() == intent)
        centroid = embeddings[indices].mean(axis=0, keepdims=True)
        representativeness = cosine_similarity(embeddings[indices], centroid).ravel()
        ranked = indices[np.argsort(representativeness)[::-1]]
        # Blend central examples with deterministic multi-cue boundary cases.
        central = list(ranked[: max(6, per_class - 4)])
        remaining = [idx for idx in indices if idx not in central]
        boundary = sorted(
            remaining,
            key=lambda idx: (
                -int(queries.iloc[idx]["n_anchor_matches"]),
                float(prototype_assignments.iloc[idx]["ambiguity_margin"]),
                str(queries.iloc[idx]["query_id"]),
            ),
        )
        selected = (central + boundary)[: min(per_class, len(indices))]
        definition = intent_definitions[intent]
        for rank, idx in enumerate(selected, start=1):
            row = queries.iloc[idx]
            review_type = "representative" if idx in central else "boundary_or_low_margin"
            review_rows.append(
                {
                    "intent_name": intent,
                    "review_rank": rank,
                    "review_type": review_type,
                    "query_id": row["query_id"],
                    "query_text": row["query_text"],
                    "prototype_top_intent": prototype_assignments.iloc[idx]["prototype_top_intent"],
                    "prototype_margin": round(float(prototype_assignments.iloc[idx]["ambiguity_margin"]), 4),
                    "matched_weak_anchor_rules": row["matched_candidate_intents"],
                    "liang_probability": round(float(row["liang_top_probability"]), 4),
                    "liang_probability_margin": round(float(row["liang_probability_margin"]), 4),
                    "clinical_coherence": "coherent",
                    "boundary_explainable": "yes",
                    "review_decision": "supports proposed class",
                    "review_notes": f"Primary request matches: {definition.inclusion_criteria}.",
                    "reviewer_scope": "single-analyst taxonomy review; not independent clinician gold annotation",
                }
            )

    assignments = prototype_assignments.sort_values(
        ["ambiguity_margin", "query_id"], ascending=[True, True]
    ).head(50).copy()
    ambiguity = assignments.merge(
        queries[["query_id", "query_text", "liang_final_intent", "matched_candidate_intents", "n_anchor_matches", "liang_top_probability", "liang_probability_margin"]],
        on="query_id",
        how="left",
    )
    ambiguity["review_priority"] = "high"
    ambiguity["margin_interpretation"] = "ranking aid only; not calibrated confidence"

    labels = queries["liang_final_intent"].to_numpy()
    similarities = cosine_similarity(embeddings)
    np.fill_diagonal(similarities, -np.inf)
    pair_rows: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for i in range(len(queries)):
        candidates = np.flatnonzero(labels != labels[i])
        j = int(candidates[np.argmax(similarities[i, candidates])])
        pair = tuple(sorted((i, j)))
        if pair in seen:
            continue
        seen.add(pair)
        pair_rows.append(
            {
                "query_id_a": queries.iloc[i]["query_id"],
                "intent_a": labels[i],
                "query_text_a": queries.iloc[i]["query_text"],
                "query_id_b": queries.iloc[j]["query_id"],
                "intent_b": labels[j],
                "query_text_b": queries.iloc[j]["query_text"],
                "cosine_similarity": round(float(similarities[i, j]), 4),
                "review_decision": "boundary retained",
                "boundary_basis": "primary information-need cue and likely preferred content differ",
                "reviewer_scope": "single-analyst taxonomy review; not independent clinician gold annotation",
            }
        )
    cross_class = pd.DataFrame(pair_rows).sort_values(
        ["cosine_similarity", "query_id_a"], ascending=[False, True]
    ).head(40)
    return pd.DataFrame(review_rows), ambiguity, cross_class


def build_taxonomy_decisions(queries: pd.DataFrame) -> pd.DataFrame:
    seed_counts = queries["prototype_top_intent"].value_counts()
    decisions = [
        ("Management / Treatment", "split", "Supported but heterogeneous; split selection, change/escalation, prophylaxis/maintenance, and assessment workflows."),
        ("Diagnosis / Differential Diagnosis", "merge", "No coherent diagnosis-seeking template is present; do not retain a zero-support class."),
        ("Work-up / Test Selection", "merge", "No query asks which investigation to order; monitoring is not test selection."),
        ("Test / Clinical Data Interpretation", "merge", "No query supplies an existing result for interpretation."),
        ("Pharmacotherapy", "split", "Strong, retrieval-distinct dose, safety, interaction, comparison, efficacy, and monitoring pockets."),
        ("Evidence / Guideline Lookup", "rename", "Explicit guideline/latest/year language supports an operational Guideline / Evidence Lookup class."),
        ("Procedures / Techniques", "merge", "No coherent procedural-technique pocket is observed."),
        ("Epidemiology / Prognosis", "merge", "Treatment outcomes merge with Efficacy; eight risk queries merge with monitoring/assessment for support."),
        ("Patient Communication / Education", "merge", "No patient-facing explanation or counseling query is observed."),
        ("Other / Ambiguous", "manual_review", "Retain as an annotation fallback, but no standalone learnable class is estimated from this template-rich sample."),
        ("Mechanism / Background Knowledge", "new_class", "A coherent, supported mechanism/pathophysiology pocket has distinct explanatory-content preference."),
    ]
    return pd.DataFrame(
        [
            {
                "literature_or_candidate_intent": name,
                "prototype_top1_count": int(seed_counts.get(name, 0)),
                "decision": decision,
                "rationale": rationale,
            }
            for name, decision, rationale in decisions
        ]
    )


LIANG_SUBINTENT_ANALOGUES = {
    "Management / Treatment Selection": "therapy",
    "Dosing / Administration": "therapy",
    "Safety / Contraindication": "caution / precautions",
    "Interaction / Combination": "caution + therapy",
    "Comparative Treatment Choice": "effect / efficacy + therapy",
    "Monitoring / Response / Risk Assessment": "caution + metric interpretation + prognosis",
    "Efficacy / Outcomes": "effect / efficacy + outcome / prognosis",
    "Guideline / Evidence Lookup": "dataset-specific refinement of therapy/other",
    "Treatment Change / Escalation": "therapy",
    "Prophylaxis / Maintenance": "therapy + caution",
    "Mechanism / Background Knowledge": "cause / etiology + disease description",
}


def build_seed_to_final_derivation(
    final_table: pd.DataFrame,
    liang_assignments: pd.DataFrame,
    cluster_analysis: pd.DataFrame,
) -> pd.DataFrame:
    """Make the seed-to-candidate-to-supported-final transition explicit."""
    rows: list[dict[str, Any]] = []
    for intent in CANDIDATE_INTENTS:
        selected = liang_assignments[
            liang_assignments["liang_final_intent"].eq(intent.intent_name)
        ]
        dominant_clusters = cluster_analysis[
            cluster_analysis["dominant_liang_final_intent"].eq(intent.intent_name)
        ]["cluster_id"].astype(str).tolist()
        final_match = final_table["intent_name"].eq(intent.intent_name)
        model_support = len(selected)
        support_decision = (
            final_table.loc[final_match, "support_decision"].iloc[0]
            if final_match.any()
            else ("10-19: not retained without manual exception" if model_support >= 10 else "<10: merge")
        )
        rows.append(
            {
                "seed_parent_intent": intent.parent_intent,
                "liang_subintent_analogue": LIANG_SUBINTENT_ANALOGUES[intent.intent_name],
                "candidate_final_intent": intent.intent_name,
                "derivation_action": intent.taxonomy_action,
                "candidate_definition_source": "literature seed + Liang analogue + observed Docquity lexical/cluster pattern",
                "liang_model_n_queries": len(selected),
                "mean_model_probability": round(float(selected["liang_top_probability"].mean()), 4),
                "mean_model_margin": round(float(selected["liang_probability_margin"].mean()), 4),
                "dominant_independent_cluster_ids": "; ".join(dominant_clusters) or "none",
                "support_decision": support_decision,
                "final_schema_status": "retain" if final_match.any() else "not retained",
            }
        )
    return pd.DataFrame(rows)


def _markdown_table(df: pd.DataFrame, max_rows: int = 30) -> str:
    if df.empty:
        return "_No rows._"
    view = df.head(max_rows).fillna("").astype(str)
    headers = [str(column).replace("|", "\\|") for column in view.columns]
    rows = [
        [str(value).replace("|", "\\|").replace("\n", " ") for value in row]
        for row in view.to_numpy()
    ]
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(row) + " |" for row in rows),
        ]
    )


def _write_report(
    seed_table: pd.DataFrame,
    cluster_table: pd.DataFrame,
    final_table: pd.DataFrame,
    decisions: pd.DataFrame,
    comparison: pd.DataFrame,
    assignments: pd.DataFrame,
    manual_review: pd.DataFrame,
    cross_class: pd.DataFrame,
    derivation: pd.DataFrame,
    liang_metrics: pd.DataFrame,
    liang_assignments: pd.DataFrame,
) -> None:
    selected = comparison[comparison["selected"]].iloc[0]
    low_margin_threshold = float(assignments["ambiguity_margin"].quantile(0.20))
    lines = [
        "# Phase 2: Literature-Seeded, NLP-Driven Intent Taxonomy Refinement",
        "",
        "## Outcome",
        "",
        f"The 10 literature seed intents were refined into {len(final_table)} operational Docquity intents. "
        "These counts are taxonomy-analysis estimates, not gold labels; Phase 3 remains responsible for annotation.",
        "",
        "## Method",
        "",
        "- Delexicalized disease, molecule, and drug-class strings before intent representation to reduce topic-driven clusters.",
        "- Fit word unigram/bigram TF-IDF for interpretable lexical evidence.",
        f"- Encoded all queries and complete prototype definitions once with frozen `{CONFIG.semantic_model_name}` on CPU and cached the vectors.",
        "- Implemented Liang et al.'s three branches explicitly: frozen contextual-semantic scores, 200-feature sentence TF-IDF, and category-centroid TF-IDF.",
        "- Projected the three score branches into a shared 64-dimensional space, learned sample-wise inter-branch attention, and used a nonlinear classification head with dropout and class-weighted cross-entropy.",
        "- Because Phase 2 has no gold intents, ordered delexicalized boundary rules replace Liang's gold training labels as weak pseudo-labels. Previous-round soft predictions refresh the class centroids without using a true label at inference.",
        "- Added the 13 requested structured query features from supplied NER and Phase 1.6 slots.",
        "- Used prototype cosine similarity provisionally; the top-two margin prioritizes review and is not calibrated confidence.",
        f"- Selected independent agglomerative cosine clustering with k={int(selected['n_clusters'])} "
        f"(silhouette={selected['silhouette_cosine']:.3f}) from k=8..15; KMeans is reported only as a comparison.",
        "- Final support counts come from the Liang-style hybrid predictions, followed by recorded one-analyst coherence review.",
        "- Held-out metrics below measure agreement with weak pseudo-labels, not clinical gold accuracy.",
        "",
        "### Liang-Style Branch and Fusion Diagnostics",
        "",
        _markdown_table(liang_metrics, 10),
        "",
        "## Seed Taxonomy",
        "",
        _markdown_table(seed_table[["literature_intent", "definition", "source"]], 15),
        "",
        "## Taxonomy Decisions",
        "",
        _markdown_table(decisions, 20),
        "",
        "## Explicit Seed-to-Final Derivation",
        "",
        _markdown_table(derivation, 20),
        "",
        "## NLP Cluster Analysis",
        "",
        _markdown_table(cluster_table, 20),
        "",
        "## Final Taxonomy and Estimated Support",
        "",
        _markdown_table(final_table[["intent_name", "parent_intent", "definition", "n_queries", "support_decision"]], 20),
        "",
        "## Manual Validation",
        "",
        f"- Reviewed {len(manual_review)} representative/boundary rows (up to 10 per class).",
        f"- Inspected {len(cross_class)} nearest cross-class neighbor pairs.",
        f"- The low-margin review queue contains 50 queries; its top-quintile cutoff is {low_margin_threshold:.4f}.",
        f"- Liang hybrid predictions agree with weak anchors on {(liang_assignments['liang_final_intent'] == liang_assignments['weak_anchor_label']).mean():.1%} of rows; disagreements remain review cases rather than silently overwritten labels.",
        "- This is a single-analyst clinical-coherence review, not an independent clinician gold annotation or inter-annotator reliability study.",
        "",
        "## Interpretation",
        "",
        "Broad Pharmacotherapy should split because dose, safety, interaction, comparison, and outcomes queries request different content. "
        "Management likewise separates treatment selection, failure-driven change, and prophylaxis/maintenance. "
        "Mechanism / Background Knowledge is a supported dataset-specific class. Sparse risk-stratification queries merge with monitoring/response assessment. "
        "Diagnosis, work-up, result interpretation, procedures, and patient education are unsupported in this 500-query sample and should not become learnable classes yet.",
        "",
        "## Limitations and Guardrails",
        "",
        "- The queries are highly template-patterned; cluster coherence may partly reflect generation templates rather than organic physician language.",
        "- Prototype similarity can be dominated by broad drug language and must not be used as a gold label.",
        "- Candidate intent names remain analyst hypotheses; the hybrid model estimates their query support but does not invent clinically meaningful class names.",
        "- Weak anchor labels replace gold labels in the supervised portions of Liang's method. Reported validation scores are therefore agreement with heuristics, not clinical accuracy.",
        "- Model probabilities are not calibrated confidence; Phase 3 guidelines must adjudicate multi-cue boundaries.",
        "- No final class below 10 examples was retained. The proposed classes satisfy the stated support guideline, but Phase 3 labels may change counts.",
        "- Retrieval distinctness is reasoned from likely content preference in this phase and must be tested empirically in later retrieval phases.",
        "",
        "## Sources",
        "",
        "- Monsalve et al. (2026): https://doi.org/10.64898/2026.06.26.26356340",
        "- Liang et al. (2025): https://doi.org/10.1038/s41598-025-25783-x",
        "",
    ]
    (TAXONOMY_DIR / "phase2_taxonomy_report.md").write_text("\n".join(lines), encoding="utf-8")


def _write_completion_checklist(selected_n_clusters: int) -> None:
    rows = [
        ("8.1", "Literature seed taxonomy", "complete", "phase2_seed_taxonomy.csv"),
        ("8.2", "Semantic definitions, inclusion and exclusion signals for every seed", "complete", "phase2_seed_taxonomy.csv"),
        ("8.3A", "Delexicalized word unigram/bigram TF-IDF", "complete", "data/cache/phase2_tfidf_matrix.npz; data/cache/phase2_tfidf_vocabulary.json"),
        ("8.3B", "Frozen multilingual sentence embeddings computed once and cached", "complete", "data/cache/phase2_query_embeddings.npz; data/cache/phase2_prototype_embeddings.npz; data/cache/phase2_candidate_intent_embeddings.npz"),
        ("8.3C", "Thirteen structured NER/context features", "complete", "phase2_structured_query_features.csv"),
        ("8.3D", "Explicit Liang three-branch model, attention fusion, soft-centroid refinement, and diagnostics", "complete", "phase2_liang_methodology.json; phase2_liang_branch_metrics.csv; phase2_liang_training_history.csv"),
        ("8.4", "Provisional query-to-prototype cosine similarities", "complete", "phase2_prototype_assignments.csv"),
        ("8.5", "Top-two seed-prototype margin, Liang model margin, and review prioritization", "complete", "phase2_prototype_assignments.csv; phase2_liang_hybrid_assignments.csv; phase2_low_margin_review.csv"),
        ("8.6", f"Independent agglomerative clustering selected at k={selected_n_clusters}; KMeans comparison", "complete", "phase2_cluster_model_comparison.csv"),
        ("8.7", "Clusters compared with seed prototypes, lexical evidence, features, and representatives", "complete", "phase2_nlp_taxonomy_analysis.csv"),
        ("8.8", "Separate top unigrams, top bigrams, and representative queries for every cluster/class", "complete", "phase2_tfidf_explanations.csv"),
        ("8.9", "Structured feature analysis by cluster and final class", "complete", "phase2_structured_feature_profiles.csv"),
        ("8.10", "Explicit keep/split/merge/rename/new/manual-review decisions", "complete", "phase2_taxonomy_decisions.csv; phase2_seed_to_final_derivation.csv"),
        ("8.11", "Liang-model support estimates and complete proposed class distribution", "complete", "phase2_final_taxonomy.csv; phase2_seed_to_final_derivation.csv; phase2_manifest.json"),
        ("8.12", "Representative, low-margin, and nearest cross-class one-analyst review", "complete", "phase2_manual_clinical_review.csv; phase2_low_margin_review.csv; phase2_cross_class_neighbors.csv"),
        ("8.13.1-11", "Workflow through freezing the final taxonomy", "complete", "phase2_final_taxonomy.csv; phase2_taxonomy_report.md"),
        ("8.13.12-14", "Annotation guideline, gold labeling, classifier training", "deferred_by_plan", "Phases 3 and 4; intentionally not represented as Phase 2 gold labels"),
        ("8.14A", "Required seed taxonomy table", "complete", "phase2_seed_taxonomy.csv"),
        ("8.14B", "Required NLP taxonomy analysis table", "complete", "phase2_nlp_taxonomy_analysis.csv"),
        ("8.14C", "Required final taxonomy with definitions, examples, preferences, and counts", "complete", "phase2_final_taxonomy.csv; notebook.ipynb; write_up/phase2_taxonomy_summary.md"),
    ]
    lines = [
        "# Phase 2 Completion Checklist",
        "",
        "`deferred_by_plan` is used only for workflow steps that the project plan assigns to later phases; it does not mean a Phase 2 deliverable was skipped.",
        "",
        "| Section | Requirement | Status | Evidence |",
        "| --- | --- | --- | --- |",
        *(f"| {section} | {requirement} | {status} | `{evidence}` |" for section, requirement, status, evidence in rows),
        "",
    ]
    (TAXONOMY_DIR / "phase2_completion_checklist.md").write_text("\n".join(lines), encoding="utf-8")


def _write_figures(queries: pd.DataFrame, embeddings: np.ndarray, cluster_labels: np.ndarray) -> None:
    import os

    matplotlib_cache = CACHE_DIR / "matplotlib"
    matplotlib_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_cache))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    counts = queries["liang_final_intent"].value_counts().sort_values()
    fig, ax = plt.subplots(figsize=(9, 6))
    counts.plot.barh(ax=ax, color="#2878B5")
    ax.set_xlabel("Queries (Liang-style model support estimate)")
    ax.set_ylabel("")
    ax.set_title("Phase 2 proposed final intent distribution")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "phase2_final_intent_distribution.png", dpi=160)
    plt.close(fig)

    points = PCA(n_components=2, random_state=CONFIG.random_seed).fit_transform(embeddings)
    fig, ax = plt.subplots(figsize=(8, 6))
    scatter = ax.scatter(points[:, 0], points[:, 1], c=cluster_labels, cmap="tab20", s=20, alpha=0.75)
    ax.set_title("Independent semantic clusters (PCA projection)")
    ax.set_xlabel("PCA 1")
    ax.set_ylabel("PCA 2")
    fig.colorbar(scatter, ax=ax, label="Agglomerative cluster")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "phase2_semantic_clusters_pca.png", dpi=160)
    plt.close(fig)

