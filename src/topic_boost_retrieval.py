"""Phase 11 follow-up: modest entity and topic-gated context boosts.

Run python -m src.topic_boost_retrieval. Weights selected exclusively on temporal
validation; this is exploratory following inspection of earlier test results.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.config import CONTENT_PATH, QUERIES_PATH, EXPERIMENT_LOG_PATH
from src.evaluation import evaluate_rankings, summarize_metrics
from src.evaluation_split import SPLIT_DIR
from src.incremental_retrieval import PHASE11_DIR, build_signals, rank_scores, paired_delta
from src.structured_compatibility import COMPATIBILITY_MATRIX_PATH

OUTPUT = PHASE11_DIR.parent / 'topic_boost'
GRID = (0., .025, .05, .1, .2)


def topic_gate(pairs, shape):
    """Exact disease OR molecule overlap; broad class/area alone is insufficient.

    This is dimension-level overlap, not full coverage of every named entity.
    No supplied disease/molecule evidence leaves the gate closed.
    """
    columns = pairs[['disease_match', 'molecule_match']]
    if columns.isna().any().any():
        raise ValueError('Missing topic evidence')
    return columns.astype(bool).any(axis=1).to_numpy().reshape(shape).astype(float)


def boosted_scores(hybrid, entities, context, gate, alpha, beta):
    if alpha < 0 or beta < 0:
        raise ValueError('Boost weights must be nonnegative')
    return hybrid + alpha * entities + beta * gate * context


def choose_weights(trials):
    """Prefer less boosting on exact validation ties; never receive test metrics."""
    return trials.assign(total=trials.alpha + trials.beta).sort_values(
        ['ndcg@10', 'total', 'alpha', 'beta'], ascending=[False, True, True, True]).iloc[0]


def table(frame):
    return '\n'.join(['| ' + ' | '.join(map(str, frame.columns)) + ' |',
                      '| ' + ' | '.join(['---'] * len(frame.columns)) + ' |'] +
                     ['| ' + ' | '.join(map(str, row)) + ' |' for row in frame.itertuples(index=False, name=None)])


def run(output_dir=OUTPUT):
    output_dir.mkdir(parents=True, exist_ok=True)
    queries = pd.read_csv(QUERIES_PATH).sort_values('query_id').reset_index(drop=True)
    content = pd.read_csv(CONTENT_PATH).sort_values('content_id').reset_index(drop=True)
    signals, pairs, runtime, caches = build_signals(queries, content)
    hybrid = (signals['bm25'] + signals['dense']) / 2
    gate = topic_gate(pairs, hybrid.shape)
    validation_path = SPLIT_DIR / 'temporal_validation_judgments.csv'
    validation = pd.read_csv(validation_path)
    cached_rankings = {}
    def ranking(alpha, beta, gated):
        key = (float(alpha), float(beta), bool(gated))
        if key not in cached_rankings:
            score = boosted_scores(hybrid, signals['entities'], signals['context'], gate if gated else np.ones_like(gate), alpha, beta)
            cached_rankings[key] = rank_scores(score, queries.query_id, content.content_id)
        return cached_rankings[key]
    trials = []
    for gated in (False, True):
        for alpha in GRID:
            for beta in GRID:
                metrics = evaluate_rankings(ranking(alpha, beta, gated), validation)
                trials.append(dict(gated=gated, alpha=alpha, beta=beta, **summarize_metrics(metrics)))
    trials = pd.DataFrame(trials)
    trials.to_csv(output_dir / 'validation_grid.csv', index=False)
    configs = {'hybrid': (0., 0., True)}
    families = {
        'entity_only': trials[(trials.beta == 0) & trials.gated],
        'gated_context_only': trials[(trials.alpha == 0) & trials.gated],
        'ungated_context_only': trials[(trials.alpha == 0) & ~trials.gated],
        'joint_gated': trials[trials.gated],
        'joint_ungated': trials[~trials.gated],
    }
    for name, candidates in families.items():
        row = choose_weights(candidates)
        configs[name] = (float(row.alpha), float(row.beta), bool(row.gated))
    alpha, beta, _ = configs['joint_gated']
    # Controlled removals keep the joint-selected weights fixed.
    configs.update({'joint_minus_entities': (0., beta, True),
                    'joint_minus_context': (alpha, 0., True),
                    'joint_remove_gate': (alpha, beta, False)})
    # A predeclared nonzero diagnostic still tests gating when validation chooses zero.
    configs.update({'fixed_entity_010': (.1, 0., True),
                    'fixed_joint_gated_010': (.1, .1, True),
                    'fixed_joint_ungated_010': (.1, .1, False)})
    pd.DataFrame([dict(experiment=n, alpha=a, beta=b, gated=g) for n, (a,b,g) in configs.items()]).to_csv(output_dir / 'configurations.csv', index=False)
    rankings = {n: ranking(*config) for n, config in configs.items()}
    previous = pd.read_csv(PHASE11_DIR / 'rankings.csv.gz')
    old_hybrid = previous[previous.experiment.eq('R-E4')][['query_id','content_id','rank']].reset_index(drop=True)
    pd.testing.assert_frame_equal(rankings['hybrid'][old_hybrid.columns], old_hybrid)
    pd.concat([r.assign(experiment=n) for n,r in rankings.items()],ignore_index=True).to_csv(output_dir / 'rankings.csv.gz', index=False)
    summaries, details, comparisons, slices = [], [], [], []
    inputs = [CONTENT_PATH, QUERIES_PATH, COMPATIBILITY_MATRIX_PATH, *caches, validation_path]
    metadata = pairs.groupby('query_id').first()[['query_language','query_intent','context_constraint_count']].reset_index()
    metadata['has_context'] = metadata.context_constraint_count.gt(0)
    for protocol in ('temporal','query','query_dedup'):
        for split in ('validation','test'):
            path = SPLIT_DIR / f'{protocol}_{split}_judgments.csv'
            inputs.append(path)
            judgments = pd.read_csv(path)
            primary = {}
            for name, ranks in rankings.items():
                for scheme, threshold in [('relevance_grade',1),('conservative_relevance_grade',1),('event_hierarchy_relevance_grade',1),('relevance_grade',2)]:
                    per = evaluate_rankings(ranks, judgments, scheme, threshold)
                    tags = dict(protocol=protocol, split=split, experiment=name, scheme=scheme, threshold=threshold)
                    summaries.append({**tags, **summarize_metrics(per)})
                    if scheme == 'relevance_grade' and threshold == 1:
                        primary[name] = per
                        details.append(per.assign(**tags))
                        enriched = per.merge(metadata, on='query_id',validate='one_to_one')
                        for dimension in ('query_language','query_intent','has_context'):
                            for value, group in enriched.groupby(dimension):
                                slices.append({**tags,'dimension':dimension,'value':value,**summarize_metrics(group)})
            contrasts = [(n,'hybrid') for n in configs if n!='hybrid'] + [(n,'joint_gated') for n in ('joint_minus_entities','joint_minus_context','joint_remove_gate')] + [('fixed_joint_gated_010','fixed_joint_ungated_010')]
            for candidate, reference in contrasts:
                delta = paired_delta(primary[reference], primary[candidate])
                aligned = primary[candidate].set_index('query_id')['ndcg@10'] - primary[reference].set_index('query_id')['ndcg@10']
                comparisons.append(dict(protocol=protocol,split=split,candidate=candidate,reference=reference,
                    delta_ndcg=delta['delta_vs_full'],lower=delta['lower'],upper=delta['upper'],
                    improved=int((aligned>0).sum()),worsened=int((aligned<0).sum()),unchanged=int((aligned==0).sum()),positive_queries=delta['positive_queries']))
    # Metric equality can hide changed unjudged results; record top-10 churn.
    churn = []
    for candidate, reference in [('joint_gated','hybrid'), ('fixed_joint_gated_010','fixed_entity_010'), ('fixed_joint_gated_010','fixed_joint_ungated_010')]:
        left = rankings[candidate].query('rank <= 10').groupby('query_id').content_id.agg(tuple)
        right = rankings[reference].query('rank <= 10').groupby('query_id').content_id.agg(tuple)
        churn.append(dict(candidate=candidate, reference=reference, all_query_order_changes=int((left != right).sum()),
                          all_query_membership_changes=sum(set(a)!=set(b) for a,b in zip(left,right))))
    pd.DataFrame(churn).to_csv(output_dir/'ranking_changes.csv',index=False)
    summary = pd.DataFrame(summaries)
    comparison = pd.DataFrame(comparisons)
    summary.to_csv(output_dir/'metrics.csv',index=False)
    comparison.to_csv(output_dir/'paired_comparisons.csv',index=False)
    pd.concat(details,ignore_index=True).to_csv(output_dir/'per_query_metrics.csv.gz',index=False)
    pd.DataFrame(slices).to_csv(output_dir/'slices.csv',index=False)
    manifest = dict(formula='mean(normalized BM25, shifted dense cosine) + alpha*entity_coverage + beta*topic_gate*context_coverage',
        grid=GRID, configs=configs, selection='temporal validation NDCG@10; ties prefer lower total boost, alpha, beta',
        topic_gate='exact disease OR molecule overlap; any one entity suffices; missing evidence=closed; class/area insufficient',
        feature_changes='none; existing context heuristics retained to isolate weighting/gating; no intent boost',
        diagnostic='fixed 0.1 entity and context weights specified before run; not selected on test',
        limitations=['Exploratory follow-up motivated by inspected test results; no pristine holdout',
            'Weak behavioral labels and coarse metadata; no clinical relevance claim',
            'Multiple validation trials and post-selection intervals; paired query bootstrap not cluster-robust'],
        gate_pairs=int(gate.sum()),context_pairs_before=int((signals['context']>0).sum()),
        context_pairs_after=int(((signals['context']>0)&(gate>0)).sum()),**runtime,
        sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs+[Path(__file__),Path('src/incremental_retrieval.py'),Path('src/evaluation.py'), SPLIT_DIR/'phase8_split_manifest.json']})
    (output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    primary = summary.query("protocol == 'temporal' and scheme == 'relevance_grade' and threshold == 1")
    view = primary.pivot(index='experiment', columns='split', values=['ndcg@10','recall@10'])
    view.columns=[' '.join(c) for c in view.columns]
    report = '\n\n'.join(['# Modest boosts and topic-conditioned context',
        'Run `.venv/bin/python -m src.topic_boost_retrieval`. This follow-up preserves the Phase 11 hybrid and structured features, changing only boost strength and topic gating. No new embeddings, intent signal, or model training are needed.',
        '`score = hybrid + alpha × entity_coverage + beta × topic_gate × context_coverage`. Hybrid is the mean of normalized BM25 and shifted dense cosine. Gate=1 when an exact supplied disease OR molecule match exists; drug-class/area overlap alone is insufficient. This permissive gate does not guarantee all query entities match.',
        'Weights are selected from 0, 0.025, 0.05, 0.1, 0.2 using only temporal-validation NDCG@10. Ties prefer the smallest total boost, then alpha, then beta. Entity-only, context-only and joint families are selected separately. Joint removals keep its chosen weights unchanged; fixed 0.1 diagnostics isolate gating even if selection disables context.',
        table(pd.read_csv(output_dir/'configurations.csv')),
        table(view.reset_index().round(5)),
        '## Interpretation',
        f"Validation chose alpha={alpha:g}, beta={beta:g} for the gated joint family. Zero beta means there is no selected context contribution to attribute to gating. Selection is kept fixed despite test results; the fixed-weight comparisons are diagnostics, not a test-selected replacement.",
        'The paired table below should determine whether gains are distinguishable from zero. Equal NDCG does not imply identical rankings: unjudged documents can move without affecting the proxy. Ranking churn across all 500 queries is recorded separately:',
        table(pd.DataFrame(churn)),
        '## Paired temporal-test comparisons',
        'Delta=candidate minus reference. Bootstrap 95% intervals use 2,000 paired query resamples, seed 42; these are descriptive, not selection/multiplicity-adjusted or cluster-robust.',
        table(comparison.query("protocol == 'temporal' and split == 'test'").drop(columns=['protocol','split']).round(5)),
        f"Topic gating retains {manifest['context_pairs_after']:,} of {manifest['context_pairs_before']:,} pairs with a positive context score. Missing topic evidence closes the gate but never excludes a document from retrieval.",
        '## Limits',
        'This experiment was motivated by earlier test inspection, so all confirmation is exploratory. Sparse, sometimes off-topic behavioral positives can reward clinically questionable results. No-positive queries retain undefined relevance metrics. Context retains the original dosing/drug-profile and comparison/review heuristics; exact numeric renal compatibility is not established. Separating explicit context from metadata proxies remains future work. Query/query_dedup and alternate-grade results are sensitivity checks, never used to choose weights. No claim of clinical improvement follows from these proxy metrics.',
        'Codex assisted with code and interpretation; the executable makes no LLM calls or new judgments. Full rankings, validation grid, metrics, per-query deltas, slices and provenance are saved beside this report.'
    ])+'\n'
    # Narrative findings are consolidated in write_up/phase11_summary.md.
    log = pd.read_csv(EXPERIMENT_LOG_PATH)
    for name in ('entity_only','joint_gated','joint_ungated'):
        experiment='R-TB-'+name
        values=primary[primary.experiment.eq(name)].set_index('split')['ndcg@10']
        row=dict(experiment=experiment,hypothesis='modest boosts and topic gating improve hybrid proxy ranking',method=str(configs[name]),primary_metric='NDCG@10',result=f"Validation={values['validation']:.5f}; test={values['test']:.5f}",decision='exploratory validation-selected configuration; no clean holdout')
        log=pd.concat([log[~log.experiment.eq(experiment)],pd.DataFrame([row])],ignore_index=True)
    log.to_csv(EXPERIMENT_LOG_PATH,index=False)
    return {'output_dir':str(output_dir),'joint_gated':configs['joint_gated']}


if __name__ == '__main__':
    print(json.dumps(run(),indent=2))
