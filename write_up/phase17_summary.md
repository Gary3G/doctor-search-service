# Phase 17 — Production System Design

## Executive Summary

The recommended first production version is a conservative, observable search service built around the **frozen Phase 12 runtime ranker selected in Phase 16**:

- normalized BM25 over the searchable content text;
- frozen `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` embeddings;
- supplied/production NER entities and bounded ICD-10/ATC hierarchy features;
- deterministic contextual-slot extraction;
- the Phase 5 T1-E4 intent classifier;
- a hard predicted-intent/content-type compatibility feature with the validation-selected weight of `0.25` on the four-component R-E6 base score;
- deterministic ranking and stable tie-breaking;
- no separately learned reranker or cross-encoder in the launch candidate.

This is the appropriate starting point because the learned logistic reranker, multilingual cross-encoder, MedCPT cross-encoder, and S-PubMedBERT replacement did not demonstrate a validation-supported improvement that transferred to the temporal test set. The selection means **“best supported by the current evidence,” not “clinically proven.”** The present evaluation uses sparse, exposure-biased behavioral labels, only about three percent of returned top-10 results are judged, and the corpus available to the assessment contains titles rather than abstracts or full article sections.

Productionization is therefore not simply a matter of putting the notebook behind an API. The work must add:

1. an online query-understanding and retrieval service for arbitrary queries;
2. offline full-text/section ingestion, index construction, model packaging, and reproducible versioning;
3. conjunction-aware safety checks and an explicit insufficient-evidence response;
4. privacy-preserving impression and engagement logging;
5. clinician-adjudicated relevance evaluation alongside debiased behavioral metrics;
6. monitoring, fallbacks, progressive rollout, and fast rollback;
7. a retraining process in which intent and ranking components are governed separately.

The search system should assist clinicians in finding source content. It should not diagnose, prescribe, synthesize unsupported treatment advice, or present ranking confidence as medical certainty. Source provenance, publication date, and evidence quality must remain visible to the doctor.

---

## 1. Design Goals and Non-Goals

### 1.1 Goals

The production system should:

- return clinically topical content for English, Bahasa Indonesia, and mixed-language queries;
- respect explicit disease, molecule, drug-class, age, pregnancy, renal/hepatic, route, year, dose, comparison, and prior-treatment constraints where evidence exists;
- retrieve both exact lexical matches and useful semantic matches;
- preserve provenance and expose why a result matched;
- remain useful when one model or feature family is unavailable;
- distinguish missing evidence from contradictory evidence;
- detect corpus gaps instead of confidently returning the wrong molecule or disease;
- support reproducible offline evaluation, shadow testing, canaries, A/B tests, and rollback;
- collect high-quality feedback without turning raw clicks into unquestioned truth;
- keep latency and infrastructure cost predictable.

### 1.2 Non-goals for the first production release

The first release should not:

- generate patient-specific treatment recommendations;
- replace clinical judgment or local guidelines;
- claim that a click, dwell event, bookmark, or return visit proves clinical relevance;
- fine-tune a query encoder, train a cross-encoder, or deploy a learned reranker before better labels exist;
- hard-filter on every extracted slot, because extraction errors and incomplete document metadata can destroy recall;
- silently infer patient identity or persist raw personal/health information beyond an approved retention policy;
- use the assessment’s cached 500-query cross-product as an online serving mechanism;
- treat the observed Phase 12 or Phase 16 test scores as a production acceptance threshold.

### 1.3 Initial service-level objectives

Traffic is not supplied, so capacity must be load-tested against observed production demand rather than invented from the assessment sample. Reasonable **starting objectives**, to be approved with product and platform owners, are:

| Objective | Starting target | Notes |
| --- | ---: | --- |
| Search API availability | 99.9% monthly | Excludes planned maintenance only if product policy permits. |
| p50 end-to-end latency | <= 150 ms | Warm service, cached models and index. |
| p95 end-to-end latency | <= 400 ms | Includes query understanding and candidate ranking. |
| p99 end-to-end latency | <= 800 ms | Beyond this, use a bounded fallback rather than queue indefinitely. |
| Successful-result rate | >= 99.5% | A deliberate `insufficient_evidence` response is successful, not a server error. |
| Index freshness | <= 24 hours initially | Urgent safety content needs a separate expedited path. |
| Event durability | >= 99.9% accepted events | Measured by producer/consumer reconciliation. |
| Rollback time | <= 15 minutes | Model/config/index versions must be independently reversible. |

Clinical-quality targets should be set only after a clinician-judged benchmark exists. Until then, behavioral NDCG and CTR are diagnostics rather than release criteria by themselves.

---

## 2. What the Assessment Establishes

### 2.1 Selected launch candidate

The runtime ranking formula is the Phase 12 predicted-hard-intent configuration:

```text
base_score = mean(
    normalized_bm25,
    normalized_dense_similarity,
    entity_compatibility,
    contextual_compatibility
)

final_score = base_score + 0.25 * predicted_intent_content_type_compatibility
```

Phase 16 retains multilingual MiniLM and selects no additional reranker. On the assessment’s temporal split, this system achieved validation/test NDCG@10 of `0.03146 / 0.01851`. These numbers reflect behavior-derived judgments and are not estimates of clinical correctness.

### 2.2 Evidence supporting each component

- BM25 remains a useful exact-match anchor and was important in Phase 11 ablations.
- Dense retrieval was stronger than BM25 alone, although its incremental value inside the complete additive score was not established.
- Structured entities improved the BM25 branch, particularly where lexical matching alone was insufficient.
- Context evidence was sparse in titles and unstable; it should be used cautiously and never assume that absence means conflict.
- Intent was the strongest observed structured discriminator. Hard predicted intent preserved most of the assisted-label benefit and agreed with the assisted label on 85.8% of the 500 queries.
- Intent gains were concentrated in interaction, dosing, and some safety information needs rather than globally distributed.

### 2.3 Critical limitations carried into production planning

- Intent targets are model-assisted weak labels, not independent clinician annotations.
- Template-held-out intent Macro F1 was `0.842`, materially below row-stratified `0.970`.
- The final intent model was refit on queries that overlap the retrieval temporal test, so the current result is not a clean unseen-query estimate.
- The retrieval target is exposure- and position-biased engagement.
- Unjudged content is computationally assigned zero gain but is not known to be irrelevant.
- Titles do not contain much of the dosing, pregnancy, renal, contraindication, or monitoring evidence needed to answer constrained queries.
- The current additive score can let a generic context template for the wrong molecule outrank an entity-correct result.
- Comparison and interaction queries need all requested entities and their relationship, not partial independent matches.
- The small assessment corpus does not establish production latency, capacity, multilingual coverage, or safety.

These limitations determine the production roadmap: improve evidence and evaluation before increasing model complexity.

---

## 3. Target Architecture

### 3.1 Online serving path

```text
Doctor / Client
      |
      v
API Gateway: authentication, authorization, rate limits, request ID
      |
      v
Search Orchestrator
      |
      +--> normalization + language identification
      +--> entity recognition/normalization
      +--> contextual-slot extraction
      +--> intent prediction + confidence/OOD checks
      |
      v
Structured Query Object
      |
      +--> sparse index --------------------+
      |                                     |
      +--> dense ANN index -----------------+--> candidate union/dedup
      |                                     |
      +--> structured/entity lookup --------+
      |
      v
Feature assembly + deterministic Phase 12 ranker
      |
      v
Conjunction checks + evidence/quality policy + abstention
      |
      v
Top-K results with provenance, match reasons, and version metadata
      |
      +--> async impression event
      `--> metrics/traces/audit metadata
```

### 3.2 Offline data and model path

```text
Content sources
      |
      v
Ingestion -> validation -> canonicalization -> deduplication -> sectioning
      |
      +--> NER / terminology normalization / safety metadata
      +--> BM25 document construction
      +--> dense embedding generation
      +--> content quality and provenance features
      |
      v
Immutable index bundle + manifest
      |
      v
Staging validation -> shadow load -> atomic production activation

Search events + reviewed judgments
      |
      v
Validated analytics tables -> debiasing -> train/validation/test snapshots
      |
      +--> intent training/evaluation
      +--> retrieval/reranking evaluation
      +--> slice and safety evaluation
      |
      v
Model registry -> approval gates -> shadow/canary -> champion/challenger
```

The online and offline paths must communicate through versioned contracts, not shared notebook state or mutable CSV files.

### 3.3 Logical services

| Component | Responsibility | State/failure behavior |
| --- | --- | --- |
| API gateway | Authentication, tenant policy, rate limiting, request size limits | Reject invalid/unauthorized traffic before search. |
| Search orchestrator | Deadline propagation, parallel calls, candidate merge, rank, response | Owns request-level fallback decisions. |
| Query understanding | Normalize language, entities, slots, and intent | Returns values, confidence, provenance, and warnings. |
| Sparse retrieval | Exact and fielded lexical retrieval | Primary low-risk fallback. |
| Dense retrieval | Multilingual semantic candidates from ANN | Optional under timeout; index/model versions must match. |
| Structured retrieval | Entity/code lookups and bounded hierarchy expansion | Improves candidate recall; must not over-expand. |
| Feature/ranking layer | Calculate frozen Phase 12 scores | Pure, deterministic for a fixed request and version set. |
| Evidence policy | Required-entity checks, contraindication/constraint conflict, abstention | Cannot be bypassed by a high semantic or intent score. |
| Content metadata store | Display metadata, provenance, source, dates, permissions | Must enforce document visibility and retraction status. |
| Event collector | Impression and interaction logging | Asynchronous; search must not fail if analytics is unavailable. |
| Configuration/model registry | Approved weights, models, schemas, index compatibility | Signed, immutable versions with rollback pointers. |

A small initial deployment can combine several logical services in one process. The boundaries still matter because they define contracts, metrics, testing, and future scaling.

---

## 4. Online Query Flow

### 4.1 Request validation and policy

The gateway should validate:

- authenticated doctor/user and tenant/market;
- supported API version;
- maximum query length and encoding;
- locale, region, and permitted content collections;
- requested result count within a safe bound;
- optional filters such as publication date or content type;
- absence of unsupported control characters or query-injection payloads.

Every request receives a non-identifying `request_id`. The raw query should not be included in generic application logs. If raw-query retention is approved, it belongs in a restricted data store with explicit purpose, encryption, access controls, and a short retention schedule.

### 4.2 Normalization and language handling

Normalization should be conservative:

- Unicode normalization and whitespace cleanup;
- case-folded retrieval representation while preserving the original display query;
- standardized punctuation and numeric units;
- common medical abbreviation expansion with ambiguity tracking;
- language identification that permits `EN`, `ID`, and `MIXED` rather than forcing one language;
- optional spelling correction only as an alternate retrieval form, never an irreversible rewrite.

The service should retain both the original and normalized forms. Drug names, codes, doses, units, and numeric thresholds must not be altered by general spell correction. If language confidence is low, run language-neutral normalization and use multilingual retrieval.

### 4.3 Entity recognition and normalization

Production will not receive the assessment’s pre-supplied entity columns, so an entity service must provide:

- diseases and ICD-10 codes;
- molecules and ATC codes;
- drug classes and ATC classes;
- therapeutic areas;
- surface spans, canonical values, confidence, and model/dictionary provenance;
- relationships such as comparison pairs, interaction pairs, and disease–drug association when explicit.

Exact terminology matches should be combined with an evaluated multilingual NER model or terminology linker. Bounded hierarchy expansion may add ICD parents and molecule-to-ATC-class relations. Expansion must be labeled separately from exact matches so that a class-level match cannot masquerade as an exact molecule match.

Ambiguous abbreviations should produce alternatives with confidence rather than a silent single interpretation. Low-confidence entities can contribute soft retrieval evidence, but safety-critical filtering must require stronger evidence or user clarification.

### 4.4 Contextual-slot extraction

The assessment extractor covers age group, pregnancy, year, recency, dose context, route, renal impairment, hepatic impairment, comparison, negation, and prior-treatment failure. Production should extend the schema to value-bearing slots where supported:

| Group | Examples | Matching semantics |
| --- | --- | --- |
| Demographics | age, age group, sex, pregnancy/lactation | Exact/range compatibility; unknown is neutral. |
| Administration | dose value/unit, frequency, route, duration, timing | Normalize units; explicit contradiction differs from absence. |
| Physiology/labs | eGFR/CrCl value or range, hepatic function, lab name/value/unit | Preserve comparator and units; use clinically reviewed ranges. |
| Disease state | severity, stage, acute/chronic, refractory, comorbidity | Value-aware, potentially ontology-backed. |
| Treatment state | current/prior therapy, failure, intolerance, escalation | Relationship-aware, not a bag of booleans. |
| Evidence constraints | year, latest/recency, guideline/evidence request | Affects source/type/recency preferences. |
| Logical operators | negation, comparison, interaction, conjunction | Maintains scope and entity relationship. |

Each slot needs `value`, `normalized_value`, `span`, `confidence`, `source`, and `scope`. Missing document evidence remains **unknown**, not conflicting. Negation must be scoped to the affected entity or condition rather than represented only as a query-level flag.

### 4.5 Intent classification

The initial intent service packages the Phase 5 T1-E4 classifier and all preprocessing together. It returns:

- top intent and parent intent;
- full class probabilities;
- top-two margin;
- entropy/calibration score;
- out-of-distribution indicator;
- model version and feature-extraction version.

The launch ranker uses hard predicted intent only when confidence is sufficient. A production confidence policy should be selected on a calibration set; it must not be copied from the assessment without evaluation. When confidence is low, the service should either use a conservative multi-intent representation or set the intent ranking feature to neutral. It should never force a low-margin prediction simply because an argmax exists.

The system must support `Other / Ambiguous` and out-of-distribution behavior. The assessment classifier cannot learn this class because it has no training examples, so production launch requires an abstention mechanism even before the taxonomy is expanded.

### 4.6 Structured query object

An internal representation should be immutable within the request:

```json
{
  "schema_version": "query-understanding-v1",
  "request_id": "opaque-id",
  "original_text": "restricted/not logged by default",
  "normalized_text": "...",
  "languages": [{"code": "id", "probability": 0.62}, {"code": "en", "probability": 0.38}],
  "entities": [
    {
      "type": "molecule",
      "surface": "...",
      "canonical_id": "ATC:...",
      "match_kind": "exact",
      "confidence": 0.97
    }
  ],
  "relations": [{"type": "interaction_between", "arguments": ["entity-1", "entity-2"]}],
  "slots": [{"type": "renal_function", "operator": "<", "value": 30, "unit": "mL/min"}],
  "intent": {
    "label": "Dosing / Administration",
    "confidence": 0.74,
    "margin": 0.19,
    "abstained": false
  },
  "warnings": [],
  "versions": {
    "normalizer": "...",
    "entity_model": "...",
    "slot_rules": "...",
    "intent_model": "..."
  }
}
```

The object passed to analytics should omit or tokenize sensitive spans according to the privacy policy.

### 4.7 Candidate generation

Sparse, dense, and structured retrieval should run in parallel under a shared deadline.

**Sparse branch**

- Use BM25 with field-specific boosts for title, section heading, body/passage, normalized entities, and source metadata.
- Preserve phrase, exact molecule/code, and numeric matches.
- Keep the assessment parameters (`k1=1.5`, `b=0.75`) only as an initial reference; retune on a clinician-judged production corpus.

**Dense branch**

- Encode the query once with the frozen multilingual MiniLM model.
- Search a precomputed ANN index over passages or sections, not only titles.
- Store normalized vectors and metric configuration in the index manifest.
- Enforce compatibility between query encoder version and content-embedding version.

**Structured branch**

- Retrieve exact canonical-entity matches first.
- Add bounded hierarchy candidates separately.
- Support pairwise lookups for multi-molecule comparison and interaction queries.
- Apply authorization and content-availability filters before the candidate reaches ranking.

An initial candidate budget might be 100–300 per branch, deduplicated to a bounded union. The exact depths must be chosen by candidate-recall and latency curves. A reranker cannot recover a relevant document excluded at this stage, so Recall@K of the union is a primary engineering metric.

### 4.8 Candidate union and feature assembly

Candidates are keyed by content/passage ID and retain provenance from every branch. Scores should be normalized using fixed, versioned calibration learned on training/validation data or rank-based fusion. Per-request min-max normalization can be unstable when a branch has little score variance and should be monitored before production adoption.

Feature families include:

- normalized BM25 score and sparse rank;
- dense cosine similarity and dense rank;
- exact disease, molecule, class, and therapeutic-area matches;
- bounded ICD/ATC hierarchy matches;
- requested-value entity coverage;
- pairwise comparison/interaction coverage;
- explicit entity conflicts;
- value-aware contextual compatibility and explicit contradiction;
- intent/content-type compatibility;
- content quality, source quality, publication and review dates;
- language compatibility;
- retraction/expiry/availability policy;
- branch provenance and candidate-recall diagnostics.

User identity, protected attributes, popularity shortcuts, impression position, and downstream engagement must not be online ranking features unless separately justified, reviewed, and tested for harm.

### 4.9 Ranking policy

The first production candidate should faithfully reproduce the validated Phase 12 score while using better online inputs and passage evidence. It is best described as a **deterministic ranking layer**, not a learned reranker.

Before scoring, apply non-negotiable eligibility rules: access permission, active content, permitted geography, no known retraction, and required source policy. After scoring, apply conjunction-aware guards:

- multi-drug interaction/comparison queries require coverage of every high-confidence requested molecule for a result to be labeled a direct match;
- wrong-molecule evidence cannot be rescued by a generic dosing or renal template;
- explicit pregnancy, renal, hepatic, route, or numeric contradictions receive a policy penalty or are demoted from direct-answer positions;
- absence of a slot in a document remains unknown and may still be retrieved, especially while full-text coverage is incomplete;
- a hierarchy match cannot receive the same explanation label as an exact match.

These guards should first be evaluated as features and result labels rather than aggressive hard filters. The only hard filters should be high-precision policy conditions whose recall impact has been reviewed.

Stable tie-breaking should use deterministic keys such as score, evidence tier, publication/review policy, and content ID. Never use nondeterministic set order.

### 4.10 Evidence tiers and abstention

The response should distinguish:

1. **Direct match:** all required high-confidence entities/relations are present and no explicit critical constraint conflicts.
2. **Related evidence:** partial or hierarchical match that may inform the query but does not satisfy every requirement.
3. **Insufficient evidence:** no candidate meets the minimum direct-match policy.

The service can still return related evidence in the third case, but the UI must state the gap. For example: “No indexed source explicitly covers both requested medicines and the interaction; showing related sources.” This is safer and more honest than presenting a wrong-molecule template as a complete answer.

Abstention thresholds should be selected against clinician-reviewed harmful-mismatch and coverage metrics, not CTR.

### 4.11 Response contract

Each result should provide:

- content/passage ID and canonical content ID;
- title and a bounded matched excerpt;
- content type, source, author/publisher where available;
- publication date, last reviewed date, and version;
- language;
- source-quality/evidence metadata;
- match tier and concise evidence reasons;
- URL or authorized access token;
- rank and an opaque impression token;
- model, index, ranker, and policy versions at response level.

Internal raw scores can be logged in restricted diagnostics but should not be displayed as probabilities of clinical correctness.

### 4.12 How query decomposition flows into retrieval

Query decomposition is not a separate analytical report that sits beside retrieval. It is the control plane for candidate generation, feature calculation, evidence policy, and the explanation attached to each result.

```text
Raw query
   |
   +--> normalized text -----------------------> BM25 query + dense encoder input
   |
   +--> language ------------------------------> analyzer/field choice + language feature
   |
   +--> disease/molecule/class/area -----------> exact structured lookup
   |                                             hierarchy expansion
   |                                             entity coverage/conflict features
   |
   +--> age/pregnancy/renal/route/year/etc. ---> compatible passage lookup
   |                                             context match/conflict features
   |                                             safety/evidence policy
   |
   +--> comparison/interaction relations ------> pairwise candidate lookup
   |                                             all-entity conjunction check
   |
   +--> intent + confidence -------------------> content-type compatibility
   |                                             intent boost or neutral fallback
   |
   `--> required evidence set -----------------> direct / related / insufficient tier
                                                 result explanation
```

The flow has four concrete effects.

1. **It changes what is retrieved.** Normalized text feeds both BM25 and the dense query encoder. Exact entities and codes issue structured lookups, while ICD/ATC parents add bounded recall candidates. Explicit entity relations issue pairwise lookups so an interaction between A and B is not reduced to independent matches for A or B.
2. **It changes how candidates are scored.** Every candidate is compared with the structured query object to calculate exact entity coverage, hierarchy coverage, value-aware slot compatibility, explicit conflicts, pairwise relation coverage, language compatibility, and intent/content-type compatibility. The launch score combines these with sparse and dense scores.
3. **It constrains what can be called an answer.** High-confidence required entities and relations form a `required_evidence_set`. A document missing one comparator may still appear as related evidence, but cannot be presented as a direct answer. Explicit critical contradictions can demote a candidate even when its lexical or semantic score is high.
4. **It makes the result auditable.** The same matches used by ranking produce reason codes such as `exact_molecule`, `icd_parent`, `renal_constraint_unknown`, or `intent_content_compatible`. This avoids inventing a post-hoc explanation unrelated to the score.

The mapping should be explicit and versioned:

| Decomposed query output | Candidate-generation use | Ranking/policy use | Missing or low-confidence behavior |
| --- | --- | --- | --- |
| Normalized text | BM25 query and dense encoding | BM25/dense scores | Always available from conservative normalization. |
| Language probabilities | Select analyzers/fields; multilingual index | Language compatibility and slice tag | Use multilingual/default path. |
| Disease/ICD | Exact code/name lookup; bounded parent expansion | Exact, hierarchy, coverage, and conflict features | Do not hard-filter; mark unknown. |
| Molecule/ATC | Exact lookup; molecule-to-class expansion | Exact molecule prerequisite for direct-match dosing/safety results | Do not let a generic drug-class match claim exact coverage. |
| Drug class/therapeutic area | Structured recall candidates | Weaker class/topic compatibility | Keep separate from exact molecule evidence. |
| Comparison/interaction arguments | Pairwise lookup requiring both arguments | All-argument coverage and relationship feature | If one argument is unresolved, lower confidence and avoid direct-match claim. |
| Age/pregnancy/renal/hepatic | Compatible passage lookup when indexed | Match, unknown, explicit-conflict state | Unknown is neutral; explicit conflict is not. |
| Dose/route/duration/lab value | Unit-normalized field/range lookup | Value/range compatibility | Retain raw span and request clarification when ambiguous. |
| Year/recency | Date-aware candidate branch/filter | Recency compatibility with source-quality guard | Do not prefer newer low-quality evidence solely for recency. |
| Intent distribution | Optional intent-specific candidate expansion | Hard compatibility only above confidence threshold; otherwise neutral/mixture | Abstain on low margin or OOD input. |

An example illustrates the difference. For `renal dose adjustment of bortezomib`, decomposition produces the molecule `bortezomib`, a renal-impairment slot, and dosing intent. BM25 and dense retrieval find lexical and semantic candidates; the structured branch adds exact bortezomib and renal/dose-section candidates. During ranking, an article about renal dose adjustment for another medicine can receive contextual similarity but fails exact-molecule coverage, so it cannot outrank an entity-correct result merely because it follows a common renal-dosing title template. If no passage covers both bortezomib and renal dosing, the response becomes `insufficient_evidence` with related sources rather than a false direct match.

The full decomposition should be calculated once per request and reused by all branches. Re-running subtly different extractors inside each retriever would create inconsistent scoring, explanations, and monitoring.

---

## 5. Offline Content and Index Pipeline

### 5.1 Content ingestion

Every content source needs a connector contract covering:

- stable source ID and canonical content ID;
- title, abstract, body, section hierarchy, tables where usable, and language;
- publication, update, review, expiry, and retraction dates;
- content type and source type;
- geography/licensing/access controls;
- provenance and checksum;
- deletion and correction events.

The pipeline should reject or quarantine malformed records, unexpected schema changes, missing identifiers, invalid dates, empty text, and unauthorized content. Corrections and retractions require an expedited path rather than waiting for a routine rebuild.

### 5.2 Canonicalization and deduplication

Create a canonical document with versioned passages. Detect exact duplicates by checksum and near duplicates by normalized text/signature. Preserve source provenance even when several source records map to one canonical item. Search should avoid filling top results with copies of the same article or template.

### 5.3 Section/passage indexing

Index at clinically meaningful boundaries such as indications, dosing, contraindications, interactions, pregnancy, renal adjustment, monitoring, and guideline recommendations. Keep document-level metadata attached to each passage.

Passage-level indexing directly addresses the largest assessment limitation: relevant constraints frequently appear in the body but not in the title. Candidate results should be collapsed to a configurable number per document after passage scoring to preserve result diversity.

### 5.4 Offline enrichment

For each content version, compute:

- sparse index text fields;
- dense MiniLM embedding;
- exact and normalized entities with spans;
- bounded hierarchy values;
- contextual evidence with scope;
- content type, language, recency, and quality features;
- evidence-section labels where available;
- retraction, expiry, and access policy.

Automatically extracted clinical fields must retain confidence and provenance. Human-curated source metadata should not be overwritten by a lower-confidence model output.

### 5.5 Index bundles and activation

An immutable index bundle should include:

- sparse index version;
- dense index version and encoder hash;
- metadata/structured index version;
- source snapshot and passage counts;
- schema version;
- preprocessing code/config hashes;
- validation results;
- build timestamp and owner;
- compatibility matrix with query and ranking versions.

Activation should be atomic: a request must never mix an old sparse index with incompatible new embeddings or metadata. Keep at least the active and previous known-good bundles available for rollback.

---

## 6. Latency, Capacity, and Cost

### 6.1 Illustrative latency budget

| Stage | p95 budget | Degradation rule |
| --- | ---: | --- |
| Gateway and request validation | 20 ms | Fail closed on authorization; reject malformed requests. |
| Normalization/language | 20 ms | Fall back to multilingual/default normalization. |
| Entity/slot/intent inference | 100 ms | Use partial structured object with warnings; neutralize failed features. |
| Sparse, dense, structured retrieval in parallel | 150 ms | Continue with completed branches at deadline. |
| Feature assembly/ranking/policy | 60 ms | Deterministic local path; fail to sparse ranking if needed. |
| Metadata fetch/serialization | 50 ms | Bounded result set and cache. |
| Network margin | 100 ms | Shared deadline propagation. |

The stages run partly in parallel, so budgets are not simply additive. These are design targets, not measured assessment results.

### 6.2 Capacity planning

Measure and plan for:

- peak requests per second and burst factor;
- average and p99 query length;
- candidate depth per branch;
- corpus/passages/vector count and growth rate;
- embedding inference time per CPU/GPU instance;
- cache hit rates;
- concurrent index versions during rollout;
- event volume and retention;
- rebuild duration and recovery time.

Load tests should replay language, query-length, entity-count, and contextual-complexity distributions, including expensive adversarial cases. Run soak tests to detect memory leaks and ANN tail-latency drift.

### 6.3 Cost controls

- Precompute all document embeddings.
- Encode each unique normalized query once per request and use a bounded query cache only if privacy policy permits.
- Keep candidate and reranking depths bounded.
- Batch offline embedding jobs.
- Autoscale stateless online workers while keeping index memory requirements explicit.
- Use the deterministic launch ranker before paying the latency/cost of a cross-encoder that has not demonstrated value.
- Track cost per thousand searches and cost per index rebuild by model/index version.

---

## 7. Failure Handling and Fallback Matrix

| Failure | User-visible behavior | Logged action |
| --- | --- | --- |
| Intent service timeout/low confidence | Rank without intent; do not force a class | `intent_degraded=true`, confidence/version. |
| Entity service timeout | Sparse+dense retrieval; suppress direct-match claim | Missing feature family and latency. |
| Dense service timeout | Sparse+structured result | Branch timeout and candidate overlap. |
| Sparse service timeout | Dense+structured if available; otherwise service error | High-severity operational alert. |
| Structured lookup failure | Sparse+dense; neutral structured score | Schema/index mismatch alert. |
| Ranker/config unavailable | Stable BM25 fallback | Page/on-call if sustained. |
| Metadata store partial failure | Drop incomplete candidate; backfill from cache | Missing content IDs and store health. |
| Event collector unavailable | Serve results; buffer/drop by explicit policy | Event-loss counter and reconciliation alert. |
| No direct candidate | `insufficient_evidence` plus clearly labeled related sources | Corpus-gap event for review. |
| Index/model incompatibility | Refuse activation; retain prior bundle | Deployment gate failure. |

Fallback quality must be evaluated offline. A technically successful fallback that returns unsafe mismatches is not acceptable.

---

## 8. Feedback and Learning Loop

### 8.1 Event model

At minimum, log separate append-only events for:

**Search request**

- request/impression ID, pseudonymous user/session ID, timestamp;
- market, app version, language signals;
- query fingerprint or approved protected query representation;
- query-understanding outputs/confidences without unrestricted raw PHI;
- all serving versions and degradation flags.

**Impression**

- ordered content IDs actually rendered;
- rank, match tier, branch provenance, and score components;
- experiment/champion-challenger assignment;
- presentation context and pagination;
- eligibility and abstention outcome.

**Interaction**

- click/open, save/bookmark, share, dwell with heartbeat validity, scroll, return visit;
- result ID, original impression ID, event timestamp;
- explicit helpful/not-helpful feedback and reason where offered.

**Content lifecycle**

- content update, correction, expiry, retraction, and access-policy changes.

Events require unique IDs, schema versions, idempotency keys, event-time and ingestion-time timestamps, and bot/internal-traffic markers.

### 8.2 Interpreting behavior

Behavior remains useful but biased:

- only shown items can be clicked;
- higher ranks receive more attention;
- dwell may indicate confusion, not usefulness;
- short answers may have low dwell despite high value;
- repeated visits can indicate value or failure;
- saves/bookmarks are stronger signals but still not correctness labels.

The analytics layer should preserve `unjudged` separately from `nonpositive`. Where product risk permits, use randomized interleaving or small exploration buckets to estimate position/exposure effects. Apply inverse-propensity or doubly robust evaluation only after the logging policy is known and validated; do not mechanically debias incomplete historical data.

### 8.3 Clinician relevance program

Create a standing reviewed dataset using pooled results from BM25, the champion, dense and structured variants, challengers, and corpus-gap cases. At least two qualified clinical reviewers should independently score:

- topical relevance;
- required-entity correctness;
- contextual-constraint satisfaction;
- answer completeness;
- evidence/source quality;
- potential harmful mismatch;
- overall clinical usefulness.

Use a third reviewer for adjudication and report agreement. Reviewers should be blinded to system identity. Include English, Indonesian, mixed-language, rare intents, constrained dosing, pregnancy, renal/hepatic, multi-drug interaction, comparison, low-confidence intent, and abstention cases.

This dataset, not CTR alone, becomes the principal release gate for clinical ranking changes.

---

## 9. Retraining and Model Governance

### 9.1 Separate component schedules

**Intent classifier**

- Review drift monthly and retrain when enough new clinician-reviewed intent labels or material taxonomy/language changes exist.
- Train on labels available before a temporal cutoff.
- Group near-duplicate/delexicalized templates within folds.
- Produce out-of-fold predictions for any query reused in downstream ranker training.
- Calibrate probabilities and abstention thresholds on held-out data.

**Retrieval/ranking**

- Rebuild indexes when content changes; this is not model retraining.
- Revisit weights or train a reranker only when new judged query-document pairs support it.
- Use grouped, time-aware train/validation/test snapshots shared across intent, feature, and ranking evaluation.
- Keep a genuinely untouched confirmation period.

**Embeddings/NER/slot models**

- Upgrade independently behind compatibility tests.
- Re-embed the entire corpus when the encoder changes.
- Evaluate extraction accuracy separately from retrieval impact.

### 9.2 Minimum data policy

A fixed universal row count is misleading because power depends on effect size, query clustering, judgment density, and slice coverage. The final threshold should come from a preregistered power analysis. A practical initial eligibility policy is:

- at least **10,000 new eligible search impressions** after the last training cutoff;
- at least **2,000 positive engagement events** for any behavior-trained challenger;
- at least **1,000 newly clinician-reviewed queries** for intent retraining, with no supported intent below an agreed floor and at least 100 independent templates per major intent where feasible;
- at least **5,000 clinician-judged query-document pairs** across a minimum of 500 distinct queries for reranker reconsideration;
- at least **200 eligible reviewed queries per critical language/safety slice** used for a release claim;
- sufficient paired-query sample size to detect the predefined minimum meaningful NDCG/usefulness change at the chosen alpha and power.

If those conditions are not met, continue collecting data or update only rules/content/indexes whose behavior is independently verifiable. Do not retrain merely because a calendar date arrived.

The counts above are starting governance thresholds, not findings from the assessment. They should be revised from observed traffic, class prevalence, and variance.

### 9.3 Versioned training datasets

Every dataset snapshot should record:

- immutable event and judgment cutoffs;
- included markets/languages/content collections;
- query-template grouping and deduplication;
- labeling guideline and adjudication version;
- exposure/position debiasing method;
- feature and schema versions;
- exclusions, consent, deletion handling, and data lineage;
- hashes/counts and reproducible build job;
- train/validation/test assignment manifest.

Deleting data subject to policy must propagate to future training snapshots and, where required, trigger model/data-governance review.

### 9.4 Validation gates

A challenger must pass all relevant gates:

1. reproducible build and artifact integrity;
2. schema and model/index compatibility;
3. intent/extraction unit and regression tests;
4. no regression beyond tolerance on clinician-judged NDCG, Recall, usefulness, and harmful mismatch;
5. acceptable results on language, intent, entity-complexity, and safety-critical slices;
6. calibrated confidence and abstention performance;
7. latency, throughput, memory, and cost budgets;
8. privacy/security review and license approval;
9. shadow traffic comparison;
10. canary health and rollback exercise;
11. controlled online experiment with predeclared primary and guardrail metrics.

A higher CTR cannot override a harmful-mismatch or source-safety regression.

### 9.5 Champion–challenger deployment

- Keep one explicitly registered champion.
- Run challengers in shadow first, recording results without displaying them.
- Compare candidate recall, ranking changes, abstention, latency, and clinical-review samples.
- Canary to a small eligible traffic fraction with kill switches.
- Expand progressively only when automated and human-review gates pass.
- Retain the previous champion, configuration, and indexes for immediate rollback.
- Prevent users from being assigned to incompatible experiment variants within one session unless the experiment design explicitly requires it.

### 9.6 How new behavioral signals become a retraining candidate

New events should enter a controlled batch learning loop; the live model must not update directly from individual clicks.

```text
Requests + impressions + interactions
              |
              v
Schema validation, deduplication, bot filtering, delayed-event closure
              |
              v
Exposure-aware query-document event table
              |
              +--> behavioral grades/propensity diagnostics
              +--> clinician review sample and explicit feedback
              |
              v
Immutable time-bounded dataset snapshot
              |
              +--> intent-label dataset (reviewed labels only)
              `--> ranking dataset (behavior + clinical judgments)
              |
              v
Temporal/template-grouped train -> validation -> untouched test
              |
              v
Challenger training and calibration
              |
              v
Offline gates -> shadow -> canary -> controlled experiment
              |
              v
Promote or reject; retain champion and rollback artifacts
```

The workflow is:

1. **Close the observation window.** Wait long enough to capture delayed dwell, bookmark, and return events. Join every interaction to the exact rendered impression and serving versions. An exposed item with no recorded engagement can become a nonpositive behavioral observation; an unexposed item remains unjudged.
2. **Validate the event stream.** Remove duplicates and bots, reconcile producer/consumer counts, check missing IDs and timestamp order, and quarantine schema violations. Do not train if impression logging is incomplete because that changes the meaning of the labels.
3. **Construct graded behavioral evidence.** Preserve click, dwell, deep scroll, save, and return signals separately before deriving any grade. Estimate position/exposure propensity from controlled traffic where possible and retain the raw components for sensitivity analyses.
4. **Add stronger supervision.** Sample disagreements, new intents, low-confidence/OOD queries, corpus gaps, safety-critical slices, and large champion–challenger rank changes for blinded clinical review. Explicit doctor feedback is useful but should not bypass review for safety-critical decisions.
5. **Freeze a versioned snapshot.** Use an event-time cutoff, query/template grouping, data lineage, and content/model versions. Keep all future events out of training and preserve an untouched temporal confirmation period.
6. **Train components separately.** Intent retraining uses clinician-reviewed intent labels, not click-derived intent. A ranking challenger may use debiased behavioral evidence plus clinician judgments. Content index refreshes do not require ranking-model retraining. Encoder, NER, and slot changes are evaluated independently.
7. **Evaluate against the champion.** Primary release evidence is paired clinician-judged quality and harmful-mismatch performance. Behavioral NDCG, Recall, CTR, save rate, reformulation, calibration, latency, and slice metrics are secondary/supporting gates. Report judgment coverage and confidence intervals.
8. **Deploy progressively.** A passing challenger runs in shadow, then a small canary, then a preregistered experiment. Promotion changes a registry pointer; the old model and compatible indexes remain ready for rollback.

The cadence should be **data- and drift-triggered**, with a scheduled monthly review rather than automatic monthly retraining. A normal operating pattern is weekly data-quality aggregation, monthly model-health review, and quarterly retraining consideration. Retrain earlier for a taxonomy change, sustained drift, a new market/language, or a confirmed quality regression. Skip retraining when minimum data and slice-coverage gates are not met.

Behavioral feedback creates a closed-loop risk: the champion determines what is exposed, exposed items acquire labels, and a new model may learn to reproduce the champion. Countermeasures are pooled clinical judgments, small governed exploration, position-aware evaluation, candidate sources from multiple systems, explicit preservation of unjudged status, and a test set whose judgments are not derived only from champion exposure.

---

## 10. Monitoring and Alerting

### 10.1 Query-understanding monitoring

| Metric | Why it matters | Example investigation trigger |
| --- | --- | --- |
| Language distribution and confidence | Detect market/mix changes and detector failures | Sudden shift not explained by traffic source. |
| Intent distribution, confidence, entropy, OOD rate | Detect taxonomy/model drift | Sustained OOD or low-margin increase. |
| Entity coverage by type | Detect NER/dictionary regressions | Molecule/disease coverage drops after release. |
| Slot coverage by type | Detect extraction or query-mix shifts | Renal/pregnancy coverage changes unexpectedly. |
| Empty structured object rate | Measures fallback exposure | Exceeds historical band by language. |
| Contradictory/invalid values | Detect unit/parser bugs | Impossible age, dose, year, or renal values. |
| Extraction latency/error rate | Operational health | Breach of component SLO. |

Monitor distributions by language, client version, market, and model version. Compare against both a recent rolling baseline and a stable reference window.

### 10.2 Retrieval and ranking monitoring

- candidate count and empty-candidate rate by branch;
- candidate-union Recall@K on delayed judged data;
- overlap among sparse, dense, and structured candidates;
- score/rank distributions and normalization degeneracy;
- exact-entity and conjunction coverage in top K;
- direct/related/insufficient-evidence rates;
- zero-result and corpus-gap rates;
- duplicate-domain/content concentration;
- stale, expired, inaccessible, or retracted result rate;
- source and publication-date distributions;
- per-stage and end-to-end latency, timeouts, and fallback rate;
- online CTR, save rate, validated long-dwell rate, return visits, reformulation, abandonment;
- judged fraction and position/exposure propensity;
- delayed clinician-judged NDCG, Recall, usefulness, and harmful-mismatch rate.

An NDCG proxy computed from behavior should always be labeled as such and reported with judgment coverage.

### 10.3 Data quality monitoring

- producer/consumer event reconciliation;
- duplicate event and idempotency rate;
- missing request, query, content, impression, session, or version IDs;
- invalid event order and timestamp skew;
- schema compatibility and unknown enum values;
- content source freshness and ingest lag;
- document/passage count changes;
- orphaned passages or vectors;
- embedding dimension/norm drift;
- join coverage from impressions to interactions;
- bot/internal-traffic contamination;
- deletion/retraction propagation latency.

### 10.4 Fairness and safety monitoring

At minimum, slice quality by language, market, query length, intent, entity count, and contextual constraints. If demographic attributes are used, monitoring and retention require explicit governance. Pay special attention to pregnancy, pediatric, elderly, renal/hepatic, contraindication, interaction, and multi-drug queries.

Track:

- critical-constraint contradiction rate;
- wrong-molecule/wrong-disease rate in reviewed samples;
- multi-entity partial-match rate;
- low-confidence intent override rate;
- direct-match precision and abstention coverage;
- retracted/outdated evidence exposure;
- disparity in latency, abstention, and reviewed usefulness across languages/markets.

### 10.5 Alerting tiers

**Page immediately:** authorization leakage, retracted content being served, widespread 5xx errors, index corruption, model/index incompatibility, severe latency/availability breach, or a confirmed harmful-ranking regression.

**Same-business-day investigation:** event loss, source freshness breach, sharp fallback/OOD/zero-result changes, entity-coverage regression, or elevated constraint contradictions.

**Review in regular model-health meeting:** gradual distribution drift, slice deterioration without immediate harm, calibration decay, or cost increase.

Every alert needs an owner, dashboard, runbook, and clear close condition.

### 10.6 What monitoring looks like in practice

Monitoring should operate at three speeds rather than combine every signal into one dashboard.

**Real-time service dashboard (one- to five-minute windows)**

- request rate, 2xx/4xx/5xx, availability, and saturation;
- p50/p95/p99 end-to-end and per-stage latency;
- sparse, dense, entity, intent, metadata, and event-collector error/timeout rates;
- fallback path and partial-response rates;
- empty-candidate, zero-result, and `insufficient_evidence` rates;
- active model/config/index versions;
- retracted or unauthorized-content checks.

This dashboard supports on-call response. Alerts use burn-rate or sustained-window policies so a single noisy minute does not page unnecessarily, while authorization or retraction violations page immediately.

**Daily data and search-quality dashboard**

- request-to-impression-to-interaction join coverage;
- late, duplicate, missing, or invalid events;
- content/index freshness and document/vector count reconciliation;
- query language, intent, confidence, OOD, entity, and slot distributions;
- candidate counts/overlap by retrieval branch;
- direct/related/insufficient result mix;
- explicit entity/context conflict rates in top K;
- CTR, save, valid dwell, reformulation, abandonment, and judgment coverage by rank;
- slices by language, market, intent, client, and safety-critical constraint.

These metrics are compared with a rolling recent baseline, the same weekday/time window where seasonality matters, and the last known-good model version. Changes should be annotated with deployments, index refreshes, traffic campaigns, and content-source incidents.

**Weekly/monthly model-health review**

- delayed clinician-judged NDCG/Recall/usefulness and harmful-mismatch rate;
- intent accuracy/calibration and extraction precision/recall on newly reviewed samples;
- wrong-molecule/disease, partial multi-entity match, and critical-constraint contradiction rates;
- abstention precision, coverage, and successful recovery after query reformulation;
- champion–challenger paired differences and confidence intervals;
- drift by language, intent, entities, slots, source, and content age;
- data sufficiency for retraining and unresolved corpus gaps;
- latency/cost per search and index-build cost.

Every request trace should carry `request_id`, language/entity/slot/intent versions, branch latency and candidate counts, selected fallback, final policy tier, and model/index/config versions. Raw query text is not required in ordinary traces. This makes it possible to answer whether a quality change came from traffic mix, extraction, candidate generation, ranking, policy, content freshness, or instrumentation.

An alert should link directly to a runbook with: impact definition, likely causes, diagnostic queries, safe mitigations, rollback steps, owner, escalation path, and verification criteria. Quality alerts should automatically assemble a privacy-safe sample of affected request IDs for review rather than expose raw queries broadly.

---

## 11. Privacy, Security, and Clinical Safety

### 11.1 Data minimization

Doctor queries may contain patient details even if the UI discourages them. Apply defense in depth:

- display a product notice not to enter directly identifying patient information where appropriate;
- detect likely identifiers before analytics storage;
- separate operational search processing from analytics retention;
- pseudonymize user/session identifiers;
- encrypt in transit and at rest;
- restrict raw-query access and audit every access;
- define market-specific retention and deletion policies;
- use aggregated or redacted data for routine dashboards;
- never include raw queries in exception traces or general logs.

Applicable legal and clinical requirements must be confirmed with the organization’s privacy, security, regulatory, and medical-safety owners for each deployment market; this design is not a compliance determination.

### 11.2 Access control and supply chain

- Least-privilege service identities and role-based access for data, models, and dashboards.
- Tenant/content entitlement filters applied before ranking and rechecked at content fetch.
- Signed model/index artifacts with checksums and provenance.
- Dependency and container vulnerability scanning.
- Approved model and content licenses; S-PubMedBERT’s non-commercial license concern is one reason it is not a production default.
- Secrets in a managed secret store, never in notebooks or model manifests.
- Audit logs for model activation, configuration changes, reviewer label changes, and data exports.

### 11.3 Clinical safety presentation

- Clearly identify the system as search/retrieval support.
- Show source, date, review status, and evidence type.
- Label related evidence and incomplete matches.
- Avoid unsupported generated summaries in the first release.
- Provide a visible path to report incorrect, outdated, or unsafe results.
- Support rapid content suppression and incident response.
- Keep a medical-safety reviewer in the release and incident process.

---

## 12. Testing Strategy

### 12.1 Component tests

- normalization preserves drugs, units, numeric comparators, and negation;
- bilingual/mixed-language entity and slot fixtures;
- exact versus hierarchy match semantics;
- missing versus explicit conflict behavior;
- multi-molecule and comparison/interaction relationship coverage;
- stable score calculation and tie-breaking;
- confidence gating and intent abstention;
- event schema and idempotency;
- content permissions, retractions, and expiry.

### 12.2 Integration and contract tests

- query-understanding schema compatibility;
- encoder/index and ranker/feature compatibility;
- sparse/dense/structured candidate merge;
- complete version metadata in responses and events;
- fallback behavior under every component timeout;
- atomic index switch and rollback;
- end-to-end deletion and content-retraction propagation.

### 12.3 Golden-query regression suite

Maintain reviewed queries covering:

- exact entity queries;
- Indonesian and mixed-language phrasing;
- dosing with renal/hepatic constraints;
- pregnancy/pediatric/elderly safety;
- drug interactions and comparisons requiring both entities;
- treatment failure/escalation;
- latest guideline/year requirements;
- ambiguous abbreviations and low-confidence intent;
- no-answer/corpus-gap cases;
- the Phase 14 representative failures.

Golden tests should assert invariants and acceptable rank ranges rather than freeze every order forever. Clinically unsafe mismatches should be explicit negative fixtures.

### 12.4 Performance and resilience tests

- cold- and warm-start latency;
- expected and peak concurrency;
- index rebuild/load time;
- large/long/adversarial queries;
- dependency slowdown and partial outage;
- event-backlog recovery;
- region/zone failure where applicable;
- rollback under active load.

---

## 13. Deployment and Operations

### 13.1 Artifact packaging

Package together or explicitly declare compatibility among:

- normalizer and language detector;
- entity/terminology resources;
- contextual-slot extractor;
- intent preprocessing, model, taxonomy, and calibration;
- dense tokenizer/encoder;
- ranker weights and feature schema;
- evidence/abstention policy;
- sparse, dense, structured, and metadata index bundles.

Each artifact needs semantic version, content hash, build source, dependency lock, validation report, owner, and rollback target.

### 13.2 Release sequence

1. Reproduce the champion offline from immutable artifacts.
2. Validate compatibility and golden tests in staging.
3. Load the new bundle alongside the champion.
4. Run shadow traffic and compare outputs/latency.
5. Conduct targeted clinical review of changed and abstained queries.
6. Canary to a small traffic fraction.
7. Expand progressively with automated guardrails.
8. Declare the version active and retain prior artifacts.
9. Complete a post-release review and update the model card.

### 13.3 Ownership

| Area | Primary owner | Required partner |
| --- | --- | --- |
| Search API/platform | Search/backend engineering | SRE/security |
| Query understanding and ranker | Applied ML/NLP | Clinical reviewers/product |
| Content ingestion/index | Data/search engineering | Content governance |
| Events/experimentation | Data platform/analytics | Privacy/product |
| Clinical quality and incidents | Medical safety/content clinical owner | ML/product/legal as needed |
| Privacy/security/compliance | Designated governance teams | All system owners |

The on-call rotation needs runbooks for rollback, stale/retracted content, index mismatch, event loss, quality regression, and dependency failure.

---

## 14. Recommended Production Roadmap

### Stage 0 — Evaluation foundation

- Define clinical relevance and harmful-mismatch rubrics.
- Build blinded pooled judgments with qualified reviewers.
- Create aligned temporal/template-grouped splits for the full pipeline.
- Establish golden queries and corpus-gap labels.
- Measure the BM25 and frozen Phase 12 candidate fairly on full-text/passage evidence.

**Exit gate:** sufficient reviewed coverage to set clinical-quality and abstention thresholds.

### Stage 1 — Reliable offline content platform

- Ingest full text with provenance, dates, permissions, and retractions.
- Create canonical documents and clinically meaningful passages.
- Build immutable sparse, dense, structured, and metadata index bundles.
- Add artifact registry, compatibility checks, staging validation, and rollback.

**Exit gate:** reproducible builds, freshness SLO, and atomic activation proven.

### Stage 2 — Online baseline

- Serve normalization, language, NER, slots, and intent for arbitrary queries.
- Implement parallel candidate generation and deterministic Phase 12 ranking.
- Add confidence-gated intent, explicit fallbacks, result provenance, and traceable versions.
- Log privacy-reviewed requests, impressions, and interactions.

**Exit gate:** load/resilience/security tests and offline parity pass.

### Stage 3 — Safety and evidence controls

- Add relationship-aware multi-entity matching.
- Add value-aware clinical constraints and explicit-conflict semantics.
- Add evidence tiers, abstention, corpus-gap feedback, and rapid content suppression.
- Validate language and safety-critical slices.

**Exit gate:** harmful-mismatch and abstention targets pass clinician review.

### Stage 4 — Controlled launch

- Shadow traffic, then canary.
- Review changed, low-confidence, and insufficient-evidence cases.
- Run a preregistered online experiment with quality guardrails.
- Expand only with stable system, safety, and slice metrics.

### Stage 5 — Model improvements

Only after evaluation and candidate recall are strong:

- learn calibrated fusion weights;
- test language-gated or multilingual biomedical embeddings;
- fine-tune a query/document bi-encoder using reviewed positives and hard negatives;
- reconsider a lightweight or cross-encoder reranker;
- mine hard negatives that match disease and drug but violate one context constraint;
- evaluate joint intent/slot models and periodic representation learning.

Every extension remains a challenger until it passes the same gates. Higher capacity is not itself a reason to deploy.

---

## 15. Key Design Decisions and Trade-offs

| Decision | Rationale | Cost/trade-off |
| --- | --- | --- |
| Launch with deterministic Phase 12 ranking | Best-supported deployable assessment system; simple and debuggable | Additive scoring is limited and must be guarded for conjunctions. |
| No learned/cross-encoder reranker initially | Challengers did not improve reliably | Leaves potential semantic precision unrealized until labels improve. |
| Multilingual MiniLM over PubMedBERT replacement | Validation favored MiniLM; bilingual coverage and licensing are safer | Less biomedical specialization. |
| Passage/full-text index | Needed for clinical constraints absent from titles | Higher ingestion, storage, and attribution complexity. |
| Soft evidence plus explicit conflict | Preserves recall under incomplete metadata | Requires careful explanations and abstention. |
| Conjunction-aware direct-match policy | Prevents wrong-molecule/context-template failures | May increase abstention when the corpus is incomplete. |
| Confidence-gated intent | Avoids brittle low-margin hard decisions | Some intent benefit is intentionally forgone. |
| Behavior plus clinician judgments | Scales feedback while anchoring clinical validity | Clinical review is slower and more expensive. |
| Modular versioning and independent rollback | Limits blast radius and supports diagnosis | Operational and registry complexity. |

---
