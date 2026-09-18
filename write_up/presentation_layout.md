# PowerPoint Presentation Layout: Multilingual Medical Query Understanding and Retrieval

## Presentation format

- **Core talk:** approximately 47–50 minutes
- **Questions and discussion:** 5–10 minutes
- **Core slides:** 26
- **Optional appendix:** 6 backup slides
- **Audience:** research, machine-learning, search, product, and engineering stakeholders
- **Narrative:** problem framing → Task 1 → Task 2 → production system → three-month plan
- **Evidence convention:** all quoted queries and content titles below come from the project datasets. Metrics are reported as behavioral-proxy results unless explicitly described otherwise.

## Visual language

- Use one consistent color per evidence type:
  - blue: query understanding and intent;
  - teal: retrieval and ranking;
  - amber: uncertainty, sparse evidence, or abstention;
  - red: harmful or clinically implausible mismatch;
  - gray: unjudged or unavailable evidence.
- Put the conclusion in the slide title whenever possible.
- Keep tables to the minimum rows needed to make the argument.
- Show query examples in a monospace treatment and preserve the original English, Bahasa Indonesia, or mixed-language wording.
- Add a small footer to result slides: “Behavior-derived relevance; unjudged is not the same as irrelevant.”

---

## Slide 1 — From Query Intent to Defensible Medical Retrieval

**Time:** 0.5 minute

**On-slide content**

- Multilingual medical query understanding and retrieval
- Task 1: intent taxonomy, weak labeling, and classification
- Task 2: behavioral relevance, hybrid retrieval, and intent-aware ranking
- Production design and a three-month improvement plan

**Visual**

A single horizontal flow: `doctor query → decomposition → retrieval → ranked evidence`.

**Speaker notes**

Open with the central conclusion: the project did not fail because it lacked a larger model. The main constraints were incomplete supervision, title-only content evidence, and ranking logic that did not enforce clinical conjunctions.

---

## Slide 2 — The Short Answer

**Time:** 1.5 minutes

**On-slide content**

- **Task 1:** an 11-intent schema was learnable, but ordinary cross-validation overstated generalization.
- **Task 2:** intent improved ordering for specific information needs, especially interaction and dosing, but gains were concentrated in a few queries.
- **Biggest surprise:** more sophisticated models did not overcome weak labels or missing answer-bearing text.
- **Biggest failure:** additive scores could reward the right template for the wrong molecule.
- **Production recommendation:** start with a transparent hybrid, add conjunction checks and abstention, and improve behavioral evidence before training a more complex ranker.

**Visual**

Five concise “finding cards,” one for each bullet.

**Speaker notes**

State explicitly that this is an evidence-building result, not a claim of clinical readiness.

---

## Slide 3 — Why This Is an Ambiguous Research Problem

**Time:** 1.5 minutes

**Trait:** Research judgment

**On-slide content**

- 500 queries: 222 English, 173 mixed-language, 105 Bahasa Indonesia
- 345 content items, with titles and metadata but no article bodies
- 7,190 impressions and 1,500 recorded interactions
- No supplied intent labels
- No clinician-labeled query–content relevance set
- Only 4.1% of all possible query–content pairs were ever exposed

**Visual**

Four dataset blocks feeding two missing-label questions:

1. What did the doctor mean?
2. Which content actually answered the question?

**Speaker notes**

Frame the work as two linked inference problems. The taxonomy determines what “intent” means; the exposure process determines what behavioral relevance can and cannot tell us.

---

## Slide 4 — The Same Disease and Drug Can Express Different Needs

**Time:** 1.5 minutes

**Trait:** Research judgment

**On-slide content**

Verbatim dataset examples for Major Depressive Disorder and Venlafaxine:

| Query | Information need |
| --- | --- |
| Q121: `when to start Venlafaxine in Major Depressive Disorder` | Treatment selection |
| Q187: `dosis Venlafaxine pada Major Depressive Disorder pasien hypertension aman tidak` | Safety / contraindication |
| Q366: `Venlafaxine long term outcomes Major Depressive Disorder` | Efficacy / outcomes |
| Q413: `SNRIs terbaru untuk Major Depressive Disorder 2024` | Guideline / evidence lookup |
| Q430: `Major Depressive Disorder dengan renal impairment penyesuaian dosis Venlafaxine` | Dosing / administration |
| Q471: `monitoring terapi Venlafaxine pada Major Depressive Disorder` | Monitoring / response |

**Visual**

Keep “Major Depressive Disorder + Venlafaxine” fixed in the center and fan out to six intent labels.

**Speaker notes**

This is why entity matching alone cannot solve the task. The preferred content changes even when the clinical topic is constant.

---

## Slide 5 — Task 1 Began with Taxonomy Design, Not Model Selection

**Time:** 2.5 minutes

**Trait:** Research judgment

**On-slide content**

The retained schema had 11 operational intents:

1. Management / Treatment Selection
2. Dosing / Administration
3. Safety / Contraindication
4. Interaction / Combination
5. Comparative Treatment Choice
6. Monitoring / Response / Risk Assessment
7. Efficacy / Outcomes
8. Guideline / Evidence Lookup
9. Treatment Change / Escalation
10. Prophylaxis / Maintenance
11. Mechanism / Background Knowledge

Design decisions:

- split broad pharmacotherapy because dosing, safety, interaction, comparison, and efficacy prefer different evidence;
- split initial treatment from failure-driven escalation and maintenance;
- merge sparse risk-stratification queries into monitoring;
- add mechanism as a coherent dataset-specific class;
- do not retain unsupported diagnosis, procedure, or patient-education classes.

**Paper involvement**

- **Monsalve et al. (2026):** supplied the physician-search seed taxonomy and motivated face-validity review of representative and boundary cases.
- **Liang et al. (2025):** informed the finer medical-query distinctions and the expectation that neighboring intents would be difficult to separate.

**Visual**

A “seed → split / merge / rename / add / drop → final schema” diagram.

**Speaker notes**

Emphasize that the literature constrained the search space, while observed query structure determined the final classes. The schema was adapted, not copied.

---

## Slide 6 — Labeling Without Gold Labels: Three Signals, One Auditable Policy

**Time:** 2 minutes

**Trait:** Research judgment

**On-slide content**

- **Rule signal:** ordered bilingual cues such as `dose`, `aman`, `guideline`, `vs`, `interaksi obat`, `monitoring`, and `mechanism`.
- **Prototype signal:** multilingual semantic similarity between a delexicalized query and complete intent definitions.
- **Cluster signal:** independently discovered query structure mapped to the intent schema.
- 60-query pilot → 180-query reviewed reference subset → labels for all 500 queries.
- Sampling emphasized disagreement, low margins, rare intents, language, therapeutic area, and template coverage.
- Three-signal Fleiss’ kappa increased from 0.324 to 0.357 after cluster-to-intent mapping.

**Boundary statement**

These are model-assisted reference labels, not independently adjudicated clinical ground truth.

**LLM use boundary**

LLM assistance was used for bounded semantic review of ambiguous cases and explanations. It was not used to manufacture retrieval relevance grades, tune ranking weights, or serve online predictions.

**Visual**

Three arrows—rules, prototypes, clusters—feeding an adjudication box with preserved confidence and disagreement metadata.

**Speaker notes**

The point is not that three weak signals become truth. The value is that disagreements become visible and can guide selective review and later data collection.

---

## Slide 7 — The First “Great” Score Was Mostly Template Memorization

**Time:** 2 minutes

**Trait:** Technical depth

**On-slide content**

| Evaluation | Template overlap | Macro F1 |
| --- | --- | ---: |
| Five-fold row-stratified weak-label CV | Yes | **0.981** |
| Two-fold template-held-out stress test | No | **0.509** |

- 362 retained training rows collapsed to only 91 delexicalized templates.
- Eight intents had fewer than five distinct templates.
- Monitoring had eight rows but only one independent template.
- The 0.472 F1 gap changed the model-selection criterion.

**Visual**

Two large bars: 0.981 versus 0.509, annotated “same patterns recur” and “unseen formulations.”

**Speaker notes**

This is the clearest example of research judgment affecting the result. Reporting only random row folds would have produced a confident but misleading story.

---

## Slide 8 — Semantic Representation Plus Structured Context Generalized Better

**Time:** 2 minutes

**Trait:** Technical depth

**On-slide content**

| Representation | Row-CV Macro F1 | Template-held-out Macro F1 |
| --- | ---: | ---: |
| Word TF-IDF | **0.981** | 0.509 |
| Prototype similarity | 0.683 | 0.651 |
| TF-IDF + entities + context | 0.961 | 0.678 |
| Frozen multilingual embeddings | 0.969 | 0.794 |
| **Embeddings + entities + context** | 0.970 | **0.842** |

Selected feature vector:

- 384-dimensional multilingual query embedding;
- eight entity presence/count features;
- 18 contextual features such as dose, comparison, recency, pregnancy, renal/hepatic context, and prior failure;
- class-balanced Logistic Regression.

**Paper involvement**

Liang et al. (2025) motivated testing lexical, semantic, and category/structured branches as complementary signals. The project implemented that idea with frozen multilingual representations and explicit structured features rather than reproducing the paper’s supervised architecture.

**Visual**

A grouped bar chart focused on template-held-out F1.

**Speaker notes**

The selected model gave up 0.011 row-CV F1 to gain 0.333 on unseen templates. That is the tradeoff worth making.

---

## Slide 9 — Task 1 Failure Cases Reveal Competing-Cue Boundaries

**Time:** 2 minutes

**Trait:** Technical depth and honest evaluation

**On-slide content**

| Verbatim query | Reference intent | Prediction | Why it failed |
| --- | --- | --- | --- |
| `dosis Semaglutide pada Obesity pasien hypertension aman tidak` | Safety | Dosing | Dose feature overrode `aman tidak` |
| `Malaria with pregnancy first line drug` | Treatment selection | Safety | Pregnancy overwhelmed first-line selection |
| `Ramipril combination therapy Hypertension` | Interaction | Treatment selection | Short combination phrasing looked generic |
| `kapan mulai terapi Adalimumab pada Gout` | Treatment selection | Maintenance | Initiation confused with longitudinal care |

Additional limitations:

- no examples of `Other / Ambiguous`;
- mixed-language grouped Macro F1 was 0.636 versus 0.926 for English;
- probabilities were not calibrated for abstention;
- embedding-assisted data selection may make the embedding result optimistic.

**Visual**

Highlight the competing cue in each query with two colors.

**Speaker notes**

Explain that structured features can fix semantic errors and also create them. The solution is calibrated or gated fusion, not blindly adding more features.

---

## Slide 10 — Task 1: What We Found, What Surprised Us, Where It Failed

**Time:** 1 minute

**On-slide content**

- **Found:** intent is operationally useful when it changes the preferred evidence or content type.
- **Surprised:** a nearly perfect lexical score collapsed on unseen templates.
- **Failed:** sparse templates, no ambiguity class, competing cues, and weak reference labels limited defensible generalization.
- **Decision:** retain the embedding + structured classifier, but treat confidence and out-of-distribution handling as missing production requirements.

**Visual**

Three columns: found / surprised / failed.

---

## Slide 11 — Task 2 Started by Defining Relevance from Exposure and Behavior

**Time:** 2 minutes

**Trait:** Research judgment

**On-slide content**

The analytical unit was one `(query, content, session)` impression.

| Grade | Behavioral evidence |
| ---: | --- |
| 0 | Exposed with no recorded engagement |
| 1 | Click shorter than 10 seconds |
| 2 | Click at least 10 seconds or deep scroll |
| 3 | Bookmark, return, or deep scroll at least 150 seconds |
| Unjudged | Never exposed |

Rules deliberately excluded inferred rank, doctor ID, content popularity, session length, intent, and content type from the target.

**Visual**

An exposure funnel: 7,190 impressions → 1,500 interactions → graded evidence.

**Speaker notes**

Grade 0 is a nonpositive behavioral observation, not proof of clinical irrelevance. Unexposed content must remain unjudged.

---

## Slide 12 — The Behavioral Signal Was Useful but Incomplete

**Time:** 1.5 minutes

**Trait:** Research judgment

**On-slide content**

- 5,690 grade-0 impressions, 444 grade 1, 710 grade 2, 346 grade 3
- 350 of 500 queries had at least one observed positive
- 150 queries had no observed positive
- Only 7,037 of 172,500 possible query–content pairs were exposed: **4.1% coverage**
- Median query judgment coverage was 2.9% of the corpus
- Rank-one engagement was 24.1% versus 20.4% at later ranks
- 49 repeated pairs switched between engaged and unengaged outcomes

**What the project needed more of**

Complete impressions, explicit rendered rank, validated dwell, reformulation, return, save, negative feedback, downstream task success, and a small governed exploration stream.

**Visual**

A sparse 500 × 345 relevance matrix with only 4.1% of cells colored.

**Speaker notes**

Selective expert review can be useful for high-risk calibration, but it is expensive and should not be the only path to better supervision. The first priority is a more complete, position-aware behavioral signal.

---

## Slide 13 — A Proxy Miss Can Be a Plausible Retrieval Success

**Time:** 2 minutes

**Trait:** Honest evaluation

**On-slide content**

**Query Q180**

`tatalaksana Type 1 Diabetes Mellitus panduan terbaru 2023`

Top results:

1. `Asia-Pacific Guideline: Type 1 Diabetes Mellitus in Primary Care 2023`
2. `Clinical Practice Guideline: Type 1 Diabetes Mellitus Management 2023`

Both exact-looking results were unjudged. The only recorded positive was an off-topic 2024 colorectal-cancer review.

**Conclusion**

Behavioral NDCG recorded a miss even though the ranking looked plausible from the available title evidence.

**Visual**

Split the slide into “what the ranker returned” and “what the log rewarded.” Use gray for unjudged and red for the off-topic positive.

**Speaker notes**

This example prevents an overly optimistic or overly pessimistic interpretation. The metric is measuring agreement with logged exposure and engagement, not clinical truth.

---

## Slide 14 — The Retrieval Ladder: Every Signal Had to Earn Its Place

**Time:** 2 minutes

**Trait:** Technical depth

**On-slide content**

Temporal test results, NDCG@10:

| System | NDCG@10 | Recall@10 | MRR@10 |
| --- | ---: | ---: | ---: |
| BM25 | 0.01021 | 0.01609 | 0.02016 |
| BM25 + entities | 0.01303 | 0.02359 | 0.02379 |
| BM25 + entities + context | 0.01477 | 0.03154 | 0.02389 |
| Dense | 0.01584 | 0.02972 | 0.01735 |
| Plain hybrid | 0.01651 | 0.03528 | 0.02304 |
| Hybrid + entities + context | 0.01105 | 0.02063 | 0.02091 |
| Hybrid + entities + context + assisted intent | **0.01940** | **0.04801** | **0.02857** |

**Paper involvement**

Lopez et al. (2025) shaped the structured retrieval sequence: extract entities, normalize codes, add bounded hierarchy, compute compatibility, and ablate each contribution. This project used supplied entity metadata and deterministic matching; it did not reproduce the published model.

**Visual**

A line or staircase chart, with the drop at “hybrid + structure” clearly visible.

**Speaker notes**

Structured signals helped BM25 but hurt when averaged equally into the hybrid. Useful features can become harmful through scale, correlation, or missing evidence.

---

## Slide 15 — Does Intent Change Retrieval? Yes, but Not Uniformly

**Time:** 2 minutes

**Trait:** Technical depth

**On-slide content**

Runtime intent results:

| Intent input | Validation NDCG@10 | Test NDCG@10 | Test Recall@10 |
| --- | ---: | ---: | ---: |
| No intent | 0.02727 | 0.01105 | 0.02063 |
| Predicted soft intent | 0.03084 | 0.01115 | 0.02063 |
| **Predicted hard intent** | **0.03146** | **0.01851** | **0.04346** |
| Assisted reference intent | **0.03146** | **0.01940** | **0.04801** |

Predicted-hard intent versus no intent by selected test slice:

- Interaction / Combination: +0.06422 NDCG@10
- Dosing / Administration: +0.01812
- Management / Treatment Selection: +0.00677
- Safety / Contraindication: +0.00540
- Treatment Change / Escalation: −0.00942

Only 8 of 110 eligible queries improved, 2 worsened, and 100 were unchanged; the paired interval included zero.

**Visual**

A diverging slice chart plus a small “8 / 2 / 100” changed-query counter.

**Speaker notes**

The correct claim is intent-specific utility, not universal improvement.

---

## Slide 16 — A Concrete Intent Win: Q069

**Time:** 1.5 minutes

**Trait:** Technical depth

**On-slide content**

**Query**

`dosis titrasi Alendronate Osteoporosis toleransi pasien`

**Behavior-positive content**

`Konsensus Nasional: Osteoporosis di Indonesia 2022`

- exact disease, molecule, drug class, and therapeutic-area matches;
- grade 3 from one 158-second deep scroll;
- without intent: rank 5;
- with dosing intent: rank 2;
- NDCG@10: 0.17358 → 0.28310;
- MRR@10: 0.20 → 0.50.

**Caveat**

The title is a general consensus, not explicit titration guidance. This demonstrates the mechanism against the behavioral target, not confirmed clinical answer quality.

**Visual**

Before/after ranked lists with the positive content moving from 5 to 2.

---

## Slide 17 — The Main Retrieval Failure Was Conjunction, Not Semantics

**Time:** 2.5 minutes

**Trait:** Technical depth and honest evaluation

**On-slide content**

**Q019**

`Rheumatoid Arthritis dengan renal impairment penyesuaian dosis Bortezomib`

Top three results were renal-dose articles for Atorvastatin, Apixaban, and Dupilumab. The closest Bortezomib/Rheumatoid Arthritis title was rank 11.

**Q101**

`Dolutegravir drug interaction with Tenofovir disoproxil in Malaria`

The ranker matched each drug or disease independently but could not require both drugs and the interaction relationship.

**Q146**

`Bedaquiline vs Rifampicin untuk pasien Tuberculosis mana lebih efektif`

Bedaquiline safety titles outranked a class-level efficacy item; no title compared both requested drugs.

**Diagnosis**

- additive scores allow context to compensate for the wrong molecule;
- “any overlap” is inadequate for multi-value queries;
- title-only indexing often contains no candidate satisfying the full request;
- the correct system behavior may be `insufficient_evidence`, not forced ranking.

**Visual**

For each example, show required evidence as a checklist and mark which requirement the top result fails.

---

## Slide 18 — More Capacity Did Not Repair the Evidence Problem

**Time:** 1.5 minutes

**Trait:** Technical depth and research judgment

**On-slide content**

| Challenger | Validation NDCG@10 | Test NDCG@10 | Decision |
| --- | ---: | ---: | --- |
| Selected deterministic hybrid | 0.03146 | **0.01851** | Retain |
| Learned logistic reranker | **0.03363** | 0.01653 | Validation gain did not transfer |
| Multilingual cross-encoder | 0.02723 | 0.01545 | Reject |
| Biomedical cross-encoder | 0.03027 | 0.01755 | Reject |
| Biomedical embedding replacement | 0.02869 | 0.01488 | Reject |

What the learned reranker exposed:

- it learned clinically implausible coefficient directions;
- it increased the fraction of historically judged results;
- it appeared to learn exposure and engagement regularities rather than stable clinical relevance.

**Visual**

Validation and test paired bars for each model.

---

## Slide 19 — Task 2: What We Found, What Surprised Us, Where It Failed

**Time:** 1 minute

**On-slide content**

- **Found:** entities and context help lexical retrieval; intent helps selected information needs.
- **Surprised:** better extraction and larger models could reduce the behavioral metric.
- **Failed:** sparse exposure, off-topic positives, title-only evidence, additive matching, and repeated test inspection limited strong claims.
- **Decision:** retain the simplest supported hybrid; improve evidence, conjunction logic, and abstention before adding model complexity.

**Visual**

Three columns: found / surprised / failed, ending in the selected decision.

---

## Slide 20 — Production Principle: Decomposition Is the Retrieval Control Plane

**Time:** 1.5 minutes

**Trait:** Production thinking

**On-slide content**

Query decomposition should control:

- which candidate branches run;
- what counts as exact, related, or insufficient evidence;
- which features are calculated;
- when intent may influence ranking;
- which explicit conflicts matter;
- what match reason is shown to the user;
- what is monitored by language, intent, entity, and constraint slice.

Production rules:

- unknown evidence is neutral, not contradictory;
- class-level similarity cannot masquerade as an exact molecule match;
- low-confidence intent falls back to neutral;
- missing required evidence triggers a lower evidence tier or abstention.

**Visual**

A “structured query object” at the center controlling retrieval, ranking, policy, explanation, and monitoring.

---

## Slide 21 — Production Architecture

**Time:** 2.5 minutes

**Trait:** Production thinking

**On-slide content**

```text
Doctor query
    |
    v
Gateway: authentication, policy, request ID
    |
    v
Query understanding
  - normalization and language
  - entities and canonical codes
  - contextual values and scope
  - intent, confidence, OOD
    |
    v
Structured query object
    |
    +--> sparse fielded index ---------+
    +--> multilingual dense index -----+--> candidate union
    +--> structured/pairwise lookup ---+
                                        |
                                        v
Feature assembly + deterministic ranker
    |
    v
Conjunction policy + evidence tier + abstention
    |
    v
Results with provenance, dates, match reasons, and versions
    |
    `--> asynchronous impression and interaction events
```

Offline:

- ingest full text, preserve provenance, deduplicate, and section content;
- precompute document embeddings;
- build immutable sparse, dense, structured, and metadata index bundles;
- stage, validate, activate atomically, and retain the previous bundle for rollback.

**Visual**

Use the architecture diagram as the entire slide, with online path above and offline path below.

**Speaker notes**

The launch ranker is deterministic for a fixed model/index/config bundle. Sparse retrieval is the stable fallback. Dense, structured, and intent failures degrade independently.

---

## Slide 22 — How Decomposition Changes Retrieval for Q019

**Time:** 2 minutes

**Trait:** Technical depth and production thinking

**On-slide content**

**Input**

`Rheumatoid Arthritis dengan renal impairment penyesuaian dosis Bortezomib`

**Decomposition**

- disease: Rheumatoid Arthritis
- molecule: Bortezomib
- drug class: Proteasome inhibitors
- renal context: impairment
- intent: Dosing / Administration
- required relationship: the same candidate must cover the named molecule and renal-dose question

**Retrieval effects**

- sparse/dense branches retrieve lexical and semantic candidates;
- structured lookup adds exact Bortezomib and renal/dose-section candidates;
- ranking computes per-value coverage rather than “any overlap”;
- a renal-dose article for Atorvastatin may appear as related evidence but cannot be a direct match;
- if no passage covers both Bortezomib and renal dosing, return `insufficient_evidence` with labeled related sources.

**Visual**

Transform the query into chips, then show each chip connecting to a retrieval or policy action.

---

## Slide 23 — New Behavioral Signals Enter a Governed Batch Learning Loop

**Time:** 2 minutes

**Trait:** Production thinking

**On-slide content**

```text
Requests + rendered impressions + interactions
                    |
                    v
Schema validation, deduplication, bot filtering,
rank/version joins, and delayed-event closure
                    |
                    v
Exposure-aware query–content table
  - raw clicks, valid dwell, saves, returns
  - reformulation and abandonment
  - explicit feedback and downstream task outcome
  - unexposed remains unjudged
                    |
                    v
Position/exposure diagnostics + versioned snapshot
                    |
                    v
Temporal and template-grouped train/validation/test
                    |
                    v
Challenger → offline gates → shadow → canary → experiment
                    |
                    v
Promote or reject; champion and rollback remain available
```

Governance rules:

- no online learning from an individual click;
- close the observation window before labeling;
- retrain because data sufficiency or drift warrants it, not just because a date arrived;
- train intent from intent evidence, not inferred click intent;
- index refresh is separate from model retraining;
- use selective reviewer audits for high-risk or disputed cases when available, while prioritizing complete behavioral capture at scale.

**Visual**

A circular learning loop with a hard gate between events and training.

---

## Slide 24 — Monitoring Must Explain Where Quality Changed

**Time:** 2 minutes

**Trait:** Production thinking

**On-slide content**

**Real time: service health**

- availability, saturation, p50/p95/p99 latency;
- branch errors, timeouts, fallback rate;
- empty candidates and `insufficient_evidence` rate;
- active model, index, schema, and configuration versions;
- retracted or unauthorized content checks.

**Daily: data and search behavior**

- request → impression → interaction join coverage;
- missing rank/version IDs, duplicate and delayed events;
- language, intent confidence, OOD, entity, and slot distributions;
- candidate counts and branch overlap;
- click, save, valid dwell, return, reformulation, and abandonment by rank;
- exact-entity, pairwise-conjunction, and explicit-conflict rates in top K.

**Weekly/monthly: quality and drift**

- candidate Recall@K and behavior-derived NDCG with judgment coverage;
- harmful-mismatch audits for wrong molecule, disease, or critical constraint;
- confidence calibration and abstention quality;
- language, intent, and safety-critical slices;
- champion–challenger paired changes and retraining readiness.

**Visual**

Three stacked dashboards labeled real time, daily, and model-health review.

**Speaker notes**

Every trace should carry component versions and branch provenance so a change can be attributed to traffic, extraction, candidate generation, ranking, content freshness, or instrumentation.

---

## Slide 25 — What I Would Do Differently with Three Months

**Time:** 4 minutes

**Trait:** Research judgment, technical depth, and production thinking

**On-slide content**

### Month 1 — Fix the evidence and evaluation foundation

- instrument explicit rendered rank, branch provenance, valid dwell, reformulation, return, save, negative feedback, and downstream task outcome;
- preserve unexposed as unjudged and establish position/exposure diagnostics;
- freeze shared temporal and template-grouped splits for intent and retrieval;
- build a golden regression set from high-risk and disagreement cases;
- use a small selective expert audit only for safety-critical calibration if available;
- ingest article bodies or abstracts and define clinically meaningful sections.

**Exit criteria**

- event joins and version attribution are reliable;
- outcome maturity windows are defined;
- evaluation is reproducible and no longer depends only on historical exposure;
- full-text or section evidence is searchable in a staging index.

### Month 2 — Build the retrieval system the failure analysis actually calls for

- implement the versioned structured query object;
- run sparse, dense, and structured candidate generation in parallel;
- add value-aware entity coverage and explicit comparison/interaction relations;
- retrieve from dosing, safety, renal, pregnancy, monitoring, and interaction sections;
- add direct / related / insufficient-evidence tiers;
- confidence-gate intent and add an ambiguity/OOD fallback;
- build deterministic parity, latency, resilience, and rollback tests.

**Exit criteria**

- Q019-, Q101-, and Q146-style conjunction failures are handled by prerequisites or abstention;
- candidate recall and harmful mismatch improve on the frozen regression set;
- a fallback path works when intent, dense retrieval, or structured lookup fails.

### Month 3 — Evaluate, harden, and only then reconsider learning

- run shadow evaluation with complete impressions and position-aware metrics;
- inspect changed rankings, abstentions, and high-risk slices;
- calibrate fusion weights and intent confidence on validation only;
- train a challenger only if label and candidate coverage are sufficient;
- add monitoring dashboards, alerts, runbooks, and atomic rollback;
- canary behind quality and safety guardrails.

**Exit criteria**

- quality gains persist across languages and constraint slices;
- event completeness, latency, freshness, and fallback targets pass;
- any learned challenger beats the deterministic champion on preregistered metrics without increasing harmful mismatch.

**Visual**

A three-column roadmap with “evidence,” “retrieval,” and “controlled launch” as the dominant themes.

**Speaker notes**

The sequencing is deliberate: complete the behavioral signal and answer-bearing corpus before spending the final month on model complexity. A learned reranker is an option, not a required deliverable.

---

## Slide 26 — Final Takeaways

**Time:** 1 minute, followed by 5–10 minutes of questions

**On-slide content**

1. Define intent around retrieval decisions, not around an attractive label list.
2. Weak supervision is usable when provenance, disagreement, and uncertainty remain visible.
3. Evaluate unseen templates; random row splits can reward memorization.
4. Intent helps where it changes preferred evidence, but it is not a universal ranking boost.
5. Better models cannot retrieve evidence that is absent from the indexed content.
6. Clinical queries require entity and relationship conjunctions, not independent additive matches.
7. Production quality depends on complete behavioral signals, versioned data, fallbacks, monitoring, and the ability to say “insufficient evidence.”

**Visual**

Return to the opening flow, now annotated with the seven lessons.

---

# Optional Appendix

## Appendix Slide A1 — Full Intent Distribution

| Intent | Queries |
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

---

## Appendix Slide A2 — Structured Retrieval Formula and Its Limitation

**On-slide content**

```text
entity_score = matched entity dimensions / populated query entity dimensions
context_score = matched contextual constraints / active contextual constraints

structured_score = mean(entity_score, context_score)
```

Limitation: “any overlap within a dimension” can give full molecule-dimension credit even when a multi-drug request requires every molecule and their relationship.

Signed-score redundancy example:

```text
0.20E - 0.20(1 - E) = 0.40E - 0.20
```

If conflict is simply the complement of coverage, the penalty adds no independent ranking information.

---

## Appendix Slide A3 — Language and Complexity Slices

| Test slice | BM25 NDCG@10 | Hybrid without intent | Hybrid + predicted intent |
| --- | ---: | ---: | ---: |
| English | 0.01407 | 0.01860 | 0.02279 |
| Bahasa Indonesia | 0.00208 | 0.00256 | 0.01020 |
| Mixed language | 0.00921 | 0.00518 | 0.01704 |
| No extra context | 0.01554 | 0.01787 | 0.02437 |
| One context constraint | 0.00580 | 0.00480 | 0.00874 |
| Multiple constraints | 0.00000 | 0.00000 | 0.02409 |

Use support labels when presenting these values: several constrained slices are sparse, and the multiple-constraint estimate is based on 12 eligible queries.

---

## Appendix Slide A4 — Recommended Fallback Matrix

| Failure | Response behavior |
| --- | --- |
| Intent timeout or low confidence | Rank without intent |
| Entity extraction timeout | Sparse + dense; suppress direct-match claim |
| Dense timeout | Sparse + structured |
| Structured lookup failure | Sparse + dense; neutral structured score |
| Ranker/config unavailable | Stable BM25 fallback |
| No candidate satisfies required evidence | `insufficient_evidence` plus labeled related sources |
| Model/index incompatibility | Refuse activation and retain the previous bundle |

---

## Appendix Slide A5 — Reference Papers and Exact Project Use

1. **Lopez I, Swaminathan A, Vedula K, et al.** “Clinical entity augmented retrieval for clinical information extraction.” *npj Digital Medicine*. 2025;8:45. DOI: 10.1038/s41746-024-01377-1.
   - Used to shape the extract → normalize → augment → match → ablate sequence for structured entity and context retrieval.
   - Not treated as a reproduced model or a source of borrowed performance claims.

2. **Monsalve K, Villa MC, Castaño-Villegas N, Zea J, Velásquez L.** “Clinical Information Needs Among Latin American Physicians: A Multi-Country Analysis of Semantic Clinical Search.” *medRxiv*. 2026. Preprint. DOI: 10.64898/2026.06.26.26356340.
   - Used as the physician-search seed taxonomy and as support for reviewing representative, rare, low-margin, multilingual, and boundary cases.

3. **Liang Z, Zhao Y, Xu H, Huang H, et al.** “A hybrid model integrating RoBERTa, TF-IDF, and attention mechanism for medical query intent classification.” *Scientific Reports*. 2025;15:42847. DOI: 10.1038/s41598-025-25783-x.
   - Used to motivate finer intent boundaries and testing complementary semantic, lexical, and category/structured signals.
   - Adapted to the available multilingual weak-supervision setting rather than reproduced directly.

---

## Appendix Slide A6 — Questions to Invite

- Which information needs should be hard prerequisites versus soft preferences?
- What additional behavioral outcome best approximates successful clinical information seeking?
- Where is abstention preferable to a related but incomplete result?
- Which slices require explicit launch gates by language, intent, or safety constraint?
- What evidence threshold should be required before reconsidering a learned reranker?
