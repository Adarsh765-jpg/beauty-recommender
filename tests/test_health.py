"""Phase 0 smoke tests: the API surface exists and is shaped as expected."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["received_path"] == "/api/health"


def test_unmatched_route_reports_received_path() -> None:
    """An unmatched path must identify itself rather than 404 silently."""
    response = client.get("/health")
    assert response.status_code == 404

    body = response.json()
    assert body["error"] == "no_route"
    assert body["received_path"] == "/health"
