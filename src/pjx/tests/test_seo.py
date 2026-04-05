import tempfile
from pathlib import Path

from pjx.seo import SitemapEntry, discover_pages, generate_robots, generate_sitemap


def test_generate_sitemap():
    entries = [
        SitemapEntry(loc="/", lastmod="2026-04-04", priority=1.0),
        SitemapEntry(loc="/about"),
    ]
    xml = generate_sitemap(entries, "https://example.com")
    assert '<?xml version="1.0"' in xml
    assert "<loc>https://example.com/</loc>" in xml
    assert "<loc>https://example.com/about</loc>" in xml
    assert "<priority>1.0</priority>" in xml


def test_generate_robots():
    txt = generate_robots("https://example.com")
    assert "User-agent: *" in txt
    assert "Sitemap: https://example.com/sitemap.xml" in txt


def test_generate_robots_with_disallow():
    txt = generate_robots("https://example.com", disallow=["/admin", "/api"])
    assert "Disallow: /admin" in txt
    assert "Disallow: /api" in txt


def test_discover_pages():
    with tempfile.TemporaryDirectory() as tmpdir:
        pages = Path(tmpdir) / "pages"
        pages.mkdir()
        (pages / "home.jinja").write_text("<h1>Home</h1>")
        (pages / "about.jinja").write_text("<h1>About</h1>")
        (pages / "404.jinja").write_text("<h1>404</h1>")

        users = pages / "users"
        users.mkdir()
        (users / "[id].jinja").write_text("<h1>User</h1>")

        entries = discover_pages(Path(tmpdir))

        locs = {e.loc for e in entries}
        assert "/" in locs
        assert "/about" in locs
        assert "/404" not in locs  # error pages skipped
        # dynamic routes skipped
        assert not any("[" in loc for loc in locs)
