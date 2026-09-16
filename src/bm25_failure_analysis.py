"""Phase 10: reproducible validation sample plus explicitly authored case reviews.

Run with python -m src.bm25_failure_analysis. Does not tune or modify retrieval.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from src.bm25_baseline import BASELINE_DIR
from src.config import CONTENT_PATH, PROJECT_ROOT, CONFIG
from src.evaluation_split import SPLIT_DIR
from src.retrieval import BM25Retriever

REVIEW_DIR = BASELINE_DIR / 'failure_analysis'
NOTES_PATH = PROJECT_ROOT / 'data/processed/phase10_review_notes.csv'
CATEGORIES = (
    'lexical mismatch', 'synonym mismatch', 'abbreviation mismatch',
    'English-Indonesian mismatch', 'partial entity match',
    'wrong molecule within correct drug class', 'intent mismatch',
    'missing contextual constraint', 'age mismatch', 'temporal mismatch',
    'pregnancy mismatch', 'renal-function mismatch', 'severity mismatch',
    'weak behavioral ground truth',
)


def select_review_queries(metrics: pd.DataFrame) -> pd.DataFrame:
    """Fixed purposive quotas; sorted IDs make sampling independent of file order."""
    frame = metrics.query(
        "protocol == 'temporal' and split == 'validation' and "
        "scheme == 'relevance_grade' and threshold == 1"
    ).sort_values('query_id').copy()
    if frame.query_id.duplicated().any():
        raise ValueError('Duplicate validation metric rows')
    frame['stratum'] = 'miss'
    frame.loc[frame['recall@10'].gt(0), 'stratum'] = 'hit'
    frame.loc[frame.positive_pairs.eq(0), 'stratum'] = 'no_positive'
    groups = []
    for name, count in [('hit', 8), ('no_positive', 6), ('miss', 26)]:
        group = frame[frame.stratum.eq(name)]
        if len(group) < count:
            raise ValueError(f'Insufficient {name} queries for frozen review quota')
        groups.append(group.sample(n=count, random_state=CONFIG.random_seed))
    return pd.concat(groups).sort_values('query_id').reset_index(drop=True)


def build_phase10_artifacts(output_dir: Path = REVIEW_DIR) -> dict:
    paths = [BASELINE_DIR / 'bm25_per_query_metrics.csv', BASELINE_DIR / 'bm25_rankings.csv',
             SPLIT_DIR / 'temporal_validation_judgments.csv', PROJECT_ROOT / 'queries_labeled.csv',
             CONTENT_PATH, NOTES_PATH]
    metrics, rankings, judgments, queries, content, notes = [pd.read_csv(p) for p in paths]
    selected = select_review_queries(metrics)
    if notes.query_id.duplicated().any() or set(notes.query_id) != set(selected.query_id):
        raise ValueError('Authored reviews must cover exactly the frozen sample')
    selected = selected.merge(notes.fillna(''), on='query_id', validate='one_to_one')
    selected = selected.merge(queries, on='query_id', validate='one_to_one')
    retriever = BM25Retriever(content)
    docs = content.set_index('content_id')
    cases, pairs, lines = [], [], [
        '# Phase 10: BM25 case review', '',
        '40 temporal-validation queries: 26 misses, 8 hits and 6 without positive judgments. '
        'Seed 42 within each stratum; purposive quotas are not population prevalence estimates. '
        'Review is by Codex from titles and supplied metadata, not independent clinician adjudication. '
        'Behavioral positives are observed engagement, not expected clinically relevant answers. '
        'Context mismatch labels include missing title evidence, not necessarily contradiction. '
        'No model changes or test-set selection occur in this phase.', '',
    ]
    slots = ['age_group', 'pregnancy_status', 'year', 'recency_flag', 'dose_context_flag',
             'route', 'renal_function_group', 'hepatic_impairment_flag', 'comparison_flag',
             'negation_flag', 'prior_treatment_failure_flag']
    for _, row in selected.iterrows():
        qid = row.query_id
        full = retriever.search(row.query_text, len(content)).set_index('content_id')
        saved = rankings[rankings.query_id.eq(qid)].sort_values('rank')
        if saved.content_id.tolist() != full.head(len(saved)).index.tolist():
            raise ValueError('Saved baseline differs from current retrieval; refresh review')
        js = judgments[judgments.query_id.eq(qid)].set_index('content_id')
        positives = js[js.relevance_grade.gt(0)].sort_values(
            ['relevance_grade', 'content_id'], ascending=[False, True])
        categories = row.ranking_categories.split(';') if row.ranking_categories else []
        # This qualitative assessment is authored in the review notes, not inferred from grades.
        proxy_issue = row.proxy_issue
        if proxy_issue != 'broad same-disease positive; exact intent unverified':
            categories.append('weak behavioral ground truth')
        if not set(categories).issubset(CATEGORIES):
            raise ValueError('Unknown review category')
        decomposition = {k: row[k] for k in ['disease_entity', 'molecule_entity', 'drug_class_entity', 'intent'] + slots
                         if pd.notna(row[k]) and str(row[k]) not in ('False', '')}
        candidate = row.candidate_id
        record = dict(query_id=qid, query_text=row.query_text, language=row.language, stratum=row.stratum,
                      recall_at_10=row['recall@10'], ndcg_at_10=row['ndcg@10'],
                      judged_fraction_at_10=row['judged_fraction@10'], positive_pairs=int(row.positive_pairs),
                      decomposition=json.dumps(decomposition, ensure_ascii=False),
                      categories=';'.join(categories), proxy_issue=proxy_issue,
                      review_note=row.review_note, next_step=row.next_step, reviewer=row.reviewer,
                      candidate_id=candidate, candidate_rank=int(full.loc[candidate, 'rank']) if candidate else None,
                      candidate_status='plausible from title/metadata; not adjudicated relevant' if candidate else 'no specific alternative established')
        cases.append(record)
        lines += [f'## {qid}: {row.query_text}', '', f'**Stratum:** {row.stratum}. **Categories:** {record["categories"] or "none established"}.',
                  '', f'**Decomposition:** `{record["decomposition"]}`', '',
                  '| Role | Content | Rank | Grade | Title |', '| --- | --- | ---: | --- | --- |']
        roles = [(cid, 'retrieved top 3') for cid in saved.head(3).content_id]
        roles += [(cid, 'strongest observed positive') for cid in positives.head(2).index]
        roles += [(cid, 'observed top-10 hit') for cid in saved.head(10).content_id
                  if cid in positives.index]
        if candidate:
            roles.append((candidate, 'plausible inspection candidate'))
        for cid, role in roles:
            grade = int(js.loc[cid, 'relevance_grade']) if cid in js.index else 'unjudged'
            pair = dict(query_id=qid, role=role, content_id=cid, rank=int(full.loc[cid, 'rank']),
                        score=float(full.loc[cid, 'score']), grade=grade,
                        **docs.loc[cid].fillna('').to_dict())
            pairs.append(pair)
            lines.append(f'| {role} | {cid} | {pair["rank"]} | {grade} | {pair["title"]} |')
        lines += ['', row.review_note, '', f'**Behavioral evidence:** {proxy_issue}.', '',
                  f'**Next check:** {row.next_step}', '']
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = pd.DataFrame(cases)
    cases.to_csv(output_dir / 'review_cases.csv', index=False)
    pd.DataFrame(pairs).to_csv(output_dir / 'review_evidence.csv', index=False)
    counts = cases.categories.str.split(';').explode().value_counts()
    coverage = pd.DataFrame([dict(category=c, reviewed_query_count=int(counts.get(c, 0)),
                                 status='observed in this review' if counts.get(c, 0) else 'not established in this sample')
                             for c in CATEGORIES])
    coverage.to_csv(output_dir / 'category_coverage.csv', index=False)
    (output_dir / 'review_cases.md').write_text('\n'.join(lines))
    manifest = dict(phase=10, protocol='temporal', split='validation', seed=CONFIG.random_seed,
                    quotas={'miss': 26, 'hit': 8, 'no_positive': 6}, query_count=len(cases),
                    selection='fixed quotas; sample sorted query IDs with pandas random_state=42',
                    reviewer='Codex title/metadata review; not clinician gold',
                    limitations=['purposive sample', 'title-only content', 'weak behavioral evidence',
                                 'intent and slots are earlier pipeline outputs, not independent gold'],
                    versions={'pandas': pd.__version__},
                    sha256={str(p.relative_to(PROJECT_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in paths + [Path(__file__), Path(__file__).with_name('retrieval.py')]})
    (output_dir / 'phase10_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return {'cases': str(output_dir / 'review_cases.csv'), 'report': str(output_dir / 'review_cases.md'),
            'coverage': str(output_dir / 'category_coverage.csv')}


if __name__ == '__main__':
    print(json.dumps(build_phase10_artifacts(), indent=2))
