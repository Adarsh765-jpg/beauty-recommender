"""Tests for skin-type cohort prior."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from engine.artifacts import load_artifacts
from engine.cohort_signal import cohort_score_for_product
from engine.ranking import _rank_eligible
from engine.types import BeautyProfile
from src.cohort.build_cohort_stats import build_cohort_stats, train_review_count
from src.config import COHORT_MIN_REVIEWS, DATA_ARTIFACTS, DATA_INTERIM, REPORTS_DIR
from src.evaluation.split import temporal_split


@pytest.fixture(scope="module")
def reviews_with_split() -> pd.DataFrame:
    path = DATA_INTERIM / "reviews_clean.parquet"
    if not path.exists():
        pytest.skip("cleaned reviews missing")
    return temporal_split(pd.read_parquet(path))


@pytest.fixture(scope="module")
def catalog_product_ids() -> set[str]:
    if not (DATA_ARTIFACTS / "catalog.json").exists():
        pytest.skip("catalog missing")
    catalog = json.loads((DATA_ARTIFACTS / "catalog.json").read_text(encoding="utf-8"))
    return {str(item["product_id"]) for item in catalog}


def test_cohort_stats_use_train_reviews_only(
    reviews_with_split: pd.DataFrame,
    catalog_product_ids: set[str],
) -> None:
    stats = build_cohort_stats(reviews_with_split, catalog_product_ids, split_name="train")
    val_rows = reviews_with_split.loc[reviews_with_split["split"] == "val"]
    sample = val_rows.loc[val_rows["has_valid_skin_type"]].iloc[0]

    product_id = str(sample["product_id"])
    skin_type = str(sample["skin_type"])
    expected_count = train_review_count(reviews_with_split, product_id, skin_type)
    actual_count = stats["cells"].get(product_id, {}).get(skin_type, {}).get("review_count", 0)
    assert actual_count == expected_count


def test_all_val_rows_use_train_only_counts(
    reviews_with_split: pd.DataFrame,
    catalog_product_ids: set[str],
) -> None:
    stats = build_cohort_stats(reviews_with_split, catalog_product_ids, split_name="train")
    val_rows = reviews_with_split.loc[reviews_with_split["split"] == "val"]

    checked = 0
    for _, row in val_rows.iterrows():
        if not row.get("has_valid_skin_type", False):
            continue
        product_id = str(row["product_id"])
        if product_id not in catalog_product_ids:
            continue
        skin_type = str(row["skin_type"])
        expected_count = train_review_count(reviews_with_split, product_id, skin_type)
        actual_count = stats["cells"].get(product_id, {}).get(skin_type, {}).get("review_count", 0)
        assert actual_count == expected_count
        checked += 1

    assert checked > 0


def test_cohort_fallback_when_insufficient_evidence() -> None:
    stats = {
        "cells": {
            "P1": {
                "dry": {"review_count": 2, "shrunk_rate": 0.95},
            }
        }
    }
    score, used = cohort_score_for_product(
        {"product_id": "P1"},
        "dry",
        stats,
        COHORT_MIN_REVIEWS,
    )
    assert score == 0.0
    assert used is False


def test_cohort_active_when_min_reviews_met() -> None:
    stats = {
        "cells": {
            "P1": {
                "dry": {"review_count": 10, "shrunk_rate": 0.82},
            }
        }
    }
    score, used = cohort_score_for_product(
        {"product_id": "P1"},
        "dry",
        stats,
        COHORT_MIN_REVIEWS,
    )
    assert score == pytest.approx(0.82)
    assert used is True


def test_ranking_uses_cohort_fallback_for_sparse_cell() -> None:
    if not (DATA_ARTIFACTS / "meta.json").exists():
        pytest.skip("artifacts missing")

    artifacts = load_artifacts()
    cohort_stats = artifacts.meta.get("cohort_stats") or {}
    sparse_product = None
    for product in artifacts.catalog:
        product_id = str(product["product_id"])
        for skin_type in ("combination", "dry", "normal", "oily"):
            cell = cohort_stats.get("cells", {}).get(product_id, {}).get(skin_type)
            if cell and int(cell["review_count"]) < COHORT_MIN_REVIEWS:
                sparse_product = (product_id, skin_type)
                break
        if sparse_product:
            break
    if sparse_product is None:
        pytest.skip("no sparse cohort cell found")

    product_id, skin_type = sparse_product
    product = artifacts.catalog[artifacts.id_to_index[product_id]]
    profile = BeautyProfile(skin_type=skin_type, budget_max_usd=9999.0)
    _, ranked_rows = _rank_eligible(profile, artifacts)
    matched = next(row[1] for row in ranked_rows if row[1].product_id == product_id)
    assert matched.breakdown.cohort_used is False
    assert matched.breakdown.cohort_score == 0.0
    _score, used = cohort_score_for_product(product, skin_type, cohort_stats, COHORT_MIN_REVIEWS)
    assert used is False


def test_ranking_uses_cohort_when_evidence_sufficient() -> None:
    if not (DATA_ARTIFACTS / "meta.json").exists():
        pytest.skip("artifacts missing")

    artifacts = load_artifacts()
    cohort_stats = artifacts.meta.get("cohort_stats") or {}
    if not cohort_stats.get("cells"):
        pytest.skip("cohort stats not built")

    rich_product = None
    for product_id, skin_map in cohort_stats["cells"].items():
        for skin_type, cell in skin_map.items():
            if int(cell["review_count"]) >= COHORT_MIN_REVIEWS:
                rich_product = (product_id, skin_type)
                break
        if rich_product:
            break
    assert rich_product is not None

    product_id, skin_type = rich_product
    profile = BeautyProfile(skin_type=skin_type, budget_max_usd=9999.0)
    _, ranked_rows = _rank_eligible(profile, artifacts)
    matched = next(row[1] for row in ranked_rows if row[1].product_id == product_id)
    assert matched.breakdown.cohort_used is True
    assert matched.breakdown.cohort_score > 0.0


def test_cohort_coverage_report_exists_after_build() -> None:
    report_path = REPORTS_DIR / "cohort_coverage.json"
    if not report_path.exists():
        pytest.skip("run build_artifacts to generate cohort coverage report")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["pairs_with_min_reviews"] > 0
    assert 0.0 < payload["fraction_with_min_reviews"] < 1.0
