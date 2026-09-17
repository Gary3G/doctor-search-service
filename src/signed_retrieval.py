"""Match bonuses and explicit mismatch penalties; missing evidence is neutral.

Run python -m src.signed_retrieval. Exploratory, validation-only weight selection.
"""
from __future__ import annotations
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.config import CONTENT_PATH, QUERIES_PATH, EXPERIMENT_LOG_PATH
from src.evaluation import evaluate_rankings, summarize_metrics
from src.evaluation_split import SPLIT_DIR
from src.incremental_retrieval import PHASE11_DIR, build_signals, rank_scores, paired_delta
from src.structured_compatibility import COMPATIBILITY_MATRIX_PATH, CONTENT_CONTEXT_PATH
from src.intent import INTENT_METADATA_QUERIES_PATH
from src.topic_boost_retrieval import table

OUTPUT = PHASE11_DIR.parent / 'signed_boost'
GRID = (0., .05, .2)
WEIGHTS = ('entity_bonus','entity_penalty','context_bonus','context_penalty')


def explicit_conflict(left, right):
    """Both sides must be populated, then non-equal, to incur a penalty."""
    left = left.replace(r'^\s*$', np.nan, regex=True)
    right = right.replace(r'^\s*$', np.nan, regex=True)
    # Compare only populated scalar pairs. This handles ``pd.NA`` safely and
    # preserves numeric equality such as 2025 == 2025.0.
    return pd.Series(
        [bool(a != b) if pd.notna(a) and pd.notna(b) else False for a, b in zip(left, right)],
        index=left.index,
        dtype=bool,
    )


def signed_scores(hybrid, signals, weights):
    if len(weights) != 4 or any(w < 0 for w in weights):
        raise ValueError('Expected four nonnegative weights')
    eb, ep, cb, cp = weights
    return hybrid + eb*signals['entity_bonus'] - ep*signals['entity_penalty'] + cb*signals['context_bonus'] - cp*signals['context_penalty']


def select(trials):
    return trials.assign(total=trials[list(WEIGHTS)].sum(axis=1)).sort_values(
        ['ndcg@10','total',*WEIGHTS],ascending=[False,True,True,True,True,True]).iloc[0]


def make_signals(base, pairs, shape):
    # Rebuild restricted conflicts, instead of using old year_conflict which
    # can treat absent publication_year as a conflict. Do not rewrite Phase 11.
    q = pd.read_csv(INTENT_METADATA_QUERIES_PATH).set_index('query_id')
    c = pd.read_csv(CONTENT_CONTEXT_PATH).set_index('content_id')
    conflicts = {}
    for name, qc, cc in [('age','age_group','content_age_group'),('route','route','content_route'),('year','year','publication_year')]:
        left = pairs.query_id.map(q[qc]); right = pairs.content_id.map(c[cc])
        if name == 'year':
            left = pd.to_numeric(left,errors='coerce'); right = pd.to_numeric(right,errors='coerce')
        conflicts[name] = explicit_conflict(left,right)
    denominator = pairs.context_constraint_count.replace(0,np.nan)
    penalty = (sum(v.astype(int) for v in conflicts.values()) / denominator).fillna(0.).to_numpy().reshape(shape)
    signals = {'entity_bonus':base['entities'], 'context_bonus':base['context'],
               'entity_penalty':pairs.entity_conflict_rate.to_numpy(float).reshape(shape), 'context_penalty':penalty}
    if any(not np.isfinite(s).all() for s in signals.values()):
        raise ValueError('Invalid signed feature')
    audit = [{'feature':k,'nonzero_pairs':int((v!=0).sum()),'mean':float(v.mean())} for k,v in signals.items()]
    audit += [{'feature':f'explicit_{k}_conflict','nonzero_pairs':int(v.sum()),'mean':float(v.mean())} for k,v in conflicts.items()]
    return signals,pd.DataFrame(audit)


def run(output_dir=OUTPUT):
    output_dir.mkdir(parents=True,exist_ok=True)
    queries=pd.read_csv(QUERIES_PATH).sort_values('query_id').reset_index(drop=True)
    content=pd.read_csv(CONTENT_PATH).sort_values('content_id').reset_index(drop=True)
    base,pairs,runtime,caches=build_signals(queries,content)
    hybrid=(base['bm25']+base['dense'])/2
    signals,audit=make_signals(base,pairs,hybrid.shape)
    complement_error=float(np.max(np.abs(signals['entity_bonus']+signals['entity_penalty']-1)))
    audit.to_csv(output_dir/'feature_audit.csv',index=False)
    validation_path=SPLIT_DIR/'temporal_validation_judgments.csv'
    validation=pd.read_csv(validation_path)
    rankings_cache={}
    def ranking(weights):
        weights=tuple(weights)
        if weights not in rankings_cache:
            rankings_cache[weights]=rank_scores(signed_scores(hybrid,signals,weights),queries.query_id,content.content_id)
        return rankings_cache[weights]
    trials=[]
    for weights in itertools.product(GRID,repeat=4):
        trials.append(dict(zip(WEIGHTS,weights)) | summarize_metrics(evaluate_rankings(ranking(weights),validation)))
    trials=pd.DataFrame(trials)
    trials.to_csv(output_dir/'validation_grid.csv',index=False)
    configs={'hybrid':(0.,0.,0.,0.)}
    families={'bonuses_only':trials[(trials.entity_penalty==0)&(trials.context_penalty==0)],
              'penalties_only':trials[(trials.entity_bonus==0)&(trials.context_bonus==0)],'both':trials}
    for name,frame in families.items():
        row=select(frame); configs[name]=tuple(float(row[w]) for w in WEIGHTS)
    for i,w in enumerate(WEIGHTS):
        reduced=list(configs['both']); reduced[i]=0.; configs['both_minus_'+w]=tuple(reduced)
    configs.update(fixed_bonuses=(.05,0.,.05,0.),fixed_penalties=(0.,.05,0.,.05),fixed_both=(.05,.05,.05,.05))
    pd.DataFrame([dict(experiment=n,**dict(zip(WEIGHTS,w))) for n,w in configs.items()]).to_csv(output_dir/'configurations.csv',index=False)
    rankings={n:ranking(w) for n,w in configs.items()}
    prior=pd.read_csv(PHASE11_DIR/'rankings.csv.gz')
    cols=['query_id','content_id','rank']
    pd.testing.assert_frame_equal(rankings['hybrid'][cols],prior[prior.experiment.eq('R-E4')][cols].reset_index(drop=True))
    pd.concat([r.assign(experiment=n) for n,r in rankings.items()],ignore_index=True).to_csv(output_dir/'rankings.csv.gz',index=False)
    inputs=[CONTENT_PATH,QUERIES_PATH,COMPATIBILITY_MATRIX_PATH,CONTENT_CONTEXT_PATH,INTENT_METADATA_QUERIES_PATH,*caches]
    metadata=pairs.groupby('query_id').first()[['query_language','query_intent','context_constraint_count']].reset_index()
    metadata['has_context']=metadata.context_constraint_count.gt(0)
    summaries=[]; details=[]; comparisons=[]; slices=[]
    for protocol in ('temporal','query','query_dedup'):
        for split in ('validation','test'):
            path=SPLIT_DIR/f'{protocol}_{split}_judgments.csv';inputs.append(path)
            judgments=pd.read_csv(path); primary={}
            for name,ranks in rankings.items():
                for scheme,threshold in [('relevance_grade',1),('conservative_relevance_grade',1),('event_hierarchy_relevance_grade',1),('relevance_grade',2)]:
                    tags=dict(protocol=protocol,split=split,experiment=name,scheme=scheme,threshold=threshold)
                    per=evaluate_rankings(ranks,judgments,scheme,threshold)
                    summaries.append(tags|summarize_metrics(per))
                    if scheme=='relevance_grade' and threshold==1:
                        primary[name]=per;details.append(per.assign(**tags))
                        enriched=per.merge(metadata,on='query_id',validate='one_to_one')
                        for dimension in ('query_language','query_intent','has_context'):
                            for value,group in enriched.groupby(dimension):
                                slices.append(tags|dict(dimension=dimension,value=value)|summarize_metrics(group))
            contrasts=[(n,'hybrid') for n in configs if n!='hybrid']+[(n,'both') for n in configs if n.startswith('both_minus_')]+[('fixed_both','fixed_bonuses')]
            for candidate,reference in contrasts:
                delta=paired_delta(primary[reference],primary[candidate])
                diff=primary[candidate].set_index('query_id')['ndcg@10']-primary[reference].set_index('query_id')['ndcg@10']
                comparisons.append(dict(protocol=protocol,split=split,candidate=candidate,reference=reference,delta_ndcg=delta['delta_vs_full'],lower=delta['lower'],upper=delta['upper'],positive_queries=delta['positive_queries'],improved=int((diff>0).sum()),worsened=int((diff<0).sum()),unchanged=int((diff==0).sum())))
    summary=pd.DataFrame(summaries); comparison=pd.DataFrame(comparisons)
    summary.to_csv(output_dir/'metrics.csv',index=False);comparison.to_csv(output_dir/'paired_comparisons.csv',index=False)
    pd.concat(details,ignore_index=True).to_csv(output_dir/'per_query_metrics.csv.gz',index=False)
    pd.DataFrame(slices).to_csv(output_dir/'slices.csv',index=False)
    manifest=dict(entity_complement_max_error=complement_error,formula='hybrid + entity_bonus*entity_coverage - entity_penalty*entity_conflict_rate + context_bonus*context_coverage - context_penalty*explicit_context_conflict_rate',grid=GRID,configurations=configs,
        selection='81 validation trials; temporal NDCG@10; ties prefer lowest sum then lexicographic weights',
        entity_conflict='both query/content dimension populated but no exact overlap; disease/molecule/class/area; divided by active query dimensions',
        context_conflict='only explicit age-group, route, year mismatch with both sides populated; divided by all active query context constraints',
        missing='zero contribution for either side missing; publication-year missing handling rebuilt locally',
        bonuses='unchanged Phase 11 coverage including coarse drug_profile/review proxies; no topic gate or intent',
        cautions=['metadata non-overlap is soft evidence, not proven clinical incompatibility','No pregnancy/renal/dosing/recency penalties; absent title evidence stays neutral','Exploratory after previous test inspection; no pristine holdout','Paired query bootstrap 2000 seed42; not cluster robust or multiple-comparison adjusted'],**runtime,
        sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs+[Path(__file__),Path('src/incremental_retrieval.py'),Path('src/structured_compatibility.py'),Path('src/evaluation.py'),SPLIT_DIR/'phase8_split_manifest.json']})
    (output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    primary=summary.query("protocol == 'temporal' and scheme == 'relevance_grade' and threshold == 1")
    view=primary.pivot(index='experiment',columns='split',values=['ndcg@10','recall@10','mrr@10']);view.columns=[' '.join(c) for c in view.columns]
    report='\n\n'.join(['# Match bonuses and explicit mismatch penalties',
        'Run `.venv/bin/python -m src.signed_retrieval`. This experiment tests hybrid, bonuses only, penalties only, and both. All 500 queries and 345 documents use the previous cached hybrid scores; baseline ordering is checked against R-E4.',
        manifest['formula'],
        'Entity penalties require populated metadata on both sides and no overlap for a dimension (disease, molecule, drug class, therapeutic area). Missing metadata contributes zero. These are soft mismatches: a document may remain useful despite different metadata. Any one entity overlap still satisfies its dimension; per-entity coverage is not introduced.',
        'Context penalties are restricted to explicit age-group, route and requested-year mismatch. Both sides must be present. The old publication-year conflict definition was not reused because it could penalize missing publication years. Context penalty count is divided by the existing total number of query constraints, avoiding disproportionate penalties for one comparable field. No penalties are applied for missing dosing, renal, pregnancy or other title wording.',
        'Bonuses preserve existing Phase 11 entity/context coverage, including content-type proxies, to isolate the penalty addition. No topic gating or intent score is used. Weight grid = {0, 0.05, 0.2} independently for four terms: 81 combinations. Select within each family by temporal-validation NDCG@10, breaking ties by smallest total then lexicographic weights. Controlled removals keep remaining selected weights fixed. Fixed 0.05 diagnostics ensure nonzero penalties are tested even when validation disables them.',
        table(pd.read_csv(output_dir/'configurations.csv')),table(view.reset_index().round(5)),
        '## What the experiment reveals',
        f'Entity match coverage plus entity conflict rate differs from 1 by at most {complement_error:.8f} across all pairs. When this is zero, subtracting p*(1-match) equals adding p*match minus a document-independent constant. Penalties-only and bonuses-only therefore provide the same entity ordering at equal weights; combining them increases the effective entity coefficient. Missing-neutral behavior still matters for future incomplete metadata, but it adds no new entity evidence in this dataset.',
        'Context conflicts are overwhelmingly requested-year mismatches; age and route conflicts are rare. Validation selected zero context penalty. The current result does not demonstrate that penalties improve retrieval. The combined selected configuration improves validation but decreases temporal-test NDCG; its paired interval against hybrid includes zero.',
        '## Feature audit',table(audit.round(5)),
        '## Paired test comparisons',
        'Delta=candidate minus reference. Paired 95% query-bootstrap intervals use 2,000 resamples, seed42; descriptive, not adjusted for model selection/multiplicity or query clustering.',
        table(comparison.query("protocol == 'temporal' and split == 'test'").drop(columns=['protocol','split']).round(5)),
        '## Limits',
        'This is exploratory after previous test inspection. Behavioral positives are sparse and may be off-topic; unjudged zero gain does not mean irrelevant. Missing-positive query metrics remain undefined. Validation-selected weights are never changed based on test results. Alternate grades and query/query_dedup protocols are sensitivity only. Metadata completeness, coarse age groups and incomplete titles limit mismatch interpretation. No clinical improvement is established by the proxy alone.',
        'Saved outputs include the full validation grid, configurations, rankings, per-query metrics, slices, grade sensitivities and input/code hashes. Codex assisted with implementation; this executable makes no LLM calls or new clinical judgments.'
    ])+'\n'
    # Narrative findings are consolidated in write_up/phase11_summary.md.
    log=pd.read_csv(EXPERIMENT_LOG_PATH)
    for name in ('bonuses_only','penalties_only','both'):
        experiment='R-SIGNED-'+name
        values=primary[primary.experiment.eq(name)].set_index('split')['ndcg@10']
        row=dict(experiment=experiment,hypothesis='explicit mismatch penalties improve hybrid with missing evidence neutral',method=str(dict(zip(WEIGHTS,configs[name]))),primary_metric='NDCG@10',result=f"Validation={values['validation']:.5f}; test={values['test']:.5f}",decision='exploratory validation-selected weights')
        log=pd.concat([log[~log.experiment.eq(experiment)],pd.DataFrame([row])],ignore_index=True)
    log.to_csv(EXPERIMENT_LOG_PATH,index=False)
    return {'output_dir':str(output_dir),'selected_both':configs['both']}


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
