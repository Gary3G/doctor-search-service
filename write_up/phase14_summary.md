# Phase 14 — Detailed Failure Analysis

## Approach

Phase 14 reviews 12 representative residual errors from the frozen Phase 12 runtime ranker (`with_predicted_hard_intent`). Every case is an eligible temporal-test query with zero behavior-derived Recall@10. The sample is purposive rather than random: it covers constrained dosing, multi-drug interactions, comparison, pregnancy, monitoring, low-confidence intent errors, corpus gaps, and evaluation-label failures. No retrieval score, model weight, label, or test judgment is changed.

For every case, the generated report records the query, an expected answer requirement and closest title-level candidate, the top three retrieved titles, structured query decomposition, a case-specific failure explanation, and a proposed improvement. The evidence table preserves whether each item is behaviorally judged or unjudged and records its final-system rank. “Expected” means plausible from title and metadata; it is not a new relevance label.

**Where an LLM was used:** An LLM-assisted process produced the 12 qualitative reviews from query text, supplied entities and slots, predicted intent, content titles and metadata, and behavior-derived judgments. This semantic review identified whether a miss was more consistent with ranking logic, corpus coverage, intent classification, or the evaluation proxy. The saved annotations are in `data/processed/phase14_failure_reviews.csv`.

**Where an LLM was not used:** Case validation, evidence joins, rank lookup, decomposition serialization, category aggregation, artifact generation, and provenance hashing are deterministic. Rerunning `.venv/bin/python -m src.final_failure_analysis` makes no LLM calls and reproduces the saved review rather than independently regenerating its judgments.

## Key Findings

Across the complete retrieval experiment, useful signals were present but the evidence does not support claiming a broadly effective clinical search engine. Plain BM25 reached test NDCG@10 of **0.01021**. Dense retrieval improved this to **0.01584**, and plain hybrid retrieval reached **0.01651**. Adding entity and context structure to BM25 increased test NDCG@10 to **0.01477**, showing that structured evidence can help lexical retrieval. The deployable hybrid system with predicted hard intent reached **0.01851**, compared with **0.01105** without intent. Assisted reference intent reached **0.01940**, but this is a ceiling diagnostic rather than a deployable result.

The gains were concentrated rather than global. Predicted intent agreed with the assisted intent on **85.8%** of all queries and was most useful for interaction, dosing, and some safety queries. Most eligible test-query rankings did not change. The paired interval for the predicted-intent improvement included zero, and structure did not improve monotonically as contextual complexity increased. The supported conclusion is therefore that structure and intent are useful for particular information needs, not that either universally improves retrieval.

The recurring residual problem is conjunction failure, not one globally wrong component. Ten of the 12 reviewed cases have no title that explicitly satisfies every requested entity, intent, and contextual constraint. This is both a corpus/indexing limitation and a ranking challenge: the system often chooses either the right context template with the wrong molecule or the right entities with the wrong information need.

Category counts overlap and describe only this purposive sample:

| Failure pattern | Reviewed queries |
| --- | ---: |
| Corpus/title coverage gap | 10 |
| Low-confidence intent error | 4 |
| Context template outranks entity compatibility | 3 |
| Intent template mismatch | 2 |
| Multi-entity conjunction failure | 2 |
| Wrong-molecule ranking | 2 |
| Weak behavioral ground truth | 2 |

Representative examples:

| Query | Remaining failure | Most credible improvement |
| --- | --- | --- |
| Q019: renal dose adjustment of bortezomib | Ten renal-dose articles for other molecules precede the closest bortezomib/rheumatoid-arthritis item at rank 11 | Gate context boosts on exact molecule and disease coverage; index article sections |
| Q051: add-on therapy after dolutegravir failure | Hard intent changes from Treatment Change to Efficacy at a 0.004 margin; no title covers post-failure therapy | Confidence-gated intent plus explicit prior-failure evidence |
| Q101: dolutegravir–tenofovir interaction | The ranker matches each drug or disease independently but not the pairwise interaction | Per-value entity coverage and pairwise interaction features |
| Q146: bedaquiline vs rifampicin | Safety titles outrank a class-level efficacy item; no direct comparison title exists | Require both comparator values and comparison/efficacy evidence |
| Q224: hepatic losartan dosing | Eight dose-adjustment templates for other drugs outrank the exact losartan/hypertension item at rank 9 | Conjunction-aware reranking and full-text dose-section retrieval |
| Q409: spironolactone dosing in heart failure | The only spironolactone/heart-failure title is rank 20; generic dosing templates dominate | Exact entity prerequisites before generic intent boosts |

Two cases demonstrate why a proxy miss is not automatically a clinical ranking failure. For Q180, exact-looking 2023 type-1-diabetes guideline titles are ranks 1 and 2 but are unjudged; the only behavior-positive item is an off-topic colorectal-cancer review. For Q393, assisted intent moves a behavior-positive monitoring article to rank 10, but that article concerns CNS stimulants in breast cancer rather than SSRIs in ADHD. Optimizing either case toward the logged positive would make the apparent metric better without a credible clinical improvement.

The most surprising result was how often a more defensible representation produced a worse behavior-derived metric. Dense retrieval was stronger than BM25 alone but showed little incremental value inside the full combination. Entity features helped the BM25 branch but sometimes hurt hybrid retrieval. Removing content-type shortcuts that treated `drug_profile` as dosing evidence or `review` as comparison evidence made the features more credible, yet reduced the proxy score. Hard intent also outperformed probability-weighted intent even though preserving uncertainty appeared conceptually safer. These reversals suggest that the metric frequently rewards exposure and content-template correlations rather than answer-level clinical relevance.

Another surprise was the gap between intent classification and retrieval impact. Row-stratified intent Macro F1 was **0.970**, while template-held-out Macro F1 fell to **0.842**. Even with strong aggregate intent replication, predicted intent changed relatively few rankings. Every supplied test query also had both disease and drug metadata, which made several planned entity-complexity comparisons impossible to identify.

## Honest Evaluation

This is a single LLM-assisted review of titles and supplied metadata, not clinician adjudication. Article body text is unavailable, so a title-level gap does not prove the content body lacks the answer. Conversely, a broadly matching title does not prove clinical relevance. The expected candidates are inspection aids and are not written back into the relevance labels.

The 12 fixed cases were deliberately chosen for interpretability and coverage; category counts are not population prevalence estimates. All cases come from a test set inspected in earlier phases, and Phase 14 is diagnostic rather than confirmatory. Behavior-derived relevance remains sparse and biased by exposure and engagement. Unjudged content receives zero computational gain but is not known to be irrelevant.

The evaluation target is the largest weakness. A click, long dwell, bookmark, or return visit is evidence of engagement, not proof that an article correctly and completely answers a clinical question. Position and exposure determine which documents can receive that signal. Some exact-looking matches were never judged, while visibly off-topic documents received positive grades. Absolute retrieval scores and system comparisons must therefore be interpreted as performance against a logging proxy, not clinical utility.

The ranking formula also treats evidence too additively. Disease, molecule, context, and intent scores can compensate for one another even when a clinical constraint should be mandatory. This is why renal- or hepatic-dose templates for the wrong molecule can outrank weaker but entity-correct candidates. Multi-drug interactions and comparisons are especially vulnerable because matching either molecule can contribute credit without satisfying the requested pairwise relationship.

Title-only retrieval compounds this problem. Renal thresholds, pregnancy precautions, monitoring parameters, contraindications, and dose adjustments commonly occur in article sections rather than titles. When the exact conjunction is absent from titles, weight tuning alone cannot recover the needed evidence. Some contextual features were also based on coarse content-type proxies, and supplied entity metadata occasionally introduced concepts not stated in the query.

The intent result is not a clean end-to-end estimate for unseen queries. The classifier reproduces an assisted weak-label policy rather than independently adjudicated clinical intent. Its split was not aligned with the temporal retrieval split, and 97 of the 139 temporal-test query IDs were included when the final intent model was refitted. Retrieval relevance labels were not used to train that classifier, but the overlap still creates leakage risk if the result is interpreted as unseen-query performance. Hard intent can also affect ranking when the top-two probability margin is extremely small.

Finally, the corpus itself limits what the system can demonstrate. Several queries request combinations for which no title-level answer exists, and the data contain repeated templates, duplicated self-comparisons, and clinically questionable disease–drug pairings. In such cases, the system is being scored on choosing among inadequate candidates rather than retrieving a complete answer.

Three Phase 14 tests enforce the frozen temporal-test miss set, evidence semantics for Q180, and assisted-versus-runtime intent ranks for Q393. These tests establish reproducibility and prevent silent evidence drift; they do not validate the clinical judgments.

## What I Would Do Differently

1. **Fix evaluation before further tuning.** I would obtain blinded judgments from at least two clinically qualified reviewers over pooled top results from all major systems. The rubric would separately score topical relevance, answer completeness, clinical usefulness, and harmful mismatch. Disagreements would be adjudicated, and unjudged documents would remain distinct from irrelevant ones.
2. **Use a genuinely untouched, shared end-to-end split.** Intent labels and models, retrieval features, relevance judgments, and tuning would use aligned temporal boundaries. Near-duplicate query templates would remain in the same partition, and intent predictions used for offline evaluation would be out of fold.
3. **Index full text at section or passage level.** Dosing, pregnancy, monitoring, interaction, and contraindication evidence should be retrieved from the section where it appears instead of inferred from title or content type.
4. **Make scoring conjunction-aware.** I would add per-value molecule coverage, required disease compatibility, comparator-pair and interaction-pair coverage, and value-specific clinical-context compatibility. Strong context or intent boosts would apply only after required entity constraints are satisfied.
5. **Use calibrated intent confidence.** Low-margin or out-of-distribution predictions would fall back to the no-intent ranker or a conservative multi-intent mixture rather than forcing a hard class.
6. **Add abstention and corpus-gap handling.** When no candidate covers the required entities and constraints, the system should say that matching evidence is insufficient rather than presenting a wrong-molecule template as an answer.
7. **Evaluate realistic edge cases deliberately.** I would collect more queries with no recognized entities, one entity, disease-only and drug-only requests, multi-molecule comparisons, numeric renal/lab constraints, and multiple simultaneous constraints so the planned slice hypotheses are actually testable.

Artifacts are under `outputs/retrieval/phase14/`: `failure_cases.csv`, `failure_evidence.csv`, `category_coverage.csv`, `failure_cases.md`, and `manifest.json`.
