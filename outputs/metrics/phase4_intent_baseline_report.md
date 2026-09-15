# Phase 4: Intent Classification Baseline

## Outcome

The text-only TF-IDF + Logistic Regression baseline reaches **0.981 macro F1** in five-fold cross-validation over 362 Phase 3 weak labels after excluding the 138 three-way disagreements. Macro precision is 0.991, macro recall is 0.972, weighted F1 is 0.983, and accuracy is 0.983. These numbers measure agreement with the weak-label policy, not clinical accuracy. Accuracy is retained only as a secondary descriptive metric.

The broader top-level intent evaluation reaches 0.981 macro F1. This top-level score uses the fixed Phase 2 subtype-to-parent mapping, including the two multi-parent labels retained by the taxonomy.

## Evaluation design

The training set contains 151 unanimous cases, 127 two-signal agreements that include the rule, and 84 prototype-plus-cluster agreements against the rule. The 138 three-way disagreements are excluded. For the 84 rule-versus-semantic conflicts, the target remains the frozen Phase 3 schema-adjudicated rule label; their conflict status remains in the source dataset and is not treated as independent consensus. The estimator is word unigram/bigram TF-IDF followed by class-balanced Logistic Regression (`liblinear`, C=1.0). No supplied entities, contextual slots, embeddings, rules, or Phase 2 signal columns are model inputs.

The weak-label set is highly templated: 362 queries collapse to 91 entity-delexicalized templates. Five-fold stratification is possible by row because every class has at least 6 examples. It cannot also hold out every near-duplicate template while evaluating all 11 classes: Monitoring / Response / Risk Assessment has only one independent template after filtering. Near-identical entity-swapped phrasings therefore cross folds, and the primary score is explicitly a weak-label replication estimate.

As a sensitivity analysis, two-fold template-grouped CV is run on the 10 classes with at least two templates. It has zero template overlap and reaches 0.509 macro F1 and 0.548 accuracy across 354 queries. Monitoring / Response / Risk Assessment is excluded from this diagnostic because unseen-template evaluation is mathematically impossible with one template. The gap between row-stratified and template-held-out results is direct evidence that the model relies heavily on recurring query forms.

## Taxonomy sanity checks

- Final supported classes: 11.
- `Other / Ambiguous`: 0 of 500 (0.0%). It cannot be trained or evaluated because it is unobserved.
- Smallest retained weak-label class: 6 rows.
- Weighted cluster purity against retained weak intent: 0.580.
- Prototype disagreements against the retained schema label: 107.

All 11 observed subtypes are evaluable in row-stratified weak-label CV. Per-class metrics remain descriptive. The following classes have fewer than five independent delexicalized templates and therefore especially limited evidence of linguistic generalization: Interaction / Combination, Comparative Treatment Choice, Monitoring / Response / Risk Assessment, Efficacy / Outcomes, Guideline / Evidence Lookup, Treatment Change / Escalation, Prophylaxis / Maintenance, Mechanism / Background Knowledge.

## Interpretation and limitations

This is a transparent lexical baseline trained on deliberately retained weak supervision, not a clinical-validity estimate. The labels are not independently clinician-annotated, the prototype and cluster signals are correlated, and the cluster mapping was optimized in-sample. High row-stratified performance is expected when label rules and query templates share explicit lexical cues. The grouped sensitivity result, confusion matrix, and error table should guide later failure analysis; none should be used to claim production readiness.
