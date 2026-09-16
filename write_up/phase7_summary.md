# Phase 7 and 7.5 Summary: Behavioral Relevance and Structured Compatibility

## Approach

Phase 7 converts the Phase 6 impression-level behavioral table into explicit graded weak relevance evidence. The primary rule uses only the observed terminal outcome and dwell time. It does not use inferred rank, doctor or content identity, exposure frequency, session length, intent, language, source type, or content type, which avoids directly encoding the strongest observed propensity and exposure biases into the target.

The frozen primary scheme uses round thresholds close to the observed medians: 10 seconds for a meaningful click (observed click median 10.5 seconds) and 150 seconds for a strong deep scroll (observed deep-scroll median 152 seconds). Grade 3 denotes a bookmark, return visit, or deep scroll lasting at least 150 seconds. Grade 2 denotes any other deep scroll or a click lasting at least 10 seconds. Grade 1 denotes a shorter click. Grade 0 means exposed without observed engagement; it does not establish clinical irrelevance.

At the session-exposure grain, the scheme assigns 5,690 grade-0 rows (79.1%), 444 grade-1 rows (6.2%), 710 grade-2 rows (9.9%), and 346 grade-3 rows (4.8%). Every one of the 7,190 impressions receives a label, and every one of the 1,500 observed engagement outcomes receives a positive grade.

For later retrieval evaluation, session observations are also aggregated to 7,037 exposed query-content pairs. The pair grade is the maximum observed session grade because a positive action supplies affirmative evidence, while a non-action may mean the result was not examined. The aggregate retains exposure count, mean grade, grade-specific counts, and a conflict flag. Fifty-five repeated pairs have conflicting grades. Unexposed query-content pairs are absent from the judgment artifact and remain unjudged.

Positive-dependent retrieval metrics have behavior-derived support for 350 of 500 queries. The remaining 150 queries have no observed positive and must be excluded explicitly or reported as a separate coverage slice. Of all queries, 307 have a grade-2-or-higher item and 188 have a grade-3 item.

A conservative sensitivity scheme raises the meaningful-click threshold to 30 seconds and the strong-scroll threshold to 180 seconds. It changes the strength assigned to 442 session rows (6.1%) while preserving the same positive-versus-no-observed-engagement boundary. An event-only hierarchy is retained as a second reference. Later retrieval results should be reported under both the primary and conservative schemes.

### Behavioral grading and Phase 6 evidence

Phase 6 contains 944 clicks, 436 deep scrolls, 91 bookmarks, and 29 return visits. Every engaged row has exactly one event type, so the rules treat events as alternative terminal outcomes rather than requiring a click followed by another action. All 66 zero-dwell clicks remain weak engagement. The three schemes differ only in engagement strength:

| Behavior | Primary median dwell | Conservative dwell | Event hierarchy |
| --- | ---: | ---: | ---: |
| Impression without engagement | 0 | 0 | 0 |
| Click below 10 seconds | 1 | 1 | 1 |
| Click from 10 to below 30 seconds | 2 | 1 | 1 |
| Click at least 30 seconds | 2 | 2 | 1 |
| Deep scroll below 150 seconds | 2 | 2 | 2 |
| Deep scroll from 150 to below 180 seconds | 3 | 2 | 2 |
| Deep scroll at least 180 seconds | 3 | 3 | 2 |
| Bookmark or return visit | 3 | 3 | 3 |

The medians provide reproducible cutoffs, but they do not validate clinical satisfaction. Event hierarchy supplies a reference independent of dwell measurement. Phase 6's position, doctor-propensity, popularity, and session-opportunity findings justify keeping those variables out of the grade rule. Excluding them does not remove their influence on observed behavior.

### Phase 7.5 and the CLEAR adaptation

Phase 7.5 computes structured compatibility for every combination of 500 queries and 345 content items. The project plan attributes its inspiration to CLEAR, described there as retrieving entity-relevant context from clinical notes. The implementation adopts the plan's extraction, selection, augmentation, and matching pattern for independent medical content. The attribution to Lopez et al., *npj Digital Medicine* (2025), still requires verification against the original publication before final submission; no reproduced CLEAR model or published performance result is claimed here.

| Methodological stage | Project implementation | Why it is useful |
| --- | --- | --- |
| Entity extraction | Supplied disease, molecule, drug-class, therapeutic-area, ICD-10, and ATC labels plus Phase 1.6 slots | Makes existing clinical structure available without another trained NER model. |
| Relevance-oriented selection | Separate exact entities, hierarchy, context, intent priors, and conflicts | Gives extracted fields distinct roles and avoids turning every field into a hard filter. |
| Entity augmentation | Normalize names; derive three-character ICD categories and five-character ATC classes | Identifies bounded clinical relatedness when exact identity differs. |
| Target matching | Compute overlap, coverage, hierarchy, context, and mismatch features | Turns clinical metadata into explicit ranking evidence. |
| Retrieval integration | Provide a fixed structured score for later BM25/hybrid reranking | Supplies a CPU-friendly feature whose downstream contribution can be tested. |
| Component evaluation | Retain separate feature groups for ablation | Supports separating extraction quality from ranking contribution; independent extraction evaluation remains outstanding. |

For example, apixaban and rivaroxaban can share an ATC class while differing at the molecule level. Exact mismatch and class compatibility are exposed simultaneously. The adaptation uses deterministic matching and supplied codes; external synonym ontologies, neural entity selection, and encoder training are not implemented.

Content context is extracted from titles because bodies and dedicated context fields are unavailable. Features cover age group, pregnancy, year, recency, dosing, route, renal and hepatic context, comparison, and prior treatment failure. Publication year supplies temporal evidence. Drug-profile content provides an additional dosing cue, and review content provides a comparison cue; these are heuristic proxies. An intent-to-content-type prior remains separate. Negation is carried as a query flag because entity-level negation scope is not implemented.

### Structured score definition

The compatibility matrix contains no behavioral relevance grade, click, dwell, rank, doctor, session, popularity, or exposure feature. Behavioral judgments are joined only for descriptive diagnostics; they do not determine matching features, thresholds, or weights.

The current entity coverage counts **populated entity dimensions**, not individual mentions. The four dimensions are disease, molecule, drug class, and therapeutic area. Any overlap within a dimension supplies credit. Exact coverage uses exact matches; augmented coverage also accepts ICD-category or ATC-class relations. A query containing multiple molecules therefore does not require each molecule to match for its molecule dimension to receive credit.

`entity_score = matched exact-or-hierarchical dimensions / populated query entity dimensions`

`context_score = matched active contextual constraints / active query contextual constraints`

`structured_score = (entity_score + context_score) / 2` when contextual constraints exist; otherwise it equals `entity_score`. A component with zero denominator receives zero. For example, entity score 0.75 and context score 0.50 produce structured score 0.625. Conflict rates and intent compatibility are retained separately and do not alter the initial score. No weight was chosen using behavioral grades.

Exact year matching compares requested year with publication year. Recency matching rewards publication within one year of the corpus maximum; publications more than two years older receive a recency-conflict flag. Missing title context receives no match credit and no explicit conflict. Consequently, missing evidence still reduces contextual coverage when a query constraint is active.

### Combining the phase outputs

Join the outputs on `(query_id, content_id)`: one-to-one for pair-level judgments and many-to-one for session exposures. Preserve all exposed judgments. If joining onto the full corpus matrix, leave unexposed relevance grades missing rather than assigning zero. The existing descriptive diagnostic joins the observed judgments and compatibility matrix; a combined review table with agreement flags is a proposed extension.

| Behavioral evidence | Structured evidence | Proposed review interpretation |
| --- | --- | --- |
| Strong engagement | Strong compatibility | Supported positive candidate. |
| Strong engagement | Low compatibility or potential conflicts | Disagreement: inspect behavioral noise, metadata, and extraction. |
| No engagement | Strong compatibility | Possible missed positive; examination and exposure uncertainty remain. |
| No engagement | Low compatibility | Weak negative candidate with incomplete evidence. |

These categories are not implemented confidence labels or calibrated probabilities. Their thresholds require validation. A proposed qualitative confidence layer could distinguish deliberate actions, sustained engagement, brief clicks, and uncertain zeros, but its reliability must be measured against independent judgments.

For later learning-to-rank, Phase 7 grades should be targets and Phase 7.5 features should be inputs. Adding structured score directly to behavioral grade would create a composite target. Evaluating an entity-aware ranker against that target could reward the same features used to manufacture its labels. Any composite-target experiment needs independent relevance judgments for evaluation, while the original behavioral grades remain available for sensitivity analysis.

## Key Findings

All 7,190 exposures receive labels, and all 1,500 observed engagement outcomes receive positive grades under every scheme.

| Scheme | Grade 0 | Grade 1 | Grade 2 | Grade 3 |
| --- | ---: | ---: | ---: | ---: |
| Primary median dwell | 5,690 | 444 | 710 | 346 |
| Conservative dwell | 5,690 | 811 | 418 | 271 |
| Event hierarchy | 5,690 | 944 | 436 | 120 |

The conservative scheme lowers 367 grade-2 rows to grade 1 and 75 grade-3 rows to grade 2. The 442 changes represent 6.1% of all exposures but 29.5% of engaged exposures, showing substantial sensitivity within the positive evidence.

### Coverage and repeated observations

| Measure | Result |
| --- | ---: |
| Observed query–content pairs | 7,037 |
| Pair grades 0 / 1 / 2 / 3 after maximum aggregation | 5,547 / 438 / 707 / 345 |
| Queries with any positive | 350 of 500 |
| Queries without any positive | 150 of 500 |
| Queries with grade 2 or higher | 307 of 500 |
| Queries with grade 3 | 188 of 500 |
| Repeated pairs with differing primary grades | 55 |
| Observed share of all possible pairs | 4.1% |

Phase 6 found 49 repeated pairs switching between engaged and unengaged outcomes. Phase 7 finds 55 pairs with differing grades because disagreement also includes changes in positive strength. Eligibility for positive-dependent metrics depends on the relevance threshold: using grade 2 or higher would reduce eligible queries from 350 to 307. That threshold and excluded-query count must accompany reported metrics.

### Structured compatibility and mean score

| Measure | Result |
| --- | ---: |
| Complete feature matrix | 172,500 pairs |
| Pairs with any exact or hierarchical entity match | 12,354 |
| Pairs with any contextual match | 14,278 |
| Queries with contextual constraints | 236 |
| Pairs with positive structured score | 25,300 (14.7%) |
| Mean structured score | 0.0561 |
| Exposed-pair Spearman correlation with behavioral grade | −0.0049 |

Mean structured score is the sum of all pair scores divided by 172,500. About 85.3% of pairs receive zero, pulling the average down. The mean describes the sparsity of matching evidence across the full corpus; it is neither 5.6% accuracy nor a relevance probability. Ranking usefulness depends on ordering documents within queries and improving retrieval metrics.

The near-zero observed association supplies no evidence of retrieval improvement. Limited metadata, weak labels, historical exposure, and feature design may each contribute. This finding warrants controlled evaluation and should not be dismissed or used to tune against an eventual test set.

### Failure cases

| Situation | Current behavior | Implication |
| --- | --- | --- |
| Multiple query molecules, only one matched | Any overlap satisfies the molecule dimension | Coverage can overstate fulfillment of compositional requests. |
| Different molecules share a class | Hierarchical molecule match and exact conflict can both be true | The initial scalar score may overreward a substitute molecule. |
| Required context absent from title | No match credit and no explicit conflict | The coverage score cannot distinguish missing evidence from an unaddressed constraint. |
| Generic review for comparison request | Content type supplies comparison credit | A review may not compare the requested alternatives. |
| Different entity metadata | Conflict indicator is set | Metadata mismatch does not establish clinical contradiction. |
| Query specifies both year and recency | Both contribute to context coverage | Correlated temporal constraints can receive additional influence. |

Entity-conflict flags occur for 170,709 pairs, approximately 99% of the complete matrix, reflecting their broad mismatch definition. They should not become blanket exclusion rules. Pregnancy-conflict and renal-conflict columns are currently constant false; explicit incompatible populations are not detected. Age and route conflicts compare extracted categories without proving that content excludes other populations or routes.

## Honest Evaluation

These phases establish reproducible weak labels and inspectable clinical features. They do not establish clinical relevance accuracy or improvements in Recall, MRR, or NDCG. The CLEAR-inspired approach has increased representational detail; retrieval benefit remains a hypothesis.

Behavior is conditioned on historical exposure. Grade 0 can reflect non-examination, snippet satisfaction, abandonment, competing relevant results, or limited opportunity. The 4.1% judgment coverage leaves most corpus pairs unjudged. Phase 6 found heterogeneous doctor propensity, content exposure associated with engagement, and session opportunity associated with outcomes. Serving timestamps tie for 23.8% of impressions, weakening inferred-rank propensity analysis. Excluding these variables from labels does not correct the observational biases.

Dwell thresholds partition a distribution without validating satisfaction: short interactions can answer a question and long interactions can reflect difficulty or distraction. Maximum aggregation gives affirmative evidence priority but also gives frequently exposed pairs more opportunities to acquire high grades. Exposure counts, mean grade, and conflict flags make this assumption auditable, rather than correcting it.

The current pair judgments aggregate across all sessions. Later temporal, doctor, or session splits must partition exposure records before reaggregating judgments. Reusing full-history maximum grades across training and evaluation could let the same event influence both. Evaluation split design remains a later phase.

Entity coverage is dimension-level rather than the individual-entity coverage described in the plan's example. Hierarchy matches receive full coverage credit, missing context reduces coverage, and initial temporal/content-type priors remain unvalidated. Numeric age, eGFR operators and values, sex, severity, dose values, and units are not evaluated compatibility dimensions here. Independent clinician annotations do not yet validate extraction accuracy or proposed confidence categories; the Phase 1.6 review scaffold is insufficient for independent precision, recall, or F1 claims.

At implementation completion, all 58 repository tests passed, including matrix uniqueness, behavior exclusion, score bounds, and selected matching cases. These verify software contracts rather than clinical correctness. The notebook, reports, examples, feature dictionary, and compressed full matrix provide reproducible inspection. The CLEAR bibliographic reference and precise methodological attribution still require verification before the final submission.

## What I Would Do Differently

I would first obtain independent relevance judgments across the four behavioral/structural agreement categories, including high-engagement mismatches, compatible unengaged documents, and unexposed documents. Reviewers should judge relevance without seeing the behavioral grade or structured score. This would test whether disagreement identifies noisy positives or missed positives and provide a target independent of the ranker's features.

I would evaluate extraction separately on annotated query and document examples. Categorical slots need precision, recall, and F1; supported numeric constraints need value, operator, and unit checks. Richer document text would improve contextual evidence. Explicit unknown, matched, and incompatible states would better represent title limitations. Renal and pregnancy conflicts should be supported by explicit evidence of incompatibility.

I would implement per-entity coverage for multi-disease and multi-molecule requests while avoiding double counting names and corresponding codes. Exact matches, hierarchy-only matches, and class matches should remain separate. I would reassess review/drug-profile proxies and distinguish metadata differences from explicit exclusion or contradiction. These changes would more closely implement the plan's compositional matching objective.

I would join both phase outputs into a review table while preserving the behavioral grade. Agreement flags and qualitative confidence levels should remain uncalibrated until independently evaluated. Positive-exposure rate and distinct-doctor count could supplement existing exposure/session counts for uncertainty analysis, without becoming automatic relevance bonuses. Maximum aggregation should be compared with alternatives within each evaluation partition.

I would freeze the evaluation protocol before tuning retrieval, partition exposure records before aggregation, and compare BM25 with additions of exact entities, hierarchy, context, intent, and conflict features. Learned weights would use training data and validation selection. Behavioral grades would supply weak targets, and the independent review sample would assess clinical relevance. Each comparison should report Recall@K, MRR, NDCG, judgment coverage, and no-positive-query counts.

I would repeat retrieval comparisons under primary, conservative, and event-only grades, explicitly stating binary thresholds where needed. Query-level bootstrap uncertainty and slices by intent, language, contextual constraints, and repeated-observation disagreement would help assess stability. A composite behavioral/structured target should only be considered with independent evaluation that avoids rewarding the same features used to create it.

Finally, I would verify the original CLEAR publication and document which components were adopted, adapted, or omitted. Richer ontology expansion, neural extraction, and learned reranking should be justified through controlled component experiments and available data. Later phases must establish whether the current clinical features improve search before claiming a CLEAR-derived performance gain.
