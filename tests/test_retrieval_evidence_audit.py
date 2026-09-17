import pandas as pd
from src.retrieval_evidence_audit import literal_span, OUTPUT


def test_literal_evidence_respects_word_boundaries_and_punctuation():
    assert literal_span('PIPERACILLIN–tazobactam treatment','Piperacillin-tazobactam')=='PIPERACILLIN–tazobactam'
    assert literal_span('Metoprolol versus Empagliflozin','Empagliflozin')=='Empagliflozin'
    assert literal_span('Metoprolol','Met')==''
    assert literal_span('GLP-1 receptor agonists','Semaglutide')==''


def test_audit_sample_has_complete_review_and_separate_random_risk_groups():
    frame=pd.read_csv(OUTPUT/'reviewed_sample.csv')
    assert len(frame)==60 and not frame.duplicated(['side','record_id']).any()
    assert frame.review_notes.notna().all()
    for side,g in frame.groupby('side'):
        random=g[g.sample_group.eq('language_stratified_random')]
        assert random.groupby('language').size().to_dict()=={'EN':6,'ID':6,'MIXED':6}
        assert g.sample_group.eq('targeted_risk').sum()==12
    assert not any('relevance' in c or 'rank' in c for c in frame.columns)


def test_evidence_counts_reconcile_without_treating_metadata_only_as_wrong():
    ent=pd.read_csv(OUTPUT/'entity_evidence.csv').query('duplicate == False')
    summary=pd.read_csv(OUTPUT/'entity_support_summary.csv')
    assert summary.unique_terms.sum()==len(ent)
    assert summary.literal_supported.sum()==ent.evidence_source.eq('text_and_metadata').sum()
    assert ent[ent.evidence_source.eq('text_and_metadata')].evidence_span.notna().all()
    assert set(ent.evidence_source)=={'text_and_metadata','metadata_without_literal_text_support'}
