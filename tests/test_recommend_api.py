"""Tests for the /api/recommend contract."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from src.config import DATA_ARTIFACTS

client = TestClient(app)


@pytest.fixture(scope="module")
def require_artifacts() -> None:
    if not (DATA_ARTIFACTS / "meta.json").exists():
        pytest.skip("artifacts not built yet")


def test_recommend_returns_ranked_products(require_artifacts: None) -> None:
    response = client.post(
        "/api/recommend",
        json={
            "skin_type": "dry",
            "concerns": ["hydration"],
            "budget_max_usd": 80,
            "top_k": 5,
        },
    )
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["candidate_count"] > 0
    assert len(body["items"]) == 5
    assert body["items"][0]["explanation"] is not None
    assert body["items"][0]["scores"]["final_score"] >= body["items"][-1]["scores"]["final_score"]


def test_recommend_invalid_skin_type_returns_422() -> None:
    response = client.post(
        "/api/recommend",
        json={"skin_type": "sensitive", "concerns": [], "budget_max_usd": 50},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert isinstance(body["detail"], list)
    assert body["detail"][0]["field"] == "skin_type"


def test_recommend_no_match_returns_relaxations(require_artifacts: None) -> None:
    response = client.post(
        "/api/recommend",
        json={
            "skin_type": "combination",
            "concerns": ["brightening"],
            "budget_max_usd": 1,
            "top_k": 5,
        },
    )
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "no_match"
    assert body["items"] == []
    assert body["candidate_count"] == 0
    assert body["relaxations"]


def test_schema_endpoint_lists_supported_values() -> None:
    response = client.get("/api/schema")
    assert response.status_code == 200
    body = response.json()
    assert "dry" in body["skin_types"]
    assert "hydration" in body["concerns"]
    assert "fragrance" in body["exclusions"]


def test_health_reports_artifact_readiness(require_artifacts: None) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["artifacts_ready"] is True
