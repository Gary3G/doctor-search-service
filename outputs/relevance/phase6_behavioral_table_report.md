# Phase 6: Query-Content Behavioral Table

## Result

The impression-defined table contains 7,190 unique `(query_id, content_id, session_id)` rows. All behavioral signals resolve to one of these rows, and every impression unit is retained.

- Engaged rows: 1,500 (20.9%)
- Rows with no observed engagement: 5,690
- Linked behavioral events: 1,500
- Queries / content / sessions: 500 / 345 / 813

## Event Coverage

| event_type | analytical_rows | share_of_all_rows | median_dwell_seconds | mean_dwell_seconds | max_dwell_seconds |
| --- | --- | --- | --- | --- | --- |
| click | 944 | 0.131 | 10.5 | 14.454 | 111 |
| scroll_deep | 436 | 0.061 | 152.0 | 150.966 | 239 |
| return_visit | 29 | 0.004 | 213.0 | 224.586 | 353 |
| save_bookmark | 91 | 0.013 | 94.0 | 100.67 | 179 |
| no_observed_engagement | 5690 | 0.791 | 0.0 | 0.0 | 0 |

## Join and Aggregation Contract

- Impressions define the row universe; signals use a left join.
- Query attributes come from the Phase 3 labeled query file, including Phase 1.6 slots.
- Content attributes come from the supplied content file.
- Event flags indicate whether an event type occurred; `dwell_time` sums event dwell seconds within the analytical unit.
- `inferred_rank` is deterministic serving order within a session-query and is not a supplied rank field.
- The builder validates foreign keys, doctor consistency, nonnegative dwell, and event-after-impression timing.

## Interpretation Boundary

Phase 6 assigns no relevance label. A row with no click or downstream event means only that no engagement was observed. It can reflect non-examination, position bias, competing results, or answer satisfaction and must not automatically be treated as irrelevant. Phase 7 will define graded relevance from these behavior features.

## Known Schema Limits

- Exact age, eGFR, and disease severity are absent because Phase 1.6 did not extract them; the table includes age group and renal-function group instead.
- Query intent is a Phase 3 model-assisted weak label, not independent clinician annotation.
- The raw data has no explicit position field, so only inferred serving order is available for later bias analysis.

## Artifacts

- Behavioral table: `/Users/hol/Documents/Task/doctor-search-service/data/processed/query_content_behavioral.csv`
- Metrics: `/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/phase6_behavioral_table_metrics.json`
- Event summary: `/Users/hol/Documents/Task/doctor-search-service/outputs/relevance/phase6_behavioral_event_summary.csv`
