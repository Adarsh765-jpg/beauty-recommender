"""Assemble recommendation-ready product records."""

from __future__ import annotations

from typing import Any, TypedDict

import pandas as pd

from src.features.ingredient_rules import derive_concerns, detect_exclusions
from src.features.skin_suitability import derive_suited_skin_types
from src.features.text_builder import build_product_text

CONCERN_LABELS: dict[str, str] = {
    "hydration": "Hydration",
    "acne_oil_control": "Acne & oil control",
    "brightening": "Brightening",
    "barrier_support": "Barrier support",
    "anti_aging": "Anti-aging",
}


class ProductRecord(TypedDict):
    product_id: str
    product_name: str
    brand: str
    primary_category: str
    secondary_category: str
    tertiary_category: str
    price_usd: float
    rating: float | None
    review_count: int
    loves_count: int
    ingredients: list[str]
    highlights: list[str]
    derived_concerns: list[str]
    derived_benefits: list[str]
    suited_skin_types: list[str]
    exclusion_flags: dict[str, bool]
    text: str
    out_of_stock: bool


def _safe_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if hasattr(value, "tolist"):
        converted = value.tolist()
        if isinstance(converted, list):
            return [str(item) for item in converted]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return []


def build_product_record(row: pd.Series) -> ProductRecord:
    ingredients = _safe_list(row.get("ingredients_list"))
    highlights = _safe_list(row.get("highlights_list"))
    concerns = derive_concerns(ingredients, highlights)

    return ProductRecord(
        product_id=str(row["product_id"]),
        product_name=str(row["product_name"]),
        brand=str(row["brand_name"]),
        primary_category=str(row.get("primary_category") or ""),
        secondary_category=str(row.get("secondary_category") or ""),
        tertiary_category=str(row.get("tertiary_category") or ""),
        price_usd=float(row["price_usd"]),
        rating=float(row["rating"]) if pd.notna(row.get("rating")) else None,
        review_count=int(row.get("reviews") or 0),
        loves_count=int(row.get("loves_count") or 0),
        ingredients=ingredients,
        highlights=highlights,
        derived_concerns=concerns,
        derived_benefits=[CONCERN_LABELS[c] for c in concerns if c in CONCERN_LABELS],
        suited_skin_types=derive_suited_skin_types(highlights),
        exclusion_flags=detect_exclusions(ingredients),
        text=build_product_text(
            product_name=str(row["product_name"]),
            brand_name=str(row["brand_name"]),
            primary_category=str(row.get("primary_category") or ""),
            secondary_category=str(row.get("secondary_category") or ""),
            tertiary_category=str(row.get("tertiary_category") or ""),
            highlights=highlights,
        ),
        out_of_stock=bool(row.get("out_of_stock", False)),
    )


def build_catalog(products: pd.DataFrame, skincare_only: bool = True) -> list[ProductRecord]:
    subset = products.loc[products["is_skincare"]].copy() if skincare_only else products.copy()
    return [build_product_record(row) for _, row in subset.iterrows()]


def catalog_summary(catalog: list[ProductRecord]) -> dict[str, Any]:
    if not catalog:
        return {"product_count": 0}

    concern_counts: dict[str, int] = {}
    skin_counts: dict[str, int] = {}
    with_text = 0
    with_concerns = 0
    with_skin = 0

    for record in catalog:
        if record["text"].strip():
            with_text += 1
        if record["derived_concerns"]:
            with_concerns += 1
        if record["suited_skin_types"]:
            with_skin += 1
        for concern in record["derived_concerns"]:
            concern_counts[concern] = concern_counts.get(concern, 0) + 1
        for skin in record["suited_skin_types"]:
            skin_counts[skin] = skin_counts.get(skin, 0) + 1

    return {
        "product_count": len(catalog),
        "with_non_empty_text": with_text,
        "with_derived_concerns": with_concerns,
        "with_suited_skin_types": with_skin,
        "concern_counts": concern_counts,
        "suited_skin_type_counts": skin_counts,
    }
