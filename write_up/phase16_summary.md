# Phase 16 — Embedding and Reranker Model Selection

## Approach

Phase 16 consolidates the Phase 15 model comparisons into a final embedding and reranker selection. Every challenger starts from the frozen Phase 12 runtime ranker, and selection is based on temporal-validation NDCG@10 before descriptive inspection of temporal-test performance.

For dense retrieval, `pritamdeka/S-PubMedBert-MS-MARCO` was evaluated as both a complete replacement for `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` and as a blended dense signal at PubMedBERT weights 0, 0.25, 0.50, 0.75, and 1.00. BM25, entity coverage, contextual coverage, predicted intent, and the validated intent coefficient were held fixed. Dense-only rankings were retained as diagnostics.

For reranking, three approaches were compared with the same Phase 12 baseline: a project-trained logistic reranker, the frozen multilingual `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, and the frozen biomedical `ncbi/MedCPT-Cross-Encoder`. Cross-encoder candidate depth and blend weight were selected only on validation. All models were evaluated with the same primary behavior-derived relevance grade and temporal split.

## Key Findings

| System | Validation NDCG@10 | Test NDCG@10 | Selection outcome |
| --- | ---: | ---: | --- |
| Frozen Phase 12 baseline | 0.03146 | **0.01851** | Retained |
| Learned logistic reranker | **0.03363** | 0.01653 | Rejected: validation gain did not generalize |
| Multilingual cross-encoder | 0.02723 | 0.01545 | Rejected |
| MedCPT cross-encoder | 0.03027 | 0.01755 | Rejected |
| Full S-PubMedBERT embedding replacement | 0.02869 | 0.01488 | Rejected |

Validation selected PubMedBERT weight zero. Weights 0.25 and 0.50 did not change the measured validation top 10, while larger weights reduced NDCG@10 and Recall@10. S-PubMedBERT dense-only produced a higher descriptive test NDCG@10 than multilingual MiniLM dense-only (0.02146 versus 0.01584), but it was substantially worse on validation (0.01773 versus 0.03079), so the apparent test benefit was not stable enough for selection.

MedCPT was the strongest frozen cross-encoder challenger and transferred better than the general multilingual cross-encoder, but it still remained below Phase 12 on both validation and test. The learned logistic reranker was the only challenger to beat Phase 12 on validation, but its test NDCG@10 and Recall@10 declined. Phase 16 therefore selects the existing multilingual MiniLM as the dense embedding and selects no additional reranker. The deployable system remains the frozen Phase 12 hybrid ranker.

## Honest Evaluation

These results measure agreement with sparse behavioral proxies, not clinician-adjudicated clinical relevance. Only about three percent of returned top-10 items are judged, grade zero means exposure without observed engagement rather than proven irrelevance, and several observed positives are clinically off-topic. Large ranking changes can therefore remain invisible, while semantically plausible changes can be penalized.

The temporal test split was inspected during earlier phases, so its metrics are descriptive rather than pristine confirmation. The validation set is also small enough that model selection is unstable: most eligible queries are unchanged and paired intervals generally include zero. The learned reranker was trained on biased exposure data, while the frozen cross-encoders and embeddings were trained for objectives that do not exactly match short bilingual clinical-title retrieval.

The corpus exposes titles but not abstracts, article sections, or full text. This particularly limits MedCPT and PubMedBERT, whose biomedical training cannot recover evidence absent from a title. English-focused biomedical models also face distribution shift on Indonesian and mixed-language queries. Finally, S-PubMedBERT carries a CC BY-NC 2.0 license, which may independently prevent commercial deployment.

The selection should consequently be read as “no challenger demonstrated a reliable improvement under the available offline protocol,” not as proof that multilingual MiniLM or the Phase 12 ranker is clinically optimal.

## What You Would Do Differently

First, I would construct pooled relevance judgments from qualified clinical reviewers. Pools would combine lexical, multilingual dense, biomedical dense, and cross-encoder results, with assessors blinded to system identity. Judgments would explicitly distinguish entity correctness, clinical intent, contextual constraints, evidence quality, and overall usefulness.

Second, I would index abstracts or clinically meaningful passages instead of titles alone. Queries and documents would be represented asymmetrically where the model supports it, and candidate generation would preserve exact disease, molecule, and safety or dosing constraints. Hard negatives would match the disease and drug while violating exactly one requested constraint.

Third, I would reserve a genuinely untouched temporal test set and perform all architecture, blending, calibration, and threshold decisions on train and validation only. Evaluation would report confidence intervals, language slices, conjunction-complexity slices, and candidate-recall ceilings in addition to aggregate NDCG and Recall.

Finally, I would test a multilingual biomedical retrieval strategy rather than choosing between general multilingual and English biomedical representations. Practical options include late fusion, language-gated embeddings, or domain adaptation using reviewed bilingual query-document pairs. A reranker would be reconsidered only after candidate recall and label quality are strong enough for its additional capacity to be evaluated meaningfully.
