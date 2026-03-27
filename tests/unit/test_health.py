"""Tests for pjx.health — health check endpoints."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pjx.config import PJXConfig
from pjx.health import health_routes


@pytest.fixture()
def health_app(tmp_path: Path):
    """Create a FastAPI app with health endpoints."""
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    app = FastAPI()
    config = PJXConfig(template_dirs=[tpl_dir])
    health_routes(app, config)
    return TestClient(app)


class TestHealthEndpoints:
    def test_health_returns_ok(self, health_app: TestClient) -> None:
        response = health_app.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_ready_with_existing_dirs(self, health_app: TestClient) -> None:
        response = health_app.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert all(data["checks"].values())

    def test_ready_with_missing_dir(self, tmp_path: Path) -> None:
        app = FastAPI()
        config = PJXConfig(template_dirs=[tmp_path / "nonexistent"])
        health_routes(app, config)
        client = TestClient(app)
        response = client.get("/ready")
        data = response.json()
        assert data["status"] == "not_ready"
