"""Ranking accuracy metrics and behavioral diagnostics."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import Any


def precision_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top = ranked_ids[:k]
    hits = sum(1 for product_id in top if product_id in relevant_ids)
    return hits / k


def recall_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids or k <= 0:
        return 0.0
    top = ranked_ids[:k]
    hits = sum(1 for product_id in top if product_id in relevant_ids)
    return hits / len(relevant_ids)


def hit_rate_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0 or not relevant_ids:
        return 0.0
    return 1.0 if any(product_id in relevant_ids for product_id in ranked_ids[:k]) else 0.0


def reciprocal_rank(ranked_ids: Sequence[str], relevant_ids: set[str]) -> float:
    for rank, product_id in enumerate(ranked_ids, start=1):
        if product_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def average_precision_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids or k <= 0:
        return 0.0

    hits = 0
    precision_sum = 0.0
    for rank, product_id in enumerate(ranked_ids[:k], start=1):
        if product_id in relevant_ids:
            hits += 1
            precision_sum += hits / rank
    return precision_sum / min(len(relevant_ids), k)


def ndcg_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0 or not relevant_ids:
        return 0.0

    dcg = 0.0
    for index, product_id in enumerate(ranked_ids[:k]):
        if product_id in relevant_ids:
            dcg += 1.0 / math.log2(index + 2)

    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(index + 2) for index in range(ideal_hits))
    if idcg == 0:
        return 0.0
    return dcg / idcg


def compute_accuracy_metrics(
    ranked_ids: Sequence[str],
    relevant_ids: set[str],
    k_values: Iterable[int],
) -> dict[str, float]:
    metrics: dict[str, float] = {
        "mrr": reciprocal_rank(ranked_ids, relevant_ids),
    }
    for k in k_values:
        metrics[f"precision@{k}"] = precision_at_k(ranked_ids, relevant_ids, k)
        metrics[f"recall@{k}"] = recall_at_k(ranked_ids, relevant_ids, k)
        metrics[f"map@{k}"] = average_precision_at_k(ranked_ids, relevant_ids, k)
        metrics[f"ndcg@{k}"] = ndcg_at_k(ranked_ids, relevant_ids, k)
        metrics[f"hit_rate@{k}"] = hit_rate_at_k(ranked_ids, relevant_ids, k)
    return metrics


def catalog_coverage(recommendation_lists: Sequence[Sequence[str]], catalog_size: int) -> float:
    if catalog_size <= 0:
        return 0.0
    recommended = {product_id for recs in recommendation_lists for product_id in recs}
    return len(recommended) / catalog_size


def intra_list_diversity(
    recommended_ids: Sequence[str],
    product_tags: dict[str, set[str]],
) -> float:
    """Average pairwise Jaccard distance over concern tags."""
    tags = [product_tags.get(product_id, set()) for product_id in recommended_ids]
    if len(tags) < 2:
        return 0.0

    distances: list[float] = []
    for i in range(len(tags)):
        for j in range(i + 1, len(tags)):
            union = tags[i] | tags[j]
            if not union:
                distances.append(0.0)
                continue
            intersection = tags[i] & tags[j]
            jaccard = len(intersection) / len(union)
            distances.append(1.0 - jaccard)
    return sum(distances) / len(distances)


def novelty_at_k(
    ranked_ids: Sequence[str],
    popularity_prob: dict[str, float],
    k: int,
) -> float:
    if k <= 0:
        return 0.0
    scores: list[float] = []
    for product_id in ranked_ids[:k]:
        prob = popularity_prob.get(product_id, 1e-12)
        scores.append(-math.log(prob))
    return sum(scores) / len(scores) if scores else 0.0


def build_popularity_distribution(catalog: list[dict[str, Any]]) -> dict[str, float]:
    weights = [max(int(item.get("loves_count") or 0), 1) for item in catalog]
    total = float(sum(weights))
    return {
        str(item["product_id"]): weight / total
        for item, weight in zip(catalog, weights, strict=True)
    }
