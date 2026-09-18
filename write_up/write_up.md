# Project Learnings: Multilingual Medical Query Understanding and Retrieval

## Executive Summary

This project asked whether a practical search system could infer a doctor's information need from a short English, Bahasa Indonesia, or mixed-language query and use that understanding to retrieve more relevant medical content than a lexical baseline.

The project produced an end-to-end research pipeline covering data audit, contextual slot extraction, intent-taxonomy design, model-assisted intent labeling, intent classification, behavior-derived relevance, BM25 and dense retrieval, structured clinical matching, intent-aware reranking, slice analysis, failure review, model selection, and production design.

The selected runtime-oriented system combines:

- title-only BM25;
- frozen multilingual MiniLM similarity;
- disease, molecule, drug-class, therapeutic-area, and ICD/ATC compatibility;
- deterministic contextual compatibility;
- the selected intent classifier; and
- a validation-selected hard intent/content-type compatibility bonus.

Its scoring rule is:

```text
base_score = mean(
    normalized_bm25,
    normalized_dense_similarity,
    entity_compatibility,
    contextual_compatibility
)

final_score = base_score
            + 0.25 * predicted_intent_content_type_compatibility
```

The selected system achieved temporal validation/test NDCG@10 of **0.03146 / 0.01851**, compared with **0.02400 / 0.01021** for BM25 and **0.02727 / 0.01105** for the same hybrid without intent. The point estimate supports intent as a useful signal, especially for interaction and dosing queries, but the improvement was concentrated in a small number of queries and its paired test interval included zero.

The most important conclusion is therefore not that the project produced a clinically ready ranker. It did not. The useful result is a better understanding of the problem:

1. Query intent and clinical constraints matter, but they help different query slices in different ways.
2. Exact clinical conjunctions matter more than independent additive matches. A result matching the right dosing template but the wrong molecule is not a good answer.
3. Title-only content is inadequate for many dosing, renal, pregnancy, monitoring, and interaction questions.
4. Behavioral logs provide useful weak evidence, but sparse exposure and position-biased engagement are not clinical relevance judgments.
5. More model capacity did not solve these data and evaluation limitations. A learned reranker, two cross-encoders, and a biomedical embedding replacement all failed to demonstrate a stable improvement over the simpler frozen system.

The best next investment is not another round of weight tuning. It is more complete behavioral evidence, section-level content, conjunction-aware matching, and a genuinely untouched end-to-end temporal evaluation. Clinician adjudication would be valuable if resources allow, but it is treated here as an optional high-cost validation layer rather than a prerequisite.

---

## 1. Problem Framing

The retrieval target is a clinician's information need, not merely lexical similarity. A short query such as `renal dose adjustment of Losartan in CKD` contains at least four distinct requirements:

- a disease or clinical setting;
- a specific molecule;
- a dosing information need; and
- a renal-function constraint.

A document can overlap heavily with that query while answering the wrong question. It may discuss Losartan safety rather than dosing, renal dosing for another molecule, or general CKD management. Medical search therefore requires both broad recall and precise compatibility.

The problem is made harder by five properties of the supplied data:

- queries are short, multilingual, and often code-switched;
- the supplied entities do not capture all clinically important constraints;
- the content corpus exposes titles and metadata rather than answer-bearing sections or full text;
- there are no human relevance judgments; and
- historical behavior is available only for previously exposed content and is affected by rank, examination, and engagement bias.

The practical objective was consequently narrower than “build a medically correct search engine.” It was to construct an auditable research system, measure whether structured query understanding adds signal beyond BM25, identify where the evidence is trustworthy, and describe what would be required before production use.

### Data in scope

| Dataset | Rows | Main role |
| --- | ---: | --- |
| Queries | 500 | Query text, language, supplied clinical entities, and therapeutic area |
| Content | 345 | Content titles, types, metadata, and supplied clinical entities |
| Impressions | 7,190 | Query-content exposure evidence |
| Behavioral events | 1,500 | Click, deep-scroll, bookmark, and return evidence |

The query language mix is 222 English, 173 mixed-language, and 105 Bahasa Indonesia queries. The raw tables contain no missing values, and query/content IDs are unique. The clean schema made experimentation straightforward, but it should not be confused with realistic production traffic: queries are strongly template-patterned and all supplied test queries contain both disease and drug metadata.

### Design principles

The work followed four principles:

1. **Separate concepts with different meanings.** Entities describe clinical topics, slots describe constraints, and intent describes the requested information. They were not collapsed into one label.
2. **Freeze simple references before adding complexity.** BM25, relevance rules, split definitions, and deterministic tie-breaking were fixed before retrieval extensions.
3. **Add signals incrementally.** Sparse, dense, entity, context, and intent contributions were tested separately and through removal ablations.
4. **Treat every proxy honestly.** Algorithmic agreement was not called clinical annotation, unjudged content was not called irrelevant, and descriptive test results were not presented as pristine confirmation.

---

## 2. Approach

### 2.1 Data audit and query decomposition

The first stage profiled data quality, query length, languages, entity coverage, behavioral patterns, duplicate candidates, exposure, and engagement. A 120-query review sample was used to identify clinical information that existed in the text but not in the supplied entity columns.

[Lopez et al. (2025)](https://doi.org/10.1038/s41746-024-01377-1) shaped the decomposition goal through CLEAR's central finding that clinically relevant entities should actively determine what evidence is retrieved, rather than remain descriptive metadata. CLEAR operates on chunks from long clinical notes; this project adapted only that retrieval principle. Supplied entities were preserved as topic evidence, while the audit identified additional query constraints that would later be normalized and matched separately.

Eleven contextual fields were selected because they were repeated, potentially relevance-changing, and reasonably extractable:

- age group;
- pregnancy status;
- year;
- recency request;
- dosing context;
- route;
- renal-function context;
- hepatic impairment;
- comparison;
- negation; and
- prior treatment failure.

Deterministic bilingual rules populated at least one contextual slot for 242 of 500 queries. The most common were dosing context (93), recency (49), pregnancy (37), year (29), age group (25), prior treatment failure (24), and renal context (22).

Numeric age, sex, dose value, duration, laboratory values, eGFR, and disease severity were deferred because the observed support was absent, sparse, or ambiguous. That restraint was deliberate: an empty field is preferable to an unreliable clinical fact that later becomes a ranking constraint.

### 2.2 Intent-taxonomy adaptation

The taxonomy began with the physician-search categories reported by [Monsalve et al. (2026)](https://doi.org/10.64898/2026.06.26.26356340), including Management / Treatment, Diagnosis, Work-up / Test Selection, Test Interpretation, Pharmacotherapy, Evidence / Guideline Lookup, Procedures, Epidemiology / Prognosis, Patient Communication, and Other / Ambiguous. This paper provided the top-level physician-oriented seed, not a fixed answer. It is a preprint, and its categories were treated as hypotheses to test against the Docquity queries.

[Liang et al. (2025)](https://doi.org/10.1038/s41598-025-25783-x) informed the finer candidate boundaries and known confusions. Its intent distinctions—particularly therapy, precautions/safety, effect/efficacy, diagnosis, disease description, etiology, prognosis, and interpretation—helped identify where a broad Monsalve category might need to split or where adjacent intents might remain difficult to separate.

The observed data then determined what to retain, split, merge, rename, or add. Disease, molecule, and drug-class mentions were delexicalized so that topic would not masquerade as intent.

The analysis combined:

- unigram/bigram TF-IDF for interpretable lexical cues;
- frozen multilingual MiniLM embeddings for semantic prototypes;
- ambiguity margins between the two nearest intent definitions;
- agglomerative and KMeans cluster comparisons;
- a 15-cluster selected agglomerative solution;
- structured feature profiles by cluster; and
- manual review of representative, low-margin, and cross-class-neighbor queries.

The literature schema was adapted rather than copied:

| Published seed idea | Observed query structure | Final decision |
| --- | --- | --- |
| Broad Pharmacotherapy | Distinct dosing, safety, interaction, comparison, efficacy, and monitoring patterns | Split into retrieval-relevant sub-intents |
| Broad Management / Treatment | Initial selection, failure-driven changes, and prophylaxis/maintenance had different cues and preferred content | Split into three operational intents |
| Evidence Synthesis / Research | Queries predominantly requested guidelines, current evidence, or year-specific updates | Rename to Guideline / Evidence Lookup |
| Risk stratification | Small but coherent pocket with monitoring and response language | Merge into Monitoring / Response / Risk Assessment |
| Mechanistic questions | Coherent “mechanism,” “cara kerja,” and pathophysiology cluster | Add Mechanism / Background Knowledge |
| Diagnosis, procedures, and patient education | No sufficiently coherent, supported query pocket | Do not retain as learnable classes |

The resulting 11 intents were:

| Intent | Final query count |
| --- | ---: |
| Management / Treatment Selection | 58 |
| Dosing / Administration | 96 |
| Safety / Contraindication | 84 |
| Interaction / Combination | 21 |
| Comparative Treatment Choice | 23 |
| Monitoring / Response / Risk Assessment | 33 |
| Efficacy / Outcomes | 20 |
| Guideline / Evidence Lookup | 59 |
| Treatment Change / Escalation | 46 |
| Prophylaxis / Maintenance | 31 |
| Mechanism / Background Knowledge | 29 |

This was one of the strongest parts of the project because each class had a stated definition, inclusion and exclusion rules, boundary examples, likely content preference, and an explicit derivation from the seed taxonomy. It was still a model-assisted analyst taxonomy, not independently validated clinical ground truth.

### 2.3 Intent labeling

A combined strategy labeled all 500 queries:

- ordered bilingual rules captured explicit information-need cues;
- prototype similarity compared each delexicalized query with the 11 intent definitions; and
- cluster assignments supplied an independent structural view of the query space.

A 60-query pilot was expanded to a 180-query reviewed reference subset using uncertainty and coverage sampling. Every intent had at least 12 reviewed examples. The other 320 labels used the frozen three-signal policy. Explicit rule boundaries were retained when semantic signals disagreed, and disagreements, confidence, provenance, and review flags were preserved rather than hidden.

The review design follows the face-validity principle used by [Monsalve et al. (2026)](https://doi.org/10.64898/2026.06.26.26356340): inspect a stratified sample rather than accept an automatically induced taxonomy at face value. Here, the sample deliberately emphasized rare intents, multilingual coverage, low semantic margins, three-signal disagreements, multi-cue boundaries, and cluster/model disagreements. This was a project-specific adaptation, not a reproduction of the paper's annotation process.

Three-signal Fleiss' kappa increased from 0.324 to 0.357 after cluster-to-intent mapping. This is algorithmic agreement, not inter-annotator agreement. No independent second clinician labeled the data, and no query exercised the `Other / Ambiguous` fallback.

### 2.4 Intent classification

The modeling strategy was directly informed by [Liang et al. (2025)](https://doi.org/10.1038/s41598-025-25783-x). That paper found complementary value in three branches: contextual semantics, sentence-level TF-IDF, and category-centroid TF-IDF, combined with adaptive attention. It also emphasized class imbalance, Macro F1, per-class performance, and confusion among semantically adjacent intents.

The taxonomy-support model adapted the three-branch idea using multilingual semantic representations, a 200-feature TF-IDF branch, category-centroid TF-IDF, shared projection, attention fusion, and soft-prototype refinement. Because this project did not begin with supervised gold intents, weak anchors replaced the paper's true labels during taxonomy exploration; those agreement scores were not interpreted as clinical accuracy.

For the final classifier comparison, the paper's broader finding—that lexical, semantic, and category/structured signals can be complementary—became a testable hypothesis rather than an assumed architecture choice. The lexical baseline used word TF-IDF and class-balanced Logistic Regression. Its five-fold row-stratified Macro F1 was 0.981, but its template-held-out Macro F1 fell to 0.509. This gap revealed substantial template leakage and changed the model-selection criterion.

The improved experiments compared prototype similarity, lexical plus entity features, lexical plus entity/context features, frozen multilingual embeddings, and embeddings plus structured features.

| Model | Row-CV Macro F1 | Template-held-out Macro F1 |
| --- | ---: | ---: |
| TF-IDF baseline | **0.981** | 0.509 |
| Prototype similarity | 0.683 | 0.651 |
| TF-IDF + supplied entities | 0.969 | 0.514 |
| TF-IDF + entities + context | 0.961 | 0.678 |
| Frozen multilingual embeddings | 0.969 | 0.794 |
| **Frozen embeddings + entities + context** | 0.970 | **0.842** |

The final classifier sacrificed a small amount of row-CV performance for a large improvement on unseen templates. This was the right tradeoff: the row-CV headline was impressive but measured replication of recurring weak-label patterns more than robust generalization.

### 2.5 Weak relevance supervision

Because no human query-document relevance labels were supplied, impressions and behavioral events were joined into exposure-level records. The primary grades were:

| Grade | Behavioral evidence |
| ---: | --- |
| 0 | Impression without recorded engagement |
| 1 | Short click |
| 2 | Click of at least 10 seconds or deep scroll |
| 3 | Bookmark, return, or deep scroll of at least 150 seconds |

Conservative dwell thresholds and an event-hierarchy scheme were retained as sensitivity variants. The primary scheme labeled all 7,190 exposures as 5,690 grade 0, 444 grade 1, 710 grade 2, and 346 grade 3. After maximum aggregation there were 7,037 observed query-content pairs; 350 of 500 queries had at least one positive and 150 did not.

Only 4.1% of all possible query-content pairs were observed. Unexposed pairs remained unjudged. Retrieval metrics assigned them zero computational gain because conventional NDCG requires a gain value, but the project did not redefine them as negatives.

A behavior-independent compatibility matrix was also computed for all 172,500 query-content pairs. It included exact and hierarchical entity overlap, contextual matching, coverage, and conflicts. The mean structured score was 0.0561, and its exposed-pair Spearman correlation with behavioral grade was -0.0049. That near-zero correlation was important: clinical structure and observed engagement measured different things, and neither should silently replace the other.

This matrix implemented the matching stage inspired by CLEAR in [Lopez et al. (2025)](https://doi.org/10.1038/s41746-024-01377-1). Disease, molecule, drug-class, therapeutic-area, ICD-10, and ATC evidence was normalized; bounded ICD/ATC hierarchy matches supplied controlled augmentation; and exact match, hierarchy, context, coverage, and conflict remained inspectable features. Unlike CLEAR, the matrix ranked independent content items and did not retrieve note chunks for an extraction model.

### 2.6 Evaluation protocol

The primary protocol split sessions chronologically at approximately 60/20/20 and rebuilt behavior-derived labels independently inside each partition. It assigned 4,287 exposures to train, 1,444 to validation, and 1,459 to test. The temporal validation/test partitions each contained 139 queries; 113 validation queries and 110 test queries had observed positives.

Two sensitivity protocols measured query generalization:

- a query-held-out split; and
- a duplicate-aware query-held-out split using normalized character 3–5 gram similarity at a 0.95 threshold.

Every impression and behavioral event was assigned exactly once under each protocol, with no session or impression overlap. The duplicate-aware split kept the three detected near-duplicate pairs within partitions. Metrics included graded NDCG, Recall@K, hit rate, MRR, behavioral-label coverage, no-positive-query counts, bootstrap intervals, and language/intent/context slices.

### 2.7 Retrieval experiments

The fixed baseline was BM25 over content titles only, using Unicode normalization, case folding, word/number tokenization, `k1=1.5`, `b=0.75`, and content ID for deterministic tie-breaking.

CLEAR's component-evaluation principle from [Lopez et al. (2025)](https://doi.org/10.1038/s41746-024-01377-1) shaped the experiment order. Entities were not assumed to help simply because entity-guided retrieval worked in the paper's clinical-note extraction task. BM25, dense similarity, exact/hierarchical entity compatibility, contextual compatibility, and intent were added incrementally and later removed in ablations. This tested whether the transferable CLEAR hypothesis actually held for doctor-query-to-content ranking.

The principal retrieval matrix was:

| ID | Configuration | Validation NDCG@10 | Test NDCG@10 | Test Recall@10 | Test MRR@10 |
| --- | --- | ---: | ---: | ---: | ---: |
| R-B0 | BM25 | 0.02400 | 0.01021 | 0.01609 | 0.02016 |
| R-E1 | BM25 + entities | 0.02899 | 0.01303 | 0.02359 | 0.02379 |
| R-E2 | BM25 + entities + context | 0.02966 | 0.01477 | 0.03154 | 0.02389 |
| R-E3 | Frozen dense | 0.03079 | 0.01584 | 0.02972 | 0.01735 |
| R-E4 | BM25 + dense | 0.02545 | 0.01651 | 0.03528 | 0.02304 |
| R-E5 | Hybrid + entities | 0.02467 | 0.01220 | 0.02177 | 0.02221 |
| R-E6 | Hybrid + entities + context | 0.02727 | 0.01105 | 0.02063 | 0.02091 |
| R-E7 | R-E6 + assisted intent | **0.03146** | **0.01940** | **0.04801** | **0.02857** |

The runtime intent-retrieval experiment then replaced the assisted label with deployable intent predictions. The saved classifier agreed with assisted intent on 85.8% of all queries.

| Intent input | Validation NDCG@10 | Test NDCG@10 | Test Recall@10 | Test MRR@10 |
| --- | ---: | ---: | ---: | ---: |
| No intent | 0.02727 | 0.01105 | 0.02063 | 0.02091 |
| Predicted soft intent | 0.03084 | 0.01115 | 0.02063 | 0.02136 |
| **Predicted hard intent** | **0.03146** | **0.01851** | **0.04346** | **0.02766** |
| Assisted intent | **0.03146** | **0.01940** | **0.04801** | **0.02857** |

Hard predicted intent was selected. Its test NDCG@10 improvement over no intent was +0.00746, with a paired 95% bootstrap interval of [-0.00034, 0.01763]. Eight eligible queries improved, two worsened, and 100 were unchanged. This is a useful but localized signal, not proof of a global gain.

### 2.8 Optional model challengers

More complex approaches were evaluated against the frozen predicted-intent hybrid system:

| System | Validation NDCG@10 | Test NDCG@10 | Decision |
| --- | ---: | ---: | --- |
| **Frozen predicted-intent hybrid** | 0.03146 | **0.01851** | Retain |
| Learned logistic reranker | **0.03363** | 0.01653 | Reject; validation gain did not transfer |
| Multilingual cross-encoder | 0.02723 | 0.01545 | Reject |
| MedCPT cross-encoder | 0.03027 | 0.01755 | Reject |
| Full S-PubMedBERT replacement | 0.02869 | 0.01488 | Reject |

The result was a useful exercise in restraint. The hybrid findings in [Liang et al. (2025)](https://doi.org/10.1038/s41598-025-25783-x) motivated testing complementary representations, while CLEAR motivated testing entity-guided retrieval, but neither paper was used to predetermine the winning system. Higher-capacity models were not promoted simply because they were more sophisticated. Validation selected zero PubMedBERT blend weight; both cross-encoders trailed the baseline; and the learned reranker's small validation improvement reversed on test.

---

## LLM Use and Deliberate Non-Use

An LLM was used selectively for qualitative interpretation and development support. It was not part of the executable retrieval path, the behavioral-label construction, or the metric calculation.

### Where and why an LLM was used

1. **Intent-taxonomy and labeling review.** The analyst workflow used LLM assistance to inspect representative queries, low-margin cases, cross-class neighbors, and multi-cue intent boundaries. This was useful for interpreting short bilingual or mixed-language queries and for writing explicit inclusion, exclusion, and boundary rationales. The operational labels still came from the documented rule, prototype, cluster, and adjudication policy; the LLM-assisted subset is described as a reviewed reference, not clinical ground truth.
2. **Evidence-source audit.** An LLM-assisted review examined 60 selected query/title records after deterministic profiling. It identified cases such as metadata-only molecules, missed Indonesian comparison cues, coordinated renal/hepatic wording, negation-scope errors, and duplicated self-relations. This semantic layer was useful because literal string checks alone could not determine whether a field was supported, inferred, or potentially misleading.
3. **BM25 failure analysis.** The fixed-baseline review used LLM assistance to interpret 40 validation cases from query text, top-ranked titles, supplied metadata, and behavioral evidence. The review assigned overlapping failure categories, identified apparently off-topic behavioral positives, and proposed targeted checks. It did not change the baseline, labels, or ranking weights.
4. **Final retrieval failure analysis.** The predicted-intent ranker review used LLM assistance for 12 fixed temporal-test misses. The review separated likely ranking failures, corpus/title coverage gaps, intent errors, conjunction failures, and behavioral-proxy failures. Expected candidates were inspection aids and were not written back as relevance labels.

### Where and why an LLM was not used

- **Online query processing and ranking:** the selected system uses deterministic normalization and slot rules, supplied clinical entities, a saved intent classifier, BM25, frozen dense embeddings, structured compatibility, and a fixed scoring rule. It makes no generative LLM call at retrieval time. This keeps latency, cost, and behavior predictable.
- **Behavioral relevance labels:** grades come only from impressions and recorded clicks, dwell, deep scroll, bookmarks, and return visits. LLM opinions never create, overwrite, or strengthen a relevance grade, preventing qualitative review from becoming circular evaluation evidence.
- **Dataset splits and leakage controls:** chronological, query-held-out, and duplicate-aware assignments are deterministic. The LLM did not choose split membership, temporal boundaries, or eligible queries.
- **Retrieval scores and model selection:** BM25, dense similarity, entity/context compatibility, intent compatibility, learned-reranker fitting, validation selection, and tie-breaking are implemented in code. The LLM did not rerank candidates or choose a model from subjective inspection.
- **Metrics and uncertainty:** Recall, hit rate, MRR, NDCG, behavioral-label coverage, slice metrics, and bootstrap intervals are computed deterministically from frozen artifacts.
- **Artifact generation:** the BM25 failure-analysis, evidence-audit, and final failure-analysis scripts replay saved annotations and rebuild tables, reports, category counts, and provenance without making an LLM call. This separates reproducible computation from the original semantic review.

The boundary was deliberate. LLM assistance was most useful where the task required semantic interpretation of ambiguous language or explanation of a failure. It was excluded where it could contaminate targets, make comparisons non-reproducible, introduce opaque clinical judgments, or add unnecessary serving cost and latency. All LLM-assisted judgments remain exploratory annotations rather than authoritative medical or relevance labels.

---

## 3. Key Findings

### 3.1 Intent is useful, but mostly where it changes the preferred content type

Predicted intent helped the test slices for Interaction / Combination, Dosing / Administration, Management / Treatment Selection, and Safety / Contraindication. The largest change was Interaction / Combination, where NDCG@10 rose from 0.00387 to 0.06809 across six eligible queries. Dosing rose from 0.00789 to 0.02601 across 22 eligible queries.

The effect was not universal. Treatment Change / Escalation declined, most query rankings were unchanged, and the global bootstrap interval included zero. Intent should therefore be confidence-gated and treated as a preference signal, not a mandatory classification that overrides clinical entity requirements.

### 3.2 Structured matching helps lexical retrieval more reliably than it helps the full hybrid

Adding entities and context to BM25 raised test NDCG@10 from 0.01021 to 0.01477 and Recall@10 from 0.01609 to 0.03154. The same equal-weight structured features reduced the plain hybrid from 0.01651 to 0.01105 before intent was added.

This result partially supports the transferable premise from [Lopez et al. (2025)](https://doi.org/10.1038/s41746-024-01377-1): explicit clinical entities can improve retrieval when lexical similarity is insufficient. The reversal in the full hybrid also defines the boundary of that transfer. A short title may receive overlapping credit from text, dense similarity, entity metadata, and coarse context, even though it satisfies only part of the information need. Structured features should remain separate and be used with prerequisites rather than averaged indiscriminately.

### 3.3 Dense retrieval improves lexical mismatch, but its incremental value is uncertain

Dense-only retrieval outperformed BM25 on test NDCG@10, and the plain sparse+dense hybrid was stronger still. However, removing dense from the full R-E7 system slightly increased test NDCG@10. This does not make dense retrieval useless; it means the current additive combination and weak evaluation target did not establish a unique contribution once other correlated signals were present.

### 3.4 Query complexity requires conjunction-aware evidence

The recurring failure was not lack of a single feature. It was failure to require the complete conjunction of disease, molecule, relation, intent, and context. Examples included:

- renal-dose templates for the wrong molecule outranking the correct drug;
- interaction queries matching either drug independently but not the pair;
- comparison queries retrieving safety content without both comparators;
- correct disease/drug results addressing the wrong information need; and
- generic context templates outranking entity-correct content.

The current additive score permits one strong feature to compensate for a missing required condition. Clinical retrieval often needs conditional logic: a dosing bonus should not dominate unless the requested molecule is present, and a comparison result should cover both comparators and the relationship between them.

### 3.5 Corpus coverage is a first-class system property

Ten of the 12 detailed residual-error cases had no title that explicitly satisfied all requested requirements. Title-only retrieval cannot recover renal thresholds, pregnancy precautions, detailed dose adjustments, monitoring parameters, or contraindications that appear only in the body. Several apparent ranker failures were actually corpus or indexing failures.

This changes how errors should be handled. A system should not always force a ranked answer. It should distinguish:

- direct matches satisfying required evidence;
- related but incomplete evidence; and
- insufficient evidence in the indexed corpus.

### 3.6 Behavioral optimization can conflict with clinical plausibility

Thirty-two of 40 reviewed BM25 cases had an apparently off-topic strongest behavior-positive title. In the detailed predicted-intent ranker examples, exact-looking results were unjudged while off-topic exposed documents received positive grades. Removing weak content-type shortcuts made the representation more defensible but sometimes reduced the behavioral metric.

The learned reranker also increased the fraction of historically judged items in its top results. That can improve agreement with the logging policy without improving clinical usefulness. Its clinically implausible coefficients—including positive weights for some conflict features—were further evidence that it learned exposure regularities.

### 3.7 Slice analysis exposed gaps hidden by aggregate scores

The selected ranker performed better than BM25 across English, Bahasa Indonesia, and mixed-language test slices, but support varied. Multiple constraints showed a positive structured-retrieval point estimate, yet only 12 eligible queries supported it. Renal/lab, comparison, multi-molecule, guideline, efficacy, and mechanism slices were sparse or zero-valued.

Several planned entity-complexity comparisons were impossible because every test query had supplied disease and drug metadata. The dataset could not answer how the system behaves when NER is absent or partial. Reporting an aggregate metric alone would have hidden this identifiability problem.

### 3.8 Simpler won because the evidence did not justify complexity

The final selection retained multilingual MiniLM and no separate reranker. That does not prove the selected model is intrinsically best. It means none of the challengers demonstrated a validation-supported improvement that transferred under the available protocol.

This distinction matters. [Liang et al. (2025)](https://doi.org/10.1038/s41598-025-25783-x) and [Lopez et al. (2025)](https://doi.org/10.1038/s41746-024-01377-1) supplied well-motivated hybrid and entity-aware hypotheses, but the project evidence—not the literature alone—determined model selection. The result supports a conservative deployment candidate and an experimental roadmap, not a claim that biomedical embeddings, cross-encoders, or learning-to-rank are ineffective in general.

---

## 4. Honest Evaluation

### What the project establishes

The project establishes that:

- a reproducible multilingual query-understanding and retrieval pipeline is feasible on this corpus;
- a literature-seeded taxonomy can be systematically adapted with semantic, lexical, structured, and manual-review evidence;
- frozen multilingual embeddings plus clinical structure generalize better across query templates than lexical intent classification alone;
- entity/context structure can improve a fixed BM25 baseline;
- predicted intent can improve some intent-specific retrieval slices; and
- additional model capacity is not justified by the current offline evidence.

### What the project does not establish

It does not establish clinical search quality, causal benefit from the selected features, production safety, or robust generalization to natural physician traffic.

The main reasons are:

1. **Intent labels are weak references.** A single model-assisted analyst workflow created the reviewed subset. There was no independent secondary annotation or genuine inter-annotator agreement.
2. **Relevance labels are engagement proxies.** Clicks, dwell, bookmarks, and returns measure behavior after exposure. They do not prove topical correctness, answer completeness, or clinical usefulness.
3. **Behavioral-label coverage is extremely sparse.** Only about three percent of returned top-10 items have an observed behavioral label. Unexposed documents receive zero metric gain despite unknown relevance.
4. **The content representation is incomplete.** Titles and metadata cannot reveal many answer-bearing clinical details.
5. **The retrieval test is no longer pristine.** Later experiments were chosen after earlier test inspection, so test results are descriptive.
6. **The intent/retrieval split is misaligned.** The final intent model was refit on all 362 retained weak-label queries; 97 of the 139 temporal retrieval-test query IDs were included. Retrieval labels did not train the classifier, but the result cannot be interpreted as unseen-query end-to-end performance.
7. **Queries are template-heavy.** The 0.981 lexical row-CV Macro F1 was misleadingly optimistic; grouped F1 of 0.509 was the more revealing number.
8. **Some slices are unidentifiable or very small.** All test queries contain disease and drug metadata, and several clinically important constraint slices contain only a handful of eligible examples.
9. **Qualitative reviews are interpretive diagnostics.** The BM25 baseline and predicted-intent ranker case analyses were LLM-assisted and used titles, metadata, and saved evidence. Those annotations are transparent and reproducible as stored artifacts, but they do not replace broader behavioral coverage or independent validation.

Absolute retrieval values are low. BM25 recovered 1.61% of observed positives at rank 10 on temporal test; the selected ranker recovered 4.35%. These figures partly reflect genuine retrieval difficulty and partly reflect sparse, exposure-biased behavioral signals. They should not be read either as proof that the systems are poor at clinical relevance or as evidence that unobserved outputs are good.

### Production readiness

The current implementation is an assessment and experimentation pipeline, not an online service. The selected ranker is a reasonable launch *candidate* only after the following safeguards are added:

- section-level/full-text indexing and content availability controls;
- online query processing for arbitrary inputs;
- value- and relationship-aware entity matching;
- confidence calibration, out-of-distribution detection, and fallbacks;
- direct/related/insufficient evidence tiers;
- document provenance, date, source-quality, permission, and retraction handling;
- privacy-preserving event logging;
- offline quality gates based on mature behavioral outcomes, coverage, and safety-oriented error audits;
- shadow, canary, rollback, and version-compatible model/index deployment; and
- monitoring by language, intent, entity coverage, constraints, harmful mismatches, latency, and data quality.

The search product should retrieve and expose source evidence for clinicians. It should not diagnose, prescribe, or present a ranking score as medical certainty.

---

## 5. What I Would Do Differently

### 5.1 Establish the evaluation before building the models

I would reserve a genuinely untouched temporal confirmation period at the beginning. All relevance thresholds, taxonomy changes, features, weights, and architectures would be selected without inspecting it. I would align intent training, query understanding, ranker training, and relevance evaluation to the same temporal boundaries.

For queries appearing in model development, I would generate out-of-fold intent predictions for downstream ranking. Near-duplicate and delexicalized templates would remain within one fold. I would report recurring-query, unseen-query, unseen-template, and doctor-held-out performance as distinct deployment questions.

### 5.2 Build more complete behavioral supervision before optimizing retrieval deeply

I would improve the event and exposure data before adding more ranking capacity. Every displayed result should be tied to its exact request, rank, model/index version, and candidate set. Outcomes should include clicks, valid dwell, deep scroll, saves, return visits, reformulation, abandonment, and downstream content use over a defined maturity window.

I would also increase exploration so promising documents outside the historical ranker's narrow exposure pattern can receive feedback. Randomized swaps or interleaving on a safe candidate pool would make examination propensity estimable and reduce the current dependence on historically exposed items. Training would retain each behavioral signal separately, correct for position/exposure where possible, and distinguish unexposed from exposed-without-engagement.

If budget permits, a small blinded clinician review can remain a high-value audit for safety-critical or highly disputed cases. It is a luxury validation layer in this project, not the assumed primary source of supervision.

### 5.3 Strengthen query-understanding evaluation

I would create independently reviewed samples for both intent and contextual slots before finalizing the taxonomy and extraction logic. These could be produced through structured internal review, with specialist review reserved for ambiguous or safety-sensitive cases. The intent task should allow secondary intent or genuine multi-label cases. Slot evaluation should measure span/value accuracy, units, comparators, scope, and negation—not only field coverage.

### 5.4 Index answer-bearing text

I would retrieve over sections or passages from abstracts/full text, with separate fields for title, headings, body, entities, evidence type, publication date, and source. Dosing, contraindication, pregnancy, renal, interaction, and monitoring evidence should be matched where it occurs rather than inferred from the content type.

### 5.5 Replace additive compatibility with prerequisites and relationships

I would explicitly represent each requested entity and relation. Comparison and interaction queries should require coverage of both arguments. Dosing/safety/context bonuses should be conditional on the exact requested molecule and disease when confidence is high. Missing evidence should be neutral, explicit conflict should be negative, and class- or hierarchy-level matches should remain weaker than exact identity.

### 5.6 Use behavior as biased evidence, not truth

I would retain the individual events rather than collapsing them immediately into one maximum grade. With sufficient randomized or interleaved traffic, I would estimate examination propensity, use inverse-propensity or doubly robust estimators, define a mature outcome window, and separate satisfaction proxies from discovery and retention signals. Unexposed content would remain unjudged throughout.

### 5.7 Spend less time tuning weak-label variants

The signed boosts, repaired context variants, value-aware formulas, and repeated small weight grids were useful diagnostics, but their marginal value diminished once the evaluation target was shown to be incomplete. I would stop earlier and redirect that effort to better behavioral instrumentation, controlled exploration, content inspection, and corpus-gap analysis.

### 5.8 Make the production boundary explicit sooner

I would define the online structured-query contract, evidence requirements, failure states, and model/index versioning before the later experiments. Doing so would expose earlier that the assessment's cached 500-query cross-product is a batch research artifact, not a serving architecture, and would focus experiments on features that can be computed reliably for arbitrary queries.

---

## 6. What I Would Build Next

This section is intentionally separate from the retrospective above. The order reflects dependency and expected value, not novelty.

### 6.1 A complete, versioned behavioral evaluation dataset

The immediate next build would be an impression-complete dataset over a genuinely untouched time period. It would record exact position, rendered candidate set, request/session identity, serving versions, event timestamps, outcome maturity, reformulation, abandonment, saves, repeat use, and content follow-through. Controlled exploration would provide feedback beyond the historical ranker's usual results, while propensity estimates would support position-aware evaluation.

This dataset would preserve raw signals and exposure status rather than reducing them immediately to one grade. It would include no-positive queries, multilingual queries, low-confidence intent cases, multi-entity relationships, and high-risk constraints. A small expert-reviewed sample could be added when available to audit safety and calibrate interpretation, but the main project path would rely on richer behavioral evidence.

### 6.2 Section-level hybrid retrieval

I would ingest abstracts or full text, segment documents into clinically meaningful sections/passages, and build:

- a fielded BM25 index;
- a multilingual dense ANN index;
- canonical entity/code indexes; and
- metadata filters for access, source, publication time, review status, and retractions.

Candidates would be generated in parallel and deduplicated at the document level while retaining answer-bearing passages for evidence display.

### 6.3 A typed, relationship-aware clinical query object

The next query representation would retain raw spans, normalized concepts, values, units, comparators, confidence, provenance, and logical relationships. It would support:

- exact versus ICD/ATC hierarchy matches;
- multi-molecule interaction and comparison pairs;
- dose, route, frequency, and duration;
- age ranges, pregnancy/lactation, renal and hepatic function;
- prior therapy, failure, resistance, and escalation;
- temporal constraints and recency; and
- scoped negation.

The ranker and response policy would consume the same object, making the final result auditable.

### 6.4 Conjunction-aware reranking and abstention

Before adding a large neural reranker, I would implement transparent prerequisite features and evidence tiers. A document lacking a required high-confidence molecule or comparison argument could still be shown as related evidence, but it could not be labeled a direct match. If no candidate satisfies the minimum evidence set, the service would return `insufficient_evidence` instead of a confident wrong answer.

### 6.5 Calibrated intent and slot models

With independent labels, I would train a joint or multi-task multilingual model for intent and slot extraction, evaluate it on unseen templates and future time, calibrate its probabilities, and define an abstention/OOD policy. A multi-intent distribution would replace a forced hard label where the query genuinely has more than one need.

### 6.6 Domain-aligned bi-encoder training

Once high-quality positives exist, I would fine-tune a multilingual query encoder against the content/passages using contrastive or InfoNCE loss. Hard negatives would be selected deliberately:

- correct disease, wrong molecule;
- correct molecule, wrong intent;
- both entities, wrong relationship;
- correct topic, wrong population or organ-function constraint; and
- semantically close but outdated or low-quality evidence.

The training objective should reflect asymmetric short-query-to-clinical-passage retrieval rather than generic sentence similarity.

### 6.7 Cross-encoder reranking

A multilingual biomedical cross-encoder would rerank only a bounded candidate set after recall and labels are strong enough. It would be evaluated against the simpler transparent ranker on clinical usefulness, harmful mismatch, latency, and calibration—not selected on behavioral NDCG alone.

### 6.8 Debiased learning-to-rank and online evaluation

With reliable logging and enough traffic, I would train a group-aware learning-to-rank system from propensity-corrected behavioral evidence. Offline promotion would require improvement across mature engagement, reformulation, abandonment, return-use, coverage, and harmful-mismatch proxies rather than a single click-derived metric. Where an expert-reviewed audit set is affordable, it would act as an additional safety check. The rollout would proceed through shadow comparison, targeted review, canary traffic, and a preregistered A/B or interleaving experiment with clinical and operational guardrails.

### 6.9 Production monitoring and learning loop

The production system would monitor:

- language, intent, confidence, entropy, and OOD drift;
- entity and slot coverage by type;
- direct-match, related-evidence, and insufficient-evidence rates;
- candidate overlap and retrieval-branch failures;
- harmful entity/context mismatches;
- CTR, valid dwell, saves, reformulation, and abandonment with position awareness;
- behavioral-label coverage, outcome maturity, and any available expert-audit outcomes;
- latency, throughput, cost, and index freshness; and
- event loss, duplicates, schema drift, and model/index compatibility.

Intent, extraction, indexes, and ranking would be versioned and governed separately. New behavior would create a retraining candidate only after the observation window closed, logging quality passed, a time-aware dataset snapshot was frozen, and the riskiest changes had passed targeted safety review.

---

## 7. Final Assessment

The project succeeded as an evidence-building exercise. It produced a transparent query schema, an explicit 11-intent taxonomy, a materially stronger unseen-template intent classifier, a reproducible weak-relevance and evaluation framework, a fixed BM25 reference, incremental retrieval ablations, and a conservative model-selection decision.

Its most valuable learning is that clinical retrieval quality is constrained less by the absence of another scoring model than by incomplete content evidence, non-compositional matching, and sparse behavioral supervision. Intent and structure can help, but they must operate inside a system that respects required entities and relationships, admits when evidence is missing, and is evaluated from complete, position-aware outcomes on answer-bearing content.

The selected predicted-intent hybrid ranker is the best-supported implementation in this repository. It is not the final search system. The next credible step is to improve the evidence on which the system is trained and evaluated; only then should the project spend additional complexity on fine-tuned encoders, cross-encoders, or learned ranking.

## References

1. Lopez I, Swaminathan A, Vedula K, et al. [Clinical entity augmented retrieval for clinical information extraction](https://doi.org/10.1038/s41746-024-01377-1). *npj Digital Medicine*. 2025;8:45.
2. Monsalve K, Villa MC, Castaño-Villegas N, Zea J, Velásquez L. [Clinical Information Needs Among Latin American Physicians: A Multi-Country Analysis of Semantic Clinical Search](https://doi.org/10.64898/2026.06.26.26356340). *medRxiv*. 2026. Preprint; not peer reviewed.
3. Liang Z, Zhao Y, Xu H, Huang H, et al. [A hybrid model integrating RoBERTa, TF-IDF, and attention mechanism for medical query intent classification](https://doi.org/10.1038/s41598-025-25783-x). *Scientific Reports*. 2025;15:42847.

## Artifact Guide

- Data-audit artifacts: [`outputs/audits/`](../outputs/audits/)
- Taxonomy artifacts: [`outputs/taxonomy/`](../outputs/taxonomy/)
- Intent-labeling artifacts: [`outputs/intent/`](../outputs/intent/)
- Intent-model metrics: [`outputs/metrics/`](../outputs/metrics/)
- Behavioral-relevance artifacts: [`outputs/relevance/`](../outputs/relevance/)
- Experiment overview: [`outputs/experiment_overview/experiment_overview.md`](../outputs/experiment_overview/experiment_overview.md)
- BM25 failure cases: [`outputs/retrieval/failure_analysis/review_cases.md`](../outputs/retrieval/failure_analysis/review_cases.md)
- Final retrieval failure-analysis artifacts: [`outputs/retrieval/`](../outputs/retrieval/)
- Production design: available in the `write_up/` directory
- Labeled query deliverable: [`outputs/queries_labeled.csv`](../outputs/queries_labeled.csv)
