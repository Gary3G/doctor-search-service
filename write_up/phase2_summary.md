# Phase 2 Summary: Intent Taxonomy Refinement

## Approach

Phase 2 refined the ten literature seed intents into eleven operational Docquity intents. Every proposed class has at least 20 provisional examples, but these counts are taxonomy-analysis estimates rather than gold annotations. Gold-set labeling remains a separate Phase 3 task.

The analysis used the physician-search taxonomy in [Monsalve et al. (2026)](https://doi.org/10.64898/2026.06.26.26356340) as the top-level seed. The finer therapy, caution, efficacy, diagnosis, description, etiology, prognosis, and interpretation distinctions in [Liang et al. (2025)](https://doi.org/10.1038/s41598-025-25783-x) informed candidate sub-intents. Neither published label set was copied unchanged.

Disease, molecule, and drug-class strings were replaced with placeholders before intent representation so disease topic did not drive intent clusters. Word unigram/bigram TF-IDF supplied interpretable lexical evidence. A frozen `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` encoder produced 384-dimensional vectors for all 500 English, Bahasa Indonesia, and mixed-language queries and for the full semantic definitions of the seed and candidate intents. Embeddings were computed on CPU and cached.

Final-intent support was derived with an explicit CPU adaptation of Liang et al.'s three-branch architecture:

1. the contextual branch uses frozen multilingual query-to-candidate semantic similarity;
2. the sentence branch uses Liang's 200-feature TF-IDF representation;
3. the category branch uses TF-IDF centroids estimated per candidate intent.

The three class-score vectors are independently projected into a shared 64-dimensional space. Learned sample-wise attention weights the semantic, sentence-TF-IDF, and class-centroid branches. A nonlinear classification head with dropout 0.2 and class-weighted cross-entropy produces the final model assignment. Previous-round soft predictions refresh the class centroids, implementing a leakage-avoiding soft-prototype refinement.

Liang's published model is supervised and fine-tunes Chinese RoBERTa. Phase 2 has no gold intent labels and is CPU-first, so this implementation freezes multilingual MiniLM and substitutes ordered, delexicalized boundary rules for the paper's gold training labels. A stratified holdout is used during attention-model selection. Its scores measure agreement with weak pseudo-labels—not clinical accuracy. On that holdout, semantic, sentence-TF-IDF, class-centroid-TF-IDF, and full attention fusion achieved macro-F1 values of 0.529, 0.864, 0.913, and 0.995 against the weak labels, respectively. After soft-centroid refinement, the final hybrid assignments agree with weak anchors on 95.4% of queries; the 23 disagreements are retained for Phase 3 adjudication.

Prototype cosine similarity supplied only provisional nearest-intent suggestions. The difference between the top two prototype scores formed an ambiguity margin used to prioritize review; it is not calibrated confidence. Independent agglomerative cosine clustering was selected over `k=8..15`, with KMeans retained as a comparison. The selected solution had 15 clusters and cosine silhouette 0.359. Each cluster was explained with top TF-IDF unigrams/bigrams, representative queries, nearest prototypes, and distributions for all 13 structured query features.

Taxonomy decisions used semantic, lexical, structured, model-support, retrieval-preference, and manual-review evidence. The explicit seed-to-final mapping is stored in `phase2_seed_to_final_derivation.csv`. The review covered 110 representative or boundary queries, 50 low-margin queries, and 40 nearest cross-class neighbor pairs. This was a single-analyst clinical-coherence review, not an independent clinician annotation or inter-annotator agreement study.

## Key Findings

| Intent | Parent | Operational definition | Inclusion criteria | Exclusion criteria | Likely content preference | Provisional n |
| --- | --- | --- | --- | --- | --- | ---: |
| Management / Treatment Selection | Management / Treatment | Select, initiate, or sequence treatment for a named condition. | First-line choice, best therapy, algorithm, when to start. | Dose, safety, explicit guideline lookup, failure-driven switching. | Treatment algorithms, recommendations, treatment overviews. | 58 |
| Dosing / Administration | Pharmacotherapy | Determine dose, titration, loading regimen, route, or dose adjustment. | Dose/dosis, titration, loading dose, renal/hepatic/age adjustment. | General safety without a requested regimen. | Drug monographs, dosing tables, adjustment references. | 99 |
| Safety / Contraindication | Pharmacotherapy | Assess adverse effects, contraindications, pregnancy safety, or suitability with comorbidity. | Safe/aman, contraindication, adverse/side effect, pregnancy safety. | Explicit interaction or requested regimen. | Safety monographs, contraindication sections, adverse-effect reviews. | 73 |
| Interaction / Combination | Pharmacotherapy | Assess drug interaction or combination-therapy rationale/safety. | Drug interaction/interaksi obat, combination therapy/kombinasi. | Head-to-head alternatives not intended for co-administration. | Interaction databases, combination evidence, compatibility references. | 24 |
| Comparative Treatment Choice | Pharmacotherapy | Compare two treatments for relative efficacy or preferred choice. | Versus/vs, compare, `mana lebih efektif`. | Co-administration interaction or single-treatment efficacy. | Head-to-head trials, meta-analyses, comparative reviews. | 23 |
| Monitoring / Response / Risk Assessment | Management / Treatment; Epidemiology / Prognosis | Select monitoring parameters, assess response, or perform risk stratification. | Monitoring parameters, biomarkers, risk stratification. | Adverse-effect lists without a monitoring decision; long-term efficacy. | Monitoring protocols, biomarkers, risk scores/calculators. | 40 |
| Efficacy / Outcomes | Pharmacotherapy; Epidemiology / Prognosis | Assess therapeutic effect or clinical/long-term outcomes. | Efficacy, clinical outcome data, long-term outcomes. | Head-to-head comparison; maintenance after target attainment. | Trials, systematic reviews, outcome cohorts. | 20 |
| Guideline / Evidence Lookup | Evidence / Guideline Lookup | Retrieve an explicit guideline, recent update, evidence summary, or year-constrained recommendation. | Guideline/panduan, latest/terbaru, evidence, year/update. | Clinical choice without evidence or recency request. | Guidelines, consensus statements, recent evidence. | 59 |
| Treatment Change / Escalation | Management / Treatment | Change, add, or escalate after failure, resistance, or progression. | Switch, substitution, add-on, failure, resistance, alternative. | Initial first-line choice or maintenance after success. | Step-up algorithms, refractory guidance, alternative-regimen evidence. | 44 |
| Prophylaxis / Maintenance | Management / Treatment | Prevent disease/recurrence, determine prophylaxis duration, or maintain after target attainment. | Prophylaxis/profilaksis, when to stop, target attained/maintenance. | Active-disease first-line treatment or switching after failure. | Prevention guidelines, prophylaxis durations, maintenance protocols. | 31 |
| Mechanism / Background Knowledge | New dataset-specific class | Explain mechanism of action, pathophysiology, or mechanistic role. | Mechanism/cara kerjanya, mechanism of action, pathophysiology. | Clinical efficacy, treatment selection, diagnosis. | Mechanistic reviews, pharmacology references, explainers. | 29 |

Positive and boundary examples for every class are in `outputs/taxonomy/phase2_final_taxonomy.csv` and are displayed in `notebook.ipynb`.

Broad Pharmacotherapy splits into dosing, safety, interaction/combination, comparison, efficacy/outcomes, and monitoring-related needs because these favor different content. Broad Management splits into initial treatment selection, failure-driven change/escalation, and prophylaxis/maintenance. Evidence / Guideline Lookup is renamed for the language actually observed. Mechanism / Background Knowledge is added as a coherent dataset-specific intent.

The sparse eight-query risk-stratification pocket merges with Monitoring / Response Assessment, where the likely retrieval preference is validated protocols, risk scores, and decision tools. Diagnosis, work-up/test selection, result interpretation, procedures/techniques, and patient communication/education are not retained as learnable classes because no coherent query pocket supports them. `Other / Ambiguous` remains available as an annotation fallback but is not treated as a trainable class from the current sample.

## Honest Evaluation

The supplied queries are highly template-patterned. High cluster coherence and weak-label agreement may therefore reflect generation templates as well as natural physician information needs. Candidate class names and boundary rules remain analyst hypotheses: the hybrid model estimates their support but cannot invent or clinically validate meaningful labels. Its probabilities are not calibrated confidence. Phase 3 must independently annotate boundary cases and report agreement rather than treating Phase 2 model assignments as gold labels.

Retrieval distinctness is reasoned from likely content preferences in this phase. Later retrieval experiments must test whether the proposed intent distinctions actually improve ranking.

Phase 2 provides an explicit, reproducible path from seed intents to a model-supported final schema, but it does not establish clinical ground truth. Liang et al.'s original method is supervised and fine-tunes RoBERTa; this implementation instead uses weak labels and frozen multilingual embeddings to satisfy the CPU-first constraint. Consequently, the reported metrics measure agreement with heuristic pseudo-labels rather than true clinical accuracy. The highly template-patterned queries also make lexical and centroid performance look unusually strong. Model probabilities are not calibrated, and the 23 model-versus-anchor disagreements still require adjudication.

## What I Would Do Differently

I would annotate a small, stratified clinical pilot set before training the fusion model, with deliberate coverage of dose-versus-safety, guideline-versus-treatment, adverse-effect monitoring, and other multi-intent boundaries. I would use this set to replace weak-label validation with clinical evaluation, tune taxonomy thresholds, calibrate confidence, and measure inter-annotator agreement. I would also compare the hybrid model with simpler TF-IDF and frozen-embedding classifiers under grouped splits that keep near-duplicate templates together, reducing optimistic results caused by template leakage. Finally, I would test whether each retained intent changes preferred content or improves retrieval before treating it as production-relevant.
