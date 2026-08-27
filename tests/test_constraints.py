"""Hard constraint filtering must never be overridden by score."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from engine.artifacts import ArtifactBundle, load_artifacts
from engine.constraints import _category_matches, filter_catalog, passes_constraints
from engine.ranking import rank_products
from engine.types import BeautyProfile
from src.config import DATA_ARTIFACTS


@pytest.fixture(scope="module")
def artifacts() -> ArtifactBundle:
    if not (DATA_ARTIFACTS / "meta.json").exists():
        pytest.skip("artifacts not built yet")
    return load_artifacts()


def _find_product(
    catalog: list[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
) -> dict[str, Any]:
    for product in catalog:
        if predicate(product):
            return product
    raise AssertionError("no matching product found")


def test_budget_constraint_is_absolute(artifacts: ArtifactBundle) -> None:
    expensive = _find_product(artifacts.catalog, lambda p: float(p["price_usd"]) > 150)
    profile = BeautyProfile(
        skin_type="dry",
        concerns=("hydration",),
        budget_max_usd=30.0,
    )
    assert passes_constraints(expensive, profile) is False


def test_fragrance_exclusion_is_absolute(artifacts: ArtifactBundle) -> None:
    fragranced = _find_product(
        artifacts.catalog,
        lambda p: (p.get("exclusion_flags") or {}).get("fragrance", False),
    )
    profile = BeautyProfile(
        skin_type="normal",
        exclusions=("fragrance",),
        budget_max_usd=500.0,
    )
    assert passes_constraints(fragranced, profile) is False


def test_filtered_products_never_appear_in_results(artifacts: ArtifactBundle) -> None:
    profile = BeautyProfile(
        skin_type="oily",
        concerns=("acne_oil_control",),
        exclusions=("fragrance",),
        budget_max_usd=40.0,
        category="Moisturizers",
    )
    result = rank_products(profile, artifacts, top_k=20)
    _eligible, rejected = filter_catalog(artifacts.catalog, profile)
    returned_ids = {item.product_id for item in result.items}

    for index in rejected:
        assert artifacts.catalog[index]["product_id"] not in returned_ids

    for item in result.items:
        product = artifacts.catalog[artifacts.id_to_index[item.product_id]]
        assert passes_constraints(product, profile)


def test_out_of_stock_never_returned(artifacts: ArtifactBundle) -> None:
    out_of_stock = next((p for p in artifacts.catalog if p.get("out_of_stock")), None)
    if out_of_stock is None:
        pytest.skip("no out_of_stock products in catalog")

    profile = BeautyProfile(
        skin_type="dry",
        budget_max_usd=float(out_of_stock["price_usd"]) + 10,
    )
    result = rank_products(profile, artifacts, top_k=50)
    assert out_of_stock["product_id"] not in {item.product_id for item in result.items}


def test_cleansers_alias_includes_face_wash(artifacts: ArtifactBundle) -> None:
    face_wash = next(
        (
            p
            for p in artifacts.catalog
            if str(p.get("tertiary_category") or "") == "Face Wash & Cleansers"
            and not p.get("out_of_stock")
            and float(p.get("price_usd") or 0) > 0
        ),
        None,
    )
    if face_wash is None:
        pytest.skip("no in-stock face wash products in catalog")
    profile = BeautyProfile(
        skin_type="normal",
        budget_max_usd=9999.0,
        category="Cleansers",
    )
    assert _category_matches(face_wash, "Cleansers") is True
    assert passes_constraints(face_wash, profile) is True


def test_toners_alias_includes_mists(artifacts: ArtifactBundle) -> None:
    mist = next(
        (
            p
            for p in artifacts.catalog
            if str(p.get("tertiary_category") or "") == "Mists & Essences"
            and not p.get("out_of_stock")
            and float(p.get("price_usd") or 0) > 0
        ),
        None,
    )
    if mist is None:
        pytest.skip("no mists products in catalog")
    assert _category_matches(mist, "Toners") is True
