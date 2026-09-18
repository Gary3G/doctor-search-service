# Phase 10: BM25 case review

40 temporal-validation queries: 26 misses, 8 hits and 6 without positive judgments. Seed 42 within each stratum; purposive quotas are not population prevalence estimates. The review was LLM-assisted and used titles and supplied metadata, not independent clinician adjudication. Behavioral positives are observed engagement, not expected clinically relevant answers. Context mismatch labels include missing title evidence, not necessarily contradiction. No model changes or test-set selection occur in this phase.

## Q003: interaksi obat Nivolumab dan Nivolumab pada Colorectal Cancer

**Stratum:** miss. **Categories:** partial entity match;English-Indonesian mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Colorectal Cancer", "molecule_entity": "Nivolumab; Nivolumab", "drug_class_entity": "PD-1 inhibitors; PD-1 inhibitors", "intent": "Interaction / Combination"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C202 | 1 | unjudged | Drug Interactions: Nivolumab in Non-Small Cell Lung Cancer Patients |
| retrieved top 3 | C189 | 2 | unjudged | Clinical Practice Guideline: Colorectal Cancer Management 2020 |
| retrieved top 3 | C201 | 3 | unjudged | Kasus Sulit: Colorectal Cancer Refrakter terhadap Pembrolizumab |
| strongest observed positive | C030 | 103 | 3 | Treatment Intensification in Atrial Fibrillation: When and How |
| strongest observed positive | C010 | 77 | 1 | Dosis DPP-4 inhibitors pada Type 2 Diabetes Mellitus: Referensi Cepat |

C202 preserves Nivolumab and interaction intent but changes Colorectal Cancer to lung cancer. Indonesian interaction wording has no direct English token match. Repeated identical query drugs also warrant data review.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test bilingual intent cues and joint disease/molecule coverage.

## Q015: Peptic Ulcer Disease prophylaxis Lansoprazole indication

**Stratum:** hit. **Categories:** intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Peptic Ulcer Disease", "molecule_entity": "Lansoprazole", "drug_class_entity": "Proton pump inhibitors", "intent": "Prophylaxis / Maintenance"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C157 | 1 | unjudged | Profil Keamanan Lansoprazole pada Peptic Ulcer Disease |
| retrieved top 3 | C147 | 2 | unjudged | National Guideline: Peptic Ulcer Disease Diagnosis and Treatment |
| retrieved top 3 | C150 | 3 | unjudged | Practical Guide: Initiating Omeprazole in Peptic Ulcer Disease |
| strongest observed positive | C167 | 168 | 3 | Sertraline in ADHD: Real-World Outcomes |
| strongest observed positive | C143 | 5 | 2 | Consensus Statement: Proton pump inhibitors Use in Peptic Ulcer Disease |
| observed top-10 hit | C143 | 5 | 2 | Consensus Statement: Proton pump inhibitors Use in Peptic Ulcer Disease |
| plausible inspection candidate | C143 | 5 | 2 | Consensus Statement: Proton pump inhibitors Use in Peptic Ulcer Disease |

C157 matches drug and disease but discusses safety rather than prophylaxis or stopping criteria. The grade-2 hit C143 is only a general class-use consensus.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Evaluate intent compatibility; obtain content on maintenance duration.

## Q018: interaksi obat Losartan dan Empagliflozin pada Chronic Kidney Disease

**Stratum:** hit. **Categories:** intent mismatch;partial entity match;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Chronic Kidney Disease", "molecule_entity": "Losartan; Empagliflozin", "drug_class_entity": "ARBs; SGLT2 inhibitors", "intent": "Interaction / Combination"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C065 | 1 | unjudged | Profil Keamanan Losartan pada Chronic Kidney Disease |
| retrieved top 3 | C059 | 2 | unjudged | Safety Profile of Empagliflozin in Chronic Kidney Disease |
| retrieved top 3 | C047 | 3 | unjudged | Drug Interactions: Losartan in Chronic Kidney Disease Patients |
| strongest observed positive | C104 | 180 | 2 | NRTIs: Mechanism, Indications, and Safety |
| strongest observed positive | C212 | 74 | 2 | Profil Keamanan Alendronate pada Osteoporosis |
| observed top-10 hit | C068 | 6 | 1 | Chronic Kidney Disease pada Populasi Khusus: Pendekatan Praktis |
| plausible inspection candidate | C047 | 3 | unjudged | Drug Interactions: Losartan in Chronic Kidney Disease Patients |

Two safety profiles outrank C047, whose title explicitly concerns Losartan interactions in CKD. No inspected title establishes the specific Losartan/Empagliflozin interaction.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test interaction-intent weighting and coverage of both drugs.

## Q025: Acute Coronary Syndrome guideline update 2023 summary

**Stratum:** miss. **Categories:** partial entity match;temporal mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Acute Coronary Syndrome", "molecule_entity": "Atorvastatin", "drug_class_entity": "Statins", "intent": "Guideline / Evidence Lookup", "year": 2023.0, "recency_flag": true}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C043 | 1 | unjudged | Profil Obat Statins pada Acute Coronary Syndrome |
| retrieved top 3 | C024 | 2 | unjudged | Laporan Kasus: Acute Coronary Syndrome dengan Presentasi Atipikal |
| retrieved top 3 | C333 | 3 | unjudged | WHO Guideline Update: Psoriasis 2023 |
| strongest observed positive | C104 | 127 | 1 | NRTIs: Mechanism, Indications, and Safety |

Top titles match ACS without guideline intent or the requested year; C333 matches guideline/update/2023 but concerns Psoriasis. This is an entity-versus-template tradeoff.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test disease coverage before year compatibility.

## Q029: Empagliflozin efficacy pada Type 2 Diabetes Mellitus clinical outcome data

**Stratum:** no_positive. **Categories:** partial entity match;intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Type 2 Diabetes Mellitus", "molecule_entity": "Empagliflozin", "drug_class_entity": "SGLT2 inhibitors", "intent": "Efficacy / Outcomes"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C020 | 1 | unjudged | Clinical Practice Guideline: Type 2 Diabetes Mellitus Management 2021 |
| retrieved top 3 | C005 | 2 | unjudged | Liraglutide in Type 2 Diabetes Mellitus: Real-World Outcomes |
| retrieved top 3 | C012 | 3 | unjudged | Case Report: Atypical Presentation of Type 2 Diabetes Mellitus |

C020 is a diabetes guideline; C005 is an outcomes title for Liraglutide, not the requested Empagliflozin. No validation positives exist for this query.

**Behavioral evidence:** no observed positives.

**Next check:** Test molecule coverage and inspect corpus coverage before expansion.

## Q032: interaksi obat Ramipril dan Spironolactone pada Heart Failure

**Stratum:** hit. **Categories:** partial entity match;intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Heart Failure", "molecule_entity": "Ramipril; Spironolactone", "drug_class_entity": "ACE inhibitors; Aldosterone antagonists", "intent": "Interaction / Combination"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C029 | 1 | unjudged | Profil Obat ARBs pada Heart Failure |
| retrieved top 3 | C034 | 2 | unjudged | Spironolactone Real-World Evidence in Heart Failure: A Retrospective Study |
| retrieved top 3 | C045 | 3 | unjudged | Metoprolol pada Pasien Heart Failure: Studi Kohort |
| strongest observed positive | C137 | 175 | 3 | Asthma in immunocompromised: Special Considerations |
| strongest observed positive | C031 | 5 | 2 | Clinical Practice Guideline: Heart Failure Management 2021 |
| observed top-10 hit | C031 | 5 | 2 | Clinical Practice Guideline: Heart Failure Management 2021 |

C029 is an ARB profile; C034 covers Spironolactone outcomes but does not establish interaction with Ramipril. A general HF guideline supplies the behavioral hit.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test pairwise drug coverage and interaction intent.

## Q065: Semaglutide efficacy pada Type 2 Diabetes Mellitus clinical outcome data

**Stratum:** miss. **Categories:** partial entity match;intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Type 2 Diabetes Mellitus", "molecule_entity": "Semaglutide", "drug_class_entity": "GLP-1 receptor agonists", "intent": "Efficacy / Outcomes"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C020 | 1 | unjudged | Clinical Practice Guideline: Type 2 Diabetes Mellitus Management 2021 |
| retrieved top 3 | C005 | 2 | unjudged | Liraglutide in Type 2 Diabetes Mellitus: Real-World Outcomes |
| retrieved top 3 | C012 | 3 | unjudged | Case Report: Atypical Presentation of Type 2 Diabetes Mellitus |
| strongest observed positive | C065 | 69 | 2 | Profil Keamanan Losartan pada Chronic Kidney Disease |
| strongest observed positive | C343 | 344 | 1 | Dose Adjustment of Dupilumab in Renal and Hepatic Impairment |
| plausible inspection candidate | C005 | 2 | unjudged | Liraglutide in Type 2 Diabetes Mellitus: Real-World Outcomes |

C005 names Liraglutide in the title but its supplied metadata also contains Semaglutide. This is hidden entity evidence, not proof of a wrong-molecule document. A general guideline ranks first.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test supplied entity features and audit metadata against full text.

## Q070: Furosemide long term outcomes Nephrotic Syndrome

**Stratum:** miss. **Categories:** weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Nephrotic Syndrome", "molecule_entity": "Furosemide", "drug_class_entity": "Loop diuretics", "intent": "Efficacy / Outcomes"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C053 | 1 | unjudged | Furosemide in Nephrotic Syndrome: Real-World Outcomes |
| retrieved top 3 | C049 | 2 | 0 | Safety Profile of Furosemide in Nephrotic Syndrome |
| retrieved top 3 | C066 | 3 | unjudged | Panduan Praktis: Memulai Furosemide pada Nephrotic Syndrome |
| strongest observed positive | C005 | 21 | 2 | Liraglutide in Type 2 Diabetes Mellitus: Real-World Outcomes |
| strongest observed positive | C258 | 261 | 2 | Centrally acting antihypertensives: Mechanism, Indications, and Safety |
| plausible inspection candidate | C053 | 1 | unjudged | Furosemide in Nephrotic Syndrome: Real-World Outcomes |

C053 at rank 1 directly matches Furosemide, Nephrotic Syndrome and outcomes; the inspected behavioral positives concern diabetes and pregnancy hypertension. No visible top-1 failure is established.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Prioritize independent relevance review before changing this ranking.

## Q077: algoritma terapi Iron Deficiency Anaemia step up

**Stratum:** hit. **Categories:** intent mismatch;English-Indonesian mismatch.

**Decomposition:** `{"disease_entity": "Iron Deficiency Anaemia", "molecule_entity": "Erythropoietin", "drug_class_entity": "Erythropoiesis stimulating agents", "intent": "Management / Treatment Selection"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C253 | 1 | unjudged | Hasil Jangka Panjang Terapi Erythropoiesis stimulating agents pada Iron Deficiency Anaemia |
| retrieved top 3 | C232 | 2 | unjudged | Consensus Statement: Iron preparations Use in Iron Deficiency Anaemia |
| retrieved top 3 | C240 | 3 | unjudged | Quick Reference: Iron preparations Dosing in Iron Deficiency Anaemia |
| strongest observed positive | C237 | 7 | 3 | Ferrous sulphate: Farmakologi dan Penggunaan Klinis pada Iron Deficiency Anaemia |
| observed top-10 hit | C237 | 7 | 3 | Ferrous sulphate: Farmakologi dan Penggunaan Klinis pada Iron Deficiency Anaemia |

An outcomes title ranks first for a step-up treatment algorithm. General iron guidance and dosing follow; the behavioral hit is a drug pharmacology title.

**Behavioral evidence:** broad same-disease positive; exact intent unverified.

**Next check:** Test bilingual management cues and obtain escalation-specific text.

## Q081: Stable Angina dengan hypertension pilihan drug terbaik

**Stratum:** miss. **Categories:** missing contextual constraint;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Stable Angina", "molecule_entity": "Atorvastatin", "drug_class_entity": "Statins", "intent": "Management / Treatment Selection"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C035 | 1 | unjudged | Stable Angina in Special Populations: Practical Guidance |
| retrieved top 3 | C036 | 2 | unjudged | Dosis Platelet aggregation inhibitors pada Stable Angina: Referensi Cepat |
| retrieved top 3 | C039 | 3 | unjudged | Switching Therapy in Stable Angina: A Step-by-Step Guide |
| strongest observed positive | C253 | 266 | 3 | Hasil Jangka Panjang Terapi Erythropoiesis stimulating agents pada Iron Deficiency Anaemia |
| strongest observed positive | C084 | 105 | 2 | Dose Adjustment of Valproate in Renal and Hepatic Impairment |

C035 is broadly about special populations in Stable Angina; its title does not establish hypertension-specific drug choice. Missing detail is not evidence of contradiction.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Obtain full text and evaluate comorbidity compatibility.

## Q094: kapan start Azithromycin di Asthma evidence terbaru 2022

**Stratum:** miss. **Categories:** partial entity match;temporal mismatch;intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Asthma", "molecule_entity": "Azithromycin", "drug_class_entity": "Macrolides", "intent": "Guideline / Evidence Lookup", "year": 2022.0, "recency_flag": true}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C124 | 1 | unjudged | Konsensus Nasional: Asthma di Indonesia 2024 |
| retrieved top 3 | C219 | 2 | unjudged | Konsensus Nasional: Osteoporosis di Indonesia 2022 |
| retrieved top 3 | C062 | 3 | unjudged | Konsensus Nasional: Chronic Kidney Disease di Indonesia 2022 |
| strongest observed positive | C052 | 80 | 3 | Clinical Summary: Chronic Kidney Disease Management Update 2024 |

C124 is an Asthma consensus from 2024 rather than the requested 2022 initiation evidence. Other top titles match 2022 but change the disease; Azithromycin is absent from inspected titles.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test entity/year compatibility and audit title coverage.

## Q100: prophylaxis Ischaemic Stroke Alteplase kapan bisa dihentikan

**Stratum:** miss. **Categories:** partial entity match;intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Ischaemic Stroke", "molecule_entity": "Alteplase", "drug_class_entity": "Thrombolytics", "intent": "Prophylaxis / Maintenance"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C085 | 1 | unjudged | Pedoman PNPK: Ischaemic Stroke |
| retrieved top 3 | C070 | 2 | 0 | Ischaemic Stroke in Special Populations: Practical Guidance |
| retrieved top 3 | C082 | 3 | unjudged | Rare Adverse Event of Aspirin in Ischaemic Stroke |
| strongest observed positive | C029 | 33 | 2 | Profil Obat ARBs pada Heart Failure |
| strongest observed positive | C162 | 162 | 2 | Biomarkers in Schizophrenia: Implications for Atypical antipsychotics Therapy |

Stroke guidance and an Aspirin adverse-event title do not establish when to stop Alteplase prophylaxis. No title containing Alteplase was found.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Audit query and corpus coverage; retrieve duration-specific evidence.

## Q122: Tenofovir+Lamivudine pada pasien elderly Urinary Tract Infection apa perlu adjustment

**Stratum:** miss. **Categories:** age mismatch;missing contextual constraint;intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Urinary Tract Infection", "molecule_entity": "Tenofovir+Lamivudine", "drug_class_entity": "NRTIs combination", "intent": "Dosing / Administration", "age_group": "elderly", "dose_context_flag": true}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C109 | 1 | unjudged | Panduan Praktis: Memulai Tenofovir+Lamivudine pada Urinary Tract Infection |
| retrieved top 3 | C093 | 2 | unjudged | Practical Guide: Initiating Tenofovir+Lamivudine in Urinary Tract Infection |
| retrieved top 3 | C094 | 3 | unjudged | Tenofovir+Lamivudine: Pharmacology, Dosing, and Clinical Use in Urinary Tract Infection |
| strongest observed positive | C158 | 201 | 3 | Practical Guide: Initiating Metronidazole in Inflammatory Bowel Disease |
| strongest observed positive | C127 | 178 | 2 | Risk Stratification in Asthma: Current Approaches |
| plausible inspection candidate | C094 | 3 | unjudged | Tenofovir+Lamivudine: Pharmacology, Dosing, and Clinical Use in Urinary Tract Infection |

C109 and C093 match the supplied drug/disease but describe initiation, without elderly adjustment evidence in the title. Age mismatch here means omitted evidence, not an incompatible age population.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Inspect dosing candidate C094 and add age compatibility only with supporting text.

## Q141: prophylaxis Colorectal Cancer Pembrolizumab kapan bisa dihentikan

**Stratum:** no_positive. **Categories:** intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Colorectal Cancer", "molecule_entity": "Pembrolizumab", "drug_class_entity": "PD-1 inhibitors", "intent": "Prophylaxis / Maintenance"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C201 | 1 | unjudged | Kasus Sulit: Colorectal Cancer Refrakter terhadap Pembrolizumab |
| retrieved top 3 | C189 | 2 | unjudged | Clinical Practice Guideline: Colorectal Cancer Management 2020 |
| retrieved top 3 | C196 | 3 | unjudged | Scoping Review: Emerging Therapies in Colorectal Cancer 2024 |

C201 concerns refractory disease rather than stopping prophylaxis. No behavioral positives are available; clinical relevance remains unresolved.

**Behavioral evidence:** no observed positives.

**Next check:** Obtain maintenance/stopping content and evaluate intent.

## Q143: switch dari Adalimumab ke Adalimumab Systemic Lupus Erythematosus progresif

**Stratum:** no_positive. **Categories:** partial entity match;severity mismatch;intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Systemic Lupus Erythematosus", "molecule_entity": "Adalimumab; Adalimumab", "drug_class_entity": "TNF inhibitors; TNF inhibitors", "intent": "Treatment Change / Escalation"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C214 | 1 | 0 | Adalimumab versus Adalimumab in Gout: Head-to-Head Comparison |
| retrieved top 3 | C208 | 2 | unjudged | Laporan Kasus: Systemic Lupus Erythematosus dengan Presentasi Atipikal |
| retrieved top 3 | C211 | 3 | unjudged | Case Report: Atypical Presentation of Systemic Lupus Erythematosus |

C214 matches Adalimumab but changes SLE to Gout and compares the drug with itself. Other titles match SLE without progression or switching. The query also switches a drug to itself.

**Behavioral evidence:** no observed positives.

**Next check:** Audit self-comparison artifacts; test disease and progression constraints.

## Q145: titration protocol Rivaroxaban in Community-acquired Pneumonia

**Stratum:** miss. **Categories:** partial entity match;intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Community-acquired Pneumonia", "molecule_entity": "Rivaroxaban", "drug_class_entity": "Factor Xa inhibitors", "intent": "Dosing / Administration"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C121 | 1 | 0 | Asia-Pacific Guideline: Community-acquired Pneumonia in Primary Care 2025 |
| retrieved top 3 | C122 | 2 | unjudged | Case Series: Factor Xa inhibitors in Refractory Community-acquired Pneumonia |
| retrieved top 3 | C236 | 3 | unjudged | Dose Adjustment of Rivaroxaban in Renal and Hepatic Impairment |
| strongest observed positive | C285 | 312 | 3 | Perbandingan Diazepam dan Diazepam pada Febrile Seizure |
| strongest observed positive | C295 | 63 | 3 | Risk Stratification in Stunting / Malnutrition: Current Approaches |
| plausible inspection candidate | C236 | 3 | unjudged | Dose Adjustment of Rivaroxaban in Renal and Hepatic Impairment |

A pneumonia guideline and a class-level case series outrank Rivaroxaban adjustment C236. Renal/hepatic adjustment is only a partial alternative to titration in the requested disease.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test molecule/dosing features while retaining uncertainty about disease relevance.

## Q153: Rheumatoid Arthritis guideline update 2023 summary

**Stratum:** miss. **Categories:** partial entity match;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Rheumatoid Arthritis", "molecule_entity": "Mycophenolate mofetil", "drug_class_entity": "Immunosuppressants", "intent": "Guideline / Evidence Lookup", "year": 2023.0, "recency_flag": true}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C333 | 1 | unjudged | WHO Guideline Update: Psoriasis 2023 |
| retrieved top 3 | C233 | 2 | unjudged | WHO Guideline Update: Iron Deficiency Anaemia 2023 |
| retrieved top 3 | C224 | 3 | unjudged | Risk Stratification in Rheumatoid Arthritis: Current Approaches |
| strongest observed positive | C028 | 64 | 2 | Practical Guide: Initiating Losartan in Hypertension |

C333 and C233 match guideline/update/2023 but concern Psoriasis and anaemia rather than Rheumatoid Arthritis.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Require entity coverage in a measured reranking ablation.

## Q161: Magnesium sulphate pada pasien elderly Preeclampsia apa perlu adjustment

**Stratum:** miss. **Categories:** age mismatch;missing contextual constraint;intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Preeclampsia", "molecule_entity": "Magnesium sulphate", "drug_class_entity": "Magnesium", "intent": "Dosing / Administration", "age_group": "elderly", "pregnancy_status": "pregnancy_related", "dose_context_flag": true}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C271 | 1 | unjudged | Panduan Praktis: Memulai Magnesium sulphate pada Preeclampsia |
| retrieved top 3 | C273 | 2 | unjudged | Magnesium sulphate: Farmakologi dan Penggunaan Klinis pada Preeclampsia |
| retrieved top 3 | C276 | 3 | unjudged | Efektivitas Magnesium pada Preeclampsia |
| strongest observed positive | C005 | 95 | 3 | Liraglutide in Type 2 Diabetes Mellitus: Real-World Outcomes |
| plausible inspection candidate | C273 | 2 | unjudged | Magnesium sulphate: Farmakologi dan Penggunaan Klinis pada Preeclampsia |

Initiation and pharmacology titles match Magnesium sulphate/Preeclampsia but do not establish elderly dose adjustment. The query itself needs domain review; no clinical validity is inferred.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Inspect underlying text and audit unusual query combinations.

## Q162: Diazepam contraindication in Febrile Seizure with diabetes

**Stratum:** no_positive. **Categories:** intent mismatch;missing contextual constraint;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Febrile Seizure", "molecule_entity": "Diazepam", "drug_class_entity": "Benzodiazepines", "intent": "Safety / Contraindication"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C285 | 1 | unjudged | Perbandingan Diazepam dan Diazepam pada Febrile Seizure |
| retrieved top 3 | C291 | 2 | unjudged | Perbandingan Diazepam dan Diazepam pada Febrile Seizure |
| retrieved top 3 | C278 | 3 | unjudged | Diazepam Drug Profile: Efficacy in Febrile Seizure |

Self-comparison titles outrank general Diazepam pharmacology for a contraindication question with diabetes; none of the top three titles establishes diabetes safety.

**Behavioral evidence:** no observed positives.

**Next check:** Test safety intent and comorbidity evidence; audit duplicate templates.

## Q198: Calcium channel blockers new evidence Hypertension 2022

**Stratum:** miss. **Categories:** partial entity match;temporal mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Hypertension", "molecule_entity": "Amlodipine", "drug_class_entity": "Calcium channel blockers", "intent": "Guideline / Evidence Lookup", "year": 2022.0}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C263 | 1 | unjudged | Tinjauan Sistematis: Beta blockers non-selective pada Hypertension in Pregnancy |
| retrieved top 3 | C270 | 2 | unjudged | Long-term Outcomes of Beta blockers non-selective Therapy in Hypertension in Pregnancy |
| retrieved top 3 | C256 | 3 | unjudged | New Insights into Preeclampsia Pathophysiology and Treatment |
| strongest observed positive | C145 | 175 | 1 | Metronidazole Drug Profile: Efficacy in Inflammatory Bowel Disease |

Beta-blocker pregnancy-hypertension titles rank above evidence for calcium channel blockers in hypertension in 2022. Neither requested class nor year is established in the top three titles.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test class and disease specificity before recency weighting.

## Q201: interaksi obat Semaglutide dan Liraglutide pada Obesity

**Stratum:** hit. **Categories:** lexical mismatch;English-Indonesian mismatch;partial entity match;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Obesity", "molecule_entity": "Semaglutide; Liraglutide", "drug_class_entity": "GLP-1 receptor agonists; GLP-1 receptor agonists", "intent": "Interaction / Combination"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C029 | 1 | unjudged | Profil Obat ARBs pada Heart Failure |
| retrieved top 3 | C043 | 2 | unjudged | Profil Obat Statins pada Acute Coronary Syndrome |
| retrieved top 3 | C266 | 3 | unjudged | Profil Obat Centrally acting antihypertensives pada Hypertension in Pregnancy |
| strongest observed positive | C089 | 7 | 2 | Perbandingan Topiramate dan Topiramate pada Migraine |
| strongest observed positive | C103 | 31 | 2 | Profil Keamanan Amoxicillin pada HIV/AIDS |
| observed top-10 hit | C089 | 7 | 2 | Perbandingan Topiramate dan Topiramate pada Migraine |

Generic Indonesian drug-profile wording dominates: top titles concern HF, ACS and pregnancy hypertension. The grade-2 top-10 hit C089 is a Topiramate/Migraine self-comparison.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test bilingual interaction cues and entity coverage; audit misleading proxy hit.

## Q210: switch dari Venlafaxine ke Escitalopram Major Depressive Disorder progresif

**Stratum:** hit. **Categories:** partial entity match;intent mismatch;severity mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Major Depressive Disorder", "molecule_entity": "Venlafaxine; Escitalopram", "drug_class_entity": "SNRIs; SSRIs", "intent": "Treatment Change / Escalation"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C171 | 1 | unjudged | Perbandingan Venlafaxine dan Venlafaxine pada Major Depressive Disorder |
| retrieved top 3 | C173 | 2 | unjudged | Escitalopram versus Sertraline in Major Depressive Disorder: Head-to-Head Comparison |
| retrieved top 3 | C170 | 3 | unjudged | Major Depressive Disorder in hypertension: Special Considerations |
| strongest observed positive | C118 | 132 | 2 | COPD in Pregnancy: Safety and Management Guide |
| strongest observed positive | C124 | 138 | 2 | Konsensus Nasional: Asthma di Indonesia 2024 |
| observed top-10 hit | C182 | 9 | 1 | Sertraline: Pharmacology, Dosing, and Clinical Use in Major Depressive Disorder |

C171 compares Venlafaxine with itself and C173 compares Escitalopram with Sertraline. Neither represents the requested switch pair or progressive disease. The proxy hit C182 concerns Sertraline.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test ordered switch-pair coverage and progression evidence.

## Q225: Psoriasis dengan elderly patients pilihan drug terbaik

**Stratum:** miss. **Categories:** weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Psoriasis", "molecule_entity": "Tacrolimus topical", "drug_class_entity": "Topical calcineurin inhibitors", "intent": "Management / Treatment Selection", "age_group": "elderly"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C332 | 1 | unjudged | Psoriasis in elderly patients: Special Considerations |
| retrieved top 3 | C322 | 2 | unjudged | Disseminated Intravascular Coagulation and elderly patients: Management Challenges |
| retrieved top 3 | C242 | 3 | unjudged | Challenging Case: Deep Vein Thrombosis with Concurrent elderly patients |
| strongest observed positive | C231 | 258 | 2 | Dose Adjustment of Apixaban in Renal and Hepatic Impairment |
| plausible inspection candidate | C332 | 1 | unjudged | Psoriasis in elderly patients: Special Considerations |

C332 directly matches Psoriasis and elderly patients. Its title is broad but no age mismatch is visible; the inspected behavioral positive is Apixaban renal/hepatic dosing.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Review relevance independently; inspect full text for treatment selection.

## Q232: Prednisolone side effect pada pasien Rheumatoid Arthritis apa saja

**Stratum:** miss. **Categories:** partial entity match;intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Rheumatoid Arthritis", "molecule_entity": "Prednisolone", "drug_class_entity": "Corticosteroids", "intent": "Safety / Contraindication"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C135 | 1 | unjudged | Prednisolone pada Pasien COPD: Studi Kohort |
| retrieved top 3 | C220 | 2 | unjudged | Hasil Jangka Panjang Terapi Proteasome inhibitors pada Rheumatoid Arthritis |
| retrieved top 3 | C224 | 3 | unjudged | Risk Stratification in Rheumatoid Arthritis: Current Approaches |
| strongest observed positive | C025 | 97 | 3 | Metoprolol versus Empagliflozin in Atrial Fibrillation: Head-to-Head Comparison |
| strongest observed positive | C112 | 163 | 1 | Antimalarials: Mechanism, Indications, and Safety |

C135 matches Prednisolone but concerns COPD cohort outcomes rather than RA adverse effects. Other top titles preserve RA without the drug or safety focus.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test joint entity and adverse-effect compatibility.

## Q238: Basal insulins in pregnancy and Type 1 Diabetes Mellitus

**Stratum:** miss. **Categories:** pregnancy mismatch;missing contextual constraint;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Type 1 Diabetes Mellitus", "molecule_entity": "Insulin glargine", "drug_class_entity": "Basal insulins", "intent": "Safety / Contraindication", "pregnancy_status": "pregnant"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C002 | 1 | unjudged | Clinical Practice Guideline: Type 1 Diabetes Mellitus Management 2023 |
| retrieved top 3 | C013 | 2 | unjudged | Asia-Pacific Guideline: Type 1 Diabetes Mellitus in Primary Care 2023 |
| retrieved top 3 | C003 | 3 | unjudged | A Case of Type 1 Diabetes Mellitus Resistant to Insulin degludec |
| strongest observed positive | C109 | 252 | 1 | Panduan Praktis: Memulai Tenofovir+Lamivudine pada Urinary Tract Infection |

Top titles preserve Type 1 Diabetes but omit pregnancy safety. Omission does not prove pregnancy-incompatible content.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Obtain pregnancy-specific evidence and validate context extraction on full text.

## Q278: add on Furosemide setelah Furosemide gagal Nephrotic Syndrome

**Stratum:** miss. **Categories:** intent mismatch;severity mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Nephrotic Syndrome", "molecule_entity": "Furosemide; Furosemide", "drug_class_entity": "Loop diuretics; Loop diuretics", "intent": "Treatment Change / Escalation", "prior_treatment_failure_flag": true}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C049 | 1 | unjudged | Safety Profile of Furosemide in Nephrotic Syndrome |
| retrieved top 3 | C053 | 2 | unjudged | Furosemide in Nephrotic Syndrome: Real-World Outcomes |
| retrieved top 3 | C066 | 3 | unjudged | Panduan Praktis: Memulai Furosemide pada Nephrotic Syndrome |
| strongest observed positive | C028 | 39 | 3 | Practical Guide: Initiating Losartan in Hypertension |
| strongest observed positive | C247 | 247 | 3 | Iron Deficiency Anaemia pada Populasi Khusus: Pendekatan Praktis |

Safety, outcomes and initiation titles match Furosemide/Nephrotic Syndrome but omit prior failure and escalation; the add-on query repeats the same drug.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Audit the repeated-drug query and test prior-failure compatibility.

## Q284: Proton pump inhibitors adverse effects monitoring in Peptic Ulcer Disease

**Stratum:** miss. **Categories:** intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Peptic Ulcer Disease", "molecule_entity": "Omeprazole", "drug_class_entity": "Proton pump inhibitors", "intent": "Safety / Contraindication"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C143 | 1 | unjudged | Consensus Statement: Proton pump inhibitors Use in Peptic Ulcer Disease |
| retrieved top 3 | C139 | 2 | unjudged | Narrative Review: Current Evidence for Proton pump inhibitors in Peptic Ulcer Disease |
| retrieved top 3 | C141 | 3 | unjudged | Efficacy of Proton pump inhibitors in Peptic Ulcer Disease: A Cohort Study |
| strongest observed positive | C138 | 116 | 1 | Treatment Intensification in Asthma: When and How |

C143 and C139 are broad class-use/evidence titles, while C141 explicitly concerns efficacy. None of the top three titles establishes adverse-effect monitoring.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test safety/monitoring compatibility using richer text.

## Q288: apakah Trastuzumab aman untuk Non-Small Cell Lung Cancer dengan hypertension

**Stratum:** no_positive. **Categories:** partial entity match;missing contextual constraint;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Non-Small Cell Lung Cancer", "molecule_entity": "Trastuzumab", "drug_class_entity": "HER2-targeted agents", "intent": "Safety / Contraindication"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C202 | 1 | unjudged | Drug Interactions: Nivolumab in Non-Small Cell Lung Cancer Patients |
| retrieved top 3 | C190 | 2 | unjudged | Case Series: HER2-targeted agents in Refractory Non-Small Cell Lung Cancer |
| retrieved top 3 | C263 | 3 | unjudged | Tinjauan Sistematis: Beta blockers non-selective pada Hypertension in Pregnancy |

C202 changes Trastuzumab to Nivolumab; C190 is class-level refractory lung-cancer content. Neither title establishes hypertension-specific safety.

**Behavioral evidence:** no observed positives.

**Next check:** Test molecule and comorbidity evidence; no clinical judgment without full text.

## Q346: Chronic Kidney Disease dengan renal impairment penyesuaian dosis Losartan

**Stratum:** miss. **Categories:** renal-function mismatch;missing contextual constraint;intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Chronic Kidney Disease", "molecule_entity": "Losartan", "drug_class_entity": "ARBs", "intent": "Dosing / Administration", "dose_context_flag": true, "renal_function_group": "renal_impairment"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C065 | 1 | unjudged | Profil Keamanan Losartan pada Chronic Kidney Disease |
| retrieved top 3 | C047 | 2 | unjudged | Drug Interactions: Losartan in Chronic Kidney Disease Patients |
| retrieved top 3 | C048 | 3 | unjudged | Panduan Klinis: Tatalaksana Chronic Kidney Disease 2022 |
| strongest observed positive | C124 | 172 | 3 | Konsensus Nasional: Asthma di Indonesia 2024 |
| strongest observed positive | C327 | 330 | 2 | Biomarkers in Psoriasis: Implications for IL-4/IL-13 inhibitors Therapy |

C065 and C047 match Losartan/CKD but describe safety and interactions. CKD overlap alone does not establish renal dose adjustment.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test renal dosing intent separately from disease overlap.

## Q349: dosis Liraglutide untuk pasien Obesity

**Stratum:** miss. **Categories:** partial entity match;intent mismatch;English-Indonesian mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Obesity", "molecule_entity": "Liraglutide", "drug_class_entity": "GLP-1 receptor agonists", "intent": "Dosing / Administration", "dose_context_flag": true}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C009 | 1 | unjudged | Case Report: Atypical Presentation of Obesity |
| retrieved top 3 | C005 | 2 | unjudged | Liraglutide in Type 2 Diabetes Mellitus: Real-World Outcomes |
| retrieved top 3 | C200 | 3 | unjudged | Chronic Lymphocytic Leukaemia and obesity: Management Challenges |
| strongest observed positive | C212 | 216 | 3 | Profil Keamanan Alendronate pada Osteoporosis |

An Obesity case report outranks Liraglutide outcomes in diabetes. Neither is a Liraglutide obesity dosing title; Indonesian dosing wording lacks an English equivalent token.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test bilingual dosing cues and joint entity coverage.

## Q363: target Type 2 Diabetes Mellitus sudah tercapai kapan maintenance Liraglutide

**Stratum:** miss. **Categories:** intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Type 2 Diabetes Mellitus", "molecule_entity": "Liraglutide", "drug_class_entity": "GLP-1 receptor agonists", "intent": "Prophylaxis / Maintenance"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C005 | 1 | unjudged | Liraglutide in Type 2 Diabetes Mellitus: Real-World Outcomes |
| retrieved top 3 | C012 | 2 | unjudged | Case Report: Atypical Presentation of Type 2 Diabetes Mellitus |
| retrieved top 3 | C017 | 3 | unjudged | Type 2 Diabetes Mellitus in Special Populations: Practical Guidance |
| strongest observed positive | C033 | 33 | 2 | Statins: Mechanism, Indications, and Safety |

C005 matches drug/disease but concerns outcomes rather than criteria to continue maintenance after target attainment.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Obtain duration/maintenance evidence and evaluate intent.

## Q386: Zinc side effect pada pasien Stunting / Malnutrition apa saja

**Stratum:** miss. **Categories:** intent mismatch;lexical mismatch;synonym mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Stunting / Malnutrition", "molecule_entity": "Zinc", "drug_class_entity": "Zinc supplements", "intent": "Safety / Contraindication"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C294 | 1 | unjudged | Perbandingan Zinc dan Zinc pada Stunting / Malnutrition |
| retrieved top 3 | C283 | 2 | unjudged | Drug Interactions: Zinc in Stunting / Malnutrition Patients |
| retrieved top 3 | C288 | 3 | unjudged | Zinc in Stunting / Malnutrition: Real-World Outcomes |
| strongest observed positive | C145 | 194 | 2 | Metronidazole Drug Profile: Efficacy in Inflammatory Bowel Disease |
| strongest observed positive | C338 | 340 | 2 | Laporan Kasus: Psoriasis dengan anaemia |
| plausible inspection candidate | C279 | 4 | unjudged | Rare Adverse Event of Zinc in Stunting / Malnutrition |

A Zinc self-comparison outranks C279, whose adverse-event title is closer to side-effect intent. Side effect and adverse event do not share the decisive tokens.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test safety synonym normalization; verify adverse-event article scope.

## Q392: switch from Artemether-lumefantrine to Artemether-lumefantrine in Typhoid Fever

**Stratum:** miss. **Categories:** intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Typhoid Fever", "molecule_entity": "Artemether-lumefantrine; Artemether-lumefantrine", "drug_class_entity": "Antimalarials; Antimalarials", "intent": "Treatment Change / Escalation"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C096 | 1 | unjudged | Drug Interactions: Artemether-lumefantrine in Typhoid Fever Patients |
| retrieved top 3 | C106 | 2 | unjudged | Successful Management of Severe Typhoid Fever with Artemether-lumefantrine |
| retrieved top 3 | C113 | 3 | unjudged | Risk Stratification in Typhoid Fever: Current Approaches |
| strongest observed positive | C027 | 203 | 2 | National Guideline: Atrial Fibrillation Diagnosis and Treatment |
| strongest observed positive | C037 | 42 | 2 | Atrial Fibrillation in Special Populations: Practical Guidance |

Interactions and severe-disease management outrank any switching-specific evidence. The query requests a switch from a drug to itself.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Audit query artifact and test switch intent rather than assume a valid drug transition.

## Q404: Omeprazole loading dose Peptic Ulcer Disease emergency

**Stratum:** miss. **Categories:** intent mismatch;missing contextual constraint;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Peptic Ulcer Disease", "molecule_entity": "Omeprazole", "drug_class_entity": "Proton pump inhibitors", "intent": "Dosing / Administration", "dose_context_flag": true}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C150 | 1 | unjudged | Practical Guide: Initiating Omeprazole in Peptic Ulcer Disease |
| retrieved top 3 | C157 | 2 | unjudged | Profil Keamanan Lansoprazole pada Peptic Ulcer Disease |
| retrieved top 3 | C147 | 3 | unjudged | National Guideline: Peptic Ulcer Disease Diagnosis and Treatment |
| strongest observed positive | C042 | 91 | 3 | Atrial Fibrillation in Special Populations: Practical Guidance |
| strongest observed positive | C049 | 96 | 3 | Safety Profile of Furosemide in Nephrotic Syndrome |
| plausible inspection candidate | C150 | 1 | unjudged | Practical Guide: Initiating Omeprazole in Peptic Ulcer Disease |

C150 matches Omeprazole/PUD initiation but omits loading dose and emergency context. C157 changes molecule to Lansoprazole.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Obtain administration details and evaluate loading/emergency constraints.

## Q418: monitoring Xanthine oxidase inhibitors pada Psoriatic Arthritis parameter apa

**Stratum:** miss. **Categories:** partial entity match;intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Psoriatic Arthritis", "molecule_entity": "Allopurinol", "drug_class_entity": "Xanthine oxidase inhibitors", "intent": "Monitoring / Response / Risk Assessment"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C218 | 1 | unjudged | Profil Keamanan Colchicine pada Psoriatic Arthritis |
| retrieved top 3 | C226 | 2 | unjudged | Safety Profile of Ibuprofen in Psoriatic Arthritis |
| retrieved top 3 | C227 | 3 | unjudged | Consensus Statement: NSAIDs Use in Psoriatic Arthritis |
| strongest observed positive | C231 | 263 | 2 | Dose Adjustment of Apixaban in Renal and Hepatic Impairment |

Safety titles for Colchicine and Ibuprofen and an NSAID consensus preserve Psoriatic Arthritis but miss the requested class and monitoring parameters.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test class coverage and monitoring intent; audit corpus gaps.

## Q443: prophylaxis Schizophrenia Risperidone kapan bisa dihentikan

**Stratum:** miss. **Categories:** intent mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Schizophrenia", "molecule_entity": "Risperidone", "drug_class_entity": "Atypical antipsychotics", "intent": "Prophylaxis / Maintenance"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C163 | 1 | unjudged | Risperidone: Pharmacology, Dosing, and Clinical Use in Schizophrenia |
| retrieved top 3 | C179 | 2 | unjudged | Case Report: Atypical Presentation of Schizophrenia |
| retrieved top 3 | C177 | 3 | unjudged | Successful Management of Severe Schizophrenia with Clozapine |
| strongest observed positive | C299 | 299 | 2 | Diazepam in Febrile Seizure: Real-World Outcomes |
| plausible inspection candidate | C163 | 1 | unjudged | Risperidone: Pharmacology, Dosing, and Clinical Use in Schizophrenia |

C163 is general Risperidone pharmacology/dosing, not an explicit stopping-prophylaxis title; the observed positive concerns Diazepam/seizures.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Inspect full text for maintenance criteria; audit behavioral label.

## Q454: switch dari Meropenem ke Vancomycin Sepsis progresif

**Stratum:** miss. **Categories:** partial entity match;intent mismatch;severity mismatch;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Sepsis", "molecule_entity": "Meropenem; Vancomycin", "drug_class_entity": "Carbapenems; Glycopeptides", "intent": "Treatment Change / Escalation"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C309 | 1 | 0 | Profil Keamanan Meropenem pada Sepsis |
| retrieved top 3 | C319 | 2 | unjudged | Safety Profile of Meropenem in Sepsis |
| retrieved top 3 | C314 | 3 | unjudged | Dose Adjustment of Vancomycin in Renal and Hepatic Impairment |
| strongest observed positive | C117 | 129 | 3 | Safety Profile of Bedaquiline in MDR Tuberculosis |

Meropenem safety titles and Vancomycin renal dosing omit the requested switch and progressive Sepsis.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test both-drug coverage and escalation compatibility.

## Q480: Venlafaxine dosing in Major Depressive Disorder with atrial fibrillation

**Stratum:** hit. **Categories:** partial entity match;intent mismatch;missing contextual constraint;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Major Depressive Disorder", "molecule_entity": "Venlafaxine", "drug_class_entity": "SNRIs", "intent": "Dosing / Administration", "dose_context_flag": true}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C171 | 1 | unjudged | Perbandingan Venlafaxine dan Venlafaxine pada Major Depressive Disorder |
| retrieved top 3 | C182 | 2 | unjudged | Sertraline: Pharmacology, Dosing, and Clinical Use in Major Depressive Disorder |
| retrieved top 3 | C170 | 3 | unjudged | Major Depressive Disorder in hypertension: Special Considerations |
| strongest observed positive | C045 | 219 | 3 | Metoprolol pada Pasien Heart Failure: Studi Kohort |
| strongest observed positive | C162 | 114 | 3 | Biomarkers in Schizophrenia: Implications for Atypical antipsychotics Therapy |
| observed top-10 hit | C180 | 4 | 1 | Risk Stratification in Major Depressive Disorder: Current Approaches |

C171 is a Venlafaxine self-comparison, C182 names Sertraline dosing, and C170 discusses hypertension rather than atrial fibrillation. The observed hit is general depression risk stratification.

**Behavioral evidence:** strongest observed positive title is off-topic.

**Next check:** Test exact molecule plus dosing/comorbidity evidence.

## Q485: Lansoprazole resistance in Peptic Ulcer Disease alternative therapy

**Stratum:** hit. **Categories:** intent mismatch;severity mismatch.

**Decomposition:** `{"disease_entity": "Peptic Ulcer Disease", "molecule_entity": "Lansoprazole", "drug_class_entity": "Proton pump inhibitors", "intent": "Treatment Change / Escalation", "prior_treatment_failure_flag": true}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C157 | 1 | unjudged | Profil Keamanan Lansoprazole pada Peptic Ulcer Disease |
| retrieved top 3 | C149 | 2 | unjudged | Switching Therapy in Peptic Ulcer Disease: A Step-by-Step Guide |
| retrieved top 3 | C156 | 3 | unjudged | Switching Therapy in Peptic Ulcer Disease: A Step-by-Step Guide |
| strongest observed positive | C143 | 5 | 2 | Consensus Statement: Proton pump inhibitors Use in Peptic Ulcer Disease |
| observed top-10 hit | C143 | 5 | 2 | Consensus Statement: Proton pump inhibitors Use in Peptic Ulcer Disease |
| plausible inspection candidate | C149 | 2 | unjudged | Switching Therapy in Peptic Ulcer Disease: A Step-by-Step Guide |

C157 safety outranks C149/C156 switching guides. Their metadata includes Lansoprazole, making them plausible intent-aware alternatives, though resistance-specific detail is unverified.

**Behavioral evidence:** broad same-disease positive; exact intent unverified.

**Next check:** Test intent plus supplied entities; inspect full text for resistance.

## Q493: monitoring parameters Isoniazid in Tuberculosis

**Stratum:** no_positive. **Categories:** partial entity match;weak behavioral ground truth.

**Decomposition:** `{"disease_entity": "Tuberculosis", "molecule_entity": "Isoniazid", "drug_class_entity": "Antituberculotics", "intent": "Monitoring / Response / Risk Assessment"}`

| Role | Content | Rank | Grade | Title |
| --- | --- | ---: | --- | --- |
| retrieved top 3 | C229 | 1 | unjudged | Monitoring Parameters for Bisphosphonates in Osteoporosis |
| retrieved top 3 | C151 | 2 | unjudged | Monitoring Parameters for Nitroimidazoles in Inflammatory Bowel Disease |
| retrieved top 3 | C090 | 3 | unjudged | Monitoring Parameters for Fatty acid derivatives in Parkinson Disease |

Exact monitoring-template wording retrieves Bisphosphonates/Osteoporosis and unrelated classes ahead of Isoniazid/Tuberculosis. No inspected title names Isoniazid.

**Behavioral evidence:** no observed positives.

**Next check:** Test entity coverage and obtain missing drug-specific content.
