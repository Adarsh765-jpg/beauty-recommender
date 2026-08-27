"""Build recommendation catalog artifacts from cleaned product data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import DATA_ARTIFACTS, DATA_INTERIM
from src.features.feature_engineering import build_catalog, catalog_summary
from src.features.validate_rules import (
    audit_exclusion_flags,
    validate_concern_rules,
    verify_text_excludes_ingredients,
)


def run_feature_engineering(
    *,
    products_path: Path | None = None,
    reviews_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    products_path = products_path or (DATA_INTERIM / "products_clean.parquet")
    reviews_path = reviews_path or (DATA_INTERIM / "reviews_clean.parquet")
    output_dir = output_dir or DATA_ARTIFACTS
    reports_dir = output_dir / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    products = pd.read_parquet(products_path)
    reviews = pd.read_parquet(reviews_path)

    catalog = build_catalog(products, skincare_only=True)
    summary = catalog_summary(catalog)
    rule_validation = validate_concern_rules(catalog, reviews)
    exclusion_audit = audit_exclusion_flags(catalog)
    text_audit = verify_text_excludes_ingredients(catalog)

    catalog_path = output_dir / "catalog.json"
    with catalog_path.open("w", encoding="utf-8") as handle:
        json.dump(catalog, handle, indent=2)

    validation_path = reports_dir / "rule_validation.json"
    validation_payload = {
        "concern_rules": rule_validation,
        "exclusion_audit": exclusion_audit,
        "text_field_audit": text_audit,
        "catalog_summary": summary,
    }
    with validation_path.open("w", encoding="utf-8") as handle:
        json.dump(validation_payload, handle, indent=2)

    return {
        "catalog_path": str(catalog_path),
        "validation_path": str(validation_path),
        "summary": summary,
        "rule_validation": validation_payload,
    }


def main() -> None:
    result = run_feature_engineering()
    print(json.dumps(result["summary"], indent=2))
    print(f"Wrote catalog to {result['catalog_path']}")
    print(f"Wrote validation report to {result['validation_path']}")


if __name__ == "__main__":
    main()
