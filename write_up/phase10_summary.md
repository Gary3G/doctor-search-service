## Approach

Reviewed **40 temporal-validation queries** before adding retrieval complexity: 26 with no observed positive in the top 10, 8 with at least one hit, and 6 with no validation positives. The source partition has 100 misses, 13 hits and 26 queries without positives. Each stratum is sampled from sorted query IDs with seed 42 and fixed quotas. These quotas deliberately include controls; category counts describe this review, not the prevalence of failures among all 500 queries.

Run `.venv/bin/python -m src.bm25_failure_analysis`. The notebook includes an executable Phase 10 section. The authored notes are in `data/processed/phase10_review_notes.csv`; the generated case report, evidence table, category counts and input/code fingerprints are under `outputs/retrieval/failure_analysis/`.

For every case, the review records query text, supplied entities, earlier predicted intent and extracted slots, the top three results, up to two strongest observed behavioral positives, every observed top-10 hit, an interpretation and a next check. Selected cases also include a plausible alternative, its full-corpus BM25 rank and its judgment status. Alternatives are inspection candidates, not newly assigned relevance labels. Full-corpus ranks are recomputed with the fixed baseline and checked against saved top-20 ordering.

**Where and why an LLM was used:** An LLM-assisted review covered the 40 selected queries. It interpreted query text, retrieved titles, supplied metadata and behavioral evidence; assigned mismatch categories; identified apparently off-topic behavioral positives; and produced explanations and proposed next checks. This semantic review helped distinguish multilingual wording, information-need differences and missing clinical constraints that token overlap and retrieval metrics alone cannot explain. An LLM also assisted with implementation and report drafting. Its case judgments are saved in `data/processed/phase10_review_notes.csv` as exploratory annotations, not clinician-validated labels.

**Where an LLM was not used:** Phase 10 uses deterministic code for sample selection, BM25 scoring, evidence joins, metric handling and aggregation of the saved review categories. No LLM was used in this phase to rerank documents, create or overwrite behavioral relevance grades, or tune the baseline. Keeping these operations deterministic preserves an auditable reference and prevents the reviewer's own judgments from becoming the labels used to score that reference. Running the Phase 10 script makes no LLM calls: it reads the saved annotations and rebuilds the evidence report. It reproduces the recorded review, rather than independently reproducing its semantic judgments.

## Key Findings

Categories overlap. Among the 40 reviewed queries:

| Visible issue | Queries |
| --- | ---: |
| Intent mismatch | 29 |
| Partial entity match | 21 |
| Missing contextual constraint | 9 |
| Severity / progression / prior-failure evidence missing | 5 |
| English–Indonesian wording mismatch | 4 |
| Temporal mismatch | 3 |
| Age evidence missing | 2 |
| Lexical mismatch | 2 |
| Synonym mismatch | 1 |
| Pregnancy evidence missing | 1 |
| Renal-function evidence missing | 1 |

Abbreviation mismatch and a confirmed wrong-molecule document within the correct drug class were **not established** in this sample. They remain evaluation categories, not invented examples. In particular, C005 names Liraglutide in its title but contains both Liraglutide and Semaglutide in supplied metadata: Q065 illustrates a title-only indexing limitation, not proof that the document excludes Semaglutide.

The behavioral evidence has a separate problem: **32 queries have an off-topic strongest-positive title**, with ties resolved by content ID; 6 have no observed positives. These 38 cases receive the weak-ground-truth tag. The remaining 2 have a broadly same-disease strongest positive whose exact intent relevance is still unverified. This does not mean every positive for those 32 queries is off-topic, nor that 38 rankers failed. It shows why proxy metrics alone cannot validate the ranking. All unjudged pairs remain explicitly unjudged in the evidence table.

Representative cases illustrate these findings:

| Query | Evidence | Diagnosis / next check |
| --- | --- | --- |
| Q070: Furosemide long term outcomes Nephrotic Syndrome | C053 at rank 1 directly matches drug, disease and outcomes, but is unjudged; observed positives include diabetes outcomes | Apparent metric failure without an established title-level ranking failure; prioritize relevance adjudication |
| Q201: Semaglutide/Liraglutide interactions in Obesity | Generic Indonesian drug-profile wording retrieves unrelated diseases; C089 at rank 7, a Topiramate/Migraine self-comparison, earns grade-2 credit | Lexical/entity failure plus misleading behavioral success |
| Q003: Nivolumab interactions in Colorectal Cancer | C202 at rank 1 matches drug and interaction intent but concerns lung cancer | Partial entity match; test disease-and-molecule coverage |
| Q018: Losartan/Empagliflozin interactions in CKD | Safety profiles occupy ranks 1–2; Losartan interaction title C047 is rank 3 | Intent ordering problem; even C047 does not establish the specific two-drug interaction |
| Q153: Rheumatoid Arthritis guideline update 2023 | Psoriasis and anaemia guideline-update titles lead | Shared template/year wording outweighs disease specificity |
| Q386: Zinc side effects in Stunting / Malnutrition | Self-comparison C294 leads while C279 is explicitly an adverse-event title | Test side-effect/adverse-event normalization, then inspect article scope |
| Q485: Lansoprazole resistance in Peptic Ulcer Disease | Safety C157 leads; switching guides C149/C156 rank 2–3 and their metadata includes Lansoprazole | Test intent plus entity metadata; resistance-specific relevance remains unverified |
| Q346: renal dose adjustment of Losartan in CKD | Safety and interaction titles match drug/disease without explicit dose adjustment | Renal-dosing evidence is missing; CKD token overlap is insufficient |
| Q225: Psoriasis treatment choice for elderly patients | C332 at rank 1 explicitly matches Psoriasis and elderly patients but receives no positive credit | Useful counterexample: no visible age mismatch, despite zero proxy recall |

The full report contains all 40 case-specific explanations and source IDs, including pregnancy, age, progression, dosing, temporal and no-positive examples. Repeated self-comparison/switch queries and titles are also recorded as possible data artifacts, not assumed valid clinical tasks.

## Honest Evaluation

This is an **LLM-assisted qualitative review of titles and metadata**, not independent clinician adjudication. Body text is unavailable. Context mismatch categories include missing evidence in a title; they do not establish incompatible clinical content. Query decomposition may contain supplied entities absent from the literal query and inherits previous intent/slot uncertainty. Bilingual and synonym diagnoses identify plausible lexical limitations, not measured causal improvements. No ranking parameters, behavioral labels or test-set metrics were changed.

The category counts therefore summarize one LLM review. No independent second reviewer, agreement measurement or clinician adjudication was performed. The automated tests check sampling and evidence integrity; they do not validate the correctness of the LLM's mismatch diagnoses.

Five focused tests pass: two Phase 10 checks cover deterministic validation-only sampling, immunity to changed test metrics, missing-positive metric semantics, and preservation of unjudged results and misleading proxy hits; three existing retrieval checks cover baseline ranking and metric correctness. The Phase 10 notebook cells were executed in process, preserving prior cells and outputs.

## What You Would Do Differently

1. Test supplied entity matching against the frozen BM25 reference. Distinguish entities missing from titles from entities absent from the corpus; audit metadata reliability before treating it as truth.
2. Test intent compatibility separately. Interaction, adverse effects, dose adjustment, switching and maintenance frequently lose to the correct drug/disease with the wrong information need.
3. Test contextual compatibility where evidence exists. An absent population or renal qualifier should be represented as unknown, rather than fabricated incompatibility.
4. Test bilingual cues and narrowly scoped synonyms as separate ablations; assess whether they recover entity-specific results rather than boost generic templates.
5. Obtain blinded clinician judgments of pooled results, including unjudged and no-positive controls. Sparse and sometimes off-topic behavioral evidence can reward bad results and penalize plausible ones.

These are hypotheses, not demonstrated gains. The validation partition has now informed design decisions; later confirmation should use newly reserved time or independent judgments, especially because earlier phases already inspected the current test set. No new retrieval model is implemented in Phase 10.
