"""Tests for evaluation metrics (hand-computed examples)."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.evaluation.metrics import (
    average_precision_at_k,
    compute_accuracy_metrics,
    hit_rate_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from src.evaluation.relevance import is_relevant
from src.evaluation.split import temporal_split, verify_no_temporal_overlap


def test_precision_recall_hit_rate_hand_computed() -> None:
    ranked = ["a", "b", "c", "d"]
    relevant = {"b", "d"}

    assert precision_at_k(ranked, relevant, 2) == 0.5
    assert recall_at_k(ranked, relevant, 2) == 0.5
    assert hit_rate_at_k(ranked, relevant, 2) == 1.0
    assert hit_rate_at_k(ranked, relevant, 1) == 0.0


def test_mrr_and_map_hand_computed() -> None:
    ranked = ["x", "target", "y"]
    relevant = {"target"}

    assert reciprocal_rank(ranked, relevant) == 0.5
    assert average_precision_at_k(ranked, relevant, 3) == pytest.approx(1 / 2)


def test_ndcg_hand_computed() -> None:
    ranked = ["miss", "hit", "miss2"]
    relevant = {"hit"}

    assert ndcg_at_k(ranked, relevant, 3) == pytest.approx(1 / math.log2(3))


def test_compute_accuracy_metrics_keys() -> None:
    metrics = compute_accuracy_metrics(["a", "b"], {"b"}, k_values=(1, 2))
    assert metrics["mrr"] == 0.5
    assert metrics["precision@1"] == 0.0
    assert metrics["precision@2"] == 0.5
    assert metrics["hit_rate@2"] == 1.0


def test_relevance_label_prefers_is_recommended() -> None:
    assert is_relevant(True, 2) is True
    assert is_relevant(False, 5) is False
    assert is_relevant(None, 4) is True
    assert is_relevant(None, 3) is False


def test_temporal_split_has_no_overlap() -> None:
    reviews = pd.DataFrame(
        {
            "submission_time": pd.date_range("2020-01-01", periods=100, freq="D"),
            "product_id": ["P1"] * 100,
            "author_id": [str(i) for i in range(100)],
            "rating": [5] * 100,
        }
    )
    split_reviews = temporal_split(reviews)
    assert verify_no_temporal_overlap(split_reviews) is True
    assert set(split_reviews["split"]) == {"train", "val", "test"}


def test_random_hit_rate_near_chance_synthetic() -> None:
    import random

    candidate_count = 500
    ranked_pool = [f"p{i}" for i in range(candidate_count)]
    relevant = {"p123"}
    rng = random.Random(0)
    hits = []
    for _ in range(200):
        shuffled = ranked_pool[:]
        rng.shuffle(shuffled)
        hits.append(hit_rate_at_k(shuffled, relevant, 10))
    assert sum(hits) / len(hits) == pytest.approx(10 / candidate_count, rel=0.4, abs=0.02)
