"""Combine constraints, content ranking, quality, and cohort prior."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from engine.artifacts import ArtifactBundle
from engine.cohort_signal import cohort_score_for_product
from engine.constraints import filter_catalog
from engine.content_ranker import build_profile_text, score_content_components
from engine.explain import attach_explanation
from engine.quality import quality_score
from engine.scoring import compute_final_score
from engine.types import (
    BeautyProfile,
    ContentWeights,
    MixingWeights,
    RankedProduct,
    RankingConfig,
    RankingFlags,
    RankingResult,
    ScoreBreakdown,
)
from src.config import (
    ALPHA,
    BETA,
    COHORT_MIN_REVIEWS,
    GAMMA,
    MAX_RESULTS_PER_BRAND,
    MAX_RESULTS_PER_CATEGORY,
)


def default_ranking_config() -> RankingConfig:
    return RankingConfig(
        mixing=MixingWeights(alpha=ALPHA, beta=BETA, gamma=GAMMA),
        flags=RankingFlags(),
    )


def _final_score(
    content: float,
    cohort: float,
    quality: float,
    cohort_used: bool,
    config: RankingConfig,
) -> float:
    from engine.types import ScoreBreakdown

    return compute_final_score(
        ScoreBreakdown(
            skin_match=0.0,
            concern_match=0.0,
            text_similarity=0.0,
            content_score=content,
            cohort_score=cohort,
            quality_score=quality,
            final_score=0.0,
            cohort_used=cohort_used,
        ),
        config,
    )


TextSimilarityFn = Callable[[BeautyProfile, np.ndarray], np.ndarray]


def _rank_eligible(
    profile: BeautyProfile,
    artifacts: ArtifactBundle,
    *,
    content_weights: ContentWeights | None = None,
    ranking_config: RankingConfig | None = None,
    text_similarity_fn: TextSimilarityFn | None = None,
) -> tuple[list[int], list[tuple[float, RankedProduct]]]:
    catalog = artifacts.catalog
    eligible_indices, _ = filter_catalog(catalog, profile)
    if not eligible_indices:
        return [], []

    config = ranking_config or default_ranking_config()
    eligible_products = [catalog[index] for index in eligible_indices]
    eligible_index_array = np.array(eligible_indices)
    if text_similarity_fn is not None:
        text_similarities = text_similarity_fn(profile, eligible_index_array)
    else:
        profile_vector = artifacts.tfidf_model.transform(build_profile_text(profile))
        text_similarities = artifacts.text_similarities(profile_vector)[eligible_index_array]

    skin_scores, concern_scores, text_scores, content_scores = score_content_components(
        eligible_products,
        profile,
        text_similarities,
        weights=content_weights,
    )

    catalog_mean_rating = float(artifacts.meta.get("catalog_mean_rating", 4.0))
    cohort_stats = artifacts.meta.get("cohort_stats")

    ranked_rows: list[tuple[float, RankedProduct]] = []
    for local_index, product in enumerate(eligible_products):
        cohort_value, cohort_used = cohort_score_for_product(
            product,
            profile.skin_type,
            cohort_stats,
            COHORT_MIN_REVIEWS,
        )
        quality_value = quality_score(product, catalog_mean_rating)
        content_value = float(content_scores[local_index])
        final_value = _final_score(
            content_value,
            cohort_value,
            quality_value,
            cohort_used,
            config,
        )

        breakdown = ScoreBreakdown(
            skin_match=float(skin_scores[local_index]),
            concern_match=float(concern_scores[local_index]),
            text_similarity=float(text_scores[local_index]),
            content_score=content_value,
            cohort_score=cohort_value,
            quality_score=quality_value,
            final_score=final_value,
            cohort_used=cohort_used,
        )
        ranked = RankedProduct(
            product_id=str(product["product_id"]),
            product_name=str(product["product_name"]),
            brand=str(product["brand"]),
            price_usd=float(product["price_usd"]),
            rating=float(product["rating"]) if product.get("rating") is not None else None,
            review_count=int(product.get("review_count") or 0),
            secondary_category=str(product.get("secondary_category") or ""),
            tertiary_category=str(product.get("tertiary_category") or ""),
            derived_concerns=tuple(product.get("derived_concerns") or ()),
            derived_benefits=tuple(product.get("derived_benefits") or ()),
            suited_skin_types=tuple(product.get("suited_skin_types") or ()),
            breakdown=breakdown,
        )
        ranked = attach_explanation(
            profile,
            ranked,
            content_weights=content_weights,
            ranking_config=config,
        )
        ranked_rows.append((final_value, ranked))

    ranked_rows.sort(key=lambda row: row[0], reverse=True)
    return eligible_indices, ranked_rows


def rank_product_ids(
    profile: BeautyProfile,
    artifacts: ArtifactBundle,
    *,
    content_weights: ContentWeights | None = None,
    ranking_config: RankingConfig | None = None,
    text_similarity_fn: TextSimilarityFn | None = None,
) -> list[str]:
    _, ranked_rows = _rank_eligible(
        profile,
        artifacts,
        content_weights=content_weights,
        ranking_config=ranking_config,
        text_similarity_fn=text_similarity_fn,
    )
    return [row[1].product_id for row in ranked_rows]


def rank_products(
    profile: BeautyProfile,
    artifacts: ArtifactBundle,
    *,
    top_k: int = 10,
    content_weights: ContentWeights | None = None,
    ranking_config: RankingConfig | None = None,
    text_similarity_fn: TextSimilarityFn | None = None,
) -> RankingResult:
    catalog = artifacts.catalog
    eligible_indices, ranked_rows = _rank_eligible(
        profile,
        artifacts,
        content_weights=content_weights,
        ranking_config=ranking_config,
        text_similarity_fn=text_similarity_fn,
    )

    if not eligible_indices:
        relaxations = _suggest_relaxations(profile)
        return RankingResult(
            items=[],
            candidate_count=0,
            filtered_count=len(catalog),
            relaxations=relaxations,
        )

    # When the shopper already filtered to one category, do not also cap
    # category frequency — brand diversity is still enforced hard.
    items = _diversify_top_k(
        ranked_rows,
        top_k=top_k,
        max_per_brand=MAX_RESULTS_PER_BRAND,
        max_per_category=MAX_RESULTS_PER_CATEGORY,
        enforce_category_cap=not bool(profile.category),
    )
    return RankingResult(
        items=items,
        candidate_count=len(eligible_indices),
        filtered_count=len(catalog) - len(eligible_indices),
        relaxations=[],
    )


def _diversify_top_k(
    ranked_rows: list[tuple[float, RankedProduct]],
    *,
    top_k: int,
    max_per_brand: int,
    max_per_category: int,
    enforce_category_cap: bool = True,
) -> list[RankedProduct]:
    """Greedy diversity with a hard brand cap.

    Category caps apply on the first pass when ``enforce_category_cap`` is True.
    If top-k is not full, a second pass may relax the category cap only —
    brand caps are never exceeded.
    """
    selected: list[RankedProduct] = []
    brand_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}

    def _try_add(item: RankedProduct, *, use_category_cap: bool) -> bool:
        brand_key = item.brand.strip().lower()
        category_key = (item.tertiary_category or item.secondary_category).strip().lower()
        if brand_counts.get(brand_key, 0) >= max_per_brand:
            return False
        if (
            use_category_cap
            and category_key
            and category_counts.get(category_key, 0) >= max_per_category
        ):
            return False
        selected.append(item)
        brand_counts[brand_key] = brand_counts.get(brand_key, 0) + 1
        if category_key:
            category_counts[category_key] = category_counts.get(category_key, 0) + 1
        return True

    for _, item in ranked_rows:
        if len(selected) >= top_k:
            break
        _try_add(item, use_category_cap=enforce_category_cap)

    if len(selected) < top_k and enforce_category_cap:
        selected_ids = {item.product_id for item in selected}
        for _, item in ranked_rows:
            if len(selected) >= top_k:
                break
            if item.product_id in selected_ids:
                continue
            if _try_add(item, use_category_cap=False):
                selected_ids.add(item.product_id)

    return selected


def _suggest_relaxations(profile: BeautyProfile) -> list[str]:
    suggestions: list[str] = []
    if profile.budget_max_usd < 9999:
        suggestions.append("Raise your budget.")
    if profile.exclusions:
        suggestions.append("Clear ingredient exclusions.")
    if profile.category:
        suggestions.append("Search all categories.")
    if not suggestions:
        suggestions.append("No products match the current profile.")
    return suggestions
