"""Phase 9: fixed, title-only BM25 baseline over the complete corpus."""
from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi

from src.config import CONFIG


def tokenize(text: str) -> list[str]:
    """Unicode case folding; retain words/numbers without stemming or expansion."""
    return re.findall(r'\w+', unicodedata.normalize('NFKC', text).casefold())


class BM25Retriever:
    def __init__(self, content: pd.DataFrame):
        if content.empty or content.content_id.isna().any() or content.content_id.duplicated().any():
            raise ValueError('Corpus requires unique nonmissing content IDs')
        self.content = content.sort_values('content_id').reset_index(drop=True)
        tokens = self.content.title.fillna('').map(tokenize).tolist()
        if not any(tokens):
            raise ValueError('Corpus has no indexable title tokens')
        self.index = BM25Okapi(tokens, k1=CONFIG.bm25_k1, b=CONFIG.bm25_b)

    def search(self, query: str, k: int = 20) -> pd.DataFrame:
        if k < 1:
            raise ValueError('k must be positive')
        scores = self.index.get_scores(tokenize(query))
        # Stable content-ID tie break, including empty/OOV queries.
        order = np.argsort(-scores, kind='stable')[:k]
        result = self.content.iloc[order][['content_id', 'title']].copy()
        result['rank'] = np.arange(1, len(result) + 1)
        result['score'] = scores[order]
        return result.reset_index(drop=True)

    def rank_queries(self, queries: pd.DataFrame, k: int = 20) -> pd.DataFrame:
        if queries.query_id.isna().any() or queries.query_id.duplicated().any() or queries.query_text.isna().any():
            raise ValueError('Queries require unique IDs and nonmissing text')
        results = []
        for row in queries.sort_values('query_id').itertuples():
            ranked = self.search(row.query_text, k)
            ranked.insert(0, 'query_id', row.query_id)
            results.append(ranked)
        return pd.concat(results, ignore_index=True)
