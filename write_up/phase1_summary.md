# Phases 1, 1.5, and 1.6 Summary

## Approach

Phase 1 focused on understanding the four raw datasets before modeling. I audited row counts, IDs, missingness, duplicates, language and therapeutic-area distributions, query/content entity coverage, near duplicates, behavioral-event patterns, dwell time, impression overlap, and engagement rates. I also prepared a 120-query manual review sample with provisional audit-only intent cues and missing-structure notes.

Phase 1.5 converted the audit into an extended query schema. I selected contextual slots only when they appeared repeatedly, could materially affect relevance, could be extracted reliably, and had some path to content-side matching. I kept supplied NER, contextual slots, and intent classification separate.

Phase 1.6 populated the selected contextual slots with deterministic rules and produced an enriched query table for all 500 queries. I also generated coverage summaries, extraction examples, and a manual QA sample rather than assuming the rules are fully correct.

## Key Findings

The raw data is clean at a structural level: `queries.csv` has 500 rows, `content.csv` has 345 rows, `behavioral_signals.csv` has 1,500 rows, and `impressions.csv` has 7,190 rows, with no missing values in the supplied files. Query IDs and content IDs are unique. The query set is multilingual: 222 EN, 173 MIXED, and 105 ID.

Structured matching is feasible because queries and content both include disease, molecule, drug class, therapeutic area, and language. However, useful clinical constraints remain embedded in query text, especially dosing context, recency/year, pregnancy, renal or hepatic impairment, age group, comparison, negation, and prior treatment failure.

For Phase 1.5, I selected 11 contextual columns: `age_group`, `pregnancy_status`, `year`, `recency_flag`, `dose_context_flag`, `route`, `renal_function_group`, `hepatic_impairment_flag`, `comparison_flag`, `negation_flag`, and `prior_treatment_failure_flag`. I deferred numeric age, sex, numeric dose, duration, lab values, explicit eGFR, and severity because the observed evidence was absent, sparse, or too ambiguous.

For Phase 1.6, 242 of 500 queries received at least one contextual slot. The most common extracted signal was `dose_context_flag` with 93 rows, followed by `recency_flag` with 49, `pregnancy_status` with 37, `year` with 29, `age_group` with 25, `prior_treatment_failure_flag` with 24, and `renal_function_group` with 22.

Behavioral data should be used carefully. Only 20.9% of impressions had engagement, but unengaged impressions are not automatically irrelevant because of position bias, examination bias, answer satisfaction without click, competing relevant results, and limited session time.

## Honest Evaluation

The audit is useful and reproducible, but it is still mostly descriptive. It identifies dataset structure and candidate signals, but it does not prove that any slot improves retrieval yet. The extraction rules are intentionally simple and interpretable, which is good for review, but they will miss paraphrases and may over-trigger in edge cases.

The strongest extracted slots are high-precision lexical constraints such as pregnancy, year, dosing context, renal/hepatic impairment, comparison, and prior failure. The weakest are sparse fields such as route and negation. Negation is especially limited because the pipeline only extracts a query-level flag, not which entity or condition is negated.

I also tightened one important boundary: broad Chronic Kidney Disease mentions are already captured by supplied disease NER, so Phase 1.6 no longer treats every CKD disease mention as a renal-function context. Only renal impairment, renal dose, renal adjustment, or similar contextual phrases populate `renal_function_group`.

## What I Would Do Differently

I would create a small gold QA set earlier, before finalizing the extraction rules. Even 50 manually labeled queries for contextual slots would let me estimate precision and recall instead of only reporting coverage.

I would separate content-side extraction next. Right now, content matchability is assessed mostly from title and metadata. A stronger retrieval system should extract the same contextual slots from content text or content metadata, then evaluate whether slot-aware matching improves ranking.

I would improve negation and comparison parsing before using them heavily in ranking. Query-level flags are useful for slice analysis, but entity-level scope would be safer for production retrieval.

Finally, I would keep Phase 1.6 rule-based for the submitted CPU-first system, but use the QA errors to decide whether a lightweight model-assisted extractor is worth adding later.
