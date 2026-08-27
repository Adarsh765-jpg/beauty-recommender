"""Naive ranking baselines for evaluation."""

from __future__ import annotations

import random
from typing import Any

from engine.artifacts import ArtifactBundle
from engine.constraints import filter_catalog
from engine.types import BeautyProfile


def _eligible_products(
    profile: BeautyProfile,
    artifacts: ArtifactBundle,
) -> tuple[list[int], list[dict[str, Any]]]:
    eligible_indices, _ = filter_catalog(artifacts.catalog, profile)
    products = [artifacts.catalog[index] for index in eligible_indices]
    return eligible_indices, products


def rank_random(
    profile: BeautyProfile,
    artifacts: ArtifactBundle,
    *,
    seed: int,
) -> list[str]:
    _, products = _eligible_products(profile, artifacts)
    ids = [str(product["product_id"]) for product in products]
    rng = random.Random(seed)
    rng.shuffle(ids)
    return ids


def rank_popularity(profile: BeautyProfile, artifacts: ArtifactBundle) -> list[str]:
    _, products = _eligible_products(profile, artifacts)
    products.sort(
        key=lambda product: (
            int(product.get("loves_count") or 0),
            int(product.get("review_count") or 0),
        ),
        reverse=True,
    )
    return [str(product["product_id"]) for product in products]


def rank_rating(profile: BeautyProfile, artifacts: ArtifactBundle) -> list[str]:
    _, products = _eligible_products(profile, artifacts)
    products.sort(
        key=lambda product: (
            float(product.get("rating") or 0.0),
            int(product.get("review_count") or 0),
        ),
        reverse=True,
    )
    return [str(product["product_id"]) for product in products]
