"""Product quality prior with Bayesian shrinkage toward the catalog mean."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.config import QUALITY_PRIOR_REVIEWS


def compute_catalog_rating_prior(catalog: list[dict[str, Any]]) -> float:
    ratings: list[float] = []
    for product in catalog:
        rating = product.get("rating")
        if rating is not None:
            ratings.append(float(rating))
    if not ratings:
        return 4.0
    return float(np.mean(ratings))


def quality_score(
    product: dict[str, Any],
    catalog_mean_rating: float,
    prior_reviews: int = QUALITY_PRIOR_REVIEWS,
) -> float:
    rating = product.get("rating")
    review_count = int(product.get("review_count") or 0)

    if rating is None or review_count <= 0:
        shrunk = catalog_mean_rating
    else:
        shrunk = (review_count * float(rating) + prior_reviews * catalog_mean_rating) / (
            review_count + prior_reviews
        )

    return float(np.clip(shrunk / 5.0, 0.0, 1.0))


def quality_scores_for_catalog(
    catalog: list[dict[str, Any]],
    catalog_mean_rating: float,
) -> np.ndarray:
    return np.array(
        [quality_score(product, catalog_mean_rating) for product in catalog],
        dtype=np.float32,
    )
