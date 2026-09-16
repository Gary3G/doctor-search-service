"""Run phase 9: python -m src.bm25_baseline."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import CONFIG, CONTENT_PATH, QUERIES_PATH, OUTPUT_DIR, EXPERIMENT_LOG_PATH
from src.evaluation_split import SPLIT_DIR, PARTITIONS
from src.evaluation import evaluate_rankings, summarize_metrics
from src.retrieval import BM25Retriever

BASELINE_DIR = OUTPUT_DIR / 'retrieval'
SCHEMES = ('relevance_grade', 'conservative_relevance_grade', 'event_hierarchy_relevance_grade')


def build_phase9_artifacts(output_dir: Path = BASELINE_DIR) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    content, queries = pd.read_csv(CONTENT_PATH), pd.read_csv(QUERIES_PATH)
    rankings = BM25Retriever(content).rank_queries(queries, max(CONFIG.top_k_values))
    rankings.to_csv(output_dir / 'bm25_rankings.csv', index=False)
    inputs = [CONTENT_PATH, QUERIES_PATH, SPLIT_DIR / 'phase8_split_manifest.json']
    summaries, details, slices, intervals = [], [], [], []
    for protocol in ('temporal', 'query', 'query_dedup'):
        for split in PARTITIONS:
            path = SPLIT_DIR / f'{protocol}_{split}_judgments.csv'
            inputs.append(path)
            judgments = pd.read_csv(path)
            if not set(judgments.content_id).issubset(set(content.content_id)):
                raise ValueError('Judged document missing from corpus')
            for scheme in SCHEMES:
                for threshold in (1, 2):
                    tags = dict(protocol=protocol, split=split, scheme=scheme, threshold=threshold)
                    metrics = evaluate_rankings(rankings, judgments, scheme, threshold)
                    summaries.append({**tags, **summarize_metrics(metrics)})
                    details.append(metrics.assign(**tags))
                    if scheme == 'relevance_grade' and threshold == 1:
                        # Query bootstrap is descriptive; repeated doctors/sessions and
                        # query families mean this is not a cluster-robust interval.
                        rng = np.random.default_rng(CONFIG.random_seed)
                        for metric in ('recall@5', 'recall@10', 'mrr@10', 'ndcg@10'):
                            values = metrics[metric].dropna().to_numpy()
                            means = rng.choice(values, (2000, len(values)), replace=True).mean(axis=1)
                            lo, hi = np.quantile(means, [.025, .975])
                            intervals.append({**tags, 'metric': metric, 'lower': lo, 'upper': hi, 'queries': len(values)})
                        metadata = judgments[['query_id', 'query_language', 'query_intent']].drop_duplicates('query_id')
                        enriched = metrics.merge(metadata, on='query_id', validate='one_to_one')
                        for dimension in ('query_language', 'query_intent'):
                            for value, group in enriched.groupby(dimension, dropna=False):
                                slices.append({**tags, 'dimension': dimension, 'value': value, **summarize_metrics(group)})
    summary = pd.DataFrame(summaries)
    summary.to_csv(output_dir / 'bm25_metrics.csv', index=False)
    pd.concat(details, ignore_index=True).to_csv(output_dir / 'bm25_per_query_metrics.csv', index=False)
    pd.DataFrame(slices).to_csv(output_dir / 'bm25_slices.csv', index=False)
    pd.DataFrame(intervals).to_csv(output_dir / 'bm25_bootstrap_intervals.csv', index=False)
    manifest = dict(method='BM25Okapi', representation='title only; body/summary absent',
        k1=CONFIG.bm25_k1, b=CONFIG.bm25_b, epsilon=0.25,
        tokenizer='NFKC + casefold + Unicode word tokens; no stopwords/stemming/translation',
        tie_break='ascending content_id', corpus_size=len(content), query_count=len(queries),
        tuning='none; existing project defaults frozen before evaluation',
        top_k=list(CONFIG.top_k_values), unjudged='zero gain for proxy computation only',
        eligibility='positive queries per scheme and binary threshold; graded gains unchanged',
        bootstrap='2000 query resamples; seed 42; descriptive, not cluster robust',
        versions={p: importlib.metadata.version(p) for p in ('rank-bm25', 'numpy', 'pandas')},
        sha256={str(p.relative_to(CONTENT_PATH.parents[2])): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in inputs + [Path(__file__), Path(__file__).with_name('retrieval.py'), Path(__file__).with_name('evaluation.py')]})
    (output_dir / 'bm25_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    primary = summary.query("protocol == 'temporal' and split == 'test' and scheme == 'relevance_grade' and threshold == 1").iloc[0]
    log = pd.read_csv(EXPERIMENT_LOG_PATH)
    log.loc[log.experiment.eq('R-B0'), 'result'] = f"Temporal test NDCG@10={primary['ndcg@10']:.4f}; Recall@10={primary['recall@10']:.4f}; {int(primary.positive_queries)}/{int(primary.queries)} positive queries"
    log.loc[log.experiment.eq('R-B0'), 'decision'] = 'retain fixed title-only baseline; incomplete behavioral proxy'
    log.to_csv(EXPERIMENT_LOG_PATH, index=False)
    return {'metrics': str(output_dir / 'bm25_metrics.csv'), 'rankings': str(output_dir / 'bm25_rankings.csv')}


if __name__ == '__main__':
    print(json.dumps(build_phase9_artifacts(), indent=2))
