"""Full-corpus ranking proxies with explicit incomplete-judgment coverage."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import CONFIG


def evaluate_rankings(rankings: pd.DataFrame, judgments: pd.DataFrame,
                      grade_column: str = 'relevance_grade', threshold: int = 1,
                      ks: tuple[int, ...] = CONFIG.top_k_values) -> pd.DataFrame:
    """Macro-ready per-query metrics; no-positive queries retain NaN metrics.

    Unjudged results get zero computational gain, without becoming negative labels.
    Threshold affects binary relevance and positive-metric eligibility; graded NDCG
    always retains the selected scheme's original gains.
    """
    if rankings.duplicated(['query_id', 'content_id']).any() or judgments.duplicated(['query_id', 'content_id']).any():
        raise ValueError('Duplicate query/content pairs')
    if judgments[grade_column].isna().any() or not judgments[grade_column].isin([0, 1, 2, 3]).all():
        raise ValueError('Expected relevance grades 0 through 3')
    rows = []
    ranked_groups = {q: g.sort_values('rank') for q, g in rankings.groupby('query_id')}
    for qid, group in judgments.groupby('query_id', sort=True):
        if qid not in ranked_groups:
            raise ValueError(f'Missing ranking for {qid}')
        ranked = ranked_groups[qid]
        if not np.array_equal(ranked['rank'], np.arange(1, len(ranked) + 1)):
            raise ValueError('Ranks must be consecutive starting at 1')
        if len(ranked) < max(ks):
            raise ValueError('Ranking shorter than requested cutoff')
        grades = dict(zip(group.content_id, group[grade_column]))
        positives = {cid for cid, grade in grades.items() if grade >= threshold}
        row = dict(query_id=qid, positive_pairs=len(positives), judged_pairs=len(grades), eligible=bool(positives))
        ideal = np.sort(np.array(list(grades.values())))[::-1]
        for k in ks:
            ids = ranked.content_id.iloc[:k].tolist()
            hits = np.array([cid in positives for cid in ids])
            row[f'judged_fraction@{k}'] = sum(cid in grades for cid in ids) / k
            row[f'recall@{k}'] = hits.sum() / len(positives) if positives else np.nan
            row[f'hit_rate@{k}'] = float(hits.any()) if positives else np.nan
            positions = np.flatnonzero(hits)
            row[f'mrr@{k}'] = (1 / (positions[0] + 1) if len(positions) else 0.) if positives else np.nan
            gains = np.array([2.**grades.get(cid, 0) - 1 for cid in ids])
            dcg = np.sum(gains / np.log2(np.arange(len(ids)) + 2))
            ideal_gains = 2.**ideal[:k] - 1
            idcg = np.sum(ideal_gains / np.log2(np.arange(len(ideal_gains)) + 2))
            row[f'ndcg@{k}'] = dcg / idcg if positives and idcg else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_metrics(per_query: pd.DataFrame) -> dict:
    result = dict(queries=len(per_query), positive_queries=int(per_query.eligible.sum()),
                  no_positive_queries=int((~per_query.eligible).sum()))
    for col in per_query.columns:
        if '@' in col:
            result[col] = per_query[col].mean()
    return result
