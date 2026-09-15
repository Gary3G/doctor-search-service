# Phase 4 Summary: Intent Classification Baseline

## Approach

The purpose of Phase 4 is to establish a simple, transparent text-classification baseline before adding entity, contextual, character-level, or semantic features in Phase 5. The implemented model is word unigram/bigram TF-IDF followed by class-balanced Logistic Regression. It uses only `query_text`; supplied entities, contextual slots, Phase 3 rules, prototype scores, cluster assignments, and agreement metadata are not model inputs.

The model uses the Phase 3 weak labels, excluding only the 138 three-way disagreements. This leaves 362 training and evaluation rows:

1. **Unanimous:** 151 queries where rule, prototype, and cluster agree.
2. **Two-signal agreement including rule:** 127 queries.
3. **Prototype and cluster against rule:** 84 queries.

For the third group, the target remains the frozen Phase 3 schema-adjudicated rule label. These rows are deliberately retained under the non-three-way policy, but they remain marked as low-confidence rule-versus-semantic conflicts. Prototype and cluster agreement is not equivalent to two independent annotations because both channels use the same frozen embedding representation.

I use two complementary evaluation designs:

1. **Five-fold stratified weak-label cross-validation.** All 11 intents occur in every training and test partition. This measures how reliably the baseline reproduces the operational weak-label policy. Similar entity-delexicalized query templates can occur across folds.
2. **Two-fold template-grouped sensitivity analysis.** All queries with the same delexicalized form are assigned to one fold, producing zero template overlap. This measures transfer to unseen query formulations. It covers 354 queries and 10 intents because the retained Monitoring / Response / Risk Assessment examples reduce to a single template and therefore cannot occur in both grouped training and test sets.

After cross-validation, the deployable baseline artifact is refitted on all 362 retained weak-label rows. Out-of-fold predictions, fold metrics, per-class results, confusion matrices, top coefficients, taxonomy checks, and error rows are exported for audit and later comparison.

## Key Findings

The baseline almost perfectly reproduces weak labels under ordinary stratified cross-validation, but performance falls sharply when query templates are held out.

| Evaluation | Queries | Intents | Template overlap | Macro precision | Macro recall | Macro F1 | Weighted F1 | Accuracy |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| Five-fold weak-label CV | 362 | 11 | Yes | 0.991 | 0.972 | **0.981** | 0.983 | 0.983 |
| Two-fold template-grouped sensitivity | 354 | 10 | No | 0.570 | 0.502 | **0.509** | 0.522 | 0.548 |

Top-level intent performance is 0.981 Macro F1 in weak-label CV, while top-level accuracy rises to 0.994. Four of the six subtype mistakes remain inside the broader Pharmacotherapy parent, but rare multi-parent categories keep the macro average sensitive to the other errors.

The 362 rows collapse to only 91 entity-delexicalized templates. Eight intents have fewer than five distinct templates, and Monitoring / Response / Risk Assessment has eight rows but only one template. The 0.472 absolute Macro-F1 gap between evaluation designs is therefore the central Phase 4 finding: the lexical model learns recurring query forms very effectively, but does not generalize nearly as well to new formulations.

### Per-class performance

| Intent | Weak-label n | Templates | Weak-label CV F1 | Template-held-out F1 |
| --- | ---: | ---: | ---: | ---: |
| Management / Treatment Selection | 50 | 20 | 1.000 | 0.600 |
| Dosing / Administration | 94 | 16 | 0.979 | 0.596 |
| Safety / Contraindication | 59 | 30 | 0.966 | 0.504 |
| Interaction / Combination | 21 | 4 | 0.976 | 0.343 |
| Comparative Treatment Choice | 23 | 4 | 1.000 | 0.712 |
| Monitoring / Response / Risk Assessment | 8 | 1 | 1.000 | Not evaluable |
| Efficacy / Outcomes | 20 | 2 | 1.000 | 0.000 |
| Guideline / Evidence Lookup | 6 | 3 | 0.909 | 0.909 |
| Treatment Change / Escalation | 21 | 4 | 0.976 | 0.323 |
| Prophylaxis / Maintenance | 31 | 4 | 1.000 | 0.655 |
| Mechanism / Background Knowledge | 29 | 3 | 0.983 | 0.450 |

Guideline / Evidence Lookup remains relatively robust under template holdout, although its six-query support is too small for a stable conclusion. Efficacy / Outcomes falls from perfect weak-label CV performance to zero template-held-out F1. Treatment Change / Escalation, Interaction / Combination, and Mechanism / Background Knowledge also show substantial transfer failures.

### Failure cases

Only six of 362 predictions are incorrect in weak-label CV. They nevertheless expose useful intent boundaries:

| Query | Weak target | Prediction | Interpretation |
| --- | --- | --- | --- |
| `resistensi Methyldopa ... alternatif Methyldopa` | Treatment Change / Escalation | Safety / Contraindication | Pregnancy context distracts from the resistance/switch request. |
| `Hypertension in Pregnancy pediatric dosing Methyldopa` | Dosing / Administration | Safety / Contraindication | Pregnancy language overwhelms the explicit dosing cue. |
| `Calcium channel blockers new evidence Hypertension 2022` | Guideline / Evidence Lookup | Mechanism / Background Knowledge | A rare guideline formulation lacks the more common guideline template. |
| `Ferrous sulphate drug interaction with Erythropoietin ...` | Interaction / Combination | Dosing / Administration | This interaction wording is mistaken for a medication-use question despite the explicit cue. |
| `dosis Apixaban ... pasien CKD aman tidak` | Safety / Contraindication | Dosing / Administration | Explicit dose and safety cues compete; the boundary rule selects Safety. |
| `is Bedaquiline safe ... with hepatic impairment` | Safety / Contraindication | Dosing / Administration | Organ-impairment language resembles dose-adjustment queries. |

The template-held-out analysis reveals a broader failure pattern hidden by the six row-CV errors. The largest confusion is bidirectional Dosing versus Safety: 20 Safety queries are predicted as Dosing, while 15 Dosing queries are predicted as Safety. Efficacy / Outcomes is never correctly predicted under template holdout and is most often assigned to Dosing, Safety, or Comparative Treatment Choice. Treatment Change / Escalation and Mechanism / Background Knowledge also collapse toward the frequent Dosing and Safety classes when their familiar lexical forms are absent.

Row-CV accuracy is 99.3% for unanimous labels, 97.6% for two-signal-including-rule labels, and 97.6% for prototype/cluster-against-rule labels. English accuracy is 97.5%, compared with 98.9% for Bahasa Indonesia and 99.1% for mixed-language queries. These differences are descriptive only because template composition and class distribution differ across slices.

## Honest Evaluation

The 0.981 Macro F1 is excellent evidence that a lightweight lexical classifier can reproduce the current weak-label policy. It is not evidence that intent labels are 98% clinically correct. The targets were generated through a model-assisted schema workflow rather than assigned independently by qualified clinicians, so systematic rule or taxonomy errors can be learned and rewarded during evaluation.

The primary cross-validation result also benefits from near-duplicate template reuse. The queries were not deleted because grouping preserves entity and language variants, but the retained weak-label set cannot support leakage-free evaluation of all 11 intents: Monitoring has only one independent template. Consequently, the 0.981 result should be called **weak-label agreement**, while the 0.509 grouped result is the stronger—though still limited—test of linguistic generalization.

The grouped sensitivity estimate is itself imperfect. It excludes Monitoring, uses only two folds, and several remaining intents have only two to four templates. One template can therefore move an entire class metric substantially. It is better treated as a stress test than as a precise production-performance estimate.

The 84 prototype/cluster-against-rule cases introduce an additional source of label uncertainty. Their final targets follow the explicit schema rule, while both semantic signals prefer another intent. Since prototype and cluster share an encoder, this is not a clean two-against-one human disagreement; nevertheless, these cases are useful candidates for later manual failure analysis.

Finally, the dataset contains no `Other / Ambiguous` examples. The fitted classifier is forced to choose one of the 11 supported intents for every input and has no evidence for abstention, genuinely ambiguous requests, or novel intent classes.

## What I Would Do Differently

I would obtain independent labels from at least two qualified clinical annotators for a template-diverse evaluation set. Annotators would be blinded to the rule, prototype, cluster, and classifier outputs. Disagreements would be adjudicated separately, producing a defensible clinical gold set rather than measuring agreement with weak supervision.

I would collect or author additional formulations for the sparsest intent-template combinations, especially Monitoring / Response / Risk Assessment, Efficacy / Outcomes, Guideline / Evidence Lookup, Mechanism / Background Knowledge, and Treatment Change / Escalation. At least five independent templates per class would make grouped cross-validation more stable and allow all 11 intents to participate.

For model development, I would freeze the current folds before Phase 5 and compare every representation under both protocols. The key improvement criterion should be template-held-out Macro F1 rather than the nearly saturated weak-label CV score. Character n-grams, supplied entity features, contextual slots, and frozen multilingual sentence embeddings should be evaluated incrementally so the source of any gain remains attributable.

I would also use template-balanced sample weights, such as `1 / template frequency`, to prevent repeated entity-swapped forms from dominating training without discarding useful examples. Performance should be sliced by agreement type, language, intent, template novelty, and label confidence. Probability calibration and an abstention threshold should be evaluated once manually adjudicated ambiguous examples are available.
