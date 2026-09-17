import numpy as np
import pandas as pd
import pytest
from src.signed_retrieval import explicit_conflict, signed_scores, select, WEIGHTS


def test_conflicts_require_both_values_and_preserve_missing_neutrality():
    left=pd.Series(['adult','adult',None,'','oral','2025'])
    right=pd.Series(['elderly',None,'adult','elderly','oral','2024'])
    assert explicit_conflict(left,right).tolist()==[True,False,False,False,False,True]
    assert explicit_conflict(pd.Series([2025.,2025.,np.nan]),pd.Series([2024.,np.nan,2024.])).tolist()==[True,False,False]


def test_signed_score_rewards_matches_penalizes_conflicts_and_leaves_empty_neutral():
    hybrid=np.array([[.5,.5,.5]])
    signals={'entity_bonus':np.array([[1.,0.,0.]]),'entity_penalty':np.array([[0.,1.,0.]]),
             'context_bonus':np.array([[1.,0.,0.]]),'context_penalty':np.array([[0.,1.,0.]])}
    np.testing.assert_allclose(signed_scores(hybrid,signals,(.1,.2,.05,.1)),[[.65,.2,.5]])
    np.testing.assert_equal(signed_scores(hybrid,signals,(0,0,0,0)),hybrid)
    np.testing.assert_allclose(signed_scores(hybrid,signals,(0,.2,0,.1)),[[.5,.2,.5]])
    with pytest.raises(ValueError): signed_scores(hybrid,signals,(0,-1,0,0))


def test_validation_selection_ignores_test_and_prefers_zero_on_ties():
    trials=pd.DataFrame([{**dict.fromkeys(WEIGHTS,0.),'ndcg@10':.2,'test_metric':0.},
                         {**dict.fromkeys(WEIGHTS,.2),'ndcg@10':.2,'test_metric':1.}])
    assert select(trials)[list(WEIGHTS)].sum()==0
    trials.loc[1,'ndcg@10']=.3
    assert select(trials).entity_penalty==.2


def test_complementary_entity_penalty_is_bonus_plus_query_constant():
    h=np.array([[.2,.4,.5]])
    match=np.array([[1.,.5,0.]])
    signals={'entity_bonus':match,'entity_penalty':1-match,'context_bonus':np.zeros_like(h),'context_penalty':np.zeros_like(h)}
    bonus=signed_scores(h,signals,(.2,0,0,0))
    penalty=signed_scores(h,signals,(0,.2,0,0))
    np.testing.assert_allclose(penalty,bonus-.2)
