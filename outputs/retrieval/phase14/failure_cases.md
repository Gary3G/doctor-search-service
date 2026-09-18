# Phase 14: detailed residual failure analysis

This is a purposive review of 12 eligible temporal-test top-10 misses from the frozen Phase 12 runtime ranker (`with_predicted_hard_intent`). Cases cover compositional, contextual, intent, corpus-coverage, and evaluation-proxy failures; their frequencies are not prevalence estimates. Titles and supplied metadata are available, not article bodies. An LLM-assisted review produced the semantic assessments; no clinician adjudication occurred. Unjudged means unobserved in the behavior logs, not irrelevant. No model or label was changed.

## Q019: Rheumatoid Arthritis dengan renal impairment penyesuaian dosis Bortezomib

**Expected relevant content:** Renal dose-adjustment guidance for bortezomib in rheumatoid arthritis; C220 is the closest title-level drug-and-disease match but does not mention renal dosing.

**Retrieved content:** #1 C040: Dose Adjustment of Atorvastatin in Renal and Hepatic Impairment | #2 C231: Dose Adjustment of Apixaban in Renal and Hepatic Impairment | #3 C343: Dose Adjustment of Dupilumab in Renal and Hepatic Impairment

**Query decomposition:** `{"disease_entity": "Rheumatoid Arthritis", "dose_context_flag": true, "drug_class_entity": "Proteasome inhibitors", "molecule_entity": "Bortezomib", "predicted_intent": "Dosing / Administration", "renal_function_group": "renal_impairment"}`

**Why retrieval failed:** The renal-dose template dominates the score, so ten dose-adjustment articles for other molecules precede the closest bortezomib/rheumatoid-arthritis item. No title satisfies drug, disease, and renal-dose intent together.

**What could improve it:** Require molecule and disease compatibility before applying a strong renal-dose template boost; index article body/sections or expand the corpus for the exact conjunction.

**Evidence status:** plausible_title_level_failure. The strongest observed behavioral positive is C326 (grade 2; final rank >20).

## Q051: add on therapy Malaria after Dolutegravir failure

**Expected relevant content:** Add-on or switching guidance after dolutegravir failure in malaria; C099 is the closest drug-and-disease item but only covers initiation.

**Retrieved content:** #1 C110: WHO Guideline Update: Malaria 2025 | #2 C105: Narrative Review: Current Evidence for Integrase inhibitors in Malaria | #3 C099: Panduan Praktis: Memulai Dolutegravir pada Malaria

**Query decomposition:** `{"disease_entity": "Malaria", "drug_class_entity": "Integrase inhibitors", "molecule_entity": "Dolutegravir", "predicted_intent": "Efficacy / Outcomes", "prior_treatment_failure_flag": true}`

**Why retrieval failed:** The intent classifier changes Treatment Change / Escalation to Efficacy / Outcomes with a 0.004 margin, and the prior-failure constraint has little document evidence. The corpus has no title answering post-failure add-on therapy.

**What could improve it:** Use confidence-gated intent scoring, preserve the prior-treatment-failure slot, and retrieve treatment-escalation sections or add targeted content.

**Evidence status:** plausible_title_level_failure. The strongest observed behavioral positive is C132 (grade 2; final rank >20).

## Q061: Epilepsy first line Antiepileptics other evidence based

**Expected relevant content:** First-line, evidence-based antiepileptic guidance for epilepsy; C076 is the closest disease-level drug item but is an efficacy profile rather than a guideline.

**Retrieved content:** #1 C076: Levetiracetam Drug Profile: Efficacy in Epilepsy | #2 C092: Hasil Jangka Panjang Terapi Antiepileptics other pada Migraine | #3 C080: Treatment Intensification in Epilepsy: When and How

**Query decomposition:** `{"disease_entity": "Epilepsy", "drug_class_entity": "Antiepileptics other", "molecule_entity": "Levetiracetam", "predicted_intent": "Mechanism / Background Knowledge"}`

**Why retrieval failed:** The classifier changes Guideline / Evidence Lookup to Mechanism / Background Knowledge with a 0.012 margin. The top result matches epilepsy but not the requested evidence/guideline form, and no title fully covers the request.

**What could improve it:** Back off from hard intent when the probability margin is low; add guideline/publication-type evidence and section-level retrieval.

**Evidence status:** plausible_title_level_failure. The strongest observed behavioral positive is C103 (grade 3; final rank >20).

## Q066: monitoring parameters Rosuvastatin in Acute Coronary Syndrome

**Expected relevant content:** Monitoring parameters for rosuvastatin/statins in acute coronary syndrome; C043 is the closest entity match but is a generic drug profile.

**Retrieved content:** #1 C043: Profil Obat Statins pada Acute Coronary Syndrome | #2 C035: Stable Angina in Special Populations: Practical Guidance | #3 C039: Switching Therapy in Stable Angina: A Step-by-Step Guide

**Query decomposition:** `{"disease_entity": "Acute Coronary Syndrome", "drug_class_entity": "Statins", "molecule_entity": "Rosuvastatin", "predicted_intent": "Dosing / Administration"}`

**Why retrieval failed:** The classifier selects Dosing / Administration instead of Monitoring with an almost zero margin. Generic monitoring templates for unrelated drugs then enter ranks 4-10, while the exact monitoring conjunction is absent from titles.

**What could improve it:** Use confidence-gated or multi-label intent, require entity compatibility for monitoring templates, and index monitoring sections.

**Evidence status:** plausible_title_level_failure. The strongest observed behavioral positive is C212 (grade 2; final rank >20).

## Q101: Dolutegravir drug interaction with Tenofovir disoproxil in Malaria

**Expected relevant content:** A direct dolutegravir-tenofovir interaction assessment in malaria; C099 is the closest dolutegravir/malaria item but discusses initiation.

**Retrieved content:** #1 C099: Panduan Praktis: Memulai Dolutegravir pada Malaria | #2 C105: Narrative Review: Current Evidence for Integrase inhibitors in Malaria | #3 C093: Practical Guide: Initiating Tenofovir+Lamivudine in Urinary Tract Infection

**Query decomposition:** `{"disease_entity": "Malaria", "drug_class_entity": "Integrase inhibitors; NRTIs", "molecule_entity": "Dolutegravir; Tenofovir disoproxil", "predicted_intent": "Interaction / Combination"}`

**Why retrieval failed:** The ranker retrieves each drug or the disease separately and an interaction template for another antimalarial, but it cannot enforce the two-drug-plus-disease conjunction. No exact title is present.

**What could improve it:** Represent per-value molecule coverage and pairwise interaction constraints; retrieve full text or add interaction-specific content.

**Evidence status:** plausible_title_level_failure. The strongest observed behavioral positive is C255 (grade 3; final rank >20).

## Q129: Imatinib pada ibu hamil dengan Chronic Myeloid Leukaemia

**Expected relevant content:** Pregnancy safety guidance for imatinib in chronic myeloid leukaemia; C206 is the closest special-population article.

**Retrieved content:** #1 C206: Chronic Myeloid Leukaemia pada Populasi Khusus: Pendekatan Praktis | #2 C192: National Guideline: Chronic Myeloid Leukaemia Diagnosis and Treatment | #3 C185: Dosis BCR-ABL inhibitors pada Chronic Myeloid Leukaemia: Referensi Cepat

**Query decomposition:** `{"disease_entity": "Chronic Myeloid Leukaemia", "drug_class_entity": "BCR-ABL inhibitors", "molecule_entity": "Imatinib", "predicted_intent": "Safety / Contraindication", "pregnancy_status": "pregnant"}`

**Why retrieval failed:** Disease and broad special-population evidence place C206 first, but the title does not establish pregnancy or imatinib safety explicitly. Other pregnancy articles concern unrelated diseases.

**What could improve it:** Add value-specific pregnancy compatibility and section-level evidence; abstain or expose a corpus-gap message when pregnancy safety is not documented.

**Evidence status:** plausible_title_level_gap. The strongest observed behavioral positive is C010 (grade 1; final rank >20).

## Q146: Bedaquiline vs Rifampicin untuk pasien Tuberculosis mana lebih efektif

**Expected relevant content:** Direct comparative efficacy evidence for bedaquiline versus rifampicin in tuberculosis; C125 supplies only class-level efficacy evidence.

**Retrieved content:** #1 C130: Profil Keamanan Bedaquiline pada MDR Tuberculosis | #2 C117: Safety Profile of Bedaquiline in MDR Tuberculosis | #3 C120: Safety Profile of Bedaquiline in MDR Tuberculosis

**Query decomposition:** `{"comparison_flag": true, "disease_entity": "Tuberculosis", "drug_class_entity": "Antituberculotics; Antituberculotics", "molecule_entity": "Bedaquiline; Rifampicin", "predicted_intent": "Comparative Treatment Choice"}`

**Why retrieval failed:** Bedaquiline safety articles outrank the class-level efficacy study despite the explicit comparison request. No title compares both requested drugs.

**What could improve it:** Require both comparator values and efficacy/comparison evidence; add pairwise comparison content and use a learned reranker with coverage features.

**Evidence status:** plausible_title_level_failure. The strongest observed behavioral positive is C112 (grade 2; final rank >20).

## Q180: tatalaksana Type 1 Diabetes Mellitus panduan terbaru 2023

**Expected relevant content:** Current 2023 management guidelines for type 1 diabetes; C013 and C002 directly satisfy disease, year, and guideline intent.

**Retrieved content:** #1 C013: Asia-Pacific Guideline: Type 1 Diabetes Mellitus in Primary Care 2023 | #2 C002: Clinical Practice Guideline: Type 1 Diabetes Mellitus Management 2023 | #3 C008: Treatment Intensification in Type 2 Diabetes Mellitus: When and How

**Query decomposition:** `{"disease_entity": "Type 1 Diabetes Mellitus", "drug_class_entity": "Biguanides", "molecule_entity": "Metformin", "predicted_intent": "Guideline / Evidence Lookup", "recency_flag": true, "year": 2023.0}`

**Why retrieval failed:** The final ranker places exact-looking guideline titles at ranks 1 and 2, but both are unjudged. The only behavioral positive is an off-topic 2024 colorectal-cancer review, so proxy NDCG records a miss.

**What could improve it:** Pool and clinically adjudicate top results; keep unjudged distinct from irrelevant and do not tune the ranker toward this behavioral positive.

**Evidence status:** proxy_label_failure. The strongest observed behavioral positive is C196 (grade 1; final rank >20).

## Q224: Losartan hepatic impairment dose in Hypertension

**Expected relevant content:** Hepatic dose-adjustment guidance for losartan in hypertension; C028 matches drug and disease but not hepatic impairment.

**Retrieved content:** #1 C040: Dose Adjustment of Atorvastatin in Renal and Hepatic Impairment | #2 C236: Dose Adjustment of Rivaroxaban in Renal and Hepatic Impairment | #3 C084: Dose Adjustment of Valproate in Renal and Hepatic Impairment

**Query decomposition:** `{"disease_entity": "Hypertension", "dose_context_flag": true, "drug_class_entity": "ARBs", "hepatic_impairment_flag": true, "molecule_entity": "Losartan", "predicted_intent": "Dosing / Administration"}`

**Why retrieval failed:** Eight hepatic/renal dose-adjustment templates for other molecules outrank C028. The context and dosing cues outweigh exact molecule and disease compatibility, while no title covers the complete request.

**What could improve it:** Gate context-template boosts on requested-molecule compatibility and retrieve dose-adjustment sections; add exact losartan hepatic guidance if clinically appropriate.

**Evidence status:** plausible_title_level_failure. The strongest observed behavioral positive is C046 (grade 3; final rank >20).

## Q393: monitoring SSRIs pada ADHD parameter apa

**Expected relevant content:** Monitoring parameters for SSRIs in ADHD; C166 matches class and disease but covers dosing, not monitoring.

**Retrieved content:** #1 C167: Sertraline in ADHD: Real-World Outcomes | #2 C166: Dosis SSRIs pada ADHD: Referensi Cepat | #3 C173: Escitalopram versus Sertraline in Major Depressive Disorder: Head-to-Head Comparison

**Query decomposition:** `{"disease_entity": "ADHD", "drug_class_entity": "SSRIs", "molecule_entity": "Escitalopram", "predicted_intent": "Mechanism / Background Knowledge"}`

**Why retrieval failed:** The classifier predicts Mechanism instead of Monitoring. Assisted intent would move behavior-positive C203 to rank 10, but C203 concerns CNS stimulants in breast cancer, so the apparent metric loss is not a credible clinical loss.

**What could improve it:** Use confidence-aware intent fallback and clinician judgments; do not optimize toward an off-topic behavior-positive document.

**Evidence status:** proxy_label_and_classifier_failure. The strongest observed behavioral positive is C005 (grade 3; final rank >20).

## Q409: Spironolactone dosing in Heart Failure with obesity

**Expected relevant content:** Spironolactone dosing guidance for heart failure with obesity; C034 matches spironolactone and heart failure but only reports outcomes.

**Retrieved content:** #1 C029: Profil Obat ARBs pada Heart Failure | #2 C022: Quick Reference: Vasopressin analogues Dosing in Diabetes Insipidus | #3 C006: Methimazole: Pharmacology, Dosing, and Clinical Use in Hyperthyroidism

**Query decomposition:** `{"disease_entity": "Heart Failure", "dose_context_flag": true, "drug_class_entity": "Aldosterone antagonists", "molecule_entity": "Spironolactone", "predicted_intent": "Dosing / Administration"}`

**Why retrieval failed:** The only spironolactone/heart-failure title falls to rank 20 while generic dosing and drug-profile templates for unrelated molecules dominate. Obesity is also unsupported in candidate titles.

**What could improve it:** Make exact molecule and disease coverage prerequisites for generic dosing boosts; index dosing and comorbidity sections or expand coverage.

**Evidence status:** plausible_title_level_failure. The strongest observed behavioral positive is C054 (grade 3; final rank >20).

## Q435: Artemether-lumefantrine hepatic impairment dose in Typhoid Fever

**Expected relevant content:** Hepatic dose-adjustment guidance for artemether-lumefantrine in typhoid fever; C096 matches entities but covers interactions.

**Retrieved content:** #1 C096: Drug Interactions: Artemether-lumefantrine in Typhoid Fever Patients | #2 C116: Dose Adjustment of Salmeterol in Renal and Hepatic Impairment | #3 C236: Dose Adjustment of Rivaroxaban in Renal and Hepatic Impairment

**Query decomposition:** `{"disease_entity": "Typhoid Fever", "dose_context_flag": true, "drug_class_entity": "Antimalarials", "hepatic_impairment_flag": true, "molecule_entity": "Artemether-lumefantrine", "predicted_intent": "Dosing / Administration"}`

**Why retrieval failed:** The first result matches drug and disease but not dosing; ranks 2-10 match hepatic-dose wording but use other molecules. No title combines all requested constraints.

**What could improve it:** Use a conjunction-aware reranker with molecule, disease, intent, and hepatic-context coverage; retrieve full-text dosing sections and flag unsupported combinations.

**Evidence status:** plausible_title_level_failure. The strongest observed behavioral positive is C059 (grade 3; final rank >20).
