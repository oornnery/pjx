"""Integration tests for pjx.integration — FastAPI + PJX."""

from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from pjx.integration import PJX


@pytest.fixture()
def tmp_app(tmp_path: Path) -> tuple[FastAPI, PJX, Path]:
    """Create a FastAPI app with PJX integration and temp templates."""
    tpl = tmp_path / "templates"
    tpl.mkdir()

    # Simple page template
    (tpl / "home.jinja").write_text("<h1>Welcome {{ name }}</h1>")

    # Component template
    (tpl / "greeting.jinja").write_text("<p>Hello {{ name }}</p>")

    app = FastAPI()
    from pjx.config import PJXConfig

    config = PJXConfig(template_dirs=[tpl])
    pjx = PJX(app, config=config)

    return app, pjx, tpl


class TestPageDecorator:
    def test_registers_route(self, tmp_app: tuple) -> None:
        app, pjx, _ = tmp_app

        @pjx.page("/", "home.jinja")
        def home(request: Request) -> dict:
            return {"name": "PJX"}

        routes = [r.path for r in app.routes]
        assert "/" in routes

    def test_renders_template(self, tmp_app: tuple) -> None:
        app, pjx, _ = tmp_app

        @pjx.page("/", "home.jinja")
        def home(request: Request) -> dict:
            return {"name": "PJX"}

        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Welcome PJX" in resp.text


class TestRenderManual:
    def test_render(self, tmp_app: tuple) -> None:
        _, pjx, _ = tmp_app
        result = pjx.render("greeting.jinja", {"name": "World"})
        assert "Hello World" in result

    def test_render_not_found(self, tmp_app: tuple) -> None:
        _, pjx, _ = tmp_app
        with pytest.raises(FileNotFoundError):
            pjx.render("missing.jinja", {})
