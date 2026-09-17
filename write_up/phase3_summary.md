# Phase 3 Summary: Intent Labeling

## Approach

The assessment criterion asks me to **label a subset of the 500 queries with the intent schema** and allows a manual, model-assisted, rule-based, or combined strategy, provided the approach and its limitations are explicit. I satisfy this requirement with a **combined labeling strategy**. I created a 60-query pilot and expanded it into a 180-query reviewed reference subset using the 11-intent schema developed in Phase 2. The pilot is included in the 180 rows. I then produced labels for all 500 queries so later classification and retrieval phases have a complete working dataset, although only the 180-row subset is treated as reviewed reference data.

The 180-query subset was selected using both uncertainty and coverage sampling. Uncertainty sampling prioritizes three-way signal disagreements, cases where the two semantic signals disagree with the rule signal, Phase 2 model disagreements, low prototype margins, multi-cue boundaries, and rare intents. Coverage sampling spans all 11 final intents, English, Bahasa Indonesia, mixed-language queries, all 15 therapeutic areas, short/medium/long queries, entity composition, contextual-slot complexity, and all 15 Phase 2 clusters. Every retained intent has at least 12 reviewed examples.

The combined strategy uses three algorithmic signals:

1. **Rule signal.** Ordered bilingual patterns detect explicit information-need cues such as `dose`, `aman`, `guideline`, `vs`, `interaksi obat`, `monitoring`, and `mechanism`. The ordering encodes documented boundary decisions, such as comparison taking priority over single-treatment efficacy and explicit guideline recency taking priority over generic treatment selection.
2. **Prototype signal.** Each delexicalized query is compared by cosine similarity with complete semantic definitions of the 11 final intents using cached frozen multilingual MiniLM embeddings. This supplies a query-level semantic suggestion without fitting a classifier on Phase 3 labels.
3. **Cluster signal.** Phase 3 reuses the 15 agglomerative query clusters discovered in Phase 2. It does not recluster the data. Each anonymous cluster is initially mapped to the nearest final-intent prototype using its embedding centroid. Coordinate search then adjusts the cluster-to-intent mapping to maximize Fleiss' kappa across the rule, prototype, and cluster signal outputs; semantic centroid similarity breaks exact objective ties.

The final `intent` column is the operational 11-class label. `queries_labeled.csv` contains the original query table plus only this label column. The broader parent, contextual slots, decision signals, confidence, provenance, and review fields are kept in `outputs/queries_with_intent_metadata.csv`. Unanimous and rule-plus-model agreements provide model assistance. When the prototype and cluster signals conflict with an explicit rule, the rule is retained as the schema adjudication and the row receives lower confidence and a review flag instead of being silently overwritten. If no rule matches, semantic plurality is the fallback.

This is a single model-assisted analyst workflow, not independent clinician annotation. For that reason, I describe the 180 rows as a **reviewed reference subset**, not clinical gold labels, and I do not claim inter-annotator agreement.

## Key Findings

The pipeline labels all 500 queries and retains all 11 Phase 2 intents. The reviewed reference subset contains 180 queries, including the 60-query pilot, while the remaining 320 rows use the frozen three-signal policy. No supplied query required the `Other / Ambiguous` fallback.

Optimizing the cluster-to-schema mapping increased in-sample Fleiss' kappa from 0.324 to 0.357. After optimization, pairwise Cohen kappas were 0.460 for rule versus prototype, 0.284 for rule versus cluster, and 0.377 for prototype versus cluster. Across all queries, 151 had unanimous signals, 127 had a two-signal agreement that included the rule, 84 had prototype/cluster agreement against the rule, and 138 produced three different signal labels. These disagreements are preserved as audit information rather than hidden.

| Intent | Parent | Final n | Reviewed n |
| --- | --- | ---: | ---: |
| Management / Treatment Selection | Management / Treatment | 58 | 13 |
| Dosing / Administration | Pharmacotherapy | 96 | 14 |
| Safety / Contraindication | Pharmacotherapy | 84 | 34 |
| Interaction / Combination | Pharmacotherapy | 21 | 12 |
| Comparative Treatment Choice | Pharmacotherapy | 23 | 12 |
| Monitoring / Response / Risk Assessment | Management / Treatment; Epidemiology / Prognosis | 33 | 14 |
| Efficacy / Outcomes | Pharmacotherapy; Epidemiology / Prognosis | 20 | 12 |
| Guideline / Evidence Lookup | Evidence / Guideline Lookup | 59 | 33 |
| Treatment Change / Escalation | Management / Treatment | 46 | 12 |
| Prophylaxis / Maintenance | Management / Treatment | 31 | 12 |
| Mechanism / Background Knowledge | New dataset-specific class | 29 | 12 |

The final class counts differ from the provisional Phase 2 model counts because Phase 3 applies the frozen annotation boundaries. Typical adjudications place adverse-effect surveillance under Safety rather than routine Monitoring, response biomarkers under Monitoring rather than Safety, contraindication questions under Safety rather than Dosing, and resistance or failure queries under Treatment Change / Escalation rather than Interaction.

The main outputs are `queries_labeled.csv`, `outputs/queries_with_intent_metadata.csv`, `phase3_gold_annotations.csv`, `phase3_three_signal_assignments.csv`, `phase3_signal_disagreements_adjudicated.csv`, `phase3_annotation_guidelines.csv`, `phase3_cluster_intent_mapping.csv`, and `phase3_kappa_diagnostics.json`.

## Honest Evaluation

The criterion permits a combined labeling strategy, and this implementation is explicit and reproducible: the reviewed subset, sampling reasons, three raw signals, confidence, provenance, rule matches, plurality, final adjudication, and disagreement status are all exported. It is stronger than blind pseudo-labeling because disagreements remain visible and explicit schema boundaries are not silently replaced by an opaque score.

However, the 180 labels were not independently assigned by qualified clinicians. The workflow is model-assisted and uses a schema-guided rule adjudication, so systematic errors in the taxonomy or boundary rules can remain in the reference subset. The Phase 2 weak model, Phase 3 rules, and final labels are also related; agreement between them is not independent evidence of accuracy.

The three signals are operationally separate but not statistically independent. The prototype and cluster signals share the same frozen multilingual embedding encoder, and the Phase 3 cluster signal reuses the Phase 2 cluster partition. Furthermore, the cluster-to-schema mapping is optimized on all 500 signal triples. The reported kappa is therefore an in-sample algorithmic agreement statistic, not inter-annotator reliability, held-out performance, or clinical validity. Maximizing kappa can make systems agree on the same error.

The supplied queries are highly template-patterned and every query contains an explicit supported cue. This makes deterministic rules unusually effective and explains why `Other / Ambiguous` has no examples. Natural physician traffic may contain implicit intent, misspellings, unfamiliar code-switching, novel phrasing, or genuinely equal multi-intent needs. The current single-label hierarchy cannot represent two equally important requests, and `label_confidence` is qualitative rather than calibrated.

Finally, the cluster signal is coarse. A single label is assigned to every member of a cluster, even though the largest Phase 2 cluster contains heterogeneous query templates. Cluster evidence is consequently used for agreement and review prioritization rather than treated as ground truth.

## What I Would Do Differently

I would ask two qualified clinical annotators to label the 180-query subset independently while blinded to the rule and model outputs. I would then measure Cohen's kappa between the human annotators, report per-class disagreements, and adjudicate unresolved cases with a third reviewer. That would provide a defensible gold set and a meaningful reliability statistic.

I would fit the cluster-to-schema mapping on the pilot or a development split and report kappa on a separate held-out subset instead of optimizing and evaluating agreement on the same 500 signal triples. I would also test mapping stability under bootstrap resampling and report whether small sample changes alter the selected cluster labels.

To make the signals more independent, I would build the cluster representation from a different feature family, such as delexicalized character/word TF-IDF, while retaining multilingual embeddings for prototype matching. I would compare this with the current shared-encoder implementation and select the design using held-out human annotations rather than algorithmic agreement alone.

For the remaining queries, I would train the Phase 4 CPU baseline—word and character TF-IDF with Logistic Regression—on the adjudicated human subset. I would accept high-confidence rule/classifier agreements, manually review low-confidence or disagreement cases, and evaluate with template-grouped splits so near-duplicate query templates cannot inflate performance.
