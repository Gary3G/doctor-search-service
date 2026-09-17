# Phase 12 — Connecting Intent to Retrieval

## Approach

Phase 12 tests whether query intent improves retrieval when intent comes from a runtime classifier rather than being supplied as a reference label. It starts from Phase 11 R-E6, the fixed equal mean of normalized BM25, frozen dense similarity, entity coverage, and contextual coverage. These four components are not retuned.

The experiment compares three intent inputs:

1. **Assisted intent:** the Phase 3 `intent` label, used only as a reference-label ceiling diagnostic. It comes from the ordered bilingual annotation policy supported by semantic prototypes and query clusters; it is not an independent clinician label.
2. **Predicted hard intent:** the argmax prediction from the saved Phase 5 T1-E4 classifier, which combines a frozen multilingual query embedding with entity and contextual features. This is the primary runtime-oriented configuration.
3. **Predicted soft intent:** the classifier's probability mass over every intent compatible with a content type. This diagnostic tests whether preserving classifier uncertainty is more robust than using a single hard class.

All three inputs use the same Phase 7.5 mapping from intent to compatible content types. The ranking formula is:

`score = R-E6 + epsilon × intent_compatibility`

The intent coefficient `epsilon` is selected using temporal validation NDCG@10 from `{0, 0.025, 0.05, 0.10, 0.20, 0.25, 0.50, 1.00}`. Exact validation ties select the smaller coefficient. Test judgments are evaluated only after selection within this phase, although the test set had already been inspected in earlier project phases and is therefore descriptive rather than pristine.

Validation selected `epsilon=0.25` for assisted intent, `epsilon=0.25` for predicted hard intent, and `epsilon=0.025` for predicted soft intent. The assisted configuration at `epsilon=0.25` is rank-equivalent to Phase 11 R-E7:

`mean(BM25, dense, entity, context) + 0.25 × intent`

differs from the R-E7 five-signal mean only by a positive constant multiplier. The implementation verifies that both configurations produce exactly the same top-20 rankings.

The primary analysis uses temporal behavior-derived judgments with `relevance_grade >= 1`. Query-held-out and query-deduplicated protocols, alternative relevance grades, paired query bootstraps, and per-intent slices are retained as sensitivity analyses. No behavioral relevance label is used to construct the ranking features.

## Key Findings

The classifier's hard intent prediction agrees with the assisted Phase 3 label on **85.8% of all 500 queries**. It preserves most of the retrieval benefit observed with assisted intent, while the probability-weighted variant receives a much smaller validation-selected weight and barely changes test rankings.

| Configuration | Validation NDCG@10 | Test NDCG@10 | Test Recall@10 | Test Hit Rate@10 | Test MRR@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| R-E6 without intent | 0.02727 | 0.01105 | 0.02063 | 0.06364 | 0.02091 |
| Predicted soft intent | 0.03084 | 0.01115 | 0.02063 | 0.06364 | 0.02136 |
| Predicted hard intent | **0.03146** | 0.01851 | 0.04346 | 0.10000 | 0.02766 |
| Assisted intent / Phase 11 R-E7 | **0.03146** | **0.01940** | **0.04801** | **0.10909** | **0.02857** |

Relative to R-E6 without intent, predicted hard intent increases test NDCG@10 by **0.00746**. Its paired 95% query-bootstrap interval is **[-0.00034, 0.01763]**: 8 eligible queries improve, 2 worsen, and 100 are unchanged. The point estimate is positive, but the interval includes zero, so this is not evidence of a global improvement.

Directly comparing predicted hard intent with assisted intent, test NDCG@10 is lower by **0.00089**, with a paired interval of **[-0.00266, 0]**. Of 110 eligible test queries, 109 have identical NDCG@10 and one is worse with predicted intent. Intent-classification errors therefore have a small aggregate retrieval effect in this test set, but they do remove part of the reference-label gain.

The predicted-hard effect is concentrated in specific intents:

| Assisted intent slice | Eligible queries | R-E6 NDCG@10 | Predicted-intent NDCG@10 | Delta |
| --- | ---: | ---: | ---: | ---: |
| Interaction / Combination | 6 | 0.00387 | 0.06809 | +0.06422 |
| Dosing / Administration | 22 | 0.00789 | 0.02601 | +0.01812 |
| Management / Treatment Selection | 13 | 0.01174 | 0.01851 | +0.00677 |
| Safety / Contraindication | 15 | 0.00341 | 0.00881 | +0.00540 |
| Treatment Change / Escalation | 14 | 0.03276 | 0.02334 | -0.00942 |

The remaining intent slices have no NDCG@10 change. The supported conclusion is therefore **intent-specific rather than global**. Hard predicted intent is the primary runtime result because it has the strongest validation score. Soft compatibility is not promoted: validation selects only `epsilon=0.025`, and test NDCG@10 rises by just 0.00010 from the no-intent baseline.

## Honest Evaluation

This phase improves on R-E7 by connecting an actual saved intent classifier to ranking instead of assuming that a reference intent label is available at request time. It also clearly separates the deployable prediction path from the assisted-label diagnostic. Nevertheless, it is still an offline research experiment rather than a clean end-to-end production estimate.

The largest limitation is split alignment. Intent classification was evaluated with row-stratified and template-grouped cross-validation, not a temporal split. The saved T1-E4 model used by Phase 12 was then refitted on all 362 retained Phase 3 weak-label queries. Of the 139 queries in the temporal retrieval test set, **97 were included in that intent-model refit** and 42 were unseen. Thus, many Phase 12 intent predictions are in-sample at the query level even though retrieval relevance labels were never used to train the classifier. This creates a **medium overall leakage risk** for the predicted-intent experiment and a high risk if the result is interpreted as unseen-query performance.

The retrieval temporal split also separates behavioral events rather than query identities. Fifty-six query IDs occur in both temporal retrieval train and test, 30 occur in both validation and test, and 19 occur in all three partitions. This is defensible for evaluating future interactions from recurring production traffic, but it does not measure performance exclusively on new information needs. Query-held-out and deduplicated results are useful sensitivity checks, not substitutes for an end-to-end split shared by every component.

The intent targets themselves are weak references. Phase 3 uses an ordered bilingual rule policy supported by prototype and cluster signals; only 180 queries belong to the model-assisted reviewed subset, and none were independently labeled by multiple clinicians. The Phase 5 classifier consequently measures replication of that policy. Its row-stratified Macro F1 is 0.970, while the more realistic template-held-out Macro F1 is 0.842. Neither score establishes clinical intent accuracy.

The relevance target is also incomplete and biased. NDCG is derived from impressions and engagement, so it reflects exposure, rank position, clicks, dwell time, bookmarks, and repeated use rather than clinician-adjudicated clinical relevance. Unjudged content receives zero computational gain but is not known to be irrelevant. Absolute metric values are low, improvements are concentrated in a few queries, bootstrap intervals are not corrected for multiple comparisons, and earlier phases repeatedly inspected the test set.

Intent compatibility is a coarse content-type prior. It cannot determine whether a specific article section actually answers a dosing, guideline, safety, or comparison question. Binary compatibility can demote useful content whose broad type is not on the allow-list. Probability-weighted compatibility reduces the discontinuity but did not produce a meaningful global gain here.

Finally, the Phase 12 runner is batch-oriented. It depends on labeled-query files, cached embeddings, and a precomputed query-content matrix for the fixed 500-query corpus. It is not an online service for arbitrary new queries. The saved Phase 5 estimator was serialized under scikit-learn 1.5.2 and emits compatibility warnings under the current 1.9.1 environment. Inference and Phase 11 parity checks pass, but exact-version reproduction or model regeneration is required before deployment.

## What I Would Do Differently

I would evaluate the full pipeline with a shared nested split. First, I would establish temporal train, validation, and test cutoffs for all data sources. Within the historical training period, I would keep near-duplicate query templates in the same intent-classification fold. The intent classifier would be trained only from labels available before the cutoff, then frozen before producing validation and future-test predictions. This would preserve both temporal integrity and unseen-template evaluation.

For existing labeled queries used during development, I would generate out-of-fold intent probabilities rather than predictions from a model refitted on those same queries. A final classifier could still be trained on all historical labels for deployment, but its offline evaluation would remain strictly out of sample. I would report separate slices for recurring queries, unseen query IDs, unseen templates, languages, low-confidence predictions, and each intent.

I would replace the weak intent reference set with independent annotations from at least two clinically qualified reviewers. Disagreements would be adjudicated by a third reviewer, with inter-annotator agreement and per-intent confusion reported. The retrieval test set would likewise receive a small, stratified set of clinician relevance judgments so improvements could be checked against clinical usefulness rather than engagement alone.

I would learn or tune a graded intent-content compatibility table on training and validation data instead of using a binary allow-list. Mixed-intent queries should be represented explicitly, and calibrated intent probabilities should control how strongly intent affects ranking. Low-confidence or out-of-distribution predictions should fall back to the no-intent retriever rather than forcing one of the 11 classes.

For production, I would separate evaluation from online inference. Content BM25 statistics and dense embeddings would be built offline and versioned. At request time, the service would normalize the raw query, extract entities and contextual slots, compute the query embedding, predict intent, calculate dynamic compatibility against the content index, and apply the frozen ranker. Models and indices would be loaded once at startup, with latency, concurrency, timeouts, feature availability, index freshness, drift, and fallback behavior monitored. Periodic manual labeling would remain necessary for auditing and retraining, but ordinary requests would not require manual intent labels.

The reproducible artifacts are stored under `outputs/retrieval/phase12/`: `validation_grid.csv`, `configurations.csv`, `rankings.csv.gz`, `metrics.csv`, `per_query_metrics.csv.gz`, `paired_comparisons.csv`, `intent_slices.csv`, `intent_predictions.csv`, and `manifest.json`.
