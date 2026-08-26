"""Phase 0 smoke tests: the API surface exists and is shaped as expected."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.index import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_is_namespaced_under_api() -> None:
    """Vercel does not strip the /api prefix, so an unprefixed route must 404."""
    assert client.get("/health").status_code == 404
