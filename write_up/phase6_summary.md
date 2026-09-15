# Phase 6 Summary: Query-Content Behavioral Table

Phase 6 creates the impression-defined analytical table used by the later relevance and retrieval phases. Its grain is one `(query_id, content_id, session_id)` tuple. The table contains 7,190 unique rows and retains every supplied impression, including 5,690 rows with no observed engagement.

Query attributes come from the Phase 3 labeled query artifact and include intent, supplied disease/molecule/drug-class labels, therapeutic area, and all Phase 1.6 contextual slots. Content attributes include title, content/source type, language, publication year, word count, and supplied entities. Behavioral signals are aggregated into event flags, event count, timestamps, and dwell-time summaries before a one-to-one left join, preventing event rows from multiplying the analytical units.

All 1,500 behavioral signals resolve to an impression on the three-key grain. Doctor identifiers agree, all events occur after their matching impression, and the event flags reproduce the source counts: 944 clicks, 436 deep scrolls, 91 bookmarks, and 29 return visits. The resulting observed-engagement rate is 20.9%.

No relevance label is assigned in this phase. An unengaged impression is not automatically irrelevant because position/examination bias, competing relevant results, limited session time, and satisfaction without downstream action can all suppress engagement. Phase 7 will translate the retained signals into explicitly documented graded relevance evidence.

The table includes deterministic inferred serving order because no explicit rank field exists. It includes age group and renal-function group rather than exact age or eGFR; disease severity is absent because those slots were not implemented in Phase 1.6. Query intent remains model-assisted weak supervision rather than an independent clinician label.

## Relevance-Focused EDA

The behavior file records exactly one event type for every engaged analytical row. It therefore behaves like a terminal-outcome table rather than a complete event funnel: Phase 7 must use click, deep scroll, bookmark, and return visit as alternatives instead of requiring combinations such as click plus deep scroll.

Click dwell is short and right-skewed (median 10.5 seconds, p75 20 seconds, p90 34 seconds), and 66 clicks have zero dwell. Deep scroll is clearly separated in this dataset (minimum 61 seconds, median 152 seconds). A 30-second meaningful-click rule would retain only 133 of 944 clicks, compared with 241 at 20 seconds and 500 at 10 seconds, so the chosen cutoff should be accompanied by threshold sensitivity.

Inferred rank remains a behavioral confounder: rank-one engagement is 24.1%, compared with 20.4% across later ranks. In addition, 150 of 500 queries have no observed positive interaction, and 150 of 813 sessions have no engagement. Positive-dependent retrieval metrics must report this coverage and either exclude no-positive queries explicitly or evaluate them separately.

Behavior is not stable enough to be treated as immutable relevance truth. Among the 150 query-content pairs repeated across sessions, 49 switch between engaged and unengaged outcomes. Exact ICD-10 and ATC matches show modestly higher engagement, which provides a useful construct-validity check, but matched samples are small and confounded by the existing ranker. Content-type, intent, and language differences remain descriptive slices and should not be encoded directly into relevance grades.

## Additional Bias Diagnostics

The largest limitation is judgment-pool bias. Only 7,037 of the 172,500 possible query-content pairs are ever observed, giving 4.1% global behavioral coverage. The median query has labels for only 2.9% of the corpus. Unshown documents are unjudged rather than irrelevant, so evaluating retrieval against a dense matrix that assigns them grade 0 would favor the historical ranker's exposure pool.

Session and query opportunity also appear outcome-conditioned. All 21 five-result sessions have no engagement, whereas every 11- and 12-result session contains an event. All 150 no-positive queries occur among single-session queries, while every multi-session query has at least one positive. These patterns may reflect synthetic construction or collection policy and mean that session length, exposure count, and query frequency must not become relevance features.

Doctor engagement propensity is heterogeneous: the marginal rates range from 0% to 80%, with a 13.5-point interquartile range. Even among doctors with at least 50 impressions, rates range from 5.6% to 39.3%. Content exposure count is also strongly associated with engagement rate (Spearman rho 0.661), despite modest overall exposure concentration. These associations cannot distinguish user propensity, popularity, query mix, and relevance; doctor/content identifiers and historical frequency should therefore be reserved for grouped validation and bias monitoring.

Content language and content type are exposed approximately in proportion to their inventory shares, which argues against a severe corpus-representation skew on those dimensions. Query opportunity is less even: Treatment Change / Escalation receives 1.22 times its unique-query share of impressions, while Safety / Contraindication receives 0.87 times its share. Intent-level evaluation should report both unique-query and impression support.

Finally, inferred position contains measurement error. Serving timestamps tie for 1,713 impressions (23.8%), and order inside those ties is broken by impression ID. The logs span only 30 days in January 2025, so seasonality and longer-term drift cannot be estimated. Language-level engagement rates are similar in this sample, but that is insufficient evidence that multilingual retrieval is unbiased.
