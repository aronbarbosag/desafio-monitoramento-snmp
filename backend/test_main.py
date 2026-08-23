"""Teste do app FastAPI em si (não de uma rota específica) — CORS é
middleware global, então não cabe em api/test_devices_controller.py."""

from fastapi.testclient import TestClient

from main import app


def test_cors_allows_configured_frontend_origin():
    with TestClient(app) as client:
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_rejects_origin_not_in_allowlist():
    with TestClient(app) as client:
        response = client.get("/health", headers={"Origin": "http://evil.example"})

    assert "access-control-allow-origin" not in response.headers
