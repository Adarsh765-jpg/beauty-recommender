"""Product catalog cleaning."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.config import SKINCARE_PRIMARY_CATEGORY
from src.preprocessing.common import (
    drop_report,
    normalize_id,
    parse_highlights,
    parse_ingredient_tokens,
)

BOOL_COLUMNS = (
    "limited_edition",
    "new",
    "online_only",
    "out_of_stock",
    "sephora_exclusive",
)

TEXT_COLUMNS = (
    "product_name",
    "brand_name",
    "primary_category",
    "secondary_category",
    "tertiary_category",
    "size",
    "variation_type",
    "variation_value",
)


def clean_products(products: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return cleaned products and a reconciliation report."""
    input_rows = len(products)
    drops: dict[str, int] = {}
    df = products.copy()

    df["product_id"] = df["product_id"].map(normalize_id)
    missing_id = df["product_id"].eq("")
    drop_report("missing_product_id", int(missing_id.sum()), drops)
    df = df.loc[~missing_id].copy()

    duplicate_ids = df["product_id"].duplicated(keep="first")
    drop_report("duplicate_product_id", int(duplicate_ids.sum()), drops)
    df = df.loc[~duplicate_ids].copy()

    for column in TEXT_COLUMNS:
        if column in df.columns:
            df[column] = df[column].astype(str).str.strip()
            df.loc[df[column].eq("nan"), column] = pd.NA

    for column in BOOL_COLUMNS:
        if column in df.columns:
            df[column] = df[column].fillna(0).astype(int).astype(bool)

    df["price_usd"] = pd.to_numeric(df["price_usd"], errors="coerce")
    invalid_price = df["price_usd"].isna() | (df["price_usd"] <= 0)
    drop_report("invalid_price_usd", int(invalid_price.sum()), drops)
    df = df.loc[~invalid_price].copy()

    for column in ("value_price_usd", "sale_price_usd", "rating"):
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df["reviews"] = pd.to_numeric(df["reviews"], errors="coerce").fillna(0).astype(int)
    df["loves_count"] = pd.to_numeric(df["loves_count"], errors="coerce").fillna(0).astype(int)

    df["ingredients_list"] = df["ingredients"].map(parse_ingredient_tokens)
    df["highlights_list"] = df["highlights"].map(parse_highlights)
    df["is_skincare"] = df["primary_category"].eq(SKINCARE_PRIMARY_CATEGORY)

    df = df.reset_index(drop=True)

    report = {
        "input_rows": input_rows,
        "output_rows": len(df),
        "dropped_rows": input_rows - len(df),
        "drop_reasons": drops,
        "skincare_rows": int(df["is_skincare"].sum()),
        "rows_with_ingredients": int(df["ingredients_list"].map(len).gt(0).sum()),
        "rows_with_highlights": int(df["highlights_list"].map(len).gt(0).sum()),
    }
    return df, report
