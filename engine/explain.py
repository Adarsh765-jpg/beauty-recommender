"""Evidence-gated product explanations for the Why-this panel."""

from __future__ import annotations

from dataclasses import replace

from engine.content_ranker import default_content_weights
from engine.scoring import compute_final_score
from engine.types import (
    BeautyProfile,
    ContentWeights,
    ExplanationReason,
    MixingWeights,
    ProductExplanation,
    RankedProduct,
    RankingConfig,
    RankingFlags,
    ScoreBreakdown,
    ScoreComponent,
)
from src.config import ALPHA, BETA, GAMMA

MIN_TEXT_SIMILARITY_FOR_CLAIM = 0.20
MIN_COHORT_SCORE_FOR_CLAIM = 0.55
MIN_QUALITY_SCORE_FOR_CLAIM = 0.80
MIN_REVIEWS_FOR_QUALITY_CLAIM = 20


def _default_ranking_config() -> RankingConfig:
    return RankingConfig(
        mixing=MixingWeights(alpha=ALPHA, beta=BETA, gamma=GAMMA),
        flags=RankingFlags(),
    )


CONCERN_DISPLAY: dict[str, str] = {
    "hydration": "hydration",
    "acne_oil_control": "acne and oil control",
    "brightening": "brightening",
    "barrier_support": "barrier support",
    "anti_aging": "anti-aging",
}

SKIN_TYPE_DISPLAY: dict[str, str] = {
    "combination": "combination",
    "dry": "dry",
    "normal": "normal",
    "oily": "oily",
}


def _display_concern(concern: str) -> str:
    return CONCERN_DISPLAY.get(concern, concern.replace("_", " "))


def _display_skin_type(skin_type: str) -> str:
    return SKIN_TYPE_DISPLAY.get(skin_type, skin_type.replace("_", " "))


def build_score_components(
    breakdown: ScoreBreakdown,
    *,
    content_weights: ContentWeights,
    ranking_config: RankingConfig,
) -> tuple[ScoreComponent, ...]:
    mixing = ranking_config.mixing
    flags = ranking_config.flags
    weights = content_weights.normalized()
    components: list[ScoreComponent] = []

    if flags.use_content:
        components.extend(
            [
                ScoreComponent(
                    key="skin_match",
                    label="Skin type fit",
                    raw_score=breakdown.skin_match,
                    weight=mixing.alpha * weights.w_skin,
                    contribution=mixing.alpha * weights.w_skin * breakdown.skin_match,
                ),
                ScoreComponent(
                    key="concern_match",
                    label="Concern overlap",
                    raw_score=breakdown.concern_match,
                    weight=mixing.alpha * weights.w_concern,
                    contribution=mixing.alpha * weights.w_concern * breakdown.concern_match,
                ),
                ScoreComponent(
                    key="text_similarity",
                    label="Profile text match",
                    raw_score=breakdown.text_similarity,
                    weight=mixing.alpha * weights.w_text,
                    contribution=mixing.alpha * weights.w_text * breakdown.text_similarity,
                ),
            ]
        )

    if breakdown.cohort_used and flags.use_cohort:
        components.append(
            ScoreComponent(
                key="cohort_score",
                label="Skin-type cohort signal",
                raw_score=breakdown.cohort_score,
                weight=mixing.beta,
                contribution=mixing.beta * breakdown.cohort_score,
            )
        )

    if flags.use_quality:
        components.append(
            ScoreComponent(
                key="quality_score",
                label="Review quality",
                raw_score=breakdown.quality_score,
                weight=mixing.gamma,
                contribution=mixing.gamma * breakdown.quality_score,
            )
        )
    return tuple(components)


def _skin_reason(profile: BeautyProfile, product: RankedProduct) -> ExplanationReason | None:
    if profile.skin_type not in product.suited_skin_types:
        return None
    if product.breakdown.skin_match < 1.0:
        return None

    skin_label = _display_skin_type(profile.skin_type)
    highlights = ", ".join(product.suited_skin_types)
    return ExplanationReason(
        claim_id="skin_suitability",
        message=f"Marked as suitable for {skin_label} skin",
        evidence=(
            f"skin_type={profile.skin_type}",
            f"suited_skin_types={highlights}",
            f"skin_match={product.breakdown.skin_match:.2f}",
        ),
    )


def _concern_reasons(
    profile: BeautyProfile,
    product: RankedProduct,
) -> tuple[ExplanationReason, ...]:
    if not profile.concerns:
        return ()

    overlap = sorted(set(profile.concerns) & set(product.derived_concerns))
    if not overlap:
        return ()

    reasons: list[ExplanationReason] = []
    for concern in overlap:
        label = _display_concern(concern)
        reasons.append(
            ExplanationReason(
                claim_id=f"concern_{concern}",
                message=f"Targets your {label} goals",
                evidence=(
                    f"user_concern={concern}",
                    f"derived_concerns={','.join(product.derived_concerns)}",
                    f"concern_match={product.breakdown.concern_match:.2f}",
                ),
            )
        )
    return tuple(reasons)


def _text_reason(product: RankedProduct) -> ExplanationReason | None:
    text_score = product.breakdown.text_similarity
    if text_score < MIN_TEXT_SIMILARITY_FOR_CLAIM:
        return None

    return ExplanationReason(
        claim_id="text_similarity",
        message="Description aligns with your profile keywords",
        evidence=(f"text_similarity={text_score:.2f}",),
    )


def _cohort_reason(profile: BeautyProfile, product: RankedProduct) -> ExplanationReason | None:
    if not product.breakdown.cohort_used:
        return None
    if product.breakdown.cohort_score < MIN_COHORT_SCORE_FOR_CLAIM:
        return None

    skin_label = _display_skin_type(profile.skin_type)
    rate_pct = round(product.breakdown.cohort_score * 100)
    return ExplanationReason(
        claim_id="cohort_prior",
        message=f"Recommended by {skin_label} skin reviewers ({rate_pct}% positive signal)",
        evidence=(
            f"skin_type={profile.skin_type}",
            f"cohort_score={product.breakdown.cohort_score:.2f}",
            "cohort_used=true",
        ),
    )


def _quality_reason(product: RankedProduct) -> ExplanationReason | None:
    if product.review_count < MIN_REVIEWS_FOR_QUALITY_CLAIM:
        return None
    if product.rating is None:
        return None
    if product.breakdown.quality_score < MIN_QUALITY_SCORE_FOR_CLAIM:
        return None

    return ExplanationReason(
        claim_id="review_quality",
        message=f"Strong reviews ({product.rating:.1f}★ from {product.review_count:,} ratings)",
        evidence=(
            f"rating={product.rating:.2f}",
            f"review_count={product.review_count}",
            f"quality_score={product.breakdown.quality_score:.2f}",
        ),
    )


def build_reasons(profile: BeautyProfile, product: RankedProduct) -> tuple[ExplanationReason, ...]:
    reasons: list[ExplanationReason] = []

    skin = _skin_reason(profile, product)
    if skin is not None:
        reasons.append(skin)

    reasons.extend(_concern_reasons(profile, product))

    text = _text_reason(product)
    if text is not None:
        reasons.append(text)

    cohort = _cohort_reason(profile, product)
    if cohort is not None:
        reasons.append(cohort)

    quality = _quality_reason(product)
    if quality is not None:
        reasons.append(quality)

    return tuple(reasons)


def explain_product(
    profile: BeautyProfile,
    product: RankedProduct,
    *,
    content_weights: ContentWeights | None = None,
    ranking_config: RankingConfig | None = None,
) -> ProductExplanation:
    resolved_weights = content_weights or default_content_weights()
    resolved_config = ranking_config or _default_ranking_config()
    components = build_score_components(
        product.breakdown,
        content_weights=resolved_weights,
        ranking_config=resolved_config,
    )
    reasons = build_reasons(profile, product)
    expected_final = compute_final_score(product.breakdown, resolved_config)
    return ProductExplanation(
        reasons=reasons,
        components=components,
        final_score=expected_final,
        cohort_used=product.breakdown.cohort_used and resolved_config.flags.use_cohort,
    )


def components_total(explanation: ProductExplanation) -> float:
    return sum(component.contribution for component in explanation.components)


def reason_has_evidence(
    profile: BeautyProfile,
    product: RankedProduct,
    reason: ExplanationReason,
) -> bool:
    if reason.claim_id == "skin_suitability":
        return _skin_reason(profile, product) is not None
    if reason.claim_id.startswith("concern_"):
        concern = reason.claim_id.removeprefix("concern_")
        return concern in profile.concerns and concern in product.derived_concerns
    if reason.claim_id == "text_similarity":
        return _text_reason(product) is not None
    if reason.claim_id == "cohort_prior":
        return _cohort_reason(profile, product) is not None
    if reason.claim_id == "review_quality":
        return _quality_reason(product) is not None
    return False


def validate_explanation(
    profile: BeautyProfile,
    product: RankedProduct,
    explanation: ProductExplanation,
    *,
    ranking_config: RankingConfig | None = None,
    score_tolerance: float = 1e-5,
) -> None:
    resolved_config = ranking_config or _default_ranking_config()
    if abs(explanation.final_score - product.breakdown.final_score) > score_tolerance:
        raise ValueError(
            "explanation final_score does not match ranked product breakdown final_score"
        )

    if explanation.cohort_used != (
        product.breakdown.cohort_used and resolved_config.flags.use_cohort
    ):
        raise ValueError("explanation cohort_used flag does not match active cohort term")

    total = components_total(explanation)
    if abs(total - explanation.final_score) > score_tolerance:
        raise ValueError(
            f"component contributions ({total:.6f}) do not sum to final_score "
            f"({explanation.final_score:.6f})"
        )

    has_cohort_component = any(
        component.key == "cohort_score" for component in explanation.components
    )
    if explanation.cohort_used != has_cohort_component:
        raise ValueError("cohort component presence must match cohort_used flag")

    for reason in explanation.reasons:
        if not reason_has_evidence(profile, product, reason):
            raise ValueError(f"unsupported claim emitted: {reason.claim_id}")
        if not reason.evidence:
            raise ValueError(f"claim {reason.claim_id} missing evidence")


def attach_explanation(
    profile: BeautyProfile,
    product: RankedProduct,
    *,
    content_weights: ContentWeights | None = None,
    ranking_config: RankingConfig | None = None,
) -> RankedProduct:
    explanation = explain_product(
        profile,
        product,
        content_weights=content_weights,
        ranking_config=ranking_config,
    )
    validate_explanation(profile, product, explanation, ranking_config=ranking_config)
    return replace(product, explanation=explanation)


def explanation_to_dict(explanation: ProductExplanation) -> dict[str, object]:
    return {
        "final_score": explanation.final_score,
        "cohort_used": explanation.cohort_used,
        "reasons": [
            {
                "claim_id": reason.claim_id,
                "message": reason.message,
                "evidence": list(reason.evidence),
            }
            for reason in explanation.reasons
        ],
        "components": [
            {
                "key": component.key,
                "label": component.label,
                "raw_score": component.raw_score,
                "weight": component.weight,
                "contribution": component.contribution,
            }
            for component in explanation.components
        ],
    }
