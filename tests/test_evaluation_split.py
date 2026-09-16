"""Leakage invariants for the retrieval protocol."""
import unittest

import pandas as pd

from src.evaluation_split import assign_partitions
from src.relevance_labels import aggregate_query_content_judgments, LABELED_EXPOSURES_PATH


class EvaluationSplitTests(unittest.TestCase):
    def fixture(self):
        return pd.DataFrame([dict(impression_id=f'I{i}', query_id=f'Q{i}',
            session_id=f'S{i}', doctor_id='D1', timestamp=f'2025-01-{i+1:02d}',
            last_timestamp_served=f'2025-01-{i+1:02d}', last_event_timestamp=None)
            for i in range(10)])

    def test_late_outcome_purges_entire_session(self):
        x = self.fixture()
        x.loc[0, 'last_event_timestamp'] = '2025-01-10'
        result, meta = assign_partitions(x, 'temporal')
        self.assertEqual(result.iloc[0].split, 'purged')
        self.assertEqual(set(result.split), {'train', 'validation', 'test', 'purged'})

    def test_query_split_is_order_invariant(self):
        x = self.fixture()
        a, _ = assign_partitions(x, 'query')
        b, _ = assign_partitions(x.sample(frac=1, random_state=7), 'query')
        self.assertEqual(dict(zip(a.query_id,a.split)),dict(zip(b.query_id,b.split)))

    def test_multiquery_session(self):
        x = self.fixture()
        x.loc[1, 'session_id'] = 'S0'
        result, _ = assign_partitions(x, 'query')
        self.assertEqual(result.iloc[0].split, result.iloc[1].split)

    def test_duplicate_exposure_rejected(self):
        x = self.fixture()
        with self.assertRaises(ValueError):
            assign_partitions(pd.concat([x,x.iloc[:1]]), 'query')

    def test_unknown_strategy_rejected(self):
        with self.assertRaises(ValueError):
            assign_partitions(self.fixture(), 'random_rows')

    def test_judgments_do_not_reuse_future_maximum(self):
        row = pd.read_csv(LABELED_EXPOSURES_PATH).iloc[[0]].copy()
        x = pd.concat([row] * 10, ignore_index=True)
        for col in self.fixture():
            x[col] = self.fixture()[col]
        x['query_id'] = 'Q1'
        x['relevance_grade'] = [0] * 8 + [3] * 2
        x['conservative_relevance_grade'] = x.relevance_grade
        x['event_hierarchy_relevance_grade'] = x.relevance_grade
        assigned, _ = assign_partitions(x, 'temporal')
        train = aggregate_query_content_judgments(assigned[assigned.split.eq('train')])
        test = aggregate_query_content_judgments(assigned[assigned.split.eq('test')])
        self.assertEqual(train.relevance_grade.max(), 0)
        self.assertEqual(test.relevance_grade.max(), 3)

    def test_normalized_duplicates_and_sessions_stay_together(self):
        x = self.fixture()
        x['query_text'] = [f'unrelated topic number {i}' for i in range(10)]
        x.loc[0, 'query_text'] = '  Asthma TREATMENT  '
        x.loc[1, 'query_text'] = 'asthma treatment'
        x.loc[2, 'session_id'] = 'S1'
        result, _ = assign_partitions(x, 'query_dedup')
        self.assertEqual(result.iloc[:3].split.nunique(), 1)
        self.assertEqual(result.iloc[:3].query_group.nunique(), 1)
        shuffled, _ = assign_partitions(x.sample(frac=1, random_state=7), 'query_dedup')
        self.assertEqual(dict(zip(result.query_id, result.split)), dict(zip(shuffled.query_id, shuffled.split)))

    def test_numeric_constraints_not_collapsed(self):
        from src.evaluation_split import find_duplicate_pairs
        x = pd.DataFrame({'query_id': ['A', 'B'], 'query_text': [
            'latest guideline for managing severe asthma in pediatric patients 2024',
            'latest guideline for managing severe asthma in pediatric patients 2025']})
        self.assertTrue(find_duplicate_pairs(x).empty)

    def test_near_duplicate_wording_detected(self):
        from src.evaluation_split import find_duplicate_pairs
        x = pd.DataFrame({'query_id': ['A', 'B'], 'query_text': [
            'latest guideline Preeclampsia management 2024',
            'latest Preeclampsia management guideline 2024']})
        self.assertEqual(len(find_duplicate_pairs(x)), 1)
