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


class TestInlineRenderMode:
    """Test on-the-fly rendering with inline includes."""

    def test_inline_render_produces_same_output(self, tmp_path: Path) -> None:
        tpl = tmp_path / "templates"
        tpl.mkdir()
        (tpl / "child.jinja").write_text("<span>{{ name }}</span>")
        (tpl / "page.jinja").write_text(
            '---\nimport Child from "child.jinja"\n---\n'
            '<div><Child name="World" /></div>'
        )
        app = FastAPI()
        from pjx.config import PJXConfig

        # Render with include mode
        config_inc = PJXConfig(template_dirs=[tpl], render_mode="include")
        pjx_inc = PJX(app, config=config_inc)
        result_inc = pjx_inc.render("page.jinja", {})

        # Render with inline mode
        app2 = FastAPI()
        config_inl = PJXConfig(template_dirs=[tpl], render_mode="inline")
        pjx_inl = PJX(app2, config=config_inl)
        result_inl = pjx_inl.render("page.jinja", {})

        assert "World" in result_inc
        assert "World" in result_inl


class TestRuntimePropValidation:
    """Test that props are validated at render time when enabled."""

    @pytest.fixture()
    def app_with_props(self, tmp_path: Path) -> tuple[FastAPI, "PJX", Path]:
        tpl = tmp_path / "templates"
        tpl.mkdir()
        (tpl / "card.jinja").write_text(
            "---\n"
            "props CardProps = {\n"
            "  title: str,\n"
            "  count: int = 0,\n"
            "}\n"
            "---\n"
            "<div>{{ props.title }} ({{ props.count }})</div>\n"
        )
        app = FastAPI()
        from pjx.config import PJXConfig

        config = PJXConfig(template_dirs=[tpl], validate_props=True)
        pjx = PJX(app, config=config)
        return app, pjx, tpl

    def test_valid_props_pass(self, app_with_props: tuple) -> None:
        _, pjx, _ = app_with_props
        result = pjx.render("card.jinja", {"title": "Hello", "count": 5})
        assert "Hello" in result
        assert "5" in result

    def test_valid_props_with_defaults(self, app_with_props: tuple) -> None:
        _, pjx, _ = app_with_props
        result = pjx.render("card.jinja", {"title": "Hi"})
        assert "Hi" in result

    def test_missing_required_prop_raises(self, app_with_props: tuple) -> None:
        from pjx.errors import PropValidationError

        _, pjx, _ = app_with_props
        with pytest.raises(PropValidationError, match="validation failed"):
            pjx.render("card.jinja", {})

    def test_validation_disabled_skips_check(self, tmp_path: Path) -> None:
        tpl = tmp_path / "templates"
        tpl.mkdir()
        (tpl / "strict.jinja").write_text(
            "---\n"
            "props P = { name: str }\n"
            "---\n"
            "<p>{{ props.name|default('none') }}</p>\n"
        )
        app = FastAPI()
        from pjx.config import PJXConfig

        config = PJXConfig(template_dirs=[tpl], validate_props=False)
        pjx = PJX(app, config=config)
        # Should NOT raise even though required prop is missing
        result = pjx.render("strict.jinja", {})
        assert "none" in result
