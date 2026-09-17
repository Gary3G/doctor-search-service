import numpy as np
import pandas as pd
import pytest
from src.topic_boost_retrieval import topic_gate, boosted_scores, choose_weights


def test_topic_gate_requires_exact_disease_or_molecule_and_blocks_broad_matches():
    pairs = pd.DataFrame({'disease_match':[True,False,False], 'molecule_match':[False,True,False], 'drug_class_match':[False,False,True]})
    np.testing.assert_equal(topic_gate(pairs,(1,3)),[[1,1,0]])
    pairs['disease_match']=pairs['disease_match'].astype('boolean')
    pairs.loc[0,'disease_match']=None
    with pytest.raises(ValueError): topic_gate(pairs,(1,3))


def test_context_only_changes_topic_matched_documents_and_removals_are_exact():
    hybrid=np.array([[.5,.6]])
    entity=np.array([[1.,0.]])
    context=np.ones((1,2))
    gate=np.array([[1.,0.]])
    np.testing.assert_allclose(boosted_scores(hybrid,entity,context,gate,.1,.05),[[.65,.6]])
    np.testing.assert_equal(boosted_scores(hybrid,entity,context,gate,0,0),hybrid)
    np.testing.assert_allclose(boosted_scores(hybrid,entity,context,gate,.1,0),[[.6,.6]])
    assert boosted_scores(hybrid,entity,context,gate,0,.2)[0,0] > hybrid[0,1]


def test_weight_selection_prefers_zero_when_validation_tied():
    trials=pd.DataFrame({'alpha':[.1,0.,0.], 'beta':[0.,.1,0.], 'ndcg@10':[.2,.2,.2], 'test_ndcg':[.9,.8,0.]})
    selected=choose_weights(trials)
    assert selected.alpha==0 and selected.beta==0
    trials.loc[0,'ndcg@10']=.21
    assert choose_weights(trials).alpha==.1
