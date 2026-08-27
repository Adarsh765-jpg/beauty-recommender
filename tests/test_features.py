"""Tests for feature engineering and rule validation."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from engine.analyzer import tokenize
from src.config import DATA_INTERIM
from src.features.feature_engineering import build_product_record, catalog_summary
from src.features.ingredient_rules import derive_concerns, detect_exclusions
from src.features.run_features import run_feature_engineering
from src.features.skin_suitability import derive_suited_skin_types
from src.features.text_builder import build_product_text


@pytest.fixture(scope="module")
def cleaned_products() -> pd.DataFrame:
    path = DATA_INTERIM / "products_clean.parquet"
    if not path.exists():
        pytest.skip("cleaned products parquet not present")
    return pd.read_parquet(path)


def test_derive_concerns_from_hyaluronic_product(cleaned_products: pd.DataFrame) -> None:
    row = cleaned_products.loc[cleaned_products["product_id"] == "P442539"].iloc[0]
    concerns = derive_concerns(_tolist(row["ingredients_list"]), _tolist(row["highlights_list"]))
    assert "hydration" in concerns


def _tolist(value: object) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    if hasattr(value, "tolist"):
        raw = value.tolist()
        if isinstance(raw, list):
            return [str(item) for item in raw]
    raise TypeError(f"expected list-like value, got {type(value)!r}")


def test_detect_fragrance_exclusion(cleaned_products: pd.DataFrame) -> None:
    row = cleaned_products.loc[cleaned_products["product_id"] == "P473671"].iloc[0]
    flags = detect_exclusions(_tolist(row["ingredients_list"]))
    assert flags["fragrance"] is True


def test_derive_suited_skin_types_from_best_for_highlight() -> None:
    highlights = ["Best for Dry, Combo, Normal Skin", "Good for: Dryness"]
    suited = derive_suited_skin_types(highlights)
    assert "dry" in suited
    assert "combination" in suited
    assert "normal" in suited


def test_derive_suited_skin_types_ignores_negated_phrases() -> None:
    highlights = ["Not for oily skin types", "Avoid for oily users"]
    suited = derive_suited_skin_types(highlights)
    assert "oily" not in suited


def test_text_field_excludes_ingredient_blob(cleaned_products: pd.DataFrame) -> None:
    row = cleaned_products.loc[cleaned_products["product_id"] == "P473671"].iloc[0]
    text = build_product_text(
        product_name=str(row["product_name"]),
        brand_name=str(row["brand_name"]),
        primary_category=str(row["primary_category"]),
        secondary_category=str(row["secondary_category"]),
        tertiary_category=str(row["tertiary_category"]),
        highlights=_tolist(row["highlights_list"]),
    )
    assert "Alcohol Denat" not in text
    assert "Capri Eau de Parfum" not in text


def test_tokenizer_matches_engine_contract() -> None:
    tokens = tokenize("Best-for Dry Skin Serum with 2% Niacinamide")
    assert "niacinamide" in tokens
    assert "with" not in tokens


def test_run_feature_engineering_writes_artifacts(cleaned_products: pd.DataFrame) -> None:
    if not (DATA_INTERIM / "reviews_clean.parquet").exists():
        pytest.skip("cleaned reviews parquet not present")

    result = run_feature_engineering()
    catalog_path = Path(result["catalog_path"])
    validation_path = Path(result["validation_path"])

    assert catalog_path.exists()
    assert validation_path.exists()

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert len(catalog) == int(cleaned_products["is_skincare"].sum())
    assert result["summary"]["with_non_empty_text"] == len(catalog)

    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    assert validation["text_field_audit"]["passes"] is True
    assert validation["exclusion_audit"]["fragrance"]["recall"] >= 0.9


def test_catalog_record_shape(cleaned_products: pd.DataFrame) -> None:
    skincare = cleaned_products.loc[cleaned_products["is_skincare"]].iloc[0]
    record = build_product_record(skincare)
    assert record["product_id"]
    assert isinstance(record["derived_concerns"], list)
    assert isinstance(record["exclusion_flags"], dict)
    assert record["text"]

    summary = catalog_summary([record])
    assert summary["product_count"] == 1
