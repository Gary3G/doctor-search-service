# Phase 5: Improved Intent Classification

## Outcome

Phase 5 keeps the Phase 4 labels and fold assignments fixed and changes only the query representation. The selected model is **T1-E4: frozen embeddings + entity indicators/counts + contextual slots**. It reaches **0.842 template-held-out Macro F1**, a +0.333 absolute change from the Phase 4 baseline (0.509). Its five-fold weak-label Macro F1 is 0.970, compared with 0.981 for Phase 4.

The selection rule is: simplest supervised representation within 0.010 grouped Macro F1 of the best; selection uses the Phase 4 template-held-out stress test. This prioritizes transfer to unseen query formulations rather than the nearly saturated row-stratified score.

## Experiment comparison

| Experiment | Representation | Row-CV Macro F1 | Template-held-out Macro F1 | Delta vs Phase 4 |
| --- | --- | ---: | ---: | ---: |
| T1-P0 | Final-taxonomy prototype similarity | 0.683 | 0.651 | +0.142 |
| T1-B0 | Word TF-IDF | 0.981 | 0.509 | +0.000 |
| T1-E1 | Text + supplied entities | 0.969 | 0.514 | +0.004 |
| T1-E2 | Text + entities + contextual slots | 0.961 | 0.678 | +0.169 |
| T1-E3 | Frozen sentence embeddings | 0.969 | 0.794 | +0.285 |
| T1-E4 | Frozen embeddings + entities + contextual slots | 0.970 | 0.842 | +0.333 |

T1-P0 uses the final 11 data-refined intent definitions because the original literature seed categories do not map one-to-one to the final subtype task. It is diagnostic only: prototype predictions helped form the Phase 3 agreement filter, so this score is selection-biased and not an independent zero-shot benchmark. T1-E3 and T1-E4 reuse the frozen Phase 2 multilingual embeddings; no encoder parameters are trained. Because the same embedding representation also contributed the prototype and cluster signals used by Phase 3 filtering, neither embedding experiment is fully independent of evaluation-set construction.

T1-E4 uses fixed early fusion rather than a held-out-scale sweep. The normalized embedding has unit L2 norm, the combined entity/context block is independently normalized to unit L2 norm, and the two blocks are concatenated with equal weight. This prevents raw boolean values from overwhelming individual embedding dimensions while avoiding hyperparameter selection on the outer evaluation folds.

Relative to T1-E3, T1-E4 changes 61 predictions across both protocols. It fixes 28 embedding-only errors, introduces 5 errors, and changes 28 incorrect predictions to another incorrect class. The template-held-out protocol accounts for 27 of the fixes and 5 of the introduced errors.

## Structured-feature effects

Across both protocols and both structured experiments, there are 244 changed experiment-prediction instances relative to the baseline: 99 fix a baseline error, 50 introduce an error, and 95 change one wrong prediction to another. These cases are exported for manual review. The supplied-entity branch deliberately uses only presence/count features; exact entity identities are excluded because they duplicate query text and invite disease/drug shortcuts. Extracted context can encode genuine clinical constraints, but it can also become a template shortcut; the E1/E2 coefficient audit therefore marks text versus structured feature families explicitly.

## Failure analysis

The selected-model confusion matrix and error table use the zero-template-overlap protocol, the more informative Phase 4 baseline comparison. Monitoring / Response / Risk Assessment remains excluded from this stress test because its retained weak labels contain only one independent template. Error rows retain language and signal-agreement fields, enabling review of mixed-language, rare-class, and low-confidence weak-label cases. A separate confusion-pair table and reviewed examples document the most common boundaries, while the language, label-agreement, and query-length slices remain descriptive because their class mixes differ.

## Limitations

- Targets are model-assisted weak labels, not clinician-adjudicated gold labels.
- The row-stratified protocol leaks recurring delexicalized templates by design; it measures weak-policy replication.
- The grouped protocol is a two-fold stress test over 10 classes, with several classes represented by only two to four templates.
- Prototype predictions are not independent of the retained evaluation subset.
- The E3/E4 embedding representation contributed Phase 3 prototype/cluster signals, although fold-specific classifiers never see test labels.
- `Other / Ambiguous` has no training examples, so none of the supervised models can learn abstention or novel intents.
- Feature extraction is deterministic and CPU-friendly, but structured features can amplify dataset-specific correlations.
