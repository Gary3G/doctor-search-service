# Phase 2: Literature-Seeded, NLP-Driven Intent Taxonomy Refinement

## Outcome

The 10 literature seed intents were refined into 11 operational Docquity intents. These counts are taxonomy-analysis estimates, not gold labels; Phase 3 remains responsible for annotation.

## Method

- Delexicalized disease, molecule, and drug-class strings before intent representation to reduce topic-driven clusters.
- Fit word unigram/bigram TF-IDF for interpretable lexical evidence.
- Encoded all queries and complete prototype definitions once with frozen `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` on CPU and cached the vectors.
- Implemented Liang et al.'s three branches explicitly: frozen contextual-semantic scores, 200-feature sentence TF-IDF, and category-centroid TF-IDF.
- Projected the three score branches into a shared 64-dimensional space, learned sample-wise inter-branch attention, and used a nonlinear classification head with dropout and class-weighted cross-entropy.
- Because Phase 2 has no gold intents, ordered delexicalized boundary rules replace Liang's gold training labels as weak pseudo-labels. Previous-round soft predictions refresh the class centroids without using a true label at inference.
- Added the 13 requested structured query features from supplied NER and Phase 1.6 slots.
- Used prototype cosine similarity provisionally; the top-two margin prioritizes review and is not calibrated confidence.
- Selected independent agglomerative cosine clustering with k=15 (silhouette=0.359) from k=8..15; KMeans is reported only as a comparison.
- Final support counts come from the Liang-style hybrid predictions, followed by recorded one-analyst coherence review.
- Held-out metrics below measure agreement with weak pseudo-labels, not clinical gold accuracy.

### Liang-Style Branch and Fusion Diagnostics

| model | validation_rows | accuracy_vs_weak_anchor | macro_f1_vs_weak_anchor |
| --- | --- | --- | --- |
| semantic | 100 | 0.53 | 0.5290476383390822 |
| sentence_tfidf | 100 | 0.83 | 0.8644585778206468 |
| class_centroid_tfidf | 100 | 0.89 | 0.9127967991604354 |
| liang_three_branch_attention | 100 | 0.99 | 0.9949141767323585 |

## Seed Taxonomy

| literature_intent | definition | source |
| --- | --- | --- |
| Management / Treatment | Queries asking how to manage a condition, choose treatment, sequence care, or select a first-line intervention. | Monsalve et al. (2026), Clinical Information Needs Among Latin American Physicians: A Multi-Country Analysis of Semantic Clinical Search, medRxiv, https://doi.org/10.64898/2026.06.26.26356340 |
| Diagnosis / Differential Diagnosis | Queries asking which diagnosis explains observed symptoms or how to distinguish plausible diagnoses. | Monsalve et al. (2026), Clinical Information Needs Among Latin American Physicians: A Multi-Country Analysis of Semantic Clinical Search, medRxiv, https://doi.org/10.64898/2026.06.26.26356340 |
| Work-up / Test Selection | Queries asking which diagnostic test, imaging study, laboratory test, or investigation should be ordered next. | Monsalve et al. (2026), Clinical Information Needs Among Latin American Physicians: A Multi-Country Analysis of Semantic Clinical Search, medRxiv, https://doi.org/10.64898/2026.06.26.26356340 |
| Test / Clinical Data Interpretation | Queries asking what an existing laboratory, imaging, ECG, pathology, or other clinical result means. | Monsalve et al. (2026), Clinical Information Needs Among Latin American Physicians: A Multi-Country Analysis of Semantic Clinical Search, medRxiv, https://doi.org/10.64898/2026.06.26.26356340; informed by the metric/interpretation distinction in Liang et al. (2025), A hybrid model integrating RoBERTa, TF-IDF, and attention mechanism for medical query intent classification, Scientific Reports, https://doi.org/10.1038/s41598-025-25783-x |
| Pharmacotherapy | Drug-centered queries about medication choice, dosing, safety, efficacy, interactions, administration, comparison, or monitoring. | Monsalve et al. (2026), Clinical Information Needs Among Latin American Physicians: A Multi-Country Analysis of Semantic Clinical Search, medRxiv, https://doi.org/10.64898/2026.06.26.26356340; finer boundaries informed by therapy, caution, and effect in Liang et al. (2025), A hybrid model integrating RoBERTa, TF-IDF, and attention mechanism for medical query intent classification, Scientific Reports, https://doi.org/10.1038/s41598-025-25783-x |
| Evidence / Guideline Lookup | Queries seeking a guideline, recommendation, current evidence, trial, or date-specific clinical update. | Monsalve et al. (2026), Clinical Information Needs Among Latin American Physicians: A Multi-Country Analysis of Semantic Clinical Search, medRxiv, https://doi.org/10.64898/2026.06.26.26356340 |
| Procedures / Techniques | Queries asking how to perform a clinical procedure, intervention, or bedside technique. | Monsalve et al. (2026), Clinical Information Needs Among Latin American Physicians: A Multi-Country Analysis of Semantic Clinical Search, medRxiv, https://doi.org/10.64898/2026.06.26.26356340 |
| Epidemiology / Prognosis | Queries asking about frequency, risk, natural history, expected outcomes, or prognosis of a condition or treatment. | Monsalve et al. (2026), Clinical Information Needs Among Latin American Physicians: A Multi-Country Analysis of Semantic Clinical Search, medRxiv, https://doi.org/10.64898/2026.06.26.26356340; outcome/prognosis boundary informed by Liang et al. (2025), A hybrid model integrating RoBERTa, TF-IDF, and attention mechanism for medical query intent classification, Scientific Reports, https://doi.org/10.1038/s41598-025-25783-x |
| Patient Communication / Education | Queries asking how to explain a condition, result, treatment, or risk to a patient or caregiver. | Monsalve et al. (2026), Clinical Information Needs Among Latin American Physicians: A Multi-Country Analysis of Semantic Clinical Search, medRxiv, https://doi.org/10.64898/2026.06.26.26356340 |
| Other / Ambiguous | Queries whose information need is unclear, genuinely multi-intent without a primary need, or unsupported by the operational taxonomy. | Monsalve et al. (2026), Clinical Information Needs Among Latin American Physicians: A Multi-Country Analysis of Semantic Clinical Search, medRxiv, https://doi.org/10.64898/2026.06.26.26356340; other-category ambiguity considerations informed by Liang et al. (2025), A hybrid model integrating RoBERTa, TF-IDF, and attention mechanism for medical query intent classification, Scientific Reports, https://doi.org/10.1038/s41598-025-25783-x |

## Taxonomy Decisions

| literature_or_candidate_intent | prototype_top1_count | decision | rationale |
| --- | --- | --- | --- |
| Management / Treatment | 100 | split | Supported but heterogeneous; split selection, change/escalation, prophylaxis/maintenance, and assessment workflows. |
| Diagnosis / Differential Diagnosis | 20 | merge | No coherent diagnosis-seeking template is present; do not retain a zero-support class. |
| Work-up / Test Selection | 0 | merge | No query asks which investigation to order; monitoring is not test selection. |
| Test / Clinical Data Interpretation | 0 | merge | No query supplies an existing result for interpretation. |
| Pharmacotherapy | 254 | split | Strong, retrieval-distinct dose, safety, interaction, comparison, efficacy, and monitoring pockets. |
| Evidence / Guideline Lookup | 41 | rename | Explicit guideline/latest/year language supports an operational Guideline / Evidence Lookup class. |
| Procedures / Techniques | 11 | merge | No coherent procedural-technique pocket is observed. |
| Epidemiology / Prognosis | 74 | merge | Treatment outcomes merge with Efficacy; eight risk queries merge with monitoring/assessment for support. |
| Patient Communication / Education | 0 | merge | No patient-facing explanation or counseling query is observed. |
| Other / Ambiguous | 0 | manual_review | Retain as an annotation fallback, but no standalone learnable class is estimated from this template-rich sample. |
| Mechanism / Background Knowledge | 0 | new_class | A coherent, supported mechanism/pathophysiology pocket has distinct explanatory-content preference. |

## Explicit Seed-to-Final Derivation

| seed_parent_intent | liang_subintent_analogue | candidate_final_intent | derivation_action | candidate_definition_source | liang_model_n_queries | mean_model_probability | mean_model_margin | dominant_independent_cluster_ids | support_decision | final_schema_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Management / Treatment | therapy | Management / Treatment Selection | keep_and_rename | literature seed + Liang analogue + observed Docquity lexical/cluster pattern | 58 | 0.9293 | 0.8934 | 11 | >=20: standalone supported | retain |
| Pharmacotherapy | therapy | Dosing / Administration | split | literature seed + Liang analogue + observed Docquity lexical/cluster pattern | 99 | 0.8254 | 0.7316 | 1; 3; 5; 8; 10 | >=20: standalone supported | retain |
| Pharmacotherapy | caution / precautions | Safety / Contraindication | split | literature seed + Liang analogue + observed Docquity lexical/cluster pattern | 73 | 0.6634 | 0.4993 | 2; 4; 7; 12; 13; 14 | >=20: standalone supported | retain |
| Pharmacotherapy | caution + therapy | Interaction / Combination | split | literature seed + Liang analogue + observed Docquity lexical/cluster pattern | 24 | 0.8896 | 0.8494 | none | >=20: standalone supported | retain |
| Pharmacotherapy | effect / efficacy + therapy | Comparative Treatment Choice | split | literature seed + Liang analogue + observed Docquity lexical/cluster pattern | 23 | 0.9828 | 0.9759 | none | >=20: standalone supported | retain |
| Management / Treatment; Epidemiology / Prognosis | caution + metric interpretation + prognosis | Monitoring / Response / Risk Assessment | merge_sparse_risk_with_monitoring | literature seed + Liang analogue + observed Docquity lexical/cluster pattern | 40 | 0.9417 | 0.9185 | 6; 9 | >=20: standalone supported | retain |
| Pharmacotherapy; Epidemiology / Prognosis | effect / efficacy + outcome / prognosis | Efficacy / Outcomes | split_and_merge | literature seed + Liang analogue + observed Docquity lexical/cluster pattern | 20 | 0.9874 | 0.9812 | none | >=20: standalone supported | retain |
| Evidence / Guideline Lookup | dataset-specific refinement of therapy/other | Guideline / Evidence Lookup | rename | literature seed + Liang analogue + observed Docquity lexical/cluster pattern | 59 | 0.894 | 0.8297 | none | >=20: standalone supported | retain |
| Management / Treatment | therapy | Treatment Change / Escalation | split | literature seed + Liang analogue + observed Docquity lexical/cluster pattern | 44 | 0.9809 | 0.9716 | 0 | >=20: standalone supported | retain |
| Management / Treatment | therapy + caution | Prophylaxis / Maintenance | split | literature seed + Liang analogue + observed Docquity lexical/cluster pattern | 31 | 0.9765 | 0.9688 | none | >=20: standalone supported | retain |
| New dataset-specific class | cause / etiology + disease description | Mechanism / Background Knowledge | new_class | literature seed + Liang analogue + observed Docquity lexical/cluster pattern | 29 | 0.962 | 0.9528 | none | >=20: standalone supported | retain |

## NLP Cluster Analysis

| cluster_id | n_queries | nearest_seed_intent | mean_prototype_similarity | top_terms | dominant_entity_pattern | dominant_liang_final_intent | dominant_intent_share | representative_query_ids | proposed_action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 216 | Management / Treatment | 0.4347 | medicine disease; medicine medicine; vs medicine; vs; medicine vs; kapan; switch; switch medicine; terbaru; prophylaxis; therapy; guideline | entities(disease=1.00, molecule=1.00, drug_class=1.00, multiple_molecules=0.18); comparison_flag=0.11; has_year=0.09; has_pregnancy_context=0.04; negation_flag=0.03 | Treatment Change / Escalation | 0.1991 | Q262; Q006; Q155; Q231; Q328 | manual_review |
| 1 | 34 | Pharmacotherapy | 0.347 | renal; disease renal; renal impairment; impairment; hypertension; disease hypertension; impairment penyesuaian; penyesuaian dosis; penyesuaian; dosis medicine; dosis; adjustment medicine | entities(disease=1.00, molecule=1.00, drug_class=1.00, multiple_molecules=0.00); has_renal_constraint=0.65; has_dose=0.53; negation_flag=0.06; has_route=0.03 | Dosing / Administration | 0.5294 | Q148; Q191; Q019; Q380; Q011 | manual_review |
| 2 | 14 | Pharmacotherapy | 0.3906 | disease diabetes; diabetes; obesity; disease obesity; medicine dosing; dosing disease; safe; safe disease; medicine safe; dosing; kontraindikasi; drug | entities(disease=1.00, molecule=1.00, drug_class=1.00, multiple_molecules=0.00); has_dose=0.21 | Safety / Contraindication | 0.5714 | Q464; Q374; Q497; Q228; Q162 | manual_review |
| 3 | 21 | Pharmacotherapy | 0.3504 | hepatic impairment; hepatic; impairment dose; medicine hepatic; impairment; dose disease; dose; disease hepatic; liver disease; liver; disease liver; drugclass kontraindikasi | entities(disease=1.00, molecule=1.00, drug_class=1.00, multiple_molecules=0.00); has_dose=0.71 | Dosing / Administration | 0.7143 | Q277; Q299; Q050; Q135; Q154 | split |
| 4 | 10 | Pharmacotherapy | 0.3924 | copd; disease copd; ckd; disease ckd; kontraindikasi; kontraindikasi medicine; drug; medicine disease; line drug; line; first line; first | entities(disease=1.00, molecule=1.00, drug_class=1.00, multiple_molecules=0.00); has_dose=0.20; negation_flag=0.10 | Safety / Contraindication | 0.6 | Q233; Q131; Q142; Q450; Q297 | split |
| 5 | 17 | Epidemiology / Prognosis | 0.3726 | toleransi; dosis titrasi; disease toleransi; titrasi; titrasi medicine; protocol medicine; protocol; titration; titration protocol; medicine disease; dosis | entities(disease=1.00, molecule=1.00, drug_class=1.00, multiple_molecules=0.00); has_dose=0.59 | Dosing / Administration | 1.0 | Q220; Q294; Q069; Q110; Q139 | split |
| 6 | 88 | Pharmacotherapy | 0.5442 | monitoring; mechanism; drugclass mechanism; parameters; parameters medicine; monitoring parameters; action; action disease; mechanism action; drugclass terbaru; terbaru disease; pathophysiology | entities(disease=1.00, molecule=1.00, drug_class=1.00, multiple_molecules=0.00); has_year=0.11; has_pregnancy_context=0.06; has_route=0.01 | Monitoring / Response / Risk Assessment | 0.3409 | Q237; Q418; Q498; Q259; Q174 | manual_review |
| 7 | 4 | Evidence / Guideline Lookup | 0.3917 | heart; heart failure; disease heart; failure; kontraindikasi; drugclass kontraindikasi; dosing disease; medicine dosing; kontraindikasi disease; kontraindikasi medicine; dosing; line drug | entities(disease=1.00, molecule=1.00, drug_class=1.00, multiple_molecules=0.00); has_dose=0.25 | Safety / Contraindication | 0.5 | Q125; Q475; Q222; Q132 | manual_review |
| 8 | 13 | Pharmacotherapy | 0.4277 | elderly; disease perlu; perlu; medicine elderly; elderly disease; perlu adjustment; adjustment; disease elderly; drug; elderly pilihan; drug terbaik; terbaik | entities(disease=1.00, molecule=1.00, drug_class=1.00, multiple_molecules=0.00); has_age=1.00; has_dose=0.69; has_pregnancy_context=0.08 | Dosing / Administration | 0.6923 | Q411; Q270; Q249; Q239; Q161 | split |
| 9 | 8 | Epidemiology / Prognosis | 0.4127 | risk stratification; stratification; stratification approach; disease risk; approach; risk | entities(disease=1.00, molecule=1.00, drug_class=1.00, multiple_molecules=0.00); no_context_slot_dominates | Monitoring / Response / Risk Assessment | 1.0 | Q440; Q416; Q397; Q251; Q221 | merge |
| 10 | 33 | Pharmacotherapy | 0.41 | dosis medicine; dosis; loading dose; loading; medicine loading; emergency; disease emergency; anak; disease anak; anak dosis; dose; medicine disease | entities(disease=1.00, molecule=1.00, drug_class=1.00, multiple_molecules=0.00); has_dose=1.00; has_age=0.36; has_pregnancy_context=0.03 | Dosing / Administration | 1.0 | Q349; Q115; Q429; Q165; Q181 | split |
| 11 | 11 | Management / Treatment | 0.3736 | step; step up; up; disease step; algoritma terapi; algoritma; terapi disease; terapi | entities(disease=1.00, molecule=1.00, drug_class=1.00, multiple_molecules=0.00); no_context_slot_dominates | Management / Treatment Selection | 1.0 | Q405; Q389; Q329; Q280; Q217 | keep |
| 12 | 7 | Pharmacotherapy | 0.3443 | anaemia; disease anaemia; medicine contraindication; contraindication disease; contraindication; kontraindikasi; kontraindikasi medicine; drugclass kontraindikasi; kontraindikasi disease; safe disease; medicine safe; safe | entities(disease=1.00, molecule=1.00, drug_class=1.00, multiple_molecules=0.00); no_context_slot_dominates | Safety / Contraindication | 0.5714 | Q434; Q336; Q111; Q013; Q078 | manual_review |
| 13 | 4 | Epidemiology / Prognosis | 0.2766 | atrial; disease atrial; fibrillation; atrial fibrillation; pilihan terapi; medicine dosing; dosing disease; kontraindikasi medicine; dosing; safe; safe disease; medicine safe | entities(disease=1.00, molecule=1.00, drug_class=1.00, multiple_molecules=0.00); has_dose=0.25; has_pregnancy_context=0.25 | Safety / Contraindication | 0.75 | Q026; Q457; Q211; Q480 | split |
| 14 | 20 | Pharmacotherapy | 0.3758 | pregnancy; drugclass pregnancy; pregnancy disease; disease pregnancy; hamil; hamil disease; medicine ibu; ibu hamil; ibu; pregnancy pilihan; pregnancy first; drug | entities(disease=1.00, molecule=1.00, drug_class=1.00, multiple_molecules=0.00); has_pregnancy_context=1.00; has_dose=0.05; negation_flag=0.05 | Safety / Contraindication | 0.8 | Q307; Q365; Q037; Q157; Q203 | split |

## Final Taxonomy and Estimated Support

| intent_name | parent_intent | definition | n_queries | support_decision |
| --- | --- | --- | --- | --- |
| Management / Treatment Selection | Management / Treatment | Select, initiate, or sequence a treatment strategy for a named clinical condition. | 58 | >=20: standalone supported |
| Dosing / Administration | Pharmacotherapy | Determine dose, titration, loading regimen, route, or organ-function/age dose adjustment. | 99 | >=20: standalone supported |
| Safety / Contraindication | Pharmacotherapy | Assess adverse effects, contraindications, pregnancy safety, or suitability with a comorbidity. | 73 | >=20: standalone supported |
| Interaction / Combination | Pharmacotherapy | Assess a drug-drug interaction or the rationale/safety of combination therapy. | 24 | >=20: standalone supported |
| Comparative Treatment Choice | Pharmacotherapy | Compare two named treatments, usually for relative efficacy or preferred choice. | 23 | >=20: standalone supported |
| Monitoring / Response / Risk Assessment | Management / Treatment; Epidemiology / Prognosis | Select monitoring parameters, assess treatment response, or perform clinical risk stratification. | 40 | >=20: standalone supported |
| Efficacy / Outcomes | Pharmacotherapy; Epidemiology / Prognosis | Assess therapeutic effect, clinical outcomes, or long-term outcomes for a treatment. | 20 | >=20: standalone supported |
| Guideline / Evidence Lookup | Evidence / Guideline Lookup | Retrieve an explicit guideline, recent update, evidence summary, or year-constrained recommendation. | 59 | >=20: standalone supported |
| Treatment Change / Escalation | Management / Treatment | Change, add, or escalate treatment because of failure, resistance, or progression. | 44 | >=20: standalone supported |
| Prophylaxis / Maintenance | Management / Treatment | Prevent disease/recurrence, determine prophylaxis duration, or maintain therapy after target attainment. | 31 | >=20: standalone supported |
| Mechanism / Background Knowledge | New dataset-specific class | Explain mechanism of action, pathophysiology, or a treatment's mechanistic role. | 29 | >=20: standalone supported |

## Manual Validation

- Reviewed 110 representative/boundary rows (up to 10 per class).
- Inspected 40 nearest cross-class neighbor pairs.
- The low-margin review queue contains 50 queries; its top-quintile cutoff is 0.0174.
- Liang hybrid predictions agree with weak anchors on 95.4% of rows; disagreements remain review cases rather than silently overwritten labels.
- This is a single-analyst clinical-coherence review, not an independent clinician gold annotation or inter-annotator reliability study.

## Interpretation

Broad Pharmacotherapy should split because dose, safety, interaction, comparison, and outcomes queries request different content. Management likewise separates treatment selection, failure-driven change, and prophylaxis/maintenance. Mechanism / Background Knowledge is a supported dataset-specific class. Sparse risk-stratification queries merge with monitoring/response assessment. Diagnosis, work-up, result interpretation, procedures, and patient education are unsupported in this 500-query sample and should not become learnable classes yet.

## Limitations and Guardrails

- The queries are highly template-patterned; cluster coherence may partly reflect generation templates rather than organic physician language.
- Prototype similarity can be dominated by broad drug language and must not be used as a gold label.
- Candidate intent names remain analyst hypotheses; the hybrid model estimates their query support but does not invent clinically meaningful class names.
- Weak anchor labels replace gold labels in the supervised portions of Liang's method. Reported validation scores are therefore agreement with heuristics, not clinical accuracy.
- Model probabilities are not calibrated confidence; Phase 3 guidelines must adjudicate multi-cue boundaries.
- No final class below 10 examples was retained. The proposed classes satisfy the stated support guideline, but Phase 3 labels may change counts.
- Retrieval distinctness is reasoned from likely content preference in this phase and must be tested empirically in later retrieval phases.

## Sources

- Monsalve et al. (2026): https://doi.org/10.64898/2026.06.26.26356340
- Liang et al. (2025): https://doi.org/10.1038/s41598-025-25783-x
