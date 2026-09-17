# Phase 11 — Retrieval Experiments, Findings, and Next Steps

## Executive Summary

Phase 11 evaluated sparse retrieval, dense retrieval, structured entity and context signals, intent compatibility, signed bonus/penalty scoring, repaired extraction, and value-aware handling of multi-value metadata. All primary results use the temporal split, the behavior-derived `relevance_grade >= 1` target, and NDCG@10 for validation selection.

The best prespecified configuration was **R-E7: hybrid + entities + context + intent**, with validation/test NDCG@10 of **0.03146 / 0.01940**. It improved test NDCG@10 by **0.00289**, test Recall@10 by **0.01273**, and test MRR@10 by **0.00553** over plain hybrid. The gain came mainly from intent and BM25. Entity evidence helped in some combinations; context was weak and unstable. Dense similarity did not demonstrate incremental value inside the full combination.

The later experiments did not establish a replacement for R-E7. The strongest exploratory test result was **0.02032** for the legacy signed-plus-intent setting, but validation selected a different setting, the test set had already been inspected, and the apparent advantage over R-E7 was only **0.00093**. It is recorded as a diagnostic result, not promoted as a new model.

The central failure is not simply poor weighting. Entity conflict is usually the complement of entity coverage, context evidence is sparse in titles, and the behavior labels contain exposure, position, and engagement bias. Several mathematically different formulas therefore produce the same ranking, while more aggressive penalties can demote useful broad content or reward artifacts of the logging process.

## Approach

### Evaluation design

- Corpus: **500 queries × 345 content items**, scored exhaustively.
- Retrieval text: **content title only** for both BM25 and dense similarity. Body text was unavailable.
- Sparse score: per-query min-max normalized BM25.
- Dense score: frozen multilingual MiniLM shifted cosine, `(cosine + 1) / 2`.
- Hybrid score: equal mean of normalized BM25 and dense scores.
- Structured signals: disease, molecule, drug class, therapeutic area, age, year, renal/hepatic cues, route and related context fields where available.
- Intent signal: compatibility between the assisted query-intent label and content category/type.
- Tie break: ascending `content_id`.
- Primary model selection: temporal validation NDCG@10. Test results are descriptive because the test split was examined repeatedly during follow-up experiments.

### Behavioral relevance labels

The metric gain is computed from behavior, not clinician-adjudicated clinical relevance:

| Grade | Observed behavior |
| ---: | --- |
| 3 | Bookmark, return, or scroll depth at least 150 |
| 2 | Deep scroll or click duration at least 10 seconds |
| 1 | Shorter click |
| 0 | Exposed without recorded engagement |
| unjudged | Not exposed in the logs |

The primary binary target treats grades 1–3 as relevant. NDCG also uses the graded gain. Unjudged documents contribute zero computational gain; that does **not** mean they are clinically irrelevant.

### CLEAR-inspired structure

The work used a CLEAR-style sequence: extract concepts, normalize them to ICD/ATC-compatible forms, augment hierarchical matches, apply structured compatibility, and isolate components through ablation. This helped make entity and context signals inspectable and reproducible. It was not a full implementation of CLEAR: there was no neural entity recognizer, external ontology service, learned reranker, or clinician-validated relevance set.

The clearest benefit was on the BM25 branch: test NDCG@10 rose from **0.01021** for BM25 to **0.01303** with entities and **0.01477** with entities plus context. The same structured signals did not transfer reliably to hybrid retrieval because they were correlated, coarse, and sometimes over-weighted.

## Experiment Results

### 1. Prespecified Phase 11 retrieval matrix

These eight configurations were selected and evaluated before the later diagnostic iterations.

| ID | Configuration | Validation NDCG@10 | Test NDCG@10 | Test Recall@10 | Test MRR@10 |
| --- | --- | ---: | ---: | ---: | ---: |
| R-B0 | BM25 | 0.02400 | 0.01021 | 0.01609 | 0.02016 |
| R-E1 | BM25 + entities | 0.02899 | 0.01303 | 0.02359 | 0.02379 |
| R-E2 | BM25 + entities + context | 0.02966 | 0.01477 | 0.03154 | 0.02389 |
| R-E3 | Dense | 0.03079 | 0.01584 | 0.02972 | 0.01735 |
| R-E4 | Hybrid | 0.02545 | 0.01651 | 0.03528 | 0.02304 |
| R-E5 | Hybrid + entities | 0.02467 | 0.01220 | 0.02177 | 0.02221 |
| R-E6 | Hybrid + entities + context | 0.02727 | 0.01105 | 0.02063 | 0.02091 |
| **R-E7** | **Hybrid + entities + context + intent** | **0.03146** | **0.01940** | **0.04801** | **0.02857** |

R-E7 was the validation-selected configuration. Adding entities and context with equal weights hurt the hybrid branch, but adding intent recovered and exceeded the hybrid baseline.

### 2. R-E7 removal ablations

Delta is the removed-system NDCG@10 minus full R-E7 NDCG@10. Negative values mean the removed component was useful. Confidence intervals are paired query bootstraps with 2,000 resamples and seed 42; they are descriptive and are not corrected for multiple comparisons.

| Split | Removed component | NDCG@10 | Delta | 95% interval |
| --- | --- | ---: | ---: | --- |
| Validation | none | 0.03146 | 0.00000 | — |
| Validation | BM25 | 0.03331 | +0.00184 | [-0.00842, 0.01364] |
| Validation | dense | 0.03248 | +0.00102 | [-0.00783, 0.00986] |
| Validation | entities | 0.01921 | -0.01226 | [-0.02862, -0.00065] |
| Validation | context | 0.03010 | -0.00136 | [-0.00838, 0.00332] |
| Validation | intent | 0.02727 | -0.00419 | [-0.01768, 0.00728] |
| Test | none | 0.01940 | 0.00000 | — |
| Test | BM25 | 0.00813 | -0.01126 | [-0.02521, 0.00099] |
| Test | dense | 0.02098 | +0.00158 | [-0.00130, 0.00560] |
| Test | entities | 0.01625 | -0.00315 | [-0.01266, 0.00420] |
| Test | context | 0.01823 | -0.00117 | [-0.00788, 0.00439] |
| Test | intent | 0.01105 | -0.00835 | **[-0.01887, -0.00036]** |

Intent was the only test removal whose interval excluded zero. Removing dense slightly increased test NDCG@10, so the dense branch did not show incremental value inside R-E7 even though dense alone was stronger than BM25 alone.

### 3. Modest entity and topic-conditioned context boosts

The tested formula was:

`hybrid + α × entity_coverage + β × topic_gate × context_coverage`

The grid used weights `{0, 0.025, 0.05, 0.10, 0.20}`. The topic gate allowed context only for compatible query topics.

| Configuration | Selected/fixed weights | Validation NDCG@10 | Test NDCG@10 | Test Recall@10 | Test MRR@10 |
| --- | --- | ---: | ---: | ---: | ---: |
| Hybrid | — | 0.02545 | 0.01651 | 0.03528 | 0.02304 |
| Entity only | α=0.20 | 0.02610 | 0.01511 | 0.02972 | 0.02477 |
| Gated context only | β=0.00 selected | 0.02545 | 0.01651 | 0.03528 | 0.02304 |
| Ungated context only | selected | 0.02565 | 0.01651 | 0.03528 | 0.02304 |
| Joint, gated | α=0.20, β=0.00 | 0.02610 | 0.01511 | 0.02972 | 0.02477 |
| Joint, ungated | selected | 0.02633 | 0.01511 | 0.02972 | 0.02477 |
| Fixed entity | α=0.10 | 0.02477 | 0.01682 | 0.03528 | 0.02486 |
| Fixed joint, gated | α=0.10, β=0.10 | 0.02477 | 0.01682 | 0.03528 | 0.02486 |
| Fixed joint, ungated | α=0.10, β=0.10 | 0.02490 | 0.01682 | 0.03528 | 0.02486 |

Validation selected zero context weight. The fixed 0.10 setting had a small test increase of **0.00031**, but it was worse on validation and therefore is not evidence of a reliable improvement.

### 4. Entity/context bonus and penalty

The signed formula was:

`hybrid + eb × entity_match − ep × entity_conflict + cb × context_match − cp × context_conflict`

Missing evidence was neutral. Context conflict was only asserted for explicit contradictions such as age, route, or year; ordinary absence was not penalized.

| Configuration | Validation NDCG@10 | Test NDCG@10 | Test Recall@10 | Test MRR@10 |
| --- | ---: | ---: | ---: | ---: |
| Hybrid | 0.02545 | 0.01651 | 0.03528 | 0.02304 |
| Bonuses only, selected | 0.02632 | 0.01511 | 0.02972 | 0.02477 |
| Penalties only, selected | 0.02610 | 0.01511 | 0.02972 | 0.02477 |
| Bonuses + penalties, selected | 0.02746 | 0.01393 | 0.02972 | 0.02303 |
| Fixed bonuses, 0.05 | 0.02577 | 0.01684 | 0.03528 | 0.02486 |
| Fixed penalties, 0.05 | 0.02577 | 0.01684 | 0.03528 | 0.02486 |
| Fixed bonuses + penalties, 0.05 | 0.02490 | 0.01682 | 0.03528 | 0.02486 |

The selected combined signed model overfit validation and reduced test NDCG@10 by **0.00258** from hybrid. The small fixed-weight test gains were not supported by validation.

### 5. Evidence audit and extraction repair

The audit profiled all 500 queries and 345 titles, then reviewed a stratified 60-pair sample.

| Audit finding | Result |
| --- | ---: |
| Unique content molecule annotations literally visible in titles | 128 / 399 |
| Query molecule annotations literally visible in query text | 381 / 539 |
| Indonesian comparison cues missed | 7 |
| `Renal and Hepatic Impairment` renal cues missed | 10 |
| Safety questions incorrectly flagged as negation | 10 |
| Dosing-positive documents based only on `drug_profile` type | 27 / 60 |
| Comparison-positive documents based only on `review` type | 12 / 17 |

Repairs added Indonesian comparison cues, coordinated renal/hepatic extraction, and safer negation handling. The explicit-only variant also removed content-type-only proxies for dosing and comparison.

| Retrieval configuration | Context version | Validation NDCG@10 | Test NDCG@10 | Test Recall@10 | Test MRR@10 |
| --- | --- | ---: | ---: | ---: | ---: |
| BM25 + entity + context | Legacy / cue repair | 0.02966 | 0.01477 | 0.03154 | 0.02389 |
| BM25 + entity + context | Explicit-only / repaired | 0.02966 | 0.01203 | 0.02245 | 0.02288 |
| Hybrid + entity + context | All versions | 0.02727 | 0.01105 | 0.02063 | 0.02091 |
| Hybrid + entity + context + intent | Legacy / cue repair | 0.03146 | 0.01940 | 0.04801 | 0.02857 |
| Hybrid + entity + context + intent | Explicit-only / repaired | 0.03146 | 0.01677 | 0.03891 | 0.02766 |
| Modest hybrid + entity + context | All versions | 0.02490 | 0.01682 | 0.03528 | 0.02486 |

Cue repairs changed extracted data but did not change aggregate NDCG@10. Removing weak type proxies made the representation more defensible, yet reduced the behavior metric because some behavior-positive documents were supported only by those proxies.

### 6. Repaired data with bonus and penalty

Running the signed mechanism on repaired explicit evidence produced the same headline values as the original signed experiment at the stored precision.

| Configuration | Validation NDCG@10 | Test NDCG@10 | Test Recall@10 | Test MRR@10 |
| --- | ---: | ---: | ---: | ---: |
| Repaired bonuses only | 0.02632 | 0.01511 | 0.02972 | 0.02477 |
| Repaired penalties only | 0.02610 | 0.01511 | 0.02972 | 0.02477 |
| Repaired bonuses + penalties | 0.02746 | 0.01393 | 0.02972 | 0.02303 |
| Repaired fixed bonuses, 0.05 | 0.02577 | 0.01684 | 0.03528 | 0.02486 |
| Repaired fixed penalties, 0.05 | 0.02577 | 0.01684 | 0.03528 | 0.02486 |
| Repaired fixed both, 0.05 | 0.02490 | 0.01682 | 0.03528 | 0.02486 |

The repairs affected too few score boundaries near rank 10 to change the aggregate metric. Validation again selected zero context-penalty weight.

### 7. Signed entity/context plus intent

The combined formula was:

`hybrid + ebE − epE_conflict + cbC − cpC_conflict + wiI`

Signed weights used `{0, 0.05, 0.20}` and intent used `{0, 0.05, 0.10, 0.20, 0.50}`. There were 405 validation trials for each of the legacy and repaired modes.

| Configuration | Validation NDCG@10 | Test NDCG@10 | Test Recall@10 | Test MRR@10 |
| --- | ---: | ---: | ---: | ---: |
| Hybrid | 0.02545 | 0.01651 | 0.03528 | 0.02304 |
| Intent only | 0.02358 | 0.01640 | 0.03528 | 0.02230 |
| Signed only | 0.02746 | 0.01393 | 0.02972 | 0.02303 |
| Signed + intent, validation-selected | 0.03141 | 0.01770 | 0.03891 | 0.03114 |
| All terms nonzero, validation-selected | 0.03141 | 0.01770 | 0.03891 | 0.03114 |
| Fixed all 0.05 + intent 0.20 | 0.02475 | 0.01932 | 0.04437 | 0.02602 |
| Prior signed weights + intent 0.50, legacy | 0.03115 | **0.02032** | 0.04801 | 0.03205 |
| R-E7-equivalent, legacy | **0.03146** | 0.01940 | **0.04801** | 0.02857 |
| Prior signed weights + intent 0.50, repaired | 0.03115 | 0.01770 | 0.03891 | 0.03114 |
| R-E7-equivalent, repaired | 0.03146 | 0.01677 | 0.03891 | 0.02766 |

For the validation-selected signed-plus-intent model, the paired test delta versus hybrid was **+0.00119** with 95% interval **[-0.00301, 0.00536]**. Six positive queries improved, four worsened, and 100 were unchanged. Versus R-E7, its delta was **-0.00170** with interval **[-0.00865, 0.00181]**.

The legacy prior-weight setting exceeded R-E7 on test by **0.00093**, interval **[0.00006, 0.00219]**, but had lower validation performance and was identified after repeated test inspection. It is an exploratory lead only.

### 8. Multi-value and value-aware entity/context scoring

This experiment replaced dimension-level “any overlap” with per-value accounting. Requested-value scoring averaged recall across requested disease/molecule/class/area values and penalized unmatched requested values only when the document had evidence in that dimension. Symmetric scoring used per-dimension F1 for the bonus and `1 − Jaccard` for conflict. Empty document evidence remained unknown and neutral. Context used exact match, explicit conflict, or unknown.

| Configuration | Validation NDCG@10 | Test NDCG@10 | Test Recall@10 | Test MRR@10 |
| --- | ---: | ---: | ---: | ---: |
| Hybrid | 0.02545 | 0.01651 | 0.03528 | 0.02304 |
| Original R-E7 | **0.03146** | **0.01940** | **0.04801** | 0.02857 |
| Current repaired signed all terms | 0.03141 | 0.01770 | 0.03891 | 0.03114 |
| Requested-value exact, selected | 0.03115 | 0.01770 | 0.03891 | 0.03114 |
| Symmetric exact, selected | 0.02999 | 0.01900 | 0.03891 | **0.03618** |
| Requested entity + current context | 0.03115 | 0.01770 | 0.03891 | 0.03114 |
| Symmetric entity + current context | 0.02999 | 0.01900 | 0.03891 | 0.03618 |
| Current entity + exact context | 0.03141 | 0.01770 | 0.03891 | 0.03114 |

The symmetric model improved test NDCG@10 over the current signed baseline by **0.00130**, interval **[0.00002, 0.00338]**, but remained **0.00040** below R-E7, interval **[-0.00769, 0.00466]**, and was worse on validation. Exact context made no NDCG@10 difference.

The implementation changed only **519 of 172,500 entity pairs (0.30%)** and **375 context pairs (0.22%)**. Among the 21 multi-molecule/class test queries, the current, requested-value, and symmetric models all had NDCG@10 **0.02044**. All five test queries whose NDCG changed were single-value queries. The test movement came from penalizing extra document entities, not from solving the intended multi-value problem.

### Metric sensitivity to behavior-label definitions

The primary conclusions were checked against alternative behavior-grade definitions.

| Model | Primary | Conservative | Event hierarchy | Grade ≥ 2 |
| --- | ---: | ---: | ---: | ---: |
| Hybrid test NDCG@10 | 0.01651 | 0.01701 | 0.01721 | 0.01563 |
| R-E7 test NDCG@10 | 0.01940 | 0.01921 | 0.02033 | 0.01876 |

R-E7 stayed above hybrid under these definitions, but the absolute values remained low and the labels share the same exposure process.

## Key Findings

1. **Intent is the most useful structured discriminator in this dataset.** R-E7 was the best prespecified model, and removing intent caused the largest statistically distinguishable test loss among the structured components.
2. **Entity and context signals are not universally harmful.** They improved BM25 from 0.01021 to 0.01477 test NDCG@10. They hurt when added to hybrid with equal weight because the combined score over-counted correlated and noisy evidence.
3. **Context has low effective coverage.** Title-only documents rarely express age, renal function, route, comparison state, or dosing constraints explicitly. Validation repeatedly selected zero context-penalty weight, and exact-context refinements did not move NDCG@10.
4. **The signed entity penalty is mostly redundant.** With all four query entity dimensions populated and document metadata populated, `entity_conflict ≈ 1 − entity_coverage`. Equal bonus and penalty weights therefore change the scale and add a query-constant rather than introduce independent information.
5. **Better extraction does not guarantee a better behavior metric.** Repairing obvious cue errors was semantically preferable but often did not move rankings. Removing weak proxies reduced the metric because the behavioral positives sometimes depended on those proxies.
6. **Multi-value-aware scoring did not solve the multi-value slice.** It changed very few pairs and produced no NDCG@10 improvement on multi-value test queries. The small aggregate movement came from single-value queries.
7. **The dense branch is useful alone but unproven inside the full system.** Dense outperformed BM25 alone, while removing dense from R-E7 slightly improved test NDCG@10. The likely causes are correlated ranking evidence and uncalibrated equal weighting.
8. **The absolute metric levels and sparse judgments matter.** Improvements are small, concentrated in a few queries, and evaluated against behavior affected by what was shown and where it appeared.

## Failure Mechanisms and Examples

### Correlated bonus and penalty terms

For a query with four populated entity dimensions, suppose a document matches molecule and therapeutic area but misses disease and drug class:

- entity coverage = `2 / 4 = 0.50`
- entity conflict = `2 / 4 = 0.50`
- with `eb = ep = 0.20`, signed contribution = `0.20 × 0.50 − 0.20 × 0.50 = 0`

More generally, if conflict is the complement of coverage:

`0.20E − 0.20(1 − E) = 0.40E − 0.20`

The `−0.20` term is constant for every document in that query and cannot change ranking. The formula appears to model separate reward and conflict, but it is rank-equivalent to a rescaled coverage bonus.

### Entity and context match while intent differs: Q067–C040

| Field | Value |
| --- | --- |
| Query | `kapan start Atorvastatin di Acute Coronary Syndrome evidence terbaru 2025` |
| Content | `Dose Adjustment of Atorvastatin in Renal and Hepatic Impairment` |
| Content category | `clinical_summary`; source `clinical_practice`; publication year 2025 |
| Query intent | Guideline / Evidence Lookup |
| Allowed types for intent | guideline, review, article |
| Content intent compatibility | **0** |
| Entity match | Atorvastatin, Statins, Cardiology match; ACS `I24` vs Stable Angina `I20` mismatch |
| Entity coverage / conflict | 0.75 / 0.25 |
| Context match | year 2025 and recency match; coverage 1.00 |
| Behavioral label | grade 0 from one exposure with no engagement |

The item ranked **1st** under hybrid + entities + context, then fell to **12th** after intent was added. BM25 ranked it 3rd and dense ranked it 12th. This is the clearest case where entity/context overlap was real but did not satisfy the evidence-seeking intent.

There is also a limitation in the query extraction: `kapan start` was not activated as a dosing signal. The assisted label resolved the query to evidence lookup because of the explicit evidence/year cues, but that classification had low confidence. Intent helped this observed case, while its mapping still needs independent validation.

### Intent can demote a behavior-positive but weakly matched item: Q183–C256

The query asked about pediatric Methyldopa dosing in hypertension in pregnancy. The content was an article on preeclampsia pathophysiology and treatment. It had entity coverage **0.25**, context coverage **0.33**, intent compatibility **0**, and behavior grade **2** from one meaningful exposure. Adding intent moved it from rank 31 to rank 179. It was already outside the top 10, so it did not explain the main metric gain, but it shows that binary content-type compatibility can suppress partial or exploratory relevance.

### Repair can conflict with weak behavioral positives: Q239–C268

For the Ramipril, elderly, hypertension, dose query, the only recorded positive was C268, a Methyldopa pregnancy drug profile. Its dosing compatibility came from the `drug_profile` type proxy rather than explicit title evidence. Removing that proxy made the structured evidence more honest but lowered the behavior metric. This is evidence that the label can reward exposed, weakly related content and that metric optimization alone can preserve bad proxies.

### Broad documents are penalized by symmetric multi-value scoring

Symmetric F1/Jaccard scoring penalizes extra document entities. That can help when a single-drug query retrieves an unrelated multi-drug item, but it can also demote reviews, guidelines, comparisons, and combination-therapy content whose broader entity set is appropriate. The model cannot distinguish “irrelevant extra entity” from “comparator,” “combination partner,” or “background therapy.”

## Honest Evaluation

### What the results support

- Use **R-E7 as the best prespecified research baseline** for this dataset.
- Treat intent compatibility as a promising ranking feature.
- Keep entity/context evidence available as interpretable features rather than applying large unconditional boosts or penalties.
- Preserve explicit conflict as a ternary state: match, contradiction, or unknown.

### What the results do not support

- They do not establish clinical relevance or patient-safety suitability.
- They do not justify deploying the post hoc 0.02032 test configuration.
- They do not show that signed penalties add independent value.
- They do not show that multi-value-aware scoring improved multi-value queries.
- They do not establish a reliable context benefit from title-only evidence.

### Data and evaluation limitations

- Only **7,037 unique query-content pairs** were observed from 7,190 session exposures, about **4.1%** of all possible query-content pairs.
- Temporal validation had 139 queries with 113 positives; temporal test had 139 queries with 110 positives and about 10.4 judgments per query.
- About **3.2%** of retrieved top-10 items were judged. Most rank changes therefore involve unjudged items.
- All no-positive queries were single-session; every multi-session query had a positive. Session depth strongly predicted engagement, indicating outcome-conditioned logging.
- Content exposure and engagement were strongly correlated (Spearman **0.661**), and doctor engagement rates varied widely.
- Inferred rank timestamps had ties in **23.8%** of cases, limiting position-bias correction.
- Phase 10 manually reviewed 40 cases: 38 had weak behavioral ground truth, 32 had an apparently off-topic strongest positive, 29 had intent mismatch, 21 had partial entity match, and 9 had context mismatch.
- Structured compatibility had essentially no monotonic correlation with behavior grade (Spearman **-0.0049**).
- The logs cover only 30 days, and the test split was repeatedly inspected. Confidence intervals do not repair test-set reuse.

The low absolute scores are consistent with sparse judgments and noisy behavior. They should not be interpreted as proof that the retrieved titles are clinically poor, nor should a small metric increase be interpreted as proof of clinical improvement.

## Improvement Opportunities

### 1. Build confidence-weighted behavioral targets

Keep the behavioral data, but stop treating all positives and non-click exposures as equally trustworthy. Use bookmark/return and deep engagement as higher-confidence positives, short clicks as weak positives, and exposed-no-engagement as a low-confidence negative. Train and evaluate only on exposed pairs, with sample weights reflecting evidence strength.

### 2. Represent entity roles, not only entity sets

Extract roles such as primary treatment, comparator, combination partner, failed treatment, alternative candidate, and background medication. Then score completeness according to intent:

- combination queries should require both requested drugs;
- comparison queries should reward both compared entities;
- alternative-treatment queries may accept one candidate;
- broad guidelines should not be punished merely for mentioning additional relevant entities.

This directly addresses the failure seen in symmetric multi-value penalties.

### 3. Use full content evidence with provenance

Title-only context is too sparse. If body text, abstract, tags, or section headings become available, extract evidence spans and retain provenance and confidence. Context should distinguish explicit support, explicit contradiction, and unknown. Numeric constraints such as age, eGFR, dose, route, and year need operators and ranges rather than binary overlap.

### 4. Replace equal averaging with calibrated learning

Use the validation period to fit a small regularized ranking model on BM25, dense, entity-role features, explicit context, and intent confidence. A constrained logistic, linear pairwise, or shallow tree model would estimate interactions without hiding the signal. Do not add doctor identity, historical popularity, or exposure frequency as ranking features; those would encode logging bias.

### 5. Make intent graded and independently validated

Replace binary allowed/disallowed content types with graded compatibility. Validate the runtime query-intent classifier separately from assisted labels, report confidence, and allow mixed intents such as evidence lookup plus treatment initiation. Q067 shows both the value and the brittleness of the current binary mapping.

### 6. Freeze a future temporal test period

Use the current temporal test only for exploratory analysis. Select the next system on validation or nested time splits, then evaluate once on a later untouched log window. Report per-query deltas and the number of affected positive queries so a mean increase driven by a few cases is visible.

### 7. Improve judgment coverage without claiming clinician truth

If clinician adjudication remains unavailable, pool top candidates from materially different rankers and obtain independent relevance review using a written rubric from trained reviewers. Keep this separate from behavior and report agreement. This will not create clinical ground truth, but it can reveal obvious topical and intent errors that exposure-only labels cannot assess.

## What I Would Do Differently

1. **Start with a frozen evaluation contract.** I would define the temporal split, primary label, selection metric, and one final test read before running the first weighting experiment.
2. **Audit label reliability before tuning retrieval weights.** The exposure and session-depth artifacts should have been treated as a first-order modeling problem rather than a caveat added after the retrieval experiments.
3. **Separate extraction quality from ranking quality.** I would test entity/context extraction against a small reviewed sample first, then test ranking. The repair experiment mixed a better representation with a noisy behavior metric, making “improvement” ambiguous.
4. **Use ternary, role-aware evidence from the beginning.** Missing evidence would remain unknown; penalties would require an explicit contradiction; multi-value entities would carry roles.
5. **Avoid complementary signed features.** I would inspect feature algebra and correlation before grid search. The entity bonus and penalty were largely the same signal with opposite notation.
6. **Tune one interpretable model rather than many hand-weighted formulas.** A regularized model with interaction terms and nested validation would provide clearer evidence about marginal value and reduce post hoc test chasing.
7. **Keep the report consolidated from the start.** Experiment runners now retain machine-readable CSV/JSON artifacts, while this file is the single narrative record.

## Reproducibility and Artifact Index

The detailed machine-readable results remain under:

- `outputs/retrieval/phase11/` — eight core systems, removal ablations, slices and rankings.
- `outputs/retrieval/topic_boost/` — modest entity and gated/ungated context boost grid.
- `outputs/retrieval/signed_boost/` — bonus/penalty grid and ablations.
- `outputs/audits/retrieval_evidence/` — evidence provenance and reviewed sample.
- `outputs/retrieval/context_repair/` — extraction changes, repaired features and metric comparisons.
- `outputs/retrieval/repaired_signed_boost/` — repaired signed scoring.
- `outputs/retrieval/intent_signed_boost/` — signed-plus-intent grid, paired comparisons and slices.
- `outputs/retrieval/value_aware_retrieval/` — per-value/symmetric experiments and changed-pair audit.

Each experiment directory retains its metrics, configuration, per-query results, rankings, paired comparisons, slices, and manifest as applicable. Redundant per-experiment Markdown reports were removed; this summary is the only Phase 11 narrative report.
