"""Build train-only skin-type cohort statistics for the cohort prior."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.config import COHORT_MIN_REVIEWS, COHORT_PRIOR_REVIEWS, SKIN_TYPES
from src.evaluation.relevance import is_relevant
from src.evaluation.split import temporal_split


def build_cohort_stats(
    reviews: pd.DataFrame,
    catalog_product_ids: set[str],
    *,
    split_name: str = "train",
    min_reviews: int = COHORT_MIN_REVIEWS,
    prior_reviews: int = COHORT_PRIOR_REVIEWS,
) -> dict[str, Any]:
    """Aggregate product-by-skin-type recommendation rates from one split only."""
    if "split" not in reviews.columns:
        reviews = temporal_split(reviews)

    subset = reviews.loc[
        reviews["split"].eq(split_name)
        & reviews["has_valid_skin_type"]
        & reviews["product_id"].isin(catalog_product_ids)
    ].copy()

    if subset.empty:
        raise ValueError(f"no reviews available for split={split_name!r}")

    subset["recommended"] = subset.apply(
        lambda row: is_relevant(row.get("is_recommended"), int(row["rating"])),
        axis=1,
    )
    global_rate = float(subset["recommended"].mean())

    cells: dict[str, dict[str, dict[str, float | int]]] = {}
    grouped = subset.groupby(["product_id", "skin_type"], sort=False)
    for (product_id, skin_type), group in grouped:
        review_count = len(group)
        recommendation_rate = float(group["recommended"].mean())
        shrunk_rate = (review_count * recommendation_rate + prior_reviews * global_rate) / (
            review_count + prior_reviews
        )
        cells.setdefault(str(product_id), {})[str(skin_type)] = {
            "review_count": review_count,
            "recommendation_rate": round(recommendation_rate, 4),
            "shrunk_rate": round(float(shrunk_rate), 4),
        }

    product_ids = sorted(catalog_product_ids)
    total_pairs = len(product_ids) * len(SKIN_TYPES)
    pairs_with_min_reviews = sum(
        1
        for product_id in product_ids
        for skin_type in SKIN_TYPES
        if cells.get(product_id, {}).get(skin_type, {}).get("review_count", 0) >= min_reviews
    )

    return {
        "min_reviews": min_reviews,
        "prior_reviews": prior_reviews,
        "global_recommendation_rate": round(global_rate, 4),
        "source_split": split_name,
        "cells": cells,
        "coverage": {
            "product_count": len(product_ids),
            "skin_type_count": len(SKIN_TYPES),
            "total_pairs": total_pairs,
            "pairs_with_min_reviews": pairs_with_min_reviews,
            "fraction_with_min_reviews": round(pairs_with_min_reviews / total_pairs, 4),
        },
    }


def train_review_count(
    reviews: pd.DataFrame,
    product_id: str,
    skin_type: str,
) -> int:
    if "split" not in reviews.columns:
        reviews = temporal_split(reviews)
    mask = (
        reviews["split"].eq("train")
        & reviews["product_id"].eq(product_id)
        & reviews["skin_type"].eq(skin_type)
    )
    return int(mask.sum())
