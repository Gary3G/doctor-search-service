## Approach

Implemented a fixed BM25Okapi baseline over all 345 content titles for all 500 queries. The supplied corpus has no body or summary field. No entities, intent predictions, behavioral features, translation, or clinical expansion enter the index. Unicode NFKC normalization, case folding, and word/number tokenization are applied identically to queries and titles; stopwords are retained. Existing configuration defaults are frozen: k1=1.5, b=0.75 (rank-bm25 epsilon=0.25). Equal scores are ordered by content ID, including out-of-vocabulary queries. No parameters were tuned after inspecting validation or test results.

Run `.venv/bin/python -m src.bm25_baseline` from the repository root, or execute the Phase 9 notebook cells. Phase 8 partition-specific judgments must already exist. Outputs under `outputs/retrieval/` contain top-20 rankings, aggregate and per-query metrics, language/intent slices, descriptive bootstrap intervals, and a manifest with input/code fingerprints and package versions. The experiment log records R-B0.


Retrieve against the full corpus, then evaluate separately on each frozen temporal, query-held-out, and duplicate-grouped train/validation/test partition. Evaluate all three Phase 7 grade schemes independently and binary thresholds >=1 and >=2. Recall uses the number of observed positive documents as its denominator; MRR is truncated at K. NDCG uses gains 2^grade−1 and an ideal ordering of all observed judgments for the query. The binary threshold changes eligibility and binary metrics, but does not discard grade-1 gains from graded NDCG.

Unjudged documents receive zero gain solely for proxy computation. They remain unjudged, and no new negative labels are written. Queries with no positives under the selected scheme/threshold have undefined positive-dependent metrics and are excluded from macro averages. Their counts remain visible. Judged fraction averages over every query in the partition, including those without positives. No precision claim is made.

## Key Findings

Primary scheme, grade >=1, test partition:

| Protocol | Positive / total queries | Recall@5 | Recall@10 | MRR@10 | NDCG@10 | Judged@10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Temporal (primary) | 110 / 139 | 0.0090 | 0.0161 | 0.0202 | 0.0102 | 2.88% |
| Query-held-out | 68 / 100 | 0.0117 | 0.0202 | 0.0342 | 0.0132 | 4.10% |
| Duplicate-grouped | 68 / 101 | 0.0093 | 0.0300 | 0.0300 | 0.0146 | 4.06% |

The temporal test result establishes a reproducible reference for later retrieval ablations. The query-held-out protocols produce somewhat higher scores, but evaluate different query sets and behavioral evidence; they do not demonstrate that the same model improved. All train/validation/test scores and relevance-scheme sensitivity combinations are saved in `outputs/retrieval/bm25_metrics.csv`.

## Honest Evaluation

Scores are low: the baseline recovers only 1.61% of observed positives at rank 10 on the temporal test set. However, only 2.88% of its top-10 results have observed judgments. This means the evaluation cannot reliably distinguish a relevant but historically unexposed result from an irrelevant result. Low scores are not proof that all unjudged results are wrong, and sparse judgments are not proof that the ranker is good.

The baseline has several concrete model limitations:

- **Title-only evidence:** a title may omit the drug, condition, population, or recommendation discussed in the document. Body/summary text is unavailable, and the model cannot recover information absent from its index.
- **Lexical mismatch:** BM25 depends on token overlap. It has no translation, synonym mapping, abbreviation expansion, or stemming, so English/Bahasa Indonesia equivalents and alternate medical terminology may fail to match.
- **No clinical relationships or constraint reasoning:** bag-of-words matching does not distinguish negation, treatment versus adverse effects, or the roles of compared drugs. Numeric tokens are retained, but the ranker cannot interpret dose units, age ranges, renal thresholds, or temporal compatibility.
- **No structured or intent evidence:** supplied disease/molecule entities, ICD/ATC hierarchy, extracted context, and query intent are unused. A document can share vocabulary while addressing the wrong clinical information need.
- **Fixed scoring and arbitrary ties:** k1 and b use existing defaults without validation tuning. Very short titles provide limited term-frequency evidence. Empty or entirely out-of-vocabulary queries receive tied scores and an arbitrary content-ID ordering; deterministic output is not evidence of relevance.
- **No quality or availability checks:** scores do not incorporate source quality, clinical correctness, freshness, or document availability at query time. This baseline alone is not a clinically validated search service.

The evaluation also has limitations. Behavioral grades reflect exposure, examination, engagement, and logging rather than independent clinician relevance judgments. Maximum aggregation gives repeatedly exposed pairs more opportunities to receive a high grade. Excluding the 29 temporal-test queries without positives leaves their retrieval quality unmeasured. Changing the positive threshold changes the eligible query population, so higher sensitivity scores are not directly comparable improvements.

Temporal test NDCG@10 has a descriptive 95% query-bootstrap interval of [0.0022, 0.0210] (2,000 resamples, seed 42). These intervals do not account for shared doctors, sessions, or query families. Language/intent slice tables include support counts; intent labels are used only for reporting and are not independent clinical gold labels. Small slices should not support strong conclusions.

The corpus is a static snapshot without document availability timestamps, so the temporal protocol is not a strict as-of replay. Earlier project exploration also means the existing test set is not a pristine prospective holdout. The three split protocols reuse the same underlying dataset and are not independent replications.

All 70 unit tests passed, including analytic DCG/Recall/MRR examples, perfect rankings, unknown-document handling, zero-positive exclusion, threshold sensitivity, title-only ranking, and deterministic ties. These checks establish implementation correctness, not retrieval usefulness. The full suite emitted existing scikit-learn model-version warnings from earlier intent artifacts; BM25 does not load those models. The new notebook cells were executed in-process with IPython because the sandbox blocked Jupyter kernel sockets, preserving earlier-phase outputs.

## What You Would Do Differently

I would first inspect the Phase 10 failure examples and separate lexical misses, missing title evidence, clinical constraint mismatches, and unjudged results. A small blinded clinician review of pooled top results, including unexposed documents and queries without behavioral positives, would help establish whether low proxy scores reflect poor retrieval, incomplete judgments, or both.

With richer source data, I would index title plus body/summary and evaluate field weighting. I would then test medical abbreviation/synonym normalization, bilingual retrieval, supplied entity matching, and contextual compatibility as separate ablations against this frozen baseline. Frozen multilingual embeddings could address lexical mismatch, but any benefit would need measurement rather than assumption.

I would tune BM25 parameters and any expansion or combination weights on validation evidence only. Since these test results have now been inspected, subsequent iterative decisions should be confirmed on a newly reserved time period or clinician-judged holdout. Paired comparisons on identical eligible queries would make model changes easier to interpret; cluster-aware uncertainty estimates would better reflect shared query families or doctors where support permits.

For production-oriented evaluation, I would obtain document availability timestamps, define an outcome-maturity window, and evaluate historical corpus snapshots. I would also add explicit handling for queries with no lexical matches and assess latency, clinical relevance, and source quality before treating the baseline as a deployable service. The current implementation remains the fixed CPU-friendly reference; these changes are proposed next steps, not completed Phase 9 work.
