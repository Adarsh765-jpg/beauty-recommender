"""Tests for the evidence-gated explanation engine."""

from __future__ import annotations

import random

import pytest

from engine.artifacts import ArtifactBundle, load_artifacts
from engine.content_ranker import content_score, default_content_weights
from engine.explain import (
    build_reasons,
    components_total,
    explain_product,
    reason_has_evidence,
    validate_explanation,
)
from engine.ranking import rank_products
from engine.types import BeautyProfile, RankedProduct, ScoreBreakdown
from src.config import ALPHA, BETA, DATA_ARTIFACTS, GAMMA


@pytest.fixture(scope="module")
def artifacts() -> ArtifactBundle:
    if not (DATA_ARTIFACTS / "meta.json").exists():
        pytest.skip("artifacts not built yet")
    return load_artifacts()


def _synthetic_product(
    *,
    skin_match: float = 1.0,
    concern_match: float = 1.0,
    text_similarity: float = 0.4,
    cohort_score: float = 0.6,
    quality_score: float = 0.85,
    cohort_used: bool = True,
    rating: float = 4.5,
    review_count: int = 500,
    derived_concerns: tuple[str, ...] = ("hydration",),
    suited_skin_types: tuple[str, ...] = ("dry",),
) -> RankedProduct:
    weights = default_content_weights()
    content_value = content_score(skin_match, concern_match, text_similarity, weights)
    if cohort_used:
        final_score = ALPHA * content_value + BETA * cohort_score + GAMMA * quality_score
    else:
        final_score = ALPHA * content_value + GAMMA * quality_score

    breakdown = ScoreBreakdown(
        skin_match=skin_match,
        concern_match=concern_match,
        text_similarity=text_similarity,
        content_score=content_value,
        cohort_score=cohort_score,
        quality_score=quality_score,
        final_score=final_score,
        cohort_used=cohort_used,
    )
    return RankedProduct(
        product_id="PTEST",
        product_name="Test Serum",
        brand="Test Brand",
        price_usd=45.0,
        rating=rating,
        review_count=review_count,
        secondary_category="Serums",
        tertiary_category="Face Serums",
        derived_concerns=derived_concerns,
        derived_benefits=("hydration",),
        suited_skin_types=suited_skin_types,
        breakdown=breakdown,
    )


def test_components_sum_to_final_score() -> None:
    profile = BeautyProfile(skin_type="dry", concerns=("hydration",))
    product = _synthetic_product()
    explanation = explain_product(profile, product)
    validate_explanation(profile, product, explanation)
    assert components_total(explanation) == pytest.approx(explanation.final_score)


def test_no_skin_claim_without_explicit_suitability() -> None:
    profile = BeautyProfile(skin_type="dry", concerns=("hydration",))
    product = _synthetic_product(
        suited_skin_types=(),
        skin_match=0.5,
        cohort_used=False,
        cohort_score=0.0,
    )
    reasons = build_reasons(profile, product)
    assert all(reason.claim_id != "skin_suitability" for reason in reasons)


def test_no_concern_claim_without_overlap() -> None:
    profile = BeautyProfile(skin_type="dry", concerns=("brightening",))
    product = _synthetic_product(derived_concerns=("hydration",), concern_match=0.0)
    reasons = build_reasons(profile, product)
    assert all(not reason.claim_id.startswith("concern_") for reason in reasons)


def test_no_cohort_claim_when_not_used() -> None:
    profile = BeautyProfile(skin_type="dry", concerns=("hydration",))
    product = _synthetic_product(cohort_used=False, cohort_score=0.0)
    explanation = explain_product(profile, product)
    assert explanation.cohort_used is False
    assert all(component.key != "cohort_score" for component in explanation.components)
    assert all(reason.claim_id != "cohort_prior" for reason in explanation.reasons)


def test_every_reason_has_verifiable_evidence() -> None:
    profile = BeautyProfile(skin_type="dry", concerns=("hydration", "brightening"))
    product = _synthetic_product(
        derived_concerns=("hydration", "brightening"),
        suited_skin_types=("dry",),
    )
    explanation = explain_product(profile, product)
    for reason in explanation.reasons:
        assert reason.evidence
        assert reason_has_evidence(profile, product, reason)


def test_ranked_products_include_valid_explanations(artifacts: ArtifactBundle) -> None:
    profiles = [
        BeautyProfile(skin_type="dry", concerns=("hydration",), budget_max_usd=80.0),
        BeautyProfile(
            skin_type="oily",
            concerns=("acne_oil_control",),
            exclusions=("fragrance",),
            budget_max_usd=60.0,
        ),
        BeautyProfile(skin_type="combination", concerns=("brightening",), budget_max_usd=120.0),
    ]

    for profile in profiles:
        result = rank_products(profile, artifacts, top_k=8)
        assert result.items
        for item in result.items:
            assert item.explanation is not None
            validate_explanation(profile, item, item.explanation)


def test_sampled_catalog_explanations_are_faithful(artifacts: ArtifactBundle) -> None:
    rng = random.Random(19)
    sample_profiles = [
        BeautyProfile(skin_type=skin, concerns=concerns, budget_max_usd=budget)
        for skin, concerns, budget in [
            ("dry", ("hydration",), 100.0),
            ("oily", ("acne_oil_control",), 75.0),
            ("normal", ("anti_aging",), 120.0),
            ("combination", ("barrier_support", "hydration"), 90.0),
        ]
    ]

    for profile in sample_profiles:
        result = rank_products(profile, artifacts, top_k=5)
        if not result.items:
            continue
        item = rng.choice(result.items)
        assert item.explanation is not None
        validate_explanation(profile, item, item.explanation)
