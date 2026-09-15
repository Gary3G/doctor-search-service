# Additional Bias Diagnostics for Behavioral Relevance

These diagnostics identify associations and censoring in the supplied logs. They do not establish causal bias because the existing ranker, query mix, doctor mix, and logging process are not randomized.

## 1. Judgment-pool and exposure bias

Only 7,037 of 172,500 possible query-content pairs are observed (4.1%); 165,463 pairs are unjudged. Treating every unobserved corpus item as grade 0 would convert lack of exposure into an irrelevant label and favor the historical ranker's pool.

Per-query coverage has median 2.9% and ranges from 1.4% to 22.3%. Phase 7 and retrieval evaluation should distinguish judged impressions from unjudged candidates and report pool coverage.

## 2. Outcome-conditioned session and query opportunity

| list_length | sessions | session_any_engagement_rate | per_impression_engagement_rate |
| --- | --- | --- | --- |
| 5.0 | 21.0 | 0.0 | 0.0 |
| 6.0 | 113.0 | 0.788 | 0.27 |
| 7.0 | 112.0 | 0.786 | 0.239 |
| 8.0 | 111.0 | 0.793 | 0.195 |
| 9.0 | 133.0 | 0.767 | 0.217 |
| 10.0 | 120.0 | 0.775 | 0.175 |
| 11.0 | 98.0 | 1.0 | 0.213 |
| 12.0 | 105.0 | 1.0 | 0.204 |

All 21 five-result sessions have no engagement, while every 11- and 12-result session has at least one engagement. Also, all 150 queries without a positive occur among single-session queries; every multi-session query has a positive. This pattern is consistent with outcome-conditioned sampling or synthetic construction, so exposure count and session length must not become relevance features.

## 3. Doctor propensity bias

Doctor-level engagement ranges from 0.0% to 80.0%; the interquartile range is 13.5%. Among doctors with at least 50 impressions, rates still range from 5.6% to 39.3%. The marginal doctor association is the largest screen effect (Cramer's V=0.224). This can reflect user propensity, query mix, or logging differences—not intrinsic content relevance.

## 4. Content popularity and presentation bias

Content exposure is not extremely concentrated (Gini=0.173; top decile receives 16.1% of impressions), but exposure count and observed engagement rate are strongly correlated (Spearman rho=0.661). Because positive events are part of the logged impression pool, popularity and relevance cannot be separated from these data alone. Content ID, source type, and historical exposure frequency should not directly set grades.

Source type and content type also show marginal engagement differences. These may reflect attractiveness, snippet quality, ranker policy, or query mix; use them as evaluation slices rather than label weights.

At the inventory level, content language and content type are exposed roughly in proportion to their corpus shares. Query opportunity is less even: Treatment Change / Escalation is exposed at 1.22 times its query-inventory share, while Safety / Contraindication is exposed at 0.87 times its share. Intent-level metrics should therefore report both query counts and exposure counts.

## 5. Inferred-rank measurement error

| impressions | tied_timestamp_groups | impressions_in_tied_groups | share_impressions_in_tied_groups | extra_rows_beyond_first_in_ties | largest_tied_group | tie_breaker |
| --- | --- | --- | --- | --- | --- | --- |
| 7190 | 765 | 1713 | 0.238 | 948 | 7 | impression_id |

Serving timestamps tie for 23.8% of impressions. Their internal order is resolved by impression ID, so `inferred_rank` is partly arbitrary. Any propensity correction should be a sensitivity analysis unless a true position field becomes available.

## 6. Temporal coverage

| week | impressions | engaged | engagement_rate | engagement_ci95_low | engagement_ci95_high |
| --- | --- | --- | --- | --- | --- |
| 2024-12-30/2025-01-05 | 1009 | 237 | 0.235 | 0.21 | 0.262 |
| 2025-01-06/2025-01-12 | 1568 | 295 | 0.188 | 0.17 | 0.208 |
| 2025-01-13/2025-01-19 | 1796 | 357 | 0.199 | 0.181 | 0.218 |
| 2025-01-20/2025-01-26 | 1828 | 397 | 0.217 | 0.199 | 0.237 |
| 2025-01-27/2025-02-02 | 989 | 214 | 0.216 | 0.192 | 0.243 |

The logs cover only 30 days in one calendar month. Weekly engagement ranges from 18.8% to 23.5%, but seasonality and drift cannot be estimated from this window.

## Marginal association screen

| variable | groups | cramers_v | chi_square_p_value_naive | rate_range |
| --- | --- | --- | --- | --- |
| doctor_id | 118 | 0.2243 | 0.0 | 0.8 |
| content_source_type | 12 | 0.1165 | 0.0 | 0.2251 |
| session_length | 8 | 0.0894 | 0.0 | 0.2699 |
| content_type | 6 | 0.0831 | 0.0 | 0.1551 |
| query_intent | 11 | 0.062 | 0.0021 | 0.1531 |
| content_publication_year | 6 | 0.0512 | 0.0021 | 0.0542 |
| week | 5 | 0.0381 | 0.0338 | 0.0467 |
| inferred_rank | 12 | 0.0351 | 0.6349 | 0.0539 |
| content_language | 3 | 0.0182 | 0.3046 | 0.0172 |
| query_language | 3 | 0.0147 | 0.4622 | 0.0136 |

These p-values treat impression rows as independent even though rows are clustered by session, doctor, query, and content. They are included only as a screen; effect sizes and domain plausibility matter more.

## Phase 7 safeguards

- Never label unshown query-content pairs as irrelevant; track them as unjudged.
- Keep exposure count, session length, doctor ID, content ID, source type, and inferred rank out of the grade rule.
- Use those fields for stratification, grouped splits, propensity sensitivity, and monitoring instead.
- Preserve session-level evidence and aggregate repeated pairs with exposure and disagreement fields.
- Report the 150 no-positive queries separately from queries eligible for positive-dependent metrics.
- Avoid double-counting event type and dwell as independent evidence; their distributions are tightly coupled.
- Use query- or session-clustered uncertainty estimates rather than naive impression-level p-values.
- Treat language analyses as inconclusive: observed rates are similar, but the sample cannot rule out retrieval-quality bias.
