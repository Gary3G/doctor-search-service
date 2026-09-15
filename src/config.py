"""Shared project configuration.

Keep modeling notebooks and scripts pointed at these constants so experiments
remain reproducible and easy to review.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
METRICS_DIR = OUTPUT_DIR / "metrics"
FIGURES_DIR = OUTPUT_DIR / "figures"
TAXONOMY_DIR = OUTPUT_DIR / "taxonomy"
CACHE_DIR = DATA_DIR / "cache"
EXPERIMENT_LOG_PATH = PROJECT_ROOT / "experiments" / "experiment_log.csv"

QUERIES_PATH = RAW_DATA_DIR / "queries.csv"
CONTENT_PATH = RAW_DATA_DIR / "content.csv"
BEHAVIORAL_SIGNALS_PATH = RAW_DATA_DIR / "behavioral_signals.csv"
IMPRESSIONS_PATH = RAW_DATA_DIR / "impressions.csv"


@dataclass(frozen=True)
class ProjectConfig:
    random_seed: int = 42
    validation_size: float = 0.20
    test_size: float = 0.20
    top_k_values: tuple[int, ...] = (1, 3, 5, 10, 20)
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    intent_model_name: str = "tfidf_logistic_regression"
    semantic_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    positive_relevance_threshold: float = 1.0
    negative_relevance_threshold: float = 0.0
    min_dwell_seconds_for_positive: int = 30


CONFIG = ProjectConfig()
RANDOM_SEED = CONFIG.random_seed


def set_random_seed(seed: int = RANDOM_SEED) -> None:
    """Seed local pseudo-random generators used by the project."""
    random.seed(seed)
    np.random.seed(seed)
