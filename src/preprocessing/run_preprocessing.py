"""Run product and review cleaning and write interim artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import (
    DATA_INTERIM,
    DATA_RAW,
    PRODUCT_INFO_FILENAME,
    REVIEWS_FILENAME,
)
from src.preprocessing.common import merge_reports, save_reconciliation
from src.preprocessing.product_cleaning import clean_products
from src.preprocessing.review_cleaning import clean_reviews


def run_preprocessing(
    raw_dir: Path = DATA_RAW,
    interim_dir: Path = DATA_INTERIM,
) -> dict[str, Any]:
    products_raw = pd.read_csv(raw_dir / PRODUCT_INFO_FILENAME, low_memory=False)
    reviews_raw = pd.read_csv(raw_dir / REVIEWS_FILENAME, low_memory=False)

    products, product_report = clean_products(products_raw)
    reviews, review_report = clean_reviews(reviews_raw)

    interim_dir.mkdir(parents=True, exist_ok=True)

    products_path = interim_dir / "products_clean.parquet"
    reviews_path = interim_dir / "reviews_clean.parquet"
    products.to_parquet(products_path, index=False)
    reviews.to_parquet(reviews_path, index=False)

    reconciliation = {
        "products": product_report,
        "reviews": review_report,
        "combined_drop_reasons": merge_reports(
            product_report["drop_reasons"],
            review_report["drop_reasons"],
        ),
    }

    save_reconciliation(interim_dir / "preprocessing_report.json", reconciliation)
    return reconciliation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run data preparation pipeline")
    parser.add_argument("--raw-dir", type=Path, default=DATA_RAW)
    parser.add_argument("--interim-dir", type=Path, default=DATA_INTERIM)
    args = parser.parse_args()

    report = run_preprocessing(args.raw_dir, args.interim_dir)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
