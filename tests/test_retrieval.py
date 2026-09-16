"""Analytic ranking/metric tests for the phase 9 baseline."""
import unittest
import numpy as np
import pandas as pd
from src.retrieval import BM25Retriever, tokenize
from src.evaluation import evaluate_rankings, summarize_metrics


class RetrievalTests(unittest.TestCase):
    def test_title_only_and_deterministic_ties(self):
        content = pd.DataFrame({'content_id': ['C3', 'C1', 'C2'],
            'title': ['renal dose', 'asthma management', 'diabetes care'],
            'molecule_entity': ['asthma', '', '']})
        retriever = BM25Retriever(content)
        self.assertEqual(retriever.search('asthma').content_id.iloc[0], 'C1')
        self.assertEqual(retriever.search('unseen').content_id.tolist(), ['C1', 'C2', 'C3'])
        other = BM25Retriever(content.iloc[::-1])
        pd.testing.assert_frame_equal(retriever.search('dose'), other.search('dose'))
        self.assertEqual(tokenize('EGFR <30; ＡＳＴＨＭＡ'), ['egfr', '30', 'asthma'])

    def test_known_metrics_and_unjudged(self):
        ranks = pd.DataFrame({'query_id': ['Q']*3+['Z']*3,
            'content_id': ['U', 'A', 'B']*2, 'rank': [1, 2, 3]*2})
        judgments = pd.DataFrame({'query_id': ['Q','Q','Q','Z'],
            'content_id': ['A','B','C','A'], 'relevance_grade': [3,1,2,0]})
        result = evaluate_rankings(ranks, judgments, ks=(1, 3)).set_index('query_id')
        self.assertAlmostEqual(result.loc['Q','recall@3'], 2/3)
        self.assertEqual(result.loc['Q','mrr@3'], .5)
        expected = (7/np.log2(3) + 1/2)/(7 + 3/np.log2(3) + 1/2)
        self.assertAlmostEqual(result.loc['Q','ndcg@3'], expected)
        self.assertAlmostEqual(result.loc['Q','judged_fraction@3'], 2/3)
        self.assertTrue(np.isnan(result.loc['Z','recall@3']))
        self.assertEqual(summarize_metrics(result)['positive_queries'], 1)
        strict = evaluate_rankings(ranks, judgments, threshold=2, ks=(3,)).set_index('query_id')
        self.assertEqual(strict.loc['Q','recall@3'], .5)
        self.assertEqual(strict.loc['Q','ndcg@3'], result.loc['Q','ndcg@3'])
        with self.assertRaises(ValueError):
            evaluate_rankings(ranks, pd.concat([judgments,judgments]), ks=(3,))

    def test_perfect_ranking(self):
        ranks = pd.DataFrame({'query_id':['Q']*3,'content_id':['A','B','C'],'rank':[1,2,3]})
        labels = ranks.assign(relevance_grade=[3,2,0])
        row = evaluate_rankings(ranks, labels, ks=(3,)).iloc[0]
        for metric in ('recall@3','mrr@3','ndcg@3','judged_fraction@3'):
            self.assertEqual(row[metric], 1.)
