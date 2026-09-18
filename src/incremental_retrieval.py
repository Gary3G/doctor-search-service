"""Phase 11: fixed-weight CPU retrieval experiments and removal ablations.

Run with python -m src.incremental_retrieval. No relevance labels enter scores.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import CACHE_DIR, CONFIG, CONTENT_PATH, QUERIES_PATH, OUTPUT_DIR, EXPERIMENT_LOG_PATH
from src.evaluation import evaluate_rankings, summarize_metrics
from src.evaluation_split import SPLIT_DIR
from src.retrieval import BM25Retriever, tokenize
from src.structured_compatibility import COMPATIBILITY_MATRIX_PATH
from src.taxonomy import encode_texts

PHASE11_DIR = OUTPUT_DIR / 'retrieval' / 'phase11'
# Equal weights are fixed before evaluation, not optimized against weak labels.
EXPERIMENTS = {
    'R-B0': ('bm25',),
    'R-E1': ('bm25', 'entities'),
    'R-E2': ('bm25', 'entities', 'context'),
    'R-E3': ('dense',),
    'R-E4': ('bm25', 'dense'),
    'R-E5': ('bm25', 'dense', 'entities'),
    'R-E6': ('bm25', 'dense', 'entities', 'context'),
    'R-E7': ('bm25', 'dense', 'entities', 'context', 'intent'),
}


def normalize_bm25(scores: np.ndarray) -> np.ndarray:
    low = scores.min(axis=1, keepdims=True)
    span = scores.max(axis=1, keepdims=True) - low
    return np.divide(scores - low, span, out=np.zeros_like(scores), where=span != 0)


def rank_scores(scores: np.ndarray, query_ids, content_ids, k=20) -> pd.DataFrame:
    """Rank a complete finite matrix with content-ID ties independent of input order."""
    scores = np.asarray(scores)
    if scores.shape != (len(query_ids), len(content_ids)) or not np.isfinite(scores).all():
        raise ValueError('Expected finite query-by-content score matrix')
    if len(set(query_ids)) != len(query_ids) or len(set(content_ids)) != len(content_ids):
        raise ValueError('IDs must be unique')
    if not 1 <= k <= len(content_ids):
        raise ValueError('Invalid cutoff')
    ids = np.asarray(content_ids)
    rows = []
    for qid, values in zip(query_ids, scores):
        order = np.lexsort((ids, -values))[:k]
        rows.extend((qid, ids[i], rank, float(values[i])) for rank, i in enumerate(order, 1))
    return pd.DataFrame(rows, columns=['query_id', 'content_id', 'rank', 'score'])


def combine(signals: dict, components: tuple) -> np.ndarray:
    return np.mean([signals[name] for name in components], axis=0)


def build_signals(queries, content):
    retriever = BM25Retriever(content)
    raw = np.vstack([retriever.index.get_scores(tokenize(q)) for q in queries.query_text])
    # A cached local encoder suffices: avoid mutable remote resolution on reruns.
    os.environ.setdefault('HF_HUB_OFFLINE', '1')
    qcache = CACHE_DIR / 'phase11_query_embeddings.npz'
    ccache = CACHE_DIR / 'phase11_content_embeddings.npz'
    start = time.perf_counter()
    qvec = encode_texts(queries.query_text.tolist(), qcache)
    cvec = encode_texts(content.title.fillna('').tolist(), ccache)
    seconds = time.perf_counter() - start
    pairs = pd.read_csv(COMPATIBILITY_MATRIX_PATH)
    if pairs.duplicated(['query_id', 'content_id']).any():
        raise ValueError('Duplicate compatibility pairs')
    index = pd.MultiIndex.from_product([queries.query_id, content.content_id], names=['query_id', 'content_id'])
    pairs = pairs.set_index(['query_id', 'content_id']).reindex(index)
    def matrix(column):
        values = pairs[column].to_numpy(dtype=float).reshape(raw.shape)
        if not np.isfinite(values).all():
            raise ValueError(f'Missing or invalid compatibility: {column}')
        return values
    signals = {'bm25': normalize_bm25(raw), 'dense': np.clip((qvec @ cvec.T + 1) / 2, 0, 1),
               'entities': matrix('entity_coverage'), 'context': matrix('context_coverage'),
               'intent': matrix('intent_content_type_match')}
    return signals, pairs.reset_index(), {'embedding_seconds_including_cache_load': seconds,
                                         'embedding_dimensions': qvec.shape[1]}, [qcache, ccache]


def paired_delta(full, other):
    joined = full[['query_id', 'ndcg@10']].merge(other[['query_id', 'ndcg@10']], on='query_id', suffixes=('_full', '_other'), validate='one_to_one')
    delta = (joined['ndcg@10_other'] - joined['ndcg@10_full']).dropna().to_numpy()
    if not len(delta):
        return dict(delta_vs_full=np.nan, lower=np.nan, upper=np.nan, positive_queries=0)
    rng = np.random.default_rng(CONFIG.random_seed)
    interval = np.quantile(rng.choice(delta, (2000, len(delta)), replace=True).mean(axis=1), [.025, .975])
    return dict(delta_vs_full=float(delta.mean()), lower=float(interval[0]), upper=float(interval[1]), positive_queries=len(delta))


def build_phase11_artifacts(output_dir: Path = PHASE11_DIR):
    output_dir.mkdir(parents=True, exist_ok=True)
    queries = pd.read_csv(QUERIES_PATH).sort_values('query_id').reset_index(drop=True)
    content = pd.read_csv(CONTENT_PATH).sort_values('content_id').reset_index(drop=True)
    signals, pairs, runtime, caches = build_signals(queries, content)
    def ranking(components):
        return rank_scores(combine(signals, components), queries.query_id, content.content_id)
    rankings = {name: ranking(parts) for name, parts in EXPERIMENTS.items()}
    # Validate baseline parity before interpreting any new experiments.
    baseline = pd.read_csv(OUTPUT_DIR / 'retrieval' / 'bm25_rankings.csv')
    pd.testing.assert_frame_equal(rankings['R-B0'][['query_id', 'content_id', 'rank']].reset_index(drop=True),
                                  baseline[['query_id', 'content_id', 'rank']].reset_index(drop=True))
    validation_path = SPLIT_DIR / 'temporal_validation_judgments.csv'
    validation = pd.read_csv(validation_path)
    selection = pd.DataFrame([dict(experiment=name, components=len(EXPERIMENTS[name]),
        **summarize_metrics(evaluate_rankings(ranks, validation))) for name, ranks in rankings.items()])
    selection = selection.sort_values(['ndcg@10', 'components', 'experiment'], ascending=[False, True, True])
    selected = selection.iloc[0].experiment
    selection.to_csv(output_dir / 'validation_selection.csv', index=False)
    # Complete five-signal system removal isolates every signal even if a simpler
    # configuration wins validation. Also ablate the selected system explicitly.
    configs = dict(EXPERIMENTS)
    for name, parts in [('full', EXPERIMENTS['R-E7']), ('selected', EXPERIMENTS[selected])]:
        configs[f'{name}:complete'] = parts
        for component in parts:
            if len(parts) > 1:
                configs[f'{name}:minus_{component}'] = tuple(p for p in parts if p != component)
    for name, parts in configs.items():
        if name not in rankings:
            rankings[name] = ranking(parts)
    pd.concat([r.assign(experiment=n) for n, r in rankings.items()], ignore_index=True).to_csv(output_dir / 'rankings.csv.gz', index=False)
    summaries, details, slices, ablations, inputs = [], [], [], [], [CONTENT_PATH, QUERIES_PATH, COMPATIBILITY_MATRIX_PATH, *caches]
    metadata = pairs.groupby('query_id', sort=True).first()[['query_language', 'query_intent', 'context_constraint_count', 'entity_query_count']].reset_index()
    metadata['has_context'] = metadata.context_constraint_count.gt(0)
    metadata['multiple_entity_dimensions'] = metadata.entity_query_count.gt(1)
    for protocol in ('temporal', 'query', 'query_dedup'):
        for split in ('validation', 'test'):
            path = SPLIT_DIR / f'{protocol}_{split}_judgments.csv'
            inputs.append(path)
            judgments = pd.read_csv(path)
            primary = {}
            for name, ranks in rankings.items():
                for scheme, threshold in [('relevance_grade', 1), ('conservative_relevance_grade', 1), ('event_hierarchy_relevance_grade', 1), ('relevance_grade', 2)]:
                    tags = dict(protocol=protocol, split=split, experiment=name, scheme=scheme, threshold=threshold)
                    per_query = evaluate_rankings(ranks, judgments, scheme, threshold)
                    summaries.append({**tags, **summarize_metrics(per_query)})
                    if scheme == 'relevance_grade' and threshold == 1:
                        primary[name] = per_query
                        details.append(per_query.assign(**tags))
                        enriched = per_query.merge(metadata, on='query_id', validate='one_to_one')
                        for dimension in ('query_language', 'query_intent', 'has_context', 'multiple_entity_dimensions'):
                            for value, group in enriched.groupby(dimension, dropna=False):
                                slices.append({**tags, 'dimension': dimension, 'value': value, **summarize_metrics(group)})
            for family in ('full', 'selected'):
                full = primary[f'{family}:complete']
                for name, metrics in primary.items():
                    if name.startswith(family + ':'):
                        ablations.append(dict(protocol=protocol, split=split, experiment=name, **paired_delta(full, metrics), ndcg_at_10=metrics['ndcg@10'].mean()))
    summary = pd.DataFrame(summaries)
    summary.to_csv(output_dir / 'metrics.csv', index=False)
    pd.concat(details, ignore_index=True).to_csv(output_dir / 'per_query_metrics.csv.gz', index=False)
    pd.DataFrame(slices).to_csv(output_dir / 'slices.csv', index=False)
    pd.DataFrame(ablations).to_csv(output_dir / 'ablations.csv', index=False)
    manifest = dict(selected_on_temporal_validation=selected, configurations=configs, weights='equal mean of included components; fixed before metrics',
        signals={'bm25': 'per-query full-corpus min-max; constant row zero', 'dense': '(frozen cosine + 1)/2',
                 'entities': 'Phase 7.5 entity_coverage: disease/molecule/class/area', 'context': 'Phase 7.5 context_coverage; missing evidence contributes zero, no conflict penalty',
                 'intent': 'Phase 7.5 intent/content-type rule prior; existing assisted query labels, not a new out-of-fold deployment classifier'},
        model=CONFIG.semantic_model_name, device='cpu', encoder_training=False, representation='raw query and content title only',
        tie_break='ascending content_id', queries=len(queries), content_items=len(content), **runtime,
        caveats=['Incomplete and noisy behavioral proxies; unjudged zero computational gain is not a negative label',
                 'Existing test inspected in earlier phases: descriptive confirmation, not pristine holdout',
                 'Temporal repeats queries; query and query_dedup protocols are sensitivity only, never selection',
                 'Intent prior inherits assisted labels and coarse content types; Phase 12 must test predicted/oracle intent separately',
                 'Ablation intervals: paired query bootstrap, 2000 resamples, seed 42; not cluster robust or multiplicity corrected'],
        sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs + [Path(__file__), Path('src/evaluation.py'), Path('src/retrieval.py'), Path('src/structured_compatibility.py'), Path('src/taxonomy.py'), SPLIT_DIR / 'phase8_split_manifest.json']})
    (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    log = pd.read_csv(EXPERIMENT_LOG_PATH)
    for name, components in EXPERIMENTS.items():
        if name == 'R-B0':
            continue
        val = selection.set_index('experiment').loc[name]
        test = summary.query("protocol == 'temporal' and split == 'test' and scheme == 'relevance_grade' and threshold == 1").set_index('experiment').loc[name]
        row = dict(experiment=name, hypothesis='measure incremental contribution of ' + components[-1], method=' + '.join(components), primary_metric='NDCG@10',
                   result=f"Temporal validation={val['ndcg@10']:.4f}; test={test['ndcg@10']:.4f}",
                   decision='selected on temporal validation; descriptive proxy' if name == selected else 'retain as ablation; not selected')
        log = log[~log.experiment.eq(name)]
        log = pd.concat([log, pd.DataFrame([row])], ignore_index=True)
    log.to_csv(EXPERIMENT_LOG_PATH, index=False)
    write_report(output_dir)
    return {'selected': selected, 'output_dir': str(output_dir), **runtime}


def write_report(output_dir):
    summary = pd.read_csv(output_dir / 'metrics.csv')
    manifest = json.loads((output_dir / 'manifest.json').read_text())
    slices = pd.read_csv(output_dir / 'slices.csv')
    keys = ['protocol', 'split', 'dimension', 'value']
    full = slices[slices.experiment.eq('full:complete')][keys + ['ndcg@10']].rename(columns={'ndcg@10': 'full_ndcg@10'})
    removed = slices[slices.experiment.str.startswith('full:minus_')].merge(full, on=keys, validate='many_to_one')
    removed['delta_vs_full'] = removed['ndcg@10'] - removed['full_ndcg@10']
    removed.to_csv(output_dir / 'ablation_slices.csv', index=False)
    primary = summary[(summary.scheme == 'relevance_grade') & (summary.threshold == 1) & summary.experiment.isin(EXPERIMENTS)]
    table = primary[primary.protocol.eq('temporal')].pivot(index='experiment', columns='split', values=['ndcg@10', 'recall@10'])
    def md(frame):
        headers = [str(c) for c in frame.columns]
        return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] + ['| ' + ' | '.join(str(v) for v in row) + ' |' for row in frame.itertuples(index=False, name=None)])
    table.columns = [' '.join(c) for c in table.columns]
    ablations = pd.read_csv(output_dir / 'ablations.csv')
    view = ablations[(ablations.protocol == 'temporal') & ablations.experiment.str.startswith('full:')]
    affected = removed[(removed.protocol == 'temporal') & (removed.split == 'test') & (removed.positive_queries >= 10)].copy()
    affected['absolute_delta'] = affected.delta_vs_full.abs()
    affected = affected.sort_values('absolute_delta', ascending=False).groupby('experiment', sort=False).head(2)
    text = '\n\n'.join([
        '# Phase 11 — Incremental Retrieval Experiments',
        'Run `.venv/bin/python -m src.incremental_retrieval`. All eight planned configurations were executed on CPU over all 500 queries and 345 content titles. The frozen multilingual MiniLM encoder is reused from the local model cache; query and title vectors are cached with model/text fingerprints. No encoder or reranker training was performed.',
        '## Method',
        'Each included component has equal weight, fixed before evaluation: per-query min-max BM25, shifted cosine similarity, supplied entity coverage, contextual coverage, and the existing intent/content-type compatibility prior. Full-corpus scoring avoids candidate-recall confounding. Ties use ascending content ID. Entity coverage combines disease, molecule, drug class and therapeutic area; ICD/ATC hierarchy expansion is not a separate new experiment. Context includes age, year, renal and other available Phase 7.5 fields. Missing title evidence adds no score; no hard exclusions or conflict penalties are applied. These coarse matches do not establish exact eGFR/dose compatibility.',
        'Validation selects among eight fixed configurations by NDCG@10; ties favor fewer components then experiment ID. Removal ablations hold remaining component ratios fixed, without retuning. The five-signal full system and the validation-selected system are both ablated. Query-held-out and deduplicated protocols are sensitivity checks using the same frozen choices.',
        f"Selected on temporal validation: **{manifest['selected_on_temporal_validation']}**. Dense encoding/cache load took {manifest['embedding_seconds_including_cache_load']:.2f} seconds for this recorded run.",
        md(table.reset_index().round(5)),
        '## Removal ablations',
        'Delta is removed-system NDCG@10 minus full-system NDCG@10: negative means removal hurts. Intervals are paired query-bootstrap 95% intervals (2,000 resamples, seed 42), descriptive and neither cluster-robust nor corrected for multiple comparisons.',
        md(view[['split', 'experiment', 'ndcg_at_10', 'delta_vs_full', 'lower', 'upper', 'positive_queries']].round(5)),
        '## Most affected test slices',
        'Largest absolute changes per removal among slices with at least 10 positive queries; selected post hoc for description. Both gains and losses are shown. Language, assisted intent, context presence and multiple populated entity dimensions are available in the complete slice tables.',
        md(affected[['experiment', 'dimension', 'value', 'positive_queries', 'ndcg@10', 'delta_vs_full']].round(5)),
        '## Interpretation and limits',
        'R-E7 leads the eight planned configurations. Diagnostic removals of BM25 or dense similarity score slightly higher on validation; these post-selection ablations are not promoted into a second model-selection round. Removing dense also slightly improves test NDCG, so semantic similarity has not demonstrated incremental value within the full combination. Removing intent reduces test NDCG, particularly for dosing and mixed-language slices, but this coarse assisted-label prior requires separate validation.',
        'Validation gains do not establish clinical relevance or production benefit. Behavioral positives are sparse and Phase 10 found many apparently off-topic positives; unjudged pairs receive zero gain only for metric computation. Queries with no positives keep undefined relevance metrics and explicit coverage counts. Conservative and event-hierarchy grades plus grade>=2 binary sensitivity are reported in metrics.csv. Prior phases already inspected test data, so these are descriptive results, not a pristine holdout claim.',
        'The intent signal uses existing assisted query labels and a broad content-type prior. It is not a separately validated online classifier or an oracle-versus-predicted intent experiment. Phase 12 should isolate that distinction. Body text is unavailable, and context/content-type heuristics are imperfect. Do not infer that low proxy scores prove plausible clinical results irrelevant.',
        'Implementation and interpretation were LLM-assisted. This phase makes no LLM calls, creates no relevance labels, and uses no behavioral features in ranking. No learned reranker was added: the fixed-component experiment directly tests marginal signal contributions.',
        'Artifacts: metrics.csv (all protocols/schemes), validation_selection.csv, rankings.csv.gz, per_query_metrics.csv.gz, ablations.csv, slices.csv, ablation_slices.csv and manifest.json (configuration, provenance and hashes). The notebook contains executable Phase 11 cells; the experiment log follows the Phase 11 R-E5/R-E6/R-E7 definitions, replacing the earlier placeholder R-E5 intent entry.'
    ]) + '\n'
    # Phase 11 has one curated narrative at write_up/phase11_summary.md.
    # Keep experiment runners machine-readable so reruns cannot overwrite it.


if __name__ == '__main__':
    print(json.dumps(build_phase11_artifacts(), indent=2))
