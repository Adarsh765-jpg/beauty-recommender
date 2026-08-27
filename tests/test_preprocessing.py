"""Tests for data preparation."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.config import DATA_RAW, SKIN_TYPES
from src.preprocessing.common import parse_ingredient_tokens, parse_stringified_list
from src.preprocessing.product_cleaning import clean_products
from src.preprocessing.review_cleaning import clean_reviews
from src.preprocessing.run_preprocessing import run_preprocessing


@pytest.fixture(scope="module")
def raw_products() -> pd.DataFrame:
    path = DATA_RAW / "product_info.csv"
    if not path.exists():
        pytest.skip("raw product file not present")
    return pd.read_csv(path, low_memory=False)


@pytest.fixture(scope="module")
def raw_reviews() -> pd.DataFrame:
    path = DATA_RAW / "skincare_products_reviews.csv"
    if not path.exists():
        pytest.skip("raw review file not present")
    return pd.read_csv(path, low_memory=False)


def test_parse_stringified_list_from_real_fragrance_product(raw_products: pd.DataFrame) -> None:
    row = raw_products.loc[raw_products["product_id"] == "P473671"].iloc[0]
    items = parse_stringified_list(row["ingredients"])
    assert len(items) >= 3
    assert any("Capri Eau de Parfum" in item for item in items)


def test_parse_ingredient_tokens_skips_variant_labels(raw_products: pd.DataFrame) -> None:
    row = raw_products.loc[raw_products["product_id"] == "P473671"].iloc[0]
    tokens = parse_ingredient_tokens(row["ingredients"])
    assert tokens
    assert not any(token.endswith(":") for token in tokens)
    assert any("Alcohol Denat" in token for token in tokens)


def test_clean_products_preserves_row_count(raw_products: pd.DataFrame) -> None:
    cleaned, report = clean_products(raw_products)
    assert report["output_rows"] == len(raw_products)
    assert report["dropped_rows"] == 0
    assert cleaned["product_id"].is_unique
    assert cleaned["ingredients_list"].map(len).gt(0).sum() > 0


def test_clean_reviews_drops_only_expected_duplicates(raw_reviews: pd.DataFrame) -> None:
    cleaned, report = clean_reviews(raw_reviews)
    assert report["drop_reasons"].get("duplicate_author_product_time", 0) == 9
    assert report["drop_reasons"].get("invalid_author_id", 0) == 3
    assert report["output_rows"] == len(raw_reviews) - 12
    assert set(cleaned["skin_type"].dropna().unique()).issubset(set(SKIN_TYPES))


def test_clean_reviews_normalizes_is_recommended(raw_reviews: pd.DataFrame) -> None:
    cleaned, _ = clean_reviews(raw_reviews)
    sample = cleaned["is_recommended"].dropna().head(20)
    assert sample.isin([True, False]).all()


def test_preprocessing_pipeline_reconciles(
    raw_products: pd.DataFrame, raw_reviews: pd.DataFrame
) -> None:
    _, product_report = clean_products(raw_products)
    _, review_report = clean_reviews(raw_reviews)

    product_drop_sum = sum(product_report["drop_reasons"].values())
    review_drop_sum = sum(review_report["drop_reasons"].values())

    assert product_report["input_rows"] - product_report["output_rows"] == product_drop_sum
    assert review_report["input_rows"] - review_report["output_rows"] == review_drop_sum


def test_run_preprocessing_writes_artifacts(
    tmp_path: Path, raw_products: pd.DataFrame, raw_reviews: pd.DataFrame
) -> None:
    raw_dir = tmp_path / "raw"
    interim_dir = tmp_path / "interim"
    raw_dir.mkdir()
    raw_products.to_csv(raw_dir / "product_info.csv", index=False)
    raw_reviews.to_csv(raw_dir / "skincare_products_reviews.csv", index=False)

    report = run_preprocessing(raw_dir, interim_dir)
    assert (interim_dir / "products_clean.parquet").exists()
    assert (interim_dir / "reviews_clean.parquet").exists()
    assert (interim_dir / "preprocessing_report.json").exists()
    assert report["reviews"]["output_rows"] == len(raw_reviews) - 12

    saved = json.loads((interim_dir / "preprocessing_report.json").read_text(encoding="utf-8"))
    assert saved["products"]["dropped_rows"] == 0
