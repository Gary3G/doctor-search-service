import pandas as pd
import pytest
from src.query_extraction import extract_slots as legacy
from src.query_extraction_v2 import extract_slots
from src.structured_compatibility import prepare_content_context
from src.config import CONTENT_PATH, QUERIES_PATH


@pytest.mark.parametrize('text',['Perbandingan A dan B','membandingkan A dengan B','A dibandingkan B'])
def test_indonesian_comparison_cues(text):
    assert extract_slots(text).comparison_flag
    assert not legacy(text).comparison_flag


def test_comparison_does_not_invent_distinct_drugs():
    assert extract_slots('Perbandingan Diazepam dan Diazepam').comparison_flag
    assert not extract_slots('Dosis Diazepam').comparison_flag


def test_coordinated_renal_phrase_and_negative_controls():
    assert extract_slots('Dose Adjustment in Renal and Hepatic Impairment').renal_function_group=='renal_impairment'
    assert extract_slots('Hepatic impairment').renal_function_group is None
    assert extract_slots('renal function monitoring').renal_function_group is None
    assert extract_slots('eGFR <30').renal_function_group=='severe_impairment'


@pytest.mark.parametrize('text',['obat aman tidak','kombinasi A dan B aman atau tidak'])
def test_safety_question_is_not_asserted_negation(text):
    assert legacy(text).negation_flag
    assert not extract_slots(text).negation_flag
    assert extract_slots(text+' tanpa? without heart failure').negation_flag
    assert extract_slots(text+' pada pasien tidak hamil').negation_flag


def test_explicit_policy_separates_type_proxy_and_title_evidence():
    content=pd.read_csv(CONTENT_PATH).head(1).copy()
    content['title']='Mechanism, Indications, and Safety';content['content_type']='drug_profile'
    old=prepare_content_context(content)
    new=prepare_content_context(content,slot_extractor=extract_slots,context_mode='explicit')
    assert old.iloc[0].content_dose_context
    assert new.iloc[0].dose_type_only_proxy and not new.iloc[0].content_dose_context
    content['title']='Perbandingan A dan B';content['content_type']='review'
    new=prepare_content_context(content,slot_extractor=extract_slots,context_mode='explicit')
    assert new.iloc[0].comparison_title_evidence and new.iloc[0].content_comparison_context
    assert not new.iloc[0].comparison_type_only_proxy
    with pytest.raises(ValueError):prepare_content_context(content,context_mode='unknown')


def test_corpus_repairs_match_audited_counts():
    q=pd.read_csv(QUERIES_PATH);c=pd.read_csv(CONTENT_PATH)
    oldq=[legacy(t) for t in q.query_text];newq=[extract_slots(t) for t in q.query_text]
    oldc=[legacy(t) for t in c.title];newc=[extract_slots(t) for t in c.title]
    assert sum(a.negation_flag!=b.negation_flag for a,b in zip(oldq,newq))==10
    assert sum(a.renal_function_group!=b.renal_function_group for a,b in zip(oldc,newc))==10
    assert sum(a.comparison_flag!=b.comparison_flag for a,b in zip(oldc,newc))==7
