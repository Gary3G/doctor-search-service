"""Guard the validation-only review protocol and artifact evidence semantics."""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.bm25_failure_analysis import build_phase10_artifacts, select_review_queries
from src.bm25_baseline import BASELINE_DIR


class FailureAnalysisTests(unittest.TestCase):
    def test_sample_is_validation_only_and_order_independent(self):
        metrics = pd.read_csv(BASELINE_DIR / 'bm25_per_query_metrics.csv')
        selected = select_review_queries(metrics)
        pd.testing.assert_frame_equal(selected, select_review_queries(metrics.sample(frac=1, random_state=7)))
        self.assertEqual(selected.stratum.value_counts().to_dict(), {'miss': 26, 'hit': 8, 'no_positive': 6})
        self.assertEqual(set(selected.split), {'validation'})
        self.assertEqual(set(selected.protocol), {'temporal'})
        # Test scores cannot influence selection, even if altered arbitrarily.
        metrics.loc[metrics.split.eq('test'), 'recall@10'] = 999
        pd.testing.assert_frame_equal(selected, select_review_queries(metrics))

    def test_evidence_preserves_unjudged_and_no_positive_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build_phase10_artifacts(root)
            cases = pd.read_csv(root / 'review_cases.csv').set_index('query_id')
            pairs = pd.read_csv(root / 'review_evidence.csv')
            self.assertEqual(len(cases), 40)
            self.assertTrue(cases.loc[cases.stratum.eq('no_positive'), 'recall_at_10'].isna().all())
            q070 = pairs.query("query_id == 'Q070' and role == 'retrieved top 3'").iloc[0]
            self.assertEqual(q070.content_id, 'C053')
            self.assertEqual(q070.grade, 'unjudged')
            self.assertEqual(cases.loc['Q070', 'recall_at_10'], 0)
            # A behaviorally credited, visibly off-topic hit remains a hit in the saved evidence.
            q201 = pairs.query("query_id == 'Q201' and role == 'observed top-10 hit'").iloc[0]
            self.assertEqual(q201.content_id, 'C089')
            self.assertGreater(float(q201.grade), 0)
            self.assertEqual(q201['rank'], 7)
