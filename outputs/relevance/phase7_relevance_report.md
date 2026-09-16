# Phase 7: Behavior-Derived Relevance Labels

## Frozen primary rule

The primary rule uses a 10-second click threshold and a 150-second deep-scroll threshold. These round cutoffs approximate the observed click and deep-scroll medians (10.5s and 152s). Bookmark and return visit are strong positives regardless of dwell because they are rare, intentional terminal outcomes in the supplied log.

- Grade 3: bookmark, return visit, or deep scroll with at least 150 seconds dwell.
- Grade 2: other deep scroll, or click with at least 10 seconds dwell.
- Grade 1: click with less than 10 seconds dwell.
- Grade 0: exposed without observed engagement; this does not mean clinically irrelevant.

| grade | grade_description | rows | share |
| --- | --- | --- | --- |
| 0 | exposed without observed engagement | 5690 | 79.1% |
| 1 | weak engagement | 444 | 6.2% |
| 2 | meaningful engagement | 710 | 9.9% |
| 3 | strong positive engagement | 346 | 4.8% |

## Coverage and aggregation

The labels cover all 7,190 exposed session-level rows and 7,037 observed query-content pairs. 350 of 500 queries have at least one positive judgment; 150 do not and must be excluded or reported separately for positive-dependent retrieval metrics.

For repeated query-content pairs, the retrieval judgment is the maximum observed grade. This treats an affirmative action as stronger evidence than non-action, while retaining exposure counts, mean grade, and a conflict flag. Unexposed pairs are absent and remain unjudged.

There are 55 repeated pairs with conflicting grades. They remain in the artifact with `conflicting_observations=True` for sensitivity analysis.

## Sensitivity scheme

A conservative scheme raises the click cutoff to 30s and the strong-scroll cutoff to 180s. It changes 442 session rows (6.1%) but never changes whether engagement was observed. An event-only hierarchy is also retained as a no-dwell reference. Later retrieval results should report the primary and conservative schemes.

| primary_grade | conservative_grade | rows | share |
| --- | --- | --- | --- |
| 0 | 0 | 5690 | 0.7914 |
| 1 | 1 | 444 | 0.0618 |
| 2 | 1 | 367 | 0.051 |
| 2 | 2 | 343 | 0.0477 |
| 3 | 2 | 75 | 0.0104 |
| 3 | 3 | 271 | 0.0377 |

## Interpretation boundary

These are weak, exposure-conditioned labels—not clinician relevance judgments. A zero can reflect non-examination, position bias, snippet satisfaction, competing relevant results, or session abandonment. Doctor ID, content popularity, inferred rank, session length, intent, language, and content type are not used in the grade rule. This avoids directly baking the largest measured propensity and exposure biases into the target, but it does not remove them.

## Artifacts

- Session-level labeled exposures: `/Users/hol/Documents/Task/doctor-search-service/data/processed/query_content_relevance.csv`
- Exposed-only query-content judgments: `/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/phase7_query_content_judgments.csv`
- Query coverage: `/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/phase7_query_coverage.csv`
- Metrics: `/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/phase7_relevance_metrics.json`
