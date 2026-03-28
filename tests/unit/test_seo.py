"""Tests for pjx.seo — sitemap, robots.txt, and metadata helpers."""

from pathlib import Path

from pjx.integration import SEO
from pjx.router import RouteEntry
from pjx.seo import (
    dict_to_seo,
    generate_robots,
    generate_sitemap,
    metadata,
    write_robots,
    write_sitemap,
)


def _route(url: str, *, is_api: bool = False) -> RouteEntry:
    """Create a minimal RouteEntry for testing."""
    return RouteEntry(
        url_pattern=url, template=f"{url.strip('/')}.jinja", is_api=is_api
    )


class TestGenerateSitemap:
    def test_basic_sitemap(self) -> None:
        routes = [_route("/"), _route("/about"), _route("/blog")]
        xml = generate_sitemap(routes, "https://example.com")

        assert '<?xml version="1.0"' in xml
        assert "<urlset" in xml
        assert "<loc>https://example.com/</loc>" in xml
        assert "<loc>https://example.com/about</loc>" in xml
        assert "<loc>https://example.com/blog</loc>" in xml

    def test_skips_api_routes(self) -> None:
        routes = [_route("/"), _route("/api/users", is_api=True)]
        xml = generate_sitemap(routes, "https://example.com")

        assert "<loc>https://example.com/</loc>" in xml
        assert "/api/users" not in xml

    def test_skips_dynamic_routes(self) -> None:
        routes = [_route("/"), _route("/blog/{slug}")]
        xml = generate_sitemap(routes, "https://example.com")

        assert "<loc>https://example.com/</loc>" in xml
        assert "{slug}" not in xml

    def test_homepage_priority(self) -> None:
        routes = [_route("/"), _route("/about")]
        xml = generate_sitemap(routes, "https://example.com")

        # Homepage gets 1.0, others get default 0.5
        assert "<priority>1.0</priority>" in xml
        assert "<priority>0.5</priority>" in xml

    def test_custom_defaults(self) -> None:
        routes = [_route("/about")]
        xml = generate_sitemap(
            routes,
            "https://example.com",
            default_changefreq="daily",
            default_priority=0.8,
        )

        assert "<changefreq>daily</changefreq>" in xml
        assert "<priority>0.8</priority>" in xml

    def test_trailing_slash_stripped(self) -> None:
        routes = [_route("/about")]
        xml = generate_sitemap(routes, "https://example.com/")

        assert "<loc>https://example.com/about</loc>" in xml


class TestGenerateRobots:
    def test_default_robots(self) -> None:
        txt = generate_robots()

        assert "User-agent: *" in txt
        assert "Disallow:" in txt

    def test_with_disallow(self) -> None:
        txt = generate_robots(disallow=["/admin", "/api"])

        assert "Disallow: /admin" in txt
        assert "Disallow: /api" in txt

    def test_with_allow(self) -> None:
        txt = generate_robots(allow=["/api/public"])

        assert "Allow: /api/public" in txt

    def test_with_sitemap(self) -> None:
        txt = generate_robots(sitemap_url="https://example.com/sitemap.xml")

        assert "Sitemap: https://example.com/sitemap.xml" in txt

    def test_custom_user_agent(self) -> None:
        txt = generate_robots(user_agent="Googlebot")

        assert "User-agent: Googlebot" in txt


class TestWriteSitemap:
    def test_writes_file(self, tmp_path: Path) -> None:
        routes = [_route("/"), _route("/about")]
        path = write_sitemap(routes, "https://example.com", tmp_path)

        assert path == tmp_path / "sitemap.xml"
        assert path.exists()
        content = path.read_text()
        assert "<loc>https://example.com/</loc>" in content

    def test_creates_directory(self, tmp_path: Path) -> None:
        output = tmp_path / "dist" / "public"
        routes = [_route("/")]
        path = write_sitemap(routes, "https://example.com", output)

        assert path.exists()


class TestWriteRobots:
    def test_writes_file(self, tmp_path: Path) -> None:
        path = write_robots(
            tmp_path,
            sitemap_url="https://example.com/sitemap.xml",
            disallow=["/admin"],
        )

        assert path == tmp_path / "robots.txt"
        assert path.exists()
        content = path.read_text()
        assert "Disallow: /admin" in content
        assert "Sitemap: https://example.com/sitemap.xml" in content


class TestMetadataDecorator:
    def test_marks_function(self) -> None:
        @metadata
        async def my_page():
            return {"seo": {"title": "Hello"}}

        assert my_page._pjx_metadata is True

    def test_preserves_function(self) -> None:
        @metadata
        def my_page():
            return {}

        assert callable(my_page)
        assert my_page() == {}


class TestDictToSeo:
    def test_converts_dict(self) -> None:
        seo = dict_to_seo({"title": "Hello", "description": "World"})

        assert isinstance(seo, SEO)
        assert seo.title == "Hello"
        assert seo.description == "World"

    def test_ignores_unknown_fields(self) -> None:
        seo = dict_to_seo({"title": "Hello", "unknown_field": "ignored"})

        assert seo.title == "Hello"
        assert not hasattr(seo, "unknown_field")

    def test_empty_dict(self) -> None:
        seo = dict_to_seo({})

        assert isinstance(seo, SEO)
        assert seo.title == ""
