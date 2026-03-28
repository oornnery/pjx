"""Tests for pjx.static — static site generation."""

import json
from pathlib import Path
from unittest.mock import MagicMock


from pjx.handler import RouteHandler
from pjx.static import StaticGenerator, _interpolate_url, _is_static_route


class TestIsStaticRoute:
    def test_static_no_params(self) -> None:
        assert _is_static_route("/about") is True

    def test_static_root(self) -> None:
        assert _is_static_route("/") is True

    def test_dynamic_param(self) -> None:
        assert _is_static_route("/blog/{slug}") is False

    def test_catch_all(self) -> None:
        assert _is_static_route("/docs/{path:path}") is False


class TestInterpolateUrl:
    def test_single_param(self) -> None:
        assert _interpolate_url("/blog/{slug}", {"slug": "hello"}) == "/blog/hello"

    def test_multiple_params(self) -> None:
        result = _interpolate_url("/u/{user}/post/{id}", {"user": "alice", "id": "42"})
        assert result == "/u/alice/post/42"

    def test_catch_all_param(self) -> None:
        result = _interpolate_url("/docs/{path:path}", {"path": "api/v1"})
        assert result == "/docs/api/v1"


class TestStaticGenerator:
    def test_generate_static_route(self, tmp_path: Path) -> None:
        pjx = MagicMock()
        pjx.render.return_value = "<h1>About</h1>"

        entry = MagicMock()
        entry.url_pattern = "/about"
        entry.template = "pages/about.jinja"
        entry.is_api = False
        entry.handler_path = None

        gen = StaticGenerator(pjx, tmp_path)
        pages = gen.generate([entry])

        assert len(pages) == 1
        assert pages[0].url == "/about"
        output_file = tmp_path / "about" / "index.html"
        assert output_file.exists()
        assert output_file.read_text() == "<h1>About</h1>"

    def test_generate_root_route(self, tmp_path: Path) -> None:
        pjx = MagicMock()
        pjx.render.return_value = "<h1>Home</h1>"

        entry = MagicMock()
        entry.url_pattern = "/"
        entry.template = "pages/index.jinja"
        entry.is_api = False
        entry.handler_path = None

        gen = StaticGenerator(pjx, tmp_path)
        pages = gen.generate([entry])

        assert len(pages) == 1
        output_file = tmp_path / "index.html"
        assert output_file.exists()

    def test_skips_api_routes(self, tmp_path: Path) -> None:
        pjx = MagicMock()

        entry = MagicMock()
        entry.url_pattern = "/api/users"
        entry.is_api = True

        gen = StaticGenerator(pjx, tmp_path)
        pages = gen.generate([entry])
        assert len(pages) == 0

    def test_skips_dynamic_without_static_params(self, tmp_path: Path) -> None:
        pjx = MagicMock()

        entry = MagicMock()
        entry.url_pattern = "/blog/{slug}"
        entry.template = "pages/blog/[slug].jinja"
        entry.is_api = False
        entry.handler_path = None

        gen = StaticGenerator(pjx, tmp_path)
        pages = gen.generate([entry])
        assert len(pages) == 0

    def test_writes_manifest(self, tmp_path: Path) -> None:
        pjx = MagicMock()
        pjx.render.return_value = "<h1>Page</h1>"

        entry = MagicMock()
        entry.url_pattern = "/about"
        entry.template = "pages/about.jinja"
        entry.is_api = False
        entry.handler_path = None

        gen = StaticGenerator(pjx, tmp_path)
        gen.generate([entry])

        manifest_path = tmp_path / "_routes.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert manifest["version"] == 1
        assert len(manifest["routes"]) == 1

    def test_render_error_skips_page(self, tmp_path: Path) -> None:
        pjx = MagicMock()
        pjx.render.side_effect = Exception("render failed")

        entry = MagicMock()
        entry.url_pattern = "/broken"
        entry.template = "pages/broken.jinja"
        entry.is_api = False
        entry.handler_path = None

        gen = StaticGenerator(pjx, tmp_path)
        pages = gen.generate([entry])
        assert len(pages) == 0


class TestRouteHandlerStaticParams:
    def test_register_static_params(self) -> None:
        handler = RouteHandler()

        @handler.static_params
        def get_params():
            return [{"slug": "hello"}, {"slug": "world"}]

        assert handler._static_params_fn is get_params
        result = handler._static_params_fn()
        assert len(result) == 2
