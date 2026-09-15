# Phase 5 Summary: Improved Intent Classification

## Approach

The purpose of Phase 5 is to test whether richer CPU-friendly query representations improve intent classification beyond the Phase 4 word TF-IDF baseline. The labels and evaluation partitions are frozen: every supervised experiment uses the same 362 Phase 3 weak labels, the same five row-stratified folds, and the same two template-grouped folds. This makes the representation the primary experimental change.

Five Phase 5 variants are compared with Phase 4:

1. **T1-P0 — Prototype similarity:** assign the nearest of the 11 final-taxonomy intent definitions using frozen embedding cosine similarity.
2. **T1-E1 — Text plus supplied entities:** add eight supplied-entity presence/count features to word TF-IDF.
3. **T1-E2 — Text plus entities and contextual slots:** add 18 implemented Phase 1.6 context features, including dose, comparison, recency/year, pregnancy, renal/hepatic context, route, age group, negation, and prior treatment failure.
4. **T1-E3 — Frozen sentence embeddings:** classify the cached normalized 384-dimensional multilingual query embedding with class-balanced Logistic Regression.
5. **T1-E4 — Frozen embeddings plus entities and contextual slots:** concatenate the normalized embedding with the independently L2-normalized 26-dimensional structured block, then fit class-balanced Logistic Regression.

T1-E4 therefore has 410 final input features: 384 embedding dimensions, eight entity indicators/counts, and 18 contextual features. Exact disease, molecule, drug-class, ATC, and therapeutic-area identities are excluded because they already occur in query text and could create entity-to-intent shortcuts. Prototype scores, cluster IDs, Phase 3 agreement fields, and rule outputs are not classifier inputs.

The two evaluation designs remain complementary:

1. **Five-fold stratified weak-label cross-validation.** All 11 intents are evaluated over 362 rows, but recurring delexicalized templates cross folds. This measures reproduction of the operational weak-label policy.
2. **Two-fold template-grouped sensitivity analysis.** All instances of a delexicalized template remain in one fold. It evaluates 354 queries and 10 intents with zero template overlap. Monitoring / Response / Risk Assessment is excluded because its eight retained rows reduce to a single template.

## Key Findings

The embedding representation transfers much better to unseen formulations than word TF-IDF, and structured context provides an additional improvement when fused with embeddings.

| Experiment | Representation | Row-CV Macro F1 | Template-held-out Macro F1 | Delta vs Phase 4 |
| --- | --- | ---: | ---: | ---: |
| T1-P0 | Final-taxonomy prototype similarity | 0.683 | 0.651 | +0.142 |
| T1-B0 | Word TF-IDF | **0.981** | 0.509 | — |
| T1-E1 | Text + entity indicators/counts | 0.969 | 0.514 | +0.004 |
| T1-E2 | Text + entities + contextual slots | 0.961 | 0.678 | +0.169 |
| T1-E3 | Frozen embeddings + Logistic Regression | 0.969 | 0.794 | +0.285 |
| T1-E4 | Frozen embeddings + entities + contextual slots | 0.970 | **0.842** | **+0.333** |

T1-E4 is selected because template-held-out Macro F1 is the Phase 5 model-selection metric. It improves by 0.048 over embedding-only T1-E3 and by 0.333 over Phase 4. Its row-CV Macro F1 is 0.970 rather than Phase 4's 0.981, but the Phase 4 analysis showed that the nearly saturated row score benefits heavily from recurring templates.

| Selected-model evaluation | Queries | Intents | Template overlap | Macro precision | Macro recall | Macro F1 | Weighted F1 | Accuracy |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| Five-fold weak-label CV | 362 | 11 | Yes | 0.979 | 0.965 | **0.970** | 0.964 | 0.964 |
| Two-fold template-grouped sensitivity | 354 | 10 | No | 0.878 | 0.833 | **0.842** | 0.835 | 0.842 |

The fusion weight was not chosen by sweeping the outer evaluation folds. The pretrained embedding is already unit-normalized, the combined entity/context block is separately normalized to unit L2 norm, and the two blocks are concatenated with equal weight. This fixed design prevents raw boolean slots from overwhelming individual embedding dimensions.

Relative to T1-E3, T1-E4 changes 60 predictions in the grouped stress test. Twenty-seven changes fix an embedding-only error, five introduce an error, and 28 move from one incorrect class to another. Entity indicators/counts alone are effectively neutral, while context features supply the complementary signal: comparison, dosing, recency/year, pregnancy, renal/hepatic constraints, and prior treatment failure encode boundaries that semantic similarity sometimes misses.

### Per-class performance

| Intent | Weak-label n | Templates | Phase 4 grouped F1 | T1-E3 grouped F1 | Selected T1-E4 grouped F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Management / Treatment Selection | 50 | 20 | 0.600 | 0.635 | 0.680 |
| Dosing / Administration | 94 | 16 | 0.596 | 0.869 | 0.931 |
| Safety / Contraindication | 59 | 30 | 0.504 | 0.678 | 0.785 |
| Interaction / Combination | 21 | 4 | 0.343 | 0.638 | 0.645 |
| Comparative Treatment Choice | 23 | 4 | 0.712 | 0.868 | 0.885 |
| Monitoring / Response / Risk Assessment | 8 | 1 | Not evaluable | Not evaluable | Not evaluable |
| Efficacy / Outcomes | 20 | 2 | 0.000 | 1.000 | 1.000 |
| Guideline / Evidence Lookup | 6 | 3 | 0.909 | 0.909 | 0.909 |
| Treatment Change / Escalation | 21 | 4 | 0.323 | 0.667 | 1.000 |
| Prophylaxis / Maintenance | 31 | 4 | 0.655 | 0.745 | 0.655 |
| Mechanism / Background Knowledge | 29 | 3 | 0.450 | 0.935 | 0.935 |

The largest improvements over Phase 4 occur for Efficacy, Escalation, Mechanism, Dosing, Interaction, and Safety. The perfect Efficacy and Escalation results should not be generalized: Efficacy has only two independent templates and Escalation has four. One template can move an entire rare-class metric substantially. Prophylaxis does not improve over Phase 4 and becomes one of the selected model's main remaining boundaries.

### Failure cases

T1-E4 makes 56 errors among the 354 grouped predictions, compared with 78 for T1-E3. The most common off-diagonal errors are Safety to Dosing (14), Prophylaxis to Management (12), Management to Prophylaxis (7), Interaction to Comparison (6), Management to Safety (6), and Interaction to Management (5).

| Query | Weak target | Prediction | Interpretation |
| --- | --- | --- | --- |
| `Ibuprofen side effect pada pasien Psoriatic Arthritis apa saja` | Safety / Contraindication | Dosing / Administration | The fused model overweights frequent medication-use/dosing semantics despite the explicit side-effect request. |
| `dosis Semaglutide pada Obesity pasien hypertension aman tidak` | Safety / Contraindication | Dosing / Administration | Dose and safety cues compete; the weak-label hierarchy selects Safety, while the strong dose slot pushes the model toward Dosing. |
| `terapi profilaksis Typhoid Fever dengan Artemether-lumefantrine` | Prophylaxis / Maintenance | Management / Treatment Selection | Prophylaxis is interpreted as general longitudinal treatment management. |
| `kapan mulai terapi Adalimumab pada Gout` | Management / Treatment Selection | Prophylaxis / Maintenance | Treatment initiation is incorrectly placed near longitudinal maintenance despite no prophylaxis cue. |
| `kombinasi Metoprolol dan Metoprolol pada Heart Failure aman atau tidak` | Interaction / Combination | Comparative Treatment Choice | Multiple-molecule structure identifies a multi-drug query but does not distinguish co-administration from comparison. |
| `Ramipril combination therapy Hypertension` | Interaction / Combination | Management / Treatment Selection | Short combination-therapy wording is treated as general treatment selection. |
| `Malaria with pregnancy first line drug` | Management / Treatment Selection | Safety / Contraindication | Pregnancy context overwhelms the explicit first-line selection request. |
| `target terapi Rheumatoid Arthritis dengan Proteasome inhibitors` | Management / Treatment Selection | Mechanism / Background Knowledge | The short target-therapy formulation remains semantically ambiguous without broader clinical context. |

The failure pattern illustrates both sides of fusion. Context fixes many embedding-only errors—for example, explicit dose, comparison, year, and treatment-failure cues—but it can also be too strong. The clearest example is a query containing both `dosis` and `aman tidak`: the deterministic dose feature reinforces Dosing even when the annotation policy treats the safety question as primary.

Language slices are descriptive because their class distributions differ. Grouped T1-E4 Macro F1 is 0.926 for English, 0.693 for Bahasa Indonesia, and 0.636 for mixed-language queries. Performance is also much stronger for unanimous weak labels than for rule-versus-semantic conflicts. These differences should guide data collection, not be treated as controlled language comparisons.

## Honest Evaluation

The 0.842 grouped Macro F1 is evidence that frozen semantic embeddings and structured context are complementary on this dataset. It is not evidence that intent classification is 84% clinically correct. The targets are model-assisted weak labels rather than independent clinician annotations.

There is also an embedding-related selection dependency. The same frozen representation used by T1-E3 and T1-E4 contributed the Phase 3 prototype and cluster signals that helped determine which 362 rows were retained. Fold-specific Logistic Regression models never see test labels, and prototype or cluster outputs are not model features, so this is not direct target leakage. It is nevertheless evaluation-set selection bias and can make the embedding results optimistic.

The small dataset is the dominant statistical limitation. The 362 retained rows collapse to only 91 delexicalized templates. The grouped estimate uses two folds, excludes Monitoring, and includes six other intents with fewer than five templates. The final T1-E4 model has 410 input features for 362 training rows, although 384 are fixed pretrained dimensions and Logistic Regression is regularized and class-balanced. The feature-to-row ratio, rare classes, and sparse context categories still make coefficients and per-class estimates unstable.

Several structured features also have little variation. Every supplied query has a disease, molecule, and drug class, so their presence flags are nearly constant. Route occurs only three times in the full query set. The observed final one-hot schema contains pediatric and elderly age groups, two pregnancy values, renal impairment, inhaled route, and topical route; unobserved categories cannot be learned.

Finally, `Other / Ambiguous` has no examples. The classifier is forced to choose one of the 11 supported intents for every query and cannot learn abstention, genuinely ambiguous requests, or novel intent classes.

## What I Would Do Differently

I would create an independently clinician-labeled, template-diverse test set before further model selection. The holdout should be frozen before taxonomy refinement, prototype comparison, clustering, or fusion development, and its inclusion should not depend on agreement from the evaluated embedding model.

I would collect at least five independent templates per intent, with additional emphasis on Monitoring, Efficacy, Guideline, Escalation, Prophylaxis, Interaction, and Mechanism. The new set should deliberately include competing cues such as dose plus safety, combination plus safety, pregnancy plus first-line selection, and adjustment versus treatment change.

With a larger development set, I would tune regularization and the relative embedding/structured block weight inside nested template-grouped cross-validation. I would compare early fusion with calibrated late fusion so structured rules can modify semantic predictions without overriding them too aggressively. Probability calibration and an abstention threshold should be evaluated using independently labeled ambiguous and out-of-taxonomy queries.

I would also broaden the CPU-friendly model comparison rather than assuming Logistic Regression is optimal. The first alternatives would be a class-weighted Linear SVM over word and character TF-IDF, a Linear SVM over the embedding/structured fusion vector, and regularized SGD classifiers. Character n-grams are especially relevant for spelling variation, Bahasa Indonesia morphology, mixed-language queries, abbreviations, and short medical search phrases. Linear SVM decision scores would need calibration before confidence thresholds or abstention are used.

For fusion, I would compare the current feature-level concatenation with calibrated late fusion. Separate lexical, embedding, and structured classifiers could produce out-of-fold probabilities that are combined by a constrained weighted average or a small Logistic Regression stacker. This would make it possible to reduce the contextual model's influence on conflicting queries such as dose plus safety while retaining its gains for explicit comparison, recency, and treatment-failure cues. All base-model predictions used by the stacker must be generated out of fold to avoid leakage.

I would test a hierarchical classifier that predicts the broad parent intent first and then resolves subtypes within Management or Pharmacotherapy. This may reduce implausible cross-parent errors while focusing the subtype model on boundaries such as Dosing versus Safety, Interaction versus Comparison, and initial Treatment Selection versus Escalation. The hierarchy should only be retained if end-to-end subtype Macro F1 improves; parent-stage mistakes can otherwise block the correct subtype completely.

Tree-based models would be limited to the small structured feature block rather than the 384-dimensional embedding. A shallow gradient-boosted tree or regularized random forest could capture interactions such as `dose_context × renal_constraint` and `comparison_flag × multiple_molecules`, but the current sample is too small for aggressive boosting. I would compare these models as structured late-fusion components and require stable improvements across repeated grouped splits before retaining them.

I would also compare several frozen multilingual or biomedical sentence encoders using cached CPU inference, keeping the downstream classifier and folds fixed. Encoder selection must occur on a development set rather than the final holdout. With substantially more independently labeled data and GPU resources, I would then evaluate parameter-efficient encoder fine-tuning, supervised contrastive learning with hard intent-boundary examples, and a small cross-encoder or instruction-tuned classifier. These are future extensions, not part of the current CPU-first submitted system.

I would also improve multilingual contextual extraction, especially Bahasa Indonesia and mixed-language safety, interaction, initiation, and maintenance phrasing. All later experiments should continue reporting row-CV weak-label agreement separately from template-held-out transfer, with Macro F1, per-class recall, common confusion pairs, language slices, and label-confidence slices.
