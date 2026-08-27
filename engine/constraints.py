"""Hard constraint filtering — eliminations, never score penalties."""

from __future__ import annotations

from typing import Any

from engine.types import BeautyProfile


def _category_matches(product: dict[str, Any], category: str) -> bool:
    normalized = category.strip().lower()
    secondary = str(product.get("secondary_category") or "").lower()
    tertiary = str(product.get("tertiary_category") or "").lower()
    return normalized in {secondary, tertiary}


def passes_constraints(product: dict[str, Any], profile: BeautyProfile) -> bool:
    if product.get("out_of_stock"):
        return False

    price = float(product.get("price_usd") or 0)
    if price <= 0 or price > profile.budget_max_usd:
        return False

    if profile.category and not _category_matches(product, profile.category):
        return False

    flags = product.get("exclusion_flags") or {}
    return not any(flags.get(exclusion, False) for exclusion in profile.exclusions)


def filter_catalog(
    catalog: list[dict[str, Any]],
    profile: BeautyProfile,
) -> tuple[list[int], list[int]]:
    """Return (eligible_indices, rejected_indices) preserving catalog order."""
    eligible: list[int] = []
    rejected: list[int] = []
    for index, product in enumerate(catalog):
        if passes_constraints(product, profile):
            eligible.append(index)
        else:
            rejected.append(index)
    return eligible, rejected
