"""Tests for file-based router — URL generation, scanning, sorting."""

from __future__ import annotations

from pathlib import Path

from pjx.router import (
    FileRouter,
    RouteEntry,
    _convert_segment,
    _path_to_url,
    _sort_routes,
)


# ---------------------------------------------------------------------------
# _convert_segment
# ---------------------------------------------------------------------------


class TestConvertSegment:
    """Test individual path segment → URL segment conversion."""

    def test_static_segment(self) -> None:
        assert _convert_segment("about") == "about"

    def test_dynamic_segment(self) -> None:
        assert _convert_segment("[slug]") == "{slug}"

    def test_catch_all_segment(self) -> None:
        assert _convert_segment("[...path]") == "{path:path}"

    def test_route_group_stripped(self) -> None:
        assert _convert_segment("(auth)") is None

    def test_underscore_segment(self) -> None:
        assert _convert_segment("_private") == "_private"

    def test_numeric_dynamic(self) -> None:
        assert _convert_segment("[id]") == "{id}"


# ---------------------------------------------------------------------------
# _path_to_url
# ---------------------------------------------------------------------------


class TestPathToUrl:
    """Test full path → URL conversion."""

    def test_index_root(self) -> None:
        assert _path_to_url(Path("index.jinja"), is_api=False) == "/"

    def test_simple_page(self) -> None:
        assert _path_to_url(Path("about.jinja"), is_api=False) == "/about"

    def test_nested_index(self) -> None:
        assert _path_to_url(Path("blog/index.jinja"), is_api=False) == "/blog"

    def test_dynamic_segment(self) -> None:
        assert _path_to_url(Path("blog/[slug].jinja"), is_api=False) == "/blog/{slug}"

    def test_catch_all(self) -> None:
        assert (
            _path_to_url(Path("docs/[...path].jinja"), is_api=False)
            == "/docs/{path:path}"
        )

    def test_route_group(self) -> None:
        assert _path_to_url(Path("(auth)/login.jinja"), is_api=False) == "/login"

    def test_nested_route_group(self) -> None:
        assert (
            _path_to_url(Path("(dashboard)/settings/profile.jinja"), is_api=False)
            == "/settings/profile"
        )

    def test_api_route(self) -> None:
        assert _path_to_url(Path("api/users.py"), is_api=True) == "/api/users"

    def test_deep_dynamic(self) -> None:
        assert (
            _path_to_url(Path("shop/[category]/[id].jinja"), is_api=False)
            == "/shop/{category}/{id}"
        )


# ---------------------------------------------------------------------------
# Route sorting
# ---------------------------------------------------------------------------


class TestRouteSort:
    """Test route sorting — static before dynamic, catch-all last."""

    def _entry(self, url: str) -> RouteEntry:
        return RouteEntry(url_pattern=url, template="")

    def test_static_before_dynamic(self) -> None:
        routes = [self._entry("/blog/{slug}"), self._entry("/about")]
        sorted_routes = _sort_routes(routes)
        assert sorted_routes[0].url_pattern == "/about"
        assert sorted_routes[1].url_pattern == "/blog/{slug}"

    def test_catch_all_last(self) -> None:
        routes = [
            self._entry("/{path:path}"),
            self._entry("/blog/{slug}"),
            self._entry("/about"),
        ]
        sorted_routes = _sort_routes(routes)
        assert sorted_routes[0].url_pattern == "/about"
        assert sorted_routes[-1].url_pattern == "/{path:path}"

    def test_stable_order_for_same_type(self) -> None:
        routes = [self._entry("/beta"), self._entry("/alpha")]
        sorted_routes = _sort_routes(routes)
        assert sorted_routes[0].url_pattern == "/alpha"
        assert sorted_routes[1].url_pattern == "/beta"


# ---------------------------------------------------------------------------
# FileRouter.scan() with temporary directory
# ---------------------------------------------------------------------------


class TestFileRouterScan:
    """Test filesystem scanning."""

    def test_scan_empty_dir(self, tmp_path: Path) -> None:
        pages = tmp_path / "pages"
        pages.mkdir()
        router = FileRouter(pages, [tmp_path])
        routes = router.scan()
        assert routes == []

    def test_scan_nonexistent_dir(self, tmp_path: Path) -> None:
        router = FileRouter(tmp_path / "nonexistent", [tmp_path])
        routes = router.scan()
        assert routes == []

    def test_scan_simple_pages(self, tmp_path: Path) -> None:
        pages = tmp_path / "pages"
        pages.mkdir()
        (pages / "index.jinja").write_text("<h1>Home</h1>")
        (pages / "about.jinja").write_text("<h1>About</h1>")

        router = FileRouter(pages, [tmp_path])
        routes = router.scan()
        urls = {r.url_pattern for r in routes}
        assert "/" in urls
        assert "/about" in urls

    def test_scan_skips_special_files(self, tmp_path: Path) -> None:
        pages = tmp_path / "pages"
        pages.mkdir()
        (pages / "index.jinja").write_text("<h1>Home</h1>")
        (pages / "layout.jinja").write_text("<html>{{ body }}</html>")
        (pages / "loading.jinja").write_text("<p>Loading...</p>")
        (pages / "error.jinja").write_text("<p>Error</p>")
        (pages / "_private.jinja").write_text("<p>Private</p>")

        router = FileRouter(pages, [tmp_path])
        routes = router.scan()
        assert len(routes) == 1
        assert routes[0].url_pattern == "/"

    def test_scan_dynamic_segments(self, tmp_path: Path) -> None:
        pages = tmp_path / "pages"
        blog = pages / "blog"
        blog.mkdir(parents=True)
        (blog / "[slug].jinja").write_text("<h1>{{ slug }}</h1>")

        router = FileRouter(pages, [tmp_path])
        routes = router.scan()
        assert len(routes) == 1
        assert routes[0].url_pattern == "/blog/{slug}"

    def test_scan_layout_chain(self, tmp_path: Path) -> None:
        pages = tmp_path / "pages"
        sub = pages / "admin"
        sub.mkdir(parents=True)
        (pages / "layout.jinja").write_text("<html>root</html>")
        (sub / "layout.jinja").write_text("<div>admin</div>")
        (sub / "dashboard.jinja").write_text("<h1>Dashboard</h1>")

        router = FileRouter(pages, [tmp_path])
        routes = router.scan()
        assert len(routes) == 1
        entry = routes[0]
        assert len(entry.layout_chain) == 2
        # Root layout first, nested last
        assert "layout.jinja" in entry.layout_chain[0]

    def test_scan_route_groups(self, tmp_path: Path) -> None:
        pages = tmp_path / "pages"
        auth = pages / "(auth)"
        auth.mkdir(parents=True)
        (auth / "login.jinja").write_text("<h1>Login</h1>")

        router = FileRouter(pages, [tmp_path])
        routes = router.scan()
        assert len(routes) == 1
        assert routes[0].url_pattern == "/login"

    def test_scan_api_routes(self, tmp_path: Path) -> None:
        pages = tmp_path / "pages"
        api = pages / "api"
        api.mkdir(parents=True)
        (api / "users.py").write_text(
            "from pjx.handler import APIRoute\nroute = APIRoute()\n"
        )

        router = FileRouter(pages, [tmp_path])
        routes = router.scan()
        assert len(routes) == 1
        assert routes[0].url_pattern == "/api/users"
        assert routes[0].is_api is True

    def test_scan_error_and_loading(self, tmp_path: Path) -> None:
        pages = tmp_path / "pages"
        pages.mkdir()
        (pages / "index.jinja").write_text("<h1>Home</h1>")
        (pages / "loading.jinja").write_text("<p>Loading...</p>")
        (pages / "error.jinja").write_text("<p>Error</p>")

        router = FileRouter(pages, [tmp_path])
        routes = router.scan()
        assert len(routes) == 1
        entry = routes[0]
        assert entry.loading is not None
        assert entry.error is not None
