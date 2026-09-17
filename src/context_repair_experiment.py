"""Controlled evaluation of evidence-audit repairs; no weight retuning."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.config import CONTENT_PATH, QUERIES_PATH, EXPERIMENT_LOG_PATH
from src.intent import INTENT_METADATA_QUERIES_PATH
from src.query_extraction import extract_slots as legacy_extractor
from src.query_extraction_v2 import extract_slots as repaired_extractor
from src.structured_compatibility import build_compatibility_matrix, prepare_content_context, COMPATIBILITY_MATRIX_PATH
from src.incremental_retrieval import build_signals, rank_scores, paired_delta, PHASE11_DIR
from src.evaluation_split import SPLIT_DIR
from src.evaluation import evaluate_rankings, summarize_metrics
from src.topic_boost_retrieval import table

OUTPUT=PHASE11_DIR.parent/'context_repair'


def run(output_dir=OUTPUT):
    output_dir.mkdir(parents=True,exist_ok=True)
    queries=pd.read_csv(INTENT_METADATA_QUERIES_PATH).sort_values('query_id').reset_index(drop=True)
    content=pd.read_csv(CONTENT_PATH).sort_values('content_id').reset_index(drop=True)
    base,pairs,runtime,caches=build_signals(queries,content)
    hybrid=(base['bm25']+base['dense'])/2
    variants={'legacy':(legacy_extractor,'legacy'), 'cue_repairs':(repaired_extractor,'legacy'),
              'explicit_only':(legacy_extractor,'explicit'), 'repaired_explicit':(repaired_extractor,'explicit')}
    rankings={};summaries=[];details=[];comparisons=[];slices=[];changes=[];context_audit=[]
    # Every score family keeps its original coefficients; only context varies.
    score_families={
        'BM25_E_C':lambda context:(base['bm25']+base['entities']+context)/3,
        'H_E_C':lambda context:(base['bm25']+base['dense']+base['entities']+context)/4,
        'H_E_C_I':lambda context:(base['bm25']+base['dense']+base['entities']+context+base['intent'])/5,
        'H_modest_E_C':lambda context:hybrid+.1*base['entities']+.1*context,
    }
    for variant,(extractor,policy) in variants.items():
        updated=queries.copy()
        qslots=pd.DataFrame([extractor(t).__dict__ for t in queries.query_text])
        for col in qslots:updated[col]=qslots[col]
        prepared=prepare_content_context(content,slot_extractor=extractor,context_mode=policy)
        if variant=='legacy':
            matrix=pairs
        else:
            matrix=build_compatibility_matrix(updated,content,slot_extractor=extractor,context_mode=policy)
        pd.testing.assert_frame_equal(matrix[['query_id','content_id']],pairs[['query_id','content_id']])
        np.testing.assert_allclose(matrix.entity_coverage,pairs.entity_coverage)
        np.testing.assert_array_equal(matrix.intent_content_type_match.to_numpy(),pairs.intent_content_type_match.to_numpy())
        context=matrix.context_coverage.to_numpy().reshape(hybrid.shape)
        for family,scorer in score_families.items():
            rankings[f'{family}:{variant}']=rank_scores(scorer(context),queries.query_id,content.content_id)
        context_audit.append(dict(variant=variant,title_comparison=int(prepared.title_comparison_flag.sum()),
            title_renal=int(prepared.title_renal_function_group.notna().sum()),title_dosing=int(prepared.title_dose_context_flag.sum()),
            effective_comparison=int(prepared.content_comparison_context.sum()),effective_dosing=int(prepared.content_dose_context.sum()),
            query_negation=int(updated.negation_flag.sum()),context_positive_pairs=int(matrix.context_coverage.gt(0).sum())))
        if variant=='repaired_explicit':
            updated.to_csv(output_dir/'queries_repaired.csv',index=False)
            prepared.to_csv(output_dir/'content_repaired.csv',index=False)
            matrix.to_csv(output_dir/'compatibility_repaired.csv.gz',index=False)
            for side,ids,texts in [('query',queries.query_id,queries.query_text),('content',content.content_id,content.title)]:
                for rid,text in zip(ids,texts):
                    old=legacy_extractor(text).__dict__;new=repaired_extractor(text).__dict__
                    for field in old:
                        if old[field]!=new[field]:changes.append(dict(side=side,record_id=rid,text=text,field=field,before=old[field],after=new[field]))
    rankings['hybrid']=rank_scores(hybrid,queries.query_id,content.content_id)
    old=pd.read_csv(PHASE11_DIR/'rankings.csv.gz')
    for family,exp in [('BM25_E_C','R-E2'),('H_E_C','R-E6'),('H_E_C_I','R-E7')]:
        cols=['query_id','content_id','rank']
        pd.testing.assert_frame_equal(rankings[f'{family}:legacy'][cols],old[old.experiment.eq(exp)][cols].reset_index(drop=True))
    pd.concat([r.assign(experiment=n) for n,r in rankings.items()],ignore_index=True).to_csv(output_dir/'rankings.csv.gz',index=False)
    pd.DataFrame(changes).to_csv(output_dir/'extraction_changes.csv',index=False)
    pd.DataFrame(context_audit).to_csv(output_dir/'context_audit.csv',index=False)
    metadata=pairs.groupby('query_id').first()[['query_language','query_intent','context_constraint_count']].reset_index()
    metadata['has_context']=metadata.context_constraint_count.gt(0)
    inputs=[CONTENT_PATH,QUERIES_PATH,INTENT_METADATA_QUERIES_PATH,COMPATIBILITY_MATRIX_PATH,*caches]
    for protocol in ('temporal','query','query_dedup'):
        for split in ('validation','test'):
            path=SPLIT_DIR/f'{protocol}_{split}_judgments.csv';inputs.append(path);judgments=pd.read_csv(path);primary={}
            for name,ranks in rankings.items():
                for scheme,threshold in [('relevance_grade',1),('conservative_relevance_grade',1),('event_hierarchy_relevance_grade',1),('relevance_grade',2)]:
                    tags=dict(protocol=protocol,split=split,experiment=name,scheme=scheme,threshold=threshold)
                    per=evaluate_rankings(ranks,judgments,scheme,threshold)
                    summaries.append(tags|summarize_metrics(per))
                    if scheme=='relevance_grade' and threshold==1:
                        primary[name]=per;details.append(per.assign(**tags))
                        enriched=per.merge(metadata,on='query_id',validate='one_to_one')
                        for dimension in ('query_language','query_intent','has_context'):
                            for value,group in enriched.groupby(dimension):slices.append(tags|dict(dimension=dimension,value=value)|summarize_metrics(group))
            contrasts=[(f'{f}:{v}',f'{f}:legacy') for f in score_families for v in variants if v!='legacy']
            for candidate,reference in contrasts:
                delta=paired_delta(primary[reference],primary[candidate]);d=primary[candidate].set_index('query_id')['ndcg@10']-primary[reference].set_index('query_id')['ndcg@10']
                comparisons.append(dict(protocol=protocol,split=split,candidate=candidate,reference=reference,delta_ndcg=delta['delta_vs_full'],lower=delta['lower'],upper=delta['upper'],improved=int((d>0).sum()),worsened=int((d<0).sum()),unchanged=int((d==0).sum())))
    summary=pd.DataFrame(summaries);comparison=pd.DataFrame(comparisons)
    summary.to_csv(output_dir/'metrics.csv',index=False);comparison.to_csv(output_dir/'paired_comparisons.csv',index=False)
    pd.concat(details,ignore_index=True).to_csv(output_dir/'per_query_metrics.csv.gz',index=False);pd.DataFrame(slices).to_csv(output_dir/'slices.csv',index=False)
    churn=[]
    for family in score_families:
        a=rankings[family+':legacy'].query('rank <= 10').groupby('query_id').content_id.agg(tuple)
        b=rankings[family+':repaired_explicit'].query('rank <= 10').groupby('query_id').content_id.agg(tuple)
        churn.append(dict(family=family,order_changes=int((a!=b).sum()),membership_changes=sum(set(x)!=set(y) for x,y in zip(a,b))))
    pd.DataFrame(churn).to_csv(output_dir/'ranking_changes.csv',index=False)
    manifest=dict(variants={k:dict(extractor='v2' if e is repaired_extractor else 'v1',context_policy=p) for k,(e,p) in variants.items()},
        weights='frozen original R-E2/R-E6/R-E7 and fixed hybrid + .1 entity + .1 context; no retuning or model selection',
        deployment='versioned v2 extractor and explicit policy; old snapshots preserved; use outputs here for repaired retrieval',
        scope='renal coordination, Indonesian comparison, safety-question negation; split explicit context and content-type proxies; entities/intent/labels unchanged',
        limitations=['exploratory after test inspection','behavioral relevance is sparse and noisy','no classifier retraining; intent prior held fixed','no gold extraction precision/recall claimed; audited expressions and regression cases only'],**runtime,
        sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs+[Path(__file__),Path('src/query_extraction.py'),Path('src/query_extraction_v2.py'),Path('src/structured_compatibility.py'),Path('src/evaluation.py')]})
    (output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    primary=summary.query("protocol == 'temporal' and scheme == 'relevance_grade' and threshold == 1")
    view=primary.pivot(index='experiment',columns='split',values=['ndcg@10','recall@10','mrr@10']);view.columns=[' '.join(c) for c in view.columns]
    report='\n\n'.join(['# Audit-driven context repairs: controlled retrieval evaluation',
        'Run `.venv/bin/python -m src.context_repair_experiment`. Repaired extraction is versioned in query_extraction_v2.py. Content preparation exposes explicit title evidence and type-only proxies separately; context_mode="explicit" scores title evidence for dosing/comparison. Legacy defaults and saved artifacts remain reproducible. Repaired query/content snapshots and compatibility matrix are saved with this experiment.',
        'V2 recognizes Perbandingan/membandingkan/dibandingkan; coordinated Renal and Hepatic Impairment; and excludes aman [atau] tidak safety-question spans from negation while retaining other negation. Self-comparisons remain marked as comparisons; distinct entities are not fabricated. These changes do not infer exact renal ranges, add missing molecules, or introduce fuzzy matching.',
        'Four context variants isolate cue repairs, proxy removal, and their combination. Each runs in four frozen score families: BM25+entities+context (R-E2), hybrid+entities+context (R-E6), plus intent (R-E7), and hybrid+0.1*entities+0.1*context. No weights are tuned. All historical baseline rankings are checked for exact parity.',
        '## Extraction and evidence counts',table(pd.DataFrame(context_audit)),
        'These count verified pattern changes, not extraction accuracy against independent gold labels. Negation is not a retrieval score feature, so that repair cannot directly explain ranking changes. Publication-year/other existing context metadata remain in scoring; explicit-only specifically removes dosing/drug-profile and comparison/review substitutions.',
        '## Temporal validation and test',table(view.reset_index().round(5)),
        '## Paired temporal-test deltas',
        'Delta=candidate minus same-family legacy reference; 95% paired query bootstrap, 2,000 resamples, seed42. Descriptive, not cluster-robust or corrected for multiple comparisons.',
        table(comparison.query("protocol == 'temporal' and split == 'test'").drop(columns=['protocol','split']).round(5)),
        '## Top-10 changes across all 500 queries',table(pd.DataFrame(churn)),
        '## Interpretation boundary',
        'Extraction correctness and retrieval proxy scores are separate. Repairs may move unjudged documents without improving behavioral metrics; prior test inspection makes this exploratory. No new clinical judgments were created. Entity features, assisted intent labels, trained intent models and relevance labels were held fixed. This evaluates retrieval metrics, not retrained intent-classifier accuracy. Per-query metrics, all cutoffs, alternate grades, query-held-out sensitivity, slices and fingerprints are saved beside this report.'
    ])+'\n'
    # Narrative findings are consolidated in write_up/phase11_summary.md.
    log=pd.read_csv(EXPERIMENT_LOG_PATH)
    for family in score_families:
        experiment='R-REPAIR-'+family;v=primary[primary.experiment.eq(family+':repaired_explicit')].set_index('split')['ndcg@10']
        row=dict(experiment=experiment,hypothesis='explicit repaired context improves retrieval at frozen weights',method=family+' with v2 cues and explicit dosing/comparison evidence',primary_metric='NDCG@10',result=f"Validation={v['validation']:.5f}; test={v['test']:.5f}",decision='controlled exploratory repair comparison; weights unchanged')
        log=pd.concat([log[~log.experiment.eq(experiment)],pd.DataFrame([row])],ignore_index=True)
    log.to_csv(EXPERIMENT_LOG_PATH,index=False)
    return {'output_dir':str(output_dir),'changed_slot_values':len(changes)}


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
