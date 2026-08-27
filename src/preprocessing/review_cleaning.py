"""Review table cleaning."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.config import SKIN_TYPES
from src.preprocessing.common import drop_report, normalize_id

VALID_SKIN_TYPES = set(SKIN_TYPES)


def _normalize_skin_type(value: object) -> str | None:
    if pd.isna(value):
        return None
    normalized = str(value).strip().lower()
    if normalized in VALID_SKIN_TYPES:
        return normalized
    return None


def _normalize_author_id(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text or not text.isdigit():
        return None
    return text


def _normalize_is_recommended(value: object) -> bool | None:
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric == 1.0:
            return True
        if numeric == 0.0:
            return False
        return None
    text = str(value).strip()
    try:
        numeric = float(text)
    except ValueError:
        return None
    if numeric == 1.0:
        return True
    if numeric == 0.0:
        return False
    return None


def clean_reviews(reviews: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return cleaned reviews and a reconciliation report."""
    input_rows = len(reviews)
    drops: dict[str, int] = {}
    df = reviews.copy()

    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    df["product_id"] = df["product_id"].map(normalize_id)
    missing_product = df["product_id"].eq("")
    drop_report("missing_product_id", int(missing_product.sum()), drops)
    df = df.loc[~missing_product].copy()

    missing_author = df["author_id"].map(_normalize_author_id).isna()
    drop_report("invalid_author_id", int(missing_author.sum()), drops)
    df = df.loc[~missing_author].copy()
    df["author_id"] = df["author_id"].map(_normalize_author_id).astype(str)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    invalid_rating = df["rating"].isna() | ~df["rating"].between(1, 5)
    drop_report("invalid_rating", int(invalid_rating.sum()), drops)
    df = df.loc[~invalid_rating].copy()
    df["rating"] = df["rating"].astype(int)

    df["is_recommended"] = df["is_recommended"].map(_normalize_is_recommended)
    df["skin_type"] = df["skin_type"].map(_normalize_skin_type)
    df["has_valid_skin_type"] = df["skin_type"].notna()

    df["submission_time"] = pd.to_datetime(df["submission_time"], errors="coerce")
    invalid_time = df["submission_time"].isna()
    drop_report("invalid_submission_time", int(invalid_time.sum()), drops)
    df = df.loc[~invalid_time].copy()

    duplicate_mask = df.duplicated(
        subset=["author_id", "product_id", "submission_time"], keep="first"
    )
    drop_report("duplicate_author_product_time", int(duplicate_mask.sum()), drops)
    df = df.loc[~duplicate_mask].copy()

    df["price_usd"] = pd.to_numeric(df["price_usd"], errors="coerce")

    df = df.reset_index(drop=True)

    report = {
        "input_rows": input_rows,
        "output_rows": len(df),
        "dropped_rows": input_rows - len(df),
        "drop_reasons": drops,
        "rows_with_is_recommended": int(df["is_recommended"].notna().sum()),
        "rows_with_valid_skin_type": int(df["has_valid_skin_type"].sum()),
        "rows_missing_skin_type": int((~df["has_valid_skin_type"]).sum()),
    }
    return df, report
