"""Runtime skin-type cohort prior lookup."""

from __future__ import annotations

from typing import Any


def cohort_score_for_product(
    product: dict[str, Any],
    profile_skin_type: str,
    cohort_stats: dict[str, Any] | None,
    min_reviews: int,
) -> tuple[float, bool]:
    """Return (score, has_sufficient_evidence).

    When a product-and-skin-type cell has fewer than ``min_reviews`` train
    reviews, the cohort term is omitted and ranking falls back to content +
    quality only.
    """
    if not cohort_stats:
        return 0.0, False

    product_id = str(product.get("product_id") or "")
    cells = cohort_stats.get("cells") or {}
    product_cells = cells.get(product_id) or {}
    cell = product_cells.get(profile_skin_type)
    if not cell:
        return 0.0, False

    review_count = int(cell.get("review_count") or 0)
    if review_count < min_reviews:
        return 0.0, False

    shrunk_rate = float(cell.get("shrunk_rate") or 0.0)
    return max(0.0, min(shrunk_rate, 1.0)), True
