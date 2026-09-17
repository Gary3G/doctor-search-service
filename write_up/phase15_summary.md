# Phase 15 — CPU-Friendly Learned Reranker

## Approach

Phase 15 evaluates the optional CPU-friendly extension from the project plan. The frozen dense-retrieval option was already implemented in Phase 11, so this phase tests the remaining option: a lightweight learned reranker. The comparator is the deployable Phase 12 runtime system, `with_predicted_hard_intent`.

The experiment uses 55 title- and metadata-level features: normalized BM25, frozen dense similarity, predicted-intent compatibility, the frozen Phase 12 score, individual entity and contextual compatibility fields, four conjunction interactions, content-type indicators, publication year, word count, and language compatibility. It trains 19 regularized logistic candidates: 12 pointwise binary models over `relevance_grade >= 1` and seven within-query pairwise models over ordered relevance grades.

All model fitting uses only the 4,235 temporal-train judgments: 866 positive and 3,369 nonpositive observations across 340 queries. Candidate selection uses only temporal-validation NDCG@10. The temporal-test judgments are evaluated only for the selected challenger. Query and query-deduplicated protocols are not reported because their assignments are incompatible with a model trained on the temporal split.

## Retrieval Results

Validation selected the class-balanced pointwise logistic model with `C=0.01`.

| Split | System | NDCG@10 | Recall@10 | MRR@10 | Judged fraction@10 |
| --- | --- | ---: | ---: | ---: | ---: |
| Validation | Frozen Phase 12 | 0.03146 | 0.05118 | 0.03150 | 0.03022 |
| Validation | Learned reranker | 0.03363 | 0.06491 | 0.03827 | 0.04245 |
| Test | Frozen Phase 12 | 0.01851 | 0.04346 | 0.02766 | 0.03165 |
| Test | Learned reranker | 0.01653 | 0.03153 | 0.03004 | 0.03597 |

The validation NDCG@10 change is **+0.00217**, with a paired 95% bootstrap interval of **[-0.01101, +0.01422]**. Nine eligible validation queries improve, six worsen, and 98 are unchanged.

The temporal-test NDCG@10 change is **-0.00198**, with a paired 95% bootstrap interval of **[-0.01586, +0.01111]**. Seven eligible test queries improve, seven worsen, and 96 are unchanged. Test Recall@10 falls by 0.01193, while MRR@10 rises by 0.00237. The stronger-grade diagnostic (`relevance_grade >= 2`) moves NDCG@10 from 0.01774 to 0.01894, but this is an alternate post-selection view and does not reverse the primary result.

The answer to the Phase 15 question is therefore **no demonstrated improvement**. The learned challenger has a small validation gain that is compatible with noise and does not generalize on the primary temporal-test metric. The frozen Phase 12 runtime ranker remains the preferred system.

A follow-up frozen multilingual cross-encoder experiment reaches validation/test NDCG@10 of 0.02723/0.01545 and is also not selected. A biomedical MedCPT retry improves on that challenger at 0.03027/0.01755, but remains below Phase 12 at 0.03146/0.01851. Replacing the multilingual dense embedding with S-PubMedBERT likewise lowers the complete hybrid to 0.02869/0.01488, so validation retains PubMedBERT weight zero. The consolidated embedding and reranker decision is recorded in `write_up/phase16_summary.md`.

## What the Model Learned

The largest standardized coefficients are content type, word count, query context count, and several conflict or hierarchy fields. Some directions are clinically implausible: review content and disease-hierarchy matches receive negative coefficients, while recency conflict and structured conflict receive positive coefficients. Dense similarity conditioned on entity coverage is also negative. These signs are evidence that the model is learning exposure and engagement regularities from the observed sample rather than a stable clinical relevance function.

The learned ranker increases the fraction of judged results at rank 10 on both validation and test. That can make offline behavioral metrics easier to improve because exposed content is more likely to carry a judgment, but it is not evidence of better clinical answers. The lack of a reliable primary test gain reinforces the decision not to deploy the learned model.

## Honest Evaluation

This is a pointwise/pairwise learning experiment over sparse behavioral proxies, not a clinician-adjudicated learning-to-rank study. Grade zero means exposed without observed engagement; it is not proof of irrelevance. Unexposed pairs have no training label, and the logged candidate set inherits position and exposure bias. The model does not use impression position as a feature, but that does not remove bias from its targets.

The pointwise loss does not directly optimize NDCG. Pairwise logistic candidates provide an objective-level sensitivity check, but none beats the pointwise winner on validation. Nineteen candidates are compared on only 113 positive-query validation cases, so model-selection variance is substantial. The paired validation interval includes zero.

The test split was inspected in earlier project phases, so the result is descriptive rather than pristine confirmation. Titles and metadata also cannot determine whether an article body fully and correctly answers a clinical question. Content-type and word-count effects are especially vulnerable to source and exposure shortcuts.

## Decision and Next Step

Do not replace the Phase 12 ranker with the Phase 15 learned model. Further tuning on the same behavior labels would increase researcher degrees of freedom without repairing the evaluation target. The next meaningful experiment should first obtain blinded pooled relevance judgments from qualified clinical reviewers, then train and test a group-aware reranker on a genuinely untouched temporal split. Full-text section retrieval and conjunction-aware features should be added only after that evaluation foundation exists.

Artifacts are under `outputs/retrieval/phase15/`: `validation_grid.csv`, `configurations.csv`, `rankings.csv.gz`, `metrics.csv`, `per_query_metrics.csv.gz`, `paired_comparisons.csv`, `feature_coefficients.csv`, `training_summary.csv`, `selected_model.joblib`, and `manifest.json`.
