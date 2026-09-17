import numpy as np
import pandas as pd
import pytest

from src.incremental_retrieval import combine, normalize_bm25, paired_delta, rank_scores


def test_normalization_preserves_order_and_handles_constant_negative_scores():
    raw = np.array([[-2., 0., 2.], [3., 3., 3.]])
    normalized = normalize_bm25(raw)
    np.testing.assert_allclose(normalized, [[0., .5, 1.], [0., 0., 0.]])
    ids = ['C3', 'C1', 'C2']
    ranks = rank_scores(normalized, ['Q1', 'Q2'], ids, k=3)
    assert ranks[ranks.query_id.eq('Q1')].content_id.tolist() == ['C2', 'C1', 'C3']
    assert ranks[ranks.query_id.eq('Q2')].content_id.tolist() == ['C1', 'C2', 'C3']
    with pytest.raises(ValueError):
        rank_scores(np.array([[np.nan]]), ['Q1'], ['C1'], 1)


def test_ablation_does_not_redistribute_removed_signal_or_use_behavior():
    signals = {'bm25': np.array([[1., 0.]]), 'context': np.array([[0., 1.]])}
    np.testing.assert_equal(combine(signals, ('bm25',)), [[1., 0.]])
    np.testing.assert_equal(combine(signals, ('bm25', 'context')), [[.5, .5]])
    # A contextual unknown adds no evidence and cannot become an explicit penalty.
    signals['context'][:] = 0
    assert rank_scores(combine(signals, ('bm25', 'context')), ['Q'], ['A', 'B'], 2).content_id.tolist() == ['A', 'B']


def test_paired_intervals_align_queries_and_exclude_no_positive_queries():
    full = pd.DataFrame({'query_id': ['A', 'B', 'C'], 'ndcg@10': [.4, .2, np.nan]})
    other = pd.DataFrame({'query_id': ['C', 'B', 'A'], 'ndcg@10': [np.nan, .1, .3]})
    result = paired_delta(full, other)
    assert result['positive_queries'] == 2
    assert result['delta_vs_full'] == pytest.approx(-.1)
    assert result['lower'] == pytest.approx(-.1)
    assert result['upper'] == pytest.approx(-.1)
