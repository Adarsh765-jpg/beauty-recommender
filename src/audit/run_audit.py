"""Reproducible data audit for the Sephora skincare dataset."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import (
    COHORT_MIN_REVIEWS_CANDIDATES,
    DATA_AUDIT,
    DATA_RAW,
    DATA_SAMPLE,
    PRODUCT_INFO_FILENAME,
    REVIEWS_FILENAME,
    SKIN_TYPES,
    SKINCARE_PRIMARY_CATEGORY,
)

SKIN_KEYWORDS = (
    "dry skin",
    "oily skin",
    "combination skin",
    "normal skin",
    "all skin types",
    "for dry",
    "for oily",
    "for combination",
    "for normal",
    "dryness",
    "oil-free",
    "oil control",
)


def _pct(n: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(100.0 * n / total, 2)


def _missingness(series: pd.Series) -> dict[str, Any]:
    total = len(series)
    missing = int(series.isna().sum())
    empty = int(series.astype(str).str.strip().eq("").sum()) if total else 0
    return {
        "missing_count": missing,
        "missing_pct": _pct(missing, total),
        "empty_string_count": empty,
    }


def _load_products(raw_dir: Path) -> pd.DataFrame:
    return pd.read_csv(raw_dir / PRODUCT_INFO_FILENAME, low_memory=False)


def _load_reviews(raw_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_dir / REVIEWS_FILENAME, low_memory=False)
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])
    return df


def _skincare_products(products: pd.DataFrame) -> pd.DataFrame:
    return products.loc[products["primary_category"] == SKINCARE_PRIMARY_CATEGORY].copy()


def _normalize_skin_type(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower()


def _highlights_skin_signal(skincare: pd.DataFrame) -> dict[str, Any]:
    highlights = skincare["highlights"].fillna("").astype(str).str.lower()
    non_empty = highlights.str.strip().ne("")
    keyword_hits: dict[str, int] = {}
    for kw in SKIN_KEYWORDS:
        keyword_hits[kw] = int(highlights.str.contains(kw, regex=False).sum())

    any_skin_keyword = highlights.apply(lambda text: any(kw in text for kw in SKIN_KEYWORDS))
    top_highlights = skincare.loc[non_empty, "highlights"].value_counts().head(20).to_dict()
    return {
        "skincare_with_non_empty_highlights": int(non_empty.sum()),
        "skincare_with_any_skin_keyword_in_highlights": int(any_skin_keyword.sum()),
        "skin_keyword_hits": keyword_hits,
        "top_20_highlights_values": top_highlights,
    }


def _cohort_density(reviews: pd.DataFrame) -> dict[str, Any]:
    skin = _normalize_skin_type(reviews["skin_type"])
    valid = skin.isin(SKIN_TYPES)
    subset = reviews.loc[valid, ["product_id"]].copy()
    subset["skin_type"] = skin[valid].values

    cell_counts = (
        subset.groupby(["product_id", "skin_type"], observed=True)
        .size()
        .reset_index(name="review_count")
    )

    threshold_summary: dict[str, Any] = {}
    total_cells = len(cell_counts)
    for threshold in COHORT_MIN_REVIEWS_CANDIDATES:
        passing = cell_counts.loc[cell_counts["review_count"] >= threshold]
        threshold_summary[str(threshold)] = {
            "cells_meeting_threshold": len(passing),
            "cells_meeting_threshold_pct": _pct(len(passing), total_cells),
            "unique_products_with_any_skin_meeting_threshold": int(passing["product_id"].nunique()),
        }

    by_skin = (
        cell_counts.groupby("skin_type", observed=True)["review_count"]
        .agg(["count", "median", "mean", "max"])
        .round(3)
        .reset_index()
        .to_dict(orient="records")
    )

    return {
        "total_product_skin_type_cells": total_cells,
        "cell_count_distribution": {
            "min": int(cell_counts["review_count"].min()) if total_cells else 0,
            "median": float(cell_counts["review_count"].median()) if total_cells else 0.0,
            "mean": round(float(cell_counts["review_count"].mean()), 3) if total_cells else 0.0,
            "max": int(cell_counts["review_count"].max()) if total_cells else 0,
        },
        "threshold_summary": threshold_summary,
        "cells_by_skin_type": by_skin,
    }


def _is_recommended_analysis(reviews: pd.DataFrame) -> dict[str, Any]:
    total = len(reviews)
    present = reviews["is_recommended"].notna()
    present_count = int(present.sum())
    subset = reviews.loc[present].copy()
    recommended = subset["is_recommended"].astype(float).eq(1.0)
    rating_fallback = reviews.loc[~present, "rating"] >= 4

    agreement_mask = present & reviews["rating"].notna()
    agree = reviews.loc[agreement_mask, "is_recommended"].astype(float).eq(1.0) == (
        reviews.loc[agreement_mask, "rating"] >= 4
    )
    return {
        "is_recommended_present_count": present_count,
        "is_recommended_present_pct": _pct(present_count, total),
        "is_recommended_true_count": int(recommended.sum()),
        "is_recommended_true_pct_of_present": _pct(int(recommended.sum()), present_count),
        "missing_is_recommended_count": int((~present).sum()),
        "rating_gte_4_when_is_recommended_missing": int(rating_fallback.sum()),
        "rating_vs_is_recommended_agreement_pct": _pct(int(agree.sum()), int(agreement_mask.sum())),
    }


def run_audit(raw_dir: Path = DATA_RAW) -> dict[str, Any]:
    products = _load_products(raw_dir)
    reviews = _load_reviews(raw_dir)
    skincare = _skincare_products(products)

    skincare_ids = set(skincare["product_id"].astype(str))
    review_product_ids = set(reviews["product_id"].astype(str))
    reviewed_skincare_ids = skincare_ids & review_product_ids
    skincare_without_reviews = skincare_ids - review_product_ids

    reviews_per_reviewer = reviews.groupby("author_id").size()
    reviews_per_product = reviews.groupby("product_id").size()

    join = reviews.merge(
        skincare[["product_id", "primary_category", "secondary_category"]],
        on="product_id",
        how="left",
        suffixes=("", "_product"),
    )

    skin_normalized = _normalize_skin_type(reviews["skin_type"])
    skin_counts = skin_normalized.value_counts(dropna=False).to_dict()

    price = skincare["price_usd"].dropna()

    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "source_files": {
            PRODUCT_INFO_FILENAME: {
                "path": str(raw_dir / PRODUCT_INFO_FILENAME),
                "size_bytes": (raw_dir / PRODUCT_INFO_FILENAME).stat().st_size,
            },
            REVIEWS_FILENAME: {
                "path": str(raw_dir / REVIEWS_FILENAME),
                "size_bytes": (raw_dir / REVIEWS_FILENAME).stat().st_size,
            },
        },
        "products": {
            "row_count": len(products),
            "column_count": len(products.columns),
            "columns": list(products.columns),
            "duplicate_product_id_count": int(products["product_id"].duplicated().sum()),
            "skincare_row_count": len(skincare),
            "primary_category_counts": products["primary_category"]
            .value_counts(dropna=False)
            .to_dict(),
            "missingness": {
                "ingredients": _missingness(products["ingredients"]),
                "highlights": _missingness(products["highlights"]),
                "price_usd": _missingness(products["price_usd"]),
                "rating": _missingness(products["rating"]),
            },
            "skincare_missingness": {
                "ingredients": _missingness(skincare["ingredients"]),
                "highlights": _missingness(skincare["highlights"]),
            },
            "price_usd_distribution_skincare": {
                "count": int(price.count()),
                "min": float(price.min()) if len(price) else None,
                "p25": float(price.quantile(0.25)) if len(price) else None,
                "median": float(price.median()) if len(price) else None,
                "p75": float(price.quantile(0.75)) if len(price) else None,
                "p90": float(price.quantile(0.90)) if len(price) else None,
                "max": float(price.max()) if len(price) else None,
                "mean": round(float(price.mean()), 2) if len(price) else None,
            },
            "highlights_skin_signal": _highlights_skin_signal(skincare),
        },
        "reviews": {
            "row_count": len(reviews),
            "column_count": len(reviews.columns),
            "columns": list(reviews.columns),
            "skin_type_distribution_raw": skin_counts,
            "skin_type_distribution_normalized": {
                k: int(v)
                for k, v in _normalize_skin_type(reviews["skin_type"])
                .value_counts(dropna=False)
                .items()
            },
            "observed_skin_types_excluding_nan": sorted(
                set(_normalize_skin_type(reviews["skin_type"]).dropna().unique()) - {"nan"}
            ),
            "rating_distribution": reviews["rating"]
            .value_counts(dropna=False)
            .sort_index()
            .to_dict(),
            "is_recommended": _is_recommended_analysis(reviews),
            "unique_reviewer_count": int(reviews["author_id"].nunique()),
            "reviews_per_reviewer": {
                "median": float(reviews_per_reviewer.median()),
                "mean": round(float(reviews_per_reviewer.mean()), 3),
                "max": int(reviews_per_reviewer.max()),
            },
            "reviews_per_product": {
                "median": float(reviews_per_product.median()),
                "mean": round(float(reviews_per_product.mean()), 3),
                "max": int(reviews_per_product.max()),
            },
            "product_skin_type_density": _cohort_density(reviews),
        },
        "join_coverage": {
            "skincare_product_count": len(skincare_ids),
            "reviewed_skincare_product_count": len(reviewed_skincare_ids),
            "skincare_products_without_reviews_in_subset": len(skincare_without_reviews),
            "review_rows_joined_to_skincare_catalog_pct": _pct(
                int(join["primary_category"].eq(SKINCARE_PRIMARY_CATEGORY).sum()),
                len(reviews),
            ),
            "review_product_ids_not_in_full_catalog_count": len(
                review_product_ids - set(products["product_id"].astype(str))
            ),
        },
        "spec_comparison": {},
    }

    spec = {
        "total_products_8494": report["products"]["row_count"] == 8494,
        "skincare_products_2420": report["products"]["skincare_row_count"] == 2420,
        "review_rows_49977": report["reviews"]["row_count"] == 49977,
        "reviewed_skincare_1104": report["join_coverage"]["reviewed_skincare_product_count"]
        == 1104,
        "skincare_no_reviews_1316": report["join_coverage"][
            "skincare_products_without_reviews_in_subset"
        ]
        == 1316,
        "is_recommended_present_pct_92_4": abs(
            report["reviews"]["is_recommended"]["is_recommended_present_pct"] - 92.4
        )
        < 0.5,
        "ingredients_missing_pct_11_1": abs(
            report["products"]["missingness"]["ingredients"]["missing_pct"] - 11.1
        )
        < 1.0,
        "highlights_missing_pct_26_0": abs(
            report["products"]["missingness"]["highlights"]["missing_pct"] - 26.0
        )
        < 1.0,
        "median_reviews_per_reviewer_1": report["reviews"]["reviews_per_reviewer"]["median"] == 1.0,
        "mean_reviews_per_reviewer_1_28": abs(
            report["reviews"]["reviews_per_reviewer"]["mean"] - 1.28
        )
        < 0.05,
    }
    report["spec_comparison"] = spec
    return report


def _render_markdown(report: dict[str, Any]) -> str:
    p = report["products"]
    r = report["reviews"]
    j = report["join_coverage"]
    spec = report["spec_comparison"]

    lines = [
        "# Sephora Dataset Audit",
        "",
        f"Generated: {report['generated_at_utc']}",
        "",
        "## Source files",
        "",
    ]
    for name, meta in report["source_files"].items():
        lines.append(f"- **{name}**: {meta['size_bytes']:,} bytes")

    lines.extend(
        [
            "",
            "## Products",
            "",
            f"- Total products: **{p['row_count']:,}**",
            f"- Skincare products (`primary_category == Skincare`): **{p['skincare_row_count']:,}**",
            f"- Duplicate product IDs: **{p['duplicate_product_id_count']}**",
            f"- Missing ingredients: **{p['missingness']['ingredients']['missing_pct']}%**",
            f"- Missing highlights: **{p['missingness']['highlights']['missing_pct']}%**",
            "",
            "### Skincare price (USD)",
            "",
            f"- Median: ${p['price_usd_distribution_skincare']['median']}",
            f"- p25–p75: ${p['price_usd_distribution_skincare']['p25']} – ${p['price_usd_distribution_skincare']['p75']}",
            f"- p90: ${p['price_usd_distribution_skincare']['p90']}",
            "",
            "## Reviews",
            "",
            f"- Review rows: **{r['row_count']:,}**",
            f"- Unique reviewers: **{r['unique_reviewer_count']:,}**",
            f"- Reviews per reviewer — median: **{r['reviews_per_reviewer']['median']}**, "
            f"mean: **{r['reviews_per_reviewer']['mean']}**, max: **{r['reviews_per_reviewer']['max']}**",
            f"- Reviews per product — median: **{r['reviews_per_product']['median']}**, "
            f"mean: **{r['reviews_per_product']['mean']}**, max: **{r['reviews_per_product']['max']}**",
            f"- `is_recommended` present: **{r['is_recommended']['is_recommended_present_pct']}%**",
            f"- Rating vs `is_recommended` agreement: **{r['is_recommended']['rating_vs_is_recommended_agreement_pct']}%**",
            "",
            "### Skin type distribution (normalized)",
            "",
        ]
    )
    for skin_type, count in sorted(r["skin_type_distribution_normalized"].items()):
        lines.append(f"- `{skin_type}`: {count:,}")

    lines.extend(
        [
            "",
            f"- Observed skin types (excluding NaN): {r['observed_skin_types_excluding_nan']}",
            "",
            "## Join coverage",
            "",
            f"- Skincare products: **{j['skincare_product_count']:,}**",
            f"- Skincare products with reviews in this file: **{j['reviewed_skincare_product_count']:,}**",
            f"- Skincare products without reviews in this file: **{j['skincare_products_without_reviews_in_subset']:,}**",
            "",
            "## Product × skin_type cohort density",
            "",
            f"- Total product–skin_type cells: **{r['product_skin_type_density']['total_product_skin_type_cells']:,}**",
            f"- Cell review count — median: **{r['product_skin_type_density']['cell_count_distribution']['median']}**, "
            f"max: **{r['product_skin_type_density']['cell_count_distribution']['max']}**",
            "",
            "### Threshold summary (cells meeting MIN_REVIEWS)",
            "",
            "| MIN_REVIEWS | cells | % of cells | products with ≥1 qualifying cell |",
            "|---|---:|---:|---:|",
        ]
    )
    for threshold, stats in r["product_skin_type_density"]["threshold_summary"].items():
        lines.append(
            f"| {threshold} | {stats['cells_meeting_threshold']:,} | "
            f"{stats['cells_meeting_threshold_pct']}% | "
            f"{stats['unique_products_with_any_skin_meeting_threshold']:,} |"
        )

    hs = p["highlights_skin_signal"]
    lines.extend(
        [
            "",
            "## Highlights skin-type signal (skincare only)",
            "",
            f"- Skincare rows with non-empty highlights: **{hs['skincare_with_non_empty_highlights']:,}**",
            f"- Skincare rows with any skin keyword in highlights: **{hs['skincare_with_any_skin_keyword_in_highlights']:,}**",
            "",
            "### Skin keyword hits in highlights",
            "",
        ]
    )
    for kw, count in sorted(hs["skin_keyword_hits"].items(), key=lambda x: -x[1]):
        if count:
            lines.append(f"- `{kw}`: {count}")

    lines.extend(["", "## Spec number comparison", ""])
    for key, matched in spec.items():
        status = "MATCH" if matched else "MISMATCH"
        lines.append(f"- `{key}`: **{status}**")

    return "\n".join(lines) + "\n"


def write_sample(raw_dir: Path = DATA_RAW, sample_dir: Path = DATA_SAMPLE) -> None:
    """Write a small reproducible slice for clone-without-download workflows."""
    sample_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)

    products = _load_products(raw_dir)
    skincare = _skincare_products(products)
    sample_products = skincare.sample(n=min(200, len(skincare)), random_state=42)
    sample_products.to_csv(sample_dir / PRODUCT_INFO_FILENAME, index=False)

    reviews = _load_reviews(raw_dir)
    skincare_ids = set(sample_products["product_id"].astype(str))
    subset = reviews.loc[reviews["product_id"].astype(str).isin(skincare_ids)]
    if len(subset) > 2000:
        subset = subset.sample(n=2000, random_state=int(rng.integers(0, 1_000_000)))
    subset.to_csv(sample_dir / REVIEWS_FILENAME, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Sephora dataset audit")
    parser.add_argument("--raw-dir", type=Path, default=DATA_RAW)
    parser.add_argument("--out-dir", type=Path, default=DATA_AUDIT)
    parser.add_argument("--write-sample", action="store_true")
    args = parser.parse_args()

    report = run_audit(args.raw_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    json_path = args.out_dir / "audit_report.json"
    md_path = args.out_dir / "audit_report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")

    print(f"wrote {json_path}")
    print(f"wrote {md_path}")

    if args.write_sample:
        write_sample(args.raw_dir)
        print(f"wrote sample files to {DATA_SAMPLE}")


if __name__ == "__main__":
    main()
