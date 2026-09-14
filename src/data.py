"""Data loading helpers for the supplied assessment datasets."""

from __future__ import annotations

import pandas as pd

from src.config import (
    BEHAVIORAL_SIGNALS_PATH,
    CONTENT_PATH,
    IMPRESSIONS_PATH,
    QUERIES_PATH,
)


def load_queries() -> pd.DataFrame:
    return pd.read_csv(QUERIES_PATH)


def load_content() -> pd.DataFrame:
    return pd.read_csv(CONTENT_PATH)


def load_behavioral_signals() -> pd.DataFrame:
    return pd.read_csv(BEHAVIORAL_SIGNALS_PATH, parse_dates=["event_timestamp"])


def load_impressions() -> pd.DataFrame:
    return pd.read_csv(IMPRESSIONS_PATH, parse_dates=["timestamp_served"])


def load_all_raw() -> dict[str, pd.DataFrame]:
    return {
        "queries": load_queries(),
        "content": load_content(),
        "behavioral_signals": load_behavioral_signals(),
        "impressions": load_impressions(),
    }
