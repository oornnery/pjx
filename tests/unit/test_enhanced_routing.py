"""Tests for enhanced routing — not-found, parallel routes, pattern middleware."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from pjx.config import PJXConfig
from pjx.integration import PJX
from pjx.router import FileRouter


class TestNotFound:
    def test_finds_not_found_jinja(self, tmp_path: Path) -> None:
        """not-found.jinja is discovered walking up the directory tree."""
        pages = tmp_path / "pages"
        pages.mkdir()
        (pages / "not-found.jinja").write_text("<h1>404</h1>")
        sub = pages / "blog"
        sub.mkdir()
        (sub / "index.jinja").write_text("---\n---\n<div>Blog</div>")

        tpl_dir = tmp_path
        router = FileRouter(pages, [tpl_dir])
        routes = router.scan()

        blog_route = [r for r in routes if r.url_pattern == "/blog"][0]
        assert blog_route.not_found is not None
        assert "not-found.jinja" in blog_route.not_found


class TestParallelRoutes:
    def test_detects_parallel_slots(self, tmp_path: Path) -> None:
        """@folder directories are detected as parallel route slots."""
        pages = tmp_path / "pages"
        pages.mkdir()
        dash = pages / "dashboard"
        dash.mkdir()
        (dash / "index.jinja").write_text("---\n---\n<div>Dashboard</div>")

        stats = dash / "@stats"
        stats.mkdir()
        (stats / "page.jinja").write_text("---\n---\n<div>Stats</div>")

        activity = dash / "@activity"
        activity.mkdir()
        (activity / "page.jinja").write_text("---\n---\n<div>Activity</div>")

        tpl_dir = tmp_path
        router = FileRouter(pages, [tpl_dir])
        routes = router.scan()

        dash_route = [r for r in routes if r.url_pattern == "/dashboard"][0]
        assert dash_route.parallel_slots is not None
        assert "stats" in dash_route.parallel_slots
        assert "activity" in dash_route.parallel_slots

    def test_parallel_folder_not_registered_as_route(self, tmp_path: Path) -> None:
        """@folder directories should NOT create their own routes."""
        pages = tmp_path / "pages"
        pages.mkdir()
        dash = pages / "dashboard"
        dash.mkdir()
        (dash / "index.jinja").write_text("---\n---\n<div>Dashboard</div>")

        stats = dash / "@stats"
        stats.mkdir()
        (stats / "page.jinja").write_text("---\n---\n<div>Stats</div>")

        tpl_dir = tmp_path
        router = FileRouter(pages, [tpl_dir])
        routes = router.scan()

        urls = [r.url_pattern for r in routes]
        # @stats should not create a /@stats route
        assert not any("@" in url for url in urls)


class TestPatternMiddleware:
    def test_pattern_middleware_runs(self, tmp_path: Path) -> None:
        tpl_dir = tmp_path / "templates"
        tpl_dir.mkdir()

        config = PJXConfig(template_dirs=[str(tpl_dir)])
        app = FastAPI()
        pjx = PJX(app, config=config)

        @pjx.middleware(pattern="/admin/*")
        async def admin_guard(request: Request):
            return JSONResponse({"error": "unauthorized"}, status_code=403)

        @pjx.page("/admin/settings", template="admin.jinja")
        async def admin_settings():
            return {"page": "settings"}

        # Create minimal template
        (tpl_dir / "admin.jinja").write_text("<div>Admin</div>")

        client = TestClient(app)
        response = client.get("/admin/settings")
        assert response.status_code == 403
        assert response.json() == {"error": "unauthorized"}

    def test_pattern_middleware_doesnt_match(self, tmp_path: Path) -> None:
        tpl_dir = tmp_path / "templates"
        tpl_dir.mkdir()

        config = PJXConfig(template_dirs=[str(tpl_dir)])
        app = FastAPI()
        pjx = PJX(app, config=config)

        @pjx.middleware(pattern="/admin/*")
        async def admin_guard(request: Request):
            return JSONResponse({"error": "unauthorized"}, status_code=403)

        @pjx.page("/public", template="public.jinja")
        async def public_page():
            return {}

        (tpl_dir / "public.jinja").write_text("<div>Public</div>")

        client = TestClient(app)
        response = client.get("/public")
        # Pattern doesn't match /public — middleware doesn't run
        assert response.status_code == 200

    def test_named_middleware_still_works(self, tmp_path: Path) -> None:
        tpl_dir = tmp_path / "templates"
        tpl_dir.mkdir()

        config = PJXConfig(template_dirs=[str(tpl_dir)])
        app = FastAPI()
        pjx = PJX(app, config=config)

        called = []

        @pjx.middleware(name="log")
        async def log_mw(request: Request):
            called.append("log")

        # Named middleware is registered and callable
        assert "log" in pjx._middleware_registry
