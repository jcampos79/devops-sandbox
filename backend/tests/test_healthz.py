"""Smoke test for the Phase 1 skeleton -- confirms the app boots and the
health endpoint responds. Expand per-phase in Phase 2+ (see README Roadmap)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
