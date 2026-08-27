"""Recommendation orchestration for the HTTP API."""

from __future__ import annotations

from typing import Literal

from backend.schemas import (
    ExplanationResponse,
    RecommendedProductResponse,
    RecommendRequest,
    RecommendResponse,
    ScoreBreakdownResponse,
)
from engine.artifacts import ArtifactBundle, get_artifacts
from engine.explain import explanation_to_dict
from engine.ranking import rank_products
from engine.types import BeautyProfile, RankedProduct


class ArtifactsUnavailableError(RuntimeError):
    """Raised when runtime artifacts are missing on disk."""


def _require_artifacts() -> ArtifactBundle:
    try:
        return get_artifacts()
    except FileNotFoundError as exc:
        raise ArtifactsUnavailableError(str(exc)) from exc


def _to_profile(request: RecommendRequest) -> BeautyProfile:
    return BeautyProfile(
        skin_type=request.skin_type,
        concerns=tuple(request.concerns),
        exclusions=tuple(request.exclusions),
        budget_max_usd=request.budget_max_usd,
        category=request.category,
    )


def _serialize_product(item: RankedProduct) -> RecommendedProductResponse:
    breakdown = item.breakdown
    explanation_payload = (
        ExplanationResponse.model_validate(explanation_to_dict(item.explanation))
        if item.explanation is not None
        else None
    )
    return RecommendedProductResponse(
        product_id=item.product_id,
        product_name=item.product_name,
        brand=item.brand,
        price_usd=item.price_usd,
        rating=item.rating,
        review_count=item.review_count,
        secondary_category=item.secondary_category,
        tertiary_category=item.tertiary_category,
        derived_concerns=list(item.derived_concerns),
        derived_benefits=list(item.derived_benefits),
        suited_skin_types=list(item.suited_skin_types),
        scores=ScoreBreakdownResponse(
            skin_match=breakdown.skin_match,
            concern_match=breakdown.concern_match,
            text_similarity=breakdown.text_similarity,
            content_score=breakdown.content_score,
            cohort_score=breakdown.cohort_score,
            quality_score=breakdown.quality_score,
            final_score=breakdown.final_score,
            cohort_used=breakdown.cohort_used,
        ),
        explanation=explanation_payload,
    )


def recommend(request: RecommendRequest) -> RecommendResponse:
    artifacts = _require_artifacts()
    profile = _to_profile(request)
    result = rank_products(profile, artifacts, top_k=request.top_k)

    items = [_serialize_product(item) for item in result.items]
    status: Literal["ok", "no_match"] = "ok" if items else "no_match"

    return RecommendResponse(
        status=status,
        profile={
            "skin_type": profile.skin_type,
            "concerns": list(profile.concerns),
            "exclusions": list(profile.exclusions),
            "budget_max_usd": profile.budget_max_usd,
            "category": profile.category,
            "top_k": request.top_k,
        },
        items=items,
        candidate_count=result.candidate_count,
        filtered_count=result.filtered_count,
        relaxations=result.relaxations if not items else [],
    )
