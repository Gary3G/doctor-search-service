# Doctor Search Service

A research pipeline for understanding doctors' clinical search queries and ranking medical content. The project combines multilingual query understanding, intent classification, behavior-derived relevance labels, lexical and semantic retrieval, structured clinical matching, and offline evaluation.

> This repository is an assessment and experimentation pipeline, not a production API. Its relevance labels are inferred from logged behavior rather than clinician judgments, and its current corpus contains titles and metadata rather than full article text.

## What the project does

Given an English, Bahasa Indonesia, or mixed-language medical query, the pipeline:

1. normalizes the query and extracts clinical context such as age group, pregnancy, year, dosing, route, renal/hepatic constraints, comparison, negation, and prior treatment failure;
2. predicts the doctor's information need using an 11-class intent taxonomy;
3. generates candidates with BM25 and frozen multilingual embeddings;
4. measures disease, molecule, drug-class, therapeutic-area, and contextual compatibility;
5. reranks candidates with a deterministic hybrid score and predicted intent; and
6. evaluates results with graded behavioral relevance, multiple data splits, slice analysis, and qualitative failure review.

The selected runtime-oriented ranker is:

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

The dense component uses `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. More complex learned and cross-encoder rerankers were evaluated but were not selected because their validation gains did not transfer reliably to the temporal test set.

## System design

```text
Raw query
   |
   v
Normalization and language handling
   |
   v
Query understanding
   |-- supplied clinical entities (disease, ICD-10, molecule, ATC, drug class)
   |-- extracted contextual slots
   `-- predicted intent
   |
   v
Candidate generation
   |-- title-only BM25
   `-- frozen multilingual dense retrieval
   |
   v
Entity/context compatibility + intent/content-type compatibility
   |
   v
Deterministic hybrid ranking
   |
   v
Top-K results, evaluation, and failure analysis
```

## Step-by-step project phases

| Phase | Purpose | Main output |
| --- | --- | --- |
| 0 | Set up a deterministic environment and experiment log. | Configuration, dependencies, experiment registry |
| 1 | Audit queries, content, impressions, and behavioral events for quality, coverage, language, duplication, and bias. | Data-quality reports and review samples |
| 1.5–1.6 | Define and extract clinical context that is missing from the supplied entity columns. | Enriched query table with contextual slots |
| 2 | Adapt a literature-seeded medical intent taxonomy to the observed query distribution using lexical, semantic, clustered, and structured evidence. | Final 11-intent taxonomy |
| 3 | Label a reviewed subset and all remaining queries with a combined rule, prototype, and cluster strategy. | `queries_labeled.csv` and intent metadata |
| 4–5 | Train a TF-IDF baseline, then compare semantic and structured intent classifiers under row- and template-grouped evaluation. | Selected T1-E4 intent classifier |
| 6 | Join impressions and engagement events into a query-content behavioral table. | Exposure-level behavioral dataset |
| 7 | Convert behavior into transparent grades from 0–3, retaining conservative sensitivity variants. | Query-content relevance judgments |
| 7.5 | Calculate behavior-independent entity and context compatibility for every query-content pair. | Structured compatibility features |
| 8 | Freeze temporal, query-held-out, and duplicate-aware evaluation protocols and audit overlap. | Reproducible train/validation/test assignments |
| 9 | Establish a fixed title-only BM25 baseline. | Baseline rankings and metrics |
| 10 | Review representative BM25 misses and separate ranking failures from weak-label failures. | Failure categories and evidence tables |
| 11 | Add dense, entity, context, and assisted-intent signals incrementally and run ablations. | Eight core retrieval configurations |
| 12 | Replace assisted intent with predictions from the saved runtime intent classifier. | Selected predicted-hard-intent ranker |
| 13 | Measure behavior by language, entity complexity, contextual complexity, and intent slices. | Slice metrics and bootstrap comparisons |
| 14 | Review residual errors such as conjunction failures, wrong-molecule matches, corpus gaps, and proxy-label failures. | Final qualitative failure analysis |
| 15–16 | Compare a learned logistic reranker, multilingual and biomedical cross-encoders, and PubMedBERT embeddings. | Model-selection decision: keep Phase 12 |
| 17 | Translate the experiment into a production design with versioned indexes, fallbacks, logging, monitoring, and safety constraints. | Production architecture proposal |

In short, the working design moves from **data audit → structured query understanding → weak supervision → fixed evaluation → incremental retrieval → failure analysis → production planning**. Each phase freezes its artifacts before the next phase adds complexity, making the contribution of every signal auditable.

## Data

Place the four input files in `data/raw/`:

| File | Expected contents |
| --- | --- |
| `queries.csv` | Query text, language, supplied disease/molecule/drug-class entities, ICD-10/ATC codes, and therapeutic area |
| `content.csv` | Content title and type, source, language, publication metadata, and clinical entities |
| `impressions.csv` | Which content was served for each query/session and when |
| `behavioral_signals.csv` | Click, scroll, bookmark, return, dwell-time, and related engagement events |

The included assessment data contains 500 queries, 345 content items, 7,190 impressions, and 1,500 behavioral events.

## Quick start

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest
```

Run the test suite:

```bash
python -m pytest
```

Start Jupyter from the repository root and open `notebook.ipynb`:

```bash
jupyter notebook notebook.ipynb
```

The notebook is the main guided entry point. Its `RUN_PIPELINE` flag controls whether deterministic artifacts are rebuilt. Expensive optional model-selection challengers are disabled by default and can be enabled with `RUN_MODEL_SELECTION_CHALLENGERS`.

### Rebuild the core downstream phases

After the checked-in query-taxonomy and intent-label artifacts are available, the principal executable stages can also be run directly:

```bash
python -m src.intent_improved
python -m src.relevance
python -m src.relevance_labels
python -m src.structured_compatibility
python -m src.evaluation_split
python -m src.bm25_baseline
python -m src.bm25_failure_analysis
python -m src.incremental_retrieval
python -m src.intent_retrieval
python -m src.slice_evaluation
python -m src.final_failure_analysis
python -m src.learned_reranker
```

Some phases consume artifacts produced by earlier phases, so run these commands in order. Transformer-backed stages download model weights on the first uncached run. The saved Phase 5 intent model was produced with scikit-learn 1.5.2; use that version to retrain it exactly, or reuse the checked-in model when running with a newer compatible environment.

Optional Phase 16 challengers are intentionally separate because they are slower and were not selected:

```bash
python -m src.cross_encoder_reranker
python -m src.medcpt_reranker
python -m src.pubmedbert_embedding_experiment
```

## Repository layout

```text
doctor-search-service/
|-- data/
|   |-- raw/                 # Four source datasets
|   |-- processed/           # Derived tables and saved review annotations
|   `-- cache/               # Embeddings and model-score caches
|-- experiments/
|   `-- experiment_log.csv   # Hypotheses, metrics, results, and decisions
|-- outputs/
|   |-- evaluation/          # Frozen split assignments and leakage audits
|   |-- figures/             # Diagnostic plots
|   |-- intent/              # Intent labeling artifacts
|   |-- metrics/             # Intent model metrics and reports
|   |-- retrieval/           # Rankings, metrics, ablations, and manifests
|   `-- taxonomy/            # Intent taxonomy evidence and decisions
|-- src/                     # Reusable pipeline and experiment modules
|-- tests/                   # Unit and integration tests
|-- write_up/                # Short report for each completed phase
|-- notebook.ipynb           # End-to-end reviewer-facing workflow
`-- requirements.txt
```

## Evaluation and results

The primary ranking metric is NDCG@10, supported by Recall@K, hit rate, MRR, judgment coverage, paired bootstrap comparisons, and diagnostic slices. The main protocol uses chronological session assignments; query-held-out and near-duplicate-aware variants are retained as sensitivity checks.

The selected Phase 12 runtime ranker achieved temporal validation/test NDCG@10 of **0.03146 / 0.01851**. These small absolute values must be read in context:

- only exposed query-content pairs have behavioral judgments;
- unjudged results receive zero computational gain but are not known negatives;
- engagement is affected by exposure and position bias;
- roughly three percent of returned top-10 items are judged; and
- titles alone often omit the clinical evidence needed for constrained questions.

Accordingly, the results support a comparative experimental conclusion, not a claim of clinical readiness. The next high-value step is clinician-adjudicated pooled relevance data over full-text or section-level content.

## Reproducibility

- Randomness is fixed with seed `42` in `src/config.py`.
- Retrieval ties are broken deterministically by `content_id`.
- Each major retrieval experiment writes a manifest with configuration and input/code fingerprints.
- Model selection uses validation data; reported temporal-test results are descriptive because the test set was inspected during iterative analysis.
- `experiments/experiment_log.csv` records each hypothesis, primary metric, result, and decision.

## Safety and scope

This project retrieves source material for healthcare professionals. It does not diagnose, prescribe, or replace clinical judgment. A production version should expose provenance and publication date, enforce document permissions and retraction status, detect insufficient evidence, protect sensitive query logs, and be evaluated by qualified clinical reviewers before release.
