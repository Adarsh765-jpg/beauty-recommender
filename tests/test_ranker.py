"""End-to-end ranker sanity checks on hand-built profiles."""

from __future__ import annotations

import pytest

from engine.artifacts import ArtifactBundle, load_artifacts
from engine.ranking import rank_products
from engine.types import BeautyProfile
from src.config import DATA_ARTIFACTS


@pytest.fixture(scope="module")
def artifacts() -> ArtifactBundle:
    if not (DATA_ARTIFACTS / "meta.json").exists():
        pytest.skip("artifacts not built yet")
    return load_artifacts()


def test_dry_hydration_profile_prefers_matching_products(artifacts: ArtifactBundle) -> None:
    profile = BeautyProfile(
        skin_type="dry",
        concerns=("hydration",),
        budget_max_usd=80.0,
        category="Moisturizers",
    )
    result = rank_products(profile, artifacts, top_k=5)
    assert result.candidate_count > 0
    assert len(result.items) > 0

    top = result.items[0]
    assert top.price_usd <= 80.0
    assert "hydration" in top.derived_concerns
    assert top.breakdown.final_score >= result.items[-1].breakdown.final_score


def test_oily_acne_profile_respects_fragrance_exclusion(artifacts: ArtifactBundle) -> None:
    profile = BeautyProfile(
        skin_type="oily",
        concerns=("acne_oil_control",),
        exclusions=("fragrance",),
        budget_max_usd=60.0,
    )
    result = rank_products(profile, artifacts, top_k=10)
    assert result.candidate_count > 0

    for item in result.items:
        product = artifacts.catalog[artifacts.id_to_index[item.product_id]]
        assert not product["exclusion_flags"].get("fragrance", False)
        assert item.price_usd <= 60.0


def test_impossible_budget_returns_empty_with_relaxation(artifacts: ArtifactBundle) -> None:
    profile = BeautyProfile(
        skin_type="combination",
        concerns=("brightening",),
        budget_max_usd=1.0,
    )
    result = rank_products(profile, artifacts, top_k=5)
    assert result.candidate_count == 0
    assert result.items == []
    assert result.relaxations


def test_results_respect_brand_diversity_cap(artifacts: ArtifactBundle) -> None:
    profile = BeautyProfile(
        skin_type="dry",
        concerns=("hydration",),
        budget_max_usd=9999.0,
    )
    result = rank_products(profile, artifacts, top_k=10)
    assert len(result.items) > 0
    brand_counts: dict[str, int] = {}
    for item in result.items:
        key = item.brand.strip().lower()
        brand_counts[key] = brand_counts.get(key, 0) + 1
    assert max(brand_counts.values()) <= 2


def test_category_filter_keeps_hard_brand_cap(artifacts: ArtifactBundle) -> None:
    profile = BeautyProfile(
        skin_type="dry",
        concerns=("hydration",),
        budget_max_usd=9999.0,
        category="Face Oils",
    )
    result = rank_products(profile, artifacts, top_k=10)
    if not result.items:
        pytest.skip("no face oil candidates")
    brand_counts: dict[str, int] = {}
    for item in result.items:
        key = item.brand.strip().lower()
        brand_counts[key] = brand_counts.get(key, 0) + 1
    assert max(brand_counts.values()) <= 2
    # Category filter skips the category frequency cap so top-k can fill.
    assert len(result.items) == min(10, result.candidate_count)
