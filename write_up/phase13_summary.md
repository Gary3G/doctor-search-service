# Phase 13 — Slice-Based Evaluation

## Approach

Phase 13 is a diagnostic evaluation of frozen Phase 11 and Phase 12 rankings; no model is trained, retuned, or selected here. The primary analysis uses the temporal test split and behavior-derived `relevance_grade >= 1`. Results are macro-averaged across eligible queries, and unjudged documents receive zero computational gain without being interpreted as clinically irrelevant.

| Phase 13 label | Frozen source | Scoring components |
| --- | --- | --- |
| BM25 | R-B0 | BM25 only |
| BM25 + structure | R-E2 | BM25 + entity compatibility + contextual compatibility |
| Hybrid without intent | R-E6 | BM25 + dense similarity + entity compatibility + contextual compatibility |
| Hybrid + predicted intent | Phase 12 runtime model | R-E6 + 0.25 × predicted intent/content-type compatibility |

The analysis covers language, entity count and composition, contextual complexity, top-level intent, and Pharmacotherapy sub-intent. Required overlapping context slices are reported directly; an additional exclusive zero/one/multiple-constraint view supports the complexity trend test. The structure hypothesis uses R-E2 minus R-B0, which isolates entity/context structure without adding dense retrieval. The intent hypothesis uses the predicted-intent model minus R-E6. Paired differences use 2,000 deterministic query bootstrap resamples.

## Key Findings

The central result is heterogeneity: improvements occur in particular slices rather than across all queries. Structured retrieval does not improve monotonically with contextual complexity. R-E2 minus BM25 changes test NDCG@10 by +0.00389 for no constraints, -0.00052 for one, and +0.02509 for multiple constraints. The high-complexity point estimate is positive but is based on only 12 eligible queries.

Predicted intent is most useful where intent implies a preferred content type. It changes test NDCG@10 by +0.01418 for the available prespecified Pharmacotherapy and Evidence / Guideline group, versus -0.00090 for other observed intents. Pharmacotherapy drives this result: its NDCG@10 rises from 0.00516 to 0.02318, but only 5 of 48 eligible queries improve. The largest sub-intent movement is Interaction / Combination, followed by Dosing / Administration.

**Language slices**

| slice_name | queries | eligible_queries | support_flag | BM25 | BM25 + structure | Hybrid without intent | Hybrid + predicted intent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| English | 70 | 52 | adequate | 0.01407 | 0.01860 | 0.01860 | 0.02279 |
| Bahasa Indonesia | 25 | 20 | adequate | 0.00208 | 0.00698 | 0.00256 | 0.01020 |
| Mixed language | 44 | 38 | adequate | 0.00921 | 0.01362 | 0.00518 | 0.01704 |

**Entity-complexity slices**

| slice_name | queries | eligible_queries | support_flag | BM25 | BM25 + structure | Hybrid without intent | Hybrid + predicted intent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Zero recognized entities | 0 | 0 | empty | — | — | — | — |
| One recognized entity | 0 | 0 | empty | — | — | — | — |
| Two or more recognized entities | 139 | 110 | adequate | 0.01021 | 0.01477 | 0.01105 | 0.01851 |

| slice_name | queries | eligible_queries | support_flag | BM25 | BM25 + structure | Hybrid without intent | Hybrid + predicted intent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Disease only | 0 | 0 | empty | — | — | — | — |
| Drug only | 0 | 0 | empty | — | — | — | — |
| Disease + drug | 139 | 110 | adequate | 0.01021 | 0.01477 | 0.01105 | 0.01851 |
| Multiple molecules | 10 | 9 | sparse | 0.05096 | 0.05096 | 0.05096 | 0.03631 |
| Single molecule | 129 | 101 | adequate | 0.00658 | 0.01154 | 0.00749 | 0.01693 |

**Contextual-complexity slices**

| slice_name | queries | eligible_queries | support_flag | BM25 | BM25 + structure | Hybrid without intent | Hybrid + predicted intent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| No extra contextual slot | 71 | 57 | adequate | 0.01554 | 0.01942 | 0.01787 | 0.02437 |
| Demographic constraint | 17 | 12 | sparse | 0.00000 | 0.02509 | 0.00000 | 0.02409 |
| Year constraint | 15 | 10 | sparse | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| Renal/lab constraint | 4 | 3 | very_sparse | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| Multiple constraints | 18 | 12 | sparse | 0.00000 | 0.02509 | 0.00000 | 0.02409 |

The exclusive context-count view used for the trend test is:

| slice_name | queries | eligible_queries | support_flag | BM25 | BM25 + structure | Hybrid without intent | Hybrid + predicted intent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| No constraints | 71 | 57 | adequate | 0.01554 | 0.01942 | 0.01787 | 0.02437 |
| One constraint | 50 | 41 | adequate | 0.00580 | 0.00528 | 0.00480 | 0.00874 |
| Multiple constraints | 18 | 12 | sparse | 0.00000 | 0.02509 | 0.00000 | 0.02409 |

**Top-level intent slices**

| slice_name | queries | eligible_queries | support_flag | BM25 | BM25 + structure | Hybrid without intent | Hybrid + predicted intent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Evidence / Guideline Lookup | 17 | 12 | sparse | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| Management / Treatment | 41 | 33 | adequate | 0.02217 | 0.02120 | 0.01852 | 0.01719 |
| Management / Treatment; Epidemiology / Prognosis | 9 | 9 | sparse | 0.01249 | 0.03958 | 0.03958 | 0.03958 |
| New dataset-specific class | 7 | 7 | sparse | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| Pharmacotherapy | 59 | 48 | adequate | 0.00582 | 0.01185 | 0.00516 | 0.02318 |
| Pharmacotherapy; Epidemiology / Prognosis | 6 | 1 | very_sparse | 0.00000 | 0.00000 | 0.00000 | 0.00000 |

**Pharmacotherapy sub-intents**

| slice_name | queries | eligible_queries | support_flag | BM25 | BM25 + structure | Hybrid without intent | Hybrid + predicted intent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Comparative Treatment Choice | 5 | 5 | sparse | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| Dosing / Administration | 29 | 22 | adequate | 0.00789 | 0.02247 | 0.00789 | 0.02601 |
| Efficacy / Outcomes | 6 | 1 | very_sparse | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| Interaction / Combination | 6 | 6 | sparse | 0.01068 | 0.00387 | 0.00387 | 0.06809 |
| Safety / Contraindication | 19 | 15 | sparse | 0.00278 | 0.00341 | 0.00341 | 0.00881 |

## Honest Evaluation

These results do not establish a globally superior retrieval model. Across the prespecified hypothesis rows, only 1 of 7 paired bootstrap intervals exclude zero. The intervals are uncorrected for multiple slice comparisons and are not cluster-robust. Many apparent gains come from one or two changed queries, while most eligible queries have identical NDCG@10 under both systems.

The entity analysis is not identifiable from this sample: every query has supplied disease and drug metadata, so the following required slices are empty: Zero recognized entities, One recognized entity, Disease only, Drug only. The multiple-molecule slice has only nine eligible test queries. Context categories overlap, the renal/lab slice contains only three eligible queries and represents renal constraints rather than numeric lab values, and Work-up and Test Interpretation are absent from the frozen intent taxonomy.

Relevance is inferred from exposed-item behavior rather than clinician judgments, so the evaluation inherits exposure, position, and engagement bias. Slice membership inherits supplied metadata and deterministic extraction errors. Top-level intents are assisted weak references even though runtime retrieval uses predicted intent. The test split was inspected in earlier phases, making all test results descriptive rather than pristine confirmation. The defensible decision is to retain predicted intent as an intent-specific research signal, not to claim a universal ranking improvement.

## What I Would Do Differently

1. Build clinician-adjudicated pooled judgments from the top results of all four systems, including explicit irrelevance and graded clinical usefulness, rather than treating unexposed content as zero gain.
2. Create a genuinely untouched confirmation set and preregister the slice definitions, primary contrasts, and multiplicity correction before examining results.
3. Collect or construct more queries with zero, one, disease-only, drug-only, multi-entity, renal/lab, and multiple contextual constraints so the required complexity hypotheses are actually identifiable.
4. Evaluate intent and structure with calibrated, provenance-aware features and document-section evidence instead of coarse title and content-type compatibility.
5. Report hierarchical or cluster-robust uncertainty and require both a minimum slice size and a minimum number of changed queries before interpreting a slice effect.

Artifacts: `query_slice_membership.csv`, `slice_catalog.csv`, `slice_metrics.csv`, `slice_comparisons.csv`, `hypothesis_tests.csv`, `manifest.json`, and `outputs/figures/phase13_slice_effects.png`.
