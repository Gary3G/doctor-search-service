# Completed experiments and metrics

This report reads saved results; no models were rerun. Intent uses assisted weak labels; row CV shares templates and grouped CV excludes one class. Retrieval uses sparse behavioral proxies, not clinician judgments. Earlier test inspection means retrieval confirmation and follow-up tuning are exploratory. Repeated ablations and baseline rows are retained with experiment_family identifiers, not counted as independent experiments.

## Experiment register

| experiment | hypothesis | method | primary_metric | result | decision |
| --- | --- | --- | --- | --- | --- |
| T1-B0 | lexical features can identify intent | TF-IDF + Logistic Regression | Macro F1 | 5-fold weak-label Macro F1=0.981 | retain; audit template-transfer sensitivity |
| R-B0 | lexical retrieval provides reasonable baseline | BM25 | NDCG@10 | Temporal test NDCG@10=0.0102; Recall@10=0.0161; 110/139 positive queries | retain fixed title-only baseline; incomplete behavioral proxy |
| T1-P0 | intent definitions transfer without supervised fitting | frozen candidate-prototype cosine similarity | Macro F1 | template-held-out Macro F1=0.651; delta vs T1-B0=+0.142 | not selected |
| T1-E1 | supplied entities improve unseen-template intent transfer | TF-IDF + supplied entity indicators/counts + Logistic Regression | Macro F1 | template-held-out Macro F1=0.514; delta vs T1-B0=+0.004 | not selected |
| T1-E2 | contextual slots improve unseen-template intent transfer | TF-IDF + entities + contextual slots + Logistic Regression | Macro F1 | template-held-out Macro F1=0.678; delta vs T1-B0=+0.169 | not selected |
| T1-E3 | frozen semantic embeddings improve unseen-template intent transfer | frozen multilingual embeddings + Logistic Regression | Macro F1 | template-held-out Macro F1=0.794; delta vs T1-B0=+0.285 | not selected |
| T1-E4 | semantic and structured signals are complementary | L2-normalized frozen embeddings + entity/context features + Logistic Regression | Macro F1 | template-held-out Macro F1=0.842; delta vs T1-B0=+0.333 | selected |
| R-L0 | terminal behavior and dwell can define transparent graded weak relevance | 10s meaningful-click + 150s strong-scroll thresholds; bookmark/return strong | Label and positive-query coverage | 7190/7190 exposures labeled; grades 0/1/2/3=5690/444/710/346; 350/500 queries have positives | selected primary weak-label scheme |
| R-LS1 | relevance strength should be checked against stricter dwell cutoffs | 30s meaningful-click + 180s strong-scroll thresholds | Label transition rate | 442/7190 rows change strength (6.1%); positive coverage unchanged | retain for retrieval sensitivity analysis |
| R-S0 | explicit clinical structure can produce behavior-independent ranking evidence | CLEAR-inspired exact + ICD/ATC hierarchy + contextual matching; equal entity/context average | Pairwise feature coverage | 172500/172500 corpus pairs featurized; 12354 entity-compatible and 14278 context-compatible pairs | retain for later retrieval ablation; no ranking claim yet |
| R-SPLIT | partition evidence before aggregation prevents event reuse | chronological sessions plus query-held-out and duplicate-grouped sensitivity | leakage audit | 7190 exposures and 1500 events uniquely assigned per protocol; 3 near-duplicate pairs; zero detected pair overlap in query_dedup | freeze protocol before retrieval tuning |
| R-B0-FA | separate visible ranking failures from weak behavioral evidence before added complexity | 40-query stratified temporal-validation title/metadata review | qualitative category coverage | 29 intent mismatches; 21 partial entity matches; 32 off-topic strongest positives; 6 without positives | test entity and intent ablations; obtain independent judgments; baseline unchanged |
| R-E1 | measure incremental contribution of entities | bm25 + entities | NDCG@10 | Temporal validation=0.0290; test=0.0130 | retain as ablation; not selected |
| R-E2 | measure incremental contribution of context | bm25 + entities + context | NDCG@10 | Temporal validation=0.0297; test=0.0148 | retain as ablation; not selected |
| R-E3 | measure incremental contribution of dense | dense | NDCG@10 | Temporal validation=0.0308; test=0.0158 | retain as ablation; not selected |
| R-E4 | measure incremental contribution of dense | bm25 + dense | NDCG@10 | Temporal validation=0.0255; test=0.0165 | retain as ablation; not selected |
| R-E5 | measure incremental contribution of entities | bm25 + dense + entities | NDCG@10 | Temporal validation=0.0247; test=0.0122 | retain as ablation; not selected |
| R-E6 | measure incremental contribution of context | bm25 + dense + entities + context | NDCG@10 | Temporal validation=0.0273; test=0.0110 | retain as ablation; not selected |
| R-E7 | measure incremental contribution of intent | bm25 + dense + entities + context + intent | NDCG@10 | Temporal validation=0.0315; test=0.0194 | selected on temporal validation; descriptive proxy |
| R-TB-entity_only | modest boosts and topic gating improve hybrid proxy ranking | (0.2, 0.0, True) | NDCG@10 | Validation=0.02610; test=0.01511 | exploratory validation-selected configuration; no clean holdout |
| R-TB-joint_gated | modest boosts and topic gating improve hybrid proxy ranking | (0.2, 0.0, True) | NDCG@10 | Validation=0.02610; test=0.01511 | exploratory validation-selected configuration; no clean holdout |
| R-TB-joint_ungated | modest boosts and topic gating improve hybrid proxy ranking | (0.2, 0.1, False) | NDCG@10 | Validation=0.02633; test=0.01511 | exploratory validation-selected configuration; no clean holdout |
| R-SIGNED-bonuses_only | explicit mismatch penalties improve hybrid with missing evidence neutral | {'entity_bonus': 0.2, 'entity_penalty': 0.0, 'context_bonus': 0.2, 'context_penalty': 0.0} | NDCG@10 | Validation=0.02632; test=0.01511 | exploratory validation-selected weights |
| R-SIGNED-penalties_only | explicit mismatch penalties improve hybrid with missing evidence neutral | {'entity_bonus': 0.0, 'entity_penalty': 0.2, 'context_bonus': 0.0, 'context_penalty': 0.0} | NDCG@10 | Validation=0.02610; test=0.01511 | exploratory validation-selected weights |
| R-SIGNED-both | explicit mismatch penalties improve hybrid with missing evidence neutral | {'entity_bonus': 0.2, 'entity_penalty': 0.2, 'context_bonus': 0.2, 'context_penalty': 0.0} | NDCG@10 | Validation=0.02746; test=0.01393 | exploratory validation-selected weights |
| R-EVIDENCE-AUDIT | evidence-source audit identifies extraction changes before further ranking tuning | all 845 records profiled; 60-record Codex review with random and targeted strata | evidence coverage and reviewed defects | 128/399 content molecule annotations literally supported; 7 comparison and 10 renal title misses; 10 safety-question negation flags | repair demonstrated extraction gaps and separate evidence sources; no retrieval changes |
| R-REPAIR-BM25_E_C | explicit repaired context improves retrieval at frozen weights | BM25_E_C with v2 cues and explicit dosing/comparison evidence | NDCG@10 | Validation=0.02966; test=0.01203 | controlled exploratory repair comparison; weights unchanged |
| R-REPAIR-H_E_C | explicit repaired context improves retrieval at frozen weights | H_E_C with v2 cues and explicit dosing/comparison evidence | NDCG@10 | Validation=0.02727; test=0.01105 | controlled exploratory repair comparison; weights unchanged |
| R-REPAIR-H_E_C_I | explicit repaired context improves retrieval at frozen weights | H_E_C_I with v2 cues and explicit dosing/comparison evidence | NDCG@10 | Validation=0.03146; test=0.01677 | controlled exploratory repair comparison; weights unchanged |
| R-REPAIR-H_modest_E_C | explicit repaired context improves retrieval at frozen weights | H_modest_E_C with v2 cues and explicit dosing/comparison evidence | NDCG@10 | Validation=0.02490; test=0.01682 | controlled exploratory repair comparison; weights unchanged |
| R-REPAIRED-SIGNED-bonuses_only | repaired explicit context plus signed scoring improves hybrid retrieval | {'entity_bonus': 0.2, 'entity_penalty': 0.0, 'context_bonus': 0.2, 'context_penalty': 0.0} | NDCG@10 | Validation=0.02632; test=0.01511 | exploratory validation-selected repaired signed configuration |
| R-REPAIRED-SIGNED-penalties_only | repaired explicit context plus signed scoring improves hybrid retrieval | {'entity_bonus': 0.0, 'entity_penalty': 0.2, 'context_bonus': 0.0, 'context_penalty': 0.0} | NDCG@10 | Validation=0.02610; test=0.01511 | exploratory validation-selected repaired signed configuration |
| R-REPAIRED-SIGNED-both | repaired explicit context plus signed scoring improves hybrid retrieval | {'entity_bonus': 0.2, 'entity_penalty': 0.2, 'context_bonus': 0.2, 'context_penalty': 0.0} | NDCG@10 | Validation=0.02746; test=0.01393 | exploratory validation-selected repaired signed configuration |
| R-INTENT-SIGNED-legacy-signed_plus_intent | intent improves hybrid retrieval with signed entity/context evidence | {'entity_bonus': 0.2, 'entity_penalty': 0.2, 'context_bonus': 0.05, 'context_penalty': 0.0, 'intent_bonus': 0.5} | NDCG@10 | Validation=0.03140; test=0.01770 | exploratory validation-selected configuration; test previously inspected |
| R-INTENT-SIGNED-legacy-all_terms_nonzero | intent improves hybrid retrieval with signed entity/context evidence | {'entity_bonus': 0.2, 'entity_penalty': 0.2, 'context_bonus': 0.05, 'context_penalty': 0.05, 'intent_bonus': 0.5} | NDCG@10 | Validation=0.03140; test=0.01770 | exploratory validation-selected configuration; test previously inspected |
| R-INTENT-SIGNED-repaired-signed_plus_intent | intent improves hybrid retrieval with signed entity/context evidence | {'entity_bonus': 0.2, 'entity_penalty': 0.2, 'context_bonus': 0.05, 'context_penalty': 0.0, 'intent_bonus': 0.5} | NDCG@10 | Validation=0.03140; test=0.01770 | exploratory validation-selected configuration; test previously inspected |
| R-INTENT-SIGNED-repaired-all_terms_nonzero | intent improves hybrid retrieval with signed entity/context evidence | {'entity_bonus': 0.2, 'entity_penalty': 0.2, 'context_bonus': 0.05, 'context_penalty': 0.05, 'intent_bonus': 0.5} | NDCG@10 | Validation=0.03140; test=0.01770 | exploratory validation-selected configuration; test previously inspected |
| R-VALUE-requested_exact-selected_signed_intent | per-value entities and tri-state context improve signed intent retrieval | {'entity_bonus': 0.2, 'entity_penalty': 0.2, 'context_bonus': 0.05, 'context_penalty': 0.0, 'intent_bonus': 0.5} | NDCG@10 | Validation=0.03115; test=0.01770 | exploratory validation-selected value-aware configuration |
| R-VALUE-requested_exact-selected_all_terms | per-value entities and tri-state context improve signed intent retrieval | {'entity_bonus': 0.2, 'entity_penalty': 0.2, 'context_bonus': 0.05, 'context_penalty': 0.05, 'intent_bonus': 0.5} | NDCG@10 | Validation=0.03115; test=0.01770 | exploratory validation-selected value-aware configuration |
| R-VALUE-symmetric_exact-selected_signed_intent | per-value entities and tri-state context improve signed intent retrieval | {'entity_bonus': 0.2, 'entity_penalty': 0.2, 'context_bonus': 0.05, 'context_penalty': 0.0, 'intent_bonus': 0.5} | NDCG@10 | Validation=0.02999; test=0.01900 | exploratory validation-selected value-aware configuration |
| R-VALUE-symmetric_exact-selected_all_terms | per-value entities and tri-state context improve signed intent retrieval | {'entity_bonus': 0.2, 'entity_penalty': 0.2, 'context_bonus': 0.05, 'context_penalty': 0.05, 'intent_bonus': 0.5} | NDCG@10 | Validation=0.02999; test=0.01900 | exploratory validation-selected value-aware configuration |

## Intent: all aggregate comparison metrics

| protocol | experiment | representation | n_queries | n_classes | macro_f1 | macro_precision | macro_recall | weighted_f1 | accuracy | macro_f1_delta_vs_phase4 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| row_stratified | T1-B0 | word TF-IDF | 362 | 11 | 0.98076 | 0.99105 | 0.97214 | 0.98331 | 0.98343 | 0.00000 |
| row_stratified | T1-E4 | frozen embeddings + entity indicators/counts + contextual slots | 362 | 11 | 0.97032 | 0.97852 | 0.96469 | 0.96375 | 0.96409 | -0.01044 |
| row_stratified | T1-E1 | word TF-IDF + supplied entity indicators/counts | 362 | 11 | 0.96929 | 0.98454 | 0.95761 | 0.97188 | 0.97238 | -0.01147 |
| row_stratified | T1-E3 | frozen multilingual sentence embeddings | 362 | 11 | 0.96901 | 0.97748 | 0.96315 | 0.96090 | 0.96133 | -0.01176 |
| row_stratified | T1-E2 | word TF-IDF + entity indicators/counts + contextual slots | 362 | 11 | 0.96143 | 0.97056 | 0.95425 | 0.94803 | 0.94751 | -0.01933 |
| row_stratified | T1-P0 | final-taxonomy prototype similarity | 362 | 11 | 0.68313 | 0.72230 | 0.75665 | 0.69615 | 0.70442 | -0.29764 |
| template_grouped | T1-E4 | frozen embeddings + entity indicators/counts + contextual slots | 354 | 10 | 0.84249 | 0.87813 | 0.83343 | 0.83495 | 0.84181 | 0.33338 |
| template_grouped | T1-E3 | frozen multilingual sentence embeddings | 354 | 10 | 0.79441 | 0.80434 | 0.82039 | 0.78091 | 0.77966 | 0.28531 |
| template_grouped | T1-E2 | word TF-IDF + entity indicators/counts + contextual slots | 354 | 10 | 0.67828 | 0.71793 | 0.67745 | 0.69958 | 0.71186 | 0.16917 |
| template_grouped | T1-P0 | final-taxonomy prototype similarity | 354 | 10 | 0.65144 | 0.69453 | 0.73232 | 0.68929 | 0.69774 | 0.14234 |
| template_grouped | T1-E1 | word TF-IDF + supplied entity indicators/counts | 354 | 10 | 0.51356 | 0.67981 | 0.50442 | 0.53601 | 0.57062 | 0.00446 |
| template_grouped | T1-B0 | word TF-IDF | 354 | 10 | 0.50910 | 0.57000 | 0.50178 | 0.52239 | 0.54802 | 0.00000 |

### Additional Phase 4 metrics

| level | macro_f1 | macro_precision | macro_recall | weighted_f1 | accuracy | n_queries | n_classes | n_splits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| out_of_fold_metrics | 0.98076 | 0.99105 | 0.97214 | 0.98331 | 0.98343 | nan | nan | nan |
| top_level_out_of_fold_metrics | 0.98078 | 0.99360 | 0.97059 | 0.99437 | 0.99448 | nan | nan | nan |
| template_grouped_sensitivity | 0.50910 | 0.57000 | 0.50178 | 0.52239 | 0.54802 | 354.00000 | 10.00000 | 2.00000 |

## Retrieval: primary temporal validation and test, all cutoffs

Metrics: Recall, hit rate, MRR, graded NDCG, and judged fraction at K=1,3,5,10,20. No-positive queries are excluded from relevance averages and retained in coverage counts. Judged fraction includes all evaluated queries. Threshold changes binary relevance and eligibility, not graded gains. All schemes/protocols, including Phase 9 train evaluations, are in all_retrieval_metrics.csv.

### phase11: validation

| experiment | queries | positive_queries | no_positive_queries |
| --- | --- | --- | --- |
| R-B0 | 139 | 113 | 26 |
| R-E1 | 139 | 113 | 26 |
| R-E2 | 139 | 113 | 26 |
| R-E3 | 139 | 113 | 26 |
| R-E4 | 139 | 113 | 26 |
| R-E5 | 139 | 113 | 26 |
| R-E6 | 139 | 113 | 26 |
| R-E7 | 139 | 113 | 26 |
| full:complete | 139 | 113 | 26 |
| full:minus_bm25 | 139 | 113 | 26 |
| full:minus_dense | 139 | 113 | 26 |
| full:minus_entities | 139 | 113 | 26 |
| full:minus_context | 139 | 113 | 26 |
| full:minus_intent | 139 | 113 | 26 |
| selected:complete | 139 | 113 | 26 |
| selected:minus_bm25 | 139 | 113 | 26 |
| selected:minus_dense | 139 | 113 | 26 |
| selected:minus_entities | 139 | 113 | 26 |
| selected:minus_context | 139 | 113 | 26 |
| selected:minus_intent | 139 | 113 | 26 |

K=1

| experiment | recall@1 | hit_rate@1 | mrr@1 | ndcg@1 | judged_fraction@1 |
| --- | --- | --- | --- | --- | --- |
| R-B0 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.03597 |
| R-E1 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.01439 |
| R-E2 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| R-E3 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.01439 |
| R-E4 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| R-E5 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| R-E6 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |
| R-E7 | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| full:complete | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| full:minus_bm25 | 0.02655 | 0.02655 | 0.02655 | 0.02655 | 0.05036 |
| full:minus_dense | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| full:minus_entities | 0.00885 | 0.00885 | 0.00885 | 0.00885 | 0.02878 |
| full:minus_context | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| full:minus_intent | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |
| selected:complete | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| selected:minus_bm25 | 0.02655 | 0.02655 | 0.02655 | 0.02655 | 0.05036 |
| selected:minus_dense | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| selected:minus_entities | 0.00885 | 0.00885 | 0.00885 | 0.00885 | 0.02878 |
| selected:minus_context | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| selected:minus_intent | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |

K=3

| experiment | recall@3 | hit_rate@3 | mrr@3 | ndcg@3 | judged_fraction@3 |
| --- | --- | --- | --- | --- | --- |
| R-B0 | 0.01881 | 0.02655 | 0.00885 | 0.00928 | 0.03837 |
| R-E1 | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02638 |
| R-E2 | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| R-E3 | 0.03097 | 0.03540 | 0.01475 | 0.01597 | 0.03118 |
| R-E4 | 0.01327 | 0.01770 | 0.00590 | 0.00564 | 0.03357 |
| R-E5 | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| R-E6 | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| R-E7 | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| full:complete | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| full:minus_bm25 | 0.03053 | 0.04425 | 0.03392 | 0.02902 | 0.04077 |
| full:minus_dense | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.04077 |
| full:minus_entities | 0.01947 | 0.02655 | 0.01475 | 0.01397 | 0.02878 |
| full:minus_context | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.02878 |
| full:minus_intent | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| selected:complete | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| selected:minus_bm25 | 0.03053 | 0.04425 | 0.03392 | 0.02902 | 0.04077 |
| selected:minus_dense | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.04077 |
| selected:minus_entities | 0.01947 | 0.02655 | 0.01475 | 0.01397 | 0.02878 |
| selected:minus_context | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.02878 |
| selected:minus_intent | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |

K=5

| experiment | recall@5 | hit_rate@5 | mrr@5 | ndcg@5 | judged_fraction@5 |
| --- | --- | --- | --- | --- | --- |
| R-B0 | 0.03274 | 0.06195 | 0.01637 | 0.01488 | 0.03309 |
| R-E1 | 0.03820 | 0.07080 | 0.02080 | 0.01820 | 0.04317 |
| R-E2 | 0.04705 | 0.07965 | 0.02301 | 0.02202 | 0.04317 |
| R-E3 | 0.04109 | 0.05310 | 0.01873 | 0.02113 | 0.03309 |
| R-E4 | 0.03334 | 0.05310 | 0.01342 | 0.01439 | 0.03597 |
| R-E5 | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.04173 |
| R-E6 | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.03741 |
| R-E7 | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.02878 |
| full:complete | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.02878 |
| full:minus_bm25 | 0.03201 | 0.05310 | 0.03569 | 0.03014 | 0.03309 |
| full:minus_dense | 0.04233 | 0.06195 | 0.03201 | 0.03120 | 0.03741 |
| full:minus_entities | 0.02168 | 0.03540 | 0.01652 | 0.01493 | 0.02302 |
| full:minus_context | 0.03496 | 0.05310 | 0.02979 | 0.02539 | 0.03165 |
| full:minus_intent | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.03741 |
| selected:complete | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.02878 |
| selected:minus_bm25 | 0.03201 | 0.05310 | 0.03569 | 0.03014 | 0.03309 |
| selected:minus_dense | 0.04233 | 0.06195 | 0.03201 | 0.03120 | 0.03741 |
| selected:minus_entities | 0.02168 | 0.03540 | 0.01652 | 0.01493 | 0.02302 |
| selected:minus_context | 0.03496 | 0.05310 | 0.02979 | 0.02539 | 0.03165 |
| selected:minus_intent | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.03741 |

K=10

| experiment | recall@10 | hit_rate@10 | mrr@10 | ndcg@10 | judged_fraction@10 |
| --- | --- | --- | --- | --- | --- |
| R-B0 | 0.06254 | 0.11504 | 0.02351 | 0.02400 | 0.03813 |
| R-E1 | 0.07139 | 0.12389 | 0.02831 | 0.02899 | 0.03813 |
| R-E2 | 0.07028 | 0.11504 | 0.02778 | 0.02966 | 0.03597 |
| R-E3 | 0.07142 | 0.13274 | 0.02940 | 0.03079 | 0.03237 |
| R-E4 | 0.06823 | 0.12389 | 0.02351 | 0.02545 | 0.03525 |
| R-E5 | 0.05848 | 0.10619 | 0.02502 | 0.02467 | 0.03669 |
| R-E6 | 0.06622 | 0.10619 | 0.02465 | 0.02727 | 0.03597 |
| R-E7 | 0.05118 | 0.07080 | 0.03150 | 0.03146 | 0.02950 |
| full:complete | 0.05118 | 0.07080 | 0.03150 | 0.03146 | 0.02950 |
| full:minus_bm25 | 0.04263 | 0.07080 | 0.03778 | 0.03331 | 0.03022 |
| full:minus_dense | 0.04528 | 0.07080 | 0.03311 | 0.03248 | 0.02950 |
| full:minus_entities | 0.03201 | 0.05310 | 0.01947 | 0.01921 | 0.02518 |
| full:minus_context | 0.04786 | 0.07965 | 0.03315 | 0.03010 | 0.03453 |
| full:minus_intent | 0.06622 | 0.10619 | 0.02465 | 0.02727 | 0.03597 |
| selected:complete | 0.05118 | 0.07080 | 0.03150 | 0.03146 | 0.02950 |
| selected:minus_bm25 | 0.04263 | 0.07080 | 0.03778 | 0.03331 | 0.03022 |
| selected:minus_dense | 0.04528 | 0.07080 | 0.03311 | 0.03248 | 0.02950 |
| selected:minus_entities | 0.03201 | 0.05310 | 0.01947 | 0.01921 | 0.02518 |
| selected:minus_context | 0.04786 | 0.07965 | 0.03315 | 0.03010 | 0.03453 |
| selected:minus_intent | 0.06622 | 0.10619 | 0.02465 | 0.02727 | 0.03597 |

K=20

| experiment | recall@20 | hit_rate@20 | mrr@20 | ndcg@20 | judged_fraction@20 |
| --- | --- | --- | --- | --- | --- |
| R-B0 | 0.06652 | 0.12389 | 0.02395 | 0.02592 | 0.03309 |
| R-E1 | 0.07987 | 0.14159 | 0.02939 | 0.03257 | 0.03201 |
| R-E2 | 0.08090 | 0.14159 | 0.02969 | 0.03411 | 0.03237 |
| R-E3 | 0.09503 | 0.18584 | 0.03282 | 0.03730 | 0.03525 |
| R-E4 | 0.08629 | 0.15044 | 0.02552 | 0.03161 | 0.03201 |
| R-E5 | 0.07434 | 0.12389 | 0.02656 | 0.02983 | 0.03058 |
| R-E6 | 0.07500 | 0.13274 | 0.02639 | 0.03035 | 0.03129 |
| R-E7 | 0.07389 | 0.12389 | 0.03480 | 0.03730 | 0.02770 |
| full:complete | 0.07389 | 0.12389 | 0.03480 | 0.03730 | 0.02770 |
| full:minus_bm25 | 0.06418 | 0.13274 | 0.04188 | 0.03961 | 0.02914 |
| full:minus_dense | 0.06382 | 0.12389 | 0.03626 | 0.03670 | 0.02842 |
| full:minus_entities | 0.05593 | 0.13274 | 0.02500 | 0.02692 | 0.02554 |
| full:minus_context | 0.06733 | 0.10619 | 0.03509 | 0.03509 | 0.02770 |
| full:minus_intent | 0.07500 | 0.13274 | 0.02639 | 0.03035 | 0.03129 |
| selected:complete | 0.07389 | 0.12389 | 0.03480 | 0.03730 | 0.02770 |
| selected:minus_bm25 | 0.06418 | 0.13274 | 0.04188 | 0.03961 | 0.02914 |
| selected:minus_dense | 0.06382 | 0.12389 | 0.03626 | 0.03670 | 0.02842 |
| selected:minus_entities | 0.05593 | 0.13274 | 0.02500 | 0.02692 | 0.02554 |
| selected:minus_context | 0.06733 | 0.10619 | 0.03509 | 0.03509 | 0.02770 |
| selected:minus_intent | 0.07500 | 0.13274 | 0.02639 | 0.03035 | 0.03129 |

### phase11: test

| experiment | queries | positive_queries | no_positive_queries |
| --- | --- | --- | --- |
| R-B0 | 139 | 110 | 29 |
| R-E1 | 139 | 110 | 29 |
| R-E2 | 139 | 110 | 29 |
| R-E3 | 139 | 110 | 29 |
| R-E4 | 139 | 110 | 29 |
| R-E5 | 139 | 110 | 29 |
| R-E6 | 139 | 110 | 29 |
| R-E7 | 139 | 110 | 29 |
| full:complete | 139 | 110 | 29 |
| full:minus_bm25 | 139 | 110 | 29 |
| full:minus_dense | 139 | 110 | 29 |
| full:minus_entities | 139 | 110 | 29 |
| full:minus_context | 139 | 110 | 29 |
| full:minus_intent | 139 | 110 | 29 |
| selected:complete | 139 | 110 | 29 |
| selected:minus_bm25 | 139 | 110 | 29 |
| selected:minus_dense | 139 | 110 | 29 |
| selected:minus_entities | 139 | 110 | 29 |
| selected:minus_context | 139 | 110 | 29 |
| selected:minus_intent | 139 | 110 | 29 |

K=1

| experiment | recall@1 | hit_rate@1 | mrr@1 | ndcg@1 | judged_fraction@1 |
| --- | --- | --- | --- | --- | --- |
| R-B0 | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02158 |
| R-E1 | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.02878 |
| R-E2 | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| R-E3 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02878 |
| R-E4 | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| R-E5 | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.02878 |
| R-E6 | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| R-E7 | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| full:complete | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| full:minus_bm25 | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02158 |
| full:minus_dense | 0.00265 | 0.01818 | 0.01818 | 0.01212 | 0.02878 |
| full:minus_entities | 0.00333 | 0.01818 | 0.01818 | 0.00693 | 0.03597 |
| full:minus_context | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.03597 |
| full:minus_intent | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| selected:complete | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| selected:minus_bm25 | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02158 |
| selected:minus_dense | 0.00265 | 0.01818 | 0.01818 | 0.01212 | 0.02878 |
| selected:minus_entities | 0.00333 | 0.01818 | 0.01818 | 0.00693 | 0.03597 |
| selected:minus_context | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.03597 |
| selected:minus_intent | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |

K=3

| experiment | recall@3 | hit_rate@3 | mrr@3 | ndcg@3 | judged_fraction@3 |
| --- | --- | --- | --- | --- | --- |
| R-B0 | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03597 |
| R-E1 | 0.00606 | 0.01818 | 0.01212 | 0.00478 | 0.03118 |
| R-E2 | 0.00606 | 0.01818 | 0.01212 | 0.00478 | 0.02878 |
| R-E3 | 0.01364 | 0.01818 | 0.00758 | 0.00981 | 0.03357 |
| R-E4 | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03357 |
| R-E5 | 0.00606 | 0.01818 | 0.01212 | 0.00478 | 0.02878 |
| R-E6 | 0.00606 | 0.01818 | 0.01212 | 0.00478 | 0.02638 |
| R-E7 | 0.00447 | 0.02727 | 0.01667 | 0.00584 | 0.02638 |
| full:complete | 0.00447 | 0.02727 | 0.01667 | 0.00584 | 0.02638 |
| full:minus_bm25 | 0.00253 | 0.01818 | 0.01212 | 0.00177 | 0.02158 |
| full:minus_dense | 0.00447 | 0.02727 | 0.02121 | 0.00766 | 0.02638 |
| full:minus_entities | 0.00333 | 0.01818 | 0.01818 | 0.00405 | 0.02878 |
| full:minus_context | 0.00447 | 0.02727 | 0.01667 | 0.00584 | 0.03597 |
| full:minus_intent | 0.00606 | 0.01818 | 0.01212 | 0.00478 | 0.02638 |
| selected:complete | 0.00447 | 0.02727 | 0.01667 | 0.00584 | 0.02638 |
| selected:minus_bm25 | 0.00253 | 0.01818 | 0.01212 | 0.00177 | 0.02158 |
| selected:minus_dense | 0.00447 | 0.02727 | 0.02121 | 0.00766 | 0.02638 |
| selected:minus_entities | 0.00333 | 0.01818 | 0.01818 | 0.00405 | 0.02878 |
| selected:minus_context | 0.00447 | 0.02727 | 0.01667 | 0.00584 | 0.03597 |
| selected:minus_intent | 0.00606 | 0.01818 | 0.01212 | 0.00478 | 0.02638 |

K=5

| experiment | recall@5 | hit_rate@5 | mrr@5 | ndcg@5 | judged_fraction@5 |
| --- | --- | --- | --- | --- | --- |
| R-B0 | 0.00902 | 0.03636 | 0.01621 | 0.00834 | 0.03165 |
| R-E1 | 0.01154 | 0.05455 | 0.01985 | 0.00816 | 0.03453 |
| R-E2 | 0.01154 | 0.05455 | 0.01985 | 0.00816 | 0.03165 |
| R-E3 | 0.01616 | 0.03636 | 0.01167 | 0.01058 | 0.02878 |
| R-E4 | 0.01053 | 0.04545 | 0.01758 | 0.00881 | 0.03165 |
| R-E5 | 0.01154 | 0.05455 | 0.01939 | 0.00797 | 0.03453 |
| R-E6 | 0.01154 | 0.05455 | 0.01939 | 0.00797 | 0.03309 |
| R-E7 | 0.00548 | 0.03636 | 0.01848 | 0.00537 | 0.03022 |
| full:complete | 0.00548 | 0.03636 | 0.01848 | 0.00537 | 0.03022 |
| full:minus_bm25 | 0.00548 | 0.03636 | 0.01621 | 0.00351 | 0.02014 |
| full:minus_dense | 0.01457 | 0.04545 | 0.02485 | 0.01050 | 0.03309 |
| full:minus_entities | 0.01980 | 0.05455 | 0.02636 | 0.00912 | 0.03741 |
| full:minus_context | 0.00548 | 0.03636 | 0.01848 | 0.00537 | 0.03165 |
| full:minus_intent | 0.01154 | 0.05455 | 0.01939 | 0.00797 | 0.03309 |
| selected:complete | 0.00548 | 0.03636 | 0.01848 | 0.00537 | 0.03022 |
| selected:minus_bm25 | 0.00548 | 0.03636 | 0.01621 | 0.00351 | 0.02014 |
| selected:minus_dense | 0.01457 | 0.04545 | 0.02485 | 0.01050 | 0.03309 |
| selected:minus_entities | 0.01980 | 0.05455 | 0.02636 | 0.00912 | 0.03741 |
| selected:minus_context | 0.00548 | 0.03636 | 0.01848 | 0.00537 | 0.03165 |
| selected:minus_intent | 0.01154 | 0.05455 | 0.01939 | 0.00797 | 0.03309 |

K=10

| experiment | recall@10 | hit_rate@10 | mrr@10 | ndcg@10 | judged_fraction@10 |
| --- | --- | --- | --- | --- | --- |
| R-B0 | 0.01609 | 0.06364 | 0.02016 | 0.01021 | 0.02878 |
| R-E1 | 0.02359 | 0.08182 | 0.02379 | 0.01303 | 0.03094 |
| R-E2 | 0.03154 | 0.08182 | 0.02389 | 0.01477 | 0.03309 |
| R-E3 | 0.02972 | 0.07273 | 0.01735 | 0.01584 | 0.02878 |
| R-E4 | 0.03528 | 0.08182 | 0.02304 | 0.01651 | 0.03165 |
| R-E5 | 0.02177 | 0.07273 | 0.02221 | 0.01220 | 0.03165 |
| R-E6 | 0.02063 | 0.06364 | 0.02091 | 0.01105 | 0.03165 |
| R-E7 | 0.04801 | 0.10909 | 0.02857 | 0.01940 | 0.03237 |
| full:complete | 0.04801 | 0.10909 | 0.02857 | 0.01940 | 0.03237 |
| full:minus_bm25 | 0.02102 | 0.07273 | 0.02068 | 0.00813 | 0.02446 |
| full:minus_dense | 0.04699 | 0.10909 | 0.03401 | 0.02098 | 0.03381 |
| full:minus_entities | 0.04483 | 0.09091 | 0.03093 | 0.01625 | 0.03165 |
| full:minus_context | 0.04194 | 0.10909 | 0.02857 | 0.01823 | 0.03453 |
| full:minus_intent | 0.02063 | 0.06364 | 0.02091 | 0.01105 | 0.03165 |
| selected:complete | 0.04801 | 0.10909 | 0.02857 | 0.01940 | 0.03237 |
| selected:minus_bm25 | 0.02102 | 0.07273 | 0.02068 | 0.00813 | 0.02446 |
| selected:minus_dense | 0.04699 | 0.10909 | 0.03401 | 0.02098 | 0.03381 |
| selected:minus_entities | 0.04483 | 0.09091 | 0.03093 | 0.01625 | 0.03165 |
| selected:minus_context | 0.04194 | 0.10909 | 0.02857 | 0.01823 | 0.03453 |
| selected:minus_intent | 0.02063 | 0.06364 | 0.02091 | 0.01105 | 0.03165 |

K=20

| experiment | recall@20 | hit_rate@20 | mrr@20 | ndcg@20 | judged_fraction@20 |
| --- | --- | --- | --- | --- | --- |
| R-B0 | 0.04720 | 0.10000 | 0.02274 | 0.01772 | 0.02842 |
| R-E1 | 0.04914 | 0.11818 | 0.02599 | 0.01859 | 0.02986 |
| R-E2 | 0.04801 | 0.10909 | 0.02561 | 0.01822 | 0.03129 |
| R-E3 | 0.06142 | 0.15455 | 0.02215 | 0.02476 | 0.03022 |
| R-E4 | 0.03992 | 0.10000 | 0.02409 | 0.01731 | 0.02698 |
| R-E5 | 0.03983 | 0.11818 | 0.02505 | 0.01705 | 0.03022 |
| R-E6 | 0.04346 | 0.10000 | 0.02344 | 0.01691 | 0.03058 |
| R-E7 | 0.05082 | 0.11818 | 0.02922 | 0.01993 | 0.03058 |
| full:complete | 0.05082 | 0.11818 | 0.02922 | 0.01993 | 0.03058 |
| full:minus_bm25 | 0.06254 | 0.13636 | 0.02490 | 0.02046 | 0.03129 |
| full:minus_dense | 0.06900 | 0.14545 | 0.03603 | 0.02750 | 0.03237 |
| full:minus_entities | 0.06180 | 0.10909 | 0.03223 | 0.02119 | 0.03273 |
| full:minus_context | 0.06749 | 0.15455 | 0.03136 | 0.02499 | 0.03094 |
| full:minus_intent | 0.04346 | 0.10000 | 0.02344 | 0.01691 | 0.03058 |
| selected:complete | 0.05082 | 0.11818 | 0.02922 | 0.01993 | 0.03058 |
| selected:minus_bm25 | 0.06254 | 0.13636 | 0.02490 | 0.02046 | 0.03129 |
| selected:minus_dense | 0.06900 | 0.14545 | 0.03603 | 0.02750 | 0.03237 |
| selected:minus_entities | 0.06180 | 0.10909 | 0.03223 | 0.02119 | 0.03273 |
| selected:minus_context | 0.06749 | 0.15455 | 0.03136 | 0.02499 | 0.03094 |
| selected:minus_intent | 0.04346 | 0.10000 | 0.02344 | 0.01691 | 0.03058 |

### topic_boost: validation

| experiment | queries | positive_queries | no_positive_queries |
| --- | --- | --- | --- |
| hybrid | 139 | 113 | 26 |
| entity_only | 139 | 113 | 26 |
| gated_context_only | 139 | 113 | 26 |
| ungated_context_only | 139 | 113 | 26 |
| joint_gated | 139 | 113 | 26 |
| joint_ungated | 139 | 113 | 26 |
| joint_minus_entities | 139 | 113 | 26 |
| joint_minus_context | 139 | 113 | 26 |
| joint_remove_gate | 139 | 113 | 26 |
| fixed_entity_010 | 139 | 113 | 26 |
| fixed_joint_gated_010 | 139 | 113 | 26 |
| fixed_joint_ungated_010 | 139 | 113 | 26 |

K=1

| experiment | recall@1 | hit_rate@1 | mrr@1 | ndcg@1 | judged_fraction@1 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| entity_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| gated_context_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| ungated_context_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| joint_gated | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| joint_ungated | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| joint_minus_entities | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| joint_minus_context | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| joint_remove_gate | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| fixed_entity_010 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |
| fixed_joint_gated_010 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |
| fixed_joint_ungated_010 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |

K=3

| experiment | recall@3 | hit_rate@3 | mrr@3 | ndcg@3 | judged_fraction@3 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.01327 | 0.01770 | 0.00590 | 0.00564 | 0.03357 |
| entity_only | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.02878 |
| gated_context_only | 0.01327 | 0.01770 | 0.00590 | 0.00564 | 0.03357 |
| ungated_context_only | 0.01327 | 0.01770 | 0.00590 | 0.00564 | 0.03357 |
| joint_gated | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.02878 |
| joint_ungated | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.02878 |
| joint_minus_entities | 0.01327 | 0.01770 | 0.00590 | 0.00564 | 0.03357 |
| joint_minus_context | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.02878 |
| joint_remove_gate | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.02878 |
| fixed_entity_010 | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.03597 |
| fixed_joint_gated_010 | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.03597 |
| fixed_joint_ungated_010 | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.03597 |

K=5

| experiment | recall@5 | hit_rate@5 | mrr@5 | ndcg@5 | judged_fraction@5 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.03334 | 0.05310 | 0.01342 | 0.01439 | 0.03597 |
| entity_only | 0.03643 | 0.06195 | 0.01681 | 0.01594 | 0.04029 |
| gated_context_only | 0.03334 | 0.05310 | 0.01342 | 0.01439 | 0.03597 |
| ungated_context_only | 0.03334 | 0.05310 | 0.01342 | 0.01439 | 0.03597 |
| joint_gated | 0.03643 | 0.06195 | 0.01681 | 0.01594 | 0.04029 |
| joint_ungated | 0.03643 | 0.06195 | 0.01681 | 0.01594 | 0.04029 |
| joint_minus_entities | 0.03334 | 0.05310 | 0.01342 | 0.01439 | 0.03597 |
| joint_minus_context | 0.03643 | 0.06195 | 0.01681 | 0.01594 | 0.04029 |
| joint_remove_gate | 0.03643 | 0.06195 | 0.01681 | 0.01594 | 0.04029 |
| fixed_entity_010 | 0.03429 | 0.05310 | 0.01460 | 0.01488 | 0.03885 |
| fixed_joint_gated_010 | 0.03429 | 0.05310 | 0.01460 | 0.01488 | 0.03885 |
| fixed_joint_ungated_010 | 0.03429 | 0.05310 | 0.01460 | 0.01488 | 0.03885 |

K=10

| experiment | recall@10 | hit_rate@10 | mrr@10 | ndcg@10 | judged_fraction@10 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.06823 | 0.12389 | 0.02351 | 0.02545 | 0.03525 |
| entity_only | 0.06844 | 0.12389 | 0.02468 | 0.02610 | 0.03597 |
| gated_context_only | 0.06823 | 0.12389 | 0.02351 | 0.02545 | 0.03525 |
| ungated_context_only | 0.06823 | 0.12389 | 0.02372 | 0.02565 | 0.03669 |
| joint_gated | 0.06844 | 0.12389 | 0.02468 | 0.02610 | 0.03597 |
| joint_ungated | 0.06844 | 0.12389 | 0.02490 | 0.02633 | 0.03669 |
| joint_minus_entities | 0.06823 | 0.12389 | 0.02351 | 0.02545 | 0.03525 |
| joint_minus_context | 0.06844 | 0.12389 | 0.02468 | 0.02610 | 0.03597 |
| joint_remove_gate | 0.06844 | 0.12389 | 0.02468 | 0.02610 | 0.03597 |
| fixed_entity_010 | 0.06696 | 0.11504 | 0.02305 | 0.02477 | 0.03525 |
| fixed_joint_gated_010 | 0.06696 | 0.11504 | 0.02305 | 0.02477 | 0.03525 |
| fixed_joint_ungated_010 | 0.06696 | 0.11504 | 0.02318 | 0.02490 | 0.03669 |

K=20

| experiment | recall@20 | hit_rate@20 | mrr@20 | ndcg@20 | judged_fraction@20 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.08629 | 0.15044 | 0.02552 | 0.03161 | 0.03201 |
| entity_only | 0.07765 | 0.14159 | 0.02588 | 0.02977 | 0.03165 |
| gated_context_only | 0.08629 | 0.15044 | 0.02552 | 0.03161 | 0.03201 |
| ungated_context_only | 0.08629 | 0.15044 | 0.02573 | 0.03181 | 0.03237 |
| joint_gated | 0.07765 | 0.14159 | 0.02588 | 0.02977 | 0.03165 |
| joint_ungated | 0.07765 | 0.14159 | 0.02610 | 0.03000 | 0.03237 |
| joint_minus_entities | 0.08629 | 0.15044 | 0.02552 | 0.03161 | 0.03201 |
| joint_minus_context | 0.07765 | 0.14159 | 0.02588 | 0.02977 | 0.03165 |
| joint_remove_gate | 0.07765 | 0.14159 | 0.02588 | 0.02977 | 0.03165 |
| fixed_entity_010 | 0.07892 | 0.15044 | 0.02563 | 0.03023 | 0.03273 |
| fixed_joint_gated_010 | 0.07892 | 0.15044 | 0.02563 | 0.03023 | 0.03273 |
| fixed_joint_ungated_010 | 0.07892 | 0.15044 | 0.02575 | 0.03035 | 0.03273 |

### topic_boost: test

| experiment | queries | positive_queries | no_positive_queries |
| --- | --- | --- | --- |
| hybrid | 139 | 110 | 29 |
| entity_only | 139 | 110 | 29 |
| gated_context_only | 139 | 110 | 29 |
| ungated_context_only | 139 | 110 | 29 |
| joint_gated | 139 | 110 | 29 |
| joint_ungated | 139 | 110 | 29 |
| joint_minus_entities | 139 | 110 | 29 |
| joint_minus_context | 139 | 110 | 29 |
| joint_remove_gate | 139 | 110 | 29 |
| fixed_entity_010 | 139 | 110 | 29 |
| fixed_joint_gated_010 | 139 | 110 | 29 |
| fixed_joint_ungated_010 | 139 | 110 | 29 |

K=1

| experiment | recall@1 | hit_rate@1 | mrr@1 | ndcg@1 | judged_fraction@1 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| entity_only | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| gated_context_only | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| ungated_context_only | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.03597 |
| joint_gated | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| joint_ungated | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.03597 |
| joint_minus_entities | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| joint_minus_context | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| joint_remove_gate | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| fixed_entity_010 | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| fixed_joint_gated_010 | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| fixed_joint_ungated_010 | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |

K=3

| experiment | recall@3 | hit_rate@3 | mrr@3 | ndcg@3 | judged_fraction@3 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03357 |
| entity_only | 0.00788 | 0.02727 | 0.01667 | 0.00718 | 0.03357 |
| gated_context_only | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03357 |
| ungated_context_only | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03118 |
| joint_gated | 0.00788 | 0.02727 | 0.01667 | 0.00718 | 0.03357 |
| joint_ungated | 0.00788 | 0.02727 | 0.01667 | 0.00718 | 0.03118 |
| joint_minus_entities | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03357 |
| joint_minus_context | 0.00788 | 0.02727 | 0.01667 | 0.00718 | 0.03357 |
| joint_remove_gate | 0.00788 | 0.02727 | 0.01667 | 0.00718 | 0.03357 |
| fixed_entity_010 | 0.00788 | 0.02727 | 0.01515 | 0.00710 | 0.03357 |
| fixed_joint_gated_010 | 0.00788 | 0.02727 | 0.01515 | 0.00710 | 0.03118 |
| fixed_joint_ungated_010 | 0.00788 | 0.02727 | 0.01515 | 0.00710 | 0.03118 |

K=5

| experiment | recall@5 | hit_rate@5 | mrr@5 | ndcg@5 | judged_fraction@5 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.01053 | 0.04545 | 0.01758 | 0.00881 | 0.03165 |
| entity_only | 0.01154 | 0.05455 | 0.02212 | 0.00916 | 0.03165 |
| gated_context_only | 0.01053 | 0.04545 | 0.01758 | 0.00881 | 0.03165 |
| ungated_context_only | 0.01053 | 0.04545 | 0.01758 | 0.00881 | 0.02878 |
| joint_gated | 0.01154 | 0.05455 | 0.02212 | 0.00916 | 0.03165 |
| joint_ungated | 0.01154 | 0.05455 | 0.02212 | 0.00916 | 0.03022 |
| joint_minus_entities | 0.01053 | 0.04545 | 0.01758 | 0.00881 | 0.03165 |
| joint_minus_context | 0.01154 | 0.05455 | 0.02212 | 0.00916 | 0.03165 |
| joint_remove_gate | 0.01154 | 0.05455 | 0.02212 | 0.00916 | 0.03165 |
| fixed_entity_010 | 0.02063 | 0.06364 | 0.02242 | 0.01261 | 0.03597 |
| fixed_joint_gated_010 | 0.02063 | 0.06364 | 0.02242 | 0.01261 | 0.03453 |
| fixed_joint_ungated_010 | 0.02063 | 0.06364 | 0.02242 | 0.01261 | 0.03309 |

K=10

| experiment | recall@10 | hit_rate@10 | mrr@10 | ndcg@10 | judged_fraction@10 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.03528 | 0.08182 | 0.02304 | 0.01651 | 0.03165 |
| entity_only | 0.02972 | 0.07273 | 0.02477 | 0.01511 | 0.03237 |
| gated_context_only | 0.03528 | 0.08182 | 0.02304 | 0.01651 | 0.03165 |
| ungated_context_only | 0.03528 | 0.08182 | 0.02304 | 0.01651 | 0.03165 |
| joint_gated | 0.02972 | 0.07273 | 0.02477 | 0.01511 | 0.03237 |
| joint_ungated | 0.02972 | 0.07273 | 0.02477 | 0.01511 | 0.03165 |
| joint_minus_entities | 0.03528 | 0.08182 | 0.02304 | 0.01651 | 0.03165 |
| joint_minus_context | 0.02972 | 0.07273 | 0.02477 | 0.01511 | 0.03237 |
| joint_remove_gate | 0.02972 | 0.07273 | 0.02477 | 0.01511 | 0.03237 |
| fixed_entity_010 | 0.03528 | 0.08182 | 0.02486 | 0.01682 | 0.03237 |
| fixed_joint_gated_010 | 0.03528 | 0.08182 | 0.02486 | 0.01682 | 0.03237 |
| fixed_joint_ungated_010 | 0.03528 | 0.08182 | 0.02486 | 0.01682 | 0.03165 |

K=20

| experiment | recall@20 | hit_rate@20 | mrr@20 | ndcg@20 | judged_fraction@20 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.03992 | 0.10000 | 0.02409 | 0.01731 | 0.02698 |
| entity_only | 0.03823 | 0.10000 | 0.02673 | 0.01733 | 0.02842 |
| gated_context_only | 0.03992 | 0.10000 | 0.02409 | 0.01731 | 0.02698 |
| ungated_context_only | 0.04902 | 0.10909 | 0.02454 | 0.01938 | 0.02806 |
| joint_gated | 0.03823 | 0.10000 | 0.02673 | 0.01733 | 0.02842 |
| joint_ungated | 0.03710 | 0.09091 | 0.02625 | 0.01653 | 0.02806 |
| joint_minus_entities | 0.03992 | 0.10000 | 0.02409 | 0.01731 | 0.02698 |
| joint_minus_context | 0.03823 | 0.10000 | 0.02673 | 0.01733 | 0.02842 |
| joint_remove_gate | 0.03823 | 0.10000 | 0.02673 | 0.01733 | 0.02842 |
| fixed_entity_010 | 0.03891 | 0.10000 | 0.02596 | 0.01723 | 0.02734 |
| fixed_joint_gated_010 | 0.03891 | 0.10000 | 0.02596 | 0.01723 | 0.02734 |
| fixed_joint_ungated_010 | 0.04801 | 0.10909 | 0.02642 | 0.01930 | 0.02878 |

### signed_boost: validation

| experiment | queries | positive_queries | no_positive_queries |
| --- | --- | --- | --- |
| hybrid | 139 | 113 | 26 |
| bonuses_only | 139 | 113 | 26 |
| penalties_only | 139 | 113 | 26 |
| both | 139 | 113 | 26 |
| both_minus_entity_bonus | 139 | 113 | 26 |
| both_minus_entity_penalty | 139 | 113 | 26 |
| both_minus_context_bonus | 139 | 113 | 26 |
| both_minus_context_penalty | 139 | 113 | 26 |
| fixed_bonuses | 139 | 113 | 26 |
| fixed_penalties | 139 | 113 | 26 |
| fixed_both | 139 | 113 | 26 |

K=1

| experiment | recall@1 | hit_rate@1 | mrr@1 | ndcg@1 | judged_fraction@1 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| bonuses_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| penalties_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| both | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| both_minus_entity_bonus | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| both_minus_entity_penalty | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| both_minus_context_bonus | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| both_minus_context_penalty | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| fixed_bonuses | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.01439 |
| fixed_penalties | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| fixed_both | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |

K=3

| experiment | recall@3 | hit_rate@3 | mrr@3 | ndcg@3 | judged_fraction@3 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.01327 | 0.01770 | 0.00590 | 0.00564 | 0.03357 |
| bonuses_only | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.02878 |
| penalties_only | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.02878 |
| both | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| both_minus_entity_bonus | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.02878 |
| both_minus_entity_penalty | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.02878 |
| both_minus_context_bonus | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| both_minus_context_penalty | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| fixed_bonuses | 0.01327 | 0.01770 | 0.00737 | 0.00596 | 0.03357 |
| fixed_penalties | 0.01327 | 0.01770 | 0.00737 | 0.00596 | 0.03357 |
| fixed_both | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.03597 |

K=5

| experiment | recall@5 | hit_rate@5 | mrr@5 | ndcg@5 | judged_fraction@5 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.03334 | 0.05310 | 0.01342 | 0.01439 | 0.03597 |
| bonuses_only | 0.03643 | 0.06195 | 0.01681 | 0.01594 | 0.03885 |
| penalties_only | 0.03643 | 0.06195 | 0.01681 | 0.01594 | 0.04029 |
| both | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.03885 |
| both_minus_entity_bonus | 0.03643 | 0.06195 | 0.01681 | 0.01594 | 0.03885 |
| both_minus_entity_penalty | 0.03643 | 0.06195 | 0.01681 | 0.01594 | 0.03885 |
| both_minus_context_bonus | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.04317 |
| both_minus_context_penalty | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.03885 |
| fixed_bonuses | 0.03429 | 0.05310 | 0.01534 | 0.01458 | 0.03741 |
| fixed_penalties | 0.03429 | 0.05310 | 0.01534 | 0.01458 | 0.03741 |
| fixed_both | 0.03429 | 0.05310 | 0.01460 | 0.01488 | 0.03885 |

K=10

| experiment | recall@10 | hit_rate@10 | mrr@10 | ndcg@10 | judged_fraction@10 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.06823 | 0.12389 | 0.02351 | 0.02545 | 0.03525 |
| bonuses_only | 0.06844 | 0.12389 | 0.02469 | 0.02632 | 0.03597 |
| penalties_only | 0.06844 | 0.12389 | 0.02468 | 0.02610 | 0.03597 |
| both | 0.06733 | 0.11504 | 0.02613 | 0.02746 | 0.03525 |
| both_minus_entity_bonus | 0.06844 | 0.12389 | 0.02469 | 0.02632 | 0.03597 |
| both_minus_entity_penalty | 0.06844 | 0.12389 | 0.02469 | 0.02632 | 0.03597 |
| both_minus_context_bonus | 0.05848 | 0.10619 | 0.02502 | 0.02467 | 0.03525 |
| both_minus_context_penalty | 0.06733 | 0.11504 | 0.02613 | 0.02746 | 0.03525 |
| fixed_bonuses | 0.06823 | 0.12389 | 0.02490 | 0.02577 | 0.03741 |
| fixed_penalties | 0.06823 | 0.12389 | 0.02490 | 0.02577 | 0.03597 |
| fixed_both | 0.06696 | 0.11504 | 0.02318 | 0.02490 | 0.03669 |

K=20

| experiment | recall@20 | hit_rate@20 | mrr@20 | ndcg@20 | judged_fraction@20 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.08629 | 0.15044 | 0.02552 | 0.03161 | 0.03201 |
| bonuses_only | 0.07832 | 0.15044 | 0.02644 | 0.03025 | 0.03201 |
| penalties_only | 0.07765 | 0.14159 | 0.02588 | 0.02977 | 0.03165 |
| both | 0.07611 | 0.14159 | 0.02816 | 0.03057 | 0.03094 |
| both_minus_entity_bonus | 0.07832 | 0.15044 | 0.02644 | 0.03025 | 0.03201 |
| both_minus_entity_penalty | 0.07832 | 0.15044 | 0.02644 | 0.03025 | 0.03201 |
| both_minus_context_bonus | 0.07544 | 0.13274 | 0.02730 | 0.02998 | 0.03022 |
| both_minus_context_penalty | 0.07611 | 0.14159 | 0.02816 | 0.03057 | 0.03094 |
| fixed_bonuses | 0.08777 | 0.15929 | 0.02721 | 0.03236 | 0.03381 |
| fixed_penalties | 0.08777 | 0.15929 | 0.02721 | 0.03236 | 0.03381 |
| fixed_both | 0.07892 | 0.15044 | 0.02575 | 0.03035 | 0.03309 |

### signed_boost: test

| experiment | queries | positive_queries | no_positive_queries |
| --- | --- | --- | --- |
| hybrid | 139 | 110 | 29 |
| bonuses_only | 139 | 110 | 29 |
| penalties_only | 139 | 110 | 29 |
| both | 139 | 110 | 29 |
| both_minus_entity_bonus | 139 | 110 | 29 |
| both_minus_entity_penalty | 139 | 110 | 29 |
| both_minus_context_bonus | 139 | 110 | 29 |
| both_minus_context_penalty | 139 | 110 | 29 |
| fixed_bonuses | 139 | 110 | 29 |
| fixed_penalties | 139 | 110 | 29 |
| fixed_both | 139 | 110 | 29 |

K=1

| experiment | recall@1 | hit_rate@1 | mrr@1 | ndcg@1 | judged_fraction@1 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| bonuses_only | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| penalties_only | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| both | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| both_minus_entity_bonus | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| both_minus_entity_penalty | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| both_minus_context_bonus | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.02878 |
| both_minus_context_penalty | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| fixed_bonuses | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.03597 |
| fixed_penalties | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| fixed_both | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |

K=3

| experiment | recall@3 | hit_rate@3 | mrr@3 | ndcg@3 | judged_fraction@3 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03357 |
| bonuses_only | 0.00788 | 0.02727 | 0.01667 | 0.00718 | 0.03118 |
| penalties_only | 0.00788 | 0.02727 | 0.01667 | 0.00718 | 0.03357 |
| both | 0.00788 | 0.02727 | 0.01515 | 0.00609 | 0.02878 |
| both_minus_entity_bonus | 0.00788 | 0.02727 | 0.01667 | 0.00718 | 0.03118 |
| both_minus_entity_penalty | 0.00788 | 0.02727 | 0.01667 | 0.00718 | 0.03118 |
| both_minus_context_bonus | 0.00788 | 0.02727 | 0.01515 | 0.00609 | 0.03118 |
| both_minus_context_penalty | 0.00788 | 0.02727 | 0.01515 | 0.00609 | 0.02878 |
| fixed_bonuses | 0.00788 | 0.02727 | 0.01515 | 0.00710 | 0.03357 |
| fixed_penalties | 0.00788 | 0.02727 | 0.01515 | 0.00710 | 0.03357 |
| fixed_both | 0.00788 | 0.02727 | 0.01515 | 0.00710 | 0.03357 |

K=5

| experiment | recall@5 | hit_rate@5 | mrr@5 | ndcg@5 | judged_fraction@5 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.01053 | 0.04545 | 0.01758 | 0.00881 | 0.03165 |
| bonuses_only | 0.01154 | 0.05455 | 0.02212 | 0.00916 | 0.03165 |
| penalties_only | 0.01154 | 0.05455 | 0.02212 | 0.00916 | 0.03165 |
| both | 0.01154 | 0.05455 | 0.02061 | 0.00823 | 0.03165 |
| both_minus_entity_bonus | 0.01154 | 0.05455 | 0.02212 | 0.00916 | 0.03165 |
| both_minus_entity_penalty | 0.01154 | 0.05455 | 0.02212 | 0.00916 | 0.03165 |
| both_minus_context_bonus | 0.01154 | 0.05455 | 0.02061 | 0.00823 | 0.03453 |
| both_minus_context_penalty | 0.01154 | 0.05455 | 0.02061 | 0.00823 | 0.03165 |
| fixed_bonuses | 0.02063 | 0.06364 | 0.02242 | 0.01261 | 0.03453 |
| fixed_penalties | 0.02063 | 0.06364 | 0.02242 | 0.01261 | 0.03741 |
| fixed_both | 0.02063 | 0.06364 | 0.02242 | 0.01261 | 0.03309 |

K=10

| experiment | recall@10 | hit_rate@10 | mrr@10 | ndcg@10 | judged_fraction@10 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.03528 | 0.08182 | 0.02304 | 0.01651 | 0.03165 |
| bonuses_only | 0.02972 | 0.07273 | 0.02477 | 0.01511 | 0.03165 |
| penalties_only | 0.02972 | 0.07273 | 0.02477 | 0.01511 | 0.03237 |
| both | 0.02972 | 0.07273 | 0.02303 | 0.01393 | 0.03094 |
| both_minus_entity_bonus | 0.02972 | 0.07273 | 0.02477 | 0.01511 | 0.03165 |
| both_minus_entity_penalty | 0.02972 | 0.07273 | 0.02477 | 0.01511 | 0.03165 |
| both_minus_context_bonus | 0.03086 | 0.08182 | 0.02394 | 0.01493 | 0.03022 |
| both_minus_context_penalty | 0.02972 | 0.07273 | 0.02303 | 0.01393 | 0.03094 |
| fixed_bonuses | 0.03528 | 0.08182 | 0.02486 | 0.01684 | 0.03165 |
| fixed_penalties | 0.03528 | 0.08182 | 0.02486 | 0.01684 | 0.03165 |
| fixed_both | 0.03528 | 0.08182 | 0.02486 | 0.01682 | 0.03237 |

K=20

| experiment | recall@20 | hit_rate@20 | mrr@20 | ndcg@20 | judged_fraction@20 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.03992 | 0.10000 | 0.02409 | 0.01731 | 0.02698 |
| bonuses_only | 0.04619 | 0.10000 | 0.02673 | 0.01863 | 0.02878 |
| penalties_only | 0.03823 | 0.10000 | 0.02673 | 0.01733 | 0.02842 |
| both | 0.04801 | 0.10909 | 0.02509 | 0.01781 | 0.03237 |
| both_minus_entity_bonus | 0.04619 | 0.10000 | 0.02673 | 0.01863 | 0.02878 |
| both_minus_entity_penalty | 0.04619 | 0.10000 | 0.02673 | 0.01863 | 0.02878 |
| both_minus_context_bonus | 0.04135 | 0.11818 | 0.02598 | 0.01683 | 0.03058 |
| both_minus_context_penalty | 0.04801 | 0.10909 | 0.02509 | 0.01781 | 0.03237 |
| fixed_bonuses | 0.04902 | 0.10909 | 0.02640 | 0.01970 | 0.02770 |
| fixed_penalties | 0.03992 | 0.10000 | 0.02594 | 0.01763 | 0.02698 |
| fixed_both | 0.04801 | 0.10909 | 0.02642 | 0.01930 | 0.02806 |

### context_repair: validation

| experiment | queries | positive_queries | no_positive_queries |
| --- | --- | --- | --- |
| BM25_E_C:legacy | 139 | 113 | 26 |
| H_E_C:legacy | 139 | 113 | 26 |
| H_E_C_I:legacy | 139 | 113 | 26 |
| H_modest_E_C:legacy | 139 | 113 | 26 |
| BM25_E_C:cue_repairs | 139 | 113 | 26 |
| H_E_C:cue_repairs | 139 | 113 | 26 |
| H_E_C_I:cue_repairs | 139 | 113 | 26 |
| H_modest_E_C:cue_repairs | 139 | 113 | 26 |
| BM25_E_C:explicit_only | 139 | 113 | 26 |
| H_E_C:explicit_only | 139 | 113 | 26 |
| H_E_C_I:explicit_only | 139 | 113 | 26 |
| H_modest_E_C:explicit_only | 139 | 113 | 26 |
| BM25_E_C:repaired_explicit | 139 | 113 | 26 |
| H_E_C:repaired_explicit | 139 | 113 | 26 |
| H_E_C_I:repaired_explicit | 139 | 113 | 26 |
| H_modest_E_C:repaired_explicit | 139 | 113 | 26 |
| hybrid | 139 | 113 | 26 |

K=1

| experiment | recall@1 | hit_rate@1 | mrr@1 | ndcg@1 | judged_fraction@1 |
| --- | --- | --- | --- | --- | --- |
| BM25_E_C:legacy | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| H_E_C:legacy | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |
| H_E_C_I:legacy | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| H_modest_E_C:legacy | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |
| BM25_E_C:cue_repairs | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| H_E_C:cue_repairs | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |
| H_E_C_I:cue_repairs | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| H_modest_E_C:cue_repairs | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |
| BM25_E_C:explicit_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| H_E_C:explicit_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |
| H_E_C_I:explicit_only | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| H_modest_E_C:explicit_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |
| BM25_E_C:repaired_explicit | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| H_E_C:repaired_explicit | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |
| H_E_C_I:repaired_explicit | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| H_modest_E_C:repaired_explicit | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |
| hybrid | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |

K=3

| experiment | recall@3 | hit_rate@3 | mrr@3 | ndcg@3 | judged_fraction@3 |
| --- | --- | --- | --- | --- | --- |
| BM25_E_C:legacy | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| H_E_C:legacy | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| H_E_C_I:legacy | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| H_modest_E_C:legacy | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.03597 |
| BM25_E_C:cue_repairs | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| H_E_C:cue_repairs | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| H_E_C_I:cue_repairs | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| H_modest_E_C:cue_repairs | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.03597 |
| BM25_E_C:explicit_only | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| H_E_C:explicit_only | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| H_E_C_I:explicit_only | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| H_modest_E_C:explicit_only | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.03597 |
| BM25_E_C:repaired_explicit | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| H_E_C:repaired_explicit | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| H_E_C_I:repaired_explicit | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| H_modest_E_C:repaired_explicit | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.03597 |
| hybrid | 0.01327 | 0.01770 | 0.00590 | 0.00564 | 0.03357 |

K=5

| experiment | recall@5 | hit_rate@5 | mrr@5 | ndcg@5 | judged_fraction@5 |
| --- | --- | --- | --- | --- | --- |
| BM25_E_C:legacy | 0.04705 | 0.07965 | 0.02301 | 0.02202 | 0.04317 |
| H_E_C:legacy | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.03741 |
| H_E_C_I:legacy | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.02878 |
| H_modest_E_C:legacy | 0.03429 | 0.05310 | 0.01460 | 0.01488 | 0.03885 |
| BM25_E_C:cue_repairs | 0.04705 | 0.07965 | 0.02301 | 0.02202 | 0.04317 |
| H_E_C:cue_repairs | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.03741 |
| H_E_C_I:cue_repairs | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.02878 |
| H_modest_E_C:cue_repairs | 0.03429 | 0.05310 | 0.01460 | 0.01488 | 0.03885 |
| BM25_E_C:explicit_only | 0.04705 | 0.07965 | 0.02301 | 0.02202 | 0.04173 |
| H_E_C:explicit_only | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.03741 |
| H_E_C_I:explicit_only | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.02878 |
| H_modest_E_C:explicit_only | 0.03429 | 0.05310 | 0.01460 | 0.01488 | 0.03885 |
| BM25_E_C:repaired_explicit | 0.04705 | 0.07965 | 0.02301 | 0.02202 | 0.04173 |
| H_E_C:repaired_explicit | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.03741 |
| H_E_C_I:repaired_explicit | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.02878 |
| H_modest_E_C:repaired_explicit | 0.03429 | 0.05310 | 0.01460 | 0.01488 | 0.03885 |
| hybrid | 0.03334 | 0.05310 | 0.01342 | 0.01439 | 0.03597 |

K=10

| experiment | recall@10 | hit_rate@10 | mrr@10 | ndcg@10 | judged_fraction@10 |
| --- | --- | --- | --- | --- | --- |
| BM25_E_C:legacy | 0.07028 | 0.11504 | 0.02778 | 0.02966 | 0.03597 |
| H_E_C:legacy | 0.06622 | 0.10619 | 0.02465 | 0.02727 | 0.03597 |
| H_E_C_I:legacy | 0.05118 | 0.07080 | 0.03150 | 0.03146 | 0.02950 |
| H_modest_E_C:legacy | 0.06696 | 0.11504 | 0.02318 | 0.02490 | 0.03669 |
| BM25_E_C:cue_repairs | 0.07028 | 0.11504 | 0.02778 | 0.02966 | 0.03525 |
| H_E_C:cue_repairs | 0.06622 | 0.10619 | 0.02465 | 0.02727 | 0.03669 |
| H_E_C_I:cue_repairs | 0.05118 | 0.07080 | 0.03150 | 0.03146 | 0.03022 |
| H_modest_E_C:cue_repairs | 0.06696 | 0.11504 | 0.02318 | 0.02490 | 0.03669 |
| BM25_E_C:explicit_only | 0.07028 | 0.11504 | 0.02778 | 0.02966 | 0.03525 |
| H_E_C:explicit_only | 0.06622 | 0.10619 | 0.02465 | 0.02727 | 0.03453 |
| H_E_C_I:explicit_only | 0.05118 | 0.07080 | 0.03150 | 0.03146 | 0.02878 |
| H_modest_E_C:explicit_only | 0.06696 | 0.11504 | 0.02318 | 0.02490 | 0.03669 |
| BM25_E_C:repaired_explicit | 0.07028 | 0.11504 | 0.02778 | 0.02966 | 0.03597 |
| H_E_C:repaired_explicit | 0.06622 | 0.10619 | 0.02465 | 0.02727 | 0.03525 |
| H_E_C_I:repaired_explicit | 0.05118 | 0.07080 | 0.03150 | 0.03146 | 0.02950 |
| H_modest_E_C:repaired_explicit | 0.06696 | 0.11504 | 0.02318 | 0.02490 | 0.03669 |
| hybrid | 0.06823 | 0.12389 | 0.02351 | 0.02545 | 0.03525 |

K=20

| experiment | recall@20 | hit_rate@20 | mrr@20 | ndcg@20 | judged_fraction@20 |
| --- | --- | --- | --- | --- | --- |
| BM25_E_C:legacy | 0.08090 | 0.14159 | 0.02969 | 0.03411 | 0.03237 |
| H_E_C:legacy | 0.07500 | 0.13274 | 0.02639 | 0.03035 | 0.03129 |
| H_E_C_I:legacy | 0.07389 | 0.12389 | 0.03480 | 0.03730 | 0.02770 |
| H_modest_E_C:legacy | 0.07892 | 0.15044 | 0.02575 | 0.03035 | 0.03273 |
| BM25_E_C:cue_repairs | 0.08090 | 0.14159 | 0.02969 | 0.03411 | 0.03273 |
| H_E_C:cue_repairs | 0.07500 | 0.13274 | 0.02639 | 0.03035 | 0.03129 |
| H_E_C_I:cue_repairs | 0.07389 | 0.12389 | 0.03480 | 0.03730 | 0.02770 |
| H_modest_E_C:cue_repairs | 0.07892 | 0.15044 | 0.02575 | 0.03035 | 0.03309 |
| BM25_E_C:explicit_only | 0.08975 | 0.15044 | 0.03013 | 0.03612 | 0.03201 |
| H_E_C:explicit_only | 0.07500 | 0.13274 | 0.02641 | 0.03035 | 0.03094 |
| H_E_C_I:explicit_only | 0.07389 | 0.12389 | 0.03497 | 0.03734 | 0.02698 |
| H_modest_E_C:explicit_only | 0.07892 | 0.15044 | 0.02575 | 0.03035 | 0.03273 |
| BM25_E_C:repaired_explicit | 0.08975 | 0.15044 | 0.03013 | 0.03612 | 0.03237 |
| H_E_C:repaired_explicit | 0.07500 | 0.13274 | 0.02641 | 0.03035 | 0.03129 |
| H_E_C_I:repaired_explicit | 0.07389 | 0.12389 | 0.03497 | 0.03734 | 0.02734 |
| H_modest_E_C:repaired_explicit | 0.07892 | 0.15044 | 0.02575 | 0.03035 | 0.03309 |
| hybrid | 0.08629 | 0.15044 | 0.02552 | 0.03161 | 0.03201 |

### context_repair: test

| experiment | queries | positive_queries | no_positive_queries |
| --- | --- | --- | --- |
| BM25_E_C:legacy | 139 | 110 | 29 |
| H_E_C:legacy | 139 | 110 | 29 |
| H_E_C_I:legacy | 139 | 110 | 29 |
| H_modest_E_C:legacy | 139 | 110 | 29 |
| BM25_E_C:cue_repairs | 139 | 110 | 29 |
| H_E_C:cue_repairs | 139 | 110 | 29 |
| H_E_C_I:cue_repairs | 139 | 110 | 29 |
| H_modest_E_C:cue_repairs | 139 | 110 | 29 |
| BM25_E_C:explicit_only | 139 | 110 | 29 |
| H_E_C:explicit_only | 139 | 110 | 29 |
| H_E_C_I:explicit_only | 139 | 110 | 29 |
| H_modest_E_C:explicit_only | 139 | 110 | 29 |
| BM25_E_C:repaired_explicit | 139 | 110 | 29 |
| H_E_C:repaired_explicit | 139 | 110 | 29 |
| H_E_C_I:repaired_explicit | 139 | 110 | 29 |
| H_modest_E_C:repaired_explicit | 139 | 110 | 29 |
| hybrid | 139 | 110 | 29 |

K=1

| experiment | recall@1 | hit_rate@1 | mrr@1 | ndcg@1 | judged_fraction@1 |
| --- | --- | --- | --- | --- | --- |
| BM25_E_C:legacy | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| H_E_C:legacy | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| H_E_C_I:legacy | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| H_modest_E_C:legacy | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| BM25_E_C:cue_repairs | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| H_E_C:cue_repairs | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| H_E_C_I:cue_repairs | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| H_modest_E_C:cue_repairs | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| BM25_E_C:explicit_only | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| H_E_C:explicit_only | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| H_E_C_I:explicit_only | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| H_modest_E_C:explicit_only | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| BM25_E_C:repaired_explicit | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| H_E_C:repaired_explicit | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| H_E_C_I:repaired_explicit | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| H_modest_E_C:repaired_explicit | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| hybrid | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |

K=3

| experiment | recall@3 | hit_rate@3 | mrr@3 | ndcg@3 | judged_fraction@3 |
| --- | --- | --- | --- | --- | --- |
| BM25_E_C:legacy | 0.00606 | 0.01818 | 0.01212 | 0.00478 | 0.02878 |
| H_E_C:legacy | 0.00606 | 0.01818 | 0.01212 | 0.00478 | 0.02638 |
| H_E_C_I:legacy | 0.00447 | 0.02727 | 0.01667 | 0.00584 | 0.02638 |
| H_modest_E_C:legacy | 0.00788 | 0.02727 | 0.01515 | 0.00710 | 0.03118 |
| BM25_E_C:cue_repairs | 0.00606 | 0.01818 | 0.01212 | 0.00478 | 0.02878 |
| H_E_C:cue_repairs | 0.00606 | 0.01818 | 0.01212 | 0.00478 | 0.02638 |
| H_E_C_I:cue_repairs | 0.00447 | 0.02727 | 0.01667 | 0.00584 | 0.02638 |
| H_modest_E_C:cue_repairs | 0.00788 | 0.02727 | 0.01515 | 0.00710 | 0.03118 |
| BM25_E_C:explicit_only | 0.00606 | 0.01818 | 0.01212 | 0.00478 | 0.02878 |
| H_E_C:explicit_only | 0.00606 | 0.01818 | 0.01212 | 0.00478 | 0.02638 |
| H_E_C_I:explicit_only | 0.00447 | 0.02727 | 0.01667 | 0.00584 | 0.02638 |
| H_modest_E_C:explicit_only | 0.00788 | 0.02727 | 0.01515 | 0.00710 | 0.03118 |
| BM25_E_C:repaired_explicit | 0.00606 | 0.01818 | 0.01212 | 0.00478 | 0.02878 |
| H_E_C:repaired_explicit | 0.00606 | 0.01818 | 0.01212 | 0.00478 | 0.02638 |
| H_E_C_I:repaired_explicit | 0.00447 | 0.02727 | 0.01667 | 0.00584 | 0.02638 |
| H_modest_E_C:repaired_explicit | 0.00788 | 0.02727 | 0.01515 | 0.00710 | 0.03118 |
| hybrid | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03357 |

K=5

| experiment | recall@5 | hit_rate@5 | mrr@5 | ndcg@5 | judged_fraction@5 |
| --- | --- | --- | --- | --- | --- |
| BM25_E_C:legacy | 0.01154 | 0.05455 | 0.01985 | 0.00816 | 0.03165 |
| H_E_C:legacy | 0.01154 | 0.05455 | 0.01939 | 0.00797 | 0.03309 |
| H_E_C_I:legacy | 0.00548 | 0.03636 | 0.01848 | 0.00537 | 0.03022 |
| H_modest_E_C:legacy | 0.02063 | 0.06364 | 0.02242 | 0.01261 | 0.03309 |
| BM25_E_C:cue_repairs | 0.01154 | 0.05455 | 0.01985 | 0.00816 | 0.03309 |
| H_E_C:cue_repairs | 0.01154 | 0.05455 | 0.01939 | 0.00797 | 0.03309 |
| H_E_C_I:cue_repairs | 0.00548 | 0.03636 | 0.01848 | 0.00537 | 0.03022 |
| H_modest_E_C:cue_repairs | 0.02063 | 0.06364 | 0.02242 | 0.01261 | 0.03309 |
| BM25_E_C:explicit_only | 0.01154 | 0.05455 | 0.01985 | 0.00816 | 0.03165 |
| H_E_C:explicit_only | 0.01154 | 0.05455 | 0.01939 | 0.00797 | 0.03309 |
| H_E_C_I:explicit_only | 0.00548 | 0.03636 | 0.01848 | 0.00537 | 0.03022 |
| H_modest_E_C:explicit_only | 0.02063 | 0.06364 | 0.02242 | 0.01261 | 0.03309 |
| BM25_E_C:repaired_explicit | 0.01154 | 0.05455 | 0.01985 | 0.00816 | 0.03309 |
| H_E_C:repaired_explicit | 0.01154 | 0.05455 | 0.01939 | 0.00797 | 0.03309 |
| H_E_C_I:repaired_explicit | 0.00548 | 0.03636 | 0.01848 | 0.00537 | 0.03022 |
| H_modest_E_C:repaired_explicit | 0.02063 | 0.06364 | 0.02242 | 0.01261 | 0.03309 |
| hybrid | 0.01053 | 0.04545 | 0.01758 | 0.00881 | 0.03165 |

K=10

| experiment | recall@10 | hit_rate@10 | mrr@10 | ndcg@10 | judged_fraction@10 |
| --- | --- | --- | --- | --- | --- |
| BM25_E_C:legacy | 0.03154 | 0.08182 | 0.02389 | 0.01477 | 0.03309 |
| H_E_C:legacy | 0.02063 | 0.06364 | 0.02091 | 0.01105 | 0.03165 |
| H_E_C_I:legacy | 0.04801 | 0.10909 | 0.02857 | 0.01940 | 0.03237 |
| H_modest_E_C:legacy | 0.03528 | 0.08182 | 0.02486 | 0.01682 | 0.03165 |
| BM25_E_C:cue_repairs | 0.03154 | 0.08182 | 0.02389 | 0.01477 | 0.03309 |
| H_E_C:cue_repairs | 0.02063 | 0.06364 | 0.02091 | 0.01105 | 0.03165 |
| H_E_C_I:cue_repairs | 0.04801 | 0.10909 | 0.02857 | 0.01940 | 0.03309 |
| H_modest_E_C:cue_repairs | 0.03528 | 0.08182 | 0.02486 | 0.01682 | 0.03165 |
| BM25_E_C:explicit_only | 0.02245 | 0.07273 | 0.02288 | 0.01203 | 0.03165 |
| H_E_C:explicit_only | 0.02063 | 0.06364 | 0.02091 | 0.01105 | 0.03165 |
| H_E_C_I:explicit_only | 0.03891 | 0.10000 | 0.02766 | 0.01677 | 0.03165 |
| H_modest_E_C:explicit_only | 0.03528 | 0.08182 | 0.02486 | 0.01682 | 0.03165 |
| BM25_E_C:repaired_explicit | 0.02245 | 0.07273 | 0.02288 | 0.01203 | 0.03165 |
| H_E_C:repaired_explicit | 0.02063 | 0.06364 | 0.02091 | 0.01105 | 0.03165 |
| H_E_C_I:repaired_explicit | 0.03891 | 0.10000 | 0.02766 | 0.01677 | 0.03237 |
| H_modest_E_C:repaired_explicit | 0.03528 | 0.08182 | 0.02486 | 0.01682 | 0.03165 |
| hybrid | 0.03528 | 0.08182 | 0.02304 | 0.01651 | 0.03165 |

K=20

| experiment | recall@20 | hit_rate@20 | mrr@20 | ndcg@20 | judged_fraction@20 |
| --- | --- | --- | --- | --- | --- |
| BM25_E_C:legacy | 0.04801 | 0.10909 | 0.02561 | 0.01822 | 0.03129 |
| H_E_C:legacy | 0.04346 | 0.10000 | 0.02344 | 0.01691 | 0.03058 |
| H_E_C_I:legacy | 0.05082 | 0.11818 | 0.02922 | 0.01993 | 0.03058 |
| H_modest_E_C:legacy | 0.04801 | 0.10909 | 0.02642 | 0.01930 | 0.02878 |
| BM25_E_C:cue_repairs | 0.04801 | 0.10909 | 0.02561 | 0.01822 | 0.03129 |
| H_E_C:cue_repairs | 0.04346 | 0.10000 | 0.02344 | 0.01691 | 0.03022 |
| H_E_C_I:cue_repairs | 0.05082 | 0.11818 | 0.02922 | 0.01993 | 0.03058 |
| H_modest_E_C:cue_repairs | 0.04801 | 0.10909 | 0.02642 | 0.01930 | 0.02878 |
| BM25_E_C:explicit_only | 0.04346 | 0.10909 | 0.02514 | 0.01728 | 0.03237 |
| H_E_C:explicit_only | 0.03437 | 0.09091 | 0.02279 | 0.01458 | 0.03058 |
| H_E_C_I:explicit_only | 0.04627 | 0.11818 | 0.02877 | 0.01901 | 0.03058 |
| H_modest_E_C:explicit_only | 0.03891 | 0.10000 | 0.02596 | 0.01723 | 0.02842 |
| BM25_E_C:repaired_explicit | 0.04346 | 0.10909 | 0.02514 | 0.01728 | 0.03237 |
| H_E_C:repaired_explicit | 0.03437 | 0.09091 | 0.02279 | 0.01458 | 0.03058 |
| H_E_C_I:repaired_explicit | 0.04627 | 0.11818 | 0.02877 | 0.01901 | 0.03058 |
| H_modest_E_C:repaired_explicit | 0.03891 | 0.10000 | 0.02596 | 0.01723 | 0.02842 |
| hybrid | 0.03992 | 0.10000 | 0.02409 | 0.01731 | 0.02698 |

### repaired_signed_boost: validation

| experiment | queries | positive_queries | no_positive_queries |
| --- | --- | --- | --- |
| hybrid | 139 | 113 | 26 |
| repaired_bonuses_only | 139 | 113 | 26 |
| repaired_penalties_only | 139 | 113 | 26 |
| repaired_both | 139 | 113 | 26 |
| repaired_both_minus_entity_bonus | 139 | 113 | 26 |
| repaired_both_minus_entity_penalty | 139 | 113 | 26 |
| repaired_both_minus_context_bonus | 139 | 113 | 26 |
| repaired_both_minus_context_penalty | 139 | 113 | 26 |
| repaired_fixed_bonuses | 139 | 113 | 26 |
| repaired_fixed_penalties | 139 | 113 | 26 |
| repaired_fixed_both | 139 | 113 | 26 |

K=1

| experiment | recall@1 | hit_rate@1 | mrr@1 | ndcg@1 | judged_fraction@1 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| repaired_bonuses_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| repaired_penalties_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| repaired_both | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| repaired_both_minus_entity_bonus | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| repaired_both_minus_entity_penalty | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| repaired_both_minus_context_bonus | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| repaired_both_minus_context_penalty | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| repaired_fixed_bonuses | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.01439 |
| repaired_fixed_penalties | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| repaired_fixed_both | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00719 |

K=3

| experiment | recall@3 | hit_rate@3 | mrr@3 | ndcg@3 | judged_fraction@3 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.01327 | 0.01770 | 0.00590 | 0.00564 | 0.03357 |
| repaired_bonuses_only | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.02878 |
| repaired_penalties_only | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.02878 |
| repaired_both | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| repaired_both_minus_entity_bonus | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.02878 |
| repaired_both_minus_entity_penalty | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.02878 |
| repaired_both_minus_context_bonus | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| repaired_both_minus_context_penalty | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| repaired_fixed_bonuses | 0.01327 | 0.01770 | 0.00737 | 0.00596 | 0.03357 |
| repaired_fixed_penalties | 0.01327 | 0.01770 | 0.00737 | 0.00596 | 0.03357 |
| repaired_fixed_both | 0.02212 | 0.02655 | 0.00885 | 0.01007 | 0.03597 |

K=5

| experiment | recall@5 | hit_rate@5 | mrr@5 | ndcg@5 | judged_fraction@5 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.03334 | 0.05310 | 0.01342 | 0.01439 | 0.03597 |
| repaired_bonuses_only | 0.03643 | 0.06195 | 0.01681 | 0.01594 | 0.03885 |
| repaired_penalties_only | 0.03643 | 0.06195 | 0.01681 | 0.01594 | 0.04029 |
| repaired_both | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.03885 |
| repaired_both_minus_entity_bonus | 0.03643 | 0.06195 | 0.01681 | 0.01594 | 0.03885 |
| repaired_both_minus_entity_penalty | 0.03643 | 0.06195 | 0.01681 | 0.01594 | 0.03885 |
| repaired_both_minus_context_bonus | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.04317 |
| repaired_both_minus_context_penalty | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.03885 |
| repaired_fixed_bonuses | 0.03429 | 0.05310 | 0.01534 | 0.01458 | 0.03741 |
| repaired_fixed_penalties | 0.03429 | 0.05310 | 0.01534 | 0.01458 | 0.03741 |
| repaired_fixed_both | 0.03429 | 0.05310 | 0.01460 | 0.01488 | 0.03885 |

K=10

| experiment | recall@10 | hit_rate@10 | mrr@10 | ndcg@10 | judged_fraction@10 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.06823 | 0.12389 | 0.02351 | 0.02545 | 0.03525 |
| repaired_bonuses_only | 0.06844 | 0.12389 | 0.02469 | 0.02632 | 0.03741 |
| repaired_penalties_only | 0.06844 | 0.12389 | 0.02468 | 0.02610 | 0.03597 |
| repaired_both | 0.06733 | 0.11504 | 0.02613 | 0.02746 | 0.03597 |
| repaired_both_minus_entity_bonus | 0.06844 | 0.12389 | 0.02469 | 0.02632 | 0.03741 |
| repaired_both_minus_entity_penalty | 0.06844 | 0.12389 | 0.02469 | 0.02632 | 0.03741 |
| repaired_both_minus_context_bonus | 0.05848 | 0.10619 | 0.02502 | 0.02467 | 0.03525 |
| repaired_both_minus_context_penalty | 0.06733 | 0.11504 | 0.02613 | 0.02746 | 0.03597 |
| repaired_fixed_bonuses | 0.06823 | 0.12389 | 0.02490 | 0.02577 | 0.03741 |
| repaired_fixed_penalties | 0.06823 | 0.12389 | 0.02490 | 0.02577 | 0.03597 |
| repaired_fixed_both | 0.06696 | 0.11504 | 0.02318 | 0.02490 | 0.03669 |

K=20

| experiment | recall@20 | hit_rate@20 | mrr@20 | ndcg@20 | judged_fraction@20 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.08629 | 0.15044 | 0.02552 | 0.03161 | 0.03201 |
| repaired_bonuses_only | 0.07832 | 0.15044 | 0.02644 | 0.03025 | 0.03201 |
| repaired_penalties_only | 0.07765 | 0.14159 | 0.02588 | 0.02977 | 0.03165 |
| repaired_both | 0.07611 | 0.14159 | 0.02816 | 0.03057 | 0.03165 |
| repaired_both_minus_entity_bonus | 0.07832 | 0.15044 | 0.02644 | 0.03025 | 0.03201 |
| repaired_both_minus_entity_penalty | 0.07832 | 0.15044 | 0.02644 | 0.03025 | 0.03201 |
| repaired_both_minus_context_bonus | 0.07544 | 0.13274 | 0.02730 | 0.02998 | 0.03022 |
| repaired_both_minus_context_penalty | 0.07611 | 0.14159 | 0.02816 | 0.03057 | 0.03165 |
| repaired_fixed_bonuses | 0.08777 | 0.15929 | 0.02721 | 0.03236 | 0.03417 |
| repaired_fixed_penalties | 0.08777 | 0.15929 | 0.02721 | 0.03236 | 0.03381 |
| repaired_fixed_both | 0.07892 | 0.15044 | 0.02575 | 0.03035 | 0.03345 |

### repaired_signed_boost: test

| experiment | queries | positive_queries | no_positive_queries |
| --- | --- | --- | --- |
| hybrid | 139 | 110 | 29 |
| repaired_bonuses_only | 139 | 110 | 29 |
| repaired_penalties_only | 139 | 110 | 29 |
| repaired_both | 139 | 110 | 29 |
| repaired_both_minus_entity_bonus | 139 | 110 | 29 |
| repaired_both_minus_entity_penalty | 139 | 110 | 29 |
| repaired_both_minus_context_bonus | 139 | 110 | 29 |
| repaired_both_minus_context_penalty | 139 | 110 | 29 |
| repaired_fixed_bonuses | 139 | 110 | 29 |
| repaired_fixed_penalties | 139 | 110 | 29 |
| repaired_fixed_both | 139 | 110 | 29 |

K=1

| experiment | recall@1 | hit_rate@1 | mrr@1 | ndcg@1 | judged_fraction@1 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| repaired_bonuses_only | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| repaired_penalties_only | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| repaired_both | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| repaired_both_minus_entity_bonus | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| repaired_both_minus_entity_penalty | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| repaired_both_minus_context_bonus | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.02878 |
| repaired_both_minus_context_penalty | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| repaired_fixed_bonuses | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.03597 |
| repaired_fixed_penalties | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| repaired_fixed_both | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |

K=3

| experiment | recall@3 | hit_rate@3 | mrr@3 | ndcg@3 | judged_fraction@3 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03357 |
| repaired_bonuses_only | 0.00788 | 0.02727 | 0.01667 | 0.00718 | 0.03118 |
| repaired_penalties_only | 0.00788 | 0.02727 | 0.01667 | 0.00718 | 0.03357 |
| repaired_both | 0.00788 | 0.02727 | 0.01515 | 0.00609 | 0.02878 |
| repaired_both_minus_entity_bonus | 0.00788 | 0.02727 | 0.01667 | 0.00718 | 0.03118 |
| repaired_both_minus_entity_penalty | 0.00788 | 0.02727 | 0.01667 | 0.00718 | 0.03118 |
| repaired_both_minus_context_bonus | 0.00788 | 0.02727 | 0.01515 | 0.00609 | 0.03118 |
| repaired_both_minus_context_penalty | 0.00788 | 0.02727 | 0.01515 | 0.00609 | 0.02878 |
| repaired_fixed_bonuses | 0.00788 | 0.02727 | 0.01515 | 0.00710 | 0.03357 |
| repaired_fixed_penalties | 0.00788 | 0.02727 | 0.01515 | 0.00710 | 0.03357 |
| repaired_fixed_both | 0.00788 | 0.02727 | 0.01515 | 0.00710 | 0.03357 |

K=5

| experiment | recall@5 | hit_rate@5 | mrr@5 | ndcg@5 | judged_fraction@5 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.01053 | 0.04545 | 0.01758 | 0.00881 | 0.03165 |
| repaired_bonuses_only | 0.01154 | 0.05455 | 0.02212 | 0.00916 | 0.03165 |
| repaired_penalties_only | 0.01154 | 0.05455 | 0.02212 | 0.00916 | 0.03165 |
| repaired_both | 0.01154 | 0.05455 | 0.02061 | 0.00823 | 0.03165 |
| repaired_both_minus_entity_bonus | 0.01154 | 0.05455 | 0.02212 | 0.00916 | 0.03165 |
| repaired_both_minus_entity_penalty | 0.01154 | 0.05455 | 0.02212 | 0.00916 | 0.03165 |
| repaired_both_minus_context_bonus | 0.01154 | 0.05455 | 0.02061 | 0.00823 | 0.03453 |
| repaired_both_minus_context_penalty | 0.01154 | 0.05455 | 0.02061 | 0.00823 | 0.03165 |
| repaired_fixed_bonuses | 0.02063 | 0.06364 | 0.02242 | 0.01261 | 0.03453 |
| repaired_fixed_penalties | 0.02063 | 0.06364 | 0.02242 | 0.01261 | 0.03741 |
| repaired_fixed_both | 0.02063 | 0.06364 | 0.02242 | 0.01261 | 0.03309 |

K=10

| experiment | recall@10 | hit_rate@10 | mrr@10 | ndcg@10 | judged_fraction@10 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.03528 | 0.08182 | 0.02304 | 0.01651 | 0.03165 |
| repaired_bonuses_only | 0.02972 | 0.07273 | 0.02477 | 0.01511 | 0.03165 |
| repaired_penalties_only | 0.02972 | 0.07273 | 0.02477 | 0.01511 | 0.03237 |
| repaired_both | 0.02972 | 0.07273 | 0.02303 | 0.01393 | 0.03094 |
| repaired_both_minus_entity_bonus | 0.02972 | 0.07273 | 0.02477 | 0.01511 | 0.03165 |
| repaired_both_minus_entity_penalty | 0.02972 | 0.07273 | 0.02477 | 0.01511 | 0.03165 |
| repaired_both_minus_context_bonus | 0.03086 | 0.08182 | 0.02394 | 0.01493 | 0.03022 |
| repaired_both_minus_context_penalty | 0.02972 | 0.07273 | 0.02303 | 0.01393 | 0.03094 |
| repaired_fixed_bonuses | 0.03528 | 0.08182 | 0.02486 | 0.01684 | 0.03165 |
| repaired_fixed_penalties | 0.03528 | 0.08182 | 0.02486 | 0.01684 | 0.03165 |
| repaired_fixed_both | 0.03528 | 0.08182 | 0.02486 | 0.01682 | 0.03237 |

K=20

| experiment | recall@20 | hit_rate@20 | mrr@20 | ndcg@20 | judged_fraction@20 |
| --- | --- | --- | --- | --- | --- |
| hybrid | 0.03992 | 0.10000 | 0.02409 | 0.01731 | 0.02698 |
| repaired_bonuses_only | 0.03710 | 0.09091 | 0.02625 | 0.01653 | 0.02806 |
| repaired_penalties_only | 0.03823 | 0.10000 | 0.02673 | 0.01733 | 0.02842 |
| repaired_both | 0.03891 | 0.10000 | 0.02461 | 0.01570 | 0.03165 |
| repaired_both_minus_entity_bonus | 0.03710 | 0.09091 | 0.02625 | 0.01653 | 0.02806 |
| repaired_both_minus_entity_penalty | 0.03710 | 0.09091 | 0.02625 | 0.01653 | 0.02806 |
| repaired_both_minus_context_bonus | 0.04135 | 0.11818 | 0.02598 | 0.01683 | 0.03058 |
| repaired_both_minus_context_penalty | 0.03891 | 0.10000 | 0.02461 | 0.01570 | 0.03165 |
| repaired_fixed_bonuses | 0.03992 | 0.10000 | 0.02594 | 0.01763 | 0.02734 |
| repaired_fixed_penalties | 0.03992 | 0.10000 | 0.02594 | 0.01763 | 0.02698 |
| repaired_fixed_both | 0.03891 | 0.10000 | 0.02596 | 0.01723 | 0.02770 |

### intent_signed_boost: validation

| experiment | queries | positive_queries | no_positive_queries |
| --- | --- | --- | --- |
| legacy:hybrid | 139 | 113 | 26 |
| legacy:intent_only | 139 | 113 | 26 |
| legacy:signed_only | 139 | 113 | 26 |
| legacy:signed_plus_intent | 139 | 113 | 26 |
| legacy:all_terms_nonzero | 139 | 113 | 26 |
| legacy:prior_signed_plus_intent | 139 | 113 | 26 |
| legacy:fixed_all_005_intent_020 | 139 | 113 | 26 |
| legacy:r_e7_equivalent | 139 | 113 | 26 |
| legacy:all_terms_minus_entity_bonus | 139 | 113 | 26 |
| legacy:all_terms_minus_entity_penalty | 139 | 113 | 26 |
| legacy:all_terms_minus_context_bonus | 139 | 113 | 26 |
| legacy:all_terms_minus_context_penalty | 139 | 113 | 26 |
| legacy:all_terms_minus_intent_bonus | 139 | 113 | 26 |
| repaired:hybrid | 139 | 113 | 26 |
| repaired:intent_only | 139 | 113 | 26 |
| repaired:signed_only | 139 | 113 | 26 |
| repaired:signed_plus_intent | 139 | 113 | 26 |
| repaired:all_terms_nonzero | 139 | 113 | 26 |
| repaired:prior_signed_plus_intent | 139 | 113 | 26 |
| repaired:fixed_all_005_intent_020 | 139 | 113 | 26 |
| repaired:r_e7_equivalent | 139 | 113 | 26 |
| repaired:all_terms_minus_entity_bonus | 139 | 113 | 26 |
| repaired:all_terms_minus_entity_penalty | 139 | 113 | 26 |
| repaired:all_terms_minus_context_bonus | 139 | 113 | 26 |
| repaired:all_terms_minus_context_penalty | 139 | 113 | 26 |
| repaired:all_terms_minus_intent_bonus | 139 | 113 | 26 |

K=1

| experiment | recall@1 | hit_rate@1 | mrr@1 | ndcg@1 | judged_fraction@1 |
| --- | --- | --- | --- | --- | --- |
| legacy:hybrid | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| legacy:intent_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02878 |
| legacy:signed_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| legacy:signed_plus_intent | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| legacy:all_terms_nonzero | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| legacy:prior_signed_plus_intent | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| legacy:fixed_all_005_intent_020 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| legacy:r_e7_equivalent | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| legacy:all_terms_minus_entity_bonus | 0.00885 | 0.00885 | 0.00885 | 0.00885 | 0.01439 |
| legacy:all_terms_minus_entity_penalty | 0.00885 | 0.00885 | 0.00885 | 0.00885 | 0.01439 |
| legacy:all_terms_minus_context_bonus | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| legacy:all_terms_minus_context_penalty | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| legacy:all_terms_minus_intent_bonus | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| repaired:hybrid | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| repaired:intent_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02878 |
| repaired:signed_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| repaired:signed_plus_intent | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| repaired:all_terms_nonzero | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| repaired:prior_signed_plus_intent | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| repaired:fixed_all_005_intent_020 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| repaired:r_e7_equivalent | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| repaired:all_terms_minus_entity_bonus | 0.00885 | 0.00885 | 0.00885 | 0.00885 | 0.01439 |
| repaired:all_terms_minus_entity_penalty | 0.00885 | 0.00885 | 0.00885 | 0.00885 | 0.01439 |
| repaired:all_terms_minus_context_bonus | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| repaired:all_terms_minus_context_penalty | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| repaired:all_terms_minus_intent_bonus | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |

K=3

| experiment | recall@3 | hit_rate@3 | mrr@3 | ndcg@3 | judged_fraction@3 |
| --- | --- | --- | --- | --- | --- |
| legacy:hybrid | 0.01327 | 0.01770 | 0.00590 | 0.00564 | 0.03357 |
| legacy:intent_only | 0.02212 | 0.02655 | 0.01032 | 0.01123 | 0.03357 |
| legacy:signed_only | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| legacy:signed_plus_intent | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| legacy:all_terms_nonzero | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| legacy:prior_signed_plus_intent | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| legacy:fixed_all_005_intent_020 | 0.02389 | 0.03540 | 0.01475 | 0.01308 | 0.03118 |
| legacy:r_e7_equivalent | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| legacy:all_terms_minus_entity_bonus | 0.03053 | 0.04425 | 0.02212 | 0.02096 | 0.03357 |
| legacy:all_terms_minus_entity_penalty | 0.03053 | 0.04425 | 0.02212 | 0.02096 | 0.03357 |
| legacy:all_terms_minus_context_bonus | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| legacy:all_terms_minus_context_penalty | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| legacy:all_terms_minus_intent_bonus | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| repaired:hybrid | 0.01327 | 0.01770 | 0.00590 | 0.00564 | 0.03357 |
| repaired:intent_only | 0.02212 | 0.02655 | 0.01032 | 0.01123 | 0.03357 |
| repaired:signed_only | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |
| repaired:signed_plus_intent | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| repaired:all_terms_nonzero | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| repaired:prior_signed_plus_intent | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| repaired:fixed_all_005_intent_020 | 0.02389 | 0.03540 | 0.01475 | 0.01308 | 0.03118 |
| repaired:r_e7_equivalent | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| repaired:all_terms_minus_entity_bonus | 0.03053 | 0.04425 | 0.02212 | 0.02096 | 0.03357 |
| repaired:all_terms_minus_entity_penalty | 0.03053 | 0.04425 | 0.02212 | 0.02096 | 0.03357 |
| repaired:all_terms_minus_context_bonus | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| repaired:all_terms_minus_context_penalty | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| repaired:all_terms_minus_intent_bonus | 0.02434 | 0.03540 | 0.01327 | 0.01264 | 0.02878 |

K=5

| experiment | recall@5 | hit_rate@5 | mrr@5 | ndcg@5 | judged_fraction@5 |
| --- | --- | --- | --- | --- | --- |
| legacy:hybrid | 0.03334 | 0.05310 | 0.01342 | 0.01439 | 0.03597 |
| legacy:intent_only | 0.03274 | 0.04425 | 0.01386 | 0.01513 | 0.03165 |
| legacy:signed_only | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.03885 |
| legacy:signed_plus_intent | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03165 |
| legacy:all_terms_nonzero | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03165 |
| legacy:prior_signed_plus_intent | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03022 |
| legacy:fixed_all_005_intent_020 | 0.03496 | 0.05310 | 0.01829 | 0.01747 | 0.03453 |
| legacy:r_e7_equivalent | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.02878 |
| legacy:all_terms_minus_entity_bonus | 0.03053 | 0.04425 | 0.02212 | 0.02082 | 0.03022 |
| legacy:all_terms_minus_entity_penalty | 0.03053 | 0.04425 | 0.02212 | 0.02082 | 0.03022 |
| legacy:all_terms_minus_context_bonus | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03165 |
| legacy:all_terms_minus_context_penalty | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03165 |
| legacy:all_terms_minus_intent_bonus | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.04173 |
| repaired:hybrid | 0.03334 | 0.05310 | 0.01342 | 0.01439 | 0.03597 |
| repaired:intent_only | 0.03274 | 0.04425 | 0.01386 | 0.01513 | 0.03165 |
| repaired:signed_only | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.03885 |
| repaired:signed_plus_intent | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03165 |
| repaired:all_terms_nonzero | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03165 |
| repaired:prior_signed_plus_intent | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03022 |
| repaired:fixed_all_005_intent_020 | 0.03496 | 0.05310 | 0.01829 | 0.01747 | 0.03453 |
| repaired:r_e7_equivalent | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.02878 |
| repaired:all_terms_minus_entity_bonus | 0.03053 | 0.04425 | 0.02212 | 0.02082 | 0.03022 |
| repaired:all_terms_minus_entity_penalty | 0.03053 | 0.04425 | 0.02212 | 0.02082 | 0.03022 |
| repaired:all_terms_minus_context_bonus | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03165 |
| repaired:all_terms_minus_context_penalty | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03165 |
| repaired:all_terms_minus_intent_bonus | 0.03643 | 0.06195 | 0.01903 | 0.01729 | 0.04173 |

K=10

| experiment | recall@10 | hit_rate@10 | mrr@10 | ndcg@10 | judged_fraction@10 |
| --- | --- | --- | --- | --- | --- |
| legacy:hybrid | 0.06823 | 0.12389 | 0.02351 | 0.02545 | 0.03525 |
| legacy:intent_only | 0.05701 | 0.09735 | 0.02112 | 0.02358 | 0.03453 |
| legacy:signed_only | 0.06733 | 0.11504 | 0.02613 | 0.02746 | 0.03525 |
| legacy:signed_plus_intent | 0.05229 | 0.07965 | 0.03186 | 0.03140 | 0.03022 |
| legacy:all_terms_nonzero | 0.05229 | 0.07965 | 0.03186 | 0.03140 | 0.02950 |
| legacy:prior_signed_plus_intent | 0.05118 | 0.07080 | 0.03110 | 0.03115 | 0.02806 |
| legacy:fixed_all_005_intent_020 | 0.05701 | 0.09735 | 0.02379 | 0.02475 | 0.03237 |
| legacy:r_e7_equivalent | 0.05118 | 0.07080 | 0.03150 | 0.03146 | 0.02950 |
| legacy:all_terms_minus_entity_bonus | 0.04196 | 0.07080 | 0.02532 | 0.02499 | 0.02590 |
| legacy:all_terms_minus_entity_penalty | 0.04196 | 0.07080 | 0.02532 | 0.02499 | 0.02590 |
| legacy:all_terms_minus_context_bonus | 0.04786 | 0.07965 | 0.03236 | 0.02968 | 0.03094 |
| legacy:all_terms_minus_context_penalty | 0.05229 | 0.07965 | 0.03186 | 0.03140 | 0.03022 |
| legacy:all_terms_minus_intent_bonus | 0.06733 | 0.11504 | 0.02591 | 0.02723 | 0.03597 |
| repaired:hybrid | 0.06823 | 0.12389 | 0.02351 | 0.02545 | 0.03525 |
| repaired:intent_only | 0.05701 | 0.09735 | 0.02112 | 0.02358 | 0.03453 |
| repaired:signed_only | 0.06733 | 0.11504 | 0.02613 | 0.02746 | 0.03597 |
| repaired:signed_plus_intent | 0.05229 | 0.07965 | 0.03186 | 0.03140 | 0.03022 |
| repaired:all_terms_nonzero | 0.05229 | 0.07965 | 0.03186 | 0.03140 | 0.02950 |
| repaired:prior_signed_plus_intent | 0.05118 | 0.07080 | 0.03110 | 0.03115 | 0.02878 |
| repaired:fixed_all_005_intent_020 | 0.05701 | 0.09735 | 0.02379 | 0.02475 | 0.03237 |
| repaired:r_e7_equivalent | 0.05118 | 0.07080 | 0.03150 | 0.03146 | 0.02950 |
| repaired:all_terms_minus_entity_bonus | 0.04196 | 0.07080 | 0.02532 | 0.02499 | 0.02590 |
| repaired:all_terms_minus_entity_penalty | 0.04196 | 0.07080 | 0.02532 | 0.02499 | 0.02590 |
| repaired:all_terms_minus_context_bonus | 0.04786 | 0.07965 | 0.03236 | 0.02968 | 0.03094 |
| repaired:all_terms_minus_context_penalty | 0.05229 | 0.07965 | 0.03186 | 0.03140 | 0.03022 |
| repaired:all_terms_minus_intent_bonus | 0.06733 | 0.11504 | 0.02591 | 0.02723 | 0.03597 |

K=20

| experiment | recall@20 | hit_rate@20 | mrr@20 | ndcg@20 | judged_fraction@20 |
| --- | --- | --- | --- | --- | --- |
| legacy:hybrid | 0.08629 | 0.15044 | 0.02552 | 0.03161 | 0.03201 |
| legacy:intent_only | 0.07094 | 0.14159 | 0.02373 | 0.02853 | 0.03201 |
| legacy:signed_only | 0.07611 | 0.14159 | 0.02816 | 0.03057 | 0.03094 |
| legacy:signed_plus_intent | 0.05959 | 0.10619 | 0.03350 | 0.03280 | 0.02806 |
| legacy:all_terms_nonzero | 0.05959 | 0.10619 | 0.03350 | 0.03280 | 0.02806 |
| legacy:prior_signed_plus_intent | 0.06209 | 0.10619 | 0.03324 | 0.03297 | 0.02590 |
| legacy:fixed_all_005_intent_020 | 0.07655 | 0.13274 | 0.02571 | 0.03033 | 0.02986 |
| legacy:r_e7_equivalent | 0.07389 | 0.12389 | 0.03480 | 0.03730 | 0.02770 |
| legacy:all_terms_minus_entity_bonus | 0.06003 | 0.10619 | 0.02741 | 0.02950 | 0.02662 |
| legacy:all_terms_minus_entity_penalty | 0.06003 | 0.10619 | 0.02741 | 0.02950 | 0.02662 |
| legacy:all_terms_minus_context_bonus | 0.05959 | 0.10619 | 0.03428 | 0.03295 | 0.02806 |
| legacy:all_terms_minus_context_penalty | 0.05959 | 0.10619 | 0.03350 | 0.03280 | 0.02806 |
| legacy:all_terms_minus_intent_bonus | 0.07544 | 0.13274 | 0.02738 | 0.03007 | 0.03201 |
| repaired:hybrid | 0.08629 | 0.15044 | 0.02552 | 0.03161 | 0.03201 |
| repaired:intent_only | 0.07094 | 0.14159 | 0.02373 | 0.02853 | 0.03201 |
| repaired:signed_only | 0.07611 | 0.14159 | 0.02816 | 0.03057 | 0.03165 |
| repaired:signed_plus_intent | 0.05959 | 0.10619 | 0.03350 | 0.03280 | 0.02806 |
| repaired:all_terms_nonzero | 0.05959 | 0.10619 | 0.03350 | 0.03280 | 0.02806 |
| repaired:prior_signed_plus_intent | 0.06320 | 0.11504 | 0.03377 | 0.03335 | 0.02698 |
| repaired:fixed_all_005_intent_020 | 0.07655 | 0.13274 | 0.02571 | 0.03033 | 0.02986 |
| repaired:r_e7_equivalent | 0.07389 | 0.12389 | 0.03497 | 0.03734 | 0.02734 |
| repaired:all_terms_minus_entity_bonus | 0.06298 | 0.11504 | 0.02796 | 0.02975 | 0.02770 |
| repaired:all_terms_minus_entity_penalty | 0.06298 | 0.11504 | 0.02796 | 0.02975 | 0.02770 |
| repaired:all_terms_minus_context_bonus | 0.05959 | 0.10619 | 0.03428 | 0.03295 | 0.02806 |
| repaired:all_terms_minus_context_penalty | 0.05959 | 0.10619 | 0.03350 | 0.03280 | 0.02806 |
| repaired:all_terms_minus_intent_bonus | 0.07544 | 0.13274 | 0.02738 | 0.03007 | 0.03201 |

### intent_signed_boost: test

| experiment | queries | positive_queries | no_positive_queries |
| --- | --- | --- | --- |
| legacy:hybrid | 139 | 110 | 29 |
| legacy:intent_only | 139 | 110 | 29 |
| legacy:signed_only | 139 | 110 | 29 |
| legacy:signed_plus_intent | 139 | 110 | 29 |
| legacy:all_terms_nonzero | 139 | 110 | 29 |
| legacy:prior_signed_plus_intent | 139 | 110 | 29 |
| legacy:fixed_all_005_intent_020 | 139 | 110 | 29 |
| legacy:r_e7_equivalent | 139 | 110 | 29 |
| legacy:all_terms_minus_entity_bonus | 139 | 110 | 29 |
| legacy:all_terms_minus_entity_penalty | 139 | 110 | 29 |
| legacy:all_terms_minus_context_bonus | 139 | 110 | 29 |
| legacy:all_terms_minus_context_penalty | 139 | 110 | 29 |
| legacy:all_terms_minus_intent_bonus | 139 | 110 | 29 |
| repaired:hybrid | 139 | 110 | 29 |
| repaired:intent_only | 139 | 110 | 29 |
| repaired:signed_only | 139 | 110 | 29 |
| repaired:signed_plus_intent | 139 | 110 | 29 |
| repaired:all_terms_nonzero | 139 | 110 | 29 |
| repaired:prior_signed_plus_intent | 139 | 110 | 29 |
| repaired:fixed_all_005_intent_020 | 139 | 110 | 29 |
| repaired:r_e7_equivalent | 139 | 110 | 29 |
| repaired:all_terms_minus_entity_bonus | 139 | 110 | 29 |
| repaired:all_terms_minus_entity_penalty | 139 | 110 | 29 |
| repaired:all_terms_minus_context_bonus | 139 | 110 | 29 |
| repaired:all_terms_minus_context_penalty | 139 | 110 | 29 |
| repaired:all_terms_minus_intent_bonus | 139 | 110 | 29 |

K=1

| experiment | recall@1 | hit_rate@1 | mrr@1 | ndcg@1 | judged_fraction@1 |
| --- | --- | --- | --- | --- | --- |
| legacy:hybrid | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| legacy:intent_only | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.03597 |
| legacy:signed_only | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| legacy:signed_plus_intent | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| legacy:all_terms_nonzero | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| legacy:prior_signed_plus_intent | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| legacy:fixed_all_005_intent_020 | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| legacy:r_e7_equivalent | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| legacy:all_terms_minus_entity_bonus | 0.00333 | 0.01818 | 0.01818 | 0.00693 | 0.03597 |
| legacy:all_terms_minus_entity_penalty | 0.00333 | 0.01818 | 0.01818 | 0.00693 | 0.03597 |
| legacy:all_terms_minus_context_bonus | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.03597 |
| legacy:all_terms_minus_context_penalty | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| legacy:all_terms_minus_intent_bonus | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| repaired:hybrid | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| repaired:intent_only | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.03597 |
| repaired:signed_only | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |
| repaired:signed_plus_intent | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| repaired:all_terms_nonzero | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| repaired:prior_signed_plus_intent | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| repaired:fixed_all_005_intent_020 | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| repaired:r_e7_equivalent | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| repaired:all_terms_minus_entity_bonus | 0.00333 | 0.01818 | 0.01818 | 0.00693 | 0.03597 |
| repaired:all_terms_minus_entity_penalty | 0.00333 | 0.01818 | 0.01818 | 0.00693 | 0.03597 |
| repaired:all_terms_minus_context_bonus | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.03597 |
| repaired:all_terms_minus_context_penalty | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| repaired:all_terms_minus_intent_bonus | 0.00152 | 0.00909 | 0.00909 | 0.00130 | 0.03597 |

K=3

| experiment | recall@3 | hit_rate@3 | mrr@3 | ndcg@3 | judged_fraction@3 |
| --- | --- | --- | --- | --- | --- |
| legacy:hybrid | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03357 |
| legacy:intent_only | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03357 |
| legacy:signed_only | 0.00788 | 0.02727 | 0.01515 | 0.00609 | 0.02878 |
| legacy:signed_plus_intent | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03837 |
| legacy:all_terms_nonzero | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03837 |
| legacy:prior_signed_plus_intent | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03357 |
| legacy:fixed_all_005_intent_020 | 0.00333 | 0.01818 | 0.01364 | 0.00352 | 0.03357 |
| legacy:r_e7_equivalent | 0.00447 | 0.02727 | 0.01667 | 0.00584 | 0.02638 |
| legacy:all_terms_minus_entity_bonus | 0.00548 | 0.03636 | 0.02576 | 0.00751 | 0.03597 |
| legacy:all_terms_minus_entity_penalty | 0.00548 | 0.03636 | 0.02576 | 0.00751 | 0.03597 |
| legacy:all_terms_minus_context_bonus | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03837 |
| legacy:all_terms_minus_context_penalty | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03837 |
| legacy:all_terms_minus_intent_bonus | 0.00788 | 0.02727 | 0.01515 | 0.00609 | 0.03118 |
| repaired:hybrid | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03357 |
| repaired:intent_only | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03357 |
| repaired:signed_only | 0.00788 | 0.02727 | 0.01515 | 0.00609 | 0.02878 |
| repaired:signed_plus_intent | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03597 |
| repaired:all_terms_nonzero | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03597 |
| repaired:prior_signed_plus_intent | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03357 |
| repaired:fixed_all_005_intent_020 | 0.00333 | 0.01818 | 0.01364 | 0.00352 | 0.03118 |
| repaired:r_e7_equivalent | 0.00447 | 0.02727 | 0.01667 | 0.00584 | 0.02638 |
| repaired:all_terms_minus_entity_bonus | 0.00548 | 0.03636 | 0.02576 | 0.00751 | 0.03597 |
| repaired:all_terms_minus_entity_penalty | 0.00548 | 0.03636 | 0.02576 | 0.00751 | 0.03597 |
| repaired:all_terms_minus_context_bonus | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03837 |
| repaired:all_terms_minus_context_penalty | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03597 |
| repaired:all_terms_minus_intent_bonus | 0.00788 | 0.02727 | 0.01515 | 0.00609 | 0.03118 |

K=5

| experiment | recall@5 | hit_rate@5 | mrr@5 | ndcg@5 | judged_fraction@5 |
| --- | --- | --- | --- | --- | --- |
| legacy:hybrid | 0.01053 | 0.04545 | 0.01758 | 0.00881 | 0.03165 |
| legacy:intent_only | 0.00902 | 0.03636 | 0.01576 | 0.00860 | 0.03453 |
| legacy:signed_only | 0.01154 | 0.05455 | 0.02061 | 0.00823 | 0.03165 |
| legacy:signed_plus_intent | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03453 |
| legacy:all_terms_nonzero | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03453 |
| legacy:prior_signed_plus_intent | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03597 |
| legacy:fixed_all_005_intent_020 | 0.01457 | 0.04545 | 0.01955 | 0.00889 | 0.03597 |
| legacy:r_e7_equivalent | 0.00548 | 0.03636 | 0.01848 | 0.00537 | 0.03022 |
| legacy:all_terms_minus_entity_bonus | 0.02093 | 0.06364 | 0.03167 | 0.01191 | 0.03885 |
| legacy:all_terms_minus_entity_penalty | 0.02093 | 0.06364 | 0.03167 | 0.01191 | 0.03885 |
| legacy:all_terms_minus_context_bonus | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03597 |
| legacy:all_terms_minus_context_penalty | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03453 |
| legacy:all_terms_minus_intent_bonus | 0.01154 | 0.05455 | 0.02061 | 0.00823 | 0.03309 |
| repaired:hybrid | 0.01053 | 0.04545 | 0.01758 | 0.00881 | 0.03165 |
| repaired:intent_only | 0.00902 | 0.03636 | 0.01576 | 0.00860 | 0.03453 |
| repaired:signed_only | 0.01154 | 0.05455 | 0.02061 | 0.00823 | 0.03165 |
| repaired:signed_plus_intent | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03309 |
| repaired:all_terms_nonzero | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03309 |
| repaired:prior_signed_plus_intent | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03597 |
| repaired:fixed_all_005_intent_020 | 0.01457 | 0.04545 | 0.01955 | 0.00889 | 0.03453 |
| repaired:r_e7_equivalent | 0.00548 | 0.03636 | 0.01848 | 0.00537 | 0.03022 |
| repaired:all_terms_minus_entity_bonus | 0.02093 | 0.06364 | 0.03167 | 0.01191 | 0.03885 |
| repaired:all_terms_minus_entity_penalty | 0.02093 | 0.06364 | 0.03167 | 0.01191 | 0.03885 |
| repaired:all_terms_minus_context_bonus | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03597 |
| repaired:all_terms_minus_context_penalty | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03309 |
| repaired:all_terms_minus_intent_bonus | 0.01154 | 0.05455 | 0.02061 | 0.00823 | 0.03309 |

K=10

| experiment | recall@10 | hit_rate@10 | mrr@10 | ndcg@10 | judged_fraction@10 |
| --- | --- | --- | --- | --- | --- |
| legacy:hybrid | 0.03528 | 0.08182 | 0.02304 | 0.01651 | 0.03165 |
| legacy:intent_only | 0.03528 | 0.08182 | 0.02231 | 0.01640 | 0.03022 |
| legacy:signed_only | 0.02972 | 0.07273 | 0.02303 | 0.01393 | 0.03094 |
| legacy:signed_plus_intent | 0.03891 | 0.10000 | 0.03114 | 0.01770 | 0.03381 |
| legacy:all_terms_nonzero | 0.03891 | 0.10000 | 0.03114 | 0.01770 | 0.03381 |
| legacy:prior_signed_plus_intent | 0.04801 | 0.10909 | 0.03205 | 0.02032 | 0.03381 |
| legacy:fixed_all_005_intent_020 | 0.04437 | 0.09091 | 0.02602 | 0.01932 | 0.03165 |
| legacy:r_e7_equivalent | 0.04801 | 0.10909 | 0.02857 | 0.01940 | 0.03237 |
| legacy:all_terms_minus_entity_bonus | 0.04749 | 0.10909 | 0.03765 | 0.02145 | 0.03381 |
| legacy:all_terms_minus_entity_penalty | 0.04749 | 0.10909 | 0.03765 | 0.02145 | 0.03381 |
| legacy:all_terms_minus_context_bonus | 0.03891 | 0.10000 | 0.03114 | 0.01770 | 0.03381 |
| legacy:all_terms_minus_context_penalty | 0.03891 | 0.10000 | 0.03114 | 0.01770 | 0.03381 |
| legacy:all_terms_minus_intent_bonus | 0.02972 | 0.07273 | 0.02303 | 0.01393 | 0.02950 |
| repaired:hybrid | 0.03528 | 0.08182 | 0.02304 | 0.01651 | 0.03165 |
| repaired:intent_only | 0.03528 | 0.08182 | 0.02231 | 0.01640 | 0.03022 |
| repaired:signed_only | 0.02972 | 0.07273 | 0.02303 | 0.01393 | 0.03094 |
| repaired:signed_plus_intent | 0.03891 | 0.10000 | 0.03114 | 0.01770 | 0.03381 |
| repaired:all_terms_nonzero | 0.03891 | 0.10000 | 0.03114 | 0.01770 | 0.03381 |
| repaired:prior_signed_plus_intent | 0.03891 | 0.10000 | 0.03114 | 0.01770 | 0.03309 |
| repaired:fixed_all_005_intent_020 | 0.03528 | 0.08182 | 0.02501 | 0.01659 | 0.03022 |
| repaired:r_e7_equivalent | 0.03891 | 0.10000 | 0.02766 | 0.01677 | 0.03237 |
| repaired:all_terms_minus_entity_bonus | 0.03839 | 0.10000 | 0.03674 | 0.01882 | 0.03309 |
| repaired:all_terms_minus_entity_penalty | 0.03839 | 0.10000 | 0.03674 | 0.01882 | 0.03309 |
| repaired:all_terms_minus_context_bonus | 0.03891 | 0.10000 | 0.03114 | 0.01770 | 0.03381 |
| repaired:all_terms_minus_context_penalty | 0.03891 | 0.10000 | 0.03114 | 0.01770 | 0.03381 |
| repaired:all_terms_minus_intent_bonus | 0.02972 | 0.07273 | 0.02303 | 0.01393 | 0.02950 |

K=20

| experiment | recall@20 | hit_rate@20 | mrr@20 | ndcg@20 | judged_fraction@20 |
| --- | --- | --- | --- | --- | --- |
| legacy:hybrid | 0.03992 | 0.10000 | 0.02409 | 0.01731 | 0.02698 |
| legacy:intent_only | 0.05940 | 0.11818 | 0.02477 | 0.02198 | 0.02914 |
| legacy:signed_only | 0.04801 | 0.10909 | 0.02509 | 0.01781 | 0.03237 |
| legacy:signed_plus_intent | 0.06021 | 0.13636 | 0.03393 | 0.02447 | 0.03129 |
| legacy:all_terms_nonzero | 0.06021 | 0.13636 | 0.03393 | 0.02447 | 0.03129 |
| legacy:prior_signed_plus_intent | 0.05264 | 0.11818 | 0.03287 | 0.02130 | 0.03129 |
| legacy:fixed_all_005_intent_020 | 0.06718 | 0.13636 | 0.02900 | 0.02442 | 0.02986 |
| legacy:r_e7_equivalent | 0.05082 | 0.11818 | 0.02922 | 0.01993 | 0.03058 |
| legacy:all_terms_minus_entity_bonus | 0.06930 | 0.15455 | 0.04022 | 0.02756 | 0.03273 |
| legacy:all_terms_minus_entity_penalty | 0.06930 | 0.15455 | 0.04022 | 0.02756 | 0.03273 |
| legacy:all_terms_minus_context_bonus | 0.06476 | 0.14545 | 0.03444 | 0.02578 | 0.03129 |
| legacy:all_terms_minus_context_penalty | 0.06021 | 0.13636 | 0.03393 | 0.02447 | 0.03129 |
| legacy:all_terms_minus_intent_bonus | 0.04135 | 0.11818 | 0.02577 | 0.01674 | 0.03058 |
| repaired:hybrid | 0.03992 | 0.10000 | 0.02409 | 0.01731 | 0.02698 |
| repaired:intent_only | 0.05940 | 0.11818 | 0.02477 | 0.02198 | 0.02914 |
| repaired:signed_only | 0.03891 | 0.10000 | 0.02461 | 0.01570 | 0.03165 |
| repaired:signed_plus_intent | 0.06021 | 0.13636 | 0.03364 | 0.02412 | 0.03165 |
| repaired:all_terms_nonzero | 0.06021 | 0.13636 | 0.03364 | 0.02412 | 0.03165 |
| repaired:prior_signed_plus_intent | 0.05567 | 0.12727 | 0.03304 | 0.02205 | 0.03094 |
| repaired:fixed_all_005_intent_020 | 0.07021 | 0.14545 | 0.02903 | 0.02507 | 0.03022 |
| repaired:r_e7_equivalent | 0.04627 | 0.11818 | 0.02877 | 0.01901 | 0.03058 |
| repaired:all_terms_minus_entity_bonus | 0.06930 | 0.15455 | 0.03995 | 0.02720 | 0.03309 |
| repaired:all_terms_minus_entity_penalty | 0.06930 | 0.15455 | 0.03995 | 0.02720 | 0.03309 |
| repaired:all_terms_minus_context_bonus | 0.06476 | 0.14545 | 0.03444 | 0.02578 | 0.03129 |
| repaired:all_terms_minus_context_penalty | 0.06021 | 0.13636 | 0.03364 | 0.02412 | 0.03165 |
| repaired:all_terms_minus_intent_bonus | 0.04135 | 0.11818 | 0.02577 | 0.01674 | 0.03094 |

### value_aware_retrieval: validation

| experiment | queries | positive_queries | no_positive_queries |
| --- | --- | --- | --- |
| requested_exact:hybrid | 139 | 113 | 26 |
| requested_exact:selected_signed_intent | 139 | 113 | 26 |
| requested_exact:selected_all_terms | 139 | 113 | 26 |
| requested_exact:frozen_all_terms | 139 | 113 | 26 |
| requested_exact:r_e7_style | 139 | 113 | 26 |
| symmetric_exact:hybrid | 139 | 113 | 26 |
| symmetric_exact:selected_signed_intent | 139 | 113 | 26 |
| symmetric_exact:selected_all_terms | 139 | 113 | 26 |
| symmetric_exact:frozen_all_terms | 139 | 113 | 26 |
| symmetric_exact:r_e7_style | 139 | 113 | 26 |
| current:frozen_all_terms | 139 | 113 | 26 |
| current:r_e7_equivalent | 139 | 113 | 26 |
| ablation:requested_current_context | 139 | 113 | 26 |
| ablation:symmetric_current_context | 139 | 113 | 26 |
| ablation:dimension_exact_context | 139 | 113 | 26 |
| baseline:hybrid | 139 | 113 | 26 |
| baseline:r_e7 | 139 | 113 | 26 |

K=1

| experiment | recall@1 | hit_rate@1 | mrr@1 | ndcg@1 | judged_fraction@1 |
| --- | --- | --- | --- | --- | --- |
| requested_exact:hybrid | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| requested_exact:selected_signed_intent | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| requested_exact:selected_all_terms | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| requested_exact:frozen_all_terms | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| requested_exact:r_e7_style | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| symmetric_exact:hybrid | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| symmetric_exact:selected_signed_intent | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| symmetric_exact:selected_all_terms | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| symmetric_exact:frozen_all_terms | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| symmetric_exact:r_e7_style | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| current:frozen_all_terms | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| current:r_e7_equivalent | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| ablation:requested_current_context | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| ablation:symmetric_current_context | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| ablation:dimension_exact_context | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |
| baseline:hybrid | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.02158 |
| baseline:r_e7 | 0.01770 | 0.01770 | 0.01770 | 0.01770 | 0.02158 |

K=3

| experiment | recall@3 | hit_rate@3 | mrr@3 | ndcg@3 | judged_fraction@3 |
| --- | --- | --- | --- | --- | --- |
| requested_exact:hybrid | 0.01327 | 0.01770 | 0.00590 | 0.00564 | 0.03357 |
| requested_exact:selected_signed_intent | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| requested_exact:selected_all_terms | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| requested_exact:frozen_all_terms | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| requested_exact:r_e7_style | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| symmetric_exact:hybrid | 0.01327 | 0.01770 | 0.00590 | 0.00564 | 0.03357 |
| symmetric_exact:selected_signed_intent | 0.01947 | 0.02655 | 0.02065 | 0.01839 | 0.02878 |
| symmetric_exact:selected_all_terms | 0.01947 | 0.02655 | 0.02065 | 0.01839 | 0.02878 |
| symmetric_exact:frozen_all_terms | 0.01947 | 0.02655 | 0.02065 | 0.01839 | 0.02878 |
| symmetric_exact:r_e7_style | 0.01947 | 0.02655 | 0.02065 | 0.01839 | 0.02878 |
| current:frozen_all_terms | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| current:r_e7_equivalent | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| ablation:requested_current_context | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| ablation:symmetric_current_context | 0.01947 | 0.02655 | 0.02065 | 0.01839 | 0.02878 |
| ablation:dimension_exact_context | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |
| baseline:hybrid | 0.01327 | 0.01770 | 0.00590 | 0.00564 | 0.03357 |
| baseline:r_e7 | 0.03053 | 0.04425 | 0.02802 | 0.02460 | 0.03118 |

K=5

| experiment | recall@5 | hit_rate@5 | mrr@5 | ndcg@5 | judged_fraction@5 |
| --- | --- | --- | --- | --- | --- |
| requested_exact:hybrid | 0.03334 | 0.05310 | 0.01342 | 0.01439 | 0.03597 |
| requested_exact:selected_signed_intent | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03022 |
| requested_exact:selected_all_terms | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03022 |
| requested_exact:frozen_all_terms | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03022 |
| requested_exact:r_e7_style | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.02878 |
| symmetric_exact:hybrid | 0.03334 | 0.05310 | 0.01342 | 0.01439 | 0.03597 |
| symmetric_exact:selected_signed_intent | 0.03053 | 0.04425 | 0.02507 | 0.02329 | 0.03022 |
| symmetric_exact:selected_all_terms | 0.03053 | 0.04425 | 0.02507 | 0.02329 | 0.03022 |
| symmetric_exact:frozen_all_terms | 0.03053 | 0.04425 | 0.02507 | 0.02329 | 0.03022 |
| symmetric_exact:r_e7_style | 0.03053 | 0.04425 | 0.02507 | 0.02329 | 0.03022 |
| current:frozen_all_terms | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03165 |
| current:r_e7_equivalent | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.02878 |
| ablation:requested_current_context | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03022 |
| ablation:symmetric_current_context | 0.03053 | 0.04425 | 0.02507 | 0.02329 | 0.03022 |
| ablation:dimension_exact_context | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.03165 |
| baseline:hybrid | 0.03334 | 0.05310 | 0.01342 | 0.01439 | 0.03597 |
| baseline:r_e7 | 0.03053 | 0.04425 | 0.02802 | 0.02444 | 0.02878 |

K=10

| experiment | recall@10 | hit_rate@10 | mrr@10 | ndcg@10 | judged_fraction@10 |
| --- | --- | --- | --- | --- | --- |
| requested_exact:hybrid | 0.06823 | 0.12389 | 0.02351 | 0.02545 | 0.03525 |
| requested_exact:selected_signed_intent | 0.05081 | 0.07965 | 0.03198 | 0.03115 | 0.02950 |
| requested_exact:selected_all_terms | 0.05081 | 0.07965 | 0.03198 | 0.03115 | 0.02878 |
| requested_exact:frozen_all_terms | 0.05081 | 0.07965 | 0.03198 | 0.03115 | 0.02878 |
| requested_exact:r_e7_style | 0.05118 | 0.07080 | 0.03138 | 0.03144 | 0.02950 |
| symmetric_exact:hybrid | 0.06823 | 0.12389 | 0.02351 | 0.02545 | 0.03525 |
| symmetric_exact:selected_signed_intent | 0.05081 | 0.07965 | 0.02903 | 0.02999 | 0.02878 |
| symmetric_exact:selected_all_terms | 0.05081 | 0.07965 | 0.02903 | 0.02999 | 0.02806 |
| symmetric_exact:frozen_all_terms | 0.05081 | 0.07965 | 0.02903 | 0.02999 | 0.02806 |
| symmetric_exact:r_e7_style | 0.05118 | 0.07080 | 0.02843 | 0.03028 | 0.02878 |
| current:frozen_all_terms | 0.05229 | 0.07965 | 0.03186 | 0.03140 | 0.02950 |
| current:r_e7_equivalent | 0.05118 | 0.07080 | 0.03150 | 0.03146 | 0.02950 |
| ablation:requested_current_context | 0.05081 | 0.07965 | 0.03198 | 0.03115 | 0.02878 |
| ablation:symmetric_current_context | 0.05081 | 0.07965 | 0.02903 | 0.02999 | 0.02806 |
| ablation:dimension_exact_context | 0.05229 | 0.07965 | 0.03186 | 0.03140 | 0.02950 |
| baseline:hybrid | 0.06823 | 0.12389 | 0.02351 | 0.02545 | 0.03525 |
| baseline:r_e7 | 0.05118 | 0.07080 | 0.03150 | 0.03146 | 0.02950 |

K=20

| experiment | recall@20 | hit_rate@20 | mrr@20 | ndcg@20 | judged_fraction@20 |
| --- | --- | --- | --- | --- | --- |
| requested_exact:hybrid | 0.08629 | 0.15044 | 0.02552 | 0.03161 | 0.03201 |
| requested_exact:selected_signed_intent | 0.05959 | 0.10619 | 0.03363 | 0.03282 | 0.02770 |
| requested_exact:selected_all_terms | 0.05848 | 0.09735 | 0.03318 | 0.03240 | 0.02734 |
| requested_exact:frozen_all_terms | 0.05848 | 0.09735 | 0.03318 | 0.03240 | 0.02734 |
| requested_exact:r_e7_style | 0.07389 | 0.12389 | 0.03485 | 0.03731 | 0.02734 |
| symmetric_exact:hybrid | 0.08629 | 0.15044 | 0.02552 | 0.03161 | 0.03201 |
| symmetric_exact:selected_signed_intent | 0.05959 | 0.10619 | 0.03070 | 0.03166 | 0.02770 |
| symmetric_exact:selected_all_terms | 0.05848 | 0.09735 | 0.03023 | 0.03124 | 0.02734 |
| symmetric_exact:frozen_all_terms | 0.05848 | 0.09735 | 0.03023 | 0.03124 | 0.02734 |
| symmetric_exact:r_e7_style | 0.07389 | 0.12389 | 0.03176 | 0.03607 | 0.02734 |
| current:frozen_all_terms | 0.05959 | 0.10619 | 0.03350 | 0.03280 | 0.02806 |
| current:r_e7_equivalent | 0.07389 | 0.12389 | 0.03497 | 0.03734 | 0.02734 |
| ablation:requested_current_context | 0.05959 | 0.10619 | 0.03363 | 0.03282 | 0.02806 |
| ablation:symmetric_current_context | 0.05959 | 0.10619 | 0.03070 | 0.03166 | 0.02806 |
| ablation:dimension_exact_context | 0.05848 | 0.09735 | 0.03306 | 0.03239 | 0.02734 |
| baseline:hybrid | 0.08629 | 0.15044 | 0.02552 | 0.03161 | 0.03201 |
| baseline:r_e7 | 0.07389 | 0.12389 | 0.03480 | 0.03730 | 0.02770 |

### value_aware_retrieval: test

| experiment | queries | positive_queries | no_positive_queries |
| --- | --- | --- | --- |
| requested_exact:hybrid | 139 | 110 | 29 |
| requested_exact:selected_signed_intent | 139 | 110 | 29 |
| requested_exact:selected_all_terms | 139 | 110 | 29 |
| requested_exact:frozen_all_terms | 139 | 110 | 29 |
| requested_exact:r_e7_style | 139 | 110 | 29 |
| symmetric_exact:hybrid | 139 | 110 | 29 |
| symmetric_exact:selected_signed_intent | 139 | 110 | 29 |
| symmetric_exact:selected_all_terms | 139 | 110 | 29 |
| symmetric_exact:frozen_all_terms | 139 | 110 | 29 |
| symmetric_exact:r_e7_style | 139 | 110 | 29 |
| current:frozen_all_terms | 139 | 110 | 29 |
| current:r_e7_equivalent | 139 | 110 | 29 |
| ablation:requested_current_context | 139 | 110 | 29 |
| ablation:symmetric_current_context | 139 | 110 | 29 |
| ablation:dimension_exact_context | 139 | 110 | 29 |
| baseline:hybrid | 139 | 110 | 29 |
| baseline:r_e7 | 139 | 110 | 29 |

K=1

| experiment | recall@1 | hit_rate@1 | mrr@1 | ndcg@1 | judged_fraction@1 |
| --- | --- | --- | --- | --- | --- |
| requested_exact:hybrid | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| requested_exact:selected_signed_intent | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| requested_exact:selected_all_terms | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| requested_exact:frozen_all_terms | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| requested_exact:r_e7_style | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| symmetric_exact:hybrid | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| symmetric_exact:selected_signed_intent | 0.00333 | 0.01818 | 0.01818 | 0.00693 | 0.03597 |
| symmetric_exact:selected_all_terms | 0.00333 | 0.01818 | 0.01818 | 0.00693 | 0.03597 |
| symmetric_exact:frozen_all_terms | 0.00333 | 0.01818 | 0.01818 | 0.00693 | 0.03597 |
| symmetric_exact:r_e7_style | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| current:frozen_all_terms | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| current:r_e7_equivalent | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| ablation:requested_current_context | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| ablation:symmetric_current_context | 0.00333 | 0.01818 | 0.01818 | 0.00693 | 0.03597 |
| ablation:dimension_exact_context | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |
| baseline:hybrid | 0.00182 | 0.00909 | 0.00909 | 0.00390 | 0.02878 |
| baseline:r_e7 | 0.00152 | 0.00909 | 0.00909 | 0.00303 | 0.02878 |

K=3

| experiment | recall@3 | hit_rate@3 | mrr@3 | ndcg@3 | judged_fraction@3 |
| --- | --- | --- | --- | --- | --- |
| requested_exact:hybrid | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03357 |
| requested_exact:selected_signed_intent | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03597 |
| requested_exact:selected_all_terms | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03597 |
| requested_exact:frozen_all_terms | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03597 |
| requested_exact:r_e7_style | 0.00447 | 0.02727 | 0.01667 | 0.00584 | 0.02638 |
| symmetric_exact:hybrid | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03357 |
| symmetric_exact:selected_signed_intent | 0.00548 | 0.03636 | 0.02576 | 0.00751 | 0.03597 |
| symmetric_exact:selected_all_terms | 0.00548 | 0.03636 | 0.02576 | 0.00751 | 0.03597 |
| symmetric_exact:frozen_all_terms | 0.00548 | 0.03636 | 0.02576 | 0.00751 | 0.03597 |
| symmetric_exact:r_e7_style | 0.00447 | 0.02727 | 0.01818 | 0.00619 | 0.02638 |
| current:frozen_all_terms | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03597 |
| current:r_e7_equivalent | 0.00447 | 0.02727 | 0.01667 | 0.00584 | 0.02638 |
| ablation:requested_current_context | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03597 |
| ablation:symmetric_current_context | 0.00548 | 0.03636 | 0.02576 | 0.00751 | 0.03597 |
| ablation:dimension_exact_context | 0.00548 | 0.03636 | 0.02121 | 0.00654 | 0.03597 |
| baseline:hybrid | 0.00636 | 0.01818 | 0.01212 | 0.00679 | 0.03357 |
| baseline:r_e7 | 0.00447 | 0.02727 | 0.01667 | 0.00584 | 0.02638 |

K=5

| experiment | recall@5 | hit_rate@5 | mrr@5 | ndcg@5 | judged_fraction@5 |
| --- | --- | --- | --- | --- | --- |
| requested_exact:hybrid | 0.01053 | 0.04545 | 0.01758 | 0.00881 | 0.03165 |
| requested_exact:selected_signed_intent | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03309 |
| requested_exact:selected_all_terms | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03309 |
| requested_exact:frozen_all_terms | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03309 |
| requested_exact:r_e7_style | 0.00548 | 0.03636 | 0.01848 | 0.00537 | 0.03022 |
| symmetric_exact:hybrid | 0.01053 | 0.04545 | 0.01758 | 0.00881 | 0.03165 |
| symmetric_exact:selected_signed_intent | 0.01457 | 0.04545 | 0.02803 | 0.01048 | 0.03309 |
| symmetric_exact:selected_all_terms | 0.01457 | 0.04545 | 0.02803 | 0.01048 | 0.03309 |
| symmetric_exact:frozen_all_terms | 0.01457 | 0.04545 | 0.02803 | 0.01048 | 0.03309 |
| symmetric_exact:r_e7_style | 0.00548 | 0.03636 | 0.02000 | 0.00567 | 0.03022 |
| current:frozen_all_terms | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03309 |
| current:r_e7_equivalent | 0.00548 | 0.03636 | 0.01848 | 0.00537 | 0.03022 |
| ablation:requested_current_context | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03309 |
| ablation:symmetric_current_context | 0.01457 | 0.04545 | 0.02803 | 0.01048 | 0.03309 |
| ablation:dimension_exact_context | 0.01457 | 0.04545 | 0.02303 | 0.00925 | 0.03309 |
| baseline:hybrid | 0.01053 | 0.04545 | 0.01758 | 0.00881 | 0.03165 |
| baseline:r_e7 | 0.00548 | 0.03636 | 0.01848 | 0.00537 | 0.03022 |

K=10

| experiment | recall@10 | hit_rate@10 | mrr@10 | ndcg@10 | judged_fraction@10 |
| --- | --- | --- | --- | --- | --- |
| requested_exact:hybrid | 0.03528 | 0.08182 | 0.02304 | 0.01651 | 0.03165 |
| requested_exact:selected_signed_intent | 0.03891 | 0.10000 | 0.03114 | 0.01770 | 0.03381 |
| requested_exact:selected_all_terms | 0.03891 | 0.10000 | 0.03114 | 0.01770 | 0.03309 |
| requested_exact:frozen_all_terms | 0.03891 | 0.10000 | 0.03114 | 0.01770 | 0.03309 |
| requested_exact:r_e7_style | 0.03891 | 0.10000 | 0.02766 | 0.01677 | 0.03165 |
| symmetric_exact:hybrid | 0.03528 | 0.08182 | 0.02304 | 0.01651 | 0.03165 |
| symmetric_exact:selected_signed_intent | 0.03891 | 0.10000 | 0.03618 | 0.01900 | 0.03309 |
| symmetric_exact:selected_all_terms | 0.03891 | 0.10000 | 0.03618 | 0.01900 | 0.03237 |
| symmetric_exact:frozen_all_terms | 0.03891 | 0.10000 | 0.03618 | 0.01900 | 0.03237 |
| symmetric_exact:r_e7_style | 0.03891 | 0.10000 | 0.02939 | 0.01728 | 0.03237 |
| current:frozen_all_terms | 0.03891 | 0.10000 | 0.03114 | 0.01770 | 0.03381 |
| current:r_e7_equivalent | 0.03891 | 0.10000 | 0.02766 | 0.01677 | 0.03237 |
| ablation:requested_current_context | 0.03891 | 0.10000 | 0.03114 | 0.01770 | 0.03381 |
| ablation:symmetric_current_context | 0.03891 | 0.10000 | 0.03618 | 0.01900 | 0.03309 |
| ablation:dimension_exact_context | 0.03891 | 0.10000 | 0.03114 | 0.01770 | 0.03309 |
| baseline:hybrid | 0.03528 | 0.08182 | 0.02304 | 0.01651 | 0.03165 |
| baseline:r_e7 | 0.04801 | 0.10909 | 0.02857 | 0.01940 | 0.03237 |

K=20

| experiment | recall@20 | hit_rate@20 | mrr@20 | ndcg@20 | judged_fraction@20 |
| --- | --- | --- | --- | --- | --- |
| requested_exact:hybrid | 0.03992 | 0.10000 | 0.02409 | 0.01731 | 0.02698 |
| requested_exact:selected_signed_intent | 0.06021 | 0.13636 | 0.03364 | 0.02412 | 0.03165 |
| requested_exact:selected_all_terms | 0.06476 | 0.14545 | 0.03409 | 0.02539 | 0.03201 |
| requested_exact:frozen_all_terms | 0.06476 | 0.14545 | 0.03409 | 0.02539 | 0.03201 |
| requested_exact:r_e7_style | 0.04627 | 0.11818 | 0.02877 | 0.01901 | 0.03058 |
| symmetric_exact:hybrid | 0.03992 | 0.10000 | 0.02409 | 0.01731 | 0.02698 |
| symmetric_exact:selected_signed_intent | 0.06021 | 0.13636 | 0.03875 | 0.02550 | 0.03165 |
| symmetric_exact:selected_all_terms | 0.06476 | 0.14545 | 0.03921 | 0.02677 | 0.03201 |
| symmetric_exact:frozen_all_terms | 0.06476 | 0.14545 | 0.03921 | 0.02677 | 0.03201 |
| symmetric_exact:r_e7_style | 0.04627 | 0.11818 | 0.03050 | 0.01951 | 0.03022 |
| current:frozen_all_terms | 0.06021 | 0.13636 | 0.03364 | 0.02412 | 0.03165 |
| current:r_e7_equivalent | 0.04627 | 0.11818 | 0.02877 | 0.01901 | 0.03058 |
| ablation:requested_current_context | 0.06021 | 0.13636 | 0.03364 | 0.02412 | 0.03165 |
| ablation:symmetric_current_context | 0.06021 | 0.13636 | 0.03875 | 0.02550 | 0.03165 |
| ablation:dimension_exact_context | 0.06476 | 0.14545 | 0.03409 | 0.02539 | 0.03201 |
| baseline:hybrid | 0.03992 | 0.10000 | 0.02409 | 0.01731 | 0.02698 |
| baseline:r_e7 | 0.05082 | 0.11818 | 0.02922 | 0.01993 | 0.03058 |

## Phase 11 paired ablations

| protocol | split | experiment | delta_vs_full | lower | upper | positive_queries | ndcg_at_10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| temporal | validation | full:complete | 0.00000 | 0.00000 | 0.00000 | 113 | 0.03146 |
| temporal | validation | full:minus_bm25 | 0.00184 | -0.00842 | 0.01364 | 113 | 0.03331 |
| temporal | validation | full:minus_dense | 0.00102 | -0.00783 | 0.00986 | 113 | 0.03248 |
| temporal | validation | full:minus_entities | -0.01226 | -0.02862 | -0.00065 | 113 | 0.01921 |
| temporal | validation | full:minus_context | -0.00136 | -0.00838 | 0.00332 | 113 | 0.03010 |
| temporal | validation | full:minus_intent | -0.00419 | -0.01768 | 0.00728 | 113 | 0.02727 |
| temporal | validation | selected:complete | 0.00000 | 0.00000 | 0.00000 | 113 | 0.03146 |
| temporal | validation | selected:minus_bm25 | 0.00184 | -0.00842 | 0.01364 | 113 | 0.03331 |
| temporal | validation | selected:minus_dense | 0.00102 | -0.00783 | 0.00986 | 113 | 0.03248 |
| temporal | validation | selected:minus_entities | -0.01226 | -0.02862 | -0.00065 | 113 | 0.01921 |
| temporal | validation | selected:minus_context | -0.00136 | -0.00838 | 0.00332 | 113 | 0.03010 |
| temporal | validation | selected:minus_intent | -0.00419 | -0.01768 | 0.00728 | 113 | 0.02727 |
| temporal | test | full:complete | 0.00000 | 0.00000 | 0.00000 | 110 | 0.01940 |
| temporal | test | full:minus_bm25 | -0.01126 | -0.02521 | 0.00099 | 110 | 0.00813 |
| temporal | test | full:minus_dense | 0.00158 | -0.00130 | 0.00560 | 110 | 0.02098 |
| temporal | test | full:minus_entities | -0.00315 | -0.01266 | 0.00420 | 110 | 0.01625 |
| temporal | test | full:minus_context | -0.00117 | -0.00788 | 0.00439 | 110 | 0.01823 |
| temporal | test | full:minus_intent | -0.00835 | -0.01887 | -0.00036 | 110 | 0.01105 |
| temporal | test | selected:complete | 0.00000 | 0.00000 | 0.00000 | 110 | 0.01940 |
| temporal | test | selected:minus_bm25 | -0.01126 | -0.02521 | 0.00099 | 110 | 0.00813 |
| temporal | test | selected:minus_dense | 0.00158 | -0.00130 | 0.00560 | 110 | 0.02098 |
| temporal | test | selected:minus_entities | -0.00315 | -0.01266 | 0.00420 | 110 | 0.01625 |
| temporal | test | selected:minus_context | -0.00117 | -0.00788 | 0.00439 | 110 | 0.01823 |
| temporal | test | selected:minus_intent | -0.00835 | -0.01887 | -0.00036 | 110 | 0.01105 |
| query | validation | full:complete | 0.00000 | 0.00000 | 0.00000 | 70 | 0.01243 |
| query | validation | full:minus_bm25 | -0.00043 | -0.01474 | 0.01214 | 70 | 0.01200 |
| query | validation | full:minus_dense | -0.00050 | -0.00164 | 0.00024 | 70 | 0.01193 |
| query | validation | full:minus_entities | 0.00251 | -0.00054 | 0.00668 | 70 | 0.01494 |
| query | validation | full:minus_context | 0.00111 | -0.00360 | 0.00660 | 70 | 0.01354 |
| query | validation | full:minus_intent | -0.00132 | -0.01537 | 0.01178 | 70 | 0.01111 |
| query | validation | selected:complete | 0.00000 | 0.00000 | 0.00000 | 70 | 0.01243 |
| query | validation | selected:minus_bm25 | -0.00043 | -0.01474 | 0.01214 | 70 | 0.01200 |
| query | validation | selected:minus_dense | -0.00050 | -0.00164 | 0.00024 | 70 | 0.01193 |
| query | validation | selected:minus_entities | 0.00251 | -0.00054 | 0.00668 | 70 | 0.01494 |
| query | validation | selected:minus_context | 0.00111 | -0.00360 | 0.00660 | 70 | 0.01354 |
| query | validation | selected:minus_intent | -0.00132 | -0.01537 | 0.01178 | 70 | 0.01111 |
| query | test | full:complete | 0.00000 | 0.00000 | 0.00000 | 68 | 0.01642 |
| query | test | full:minus_bm25 | -0.00101 | -0.00531 | 0.00189 | 68 | 0.01540 |
| query | test | full:minus_dense | -0.00153 | -0.00531 | 0.00052 | 68 | 0.01488 |
| query | test | full:minus_entities | -0.00387 | -0.01045 | 0.00181 | 68 | 0.01255 |
| query | test | full:minus_context | -0.00319 | -0.00934 | 0.00000 | 68 | 0.01322 |
| query | test | full:minus_intent | -0.00597 | -0.01436 | 0.00027 | 68 | 0.01045 |
| query | test | selected:complete | 0.00000 | 0.00000 | 0.00000 | 68 | 0.01642 |
| query | test | selected:minus_bm25 | -0.00101 | -0.00531 | 0.00189 | 68 | 0.01540 |
| query | test | selected:minus_dense | -0.00153 | -0.00531 | 0.00052 | 68 | 0.01488 |
| query | test | selected:minus_entities | -0.00387 | -0.01045 | 0.00181 | 68 | 0.01255 |
| query | test | selected:minus_context | -0.00319 | -0.00934 | 0.00000 | 68 | 0.01322 |
| query | test | selected:minus_intent | -0.00597 | -0.01436 | 0.00027 | 68 | 0.01045 |
| query_dedup | validation | full:complete | 0.00000 | 0.00000 | 0.00000 | 69 | 0.03418 |
| query_dedup | validation | full:minus_bm25 | -0.00151 | -0.01536 | 0.01104 | 69 | 0.03267 |
| query_dedup | validation | full:minus_dense | -0.00039 | -0.00145 | 0.00021 | 69 | 0.03379 |
| query_dedup | validation | full:minus_entities | 0.00063 | -0.00251 | 0.00458 | 69 | 0.03481 |
| query_dedup | validation | full:minus_context | -0.00293 | -0.01169 | 0.00309 | 69 | 0.03125 |
| query_dedup | validation | full:minus_intent | -0.00596 | -0.01971 | 0.00596 | 69 | 0.02822 |
| query_dedup | validation | selected:complete | 0.00000 | 0.00000 | 0.00000 | 69 | 0.03418 |
| query_dedup | validation | selected:minus_bm25 | -0.00151 | -0.01536 | 0.01104 | 69 | 0.03267 |
| query_dedup | validation | selected:minus_dense | -0.00039 | -0.00145 | 0.00021 | 69 | 0.03379 |
| query_dedup | validation | selected:minus_entities | 0.00063 | -0.00251 | 0.00458 | 69 | 0.03481 |
| query_dedup | validation | selected:minus_context | -0.00293 | -0.01169 | 0.00309 | 69 | 0.03125 |
| query_dedup | validation | selected:minus_intent | -0.00596 | -0.01971 | 0.00596 | 69 | 0.02822 |
| query_dedup | test | full:complete | 0.00000 | 0.00000 | 0.00000 | 68 | 0.01123 |
| query_dedup | test | full:minus_bm25 | -0.00424 | -0.01030 | 0.00046 | 68 | 0.00698 |
| query_dedup | test | full:minus_dense | 0.00180 | -0.00534 | 0.01253 | 68 | 0.01303 |
| query_dedup | test | full:minus_entities | -0.00076 | -0.00581 | 0.00327 | 68 | 0.01047 |
| query_dedup | test | full:minus_context | -0.00318 | -0.00846 | 0.00078 | 68 | 0.00805 |
| query_dedup | test | full:minus_intent | 0.00019 | -0.00838 | 0.00992 | 68 | 0.01142 |
| query_dedup | test | selected:complete | 0.00000 | 0.00000 | 0.00000 | 68 | 0.01123 |
| query_dedup | test | selected:minus_bm25 | -0.00424 | -0.01030 | 0.00046 | 68 | 0.00698 |
| query_dedup | test | selected:minus_dense | 0.00180 | -0.00534 | 0.01253 | 68 | 0.01303 |
| query_dedup | test | selected:minus_entities | -0.00076 | -0.00581 | 0.00327 | 68 | 0.01047 |
| query_dedup | test | selected:minus_context | -0.00318 | -0.00846 | 0.00078 | 68 | 0.00805 |
| query_dedup | test | selected:minus_intent | 0.00019 | -0.00838 | 0.00992 | 68 | 0.01142 |

## Topic-boost chosen/fixed configurations

| experiment | alpha | beta | gated |
| --- | --- | --- | --- |
| hybrid | 0.00000 | 0.00000 | True |
| entity_only | 0.20000 | 0.00000 | True |
| gated_context_only | 0.00000 | 0.00000 | True |
| ungated_context_only | 0.00000 | 0.05000 | False |
| joint_gated | 0.20000 | 0.00000 | True |
| joint_ungated | 0.20000 | 0.10000 | False |
| joint_minus_entities | 0.00000 | 0.00000 | True |
| joint_minus_context | 0.20000 | 0.00000 | True |
| joint_remove_gate | 0.20000 | 0.00000 | False |
| fixed_entity_010 | 0.10000 | 0.00000 | True |
| fixed_joint_gated_010 | 0.10000 | 0.10000 | True |
| fixed_joint_ungated_010 | 0.10000 | 0.10000 | False |

## Topic-boost paired comparisons

| protocol | split | candidate | reference | delta_ndcg | lower | upper | improved | worsened | unchanged | positive_queries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| temporal | validation | entity_only | hybrid | 0.00065 | -0.00754 | 0.00940 | 7 | 4 | 102 | 113 |
| temporal | validation | gated_context_only | hybrid | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 113 | 113 |
| temporal | validation | ungated_context_only | hybrid | 0.00020 | 0.00000 | 0.00061 | 1 | 0 | 112 | 113 |
| temporal | validation | joint_gated | hybrid | 0.00065 | -0.00754 | 0.00940 | 7 | 4 | 102 | 113 |
| temporal | validation | joint_ungated | hybrid | 0.00088 | -0.00726 | 0.00955 | 7 | 4 | 102 | 113 |
| temporal | validation | joint_minus_entities | hybrid | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 113 | 113 |
| temporal | validation | joint_minus_context | hybrid | 0.00065 | -0.00754 | 0.00940 | 7 | 4 | 102 | 113 |
| temporal | validation | joint_remove_gate | hybrid | 0.00065 | -0.00754 | 0.00940 | 7 | 4 | 102 | 113 |
| temporal | validation | fixed_entity_010 | hybrid | -0.00068 | -0.00852 | 0.00770 | 4 | 3 | 106 | 113 |
| temporal | validation | fixed_joint_gated_010 | hybrid | -0.00068 | -0.00852 | 0.00770 | 4 | 3 | 106 | 113 |
| temporal | validation | fixed_joint_ungated_010 | hybrid | -0.00055 | -0.00832 | 0.00776 | 4 | 3 | 106 | 113 |
| temporal | validation | joint_minus_entities | joint_gated | -0.00065 | -0.00940 | 0.00754 | 4 | 7 | 102 | 113 |
| temporal | validation | joint_minus_context | joint_gated | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 113 | 113 |
| temporal | validation | joint_remove_gate | joint_gated | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 113 | 113 |
| temporal | validation | fixed_joint_gated_010 | fixed_joint_ungated_010 | -0.00013 | -0.00038 | 0.00000 | 0 | 1 | 112 | 113 |
| temporal | test | entity_only | hybrid | -0.00140 | -0.00409 | 0.00025 | 1 | 2 | 107 | 110 |
| temporal | test | gated_context_only | hybrid | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 110 | 110 |
| temporal | test | ungated_context_only | hybrid | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 110 | 110 |
| temporal | test | joint_gated | hybrid | -0.00140 | -0.00409 | 0.00025 | 1 | 2 | 107 | 110 |
| temporal | test | joint_ungated | hybrid | -0.00140 | -0.00409 | 0.00025 | 1 | 2 | 107 | 110 |
| temporal | test | joint_minus_entities | hybrid | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 110 | 110 |
| temporal | test | joint_minus_context | hybrid | -0.00140 | -0.00409 | 0.00025 | 1 | 2 | 107 | 110 |
| temporal | test | joint_remove_gate | hybrid | -0.00140 | -0.00409 | 0.00025 | 1 | 2 | 107 | 110 |
| temporal | test | fixed_entity_010 | hybrid | 0.00031 | -0.00005 | 0.00104 | 2 | 1 | 107 | 110 |
| temporal | test | fixed_joint_gated_010 | hybrid | 0.00031 | -0.00005 | 0.00104 | 2 | 1 | 107 | 110 |
| temporal | test | fixed_joint_ungated_010 | hybrid | 0.00031 | -0.00005 | 0.00104 | 2 | 1 | 107 | 110 |
| temporal | test | joint_minus_entities | joint_gated | 0.00140 | -0.00025 | 0.00409 | 2 | 1 | 107 | 110 |
| temporal | test | joint_minus_context | joint_gated | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 110 | 110 |
| temporal | test | joint_remove_gate | joint_gated | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 110 | 110 |
| temporal | test | fixed_joint_gated_010 | fixed_joint_ungated_010 | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 110 | 110 |
| query | validation | entity_only | hybrid | -0.00011 | -0.00681 | 0.00926 | 2 | 5 | 63 | 70 |
| query | validation | gated_context_only | hybrid | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 70 | 70 |
| query | validation | ungated_context_only | hybrid | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 70 | 70 |
| query | validation | joint_gated | hybrid | -0.00011 | -0.00681 | 0.00926 | 2 | 5 | 63 | 70 |
| query | validation | joint_ungated | hybrid | -0.00003 | -0.00677 | 0.00933 | 2 | 5 | 63 | 70 |
| query | validation | joint_minus_entities | hybrid | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 70 | 70 |
| query | validation | joint_minus_context | hybrid | -0.00011 | -0.00681 | 0.00926 | 2 | 5 | 63 | 70 |
| query | validation | joint_remove_gate | hybrid | -0.00011 | -0.00681 | 0.00926 | 2 | 5 | 63 | 70 |
| query | validation | fixed_entity_010 | hybrid | 0.00122 | -0.00485 | 0.00978 | 3 | 2 | 65 | 70 |
| query | validation | fixed_joint_gated_010 | hybrid | 0.00102 | -0.00486 | 0.00964 | 3 | 3 | 64 | 70 |
| query | validation | fixed_joint_ungated_010 | hybrid | 0.00127 | -0.00480 | 0.00981 | 3 | 1 | 66 | 70 |
| query | validation | joint_minus_entities | joint_gated | 0.00011 | -0.00926 | 0.00681 | 5 | 2 | 63 | 70 |
| query | validation | joint_minus_context | joint_gated | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 70 | 70 |
| query | validation | joint_remove_gate | joint_gated | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 70 | 70 |
| query | validation | fixed_joint_gated_010 | fixed_joint_ungated_010 | -0.00025 | -0.00070 | 0.00000 | 0 | 2 | 68 | 70 |
| query | test | entity_only | hybrid | -0.00467 | -0.01148 | -0.00009 | 2 | 6 | 60 | 68 |
| query | test | gated_context_only | hybrid | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 68 | 68 |
| query | test | ungated_context_only | hybrid | 0.00002 | 0.00000 | 0.00005 | 1 | 0 | 67 | 68 |
| query | test | joint_gated | hybrid | -0.00467 | -0.01148 | -0.00009 | 2 | 6 | 60 | 68 |
| query | test | joint_ungated | hybrid | -0.00409 | -0.01027 | -0.00005 | 2 | 6 | 60 | 68 |
| query | test | joint_minus_entities | hybrid | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 68 | 68 |
| query | test | joint_minus_context | hybrid | -0.00467 | -0.01148 | -0.00009 | 2 | 6 | 60 | 68 |
| query | test | joint_remove_gate | hybrid | -0.00467 | -0.01148 | -0.00009 | 2 | 6 | 60 | 68 |
| query | test | fixed_entity_010 | hybrid | -0.00420 | -0.01079 | 0.00003 | 1 | 5 | 62 | 68 |
| query | test | fixed_joint_gated_010 | hybrid | -0.00260 | -0.00771 | 0.00010 | 1 | 4 | 63 | 68 |
| query | test | fixed_joint_ungated_010 | hybrid | -0.00258 | -0.00770 | 0.00012 | 1 | 4 | 63 | 68 |
| query | test | joint_minus_entities | joint_gated | 0.00467 | 0.00009 | 0.01148 | 6 | 2 | 60 | 68 |
| query | test | joint_minus_context | joint_gated | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 68 | 68 |
| query | test | joint_remove_gate | joint_gated | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 68 | 68 |
| query | test | fixed_joint_gated_010 | fixed_joint_ungated_010 | -0.00001 | -0.00003 | 0.00000 | 0 | 1 | 67 | 68 |
| query_dedup | validation | entity_only | hybrid | -0.00168 | -0.00858 | 0.00509 | 1 | 3 | 65 | 69 |
| query_dedup | validation | gated_context_only | hybrid | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 69 | 69 |
| query_dedup | validation | ungated_context_only | hybrid | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 69 | 69 |
| query_dedup | validation | joint_gated | hybrid | -0.00168 | -0.00858 | 0.00509 | 1 | 3 | 65 | 69 |
| query_dedup | validation | joint_ungated | hybrid | -0.00109 | -0.00756 | 0.00567 | 1 | 3 | 65 | 69 |
| query_dedup | validation | joint_minus_entities | hybrid | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 69 | 69 |
| query_dedup | validation | joint_minus_context | hybrid | -0.00168 | -0.00858 | 0.00509 | 1 | 3 | 65 | 69 |
| query_dedup | validation | joint_remove_gate | hybrid | -0.00168 | -0.00858 | 0.00509 | 1 | 3 | 65 | 69 |
| query_dedup | validation | fixed_entity_010 | hybrid | -0.00144 | -0.00806 | 0.00533 | 1 | 2 | 66 | 69 |
| query_dedup | validation | fixed_joint_gated_010 | hybrid | -0.00006 | -0.00647 | 0.00671 | 1 | 2 | 66 | 69 |
| query_dedup | validation | fixed_joint_ungated_010 | hybrid | 0.00014 | -0.00647 | 0.00691 | 1 | 1 | 67 | 69 |
| query_dedup | validation | joint_minus_entities | joint_gated | 0.00168 | -0.00509 | 0.00858 | 3 | 1 | 65 | 69 |
| query_dedup | validation | joint_minus_context | joint_gated | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 69 | 69 |
| query_dedup | validation | joint_remove_gate | joint_gated | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 69 | 69 |
| query_dedup | validation | fixed_joint_gated_010 | fixed_joint_ungated_010 | -0.00020 | -0.00060 | 0.00000 | 0 | 1 | 68 | 69 |
| query_dedup | test | entity_only | hybrid | 0.00315 | -0.00145 | 0.01071 | 5 | 4 | 59 | 68 |
| query_dedup | test | gated_context_only | hybrid | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 68 | 68 |
| query_dedup | test | ungated_context_only | hybrid | 0.00002 | 0.00000 | 0.00005 | 1 | 0 | 67 | 68 |
| query_dedup | test | joint_gated | hybrid | 0.00315 | -0.00145 | 0.01071 | 5 | 4 | 59 | 68 |
| query_dedup | test | joint_ungated | hybrid | 0.00317 | -0.00144 | 0.01074 | 5 | 4 | 59 | 68 |
| query_dedup | test | joint_minus_entities | hybrid | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 68 | 68 |
| query_dedup | test | joint_minus_context | hybrid | 0.00315 | -0.00145 | 0.01071 | 5 | 4 | 59 | 68 |
| query_dedup | test | joint_remove_gate | hybrid | 0.00315 | -0.00145 | 0.01071 | 5 | 4 | 59 | 68 |
| query_dedup | test | fixed_entity_010 | hybrid | 0.00337 | -0.00019 | 0.01011 | 4 | 2 | 62 | 68 |
| query_dedup | test | fixed_joint_gated_010 | hybrid | 0.00337 | -0.00019 | 0.01011 | 4 | 2 | 62 | 68 |
| query_dedup | test | fixed_joint_ungated_010 | hybrid | 0.00338 | -0.00017 | 0.01011 | 4 | 2 | 62 | 68 |
| query_dedup | test | joint_minus_entities | joint_gated | -0.00315 | -0.01071 | 0.00145 | 4 | 5 | 59 | 68 |
| query_dedup | test | joint_minus_context | joint_gated | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 68 | 68 |
| query_dedup | test | joint_remove_gate | joint_gated | 0.00000 | 0.00000 | 0.00000 | 0 | 0 | 68 | 68 |
| query_dedup | test | fixed_joint_gated_010 | fixed_joint_ungated_010 | -0.00001 | -0.00003 | 0.00000 | 0 | 1 | 67 | 68 |

## Repaired signed configurations

| experiment | entity_bonus | entity_penalty | context_bonus | context_penalty |
| --- | --- | --- | --- | --- |
| hybrid | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| repaired_bonuses_only | 0.20000 | 0.00000 | 0.20000 | 0.00000 |
| repaired_penalties_only | 0.00000 | 0.20000 | 0.00000 | 0.00000 |
| repaired_both | 0.20000 | 0.20000 | 0.20000 | 0.00000 |
| repaired_both_minus_entity_bonus | 0.00000 | 0.20000 | 0.20000 | 0.00000 |
| repaired_both_minus_entity_penalty | 0.20000 | 0.00000 | 0.20000 | 0.00000 |
| repaired_both_minus_context_bonus | 0.20000 | 0.20000 | 0.00000 | 0.00000 |
| repaired_both_minus_context_penalty | 0.20000 | 0.20000 | 0.20000 | 0.00000 |
| repaired_fixed_bonuses | 0.05000 | 0.00000 | 0.05000 | 0.00000 |
| repaired_fixed_penalties | 0.00000 | 0.05000 | 0.00000 | 0.05000 |
| repaired_fixed_both | 0.05000 | 0.05000 | 0.05000 | 0.05000 |

## Repaired signed paired comparisons

| protocol | split | candidate | reference | delta_ndcg | lower | upper | positive_queries | improved | worsened | unchanged |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| temporal | validation | repaired_bonuses_only | hybrid | 0.00087 | -0.00727 | 0.00954 | 113 | 7 | 5 | 101 |
| temporal | validation | repaired_penalties_only | hybrid | 0.00065 | -0.00754 | 0.00940 | 113 | 7 | 4 | 102 |
| temporal | validation | repaired_both | hybrid | 0.00201 | -0.00676 | 0.01126 | 113 | 7 | 4 | 102 |
| temporal | validation | repaired_both_minus_entity_bonus | hybrid | 0.00087 | -0.00727 | 0.00954 | 113 | 7 | 5 | 101 |
| temporal | validation | repaired_both_minus_entity_penalty | hybrid | 0.00087 | -0.00727 | 0.00954 | 113 | 7 | 5 | 101 |
| temporal | validation | repaired_both_minus_context_bonus | hybrid | -0.00078 | -0.01132 | 0.01006 | 113 | 7 | 4 | 102 |
| temporal | validation | repaired_both_minus_context_penalty | hybrid | 0.00201 | -0.00676 | 0.01126 | 113 | 7 | 4 | 102 |
| temporal | validation | repaired_fixed_bonuses | hybrid | 0.00032 | -0.00704 | 0.00803 | 113 | 5 | 3 | 105 |
| temporal | validation | repaired_fixed_penalties | hybrid | 0.00032 | -0.00704 | 0.00803 | 113 | 5 | 3 | 105 |
| temporal | validation | repaired_fixed_both | hybrid | -0.00055 | -0.00832 | 0.00776 | 113 | 4 | 3 | 106 |
| temporal | validation | repaired_both_minus_entity_bonus | repaired_both | -0.00114 | -0.00385 | 0.00044 | 113 | 1 | 3 | 109 |
| temporal | validation | repaired_both_minus_entity_penalty | repaired_both | -0.00114 | -0.00385 | 0.00044 | 113 | 1 | 3 | 109 |
| temporal | validation | repaired_both_minus_context_bonus | repaired_both | -0.00279 | -0.00838 | 0.00000 | 113 | 0 | 1 | 112 |
| temporal | validation | repaired_both_minus_context_penalty | repaired_both | 0.00000 | 0.00000 | 0.00000 | 113 | 0 | 0 | 113 |
| temporal | validation | repaired_fixed_both | repaired_fixed_bonuses | -0.00087 | -0.00380 | 0.00123 | 113 | 1 | 2 | 110 |
| temporal | test | repaired_bonuses_only | hybrid | -0.00140 | -0.00409 | 0.00025 | 110 | 1 | 2 | 107 |
| temporal | test | repaired_penalties_only | hybrid | -0.00140 | -0.00409 | 0.00025 | 110 | 1 | 2 | 107 |
| temporal | test | repaired_both | hybrid | -0.00258 | -0.00636 | 0.00024 | 110 | 1 | 4 | 105 |
| temporal | test | repaired_both_minus_entity_bonus | hybrid | -0.00140 | -0.00409 | 0.00025 | 110 | 1 | 2 | 107 |
| temporal | test | repaired_both_minus_entity_penalty | hybrid | -0.00140 | -0.00409 | 0.00025 | 110 | 1 | 2 | 107 |
| temporal | test | repaired_both_minus_context_bonus | hybrid | -0.00158 | -0.00573 | 0.00208 | 110 | 2 | 4 | 104 |
| temporal | test | repaired_both_minus_context_penalty | hybrid | -0.00258 | -0.00636 | 0.00024 | 110 | 1 | 4 | 105 |
| temporal | test | repaired_fixed_bonuses | hybrid | 0.00033 | -0.00001 | 0.00107 | 110 | 2 | 1 | 107 |
| temporal | test | repaired_fixed_penalties | hybrid | 0.00033 | -0.00001 | 0.00107 | 110 | 2 | 1 | 107 |
| temporal | test | repaired_fixed_both | hybrid | 0.00031 | -0.00005 | 0.00104 | 110 | 2 | 1 | 107 |
| temporal | test | repaired_both_minus_entity_bonus | repaired_both | 0.00118 | -0.00038 | 0.00368 | 110 | 2 | 1 | 107 |
| temporal | test | repaired_both_minus_entity_penalty | repaired_both | 0.00118 | -0.00038 | 0.00368 | 110 | 2 | 1 | 107 |
| temporal | test | repaired_both_minus_context_bonus | repaired_both | 0.00100 | 0.00000 | 0.00300 | 110 | 1 | 0 | 109 |
| temporal | test | repaired_both_minus_context_penalty | repaired_both | 0.00000 | 0.00000 | 0.00000 | 110 | 0 | 0 | 110 |
| temporal | test | repaired_fixed_both | repaired_fixed_bonuses | -0.00002 | -0.00006 | 0.00000 | 110 | 0 | 1 | 109 |
| query | validation | repaired_bonuses_only | hybrid | 0.00002 | -0.00674 | 0.00938 | 70 | 2 | 4 | 64 |
| query | validation | repaired_penalties_only | hybrid | -0.00011 | -0.00681 | 0.00926 | 70 | 2 | 5 | 63 |
| query | validation | repaired_both | hybrid | -0.00149 | -0.00883 | 0.00792 | 70 | 2 | 6 | 62 |
| query | validation | repaired_both_minus_entity_bonus | hybrid | 0.00002 | -0.00674 | 0.00938 | 70 | 2 | 4 | 64 |
| query | validation | repaired_both_minus_entity_penalty | hybrid | 0.00002 | -0.00674 | 0.00938 | 70 | 2 | 4 | 64 |
| query | validation | repaired_both_minus_context_bonus | hybrid | -0.00221 | -0.00997 | 0.00716 | 70 | 2 | 6 | 62 |
| query | validation | repaired_both_minus_context_penalty | hybrid | -0.00149 | -0.00883 | 0.00792 | 70 | 2 | 6 | 62 |
| query | validation | repaired_fixed_bonuses | hybrid | -0.00142 | -0.00621 | 0.00157 | 70 | 3 | 1 | 66 |
| query | validation | repaired_fixed_penalties | hybrid | -0.00142 | -0.00621 | 0.00157 | 70 | 3 | 1 | 66 |
| query | validation | repaired_fixed_both | hybrid | 0.00127 | -0.00480 | 0.00981 | 70 | 3 | 1 | 66 |
| query | validation | repaired_both_minus_entity_bonus | repaired_both | 0.00151 | 0.00004 | 0.00397 | 70 | 4 | 0 | 66 |
| query | validation | repaired_both_minus_entity_penalty | repaired_both | 0.00151 | 0.00004 | 0.00397 | 70 | 4 | 0 | 66 |
| query | validation | repaired_both_minus_context_bonus | repaired_both | -0.00073 | -0.00218 | 0.00000 | 70 | 0 | 1 | 69 |
| query | validation | repaired_both_minus_context_penalty | repaired_both | 0.00000 | 0.00000 | 0.00000 | 70 | 0 | 0 | 70 |
| query | validation | repaired_fixed_both | repaired_fixed_bonuses | 0.00269 | -0.00103 | 0.00961 | 70 | 1 | 1 | 68 |
| query | test | repaired_bonuses_only | hybrid | -0.00543 | -0.01332 | -0.00005 | 68 | 2 | 6 | 60 |
| query | test | repaired_penalties_only | hybrid | -0.00467 | -0.01148 | -0.00009 | 68 | 2 | 6 | 60 |
| query | test | repaired_both | hybrid | -0.00464 | -0.01152 | 0.00004 | 68 | 2 | 6 | 60 |
| query | test | repaired_both_minus_entity_bonus | hybrid | -0.00543 | -0.01332 | -0.00005 | 68 | 2 | 6 | 60 |
| query | test | repaired_both_minus_entity_penalty | hybrid | -0.00543 | -0.01332 | -0.00005 | 68 | 2 | 6 | 60 |
| query | test | repaired_both_minus_context_bonus | hybrid | -0.00487 | -0.01169 | -0.00014 | 68 | 2 | 6 | 60 |
| query | test | repaired_both_minus_context_penalty | hybrid | -0.00464 | -0.01152 | 0.00004 | 68 | 2 | 6 | 60 |
| query | test | repaired_fixed_bonuses | hybrid | -0.00224 | -0.00612 | 0.00005 | 68 | 1 | 5 | 62 |
| query | test | repaired_fixed_penalties | hybrid | -0.00224 | -0.00612 | 0.00005 | 68 | 1 | 5 | 62 |
| query | test | repaired_fixed_both | hybrid | -0.00419 | -0.01078 | 0.00004 | 68 | 1 | 5 | 62 |
| query | test | repaired_both_minus_entity_bonus | repaired_both | -0.00079 | -0.00257 | 0.00043 | 68 | 1 | 2 | 65 |
| query | test | repaired_both_minus_entity_penalty | repaired_both | -0.00079 | -0.00257 | 0.00043 | 68 | 1 | 2 | 65 |
| query | test | repaired_both_minus_context_bonus | repaired_both | -0.00023 | -0.00070 | 0.00000 | 68 | 0 | 1 | 67 |
| query | test | repaired_both_minus_context_penalty | repaired_both | 0.00000 | 0.00000 | 0.00000 | 68 | 0 | 0 | 68 |
| query | test | repaired_fixed_both | repaired_fixed_bonuses | -0.00195 | -0.00582 | 0.00000 | 68 | 0 | 2 | 66 |
| query_dedup | validation | repaired_bonuses_only | hybrid | -0.00241 | -0.00980 | 0.00461 | 69 | 1 | 3 | 65 |
| query_dedup | validation | repaired_penalties_only | hybrid | -0.00168 | -0.00858 | 0.00509 | 69 | 1 | 3 | 65 |
| query_dedup | validation | repaired_both | hybrid | -0.00206 | -0.00906 | 0.00466 | 69 | 1 | 4 | 64 |
| query_dedup | validation | repaired_both_minus_entity_bonus | hybrid | -0.00241 | -0.00980 | 0.00461 | 69 | 1 | 3 | 65 |
| query_dedup | validation | repaired_both_minus_entity_penalty | hybrid | -0.00241 | -0.00980 | 0.00461 | 69 | 1 | 3 | 65 |
| query_dedup | validation | repaired_both_minus_context_bonus | hybrid | -0.00206 | -0.00906 | 0.00466 | 69 | 1 | 4 | 64 |
| query_dedup | validation | repaired_both_minus_context_penalty | hybrid | -0.00206 | -0.00906 | 0.00466 | 69 | 1 | 4 | 64 |
| query_dedup | validation | repaired_fixed_bonuses | hybrid | -0.00091 | -0.00791 | 0.00617 | 69 | 2 | 2 | 65 |
| query_dedup | validation | repaired_fixed_penalties | hybrid | -0.00091 | -0.00791 | 0.00617 | 69 | 2 | 2 | 65 |
| query_dedup | validation | repaired_fixed_both | hybrid | -0.00144 | -0.00806 | 0.00533 | 69 | 1 | 2 | 66 |
| query_dedup | validation | repaired_both_minus_entity_bonus | repaired_both | -0.00035 | -0.00231 | 0.00115 | 69 | 2 | 1 | 66 |
| query_dedup | validation | repaired_both_minus_entity_penalty | repaired_both | -0.00035 | -0.00231 | 0.00115 | 69 | 2 | 1 | 66 |
| query_dedup | validation | repaired_both_minus_context_bonus | repaired_both | 0.00000 | 0.00000 | 0.00000 | 69 | 0 | 0 | 69 |
| query_dedup | validation | repaired_both_minus_context_penalty | repaired_both | 0.00000 | 0.00000 | 0.00000 | 69 | 0 | 0 | 69 |
| query_dedup | validation | repaired_fixed_both | repaired_fixed_bonuses | -0.00052 | -0.00157 | 0.00000 | 69 | 0 | 1 | 68 |
| query_dedup | test | repaired_bonuses_only | hybrid | 0.00317 | -0.00144 | 0.01074 | 68 | 5 | 4 | 59 |
| query_dedup | test | repaired_penalties_only | hybrid | 0.00315 | -0.00145 | 0.01071 | 68 | 5 | 4 | 59 |
| query_dedup | test | repaired_both | hybrid | 0.00369 | -0.00111 | 0.01145 | 68 | 5 | 4 | 59 |
| query_dedup | test | repaired_both_minus_entity_bonus | hybrid | 0.00317 | -0.00144 | 0.01074 | 68 | 5 | 4 | 59 |
| query_dedup | test | repaired_both_minus_entity_penalty | hybrid | 0.00317 | -0.00144 | 0.01074 | 68 | 5 | 4 | 59 |
| query_dedup | test | repaired_both_minus_context_bonus | hybrid | 0.00346 | -0.00135 | 0.01124 | 68 | 5 | 4 | 59 |
| query_dedup | test | repaired_both_minus_context_penalty | hybrid | 0.00369 | -0.00111 | 0.01145 | 68 | 5 | 4 | 59 |
| query_dedup | test | repaired_fixed_bonuses | hybrid | 0.00008 | -0.00028 | 0.00046 | 68 | 3 | 2 | 63 |
| query_dedup | test | repaired_fixed_penalties | hybrid | 0.00008 | -0.00028 | 0.00046 | 68 | 3 | 2 | 63 |
| query_dedup | test | repaired_fixed_both | hybrid | 0.00338 | -0.00017 | 0.01011 | 68 | 4 | 2 | 62 |
| query_dedup | test | repaired_both_minus_entity_bonus | repaired_both | -0.00053 | -0.00136 | 0.00000 | 68 | 0 | 2 | 66 |
| query_dedup | test | repaired_both_minus_entity_penalty | repaired_both | -0.00053 | -0.00136 | 0.00000 | 68 | 0 | 2 | 66 |
| query_dedup | test | repaired_both_minus_context_bonus | repaired_both | -0.00023 | -0.00070 | 0.00000 | 68 | 0 | 1 | 67 |
| query_dedup | test | repaired_both_minus_context_penalty | repaired_both | 0.00000 | 0.00000 | 0.00000 | 68 | 0 | 0 | 68 |
| query_dedup | test | repaired_fixed_both | repaired_fixed_bonuses | 0.00330 | 0.00000 | 0.00990 | 68 | 1 | 0 | 67 |

## Intent-signed configurations

| experiment | entity_bonus | entity_penalty | context_bonus | context_penalty | intent_bonus |
| --- | --- | --- | --- | --- | --- |
| legacy:hybrid | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| legacy:intent_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.10000 |
| legacy:signed_only | 0.20000 | 0.20000 | 0.20000 | 0.00000 | 0.00000 |
| legacy:signed_plus_intent | 0.20000 | 0.20000 | 0.05000 | 0.00000 | 0.50000 |
| legacy:all_terms_nonzero | 0.20000 | 0.20000 | 0.05000 | 0.05000 | 0.50000 |
| legacy:prior_signed_plus_intent | 0.20000 | 0.20000 | 0.20000 | 0.00000 | 0.50000 |
| legacy:fixed_all_005_intent_020 | 0.05000 | 0.05000 | 0.05000 | 0.05000 | 0.20000 |
| legacy:r_e7_equivalent | 0.50000 | 0.00000 | 0.50000 | 0.00000 | 0.50000 |
| legacy:all_terms_minus_entity_bonus | 0.00000 | 0.20000 | 0.05000 | 0.05000 | 0.50000 |
| legacy:all_terms_minus_entity_penalty | 0.20000 | 0.00000 | 0.05000 | 0.05000 | 0.50000 |
| legacy:all_terms_minus_context_bonus | 0.20000 | 0.20000 | 0.00000 | 0.05000 | 0.50000 |
| legacy:all_terms_minus_context_penalty | 0.20000 | 0.20000 | 0.05000 | 0.00000 | 0.50000 |
| legacy:all_terms_minus_intent_bonus | 0.20000 | 0.20000 | 0.05000 | 0.05000 | 0.00000 |
| repaired:hybrid | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| repaired:intent_only | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.10000 |
| repaired:signed_only | 0.20000 | 0.20000 | 0.20000 | 0.00000 | 0.00000 |
| repaired:signed_plus_intent | 0.20000 | 0.20000 | 0.05000 | 0.00000 | 0.50000 |
| repaired:all_terms_nonzero | 0.20000 | 0.20000 | 0.05000 | 0.05000 | 0.50000 |
| repaired:prior_signed_plus_intent | 0.20000 | 0.20000 | 0.20000 | 0.00000 | 0.50000 |
| repaired:fixed_all_005_intent_020 | 0.05000 | 0.05000 | 0.05000 | 0.05000 | 0.20000 |
| repaired:r_e7_equivalent | 0.50000 | 0.00000 | 0.50000 | 0.00000 | 0.50000 |
| repaired:all_terms_minus_entity_bonus | 0.00000 | 0.20000 | 0.05000 | 0.05000 | 0.50000 |
| repaired:all_terms_minus_entity_penalty | 0.20000 | 0.00000 | 0.05000 | 0.05000 | 0.50000 |
| repaired:all_terms_minus_context_bonus | 0.20000 | 0.20000 | 0.00000 | 0.05000 | 0.50000 |
| repaired:all_terms_minus_context_penalty | 0.20000 | 0.20000 | 0.05000 | 0.00000 | 0.50000 |
| repaired:all_terms_minus_intent_bonus | 0.20000 | 0.20000 | 0.05000 | 0.05000 | 0.00000 |

## Intent-signed paired comparisons

| protocol | split | candidate | reference | delta_ndcg | lower | upper | positive_queries | improved | worsened | unchanged |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| temporal | validation | legacy:intent_only | legacy:hybrid | -0.00187 | -0.00913 | 0.00389 | 113 | 4 | 5 | 104 |
| temporal | validation | legacy:intent_only | legacy:signed_only | -0.00388 | -0.01113 | 0.00145 | 113 | 3 | 7 | 103 |
| temporal | validation | legacy:intent_only | legacy:r_e7_equivalent | -0.00789 | -0.02122 | 0.00183 | 113 | 4 | 6 | 103 |
| temporal | validation | legacy:signed_only | legacy:hybrid | 0.00201 | -0.00676 | 0.01126 | 113 | 7 | 4 | 102 |
| temporal | validation | legacy:signed_only | legacy:r_e7_equivalent | -0.00400 | -0.01753 | 0.00759 | 113 | 5 | 6 | 102 |
| temporal | validation | legacy:signed_plus_intent | legacy:hybrid | 0.00595 | -0.00719 | 0.02360 | 113 | 7 | 7 | 99 |
| temporal | validation | legacy:signed_plus_intent | legacy:signed_only | 0.00394 | -0.00753 | 0.01729 | 113 | 7 | 6 | 100 |
| temporal | validation | legacy:signed_plus_intent | legacy:r_e7_equivalent | -0.00006 | -0.00113 | 0.00144 | 113 | 1 | 3 | 109 |
| temporal | validation | legacy:all_terms_nonzero | legacy:hybrid | 0.00595 | -0.00719 | 0.02360 | 113 | 7 | 7 | 99 |
| temporal | validation | legacy:all_terms_nonzero | legacy:signed_only | 0.00394 | -0.00753 | 0.01729 | 113 | 7 | 6 | 100 |
| temporal | validation | legacy:all_terms_nonzero | legacy:r_e7_equivalent | -0.00006 | -0.00113 | 0.00144 | 113 | 1 | 3 | 109 |
| temporal | validation | legacy:prior_signed_plus_intent | legacy:hybrid | 0.00570 | -0.00773 | 0.02311 | 113 | 6 | 8 | 99 |
| temporal | validation | legacy:prior_signed_plus_intent | legacy:signed_only | 0.00369 | -0.00793 | 0.01723 | 113 | 6 | 6 | 101 |
| temporal | validation | legacy:prior_signed_plus_intent | legacy:r_e7_equivalent | -0.00031 | -0.00091 | 0.00000 | 113 | 0 | 2 | 111 |
| temporal | validation | legacy:fixed_all_005_intent_020 | legacy:hybrid | -0.00070 | -0.00854 | 0.00663 | 113 | 5 | 5 | 103 |
| temporal | validation | legacy:fixed_all_005_intent_020 | legacy:signed_only | -0.00271 | -0.00965 | 0.00214 | 113 | 3 | 6 | 104 |
| temporal | validation | legacy:fixed_all_005_intent_020 | legacy:r_e7_equivalent | -0.00671 | -0.01792 | 0.00178 | 113 | 3 | 5 | 105 |
| temporal | validation | legacy:r_e7_equivalent | legacy:hybrid | 0.00601 | -0.00739 | 0.02340 | 113 | 6 | 7 | 100 |
| temporal | validation | legacy:r_e7_equivalent | legacy:signed_only | 0.00400 | -0.00759 | 0.01753 | 113 | 6 | 5 | 102 |
| temporal | validation | legacy:all_terms_minus_entity_bonus | legacy:hybrid | -0.00046 | -0.01213 | 0.01370 | 113 | 7 | 7 | 99 |
| temporal | validation | legacy:all_terms_minus_entity_bonus | legacy:signed_only | -0.00247 | -0.01412 | 0.00991 | 113 | 5 | 6 | 102 |
| temporal | validation | legacy:all_terms_minus_entity_bonus | legacy:r_e7_equivalent | -0.00647 | -0.01605 | 0.00038 | 113 | 1 | 5 | 107 |
| temporal | validation | legacy:all_terms_minus_entity_penalty | legacy:hybrid | -0.00046 | -0.01213 | 0.01370 | 113 | 7 | 7 | 99 |
| temporal | validation | legacy:all_terms_minus_entity_penalty | legacy:signed_only | -0.00247 | -0.01412 | 0.00991 | 113 | 5 | 6 | 102 |
| temporal | validation | legacy:all_terms_minus_entity_penalty | legacy:r_e7_equivalent | -0.00647 | -0.01605 | 0.00038 | 113 | 1 | 5 | 107 |
| temporal | validation | legacy:all_terms_minus_context_bonus | legacy:hybrid | 0.00423 | -0.01030 | 0.02200 | 113 | 7 | 7 | 99 |
| temporal | validation | legacy:all_terms_minus_context_bonus | legacy:signed_only | 0.00222 | -0.01044 | 0.01709 | 113 | 7 | 6 | 100 |
| temporal | validation | legacy:all_terms_minus_context_bonus | legacy:r_e7_equivalent | -0.00178 | -0.00872 | 0.00283 | 113 | 2 | 3 | 108 |
| temporal | validation | legacy:all_terms_minus_context_penalty | legacy:hybrid | 0.00595 | -0.00719 | 0.02360 | 113 | 7 | 7 | 99 |
| temporal | validation | legacy:all_terms_minus_context_penalty | legacy:signed_only | 0.00394 | -0.00753 | 0.01729 | 113 | 7 | 6 | 100 |
| temporal | validation | legacy:all_terms_minus_context_penalty | legacy:r_e7_equivalent | -0.00006 | -0.00113 | 0.00144 | 113 | 1 | 3 | 109 |
| temporal | validation | legacy:all_terms_minus_intent_bonus | legacy:hybrid | 0.00178 | -0.00685 | 0.01111 | 113 | 7 | 4 | 102 |
| temporal | validation | legacy:all_terms_minus_intent_bonus | legacy:signed_only | -0.00023 | -0.00070 | 0.00000 | 113 | 0 | 1 | 112 |
| temporal | validation | legacy:all_terms_minus_intent_bonus | legacy:r_e7_equivalent | -0.00424 | -0.01759 | 0.00726 | 113 | 5 | 7 | 101 |
| temporal | validation | repaired:intent_only | repaired:hybrid | -0.00187 | -0.00913 | 0.00389 | 113 | 4 | 5 | 104 |
| temporal | validation | repaired:intent_only | repaired:signed_only | -0.00388 | -0.01113 | 0.00145 | 113 | 3 | 7 | 103 |
| temporal | validation | repaired:intent_only | repaired:r_e7_equivalent | -0.00789 | -0.02122 | 0.00183 | 113 | 4 | 6 | 103 |
| temporal | validation | repaired:signed_only | repaired:hybrid | 0.00201 | -0.00676 | 0.01126 | 113 | 7 | 4 | 102 |
| temporal | validation | repaired:signed_only | repaired:r_e7_equivalent | -0.00400 | -0.01753 | 0.00759 | 113 | 5 | 6 | 102 |
| temporal | validation | repaired:signed_plus_intent | repaired:hybrid | 0.00595 | -0.00719 | 0.02360 | 113 | 7 | 7 | 99 |
| temporal | validation | repaired:signed_plus_intent | repaired:signed_only | 0.00394 | -0.00753 | 0.01729 | 113 | 7 | 6 | 100 |
| temporal | validation | repaired:signed_plus_intent | repaired:r_e7_equivalent | -0.00006 | -0.00113 | 0.00144 | 113 | 1 | 3 | 109 |
| temporal | validation | repaired:all_terms_nonzero | repaired:hybrid | 0.00595 | -0.00719 | 0.02360 | 113 | 7 | 7 | 99 |
| temporal | validation | repaired:all_terms_nonzero | repaired:signed_only | 0.00394 | -0.00753 | 0.01729 | 113 | 7 | 6 | 100 |
| temporal | validation | repaired:all_terms_nonzero | repaired:r_e7_equivalent | -0.00006 | -0.00113 | 0.00144 | 113 | 1 | 3 | 109 |
| temporal | validation | repaired:prior_signed_plus_intent | repaired:hybrid | 0.00570 | -0.00773 | 0.02311 | 113 | 6 | 8 | 99 |
| temporal | validation | repaired:prior_signed_plus_intent | repaired:signed_only | 0.00369 | -0.00793 | 0.01723 | 113 | 6 | 6 | 101 |
| temporal | validation | repaired:prior_signed_plus_intent | repaired:r_e7_equivalent | -0.00031 | -0.00091 | 0.00000 | 113 | 0 | 2 | 111 |
| temporal | validation | repaired:fixed_all_005_intent_020 | repaired:hybrid | -0.00070 | -0.00854 | 0.00663 | 113 | 5 | 5 | 103 |
| temporal | validation | repaired:fixed_all_005_intent_020 | repaired:signed_only | -0.00271 | -0.00965 | 0.00214 | 113 | 3 | 6 | 104 |
| temporal | validation | repaired:fixed_all_005_intent_020 | repaired:r_e7_equivalent | -0.00671 | -0.01792 | 0.00178 | 113 | 3 | 5 | 105 |
| temporal | validation | repaired:r_e7_equivalent | repaired:hybrid | 0.00601 | -0.00739 | 0.02340 | 113 | 6 | 7 | 100 |
| temporal | validation | repaired:r_e7_equivalent | repaired:signed_only | 0.00400 | -0.00759 | 0.01753 | 113 | 6 | 5 | 102 |
| temporal | validation | repaired:all_terms_minus_entity_bonus | repaired:hybrid | -0.00046 | -0.01213 | 0.01370 | 113 | 7 | 7 | 99 |
| temporal | validation | repaired:all_terms_minus_entity_bonus | repaired:signed_only | -0.00247 | -0.01412 | 0.00991 | 113 | 5 | 6 | 102 |
| temporal | validation | repaired:all_terms_minus_entity_bonus | repaired:r_e7_equivalent | -0.00647 | -0.01605 | 0.00038 | 113 | 1 | 5 | 107 |
| temporal | validation | repaired:all_terms_minus_entity_penalty | repaired:hybrid | -0.00046 | -0.01213 | 0.01370 | 113 | 7 | 7 | 99 |
| temporal | validation | repaired:all_terms_minus_entity_penalty | repaired:signed_only | -0.00247 | -0.01412 | 0.00991 | 113 | 5 | 6 | 102 |
| temporal | validation | repaired:all_terms_minus_entity_penalty | repaired:r_e7_equivalent | -0.00647 | -0.01605 | 0.00038 | 113 | 1 | 5 | 107 |
| temporal | validation | repaired:all_terms_minus_context_bonus | repaired:hybrid | 0.00423 | -0.01030 | 0.02200 | 113 | 7 | 7 | 99 |
| temporal | validation | repaired:all_terms_minus_context_bonus | repaired:signed_only | 0.00222 | -0.01044 | 0.01709 | 113 | 7 | 6 | 100 |
| temporal | validation | repaired:all_terms_minus_context_bonus | repaired:r_e7_equivalent | -0.00178 | -0.00872 | 0.00283 | 113 | 2 | 3 | 108 |
| temporal | validation | repaired:all_terms_minus_context_penalty | repaired:hybrid | 0.00595 | -0.00719 | 0.02360 | 113 | 7 | 7 | 99 |
| temporal | validation | repaired:all_terms_minus_context_penalty | repaired:signed_only | 0.00394 | -0.00753 | 0.01729 | 113 | 7 | 6 | 100 |
| temporal | validation | repaired:all_terms_minus_context_penalty | repaired:r_e7_equivalent | -0.00006 | -0.00113 | 0.00144 | 113 | 1 | 3 | 109 |
| temporal | validation | repaired:all_terms_minus_intent_bonus | repaired:hybrid | 0.00178 | -0.00685 | 0.01111 | 113 | 7 | 4 | 102 |
| temporal | validation | repaired:all_terms_minus_intent_bonus | repaired:signed_only | -0.00023 | -0.00070 | 0.00000 | 113 | 0 | 1 | 112 |
| temporal | validation | repaired:all_terms_minus_intent_bonus | repaired:r_e7_equivalent | -0.00424 | -0.01759 | 0.00726 | 113 | 5 | 7 | 101 |
| temporal | test | legacy:intent_only | legacy:hybrid | -0.00011 | -0.00068 | 0.00042 | 110 | 1 | 3 | 106 |
| temporal | test | legacy:intent_only | legacy:signed_only | 0.00247 | -0.00038 | 0.00631 | 110 | 4 | 2 | 104 |
| temporal | test | legacy:intent_only | legacy:r_e7_equivalent | -0.00300 | -0.01065 | 0.00323 | 110 | 4 | 7 | 99 |
| temporal | test | legacy:signed_only | legacy:hybrid | -0.00258 | -0.00636 | 0.00024 | 110 | 1 | 4 | 105 |
| temporal | test | legacy:signed_only | legacy:r_e7_equivalent | -0.00547 | -0.01269 | 0.00057 | 110 | 2 | 8 | 100 |
| temporal | test | legacy:signed_plus_intent | legacy:hybrid | 0.00119 | -0.00301 | 0.00536 | 110 | 6 | 4 | 100 |
| temporal | test | legacy:signed_plus_intent | legacy:signed_only | 0.00376 | -0.00082 | 0.00843 | 110 | 8 | 2 | 100 |
| temporal | test | legacy:signed_plus_intent | legacy:r_e7_equivalent | -0.00170 | -0.00865 | 0.00181 | 110 | 4 | 1 | 105 |
| temporal | test | legacy:all_terms_nonzero | legacy:hybrid | 0.00119 | -0.00301 | 0.00536 | 110 | 6 | 4 | 100 |
| temporal | test | legacy:all_terms_nonzero | legacy:signed_only | 0.00376 | -0.00082 | 0.00843 | 110 | 8 | 2 | 100 |
| temporal | test | legacy:all_terms_nonzero | legacy:r_e7_equivalent | -0.00170 | -0.00865 | 0.00181 | 110 | 4 | 1 | 105 |
| temporal | test | legacy:prior_signed_plus_intent | legacy:hybrid | 0.00382 | -0.00207 | 0.01128 | 110 | 7 | 4 | 99 |
| temporal | test | legacy:prior_signed_plus_intent | legacy:signed_only | 0.00639 | 0.00004 | 0.01387 | 110 | 9 | 2 | 99 |
| temporal | test | legacy:prior_signed_plus_intent | legacy:r_e7_equivalent | 0.00092 | 0.00006 | 0.00219 | 110 | 4 | 0 | 106 |
| temporal | test | legacy:fixed_all_005_intent_020 | legacy:hybrid | 0.00282 | -0.00244 | 0.01025 | 110 | 3 | 3 | 104 |
| temporal | test | legacy:fixed_all_005_intent_020 | legacy:signed_only | 0.00539 | -0.00108 | 0.01355 | 110 | 6 | 2 | 102 |
| temporal | test | legacy:fixed_all_005_intent_020 | legacy:r_e7_equivalent | -0.00008 | -0.00384 | 0.00367 | 110 | 4 | 5 | 101 |
| temporal | test | legacy:r_e7_equivalent | legacy:hybrid | 0.00289 | -0.00327 | 0.01048 | 110 | 6 | 5 | 99 |
| temporal | test | legacy:r_e7_equivalent | legacy:signed_only | 0.00547 | -0.00057 | 0.01269 | 110 | 8 | 2 | 100 |
| temporal | test | legacy:all_terms_minus_entity_bonus | legacy:hybrid | 0.00494 | -0.00088 | 0.01207 | 110 | 8 | 2 | 100 |
| temporal | test | legacy:all_terms_minus_entity_bonus | legacy:signed_only | 0.00752 | 0.00052 | 0.01554 | 110 | 9 | 2 | 99 |
| temporal | test | legacy:all_terms_minus_entity_bonus | legacy:r_e7_equivalent | 0.00205 | -0.00090 | 0.00541 | 110 | 6 | 2 | 102 |
| temporal | test | legacy:all_terms_minus_entity_penalty | legacy:hybrid | 0.00494 | -0.00088 | 0.01207 | 110 | 8 | 2 | 100 |
| temporal | test | legacy:all_terms_minus_entity_penalty | legacy:signed_only | 0.00752 | 0.00052 | 0.01554 | 110 | 9 | 2 | 99 |
| temporal | test | legacy:all_terms_minus_entity_penalty | legacy:r_e7_equivalent | 0.00205 | -0.00090 | 0.00541 | 110 | 6 | 2 | 102 |
| temporal | test | legacy:all_terms_minus_context_bonus | legacy:hybrid | 0.00119 | -0.00301 | 0.00536 | 110 | 6 | 4 | 100 |
| temporal | test | legacy:all_terms_minus_context_bonus | legacy:signed_only | 0.00376 | -0.00082 | 0.00843 | 110 | 8 | 2 | 100 |
| temporal | test | legacy:all_terms_minus_context_bonus | legacy:r_e7_equivalent | -0.00170 | -0.00865 | 0.00181 | 110 | 4 | 1 | 105 |
| temporal | test | legacy:all_terms_minus_context_penalty | legacy:hybrid | 0.00119 | -0.00301 | 0.00536 | 110 | 6 | 4 | 100 |
| temporal | test | legacy:all_terms_minus_context_penalty | legacy:signed_only | 0.00376 | -0.00082 | 0.00843 | 110 | 8 | 2 | 100 |
| temporal | test | legacy:all_terms_minus_context_penalty | legacy:r_e7_equivalent | -0.00170 | -0.00865 | 0.00181 | 110 | 4 | 1 | 105 |
| temporal | test | legacy:all_terms_minus_intent_bonus | legacy:hybrid | -0.00258 | -0.00636 | 0.00024 | 110 | 1 | 4 | 105 |
| temporal | test | legacy:all_terms_minus_intent_bonus | legacy:signed_only | 0.00000 | 0.00000 | 0.00000 | 110 | 0 | 0 | 110 |
| temporal | test | legacy:all_terms_minus_intent_bonus | legacy:r_e7_equivalent | -0.00547 | -0.01269 | 0.00057 | 110 | 2 | 8 | 100 |
| temporal | test | repaired:intent_only | repaired:hybrid | -0.00011 | -0.00068 | 0.00042 | 110 | 1 | 3 | 106 |
| temporal | test | repaired:intent_only | repaired:signed_only | 0.00247 | -0.00038 | 0.00631 | 110 | 4 | 2 | 104 |
| temporal | test | repaired:intent_only | repaired:r_e7_equivalent | -0.00037 | -0.00447 | 0.00399 | 110 | 4 | 6 | 100 |
| temporal | test | repaired:signed_only | repaired:hybrid | -0.00258 | -0.00636 | 0.00024 | 110 | 1 | 4 | 105 |
| temporal | test | repaired:signed_only | repaired:r_e7_equivalent | -0.00284 | -0.00721 | 0.00144 | 110 | 2 | 7 | 101 |
| temporal | test | repaired:signed_plus_intent | repaired:hybrid | 0.00119 | -0.00301 | 0.00536 | 110 | 6 | 4 | 100 |
| temporal | test | repaired:signed_plus_intent | repaired:signed_only | 0.00376 | -0.00082 | 0.00843 | 110 | 8 | 2 | 100 |
| temporal | test | repaired:signed_plus_intent | repaired:r_e7_equivalent | 0.00092 | 0.00006 | 0.00219 | 110 | 4 | 0 | 106 |
| temporal | test | repaired:all_terms_nonzero | repaired:hybrid | 0.00119 | -0.00301 | 0.00536 | 110 | 6 | 4 | 100 |
| temporal | test | repaired:all_terms_nonzero | repaired:signed_only | 0.00376 | -0.00082 | 0.00843 | 110 | 8 | 2 | 100 |
| temporal | test | repaired:all_terms_nonzero | repaired:r_e7_equivalent | 0.00092 | 0.00006 | 0.00219 | 110 | 4 | 0 | 106 |
| temporal | test | repaired:prior_signed_plus_intent | repaired:hybrid | 0.00119 | -0.00301 | 0.00536 | 110 | 6 | 4 | 100 |
| temporal | test | repaired:prior_signed_plus_intent | repaired:signed_only | 0.00376 | -0.00082 | 0.00843 | 110 | 8 | 2 | 100 |
| temporal | test | repaired:prior_signed_plus_intent | repaired:r_e7_equivalent | 0.00092 | 0.00006 | 0.00219 | 110 | 4 | 0 | 106 |
| temporal | test | repaired:fixed_all_005_intent_020 | repaired:hybrid | 0.00008 | -0.00341 | 0.00331 | 110 | 2 | 3 | 105 |
| temporal | test | repaired:fixed_all_005_intent_020 | repaired:signed_only | 0.00266 | -0.00208 | 0.00764 | 110 | 5 | 2 | 103 |
| temporal | test | repaired:fixed_all_005_intent_020 | repaired:r_e7_equivalent | -0.00018 | -0.00389 | 0.00356 | 110 | 3 | 5 | 102 |
| temporal | test | repaired:r_e7_equivalent | repaired:hybrid | 0.00026 | -0.00408 | 0.00441 | 110 | 5 | 5 | 100 |
| temporal | test | repaired:r_e7_equivalent | repaired:signed_only | 0.00284 | -0.00144 | 0.00721 | 110 | 7 | 2 | 101 |
| temporal | test | repaired:all_terms_minus_entity_bonus | repaired:hybrid | 0.00231 | -0.00169 | 0.00632 | 110 | 7 | 2 | 101 |
| temporal | test | repaired:all_terms_minus_entity_bonus | repaired:signed_only | 0.00489 | -0.00045 | 0.01059 | 110 | 8 | 2 | 100 |
| temporal | test | repaired:all_terms_minus_entity_bonus | repaired:r_e7_equivalent | 0.00205 | -0.00090 | 0.00541 | 110 | 6 | 2 | 102 |
| temporal | test | repaired:all_terms_minus_entity_penalty | repaired:hybrid | 0.00231 | -0.00169 | 0.00632 | 110 | 7 | 2 | 101 |
| temporal | test | repaired:all_terms_minus_entity_penalty | repaired:signed_only | 0.00489 | -0.00045 | 0.01059 | 110 | 8 | 2 | 100 |
| temporal | test | repaired:all_terms_minus_entity_penalty | repaired:r_e7_equivalent | 0.00205 | -0.00090 | 0.00541 | 110 | 6 | 2 | 102 |
| temporal | test | repaired:all_terms_minus_context_bonus | repaired:hybrid | 0.00119 | -0.00301 | 0.00536 | 110 | 6 | 4 | 100 |
| temporal | test | repaired:all_terms_minus_context_bonus | repaired:signed_only | 0.00376 | -0.00082 | 0.00843 | 110 | 8 | 2 | 100 |
| temporal | test | repaired:all_terms_minus_context_bonus | repaired:r_e7_equivalent | 0.00092 | 0.00006 | 0.00219 | 110 | 4 | 0 | 106 |
| temporal | test | repaired:all_terms_minus_context_penalty | repaired:hybrid | 0.00119 | -0.00301 | 0.00536 | 110 | 6 | 4 | 100 |
| temporal | test | repaired:all_terms_minus_context_penalty | repaired:signed_only | 0.00376 | -0.00082 | 0.00843 | 110 | 8 | 2 | 100 |
| temporal | test | repaired:all_terms_minus_context_penalty | repaired:r_e7_equivalent | 0.00092 | 0.00006 | 0.00219 | 110 | 4 | 0 | 106 |
| temporal | test | repaired:all_terms_minus_intent_bonus | repaired:hybrid | -0.00258 | -0.00636 | 0.00024 | 110 | 1 | 4 | 105 |
| temporal | test | repaired:all_terms_minus_intent_bonus | repaired:signed_only | 0.00000 | 0.00000 | 0.00000 | 110 | 0 | 0 | 110 |
| temporal | test | repaired:all_terms_minus_intent_bonus | repaired:r_e7_equivalent | -0.00284 | -0.00721 | 0.00144 | 110 | 2 | 7 | 101 |
| query | validation | legacy:intent_only | legacy:hybrid | -0.00210 | -0.00661 | 0.00054 | 70 | 1 | 4 | 65 |
| query | validation | legacy:intent_only | legacy:signed_only | -0.00061 | -0.00912 | 0.00515 | 70 | 5 | 3 | 62 |
| query | validation | legacy:intent_only | legacy:r_e7_equivalent | 0.00320 | -0.00466 | 0.01271 | 70 | 5 | 4 | 61 |
| query | validation | legacy:signed_only | legacy:hybrid | -0.00149 | -0.00883 | 0.00792 | 70 | 2 | 6 | 62 |
| query | validation | legacy:signed_only | legacy:r_e7_equivalent | 0.00381 | -0.00557 | 0.01563 | 70 | 3 | 6 | 61 |
| query | validation | legacy:signed_plus_intent | legacy:hybrid | -0.00479 | -0.01295 | 0.00245 | 70 | 2 | 6 | 62 |
| query | validation | legacy:signed_plus_intent | legacy:signed_only | -0.00331 | -0.01351 | 0.00465 | 70 | 5 | 3 | 62 |
| query | validation | legacy:signed_plus_intent | legacy:r_e7_equivalent | 0.00051 | -0.00387 | 0.00482 | 70 | 3 | 4 | 63 |
| query | validation | legacy:all_terms_nonzero | legacy:hybrid | -0.00479 | -0.01295 | 0.00245 | 70 | 2 | 6 | 62 |
| query | validation | legacy:all_terms_nonzero | legacy:signed_only | -0.00331 | -0.01351 | 0.00465 | 70 | 5 | 3 | 62 |
| query | validation | legacy:all_terms_nonzero | legacy:r_e7_equivalent | 0.00051 | -0.00387 | 0.00482 | 70 | 3 | 4 | 63 |
| query | validation | legacy:prior_signed_plus_intent | legacy:hybrid | -0.00472 | -0.01286 | 0.00250 | 70 | 3 | 6 | 61 |
| query | validation | legacy:prior_signed_plus_intent | legacy:signed_only | -0.00324 | -0.01342 | 0.00472 | 70 | 5 | 3 | 62 |
| query | validation | legacy:prior_signed_plus_intent | legacy:r_e7_equivalent | 0.00058 | -0.00378 | 0.00489 | 70 | 3 | 3 | 64 |
| query | validation | legacy:fixed_all_005_intent_020 | legacy:hybrid | -0.00049 | -0.00632 | 0.00494 | 70 | 2 | 2 | 66 |
| query | validation | legacy:fixed_all_005_intent_020 | legacy:signed_only | 0.00100 | -0.00800 | 0.00862 | 70 | 5 | 2 | 63 |
| query | validation | legacy:fixed_all_005_intent_020 | legacy:r_e7_equivalent | 0.00481 | -0.00348 | 0.01497 | 70 | 6 | 2 | 62 |
| query | validation | legacy:r_e7_equivalent | legacy:hybrid | -0.00530 | -0.01559 | 0.00354 | 70 | 4 | 6 | 60 |
| query | validation | legacy:r_e7_equivalent | legacy:signed_only | -0.00381 | -0.01563 | 0.00557 | 70 | 6 | 3 | 61 |
| query | validation | legacy:all_terms_minus_entity_bonus | legacy:hybrid | -0.00420 | -0.01278 | 0.00327 | 70 | 4 | 5 | 61 |
| query | validation | legacy:all_terms_minus_entity_bonus | legacy:signed_only | -0.00271 | -0.01311 | 0.00595 | 70 | 5 | 3 | 62 |
| query | validation | legacy:all_terms_minus_entity_bonus | legacy:r_e7_equivalent | 0.00110 | -0.00390 | 0.00643 | 70 | 4 | 2 | 64 |
| query | validation | legacy:all_terms_minus_entity_penalty | legacy:hybrid | -0.00420 | -0.01278 | 0.00327 | 70 | 4 | 5 | 61 |
| query | validation | legacy:all_terms_minus_entity_penalty | legacy:signed_only | -0.00271 | -0.01311 | 0.00595 | 70 | 5 | 3 | 62 |
| query | validation | legacy:all_terms_minus_entity_penalty | legacy:r_e7_equivalent | 0.00110 | -0.00390 | 0.00643 | 70 | 4 | 2 | 64 |
| query | validation | legacy:all_terms_minus_context_bonus | legacy:hybrid | -0.00361 | -0.01071 | 0.00294 | 70 | 2 | 7 | 61 |
| query | validation | legacy:all_terms_minus_context_bonus | legacy:signed_only | -0.00212 | -0.01196 | 0.00512 | 70 | 4 | 4 | 62 |
| query | validation | legacy:all_terms_minus_context_bonus | legacy:r_e7_equivalent | 0.00169 | -0.00331 | 0.00692 | 70 | 4 | 4 | 62 |
| query | validation | legacy:all_terms_minus_context_penalty | legacy:hybrid | -0.00479 | -0.01295 | 0.00245 | 70 | 2 | 6 | 62 |
| query | validation | legacy:all_terms_minus_context_penalty | legacy:signed_only | -0.00331 | -0.01351 | 0.00465 | 70 | 5 | 3 | 62 |
| query | validation | legacy:all_terms_minus_context_penalty | legacy:r_e7_equivalent | 0.00051 | -0.00387 | 0.00482 | 70 | 3 | 4 | 63 |
| query | validation | legacy:all_terms_minus_intent_bonus | legacy:hybrid | -0.00221 | -0.00997 | 0.00716 | 70 | 2 | 6 | 62 |
| query | validation | legacy:all_terms_minus_intent_bonus | legacy:signed_only | -0.00073 | -0.00218 | 0.00000 | 70 | 0 | 1 | 69 |
| query | validation | legacy:all_terms_minus_intent_bonus | legacy:r_e7_equivalent | 0.00309 | -0.00657 | 0.01500 | 70 | 3 | 6 | 61 |
| query | validation | repaired:intent_only | repaired:hybrid | -0.00210 | -0.00661 | 0.00054 | 70 | 1 | 4 | 65 |
| query | validation | repaired:intent_only | repaired:signed_only | -0.00061 | -0.00912 | 0.00515 | 70 | 5 | 3 | 62 |
| query | validation | repaired:intent_only | repaired:r_e7_equivalent | 0.00320 | -0.00466 | 0.01271 | 70 | 5 | 4 | 61 |
| query | validation | repaired:signed_only | repaired:hybrid | -0.00149 | -0.00883 | 0.00792 | 70 | 2 | 6 | 62 |
| query | validation | repaired:signed_only | repaired:r_e7_equivalent | 0.00381 | -0.00557 | 0.01563 | 70 | 3 | 6 | 61 |
| query | validation | repaired:signed_plus_intent | repaired:hybrid | -0.00479 | -0.01295 | 0.00245 | 70 | 2 | 6 | 62 |
| query | validation | repaired:signed_plus_intent | repaired:signed_only | -0.00331 | -0.01351 | 0.00465 | 70 | 5 | 3 | 62 |
| query | validation | repaired:signed_plus_intent | repaired:r_e7_equivalent | 0.00051 | -0.00387 | 0.00482 | 70 | 3 | 4 | 63 |
| query | validation | repaired:all_terms_nonzero | repaired:hybrid | -0.00479 | -0.01295 | 0.00245 | 70 | 2 | 6 | 62 |
| query | validation | repaired:all_terms_nonzero | repaired:signed_only | -0.00331 | -0.01351 | 0.00465 | 70 | 5 | 3 | 62 |
| query | validation | repaired:all_terms_nonzero | repaired:r_e7_equivalent | 0.00051 | -0.00387 | 0.00482 | 70 | 3 | 4 | 63 |
| query | validation | repaired:prior_signed_plus_intent | repaired:hybrid | -0.00472 | -0.01286 | 0.00250 | 70 | 3 | 6 | 61 |
| query | validation | repaired:prior_signed_plus_intent | repaired:signed_only | -0.00324 | -0.01342 | 0.00472 | 70 | 5 | 3 | 62 |
| query | validation | repaired:prior_signed_plus_intent | repaired:r_e7_equivalent | 0.00058 | -0.00378 | 0.00489 | 70 | 3 | 3 | 64 |
| query | validation | repaired:fixed_all_005_intent_020 | repaired:hybrid | -0.00049 | -0.00632 | 0.00494 | 70 | 2 | 2 | 66 |
| query | validation | repaired:fixed_all_005_intent_020 | repaired:signed_only | 0.00100 | -0.00800 | 0.00862 | 70 | 5 | 2 | 63 |
| query | validation | repaired:fixed_all_005_intent_020 | repaired:r_e7_equivalent | 0.00481 | -0.00348 | 0.01497 | 70 | 6 | 2 | 62 |
| query | validation | repaired:r_e7_equivalent | repaired:hybrid | -0.00530 | -0.01559 | 0.00354 | 70 | 4 | 6 | 60 |
| query | validation | repaired:r_e7_equivalent | repaired:signed_only | -0.00381 | -0.01563 | 0.00557 | 70 | 6 | 3 | 61 |
| query | validation | repaired:all_terms_minus_entity_bonus | repaired:hybrid | -0.00420 | -0.01278 | 0.00327 | 70 | 4 | 5 | 61 |
| query | validation | repaired:all_terms_minus_entity_bonus | repaired:signed_only | -0.00271 | -0.01311 | 0.00595 | 70 | 5 | 3 | 62 |
| query | validation | repaired:all_terms_minus_entity_bonus | repaired:r_e7_equivalent | 0.00110 | -0.00390 | 0.00643 | 70 | 4 | 2 | 64 |
| query | validation | repaired:all_terms_minus_entity_penalty | repaired:hybrid | -0.00420 | -0.01278 | 0.00327 | 70 | 4 | 5 | 61 |
| query | validation | repaired:all_terms_minus_entity_penalty | repaired:signed_only | -0.00271 | -0.01311 | 0.00595 | 70 | 5 | 3 | 62 |
| query | validation | repaired:all_terms_minus_entity_penalty | repaired:r_e7_equivalent | 0.00110 | -0.00390 | 0.00643 | 70 | 4 | 2 | 64 |
| query | validation | repaired:all_terms_minus_context_bonus | repaired:hybrid | -0.00361 | -0.01071 | 0.00294 | 70 | 2 | 7 | 61 |
| query | validation | repaired:all_terms_minus_context_bonus | repaired:signed_only | -0.00212 | -0.01196 | 0.00512 | 70 | 4 | 4 | 62 |
| query | validation | repaired:all_terms_minus_context_bonus | repaired:r_e7_equivalent | 0.00169 | -0.00331 | 0.00692 | 70 | 4 | 4 | 62 |
| query | validation | repaired:all_terms_minus_context_penalty | repaired:hybrid | -0.00479 | -0.01295 | 0.00245 | 70 | 2 | 6 | 62 |
| query | validation | repaired:all_terms_minus_context_penalty | repaired:signed_only | -0.00331 | -0.01351 | 0.00465 | 70 | 5 | 3 | 62 |
| query | validation | repaired:all_terms_minus_context_penalty | repaired:r_e7_equivalent | 0.00051 | -0.00387 | 0.00482 | 70 | 3 | 4 | 63 |
| query | validation | repaired:all_terms_minus_intent_bonus | repaired:hybrid | -0.00221 | -0.00997 | 0.00716 | 70 | 2 | 6 | 62 |
| query | validation | repaired:all_terms_minus_intent_bonus | repaired:signed_only | -0.00073 | -0.00218 | 0.00000 | 70 | 0 | 1 | 69 |
| query | validation | repaired:all_terms_minus_intent_bonus | repaired:r_e7_equivalent | 0.00309 | -0.00657 | 0.01500 | 70 | 3 | 6 | 61 |
| query | test | legacy:intent_only | legacy:hybrid | -0.00224 | -0.00751 | 0.00083 | 68 | 3 | 3 | 62 |
| query | test | legacy:intent_only | legacy:signed_only | 0.00185 | -0.00051 | 0.00481 | 68 | 5 | 2 | 61 |
| query | test | legacy:intent_only | legacy:r_e7_equivalent | -0.00341 | -0.01260 | 0.00434 | 68 | 6 | 5 | 57 |
| query | test | legacy:signed_only | legacy:hybrid | -0.00408 | -0.01025 | 0.00009 | 68 | 2 | 6 | 60 |
| query | test | legacy:signed_only | legacy:r_e7_equivalent | -0.00525 | -0.01593 | 0.00307 | 68 | 2 | 6 | 60 |
| query | test | legacy:signed_plus_intent | legacy:hybrid | -0.00196 | -0.01014 | 0.00593 | 68 | 4 | 7 | 57 |
| query | test | legacy:signed_plus_intent | legacy:signed_only | 0.00212 | -0.00419 | 0.00895 | 68 | 6 | 4 | 58 |
| query | test | legacy:signed_plus_intent | legacy:r_e7_equivalent | -0.00313 | -0.00922 | 0.00002 | 68 | 1 | 3 | 64 |
| query | test | legacy:all_terms_nonzero | legacy:hybrid | -0.00196 | -0.01014 | 0.00593 | 68 | 4 | 7 | 57 |
| query | test | legacy:all_terms_nonzero | legacy:signed_only | 0.00212 | -0.00419 | 0.00895 | 68 | 6 | 4 | 58 |
| query | test | legacy:all_terms_nonzero | legacy:r_e7_equivalent | -0.00313 | -0.00922 | 0.00002 | 68 | 1 | 3 | 64 |
| query | test | legacy:prior_signed_plus_intent | legacy:hybrid | -0.00194 | -0.01013 | 0.00596 | 68 | 4 | 7 | 57 |
| query | test | legacy:prior_signed_plus_intent | legacy:signed_only | 0.00214 | -0.00417 | 0.00897 | 68 | 6 | 3 | 59 |
| query | test | legacy:prior_signed_plus_intent | legacy:r_e7_equivalent | -0.00311 | -0.00922 | 0.00004 | 68 | 1 | 2 | 65 |
| query | test | legacy:fixed_all_005_intent_020 | legacy:hybrid | -0.00244 | -0.00771 | 0.00065 | 68 | 2 | 4 | 62 |
| query | test | legacy:fixed_all_005_intent_020 | legacy:signed_only | 0.00164 | -0.00065 | 0.00449 | 68 | 4 | 3 | 61 |
| query | test | legacy:fixed_all_005_intent_020 | legacy:r_e7_equivalent | -0.00362 | -0.01249 | 0.00372 | 68 | 4 | 4 | 60 |
| query | test | legacy:r_e7_equivalent | legacy:hybrid | 0.00117 | -0.00825 | 0.01105 | 68 | 5 | 6 | 57 |
| query | test | legacy:r_e7_equivalent | legacy:signed_only | 0.00525 | -0.00307 | 0.01593 | 68 | 6 | 2 | 60 |
| query | test | legacy:all_terms_minus_entity_bonus | legacy:hybrid | -0.00295 | -0.01169 | 0.00540 | 68 | 6 | 5 | 57 |
| query | test | legacy:all_terms_minus_entity_bonus | legacy:signed_only | 0.00113 | -0.00610 | 0.00874 | 68 | 7 | 4 | 57 |
| query | test | legacy:all_terms_minus_entity_bonus | legacy:r_e7_equivalent | -0.00412 | -0.01186 | 0.00161 | 68 | 3 | 5 | 60 |
| query | test | legacy:all_terms_minus_entity_penalty | legacy:hybrid | -0.00295 | -0.01169 | 0.00540 | 68 | 6 | 5 | 57 |
| query | test | legacy:all_terms_minus_entity_penalty | legacy:signed_only | 0.00113 | -0.00610 | 0.00874 | 68 | 7 | 4 | 57 |
| query | test | legacy:all_terms_minus_entity_penalty | legacy:r_e7_equivalent | -0.00412 | -0.01186 | 0.00161 | 68 | 3 | 5 | 60 |
| query | test | legacy:all_terms_minus_context_bonus | legacy:hybrid | -0.00217 | -0.01029 | 0.00569 | 68 | 4 | 7 | 57 |
| query | test | legacy:all_terms_minus_context_bonus | legacy:signed_only | 0.00191 | -0.00427 | 0.00876 | 68 | 6 | 4 | 58 |
| query | test | legacy:all_terms_minus_context_bonus | legacy:r_e7_equivalent | -0.00335 | -0.00961 | 0.00002 | 68 | 1 | 3 | 64 |
| query | test | legacy:all_terms_minus_context_penalty | legacy:hybrid | -0.00196 | -0.01014 | 0.00593 | 68 | 4 | 7 | 57 |
| query | test | legacy:all_terms_minus_context_penalty | legacy:signed_only | 0.00212 | -0.00419 | 0.00895 | 68 | 6 | 4 | 58 |
| query | test | legacy:all_terms_minus_context_penalty | legacy:r_e7_equivalent | -0.00313 | -0.00922 | 0.00002 | 68 | 1 | 3 | 64 |
| query | test | legacy:all_terms_minus_intent_bonus | legacy:hybrid | -0.00466 | -0.01152 | 0.00004 | 68 | 2 | 6 | 60 |
| query | test | legacy:all_terms_minus_intent_bonus | legacy:signed_only | -0.00058 | -0.00171 | 0.00000 | 68 | 0 | 2 | 66 |
| query | test | legacy:all_terms_minus_intent_bonus | legacy:r_e7_equivalent | -0.00583 | -0.01782 | 0.00305 | 68 | 2 | 7 | 59 |
| query | test | repaired:intent_only | repaired:hybrid | -0.00224 | -0.00751 | 0.00083 | 68 | 3 | 3 | 62 |
| query | test | repaired:intent_only | repaired:signed_only | 0.00240 | -0.00050 | 0.00651 | 68 | 5 | 2 | 61 |
| query | test | repaired:intent_only | repaired:r_e7_equivalent | 0.00461 | -0.00547 | 0.01737 | 68 | 7 | 4 | 57 |
| query | test | repaired:signed_only | repaired:hybrid | -0.00464 | -0.01152 | 0.00004 | 68 | 2 | 6 | 60 |
| query | test | repaired:signed_only | repaired:r_e7_equivalent | 0.00220 | -0.00594 | 0.01217 | 68 | 3 | 5 | 60 |
| query | test | repaired:signed_plus_intent | repaired:hybrid | -0.00196 | -0.01014 | 0.00593 | 68 | 4 | 7 | 57 |
| query | test | repaired:signed_plus_intent | repaired:signed_only | 0.00268 | -0.00378 | 0.00992 | 68 | 6 | 4 | 58 |
| query | test | repaired:signed_plus_intent | repaired:r_e7_equivalent | 0.00488 | -0.00052 | 0.01519 | 68 | 2 | 2 | 64 |
| query | test | repaired:all_terms_nonzero | repaired:hybrid | -0.00196 | -0.01014 | 0.00593 | 68 | 4 | 7 | 57 |
| query | test | repaired:all_terms_nonzero | repaired:signed_only | 0.00268 | -0.00378 | 0.00992 | 68 | 6 | 4 | 58 |
| query | test | repaired:all_terms_nonzero | repaired:r_e7_equivalent | 0.00488 | -0.00052 | 0.01519 | 68 | 2 | 2 | 64 |
| query | test | repaired:prior_signed_plus_intent | repaired:hybrid | -0.00194 | -0.01013 | 0.00596 | 68 | 4 | 7 | 57 |
| query | test | repaired:prior_signed_plus_intent | repaired:signed_only | 0.00270 | -0.00378 | 0.00993 | 68 | 6 | 3 | 59 |
| query | test | repaired:prior_signed_plus_intent | repaired:r_e7_equivalent | 0.00490 | -0.00050 | 0.01519 | 68 | 2 | 1 | 65 |
| query | test | repaired:fixed_all_005_intent_020 | repaired:hybrid | -0.00235 | -0.00762 | 0.00069 | 68 | 2 | 4 | 62 |
| query | test | repaired:fixed_all_005_intent_020 | repaired:signed_only | 0.00229 | -0.00049 | 0.00640 | 68 | 4 | 2 | 62 |
| query | test | repaired:fixed_all_005_intent_020 | repaired:r_e7_equivalent | 0.00449 | -0.00551 | 0.01711 | 68 | 5 | 3 | 60 |
| query | test | repaired:r_e7_equivalent | repaired:hybrid | -0.00684 | -0.02043 | 0.00418 | 68 | 4 | 7 | 57 |
| query | test | repaired:r_e7_equivalent | repaired:signed_only | -0.00220 | -0.01217 | 0.00594 | 68 | 5 | 3 | 60 |
| query | test | repaired:all_terms_minus_entity_bonus | repaired:hybrid | -0.00295 | -0.01169 | 0.00540 | 68 | 6 | 5 | 57 |
| query | test | repaired:all_terms_minus_entity_bonus | repaired:signed_only | 0.00169 | -0.00584 | 0.00993 | 68 | 7 | 4 | 57 |
| query | test | repaired:all_terms_minus_entity_bonus | repaired:r_e7_equivalent | 0.00389 | -0.00452 | 0.01575 | 68 | 4 | 4 | 60 |
| query | test | repaired:all_terms_minus_entity_penalty | repaired:hybrid | -0.00295 | -0.01169 | 0.00540 | 68 | 6 | 5 | 57 |
| query | test | repaired:all_terms_minus_entity_penalty | repaired:signed_only | 0.00169 | -0.00584 | 0.00993 | 68 | 7 | 4 | 57 |
| query | test | repaired:all_terms_minus_entity_penalty | repaired:r_e7_equivalent | 0.00389 | -0.00452 | 0.01575 | 68 | 4 | 4 | 60 |
| query | test | repaired:all_terms_minus_context_bonus | repaired:hybrid | -0.00217 | -0.01029 | 0.00569 | 68 | 4 | 7 | 57 |
| query | test | repaired:all_terms_minus_context_bonus | repaired:signed_only | 0.00246 | -0.00409 | 0.00977 | 68 | 6 | 4 | 58 |
| query | test | repaired:all_terms_minus_context_bonus | repaired:r_e7_equivalent | 0.00467 | -0.00089 | 0.01517 | 68 | 2 | 2 | 64 |
| query | test | repaired:all_terms_minus_context_penalty | repaired:hybrid | -0.00196 | -0.01014 | 0.00593 | 68 | 4 | 7 | 57 |
| query | test | repaired:all_terms_minus_context_penalty | repaired:signed_only | 0.00268 | -0.00378 | 0.00992 | 68 | 6 | 4 | 58 |
| query | test | repaired:all_terms_minus_context_penalty | repaired:r_e7_equivalent | 0.00488 | -0.00052 | 0.01519 | 68 | 2 | 2 | 64 |
| query | test | repaired:all_terms_minus_intent_bonus | repaired:hybrid | -0.00466 | -0.01152 | 0.00004 | 68 | 2 | 6 | 60 |
| query | test | repaired:all_terms_minus_intent_bonus | repaired:signed_only | -0.00002 | -0.00006 | 0.00000 | 68 | 0 | 1 | 67 |
| query | test | repaired:all_terms_minus_intent_bonus | repaired:r_e7_equivalent | 0.00218 | -0.00596 | 0.01217 | 68 | 3 | 6 | 59 |
| query_dedup | validation | legacy:intent_only | legacy:hybrid | -0.00190 | -0.00647 | 0.00078 | 69 | 1 | 1 | 67 |
| query_dedup | validation | legacy:intent_only | legacy:signed_only | -0.00039 | -0.00603 | 0.00422 | 69 | 3 | 1 | 65 |
| query_dedup | validation | legacy:intent_only | legacy:r_e7_equivalent | -0.00323 | -0.01173 | 0.00399 | 69 | 2 | 3 | 64 |
| query_dedup | validation | legacy:signed_only | legacy:hybrid | -0.00151 | -0.00808 | 0.00476 | 69 | 1 | 4 | 64 |
| query_dedup | validation | legacy:signed_only | legacy:r_e7_equivalent | -0.00285 | -0.01446 | 0.00756 | 69 | 2 | 5 | 62 |
| query_dedup | validation | legacy:signed_plus_intent | legacy:hybrid | -0.00237 | -0.00935 | 0.00337 | 69 | 2 | 3 | 64 |
| query_dedup | validation | legacy:signed_plus_intent | legacy:signed_only | -0.00086 | -0.00877 | 0.00573 | 69 | 4 | 2 | 63 |
| query_dedup | validation | legacy:signed_plus_intent | legacy:r_e7_equivalent | -0.00370 | -0.01172 | 0.00152 | 69 | 1 | 3 | 65 |
| query_dedup | validation | legacy:all_terms_nonzero | legacy:hybrid | -0.00237 | -0.00935 | 0.00337 | 69 | 2 | 3 | 64 |
| query_dedup | validation | legacy:all_terms_nonzero | legacy:signed_only | -0.00086 | -0.00877 | 0.00573 | 69 | 4 | 2 | 63 |
| query_dedup | validation | legacy:all_terms_nonzero | legacy:r_e7_equivalent | -0.00370 | -0.01172 | 0.00152 | 69 | 1 | 3 | 65 |
| query_dedup | validation | legacy:prior_signed_plus_intent | legacy:hybrid | -0.00237 | -0.00935 | 0.00337 | 69 | 2 | 3 | 64 |
| query_dedup | validation | legacy:prior_signed_plus_intent | legacy:signed_only | -0.00086 | -0.00877 | 0.00573 | 69 | 4 | 2 | 63 |
| query_dedup | validation | legacy:prior_signed_plus_intent | legacy:r_e7_equivalent | -0.00370 | -0.01172 | 0.00152 | 69 | 1 | 3 | 65 |
| query_dedup | validation | legacy:fixed_all_005_intent_020 | legacy:hybrid | -0.00049 | -0.00647 | 0.00501 | 69 | 1 | 1 | 67 |
| query_dedup | validation | legacy:fixed_all_005_intent_020 | legacy:signed_only | 0.00102 | -0.00564 | 0.00743 | 69 | 3 | 1 | 65 |
| query_dedup | validation | legacy:fixed_all_005_intent_020 | legacy:r_e7_equivalent | -0.00182 | -0.01054 | 0.00592 | 69 | 3 | 3 | 63 |
| query_dedup | validation | legacy:r_e7_equivalent | legacy:hybrid | 0.00134 | -0.00706 | 0.01073 | 69 | 4 | 3 | 62 |
| query_dedup | validation | legacy:r_e7_equivalent | legacy:signed_only | 0.00285 | -0.00756 | 0.01446 | 69 | 5 | 2 | 62 |
| query_dedup | validation | legacy:all_terms_minus_entity_bonus | legacy:hybrid | -0.00257 | -0.01014 | 0.00326 | 69 | 1 | 3 | 65 |
| query_dedup | validation | legacy:all_terms_minus_entity_bonus | legacy:signed_only | -0.00106 | -0.00883 | 0.00616 | 69 | 3 | 2 | 64 |
| query_dedup | validation | legacy:all_terms_minus_entity_bonus | legacy:r_e7_equivalent | -0.00390 | -0.01215 | 0.00233 | 69 | 2 | 3 | 64 |
| query_dedup | validation | legacy:all_terms_minus_entity_penalty | legacy:hybrid | -0.00257 | -0.01014 | 0.00326 | 69 | 1 | 3 | 65 |
| query_dedup | validation | legacy:all_terms_minus_entity_penalty | legacy:signed_only | -0.00106 | -0.00883 | 0.00616 | 69 | 3 | 2 | 64 |
| query_dedup | validation | legacy:all_terms_minus_entity_penalty | legacy:r_e7_equivalent | -0.00390 | -0.01215 | 0.00233 | 69 | 2 | 3 | 64 |
| query_dedup | validation | legacy:all_terms_minus_context_bonus | legacy:hybrid | -0.00104 | -0.00686 | 0.00366 | 69 | 2 | 3 | 64 |
| query_dedup | validation | legacy:all_terms_minus_context_bonus | legacy:signed_only | 0.00047 | -0.00611 | 0.00624 | 69 | 4 | 2 | 63 |
| query_dedup | validation | legacy:all_terms_minus_context_bonus | legacy:r_e7_equivalent | -0.00237 | -0.01049 | 0.00366 | 69 | 2 | 3 | 64 |
| query_dedup | validation | legacy:all_terms_minus_context_penalty | legacy:hybrid | -0.00237 | -0.00935 | 0.00337 | 69 | 2 | 3 | 64 |
| query_dedup | validation | legacy:all_terms_minus_context_penalty | legacy:signed_only | -0.00086 | -0.00877 | 0.00573 | 69 | 4 | 2 | 63 |
| query_dedup | validation | legacy:all_terms_minus_context_penalty | legacy:r_e7_equivalent | -0.00370 | -0.01172 | 0.00152 | 69 | 1 | 3 | 65 |
| query_dedup | validation | legacy:all_terms_minus_intent_bonus | legacy:hybrid | -0.00206 | -0.00906 | 0.00466 | 69 | 1 | 4 | 64 |
| query_dedup | validation | legacy:all_terms_minus_intent_bonus | legacy:signed_only | -0.00055 | -0.00164 | 0.00000 | 69 | 0 | 1 | 68 |
| query_dedup | validation | legacy:all_terms_minus_intent_bonus | legacy:r_e7_equivalent | -0.00339 | -0.01619 | 0.00731 | 69 | 2 | 5 | 62 |
| query_dedup | validation | repaired:intent_only | repaired:hybrid | -0.00190 | -0.00647 | 0.00078 | 69 | 1 | 1 | 67 |
| query_dedup | validation | repaired:intent_only | repaired:signed_only | 0.00016 | -0.00581 | 0.00586 | 69 | 3 | 1 | 65 |
| query_dedup | validation | repaired:intent_only | repaired:r_e7_equivalent | 0.00466 | -0.00415 | 0.01816 | 69 | 3 | 2 | 64 |
| query_dedup | validation | repaired:signed_only | repaired:hybrid | -0.00206 | -0.00906 | 0.00466 | 69 | 1 | 4 | 64 |
| query_dedup | validation | repaired:signed_only | repaired:r_e7_equivalent | 0.00450 | -0.00402 | 0.01568 | 69 | 3 | 4 | 62 |
| query_dedup | validation | repaired:signed_plus_intent | repaired:hybrid | -0.00237 | -0.00935 | 0.00337 | 69 | 2 | 3 | 64 |
| query_dedup | validation | repaired:signed_plus_intent | repaired:signed_only | -0.00031 | -0.00845 | 0.00685 | 69 | 4 | 2 | 63 |
| query_dedup | validation | repaired:signed_plus_intent | repaired:r_e7_equivalent | 0.00419 | -0.00313 | 0.01650 | 69 | 2 | 2 | 65 |
| query_dedup | validation | repaired:all_terms_nonzero | repaired:hybrid | -0.00237 | -0.00935 | 0.00337 | 69 | 2 | 3 | 64 |
| query_dedup | validation | repaired:all_terms_nonzero | repaired:signed_only | -0.00031 | -0.00845 | 0.00685 | 69 | 4 | 2 | 63 |
| query_dedup | validation | repaired:all_terms_nonzero | repaired:r_e7_equivalent | 0.00419 | -0.00313 | 0.01650 | 69 | 2 | 2 | 65 |
| query_dedup | validation | repaired:prior_signed_plus_intent | repaired:hybrid | -0.00237 | -0.00935 | 0.00337 | 69 | 2 | 3 | 64 |
| query_dedup | validation | repaired:prior_signed_plus_intent | repaired:signed_only | -0.00031 | -0.00845 | 0.00685 | 69 | 4 | 2 | 63 |
| query_dedup | validation | repaired:prior_signed_plus_intent | repaired:r_e7_equivalent | 0.00419 | -0.00313 | 0.01650 | 69 | 2 | 2 | 65 |
| query_dedup | validation | repaired:fixed_all_005_intent_020 | repaired:hybrid | -0.00049 | -0.00647 | 0.00501 | 69 | 1 | 1 | 67 |
| query_dedup | validation | repaired:fixed_all_005_intent_020 | repaired:signed_only | 0.00157 | -0.00509 | 0.00862 | 69 | 3 | 1 | 65 |
| query_dedup | validation | repaired:fixed_all_005_intent_020 | repaired:r_e7_equivalent | 0.00607 | -0.00327 | 0.01962 | 69 | 4 | 2 | 63 |
| query_dedup | validation | repaired:r_e7_equivalent | repaired:hybrid | -0.00656 | -0.02031 | 0.00333 | 69 | 3 | 4 | 62 |
| query_dedup | validation | repaired:r_e7_equivalent | repaired:signed_only | -0.00450 | -0.01568 | 0.00402 | 69 | 4 | 3 | 62 |
| query_dedup | validation | repaired:all_terms_minus_entity_bonus | repaired:hybrid | -0.00257 | -0.01014 | 0.00326 | 69 | 1 | 3 | 65 |
| query_dedup | validation | repaired:all_terms_minus_entity_bonus | repaired:signed_only | -0.00051 | -0.00869 | 0.00717 | 69 | 3 | 2 | 64 |
| query_dedup | validation | repaired:all_terms_minus_entity_bonus | repaired:r_e7_equivalent | 0.00399 | -0.00439 | 0.01691 | 69 | 3 | 2 | 64 |
| query_dedup | validation | repaired:all_terms_minus_entity_penalty | repaired:hybrid | -0.00257 | -0.01014 | 0.00326 | 69 | 1 | 3 | 65 |
| query_dedup | validation | repaired:all_terms_minus_entity_penalty | repaired:signed_only | -0.00051 | -0.00869 | 0.00717 | 69 | 3 | 2 | 64 |
| query_dedup | validation | repaired:all_terms_minus_entity_penalty | repaired:r_e7_equivalent | 0.00399 | -0.00439 | 0.01691 | 69 | 3 | 2 | 64 |
| query_dedup | validation | repaired:all_terms_minus_context_bonus | repaired:hybrid | -0.00104 | -0.00686 | 0.00366 | 69 | 2 | 3 | 64 |
| query_dedup | validation | repaired:all_terms_minus_context_bonus | repaired:signed_only | 0.00102 | -0.00591 | 0.00769 | 69 | 4 | 2 | 63 |
| query_dedup | validation | repaired:all_terms_minus_context_bonus | repaired:r_e7_equivalent | 0.00553 | -0.00307 | 0.01839 | 69 | 3 | 2 | 64 |
| query_dedup | validation | repaired:all_terms_minus_context_penalty | repaired:hybrid | -0.00237 | -0.00935 | 0.00337 | 69 | 2 | 3 | 64 |
| query_dedup | validation | repaired:all_terms_minus_context_penalty | repaired:signed_only | -0.00031 | -0.00845 | 0.00685 | 69 | 4 | 2 | 63 |
| query_dedup | validation | repaired:all_terms_minus_context_penalty | repaired:r_e7_equivalent | 0.00419 | -0.00313 | 0.01650 | 69 | 2 | 2 | 65 |
| query_dedup | validation | repaired:all_terms_minus_intent_bonus | repaired:hybrid | -0.00206 | -0.00906 | 0.00466 | 69 | 1 | 4 | 64 |
| query_dedup | validation | repaired:all_terms_minus_intent_bonus | repaired:signed_only | 0.00000 | 0.00000 | 0.00000 | 69 | 0 | 0 | 69 |
| query_dedup | validation | repaired:all_terms_minus_intent_bonus | repaired:r_e7_equivalent | 0.00450 | -0.00402 | 0.01568 | 69 | 3 | 4 | 62 |
| query_dedup | test | legacy:intent_only | legacy:hybrid | 0.00173 | -0.00100 | 0.00626 | 68 | 3 | 5 | 60 |
| query_dedup | test | legacy:intent_only | legacy:signed_only | -0.00197 | -0.01047 | 0.00522 | 68 | 4 | 6 | 58 |
| query_dedup | test | legacy:intent_only | legacy:r_e7_equivalent | -0.00001 | -0.00591 | 0.00613 | 68 | 6 | 6 | 56 |
| query_dedup | test | legacy:signed_only | legacy:hybrid | 0.00369 | -0.00111 | 0.01145 | 68 | 5 | 4 | 59 |
| query_dedup | test | legacy:signed_only | legacy:r_e7_equivalent | 0.00196 | -0.00712 | 0.01217 | 68 | 5 | 6 | 57 |
| query_dedup | test | legacy:signed_plus_intent | legacy:hybrid | 0.00044 | -0.00621 | 0.00740 | 68 | 4 | 7 | 57 |
| query_dedup | test | legacy:signed_plus_intent | legacy:signed_only | -0.00325 | -0.01282 | 0.00491 | 68 | 4 | 7 | 57 |
| query_dedup | test | legacy:signed_plus_intent | legacy:r_e7_equivalent | -0.00129 | -0.00416 | 0.00144 | 68 | 1 | 6 | 61 |
| query_dedup | test | legacy:all_terms_nonzero | legacy:hybrid | 0.00044 | -0.00621 | 0.00740 | 68 | 4 | 7 | 57 |
| query_dedup | test | legacy:all_terms_nonzero | legacy:signed_only | -0.00325 | -0.01282 | 0.00491 | 68 | 4 | 7 | 57 |
| query_dedup | test | legacy:all_terms_nonzero | legacy:r_e7_equivalent | -0.00129 | -0.00416 | 0.00144 | 68 | 1 | 6 | 61 |
| query_dedup | test | legacy:prior_signed_plus_intent | legacy:hybrid | 0.00126 | -0.00557 | 0.00825 | 68 | 5 | 7 | 56 |
| query_dedup | test | legacy:prior_signed_plus_intent | legacy:signed_only | -0.00243 | -0.01223 | 0.00585 | 68 | 5 | 6 | 57 |
| query_dedup | test | legacy:prior_signed_plus_intent | legacy:r_e7_equivalent | -0.00047 | -0.00309 | 0.00199 | 68 | 1 | 4 | 63 |
| query_dedup | test | legacy:fixed_all_005_intent_020 | legacy:hybrid | 0.00246 | -0.00090 | 0.00748 | 68 | 4 | 5 | 59 |
| query_dedup | test | legacy:fixed_all_005_intent_020 | legacy:signed_only | -0.00123 | -0.00983 | 0.00630 | 68 | 4 | 7 | 57 |
| query_dedup | test | legacy:fixed_all_005_intent_020 | legacy:r_e7_equivalent | 0.00072 | -0.00494 | 0.00652 | 68 | 5 | 4 | 59 |
| query_dedup | test | legacy:r_e7_equivalent | legacy:hybrid | 0.00174 | -0.00565 | 0.00927 | 68 | 6 | 6 | 56 |
| query_dedup | test | legacy:r_e7_equivalent | legacy:signed_only | -0.00196 | -0.01217 | 0.00712 | 68 | 6 | 5 | 57 |
| query_dedup | test | legacy:all_terms_minus_entity_bonus | legacy:hybrid | -0.00052 | -0.00766 | 0.00674 | 68 | 6 | 6 | 56 |
| query_dedup | test | legacy:all_terms_minus_entity_bonus | legacy:signed_only | -0.00422 | -0.01453 | 0.00483 | 68 | 5 | 7 | 56 |
| query_dedup | test | legacy:all_terms_minus_entity_bonus | legacy:r_e7_equivalent | -0.00226 | -0.00721 | 0.00184 | 68 | 2 | 6 | 60 |
| query_dedup | test | legacy:all_terms_minus_entity_penalty | legacy:hybrid | -0.00052 | -0.00766 | 0.00674 | 68 | 6 | 6 | 56 |
| query_dedup | test | legacy:all_terms_minus_entity_penalty | legacy:signed_only | -0.00422 | -0.01453 | 0.00483 | 68 | 5 | 7 | 56 |
| query_dedup | test | legacy:all_terms_minus_entity_penalty | legacy:r_e7_equivalent | -0.00226 | -0.00721 | 0.00184 | 68 | 2 | 6 | 60 |
| query_dedup | test | legacy:all_terms_minus_context_bonus | legacy:hybrid | 0.00023 | -0.00640 | 0.00719 | 68 | 4 | 7 | 57 |
| query_dedup | test | legacy:all_terms_minus_context_bonus | legacy:signed_only | -0.00347 | -0.01321 | 0.00470 | 68 | 4 | 7 | 57 |
| query_dedup | test | legacy:all_terms_minus_context_bonus | legacy:r_e7_equivalent | -0.00151 | -0.00440 | 0.00137 | 68 | 1 | 6 | 61 |
| query_dedup | test | legacy:all_terms_minus_context_penalty | legacy:hybrid | 0.00044 | -0.00621 | 0.00740 | 68 | 4 | 7 | 57 |
| query_dedup | test | legacy:all_terms_minus_context_penalty | legacy:signed_only | -0.00325 | -0.01282 | 0.00491 | 68 | 4 | 7 | 57 |
| query_dedup | test | legacy:all_terms_minus_context_penalty | legacy:r_e7_equivalent | -0.00129 | -0.00416 | 0.00144 | 68 | 1 | 6 | 61 |
| query_dedup | test | legacy:all_terms_minus_intent_bonus | legacy:hybrid | 0.00367 | -0.00114 | 0.01145 | 68 | 5 | 4 | 59 |
| query_dedup | test | legacy:all_terms_minus_intent_bonus | legacy:signed_only | -0.00002 | -0.00006 | 0.00000 | 68 | 0 | 1 | 67 |
| query_dedup | test | legacy:all_terms_minus_intent_bonus | legacy:r_e7_equivalent | 0.00194 | -0.00716 | 0.01217 | 68 | 5 | 7 | 56 |
| query_dedup | test | repaired:intent_only | repaired:hybrid | 0.00173 | -0.00100 | 0.00626 | 68 | 3 | 5 | 60 |
| query_dedup | test | repaired:intent_only | repaired:signed_only | -0.00197 | -0.01047 | 0.00522 | 68 | 4 | 6 | 58 |
| query_dedup | test | repaired:intent_only | repaired:r_e7_equivalent | 0.00175 | -0.00366 | 0.00759 | 68 | 6 | 4 | 58 |
| query_dedup | test | repaired:signed_only | repaired:hybrid | 0.00369 | -0.00111 | 0.01145 | 68 | 5 | 4 | 59 |
| query_dedup | test | repaired:signed_only | repaired:r_e7_equivalent | 0.00372 | -0.00495 | 0.01371 | 68 | 5 | 4 | 59 |
| query_dedup | test | repaired:signed_plus_intent | repaired:hybrid | 0.00044 | -0.00621 | 0.00740 | 68 | 4 | 7 | 57 |
| query_dedup | test | repaired:signed_plus_intent | repaired:signed_only | -0.00325 | -0.01282 | 0.00491 | 68 | 4 | 7 | 57 |
| query_dedup | test | repaired:signed_plus_intent | repaired:r_e7_equivalent | 0.00047 | -0.00062 | 0.00231 | 68 | 1 | 4 | 63 |
| query_dedup | test | repaired:all_terms_nonzero | repaired:hybrid | 0.00044 | -0.00621 | 0.00740 | 68 | 4 | 7 | 57 |
| query_dedup | test | repaired:all_terms_nonzero | repaired:signed_only | -0.00325 | -0.01282 | 0.00491 | 68 | 4 | 7 | 57 |
| query_dedup | test | repaired:all_terms_nonzero | repaired:r_e7_equivalent | 0.00047 | -0.00062 | 0.00231 | 68 | 1 | 4 | 63 |
| query_dedup | test | repaired:prior_signed_plus_intent | repaired:hybrid | 0.00043 | -0.00627 | 0.00739 | 68 | 4 | 7 | 57 |
| query_dedup | test | repaired:prior_signed_plus_intent | repaired:signed_only | -0.00327 | -0.01283 | 0.00488 | 68 | 4 | 6 | 58 |
| query_dedup | test | repaired:prior_signed_plus_intent | repaired:r_e7_equivalent | 0.00045 | -0.00060 | 0.00224 | 68 | 1 | 3 | 64 |
| query_dedup | test | repaired:fixed_all_005_intent_020 | repaired:hybrid | 0.00168 | -0.00107 | 0.00620 | 68 | 3 | 5 | 60 |
| query_dedup | test | repaired:fixed_all_005_intent_020 | repaired:signed_only | -0.00201 | -0.01053 | 0.00510 | 68 | 3 | 6 | 59 |
| query_dedup | test | repaired:fixed_all_005_intent_020 | repaired:r_e7_equivalent | 0.00171 | -0.00353 | 0.00734 | 68 | 4 | 3 | 61 |
| query_dedup | test | repaired:r_e7_equivalent | repaired:hybrid | -0.00002 | -0.00721 | 0.00716 | 68 | 4 | 6 | 58 |
| query_dedup | test | repaired:r_e7_equivalent | repaired:signed_only | -0.00372 | -0.01371 | 0.00495 | 68 | 4 | 5 | 59 |
| query_dedup | test | repaired:all_terms_minus_entity_bonus | repaired:hybrid | -0.00136 | -0.00842 | 0.00584 | 68 | 5 | 6 | 57 |
| query_dedup | test | repaired:all_terms_minus_entity_bonus | repaired:signed_only | -0.00505 | -0.01540 | 0.00371 | 68 | 4 | 7 | 57 |
| query_dedup | test | repaired:all_terms_minus_entity_bonus | repaired:r_e7_equivalent | -0.00134 | -0.00597 | 0.00235 | 68 | 2 | 5 | 61 |
| query_dedup | test | repaired:all_terms_minus_entity_penalty | repaired:hybrid | -0.00136 | -0.00842 | 0.00584 | 68 | 5 | 6 | 57 |
| query_dedup | test | repaired:all_terms_minus_entity_penalty | repaired:signed_only | -0.00505 | -0.01540 | 0.00371 | 68 | 4 | 7 | 57 |
| query_dedup | test | repaired:all_terms_minus_entity_penalty | repaired:r_e7_equivalent | -0.00134 | -0.00597 | 0.00235 | 68 | 2 | 5 | 61 |
| query_dedup | test | repaired:all_terms_minus_context_bonus | repaired:hybrid | 0.00023 | -0.00640 | 0.00719 | 68 | 4 | 7 | 57 |
| query_dedup | test | repaired:all_terms_minus_context_bonus | repaired:signed_only | -0.00347 | -0.01321 | 0.00470 | 68 | 4 | 7 | 57 |
| query_dedup | test | repaired:all_terms_minus_context_bonus | repaired:r_e7_equivalent | 0.00025 | -0.00104 | 0.00227 | 68 | 1 | 4 | 63 |
| query_dedup | test | repaired:all_terms_minus_context_penalty | repaired:hybrid | 0.00044 | -0.00621 | 0.00740 | 68 | 4 | 7 | 57 |
| query_dedup | test | repaired:all_terms_minus_context_penalty | repaired:signed_only | -0.00325 | -0.01282 | 0.00491 | 68 | 4 | 7 | 57 |
| query_dedup | test | repaired:all_terms_minus_context_penalty | repaired:r_e7_equivalent | 0.00047 | -0.00062 | 0.00231 | 68 | 1 | 4 | 63 |
| query_dedup | test | repaired:all_terms_minus_intent_bonus | repaired:hybrid | 0.00367 | -0.00114 | 0.01145 | 68 | 5 | 4 | 59 |
| query_dedup | test | repaired:all_terms_minus_intent_bonus | repaired:signed_only | -0.00002 | -0.00006 | 0.00000 | 68 | 0 | 1 | 67 |
| query_dedup | test | repaired:all_terms_minus_intent_bonus | repaired:r_e7_equivalent | 0.00370 | -0.00496 | 0.01370 | 68 | 5 | 5 | 58 |

## Value-aware configurations

| experiment | entity_bonus | entity_penalty | context_bonus | context_penalty | intent_bonus |
| --- | --- | --- | --- | --- | --- |
| requested_exact:hybrid | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| requested_exact:selected_signed_intent | 0.20000 | 0.20000 | 0.05000 | 0.00000 | 0.50000 |
| requested_exact:selected_all_terms | 0.20000 | 0.20000 | 0.05000 | 0.05000 | 0.50000 |
| requested_exact:frozen_all_terms | 0.20000 | 0.20000 | 0.05000 | 0.05000 | 0.50000 |
| requested_exact:r_e7_style | 0.50000 | 0.00000 | 0.50000 | 0.00000 | 0.50000 |
| symmetric_exact:hybrid | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| symmetric_exact:selected_signed_intent | 0.20000 | 0.20000 | 0.05000 | 0.00000 | 0.50000 |
| symmetric_exact:selected_all_terms | 0.20000 | 0.20000 | 0.05000 | 0.05000 | 0.50000 |
| symmetric_exact:frozen_all_terms | 0.20000 | 0.20000 | 0.05000 | 0.05000 | 0.50000 |
| symmetric_exact:r_e7_style | 0.50000 | 0.00000 | 0.50000 | 0.00000 | 0.50000 |
| current:frozen_all_terms | 0.20000 | 0.20000 | 0.05000 | 0.05000 | 0.50000 |
| current:r_e7_equivalent | 0.50000 | 0.00000 | 0.50000 | 0.00000 | 0.50000 |

## Value-aware paired comparisons

| protocol | split | candidate | reference | delta_ndcg | lower | upper | positive_queries | improved | worsened | unchanged |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| temporal | validation | requested_exact:hybrid | baseline:hybrid | 0.00000 | 0.00000 | 0.00000 | 113 | 0 | 0 | 113 |
| temporal | validation | requested_exact:hybrid | baseline:r_e7 | -0.00601 | -0.02340 | 0.00739 | 113 | 7 | 6 | 100 |
| temporal | validation | requested_exact:hybrid | current:frozen_all_terms | -0.00595 | -0.02360 | 0.00719 | 113 | 7 | 7 | 99 |
| temporal | validation | requested_exact:hybrid | current:r_e7_equivalent | -0.00601 | -0.02340 | 0.00739 | 113 | 7 | 6 | 100 |
| temporal | validation | requested_exact:selected_signed_intent | baseline:hybrid | 0.00570 | -0.00743 | 0.02334 | 113 | 7 | 7 | 99 |
| temporal | validation | requested_exact:selected_signed_intent | baseline:r_e7 | -0.00032 | -0.00161 | 0.00123 | 113 | 1 | 3 | 109 |
| temporal | validation | requested_exact:selected_signed_intent | current:frozen_all_terms | -0.00026 | -0.00077 | 0.00000 | 113 | 0 | 1 | 112 |
| temporal | validation | requested_exact:selected_signed_intent | current:r_e7_equivalent | -0.00032 | -0.00161 | 0.00123 | 113 | 1 | 3 | 109 |
| temporal | validation | requested_exact:selected_all_terms | baseline:hybrid | 0.00570 | -0.00743 | 0.02334 | 113 | 7 | 7 | 99 |
| temporal | validation | requested_exact:selected_all_terms | baseline:r_e7 | -0.00032 | -0.00161 | 0.00123 | 113 | 1 | 3 | 109 |
| temporal | validation | requested_exact:selected_all_terms | current:frozen_all_terms | -0.00026 | -0.00077 | 0.00000 | 113 | 0 | 1 | 112 |
| temporal | validation | requested_exact:selected_all_terms | current:r_e7_equivalent | -0.00032 | -0.00161 | 0.00123 | 113 | 1 | 3 | 109 |
| temporal | validation | requested_exact:frozen_all_terms | baseline:hybrid | 0.00570 | -0.00743 | 0.02334 | 113 | 7 | 7 | 99 |
| temporal | validation | requested_exact:frozen_all_terms | baseline:r_e7 | -0.00032 | -0.00161 | 0.00123 | 113 | 1 | 3 | 109 |
| temporal | validation | requested_exact:frozen_all_terms | current:frozen_all_terms | -0.00026 | -0.00077 | 0.00000 | 113 | 0 | 1 | 112 |
| temporal | validation | requested_exact:frozen_all_terms | current:r_e7_equivalent | -0.00032 | -0.00161 | 0.00123 | 113 | 1 | 3 | 109 |
| temporal | validation | requested_exact:r_e7_style | baseline:hybrid | 0.00599 | -0.00742 | 0.02337 | 113 | 6 | 7 | 100 |
| temporal | validation | requested_exact:r_e7_style | baseline:r_e7 | -0.00003 | -0.00008 | 0.00000 | 113 | 0 | 1 | 112 |
| temporal | validation | requested_exact:r_e7_style | current:frozen_all_terms | 0.00003 | -0.00146 | 0.00109 | 113 | 2 | 1 | 110 |
| temporal | validation | requested_exact:r_e7_style | current:r_e7_equivalent | -0.00003 | -0.00008 | 0.00000 | 113 | 0 | 1 | 112 |
| temporal | validation | symmetric_exact:hybrid | baseline:hybrid | 0.00000 | 0.00000 | 0.00000 | 113 | 0 | 0 | 113 |
| temporal | validation | symmetric_exact:hybrid | baseline:r_e7 | -0.00601 | -0.02340 | 0.00739 | 113 | 7 | 6 | 100 |
| temporal | validation | symmetric_exact:hybrid | current:frozen_all_terms | -0.00595 | -0.02360 | 0.00719 | 113 | 7 | 7 | 99 |
| temporal | validation | symmetric_exact:hybrid | current:r_e7_equivalent | -0.00601 | -0.02340 | 0.00739 | 113 | 7 | 6 | 100 |
| temporal | validation | symmetric_exact:selected_signed_intent | baseline:hybrid | 0.00454 | -0.00824 | 0.02238 | 113 | 7 | 7 | 99 |
| temporal | validation | symmetric_exact:selected_signed_intent | baseline:r_e7 | -0.00147 | -0.00372 | 0.00055 | 113 | 1 | 5 | 107 |
| temporal | validation | symmetric_exact:selected_signed_intent | current:frozen_all_terms | -0.00141 | -0.00344 | 0.00000 | 113 | 0 | 3 | 110 |
| temporal | validation | symmetric_exact:selected_signed_intent | current:r_e7_equivalent | -0.00147 | -0.00372 | 0.00055 | 113 | 1 | 5 | 107 |
| temporal | validation | symmetric_exact:selected_all_terms | baseline:hybrid | 0.00454 | -0.00824 | 0.02238 | 113 | 7 | 7 | 99 |
| temporal | validation | symmetric_exact:selected_all_terms | baseline:r_e7 | -0.00147 | -0.00372 | 0.00055 | 113 | 1 | 5 | 107 |
| temporal | validation | symmetric_exact:selected_all_terms | current:frozen_all_terms | -0.00141 | -0.00344 | 0.00000 | 113 | 0 | 3 | 110 |
| temporal | validation | symmetric_exact:selected_all_terms | current:r_e7_equivalent | -0.00147 | -0.00372 | 0.00055 | 113 | 1 | 5 | 107 |
| temporal | validation | symmetric_exact:frozen_all_terms | baseline:hybrid | 0.00454 | -0.00824 | 0.02238 | 113 | 7 | 7 | 99 |
| temporal | validation | symmetric_exact:frozen_all_terms | baseline:r_e7 | -0.00147 | -0.00372 | 0.00055 | 113 | 1 | 5 | 107 |
| temporal | validation | symmetric_exact:frozen_all_terms | current:frozen_all_terms | -0.00141 | -0.00344 | 0.00000 | 113 | 0 | 3 | 110 |
| temporal | validation | symmetric_exact:frozen_all_terms | current:r_e7_equivalent | -0.00147 | -0.00372 | 0.00055 | 113 | 1 | 5 | 107 |
| temporal | validation | symmetric_exact:r_e7_style | baseline:hybrid | 0.00483 | -0.00815 | 0.02224 | 113 | 6 | 7 | 100 |
| temporal | validation | symmetric_exact:r_e7_style | baseline:r_e7 | -0.00118 | -0.00300 | 0.00000 | 113 | 0 | 3 | 110 |
| temporal | validation | symmetric_exact:r_e7_style | current:frozen_all_terms | -0.00112 | -0.00347 | 0.00073 | 113 | 2 | 3 | 108 |
| temporal | validation | symmetric_exact:r_e7_style | current:r_e7_equivalent | -0.00118 | -0.00300 | 0.00000 | 113 | 0 | 3 | 110 |
| temporal | validation | ablation:requested_current_context | baseline:hybrid | 0.00570 | -0.00743 | 0.02334 | 113 | 7 | 7 | 99 |
| temporal | validation | ablation:requested_current_context | baseline:r_e7 | -0.00032 | -0.00161 | 0.00123 | 113 | 1 | 3 | 109 |
| temporal | validation | ablation:requested_current_context | current:frozen_all_terms | -0.00026 | -0.00077 | 0.00000 | 113 | 0 | 1 | 112 |
| temporal | validation | ablation:requested_current_context | current:r_e7_equivalent | -0.00032 | -0.00161 | 0.00123 | 113 | 1 | 3 | 109 |
| temporal | validation | ablation:symmetric_current_context | baseline:hybrid | 0.00454 | -0.00824 | 0.02238 | 113 | 7 | 7 | 99 |
| temporal | validation | ablation:symmetric_current_context | baseline:r_e7 | -0.00147 | -0.00372 | 0.00055 | 113 | 1 | 5 | 107 |
| temporal | validation | ablation:symmetric_current_context | current:frozen_all_terms | -0.00141 | -0.00344 | 0.00000 | 113 | 0 | 3 | 110 |
| temporal | validation | ablation:symmetric_current_context | current:r_e7_equivalent | -0.00147 | -0.00372 | 0.00055 | 113 | 1 | 5 | 107 |
| temporal | validation | ablation:dimension_exact_context | baseline:hybrid | 0.00595 | -0.00719 | 0.02360 | 113 | 7 | 7 | 99 |
| temporal | validation | ablation:dimension_exact_context | baseline:r_e7 | -0.00006 | -0.00113 | 0.00144 | 113 | 1 | 3 | 109 |
| temporal | validation | ablation:dimension_exact_context | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 113 | 0 | 0 | 113 |
| temporal | validation | ablation:dimension_exact_context | current:r_e7_equivalent | -0.00006 | -0.00113 | 0.00144 | 113 | 1 | 3 | 109 |
| temporal | test | requested_exact:hybrid | baseline:hybrid | 0.00000 | 0.00000 | 0.00000 | 110 | 0 | 0 | 110 |
| temporal | test | requested_exact:hybrid | baseline:r_e7 | -0.00289 | -0.01048 | 0.00327 | 110 | 5 | 6 | 99 |
| temporal | test | requested_exact:hybrid | current:frozen_all_terms | -0.00119 | -0.00536 | 0.00301 | 110 | 4 | 6 | 100 |
| temporal | test | requested_exact:hybrid | current:r_e7_equivalent | -0.00026 | -0.00441 | 0.00408 | 110 | 5 | 5 | 100 |
| temporal | test | requested_exact:selected_signed_intent | baseline:hybrid | 0.00119 | -0.00301 | 0.00536 | 110 | 6 | 4 | 100 |
| temporal | test | requested_exact:selected_signed_intent | baseline:r_e7 | -0.00170 | -0.00865 | 0.00181 | 110 | 4 | 1 | 105 |
| temporal | test | requested_exact:selected_signed_intent | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 110 | 0 | 0 | 110 |
| temporal | test | requested_exact:selected_signed_intent | current:r_e7_equivalent | 0.00092 | 0.00006 | 0.00219 | 110 | 4 | 0 | 106 |
| temporal | test | requested_exact:selected_all_terms | baseline:hybrid | 0.00119 | -0.00301 | 0.00536 | 110 | 6 | 4 | 100 |
| temporal | test | requested_exact:selected_all_terms | baseline:r_e7 | -0.00170 | -0.00865 | 0.00181 | 110 | 4 | 1 | 105 |
| temporal | test | requested_exact:selected_all_terms | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 110 | 0 | 0 | 110 |
| temporal | test | requested_exact:selected_all_terms | current:r_e7_equivalent | 0.00092 | 0.00006 | 0.00219 | 110 | 4 | 0 | 106 |
| temporal | test | requested_exact:frozen_all_terms | baseline:hybrid | 0.00119 | -0.00301 | 0.00536 | 110 | 6 | 4 | 100 |
| temporal | test | requested_exact:frozen_all_terms | baseline:r_e7 | -0.00170 | -0.00865 | 0.00181 | 110 | 4 | 1 | 105 |
| temporal | test | requested_exact:frozen_all_terms | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 110 | 0 | 0 | 110 |
| temporal | test | requested_exact:frozen_all_terms | current:r_e7_equivalent | 0.00092 | 0.00006 | 0.00219 | 110 | 4 | 0 | 106 |
| temporal | test | requested_exact:r_e7_style | baseline:hybrid | 0.00026 | -0.00408 | 0.00441 | 110 | 5 | 5 | 100 |
| temporal | test | requested_exact:r_e7_style | baseline:r_e7 | -0.00263 | -0.01051 | 0.00000 | 110 | 0 | 1 | 109 |
| temporal | test | requested_exact:r_e7_style | current:frozen_all_terms | -0.00092 | -0.00219 | -0.00006 | 110 | 0 | 4 | 106 |
| temporal | test | requested_exact:r_e7_style | current:r_e7_equivalent | 0.00000 | 0.00000 | 0.00000 | 110 | 0 | 0 | 110 |
| temporal | test | symmetric_exact:hybrid | baseline:hybrid | 0.00000 | 0.00000 | 0.00000 | 110 | 0 | 0 | 110 |
| temporal | test | symmetric_exact:hybrid | baseline:r_e7 | -0.00289 | -0.01048 | 0.00327 | 110 | 5 | 6 | 99 |
| temporal | test | symmetric_exact:hybrid | current:frozen_all_terms | -0.00119 | -0.00536 | 0.00301 | 110 | 4 | 6 | 100 |
| temporal | test | symmetric_exact:hybrid | current:r_e7_equivalent | -0.00026 | -0.00441 | 0.00408 | 110 | 5 | 5 | 100 |
| temporal | test | symmetric_exact:selected_signed_intent | baseline:hybrid | 0.00249 | -0.00161 | 0.00671 | 110 | 6 | 2 | 102 |
| temporal | test | symmetric_exact:selected_signed_intent | baseline:r_e7 | -0.00040 | -0.00769 | 0.00466 | 110 | 5 | 2 | 103 |
| temporal | test | symmetric_exact:selected_signed_intent | current:frozen_all_terms | 0.00130 | 0.00002 | 0.00338 | 110 | 4 | 1 | 105 |
| temporal | test | symmetric_exact:selected_signed_intent | current:r_e7_equivalent | 0.00223 | 0.00006 | 0.00546 | 110 | 5 | 1 | 104 |
| temporal | test | symmetric_exact:selected_all_terms | baseline:hybrid | 0.00249 | -0.00161 | 0.00671 | 110 | 6 | 2 | 102 |
| temporal | test | symmetric_exact:selected_all_terms | baseline:r_e7 | -0.00040 | -0.00769 | 0.00466 | 110 | 5 | 2 | 103 |
| temporal | test | symmetric_exact:selected_all_terms | current:frozen_all_terms | 0.00130 | 0.00002 | 0.00338 | 110 | 4 | 1 | 105 |
| temporal | test | symmetric_exact:selected_all_terms | current:r_e7_equivalent | 0.00223 | 0.00006 | 0.00546 | 110 | 5 | 1 | 104 |
| temporal | test | symmetric_exact:frozen_all_terms | baseline:hybrid | 0.00249 | -0.00161 | 0.00671 | 110 | 6 | 2 | 102 |
| temporal | test | symmetric_exact:frozen_all_terms | baseline:r_e7 | -0.00040 | -0.00769 | 0.00466 | 110 | 5 | 2 | 103 |
| temporal | test | symmetric_exact:frozen_all_terms | current:frozen_all_terms | 0.00130 | 0.00002 | 0.00338 | 110 | 4 | 1 | 105 |
| temporal | test | symmetric_exact:frozen_all_terms | current:r_e7_equivalent | 0.00223 | 0.00006 | 0.00546 | 110 | 5 | 1 | 104 |
| temporal | test | symmetric_exact:r_e7_style | baseline:hybrid | 0.00077 | -0.00341 | 0.00479 | 110 | 5 | 5 | 100 |
| temporal | test | symmetric_exact:r_e7_style | baseline:r_e7 | -0.00212 | -0.00922 | 0.00110 | 110 | 2 | 1 | 107 |
| temporal | test | symmetric_exact:r_e7_style | current:frozen_all_terms | -0.00042 | -0.00111 | 0.00000 | 110 | 0 | 3 | 107 |
| temporal | test | symmetric_exact:r_e7_style | current:r_e7_equivalent | 0.00050 | 0.00000 | 0.00130 | 110 | 2 | 0 | 108 |
| temporal | test | ablation:requested_current_context | baseline:hybrid | 0.00119 | -0.00301 | 0.00536 | 110 | 6 | 4 | 100 |
| temporal | test | ablation:requested_current_context | baseline:r_e7 | -0.00170 | -0.00865 | 0.00181 | 110 | 4 | 1 | 105 |
| temporal | test | ablation:requested_current_context | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 110 | 0 | 0 | 110 |
| temporal | test | ablation:requested_current_context | current:r_e7_equivalent | 0.00092 | 0.00006 | 0.00219 | 110 | 4 | 0 | 106 |
| temporal | test | ablation:symmetric_current_context | baseline:hybrid | 0.00249 | -0.00161 | 0.00671 | 110 | 6 | 2 | 102 |
| temporal | test | ablation:symmetric_current_context | baseline:r_e7 | -0.00040 | -0.00769 | 0.00466 | 110 | 5 | 2 | 103 |
| temporal | test | ablation:symmetric_current_context | current:frozen_all_terms | 0.00130 | 0.00002 | 0.00338 | 110 | 4 | 1 | 105 |
| temporal | test | ablation:symmetric_current_context | current:r_e7_equivalent | 0.00223 | 0.00006 | 0.00546 | 110 | 5 | 1 | 104 |
| temporal | test | ablation:dimension_exact_context | baseline:hybrid | 0.00119 | -0.00301 | 0.00536 | 110 | 6 | 4 | 100 |
| temporal | test | ablation:dimension_exact_context | baseline:r_e7 | -0.00170 | -0.00865 | 0.00181 | 110 | 4 | 1 | 105 |
| temporal | test | ablation:dimension_exact_context | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 110 | 0 | 0 | 110 |
| temporal | test | ablation:dimension_exact_context | current:r_e7_equivalent | 0.00092 | 0.00006 | 0.00219 | 110 | 4 | 0 | 106 |
| query | validation | requested_exact:hybrid | baseline:hybrid | 0.00000 | 0.00000 | 0.00000 | 70 | 0 | 0 | 70 |
| query | validation | requested_exact:hybrid | baseline:r_e7 | 0.00530 | -0.00354 | 0.01559 | 70 | 6 | 4 | 60 |
| query | validation | requested_exact:hybrid | current:frozen_all_terms | 0.00479 | -0.00245 | 0.01295 | 70 | 6 | 2 | 62 |
| query | validation | requested_exact:hybrid | current:r_e7_equivalent | 0.00530 | -0.00354 | 0.01559 | 70 | 6 | 4 | 60 |
| query | validation | requested_exact:selected_signed_intent | baseline:hybrid | -0.00521 | -0.01332 | 0.00172 | 70 | 2 | 6 | 62 |
| query | validation | requested_exact:selected_signed_intent | baseline:r_e7 | 0.00009 | -0.00447 | 0.00467 | 70 | 3 | 4 | 63 |
| query | validation | requested_exact:selected_signed_intent | current:frozen_all_terms | -0.00042 | -0.00125 | 0.00000 | 70 | 0 | 1 | 69 |
| query | validation | requested_exact:selected_signed_intent | current:r_e7_equivalent | 0.00009 | -0.00447 | 0.00467 | 70 | 3 | 4 | 63 |
| query | validation | requested_exact:selected_all_terms | baseline:hybrid | -0.00521 | -0.01332 | 0.00172 | 70 | 2 | 6 | 62 |
| query | validation | requested_exact:selected_all_terms | baseline:r_e7 | 0.00009 | -0.00447 | 0.00467 | 70 | 3 | 4 | 63 |
| query | validation | requested_exact:selected_all_terms | current:frozen_all_terms | -0.00042 | -0.00125 | 0.00000 | 70 | 0 | 1 | 69 |
| query | validation | requested_exact:selected_all_terms | current:r_e7_equivalent | 0.00009 | -0.00447 | 0.00467 | 70 | 3 | 4 | 63 |
| query | validation | requested_exact:frozen_all_terms | baseline:hybrid | -0.00521 | -0.01332 | 0.00172 | 70 | 2 | 6 | 62 |
| query | validation | requested_exact:frozen_all_terms | baseline:r_e7 | 0.00009 | -0.00447 | 0.00467 | 70 | 3 | 4 | 63 |
| query | validation | requested_exact:frozen_all_terms | current:frozen_all_terms | -0.00042 | -0.00125 | 0.00000 | 70 | 0 | 1 | 69 |
| query | validation | requested_exact:frozen_all_terms | current:r_e7_equivalent | 0.00009 | -0.00447 | 0.00467 | 70 | 3 | 4 | 63 |
| query | validation | requested_exact:r_e7_style | baseline:hybrid | -0.00535 | -0.01563 | 0.00344 | 70 | 4 | 6 | 60 |
| query | validation | requested_exact:r_e7_style | baseline:r_e7 | -0.00004 | -0.00013 | 0.00000 | 70 | 0 | 1 | 69 |
| query | validation | requested_exact:r_e7_style | current:frozen_all_terms | -0.00055 | -0.00485 | 0.00381 | 70 | 3 | 3 | 64 |
| query | validation | requested_exact:r_e7_style | current:r_e7_equivalent | -0.00004 | -0.00013 | 0.00000 | 70 | 0 | 1 | 69 |
| query | validation | symmetric_exact:hybrid | baseline:hybrid | 0.00000 | 0.00000 | 0.00000 | 70 | 0 | 0 | 70 |
| query | validation | symmetric_exact:hybrid | baseline:r_e7 | 0.00530 | -0.00354 | 0.01559 | 70 | 6 | 4 | 60 |
| query | validation | symmetric_exact:hybrid | current:frozen_all_terms | 0.00479 | -0.00245 | 0.01295 | 70 | 6 | 2 | 62 |
| query | validation | symmetric_exact:hybrid | current:r_e7_equivalent | 0.00530 | -0.00354 | 0.01559 | 70 | 6 | 4 | 60 |
| query | validation | symmetric_exact:selected_signed_intent | baseline:hybrid | -0.00453 | -0.01306 | 0.00295 | 70 | 2 | 5 | 63 |
| query | validation | symmetric_exact:selected_signed_intent | baseline:r_e7 | 0.00077 | -0.00414 | 0.00584 | 70 | 3 | 4 | 63 |
| query | validation | symmetric_exact:selected_signed_intent | current:frozen_all_terms | 0.00026 | -0.00110 | 0.00193 | 70 | 2 | 1 | 67 |
| query | validation | symmetric_exact:selected_signed_intent | current:r_e7_equivalent | 0.00077 | -0.00414 | 0.00584 | 70 | 3 | 4 | 63 |
| query | validation | symmetric_exact:selected_all_terms | baseline:hybrid | -0.00453 | -0.01306 | 0.00295 | 70 | 2 | 5 | 63 |
| query | validation | symmetric_exact:selected_all_terms | baseline:r_e7 | 0.00077 | -0.00414 | 0.00584 | 70 | 3 | 4 | 63 |
| query | validation | symmetric_exact:selected_all_terms | current:frozen_all_terms | 0.00026 | -0.00110 | 0.00193 | 70 | 2 | 1 | 67 |
| query | validation | symmetric_exact:selected_all_terms | current:r_e7_equivalent | 0.00077 | -0.00414 | 0.00584 | 70 | 3 | 4 | 63 |
| query | validation | symmetric_exact:frozen_all_terms | baseline:hybrid | -0.00453 | -0.01306 | 0.00295 | 70 | 2 | 5 | 63 |
| query | validation | symmetric_exact:frozen_all_terms | baseline:r_e7 | 0.00077 | -0.00414 | 0.00584 | 70 | 3 | 4 | 63 |
| query | validation | symmetric_exact:frozen_all_terms | current:frozen_all_terms | 0.00026 | -0.00110 | 0.00193 | 70 | 2 | 1 | 67 |
| query | validation | symmetric_exact:frozen_all_terms | current:r_e7_equivalent | 0.00077 | -0.00414 | 0.00584 | 70 | 3 | 4 | 63 |
| query | validation | symmetric_exact:r_e7_style | baseline:hybrid | -0.00502 | -0.01542 | 0.00370 | 70 | 4 | 6 | 60 |
| query | validation | symmetric_exact:r_e7_style | baseline:r_e7 | 0.00028 | -0.00013 | 0.00098 | 70 | 1 | 1 | 68 |
| query | validation | symmetric_exact:r_e7_style | current:frozen_all_terms | -0.00023 | -0.00435 | 0.00416 | 70 | 3 | 3 | 64 |
| query | validation | symmetric_exact:r_e7_style | current:r_e7_equivalent | 0.00028 | -0.00013 | 0.00098 | 70 | 1 | 1 | 68 |
| query | validation | ablation:requested_current_context | baseline:hybrid | -0.00521 | -0.01332 | 0.00172 | 70 | 2 | 6 | 62 |
| query | validation | ablation:requested_current_context | baseline:r_e7 | 0.00009 | -0.00447 | 0.00467 | 70 | 3 | 4 | 63 |
| query | validation | ablation:requested_current_context | current:frozen_all_terms | -0.00042 | -0.00125 | 0.00000 | 70 | 0 | 1 | 69 |
| query | validation | ablation:requested_current_context | current:r_e7_equivalent | 0.00009 | -0.00447 | 0.00467 | 70 | 3 | 4 | 63 |
| query | validation | ablation:symmetric_current_context | baseline:hybrid | -0.00453 | -0.01306 | 0.00295 | 70 | 2 | 5 | 63 |
| query | validation | ablation:symmetric_current_context | baseline:r_e7 | 0.00077 | -0.00414 | 0.00584 | 70 | 3 | 4 | 63 |
| query | validation | ablation:symmetric_current_context | current:frozen_all_terms | 0.00026 | -0.00110 | 0.00193 | 70 | 2 | 1 | 67 |
| query | validation | ablation:symmetric_current_context | current:r_e7_equivalent | 0.00077 | -0.00414 | 0.00584 | 70 | 3 | 4 | 63 |
| query | validation | ablation:dimension_exact_context | baseline:hybrid | -0.00479 | -0.01295 | 0.00245 | 70 | 2 | 6 | 62 |
| query | validation | ablation:dimension_exact_context | baseline:r_e7 | 0.00051 | -0.00387 | 0.00482 | 70 | 3 | 4 | 63 |
| query | validation | ablation:dimension_exact_context | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 70 | 0 | 0 | 70 |
| query | validation | ablation:dimension_exact_context | current:r_e7_equivalent | 0.00051 | -0.00387 | 0.00482 | 70 | 3 | 4 | 63 |
| query | test | requested_exact:hybrid | baseline:hybrid | 0.00000 | 0.00000 | 0.00000 | 68 | 0 | 0 | 68 |
| query | test | requested_exact:hybrid | baseline:r_e7 | -0.00117 | -0.01105 | 0.00825 | 68 | 6 | 5 | 57 |
| query | test | requested_exact:hybrid | current:frozen_all_terms | 0.00196 | -0.00593 | 0.01014 | 68 | 7 | 4 | 57 |
| query | test | requested_exact:hybrid | current:r_e7_equivalent | 0.00684 | -0.00418 | 0.02043 | 68 | 7 | 4 | 57 |
| query | test | requested_exact:selected_signed_intent | baseline:hybrid | -0.00196 | -0.01014 | 0.00593 | 68 | 4 | 7 | 57 |
| query | test | requested_exact:selected_signed_intent | baseline:r_e7 | -0.00313 | -0.00922 | 0.00002 | 68 | 1 | 3 | 64 |
| query | test | requested_exact:selected_signed_intent | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 68 | 0 | 0 | 68 |
| query | test | requested_exact:selected_signed_intent | current:r_e7_equivalent | 0.00488 | -0.00052 | 0.01519 | 68 | 2 | 2 | 64 |
| query | test | requested_exact:selected_all_terms | baseline:hybrid | -0.00196 | -0.01014 | 0.00593 | 68 | 4 | 7 | 57 |
| query | test | requested_exact:selected_all_terms | baseline:r_e7 | -0.00313 | -0.00922 | 0.00002 | 68 | 1 | 3 | 64 |
| query | test | requested_exact:selected_all_terms | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 68 | 0 | 0 | 68 |
| query | test | requested_exact:selected_all_terms | current:r_e7_equivalent | 0.00488 | -0.00052 | 0.01519 | 68 | 2 | 2 | 64 |
| query | test | requested_exact:frozen_all_terms | baseline:hybrid | -0.00196 | -0.01014 | 0.00593 | 68 | 4 | 7 | 57 |
| query | test | requested_exact:frozen_all_terms | baseline:r_e7 | -0.00313 | -0.00922 | 0.00002 | 68 | 1 | 3 | 64 |
| query | test | requested_exact:frozen_all_terms | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 68 | 0 | 0 | 68 |
| query | test | requested_exact:frozen_all_terms | current:r_e7_equivalent | 0.00488 | -0.00052 | 0.01519 | 68 | 2 | 2 | 64 |
| query | test | requested_exact:r_e7_style | baseline:hybrid | -0.00684 | -0.02043 | 0.00418 | 68 | 4 | 7 | 57 |
| query | test | requested_exact:r_e7_style | baseline:r_e7 | -0.00801 | -0.02404 | 0.00000 | 68 | 0 | 1 | 67 |
| query | test | requested_exact:r_e7_style | current:frozen_all_terms | -0.00488 | -0.01519 | 0.00052 | 68 | 2 | 2 | 64 |
| query | test | requested_exact:r_e7_style | current:r_e7_equivalent | 0.00000 | 0.00000 | 0.00000 | 68 | 0 | 0 | 68 |
| query | test | symmetric_exact:hybrid | baseline:hybrid | 0.00000 | 0.00000 | 0.00000 | 68 | 0 | 0 | 68 |
| query | test | symmetric_exact:hybrid | baseline:r_e7 | -0.00117 | -0.01105 | 0.00825 | 68 | 6 | 5 | 57 |
| query | test | symmetric_exact:hybrid | current:frozen_all_terms | 0.00196 | -0.00593 | 0.01014 | 68 | 7 | 4 | 57 |
| query | test | symmetric_exact:hybrid | current:r_e7_equivalent | 0.00684 | -0.00418 | 0.02043 | 68 | 7 | 4 | 57 |
| query | test | symmetric_exact:selected_signed_intent | baseline:hybrid | -0.00260 | -0.01068 | 0.00505 | 68 | 4 | 7 | 57 |
| query | test | symmetric_exact:selected_signed_intent | baseline:r_e7 | -0.00377 | -0.01033 | 0.00000 | 68 | 1 | 4 | 63 |
| query | test | symmetric_exact:selected_signed_intent | current:frozen_all_terms | -0.00064 | -0.00193 | 0.00000 | 68 | 0 | 1 | 67 |
| query | test | symmetric_exact:selected_signed_intent | current:r_e7_equivalent | 0.00424 | -0.00196 | 0.01502 | 68 | 2 | 3 | 63 |
| query | test | symmetric_exact:selected_all_terms | baseline:hybrid | -0.00260 | -0.01068 | 0.00505 | 68 | 4 | 7 | 57 |
| query | test | symmetric_exact:selected_all_terms | baseline:r_e7 | -0.00377 | -0.01033 | 0.00000 | 68 | 1 | 4 | 63 |
| query | test | symmetric_exact:selected_all_terms | current:frozen_all_terms | -0.00064 | -0.00193 | 0.00000 | 68 | 0 | 1 | 67 |
| query | test | symmetric_exact:selected_all_terms | current:r_e7_equivalent | 0.00424 | -0.00196 | 0.01502 | 68 | 2 | 3 | 63 |
| query | test | symmetric_exact:frozen_all_terms | baseline:hybrid | -0.00260 | -0.01068 | 0.00505 | 68 | 4 | 7 | 57 |
| query | test | symmetric_exact:frozen_all_terms | baseline:r_e7 | -0.00377 | -0.01033 | 0.00000 | 68 | 1 | 4 | 63 |
| query | test | symmetric_exact:frozen_all_terms | current:frozen_all_terms | -0.00064 | -0.00193 | 0.00000 | 68 | 0 | 1 | 67 |
| query | test | symmetric_exact:frozen_all_terms | current:r_e7_equivalent | 0.00424 | -0.00196 | 0.01502 | 68 | 2 | 3 | 63 |
| query | test | symmetric_exact:r_e7_style | baseline:hybrid | -0.00749 | -0.02093 | 0.00323 | 68 | 4 | 7 | 57 |
| query | test | symmetric_exact:r_e7_style | baseline:r_e7 | -0.00866 | -0.02533 | 0.00000 | 68 | 0 | 2 | 66 |
| query | test | symmetric_exact:r_e7_style | current:frozen_all_terms | -0.00553 | -0.01644 | 0.00035 | 68 | 2 | 3 | 63 |
| query | test | symmetric_exact:r_e7_style | current:r_e7_equivalent | -0.00064 | -0.00193 | 0.00000 | 68 | 0 | 1 | 67 |
| query | test | ablation:requested_current_context | baseline:hybrid | -0.00196 | -0.01014 | 0.00593 | 68 | 4 | 7 | 57 |
| query | test | ablation:requested_current_context | baseline:r_e7 | -0.00313 | -0.00922 | 0.00002 | 68 | 1 | 3 | 64 |
| query | test | ablation:requested_current_context | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 68 | 0 | 0 | 68 |
| query | test | ablation:requested_current_context | current:r_e7_equivalent | 0.00488 | -0.00052 | 0.01519 | 68 | 2 | 2 | 64 |
| query | test | ablation:symmetric_current_context | baseline:hybrid | -0.00260 | -0.01068 | 0.00505 | 68 | 4 | 7 | 57 |
| query | test | ablation:symmetric_current_context | baseline:r_e7 | -0.00377 | -0.01033 | 0.00000 | 68 | 1 | 4 | 63 |
| query | test | ablation:symmetric_current_context | current:frozen_all_terms | -0.00064 | -0.00193 | 0.00000 | 68 | 0 | 1 | 67 |
| query | test | ablation:symmetric_current_context | current:r_e7_equivalent | 0.00424 | -0.00196 | 0.01502 | 68 | 2 | 3 | 63 |
| query | test | ablation:dimension_exact_context | baseline:hybrid | -0.00196 | -0.01014 | 0.00593 | 68 | 4 | 7 | 57 |
| query | test | ablation:dimension_exact_context | baseline:r_e7 | -0.00313 | -0.00922 | 0.00002 | 68 | 1 | 3 | 64 |
| query | test | ablation:dimension_exact_context | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 68 | 0 | 0 | 68 |
| query | test | ablation:dimension_exact_context | current:r_e7_equivalent | 0.00488 | -0.00052 | 0.01519 | 68 | 2 | 2 | 64 |
| query_dedup | validation | requested_exact:hybrid | baseline:hybrid | 0.00000 | 0.00000 | 0.00000 | 69 | 0 | 0 | 69 |
| query_dedup | validation | requested_exact:hybrid | baseline:r_e7 | -0.00134 | -0.01073 | 0.00706 | 69 | 3 | 4 | 62 |
| query_dedup | validation | requested_exact:hybrid | current:frozen_all_terms | 0.00237 | -0.00337 | 0.00935 | 69 | 3 | 2 | 64 |
| query_dedup | validation | requested_exact:hybrid | current:r_e7_equivalent | 0.00656 | -0.00333 | 0.02031 | 69 | 4 | 3 | 62 |
| query_dedup | validation | requested_exact:selected_signed_intent | baseline:hybrid | -0.00237 | -0.00935 | 0.00337 | 69 | 2 | 3 | 64 |
| query_dedup | validation | requested_exact:selected_signed_intent | baseline:r_e7 | -0.00370 | -0.01172 | 0.00152 | 69 | 1 | 3 | 65 |
| query_dedup | validation | requested_exact:selected_signed_intent | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 69 | 0 | 0 | 69 |
| query_dedup | validation | requested_exact:selected_signed_intent | current:r_e7_equivalent | 0.00419 | -0.00313 | 0.01650 | 69 | 2 | 2 | 65 |
| query_dedup | validation | requested_exact:selected_all_terms | baseline:hybrid | -0.00237 | -0.00935 | 0.00337 | 69 | 2 | 3 | 64 |
| query_dedup | validation | requested_exact:selected_all_terms | baseline:r_e7 | -0.00370 | -0.01172 | 0.00152 | 69 | 1 | 3 | 65 |
| query_dedup | validation | requested_exact:selected_all_terms | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 69 | 0 | 0 | 69 |
| query_dedup | validation | requested_exact:selected_all_terms | current:r_e7_equivalent | 0.00419 | -0.00313 | 0.01650 | 69 | 2 | 2 | 65 |
| query_dedup | validation | requested_exact:frozen_all_terms | baseline:hybrid | -0.00237 | -0.00935 | 0.00337 | 69 | 2 | 3 | 64 |
| query_dedup | validation | requested_exact:frozen_all_terms | baseline:r_e7 | -0.00370 | -0.01172 | 0.00152 | 69 | 1 | 3 | 65 |
| query_dedup | validation | requested_exact:frozen_all_terms | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 69 | 0 | 0 | 69 |
| query_dedup | validation | requested_exact:frozen_all_terms | current:r_e7_equivalent | 0.00419 | -0.00313 | 0.01650 | 69 | 2 | 2 | 65 |
| query_dedup | validation | requested_exact:r_e7_style | baseline:hybrid | -0.00656 | -0.02031 | 0.00333 | 69 | 3 | 4 | 62 |
| query_dedup | validation | requested_exact:r_e7_style | baseline:r_e7 | -0.00790 | -0.02369 | 0.00000 | 69 | 0 | 1 | 68 |
| query_dedup | validation | requested_exact:r_e7_style | current:frozen_all_terms | -0.00419 | -0.01650 | 0.00313 | 69 | 2 | 2 | 65 |
| query_dedup | validation | requested_exact:r_e7_style | current:r_e7_equivalent | 0.00000 | 0.00000 | 0.00000 | 69 | 0 | 0 | 69 |
| query_dedup | validation | symmetric_exact:hybrid | baseline:hybrid | 0.00000 | 0.00000 | 0.00000 | 69 | 0 | 0 | 69 |
| query_dedup | validation | symmetric_exact:hybrid | baseline:r_e7 | -0.00134 | -0.01073 | 0.00706 | 69 | 3 | 4 | 62 |
| query_dedup | validation | symmetric_exact:hybrid | current:frozen_all_terms | 0.00237 | -0.00337 | 0.00935 | 69 | 3 | 2 | 64 |
| query_dedup | validation | symmetric_exact:hybrid | current:r_e7_equivalent | 0.00656 | -0.00333 | 0.02031 | 69 | 4 | 3 | 62 |
| query_dedup | validation | symmetric_exact:selected_signed_intent | baseline:hybrid | -0.00169 | -0.00887 | 0.00492 | 69 | 2 | 3 | 64 |
| query_dedup | validation | symmetric_exact:selected_signed_intent | baseline:r_e7 | -0.00303 | -0.01164 | 0.00282 | 69 | 2 | 3 | 64 |
| query_dedup | validation | symmetric_exact:selected_signed_intent | current:frozen_all_terms | 0.00067 | 0.00000 | 0.00202 | 69 | 2 | 0 | 67 |
| query_dedup | validation | symmetric_exact:selected_signed_intent | current:r_e7_equivalent | 0.00487 | -0.00310 | 0.01781 | 69 | 3 | 2 | 64 |
| query_dedup | validation | symmetric_exact:selected_all_terms | baseline:hybrid | -0.00169 | -0.00887 | 0.00492 | 69 | 2 | 3 | 64 |
| query_dedup | validation | symmetric_exact:selected_all_terms | baseline:r_e7 | -0.00303 | -0.01164 | 0.00282 | 69 | 2 | 3 | 64 |
| query_dedup | validation | symmetric_exact:selected_all_terms | current:frozen_all_terms | 0.00067 | 0.00000 | 0.00202 | 69 | 2 | 0 | 67 |
| query_dedup | validation | symmetric_exact:selected_all_terms | current:r_e7_equivalent | 0.00487 | -0.00310 | 0.01781 | 69 | 3 | 2 | 64 |
| query_dedup | validation | symmetric_exact:frozen_all_terms | baseline:hybrid | -0.00169 | -0.00887 | 0.00492 | 69 | 2 | 3 | 64 |
| query_dedup | validation | symmetric_exact:frozen_all_terms | baseline:r_e7 | -0.00303 | -0.01164 | 0.00282 | 69 | 2 | 3 | 64 |
| query_dedup | validation | symmetric_exact:frozen_all_terms | current:frozen_all_terms | 0.00067 | 0.00000 | 0.00202 | 69 | 2 | 0 | 67 |
| query_dedup | validation | symmetric_exact:frozen_all_terms | current:r_e7_equivalent | 0.00487 | -0.00310 | 0.01781 | 69 | 3 | 2 | 64 |
| query_dedup | validation | symmetric_exact:r_e7_style | baseline:hybrid | -0.00623 | -0.01993 | 0.00380 | 69 | 3 | 4 | 62 |
| query_dedup | validation | symmetric_exact:r_e7_style | baseline:r_e7 | -0.00757 | -0.02369 | 0.00099 | 69 | 1 | 1 | 67 |
| query_dedup | validation | symmetric_exact:r_e7_style | current:frozen_all_terms | -0.00386 | -0.01584 | 0.00372 | 69 | 2 | 2 | 65 |
| query_dedup | validation | symmetric_exact:r_e7_style | current:r_e7_equivalent | 0.00033 | 0.00000 | 0.00099 | 69 | 1 | 0 | 68 |
| query_dedup | validation | ablation:requested_current_context | baseline:hybrid | -0.00237 | -0.00935 | 0.00337 | 69 | 2 | 3 | 64 |
| query_dedup | validation | ablation:requested_current_context | baseline:r_e7 | -0.00370 | -0.01172 | 0.00152 | 69 | 1 | 3 | 65 |
| query_dedup | validation | ablation:requested_current_context | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 69 | 0 | 0 | 69 |
| query_dedup | validation | ablation:requested_current_context | current:r_e7_equivalent | 0.00419 | -0.00313 | 0.01650 | 69 | 2 | 2 | 65 |
| query_dedup | validation | ablation:symmetric_current_context | baseline:hybrid | -0.00169 | -0.00887 | 0.00492 | 69 | 2 | 3 | 64 |
| query_dedup | validation | ablation:symmetric_current_context | baseline:r_e7 | -0.00303 | -0.01164 | 0.00282 | 69 | 2 | 3 | 64 |
| query_dedup | validation | ablation:symmetric_current_context | current:frozen_all_terms | 0.00067 | 0.00000 | 0.00202 | 69 | 2 | 0 | 67 |
| query_dedup | validation | ablation:symmetric_current_context | current:r_e7_equivalent | 0.00487 | -0.00310 | 0.01781 | 69 | 3 | 2 | 64 |
| query_dedup | validation | ablation:dimension_exact_context | baseline:hybrid | -0.00237 | -0.00935 | 0.00337 | 69 | 2 | 3 | 64 |
| query_dedup | validation | ablation:dimension_exact_context | baseline:r_e7 | -0.00370 | -0.01172 | 0.00152 | 69 | 1 | 3 | 65 |
| query_dedup | validation | ablation:dimension_exact_context | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 69 | 0 | 0 | 69 |
| query_dedup | validation | ablation:dimension_exact_context | current:r_e7_equivalent | 0.00419 | -0.00313 | 0.01650 | 69 | 2 | 2 | 65 |
| query_dedup | test | requested_exact:hybrid | baseline:hybrid | 0.00000 | 0.00000 | 0.00000 | 68 | 0 | 0 | 68 |
| query_dedup | test | requested_exact:hybrid | baseline:r_e7 | -0.00174 | -0.00927 | 0.00565 | 68 | 6 | 6 | 56 |
| query_dedup | test | requested_exact:hybrid | current:frozen_all_terms | -0.00044 | -0.00740 | 0.00621 | 68 | 7 | 4 | 57 |
| query_dedup | test | requested_exact:hybrid | current:r_e7_equivalent | 0.00002 | -0.00716 | 0.00721 | 68 | 6 | 4 | 58 |
| query_dedup | test | requested_exact:selected_signed_intent | baseline:hybrid | 0.00001 | -0.00640 | 0.00663 | 68 | 4 | 7 | 57 |
| query_dedup | test | requested_exact:selected_signed_intent | baseline:r_e7 | -0.00172 | -0.00487 | 0.00137 | 68 | 1 | 6 | 61 |
| query_dedup | test | requested_exact:selected_signed_intent | current:frozen_all_terms | -0.00043 | -0.00129 | 0.00000 | 68 | 0 | 1 | 67 |
| query_dedup | test | requested_exact:selected_signed_intent | current:r_e7_equivalent | 0.00004 | -0.00158 | 0.00220 | 68 | 1 | 4 | 63 |
| query_dedup | test | requested_exact:selected_all_terms | baseline:hybrid | 0.00001 | -0.00640 | 0.00663 | 68 | 4 | 7 | 57 |
| query_dedup | test | requested_exact:selected_all_terms | baseline:r_e7 | -0.00172 | -0.00487 | 0.00137 | 68 | 1 | 6 | 61 |
| query_dedup | test | requested_exact:selected_all_terms | current:frozen_all_terms | -0.00043 | -0.00129 | 0.00000 | 68 | 0 | 1 | 67 |
| query_dedup | test | requested_exact:selected_all_terms | current:r_e7_equivalent | 0.00004 | -0.00158 | 0.00220 | 68 | 1 | 4 | 63 |
| query_dedup | test | requested_exact:frozen_all_terms | baseline:hybrid | 0.00001 | -0.00640 | 0.00663 | 68 | 4 | 7 | 57 |
| query_dedup | test | requested_exact:frozen_all_terms | baseline:r_e7 | -0.00172 | -0.00487 | 0.00137 | 68 | 1 | 6 | 61 |
| query_dedup | test | requested_exact:frozen_all_terms | current:frozen_all_terms | -0.00043 | -0.00129 | 0.00000 | 68 | 0 | 1 | 67 |
| query_dedup | test | requested_exact:frozen_all_terms | current:r_e7_equivalent | 0.00004 | -0.00158 | 0.00220 | 68 | 1 | 4 | 63 |
| query_dedup | test | requested_exact:r_e7_style | baseline:hybrid | -0.00007 | -0.00727 | 0.00707 | 68 | 4 | 6 | 58 |
| query_dedup | test | requested_exact:r_e7_style | baseline:r_e7 | -0.00180 | -0.00448 | 0.00000 | 68 | 0 | 3 | 65 |
| query_dedup | test | requested_exact:r_e7_style | current:frozen_all_terms | -0.00051 | -0.00235 | 0.00056 | 68 | 3 | 1 | 64 |
| query_dedup | test | requested_exact:r_e7_style | current:r_e7_equivalent | -0.00005 | -0.00014 | 0.00000 | 68 | 0 | 1 | 67 |
| query_dedup | test | symmetric_exact:hybrid | baseline:hybrid | 0.00000 | 0.00000 | 0.00000 | 68 | 0 | 0 | 68 |
| query_dedup | test | symmetric_exact:hybrid | baseline:r_e7 | -0.00174 | -0.00927 | 0.00565 | 68 | 6 | 6 | 56 |
| query_dedup | test | symmetric_exact:hybrid | current:frozen_all_terms | -0.00044 | -0.00740 | 0.00621 | 68 | 7 | 4 | 57 |
| query_dedup | test | symmetric_exact:hybrid | current:r_e7_equivalent | 0.00002 | -0.00716 | 0.00721 | 68 | 6 | 4 | 58 |
| query_dedup | test | symmetric_exact:selected_signed_intent | baseline:hybrid | -0.00065 | -0.00699 | 0.00550 | 68 | 4 | 7 | 57 |
| query_dedup | test | symmetric_exact:selected_signed_intent | baseline:r_e7 | -0.00238 | -0.00576 | 0.00083 | 68 | 1 | 8 | 59 |
| query_dedup | test | symmetric_exact:selected_signed_intent | current:frozen_all_terms | -0.00109 | -0.00279 | 0.00000 | 68 | 0 | 3 | 65 |
| query_dedup | test | symmetric_exact:selected_signed_intent | current:r_e7_equivalent | -0.00063 | -0.00274 | 0.00176 | 68 | 1 | 6 | 61 |
| query_dedup | test | symmetric_exact:selected_all_terms | baseline:hybrid | -0.00065 | -0.00699 | 0.00550 | 68 | 4 | 7 | 57 |
| query_dedup | test | symmetric_exact:selected_all_terms | baseline:r_e7 | -0.00238 | -0.00576 | 0.00083 | 68 | 1 | 8 | 59 |
| query_dedup | test | symmetric_exact:selected_all_terms | current:frozen_all_terms | -0.00109 | -0.00279 | 0.00000 | 68 | 0 | 3 | 65 |
| query_dedup | test | symmetric_exact:selected_all_terms | current:r_e7_equivalent | -0.00063 | -0.00274 | 0.00176 | 68 | 1 | 6 | 61 |
| query_dedup | test | symmetric_exact:frozen_all_terms | baseline:hybrid | -0.00065 | -0.00699 | 0.00550 | 68 | 4 | 7 | 57 |
| query_dedup | test | symmetric_exact:frozen_all_terms | baseline:r_e7 | -0.00238 | -0.00576 | 0.00083 | 68 | 1 | 8 | 59 |
| query_dedup | test | symmetric_exact:frozen_all_terms | current:frozen_all_terms | -0.00109 | -0.00279 | 0.00000 | 68 | 0 | 3 | 65 |
| query_dedup | test | symmetric_exact:frozen_all_terms | current:r_e7_equivalent | -0.00063 | -0.00274 | 0.00176 | 68 | 1 | 6 | 61 |
| query_dedup | test | symmetric_exact:r_e7_style | baseline:hybrid | -0.00071 | -0.00772 | 0.00630 | 68 | 4 | 6 | 58 |
| query_dedup | test | symmetric_exact:r_e7_style | baseline:r_e7 | -0.00245 | -0.00536 | -0.00005 | 68 | 0 | 4 | 64 |
| query_dedup | test | symmetric_exact:r_e7_style | current:frozen_all_terms | -0.00116 | -0.00339 | 0.00043 | 68 | 3 | 2 | 63 |
| query_dedup | test | symmetric_exact:r_e7_style | current:r_e7_equivalent | -0.00069 | -0.00202 | 0.00000 | 68 | 0 | 2 | 66 |
| query_dedup | test | ablation:requested_current_context | baseline:hybrid | 0.00001 | -0.00640 | 0.00663 | 68 | 4 | 7 | 57 |
| query_dedup | test | ablation:requested_current_context | baseline:r_e7 | -0.00172 | -0.00487 | 0.00137 | 68 | 1 | 6 | 61 |
| query_dedup | test | ablation:requested_current_context | current:frozen_all_terms | -0.00043 | -0.00129 | 0.00000 | 68 | 0 | 1 | 67 |
| query_dedup | test | ablation:requested_current_context | current:r_e7_equivalent | 0.00004 | -0.00158 | 0.00220 | 68 | 1 | 4 | 63 |
| query_dedup | test | ablation:symmetric_current_context | baseline:hybrid | -0.00065 | -0.00699 | 0.00550 | 68 | 4 | 7 | 57 |
| query_dedup | test | ablation:symmetric_current_context | baseline:r_e7 | -0.00238 | -0.00576 | 0.00083 | 68 | 1 | 8 | 59 |
| query_dedup | test | ablation:symmetric_current_context | current:frozen_all_terms | -0.00109 | -0.00279 | 0.00000 | 68 | 0 | 3 | 65 |
| query_dedup | test | ablation:symmetric_current_context | current:r_e7_equivalent | -0.00063 | -0.00274 | 0.00176 | 68 | 1 | 6 | 61 |
| query_dedup | test | ablation:dimension_exact_context | baseline:hybrid | 0.00044 | -0.00621 | 0.00740 | 68 | 4 | 7 | 57 |
| query_dedup | test | ablation:dimension_exact_context | baseline:r_e7 | -0.00129 | -0.00416 | 0.00144 | 68 | 1 | 6 | 61 |
| query_dedup | test | ablation:dimension_exact_context | current:frozen_all_terms | 0.00000 | 0.00000 | 0.00000 | 68 | 0 | 0 | 68 |
| query_dedup | test | ablation:dimension_exact_context | current:r_e7_equivalent | 0.00047 | -0.00062 | 0.00231 | 68 | 1 | 4 | 63 |

## Detailed source index

Contains links to saved per-class metrics, confusion matrices, slices, per-query metrics, validation trials, extraction audits, relevance diagnostics and phase reports.

- [outputs/audits/phase1_content_near_duplicates.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/phase1_content_near_duplicates.csv)

- [outputs/audits/phase1_data_audit.md](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/phase1_data_audit.md)

- [outputs/audits/phase1_metrics.json](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/phase1_metrics.json)

- [outputs/audits/phase1_query_manual_review.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/phase1_query_manual_review.csv)

- [outputs/audits/phase1_query_near_duplicates.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/phase1_query_near_duplicates.csv)

- [outputs/audits/phase1_suspicious_behavior.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/phase1_suspicious_behavior.csv)

- [outputs/audits/retrieval_evidence/all_records.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/retrieval_evidence/all_records.csv)

- [outputs/audits/retrieval_evidence/context_evidence.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/retrieval_evidence/context_evidence.csv)

- [outputs/audits/retrieval_evidence/context_source_summary.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/retrieval_evidence/context_source_summary.csv)

- [outputs/audits/retrieval_evidence/entity_evidence.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/retrieval_evidence/entity_evidence.csv)

- [outputs/audits/retrieval_evidence/entity_support_summary.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/retrieval_evidence/entity_support_summary.csv)

- [outputs/audits/retrieval_evidence/followup_diagnostics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/retrieval_evidence/followup_diagnostics.csv)

- [outputs/audits/retrieval_evidence/manifest.json](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/retrieval_evidence/manifest.json)

- [outputs/audits/retrieval_evidence/report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/retrieval_evidence/report.md)

- [outputs/audits/retrieval_evidence/review_findings.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/retrieval_evidence/review_findings.csv)

- [outputs/audits/retrieval_evidence/review_sample.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/retrieval_evidence/review_sample.csv)

- [outputs/audits/retrieval_evidence/reviewed_sample.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/retrieval_evidence/reviewed_sample.csv)

- [outputs/audits/tables/behavioral_signals/dwell_time_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/behavioral_signals/dwell_time_distribution.csv)

- [outputs/audits/tables/behavioral_signals/event_type_dwell_relationship.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/behavioral_signals/event_type_dwell_relationship.csv)

- [outputs/audits/tables/behavioral_signals/event_type_frequency.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/behavioral_signals/event_type_frequency.csv)

- [outputs/audits/tables/behavioral_signals/events_per_content.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/behavioral_signals/events_per_content.csv)

- [outputs/audits/tables/behavioral_signals/events_per_doctor.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/behavioral_signals/events_per_doctor.csv)

- [outputs/audits/tables/behavioral_signals/events_per_query.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/behavioral_signals/events_per_query.csv)

- [outputs/audits/tables/behavioral_signals/events_per_session.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/behavioral_signals/events_per_session.csv)

- [outputs/audits/tables/behavioral_signals/missing_values.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/behavioral_signals/missing_values.csv)

- [outputs/audits/tables/behavioral_signals/repeated_engagement.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/behavioral_signals/repeated_engagement.csv)

- [outputs/audits/tables/content/content_core_metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/content/content_core_metrics.csv)

- [outputs/audits/tables/content/content_type_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/content/content_type_distribution.csv)

- [outputs/audits/tables/content/disease_entity_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/content/disease_entity_distribution.csv)

- [outputs/audits/tables/content/drug_class_entity_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/content/drug_class_entity_distribution.csv)

- [outputs/audits/tables/content/entity_count_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/content/entity_count_distribution.csv)

- [outputs/audits/tables/content/language_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/content/language_distribution.csv)

- [outputs/audits/tables/content/matchable_dimensions.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/content/matchable_dimensions.csv)

- [outputs/audits/tables/content/missing_values.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/content/missing_values.csv)

- [outputs/audits/tables/content/molecule_entity_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/content/molecule_entity_distribution.csv)

- [outputs/audits/tables/content/publication_year_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/content/publication_year_distribution.csv)

- [outputs/audits/tables/content/source_type_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/content/source_type_distribution.csv)

- [outputs/audits/tables/content/therapeutic_area_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/content/therapeutic_area_distribution.csv)

- [outputs/audits/tables/content/word_count_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/content/word_count_distribution.csv)

- [outputs/audits/tables/impressions/content_exposure_frequency.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/impressions/content_exposure_frequency.csv)

- [outputs/audits/tables/impressions/engagement_by_inferred_rank.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/impressions/engagement_by_inferred_rank.csv)

- [outputs/audits/tables/impressions/impression_core_metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/impressions/impression_core_metrics.csv)

- [outputs/audits/tables/impressions/impressions_per_content.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/impressions/impressions_per_content.csv)

- [outputs/audits/tables/impressions/impressions_per_query.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/impressions/impressions_per_query.csv)

- [outputs/audits/tables/impressions/impressions_per_session.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/impressions/impressions_per_session.csv)

- [outputs/audits/tables/impressions/missing_values.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/impressions/missing_values.csv)

- [outputs/audits/tables/queries/disease_frequency.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/queries/disease_frequency.csv)

- [outputs/audits/tables/queries/drug_class_frequency.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/queries/drug_class_frequency.csv)

- [outputs/audits/tables/queries/entity_count_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/queries/entity_count_distribution.csv)

- [outputs/audits/tables/queries/language_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/queries/language_distribution.csv)

- [outputs/audits/tables/queries/language_examples.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/queries/language_examples.csv)

- [outputs/audits/tables/queries/missing_values.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/queries/missing_values.csv)

- [outputs/audits/tables/queries/molecule_frequency.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/queries/molecule_frequency.csv)

- [outputs/audits/tables/queries/query_core_metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/queries/query_core_metrics.csv)

- [outputs/audits/tables/queries/query_length_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/queries/query_length_distribution.csv)

- [outputs/audits/tables/queries/therapeutic_area_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/audits/tables/queries/therapeutic_area_distribution.csv)

- [outputs/compatibility/phase75_clear_methodology_mapping.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/compatibility/phase75_clear_methodology_mapping.csv)

- [outputs/compatibility/phase75_compatibility_examples.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/compatibility/phase75_compatibility_examples.csv)

- [outputs/compatibility/phase75_compatibility_metrics.json](/Users/hol/Documents/Task/doctor-search-service/outputs/compatibility/phase75_compatibility_metrics.json)

- [outputs/compatibility/phase75_compatibility_report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/compatibility/phase75_compatibility_report.md)

- [outputs/compatibility/phase75_feature_dictionary.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/compatibility/phase75_feature_dictionary.csv)

- [outputs/compatibility/phase75_feature_summary.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/compatibility/phase75_feature_summary.csv)

- [outputs/compatibility/phase75_observed_relevance_diagnostics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/compatibility/phase75_observed_relevance_diagnostics.csv)

- [outputs/evaluation/phase8_duplicate_overlap_audit.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/phase8_duplicate_overlap_audit.csv)

- [outputs/evaluation/phase8_duplicate_pairs.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/phase8_duplicate_pairs.csv)

- [outputs/evaluation/phase8_overlap_audit.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/phase8_overlap_audit.csv)

- [outputs/evaluation/phase8_split_manifest.json](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/phase8_split_manifest.json)

- [outputs/evaluation/phase8_split_summary.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/phase8_split_summary.csv)

- [outputs/evaluation/query_dedup_event_assignments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_dedup_event_assignments.csv)

- [outputs/evaluation/query_dedup_exposure_assignments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_dedup_exposure_assignments.csv)

- [outputs/evaluation/query_dedup_query_groups.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_dedup_query_groups.csv)

- [outputs/evaluation/query_dedup_test_judgments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_dedup_test_judgments.csv)

- [outputs/evaluation/query_dedup_test_query_coverage.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_dedup_test_query_coverage.csv)

- [outputs/evaluation/query_dedup_train_judgments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_dedup_train_judgments.csv)

- [outputs/evaluation/query_dedup_train_query_coverage.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_dedup_train_query_coverage.csv)

- [outputs/evaluation/query_dedup_validation_judgments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_dedup_validation_judgments.csv)

- [outputs/evaluation/query_dedup_validation_query_coverage.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_dedup_validation_query_coverage.csv)

- [outputs/evaluation/query_event_assignments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_event_assignments.csv)

- [outputs/evaluation/query_exposure_assignments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_exposure_assignments.csv)

- [outputs/evaluation/query_test_judgments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_test_judgments.csv)

- [outputs/evaluation/query_test_query_coverage.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_test_query_coverage.csv)

- [outputs/evaluation/query_train_judgments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_train_judgments.csv)

- [outputs/evaluation/query_train_query_coverage.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_train_query_coverage.csv)

- [outputs/evaluation/query_validation_judgments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_validation_judgments.csv)

- [outputs/evaluation/query_validation_query_coverage.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/query_validation_query_coverage.csv)

- [outputs/evaluation/temporal_event_assignments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/temporal_event_assignments.csv)

- [outputs/evaluation/temporal_exposure_assignments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/temporal_exposure_assignments.csv)

- [outputs/evaluation/temporal_test_judgments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/temporal_test_judgments.csv)

- [outputs/evaluation/temporal_test_query_coverage.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/temporal_test_query_coverage.csv)

- [outputs/evaluation/temporal_train_judgments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/temporal_train_judgments.csv)

- [outputs/evaluation/temporal_train_query_coverage.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/temporal_train_query_coverage.csv)

- [outputs/evaluation/temporal_validation_judgments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/temporal_validation_judgments.csv)

- [outputs/evaluation/temporal_validation_query_coverage.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/evaluation/temporal_validation_query_coverage.csv)

- [outputs/intent/phase3_annotation_guidelines.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/intent/phase3_annotation_guidelines.csv)

- [outputs/intent/phase3_cluster_intent_mapping.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/intent/phase3_cluster_intent_mapping.csv)

- [outputs/intent/phase3_gold_annotations.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/intent/phase3_gold_annotations.csv)

- [outputs/intent/phase3_kappa_diagnostics.json](/Users/hol/Documents/Task/doctor-search-service/outputs/intent/phase3_kappa_diagnostics.json)

- [outputs/intent/phase3_kappa_optimization_history.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/intent/phase3_kappa_optimization_history.csv)

- [outputs/intent/phase3_label_quality_audit.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/intent/phase3_label_quality_audit.csv)

- [outputs/intent/phase3_labeling_metrics.json](/Users/hol/Documents/Task/doctor-search-service/outputs/intent/phase3_labeling_metrics.json)

- [outputs/intent/phase3_labeling_report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/intent/phase3_labeling_report.md)

- [outputs/intent/phase3_pilot_annotations.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/intent/phase3_pilot_annotations.csv)

- [outputs/intent/phase3_signal_disagreements_adjudicated.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/intent/phase3_signal_disagreements_adjudicated.csv)

- [outputs/intent/phase3_three_signal_assignments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/intent/phase3_three_signal_assignments.csv)

- [outputs/metrics/phase4_intent_baseline_class_checks.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase4_intent_baseline_class_checks.csv)

- [outputs/metrics/phase4_intent_baseline_cluster_purity.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase4_intent_baseline_cluster_purity.csv)

- [outputs/metrics/phase4_intent_baseline_confusion_matrix.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase4_intent_baseline_confusion_matrix.csv)

- [outputs/metrics/phase4_intent_baseline_cv_predictions.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase4_intent_baseline_cv_predictions.csv)

- [outputs/metrics/phase4_intent_baseline_errors.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase4_intent_baseline_errors.csv)

- [outputs/metrics/phase4_intent_baseline_fold_metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase4_intent_baseline_fold_metrics.csv)

- [outputs/metrics/phase4_intent_baseline_grouped_sensitivity_predictions.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase4_intent_baseline_grouped_sensitivity_predictions.csv)

- [outputs/metrics/phase4_intent_baseline_metrics.json](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase4_intent_baseline_metrics.json)

- [outputs/metrics/phase4_intent_baseline_nearest_class_pairs.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase4_intent_baseline_nearest_class_pairs.csv)

- [outputs/metrics/phase4_intent_baseline_per_class_metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase4_intent_baseline_per_class_metrics.csv)

- [outputs/metrics/phase4_intent_baseline_report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase4_intent_baseline_report.md)

- [outputs/metrics/phase4_intent_baseline_top_features.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase4_intent_baseline_top_features.csv)

- [outputs/metrics/phase4_intent_baseline_top_level_per_class_metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase4_intent_baseline_top_level_per_class_metrics.csv)

- [outputs/metrics/phase5_intent_improved_confusion_matrix.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase5_intent_improved_confusion_matrix.csv)

- [outputs/metrics/phase5_intent_improved_confusion_pairs.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase5_intent_improved_confusion_pairs.csv)

- [outputs/metrics/phase5_intent_improved_errors.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase5_intent_improved_errors.csv)

- [outputs/metrics/phase5_intent_improved_experiment_comparison.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase5_intent_improved_experiment_comparison.csv)

- [outputs/metrics/phase5_intent_improved_fusion_vs_embedding_changes.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase5_intent_improved_fusion_vs_embedding_changes.csv)

- [outputs/metrics/phase5_intent_improved_manual_error_review.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase5_intent_improved_manual_error_review.csv)

- [outputs/metrics/phase5_intent_improved_metrics.json](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase5_intent_improved_metrics.json)

- [outputs/metrics/phase5_intent_improved_per_class_metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase5_intent_improved_per_class_metrics.csv)

- [outputs/metrics/phase5_intent_improved_prediction_changes.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase5_intent_improved_prediction_changes.csv)

- [outputs/metrics/phase5_intent_improved_predictions.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase5_intent_improved_predictions.csv)

- [outputs/metrics/phase5_intent_improved_report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase5_intent_improved_report.md)

- [outputs/metrics/phase5_intent_improved_slice_metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase5_intent_improved_slice_metrics.csv)

- [outputs/metrics/phase5_intent_improved_top_features.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/metrics/phase5_intent_improved_top_features.csv)

- [outputs/queries_labeled.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/queries_labeled.csv)

- [outputs/relevance/eda/bias/bias_association_screen.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/bias/bias_association_screen.csv)

- [outputs/relevance/eda/bias/bias_diagnostics_metrics.json](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/bias/bias_diagnostics_metrics.json)

- [outputs/relevance/eda/bias/bias_diagnostics_report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/bias/bias_diagnostics_report.md)

- [outputs/relevance/eda/bias/content_exposure_bias.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/bias/content_exposure_bias.csv)

- [outputs/relevance/eda/bias/doctor_engagement_propensity.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/bias/doctor_engagement_propensity.csv)

- [outputs/relevance/eda/bias/inferred_rank_timestamp_ties.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/bias/inferred_rank_timestamp_ties.csv)

- [outputs/relevance/eda/bias/inventory_vs_exposure_representation.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/bias/inventory_vs_exposure_representation.csv)

- [outputs/relevance/eda/bias/query_judgment_coverage.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/bias/query_judgment_coverage.csv)

- [outputs/relevance/eda/bias/session_length_bias.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/bias/session_length_bias.csv)

- [outputs/relevance/eda/bias/weekly_engagement.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/bias/weekly_engagement.csv)

- [outputs/relevance/eda/candidate_grade_sensitivity.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/candidate_grade_sensitivity.csv)

- [outputs/relevance/eda/dwell_distribution_by_event.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/dwell_distribution_by_event.csv)

- [outputs/relevance/eda/dwell_threshold_sensitivity.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/dwell_threshold_sensitivity.csv)

- [outputs/relevance/eda/engagement_by_inferred_rank.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/engagement_by_inferred_rank.csv)

- [outputs/relevance/eda/engagement_slices.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/engagement_slices.csv)

- [outputs/relevance/eda/phase6_relevance_eda_metrics.json](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/phase6_relevance_eda_metrics.json)

- [outputs/relevance/eda/phase6_relevance_eda_report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/phase6_relevance_eda_report.md)

- [outputs/relevance/eda/query_content_repeatability.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/query_content_repeatability.csv)

- [outputs/relevance/eda/session_engagement_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/session_engagement_distribution.csv)

- [outputs/relevance/eda/structured_compatibility_sanity_check.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/eda/structured_compatibility_sanity_check.csv)

- [outputs/relevance/phase6_behavioral_event_summary.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/phase6_behavioral_event_summary.csv)

- [outputs/relevance/phase6_behavioral_table_metrics.json](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/phase6_behavioral_table_metrics.json)

- [outputs/relevance/phase6_behavioral_table_report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/phase6_behavioral_table_report.md)

- [outputs/relevance/phase7_label_distribution.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/phase7_label_distribution.csv)

- [outputs/relevance/phase7_query_content_judgments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/phase7_query_content_judgments.csv)

- [outputs/relevance/phase7_query_coverage.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/phase7_query_coverage.csv)

- [outputs/relevance/phase7_relevance_metrics.json](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/phase7_relevance_metrics.json)

- [outputs/relevance/phase7_relevance_report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/phase7_relevance_report.md)

- [outputs/relevance/phase7_scheme_transitions.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/phase7_scheme_transitions.csv)

- [outputs/retrieval/bm25_bootstrap_intervals.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/bm25_bootstrap_intervals.csv)

- [outputs/retrieval/bm25_manifest.json](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/bm25_manifest.json)

- [outputs/retrieval/bm25_metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/bm25_metrics.csv)

- [outputs/retrieval/bm25_per_query_metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/bm25_per_query_metrics.csv)

- [outputs/retrieval/bm25_rankings.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/bm25_rankings.csv)

- [outputs/retrieval/bm25_slices.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/bm25_slices.csv)

- [outputs/retrieval/context_repair/compatibility_repaired.csv.gz](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/context_repair/compatibility_repaired.csv.gz)

- [outputs/retrieval/context_repair/content_repaired.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/context_repair/content_repaired.csv)

- [outputs/retrieval/context_repair/context_audit.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/context_repair/context_audit.csv)

- [outputs/retrieval/context_repair/extraction_changes.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/context_repair/extraction_changes.csv)

- [outputs/retrieval/context_repair/interpretation.md](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/context_repair/interpretation.md)

- [outputs/retrieval/context_repair/manifest.json](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/context_repair/manifest.json)

- [outputs/retrieval/context_repair/metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/context_repair/metrics.csv)

- [outputs/retrieval/context_repair/paired_comparisons.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/context_repair/paired_comparisons.csv)

- [outputs/retrieval/context_repair/per_query_metrics.csv.gz](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/context_repair/per_query_metrics.csv.gz)

- [outputs/retrieval/context_repair/queries_repaired.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/context_repair/queries_repaired.csv)

- [outputs/retrieval/context_repair/ranking_changes.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/context_repair/ranking_changes.csv)

- [outputs/retrieval/context_repair/rankings.csv.gz](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/context_repair/rankings.csv.gz)

- [outputs/retrieval/context_repair/report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/context_repair/report.md)

- [outputs/retrieval/context_repair/slices.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/context_repair/slices.csv)

- [outputs/retrieval/failure_analysis/category_coverage.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/failure_analysis/category_coverage.csv)

- [outputs/retrieval/failure_analysis/phase10_manifest.json](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/failure_analysis/phase10_manifest.json)

- [outputs/retrieval/failure_analysis/review_cases.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/failure_analysis/review_cases.csv)

- [outputs/retrieval/failure_analysis/review_cases.md](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/failure_analysis/review_cases.md)

- [outputs/retrieval/failure_analysis/review_evidence.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/failure_analysis/review_evidence.csv)

- [outputs/retrieval/intent_signed_boost/configurations.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/intent_signed_boost/configurations.csv)

- [outputs/retrieval/intent_signed_boost/feature_audit.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/intent_signed_boost/feature_audit.csv)

- [outputs/retrieval/intent_signed_boost/manifest.json](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/intent_signed_boost/manifest.json)

- [outputs/retrieval/intent_signed_boost/metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/intent_signed_boost/metrics.csv)

- [outputs/retrieval/intent_signed_boost/paired_comparisons.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/intent_signed_boost/paired_comparisons.csv)

- [outputs/retrieval/intent_signed_boost/per_query_metrics.csv.gz](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/intent_signed_boost/per_query_metrics.csv.gz)

- [outputs/retrieval/intent_signed_boost/rankings.csv.gz](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/intent_signed_boost/rankings.csv.gz)

- [outputs/retrieval/intent_signed_boost/report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/intent_signed_boost/report.md)

- [outputs/retrieval/intent_signed_boost/slices.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/intent_signed_boost/slices.csv)

- [outputs/retrieval/intent_signed_boost/validation_grid.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/intent_signed_boost/validation_grid.csv)

- [outputs/retrieval/phase11/ablation_slices.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/phase11/ablation_slices.csv)

- [outputs/retrieval/phase11/ablations.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/phase11/ablations.csv)

- [outputs/retrieval/phase11/manifest.json](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/phase11/manifest.json)

- [outputs/retrieval/phase11/metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/phase11/metrics.csv)

- [outputs/retrieval/phase11/per_query_metrics.csv.gz](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/phase11/per_query_metrics.csv.gz)

- [outputs/retrieval/phase11/rankings.csv.gz](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/phase11/rankings.csv.gz)

- [outputs/retrieval/phase11/report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/phase11/report.md)

- [outputs/retrieval/phase11/slices.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/phase11/slices.csv)

- [outputs/retrieval/phase11/validation_selection.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/phase11/validation_selection.csv)

- [outputs/retrieval/repaired_signed_boost/configurations.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/repaired_signed_boost/configurations.csv)

- [outputs/retrieval/repaired_signed_boost/feature_audit.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/repaired_signed_boost/feature_audit.csv)

- [outputs/retrieval/repaired_signed_boost/legacy_signed_metric_comparison.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/repaired_signed_boost/legacy_signed_metric_comparison.csv)

- [outputs/retrieval/repaired_signed_boost/legacy_signed_ranking_comparison.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/repaired_signed_boost/legacy_signed_ranking_comparison.csv)

- [outputs/retrieval/repaired_signed_boost/manifest.json](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/repaired_signed_boost/manifest.json)

- [outputs/retrieval/repaired_signed_boost/metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/repaired_signed_boost/metrics.csv)

- [outputs/retrieval/repaired_signed_boost/paired_comparisons.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/repaired_signed_boost/paired_comparisons.csv)

- [outputs/retrieval/repaired_signed_boost/per_query_metrics.csv.gz](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/repaired_signed_boost/per_query_metrics.csv.gz)

- [outputs/retrieval/repaired_signed_boost/rankings.csv.gz](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/repaired_signed_boost/rankings.csv.gz)

- [outputs/retrieval/repaired_signed_boost/report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/repaired_signed_boost/report.md)

- [outputs/retrieval/repaired_signed_boost/slices.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/repaired_signed_boost/slices.csv)

- [outputs/retrieval/repaired_signed_boost/validation_grid.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/repaired_signed_boost/validation_grid.csv)

- [outputs/retrieval/signed_boost/configurations.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/signed_boost/configurations.csv)

- [outputs/retrieval/signed_boost/feature_audit.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/signed_boost/feature_audit.csv)

- [outputs/retrieval/signed_boost/manifest.json](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/signed_boost/manifest.json)

- [outputs/retrieval/signed_boost/metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/signed_boost/metrics.csv)

- [outputs/retrieval/signed_boost/paired_comparisons.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/signed_boost/paired_comparisons.csv)

- [outputs/retrieval/signed_boost/per_query_metrics.csv.gz](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/signed_boost/per_query_metrics.csv.gz)

- [outputs/retrieval/signed_boost/rankings.csv.gz](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/signed_boost/rankings.csv.gz)

- [outputs/retrieval/signed_boost/report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/signed_boost/report.md)

- [outputs/retrieval/signed_boost/slices.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/signed_boost/slices.csv)

- [outputs/retrieval/signed_boost/validation_grid.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/signed_boost/validation_grid.csv)

- [outputs/retrieval/topic_boost/configurations.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/topic_boost/configurations.csv)

- [outputs/retrieval/topic_boost/manifest.json](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/topic_boost/manifest.json)

- [outputs/retrieval/topic_boost/metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/topic_boost/metrics.csv)

- [outputs/retrieval/topic_boost/paired_comparisons.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/topic_boost/paired_comparisons.csv)

- [outputs/retrieval/topic_boost/per_query_metrics.csv.gz](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/topic_boost/per_query_metrics.csv.gz)

- [outputs/retrieval/topic_boost/ranking_changes.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/topic_boost/ranking_changes.csv)

- [outputs/retrieval/topic_boost/rankings.csv.gz](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/topic_boost/rankings.csv.gz)

- [outputs/retrieval/topic_boost/report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/topic_boost/report.md)

- [outputs/retrieval/topic_boost/slices.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/topic_boost/slices.csv)

- [outputs/retrieval/topic_boost/validation_grid.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/topic_boost/validation_grid.csv)

- [outputs/retrieval/value_aware_retrieval/configurations.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/value_aware_retrieval/configurations.csv)

- [outputs/retrieval/value_aware_retrieval/feature_audit.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/value_aware_retrieval/feature_audit.csv)

- [outputs/retrieval/value_aware_retrieval/feature_changes.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/value_aware_retrieval/feature_changes.csv)

- [outputs/retrieval/value_aware_retrieval/manifest.json](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/value_aware_retrieval/manifest.json)

- [outputs/retrieval/value_aware_retrieval/metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/value_aware_retrieval/metrics.csv)

- [outputs/retrieval/value_aware_retrieval/paired_comparisons.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/value_aware_retrieval/paired_comparisons.csv)

- [outputs/retrieval/value_aware_retrieval/per_query_metrics.csv.gz](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/value_aware_retrieval/per_query_metrics.csv.gz)

- [outputs/retrieval/value_aware_retrieval/rankings.csv.gz](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/value_aware_retrieval/rankings.csv.gz)

- [outputs/retrieval/value_aware_retrieval/report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/value_aware_retrieval/report.md)

- [outputs/retrieval/value_aware_retrieval/slices.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/value_aware_retrieval/slices.csv)

- [outputs/retrieval/value_aware_retrieval/validation_grid.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/retrieval/value_aware_retrieval/validation_grid.csv)

- [outputs/schema/phase15_candidate_slot_profile.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/schema/phase15_candidate_slot_profile.csv)

- [outputs/schema/phase15_extended_query_schema.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/schema/phase15_extended_query_schema.csv)

- [outputs/schema/phase15_extended_query_schema.md](/Users/hol/Documents/Task/doctor-search-service/outputs/schema/phase15_extended_query_schema.md)

- [outputs/schema/phase16_contextual_extraction.md](/Users/hol/Documents/Task/doctor-search-service/outputs/schema/phase16_contextual_extraction.md)

- [outputs/schema/phase16_extraction_examples.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/schema/phase16_extraction_examples.csv)

- [outputs/schema/phase16_extraction_quality_review.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/schema/phase16_extraction_quality_review.csv)

- [outputs/schema/phase16_extraction_summary.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/schema/phase16_extraction_summary.csv)

- [outputs/taxonomy/phase2_cluster_model_comparison.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_cluster_model_comparison.csv)

- [outputs/taxonomy/phase2_completion_checklist.md](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_completion_checklist.md)

- [outputs/taxonomy/phase2_cross_class_neighbors.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_cross_class_neighbors.csv)

- [outputs/taxonomy/phase2_final_taxonomy.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_final_taxonomy.csv)

- [outputs/taxonomy/phase2_liang_branch_metrics.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_liang_branch_metrics.csv)

- [outputs/taxonomy/phase2_liang_hybrid_assignments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_liang_hybrid_assignments.csv)

- [outputs/taxonomy/phase2_liang_methodology.json](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_liang_methodology.json)

- [outputs/taxonomy/phase2_liang_model_disagreements.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_liang_model_disagreements.csv)

- [outputs/taxonomy/phase2_liang_training_history.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_liang_training_history.csv)

- [outputs/taxonomy/phase2_low_margin_review.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_low_margin_review.csv)

- [outputs/taxonomy/phase2_manifest.json](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_manifest.json)

- [outputs/taxonomy/phase2_manual_clinical_review.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_manual_clinical_review.csv)

- [outputs/taxonomy/phase2_nlp_taxonomy_analysis.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_nlp_taxonomy_analysis.csv)

- [outputs/taxonomy/phase2_prototype_assignments.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_prototype_assignments.csv)

- [outputs/taxonomy/phase2_seed_taxonomy.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_seed_taxonomy.csv)

- [outputs/taxonomy/phase2_seed_to_final_derivation.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_seed_to_final_derivation.csv)

- [outputs/taxonomy/phase2_structured_feature_profiles.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_structured_feature_profiles.csv)

- [outputs/taxonomy/phase2_structured_query_features.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_structured_query_features.csv)

- [outputs/taxonomy/phase2_taxonomy_decisions.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_taxonomy_decisions.csv)

- [outputs/taxonomy/phase2_taxonomy_report.md](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_taxonomy_report.md)

- [outputs/taxonomy/phase2_tfidf_explanations.csv](/Users/hol/Documents/Task/doctor-search-service/outputs/taxonomy/phase2_tfidf_explanations.csv)
