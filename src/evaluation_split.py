"""Phase 8: frozen retrieval partitions, built before pair aggregation."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import CONFIG, OUTPUT_DIR, BEHAVIORAL_SIGNALS_PATH
from src.relevance_labels import LABELED_EXPOSURES_PATH, aggregate_query_content_judgments

SPLIT_DIR = OUTPUT_DIR / 'evaluation'
PARTITIONS = ('train', 'validation', 'test')


NEAR_DUPLICATE_THRESHOLD = 0.95


def find_duplicate_pairs(exposures: pd.DataFrame) -> pd.DataFrame:
    """Conservative lexical families; never infer clinical equivalence.

    Normalize Unicode/case/whitespace, preserving digits and punctuation.
    Matching numeric tokens avoids grouping different years, doses, or ages.
    Features use query text only, never intent labels or behavioral outcomes.
    """
    queries = exposures[['query_id', 'query_text']].drop_duplicates().sort_values('query_id')
    if queries.query_id.duplicated().any() or queries.query_text.isna().any():
        raise ValueError('Each query ID must have exactly one nonmissing text')
    queries = queries.reset_index(drop=True)
    normalized = queries.query_text.map(lambda text: re.sub(
        r'\s+', ' ', unicodedata.normalize('NFKC', text).casefold()).strip())
    columns = ['query_id_left', 'query_id_right', 'text_left', 'text_right', 'similarity', 'match_type']
    if len(queries) < 2:
        return pd.DataFrame(columns=columns)
    if normalized.eq('').any():
        raise ValueError('Empty query text cannot define a duplicate family')
    vectors = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5)).fit_transform(normalized)
    similarities = cosine_similarity(vectors)
    pairs = []
    for i in range(len(queries)):
        for j in range(i + 1, len(queries)):
            exact = normalized[i] == normalized[j]
            same_numbers = re.findall(r'\d+(?:[.,]\d+)?', normalized[i]) == re.findall(r'\d+(?:[.,]\d+)?', normalized[j])
            if exact or (same_numbers and similarities[i, j] >= NEAR_DUPLICATE_THRESHOLD):
                pairs.append([queries.query_id[i], queries.query_id[j], queries.query_text[i],
                              queries.query_text[j], float(similarities[i, j]),
                              'normalized_exact' if exact else 'near_lexical'])
    return pd.DataFrame(pairs, columns=columns)


def assign_partitions(exposures: pd.DataFrame, strategy: str) -> tuple[pd.DataFrame, dict]:
    """Keep sessions intact; purge temporal sessions crossing either boundary.

    Temporal boundaries use session-start quantiles, without looking at outcomes.
    Session ends include recorded behavior, so late outcomes cannot enter training.
    """
    x = exposures.copy()
    for col in ('impression_id', 'session_id', 'query_id', 'doctor_id'):
        if x[col].isna().any():
            raise ValueError(f'Missing {col}')
    if x.impression_id.duplicated().any():
        raise ValueError('Duplicate impression IDs')
    starts = pd.to_datetime(x.timestamp, utc=True, errors='raise')
    ends = pd.concat([starts, pd.to_datetime(x.last_timestamp_served, utc=True),
                      pd.to_datetime(x.last_event_timestamp, utc=True)], axis=1).max(axis=1)
    sessions = pd.DataFrame({'session_id': x.session_id, 'start': starts, 'end': ends}).groupby('session_id').agg(start=('start', 'min'), end=('end', 'max'))
    meta = {'strategy': strategy, 'seed': CONFIG.random_seed}
    if strategy == 'temporal':
        ordered = sessions.start.sort_values()
        a = ordered.iloc[int(len(ordered) * (1-CONFIG.validation_size-CONFIG.test_size))]
        b = ordered.iloc[int(len(ordered) * (1-CONFIG.test_size))]
        if a >= b:
            raise ValueError('Insufficient distinct session start times')
        sessions['split'] = np.select(
            [sessions.end.lt(a), sessions.start.ge(a) & sessions.end.lt(b), sessions.start.ge(b)],
            PARTITIONS, default='purged')
        x['split'] = x.session_id.map(sessions.split)
        meta.update(validation_start=a.isoformat(), test_start=b.isoformat())
    elif strategy in ('query', 'query_dedup'):
        # Connected components prevent multi-query sessions from bridging splits.
        parent = {q: q for q in sorted(x.query_id.unique())}
        def root(q):
            while parent[q] != q:
                parent[q] = parent[parent[q]]
                q = parent[q]
            return q
        for _, group in x.groupby('session_id'):
            qs = sorted(group.query_id.unique())
            for q in qs[1:]:
                parent[root(q)] = root(qs[0])
        if strategy == 'query_dedup':
            pairs = find_duplicate_pairs(x)
            for pair in pairs.itertuples():
                parent[root(pair.query_id_right)] = root(pair.query_id_left)
            meta.update(near_duplicate_threshold=NEAR_DUPLICATE_THRESHOLD,
                        duplicate_pairs=len(pairs), method='char_wb TF-IDF 3-5 grams; identical numeric tokens')
        x['query_group'] = x.query_id.map(root)
        groups = sorted({root(q) for q in parent})
        np.random.default_rng(CONFIG.random_seed).shuffle(groups)
        a = int(len(groups)*(1-CONFIG.validation_size-CONFIG.test_size))
        b = int(len(groups)*(1-CONFIG.test_size))
        mapping = {q: ('train' if i<a else 'validation' if i<b else 'test') for i,q in enumerate(groups)}
        x['split'] = x.query_id.map(lambda q: mapping[root(q)])
        meta['query_session_components'] = len(groups)
    else:
        raise ValueError(f'Unknown split strategy: {strategy}')
    if x.groupby('session_id').split.nunique().max() != 1:
        raise AssertionError('Session leakage')
    if set(PARTITIONS) - set(x.split):
        raise ValueError('Empty evaluation partition')
    return x, meta


def build_phase8_artifacts(output_dir: Path = SPLIT_DIR) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    exposures = pd.read_csv(LABELED_EXPOSURES_PATH)
    summaries, overlaps, manifest = [], [], {}
    duplicate_pairs = find_duplicate_pairs(exposures)
    duplicate_pairs.to_csv(output_dir / 'phase8_duplicate_pairs.csv', index=False)
    duplicate_audits = []
    for strategy in ('temporal', 'query', 'query_dedup'):
        assigned, meta = assign_partitions(exposures, strategy)
        assigned[['impression_id', 'query_id', 'content_id', 'session_id', 'doctor_id', 'timestamp', 'first_event_timestamp', 'last_event_timestamp', 'split']].to_csv(output_dir / f'{strategy}_exposure_assignments.csv', index=False)
        if strategy == 'query_dedup':
            assigned[['query_id', 'query_text', 'query_group', 'split']].drop_duplicates().sort_values('query_id').to_csv(
                output_dir / 'query_dedup_query_groups.csv', index=False)
        memberships = assigned.groupby('query_id').split.agg(set)
        for pair in duplicate_pairs.itertuples():
            left, right = memberships[pair.query_id_left], memberships[pair.query_id_right]
            crosses = any(a != b for a in left for b in right if a in PARTITIONS and b in PARTITIONS)
            duplicate_audits.append(dict(strategy=strategy, query_id_left=pair.query_id_left,
                                         query_id_right=pair.query_id_right, crosses_partitions=crosses))
            if strategy == 'query_dedup' and crosses:
                raise AssertionError('Near-duplicate leakage')
        events = pd.read_csv(BEHAVIORAL_SIGNALS_PATH)
        event_assignment = events.merge(assigned[['query_id', 'content_id', 'session_id', 'split']],
            on=['query_id', 'content_id', 'session_id'], how='left', validate='many_to_one')
        if event_assignment.split.isna().any() or event_assignment.signal_id.duplicated().any():
            raise AssertionError('Unassigned or duplicated behavioral event')
        event_assignment[['signal_id', 'session_id', 'event_timestamp', 'split']].to_csv(
            output_dir / f'{strategy}_event_assignments.csv', index=False)
        meta['assigned_behavioral_events'] = len(event_assignment)
        for split in (*PARTITIONS, 'purged'):
            subset = assigned.loc[assigned.split.eq(split)]
            if subset.empty:
                continue
            judgments = aggregate_query_content_judgments(subset)
            judgments.to_csv(output_dir / f'{strategy}_{split}_judgments.csv', index=False)
            coverage = judgments.groupby('query_id').agg(judged_pairs=('content_id','size'), positive_pairs=('relevance_grade',lambda s: int(s.gt(0).sum())))
            coverage['eligible_positive_metrics'] = coverage.positive_pairs.gt(0)
            coverage.to_csv(output_dir / f'{strategy}_{split}_query_coverage.csv')
            summaries.append(dict(strategy=strategy, split=split, exposures=len(subset), engagements=int(subset.has_engagement.sum()), sessions=subset.session_id.nunique(), doctors=subset.doctor_id.nunique(), queries=len(coverage), judged_pairs=len(judgments), positive_queries=int(coverage.eligible_positive_metrics.sum()), no_positive_queries=int((~coverage.eligible_positive_metrics).sum()), first_impression=subset.timestamp.min(), last_impression=subset.timestamp.max()))
        for i, left in enumerate(PARTITIONS):
            for right in PARTITIONS[i+1:]:
                row = dict(strategy=strategy, left=left, right=right)
                for field in ('impression_id', 'session_id', 'query_id', 'doctor_id', 'content_id'):
                    row[field] = len(set(assigned.loc[assigned.split.eq(left),field]) & set(assigned.loc[assigned.split.eq(right),field]))
                assert row['impression_id'] == row['session_id'] == 0
                if strategy in ('query', 'query_dedup'):
                    assert row['query_id'] == 0
                overlaps.append(row)
        manifest[strategy] = meta
    pd.DataFrame(duplicate_audits, columns=['strategy', 'query_id_left', 'query_id_right', 'crosses_partitions']).to_csv(output_dir / 'phase8_duplicate_overlap_audit.csv', index=False)
    summary = pd.DataFrame(summaries)
    summary.to_csv(output_dir / 'phase8_split_summary.csv', index=False)
    pd.DataFrame(overlaps).to_csv(output_dir / 'phase8_overlap_audit.csv', index=False)
    manifest['source_sha256'] = hashlib.sha256(LABELED_EXPOSURES_PATH.read_bytes()).hexdigest()
    manifest['config'] = {'validation_size': CONFIG.validation_size, 'test_size': CONFIG.test_size}
    manifest['primary_protocol'] = 'temporal'
    manifest['preferred_query_generalization_protocol'] = 'query_dedup'
    (output_dir / 'phase8_split_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return {'summary': str(output_dir / 'phase8_split_summary.csv'), 'manifest': str(output_dir / 'phase8_split_manifest.json')}


if __name__ == '__main__':
    print(json.dumps(build_phase8_artifacts(), indent=2))
