# Phase 6 Relevance-Focused EDA

## What the behavior fields mean

All 1,500 engaged rows have exactly one event type. There are no click-plus-scroll or click-plus-bookmark rows at the Phase 6 grain. The safest reading is that the file stores mutually exclusive terminal outcomes, not a complete event funnel. Phase 7 rules should therefore use event alternatives rather than require event conjunctions.

## Dwell-time evidence

Click dwell is short and right-skewed: median 10.5s, p75 20.0s, p90 34.0s, with 66 zero-dwell clicks. Deep-scroll dwell is separated from clicks (minimum 61s, median 152s). Bookmarks and return visits are rare but intentional actions and should remain strong signals without an extra dwell requirement.

| event_type | threshold_seconds | below_threshold | at_or_above_threshold | share_at_or_above |
| --- | --- | --- | --- | --- |
| click | 5 | 297 | 647 | 0.685 |
| click | 10 | 444 | 500 | 0.53 |
| click | 20 | 703 | 241 | 0.255 |
| click | 30 | 811 | 133 | 0.141 |
| scroll_deep | 90 | 76 | 360 | 0.826 |
| scroll_deep | 120 | 142 | 294 | 0.674 |
| scroll_deep | 150 | 210 | 226 | 0.518 |
| scroll_deep | 180 | 285 | 151 | 0.346 |

A 30-second meaningful-click threshold retains only 133 of 944 clicks (14.1%); 20 seconds retains 241 (25.5%), and 10 seconds retains 500 (53.0%). These cutoffs should be compared in sensitivity analysis rather than presenting one as clinically validated.

## Position and missing-positive bias

Rank 1 engagement is 24.1% versus 20.4% for later ranks, a 3.7% absolute difference. Rates are not monotonically decreasing after rank 1, but inferred position is still a confounder and should be retained for propensity-aware sensitivity checks.

There are 150 of 813 sessions and 150 of 500 queries with no observed engagement. Those queries have no behavior-derived positive for retrieval metrics such as Recall or NDCG; report their coverage separately rather than silently treating all shown content as negative.

## Repeatability and construct validity

| repeatability | query_content_pairs | total_exposures | total_engaged_exposures | share_of_pairs | engagement_rate |
| --- | --- | --- | --- | --- | --- |
| repeated_always_engaged | 10 | 20 | 20 | 0.001 | 1.0 |
| repeated_mixed_engagement | 49 | 100 | 49 | 0.007 | 0.49 |
| repeated_never_engaged | 91 | 183 | 0 | 0.013 | 0.0 |
| single_exposure | 6887 | 6887 | 1431 | 0.979 | 0.208 |

Only 150 query-content pairs repeat across sessions, and 49 of them switch between engaged and unengaged outcomes. Preserve the session-level labels; if Phase 7 also creates a query-content aggregate, include exposure count and a conflict indicator rather than using a single event as immutable truth.

| dimension | matched | impressions | engagement_rate | engagement_ci95_low | engagement_ci95_high |
| --- | --- | --- | --- | --- | --- |
| icd10_code | False | 7054 | 0.207 | 0.198 | 0.217 |
| icd10_code | True | 136 | 0.287 | 0.217 | 0.368 |
| atc_code | False | 7073 | 0.208 | 0.199 | 0.217 |
| atc_code | True | 117 | 0.256 | 0.186 | 0.342 |
| atc_class | False | 7043 | 0.208 | 0.198 | 0.217 |
| atc_class | True | 147 | 0.252 | 0.188 | 0.328 |
| therapeutic_area | False | 6721 | 0.208 | 0.199 | 0.218 |
| therapeutic_area | True | 469 | 0.211 | 0.177 | 0.25 |
| language_exact | False | 4602 | 0.205 | 0.194 | 0.217 |
| language_exact | True | 2588 | 0.215 | 0.199 | 0.231 |

Exact ICD-10, ATC-code, and ATC-class matches have somewhat higher observed engagement than nonmatches, while therapeutic-area and exact-language matches show little separation. Match groups are small and behavior is confounded by the existing ranker, so this is a sanity check—not evidence for relevance labels.

## Illustrative Phase 7 sensitivity schemes

| scheme | grade | rows | share_all_rows | share_engaged_rows |
| --- | --- | --- | --- | --- |
| event_hierarchy | 0 | 5690 | 0.791 | 0.0 |
| event_hierarchy | 1 | 944 | 0.131 | 0.629 |
| event_hierarchy | 2 | 436 | 0.061 | 0.291 |
| event_hierarchy | 3 | 120 | 0.017 | 0.08 |
| median_dwell_split | 0 | 5690 | 0.791 | 0.0 |
| median_dwell_split | 1 | 444 | 0.062 | 0.296 |
| median_dwell_split | 2 | 710 | 0.099 | 0.473 |
| median_dwell_split | 3 | 346 | 0.048 | 0.231 |
| conservative_dwell | 0 | 5690 | 0.791 | 0.0 |
| conservative_dwell | 1 | 811 | 0.113 | 0.541 |
| conservative_dwell | 2 | 418 | 0.058 | 0.279 |
| conservative_dwell | 3 | 271 | 0.038 | 0.181 |

The schemes above are diagnostic only and are not written back to the behavioral table. They show how strong-positive support changes when dwell thresholds are introduced. Phase 7 should freeze one primary scheme, retain at least one sensitivity scheme, and report label coverage and ranking metrics under both.

## Recommended Phase 7 design constraints

- Treat bookmark and return visit as alternative strong-positive outcomes.
- Treat deep scroll as stronger evidence than a bare click; do not require a separate click flag.
- Split clicks by observed dwell quantiles and test at least two thresholds (for example 10s and 20s or 30s).
- Call grade 0 `exposed without observed engagement`, not `irrelevant`.
- Keep inferred rank, doctor, and session identifiers available for bias and robustness analyses.
- Exclude or separately report queries with no positive grade when computing positive-dependent retrieval metrics.
- Report results by intent, language, and content type, but do not encode their raw engagement rates into labels.
