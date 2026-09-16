## Approach

Phase 8 freezes the retrieval evaluation protocol before retrieval optimization. The primary split is chronological, using approximately 60%/20%/20% of session starts for training, validation, and test. Boundaries are determined without relevance grades. Each session stays intact. A session whose last recorded impression or engagement crosses a boundary is purged, preventing later recorded outcomes from entering an earlier partition.

Query–content judgments are rebuilt independently from each partition's exposures using the frozen Phase 7 grading schemes and maximum aggregation. Full-history Phase 7 pair judgments must not be reused as partition targets: a later bookmark could otherwise raise a training relevance grade. Purged judgments, if produced, are diagnostic only.

The original query-held-out sensitivity split assigns query/session connected components with seed 42. Queries connected through a shared session stay together, keeping both queries and sessions disjoint. This evaluates unseen query IDs, while chronological evaluation evaluates later activity that can include familiar queries and doctors. A doctor-only split was considered but deferred: it addresses new-user generalization rather than chronology. Random session splitting was also considered but would mix earlier and later observations.

A new preferred query-generalization split, `query_dedup`, additionally groups near-duplicate query text before assigning components. It uses Unicode NFKC, case and whitespace normalization, then character 3–5 gram TF-IDF cosine similarity >= 0.95. Numeric tokens must match exactly; years, ages, and doses are not stripped. Exact normalized matches are also linked. Duplicate links and shared-session links form connected components, assigned approximately 60%/20%/20% by component count with seed 42. This removes detected duplicate overlap across this split while retaining every query and observation. The original query split remains available as a comparison; chronology remains the primary future-activity protocol.

This is a lightweight lexical grouping heuristic, not proof of clinical equivalence. TF-IDF is fit to query text only to construct the split; it is not passed to the ranker and does not use intent or outcome labels. A high threshold favors precision but misses broader paraphrases and translations. One detected pair differs by “MDR,” which changes clinical specificity: placing the pair together conservatively prevents closely related wording from crossing partitions, without deleting either query or merging their relevance targets.

The following rules are frozen for subsequent retrieval phases; Phase 8 establishes the partitions and does not implement or report retrieval metrics:

- Fit retrieval weights, behavioral priors, and learned preprocessing on training evidence. Select configurations on validation NDCG@10, then evaluate the chosen configuration once on test.
- Retrieve against the complete 345-document corpus. Fixed document-only lexical indexing can use the corpus; behavioral features must respect partition boundaries.
- Report macro NDCG@5/10 using gain `2^grade - 1`, Recall@1/3/5/10/20, and MRR. Binary relevance is grade >= 1, with grade >= 2 as a sensitivity check. Keep primary, conservative, and event-hierarchy judgments separate.
- Preserve unexposed pairs as unjudged. Conventional full-corpus proxy metrics assign them zero gain for computation without establishing irrelevance. Report judged fraction at K alongside ranking metrics.
- Exclude queries without positives from positive-dependent metrics, but report their counts and coverage separately. Recompute eligibility for each relevance threshold. Report uncertainty and language/intent/context slices where support permits.

Run the Phase 8 notebook cell, which imports `build_phase8_artifacts` as `run_phase8` and calls `run_phase8()`, or run `python -m src.evaluation_split` from the repository root. Outputs in `outputs/evaluation/` include exposure and raw signal-ID assignments, partition-specific judgments, query eligibility tables, counts, overlap audits, and a manifest containing boundaries, seed, ratios, and the labeled-exposure input SHA-256.

## Key Findings

Validation begins January 19, 2025 at 19:04:41 UTC; test begins January 25 at 01:04:06 UTC. Naive source timestamps are interpreted consistently as UTC. No sessions cross these boundaries, so none require purging.

| Protocol | Partition | Exposures | Queries | Queries with positives | Queries without positives |
| --- | --- | ---: | ---: | ---: | ---: |
| Temporal | Train | 4,287 | 340 | 245 | 95 |
| Temporal | Validation | 1,444 | 139 | 113 | 26 |
| Temporal | Test | 1,459 | 139 | 110 | 29 |
| Query-held-out | Train | 4,359 | 300 | 212 | 88 |
| Query-held-out | Validation | 1,425 | 100 | 70 | 30 |
| Query-held-out | Test | 1,406 | 100 | 68 | 32 |
| Duplicate-grouped | Train | 4,439 | 300 | 213 | 87 |
| Duplicate-grouped | Validation | 1,407 | 99 | 69 | 30 |
| Duplicate-grouped | Test | 1,344 | 101 | 68 | 33 |

Each protocol assigns all 7,190 exposures and all 1,500 behavioral signal IDs exactly once. Impression and session overlap is zero across partitions. Query overlap is zero in the query-held-out split; chronological training and test share 56 query IDs. These are alternative experiments over the same dataset, not independent datasets to pool together.

The lexical audit finds no exact normalized duplicates and three near-duplicate pairs among six query IDs, leaving 497 query/session components. Two detected pairs span chronological partitions and one spans the original query partitions. No detected pair spans the new `query_dedup` partitions. The primary chronological protocol intentionally retains its repeated-query behavior; it is not duplicate-isolated. Pair texts and similarity scores are saved in `phase8_duplicate_pairs.csv`, cross-partition checks in `phase8_duplicate_overlap_audit.csv`, and component assignments in `query_dedup_query_groups.csv`.

All 67 repository tests passed after the duplicate-grouping update. Tests include late-outcome purging, connected query/session grouping, deterministic assignment, duplicate rejection, and partition-local aggregation. They verify software invariants, not clinical relevance accuracy. Existing serialized intent models emit scikit-learn version warnings in the newly installed environment; Phase 8 does not load those models or regenerate intent predictions.

## Honest Evaluation

The implemented split prevents direct reuse of observations and prevents future recorded session outcomes from contaminating earlier relevance aggregates. It does not establish that all earlier project decisions were independent of test data, or automatically enforce how future rankers construct features. The following failures and mitigations distinguish existing safeguards from work still needed.

| Possible failure or leakage | Consequence | Mitigation and current status |
| --- | --- | --- |
| Full-history relevance aggregation | A later positive event raises an earlier partition's target. | Implemented: split exposures first, rebuild judgments separately, and audit raw event assignments. Downstream code must use these partition artifacts. |
| Sessions or delayed recorded events cross a boundary | Later outcomes enter training through a session assigned by start time alone. | Implemented: consider the last recorded impression and engagement and purge crossing sessions. No sessions require purging in this run. |
| Full-dataset threshold selection and prior inspection | Phase 7 dwell thresholds and earlier analysis indirectly used held-out observations. | Freeze current rules and disclose the prior access. Report the event-hierarchy scheme, which avoids dwell cutoffs. A fresh future holdout is still needed for a stronger independent evaluation. |
| Intent features derived from the all-query workflow | An intent-aware ranker can benefit from held-out query information. | Pending: fit the intent model on training queries, use out-of-fold predictions for training ranker features, and predict validation/test without fitting on them. Existing intent features cannot establish unseen-query generalization. |
| Repeated query IDs in temporal evaluation | Memorized query–document preferences can inflate apparent generalization. | Query-held-out sensitivity is implemented. Still report temporal results separately for seen and unseen queries; familiar-query performance is a valid but narrower deployment claim. |
| Duplicate text, paraphrases, or templates across query partitions | Different IDs can represent almost the same information need, making query-held-out evaluation too easy. | Implemented: exact-normalized and high-similarity lexical grouping in `query_dedup`, with zero detected cross-partition pairs. Broader semantic/template grouping remains pending; the heuristic can miss paraphrases, translations, or short queries, and transitive links can overgroup related queries. |
| Shared doctors across partitions | Doctor-specific engagement habits can carry across the split, especially if identity features are introduced. | Overlap is reported, but doctor isolation is not implemented. Add doctor-held-out evaluation before claiming new-user generalization. |
| Full-history behavioral features or cached targets | Global popularity, click rates, target encodings, or accidentally loaded Phase 7 judgments can reveal validation/test outcomes. | Protocol requires training-only computation. Future feature pipelines need provenance checks and, for temporal features, as-of joins using information available before prediction. |
| Repeated test inspection | Selecting weights, features, or methods from test results makes test another validation set. | Protocol requires validation-only selection. Freeze configurations and preserve a final test evaluation record; the split code cannot enforce researcher behavior. |
| Future content in the fixed corpus | Documents unavailable during the historical search period can enter candidate rankings. | Exact availability timestamps are missing. Describe results as fixed-corpus evaluation; filter by availability time when those timestamps become available. |
| Incomplete and exposure-biased judgments | Historically unexposed but relevant documents receive zero metric gain, potentially penalizing improved discovery. | Report judgment coverage and weak-label sensitivity. Independent blinded judgments of pooled results, including unexposed documents, are still needed. |
| Exclusion of queries without positives | Metrics cover 110 of 139 temporal test queries and can conceal poor support for the remaining 29. | Eligibility and counts are exported. Report the evaluated denominator and separate coverage; do not equate missing positives with system failure or silently omit these queries. |
| Incomplete outcome follow-up | Recent test exposures may have less time to accumulate return visits or bookmarks. Boundary purging only sees recorded events. | Pending: obtain logging completeness and follow-up information, define a fixed outcome window, and exclude exposures without mature follow-up. |
| Correlated observations and small slices | Shared doctors, repeated queries, and templates can make query-level bootstrap intervals too narrow and slice results unstable. | Report sample sizes. Compare query bootstrap with doctor/template block bootstrap where support permits; avoid strong conclusions from sparse slices. |
| Timestamp assumptions or inaccurate session identifiers | Incorrect ordering, timezone interpretation, or session grouping can undermine the chronological claim. | UTC interpretation is disclosed. Validate source timezone, session semantics, missing timestamps, and clock consistency before treating this as a production replay. |

Relevance remains a behavioral proxy. Grade 0 can mean non-examination, abandonment, or satisfaction without a click; a high grade does not prove clinical correctness. Maximum aggregation also gives repeatedly exposed pairs more opportunities to receive a high grade. The split isolates evidence but does not correct these biases.

The manifest fingerprints the labeled-exposure input, but it is not a complete reproducibility lock: code, raw-event inputs, dependencies, and future model artifacts also need versioning. The scikit-learn warnings illustrate why passing tests alone is insufficient evidence of model portability.

## What You Would Do Differently

I would establish the holdout before inspecting outcome distributions or selecting relevance thresholds. For the current project, that cannot be repaired retroactively; I would freeze the existing definitions, disclose prior access, and reserve a newly collected time period for final confirmation. The event-hierarchy sensitivity check reduces dependence on dwell cutoffs but does not replace an independent holdout.

After the implemented lexical grouping, I would review the three linked pairs and inspect lower-similarity candidates for missed paraphrases, report temporal seen/unseen-query slices, and add a broader grouped semantic-family split if warranted. A separate doctor-held-out experiment would test new-user transfer. These experiments answer different questions, so I would report them separately rather than combining their scores into one headline result.

Before running intent-aware or learned retrieval, I would regenerate intent features with a training-only and out-of-fold workflow. I would make behavioral feature builders consume explicit partition inputs, test that changing test events cannot alter training features or targets, and enforce as-of computation for time-dependent features. I would version raw inputs, configuration, code, dependency versions, and generated artifacts together.

For a stronger temporal replay, I would verify timezone and session semantics, obtain document availability timestamps, and define a consistent outcome-maturity window. I would add an embargo only if the follow-up horizon or cross-session dependence justified it, and repeat evaluation across several rolling time windows to assess stability beyond this single month.

Finally, I would obtain blinded clinician judgments for pooled retrieval results, including unexposed documents and queries without observed positives. This would help distinguish genuine ranking improvements from conformity to historical exposure. I would report behavioral proxy metrics, judgment coverage, clinical evaluation, and uncertainty separately, using grouped resampling where the available independent groups support it.
