"""Integration tests for the evaluation harness."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from engine.artifacts import ArtifactBundle, load_artifacts
from src.config import DATA_ARTIFACTS, REPORTS_SMOKE_DIR
from src.evaluation.evaluate import run_evaluation
from src.evaluation.protocol import build_eval_instances
from src.evaluation.split import temporal_split, verify_no_temporal_overlap
from tests.conftest import require_clean_reviews


@pytest.fixture(scope="module")
def artifacts() -> ArtifactBundle:
    if not (DATA_ARTIFACTS / "meta.json").exists():
        pytest.skip("artifacts not built")
    return load_artifacts()


def test_random_baseline_integration_is_low(artifacts: ArtifactBundle) -> None:
    require_clean_reviews()

    REPORTS_SMOKE_DIR.mkdir(parents=True, exist_ok=True)
    result = run_evaluation(
        artifacts=artifacts,
        split_name="val",
        max_queries=100,
        seed=7,
        output_path=REPORTS_SMOKE_DIR / "evaluation_random_smoke.json",
    )

    clean_restricted = result["variants"]["clean__category_restricted"]
    random_metrics = clean_restricted["random"]

    assert random_metrics["hit_rate@10"] < 0.20
    assert random_metrics["mrr"] < 0.10


def test_evaluation_writes_report(artifacts: ArtifactBundle) -> None:
    require_clean_reviews()
    REPORTS_SMOKE_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_SMOKE_DIR / "evaluation_val_smoke.json"
    result = run_evaluation(
        artifacts=artifacts,
        split_name="val",
        max_queries=50,
        output_path=report_path,
    )
    assert report_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["queries"] == 50
    assert "clean__category_restricted" in payload["variants"]
    assert "content" in payload["variants"]["clean__category_restricted"]
    assert result["report_path"] == str(report_path)


def test_test_split_not_used_by_default_smoke(artifacts: ArtifactBundle) -> None:
    reviews_path = require_clean_reviews()
    reviews = temporal_split(pd.read_parquet(reviews_path))
    assert verify_no_temporal_overlap(reviews)

    catalog_by_id = {item["product_id"]: item for item in artifacts.catalog}
    val_instances = build_eval_instances(reviews, catalog_by_id, split="val")
    test_instances = build_eval_instances(reviews, catalog_by_id, split="test")
    assert len(val_instances) > 0
    assert len(test_instances) > 0

    val_indices = {item.review_index for item in val_instances}
    test_indices = {item.review_index for item in test_instances}
    assert val_indices.isdisjoint(test_indices)
