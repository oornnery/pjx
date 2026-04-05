from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SitemapEntry:
    loc: str
    lastmod: str | None = None
    changefreq: str | None = None
    priority: float | None = None


def generate_sitemap(
    entries: list[SitemapEntry],
    base_url: str,
) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    base = base_url.rstrip("/")

    for entry in entries:
        loc = entry.loc if entry.loc.startswith("http") else f"{base}{entry.loc}"
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        if entry.lastmod:
            lines.append(f"    <lastmod>{entry.lastmod}</lastmod>")
        if entry.changefreq:
            lines.append(f"    <changefreq>{entry.changefreq}</changefreq>")
        if entry.priority is not None:
            lines.append(f"    <priority>{entry.priority}</priority>")
        lines.append("  </url>")

    lines.append("</urlset>")
    return "\n".join(lines)


def generate_robots(
    base_url: str,
    disallow: list[str] | None = None,
    sitemap_path: str = "/sitemap.xml",
) -> str:
    base = base_url.rstrip("/")
    lines = [
        "User-agent: *",
    ]
    for path in disallow or []:
        lines.append(f"Disallow: {path}")
    if not disallow:
        lines.append("Disallow:")
    lines.append("")
    lines.append(f"Sitemap: {base}{sitemap_path}")
    return "\n".join(lines)


def discover_pages(
    templates_dir: Path,
    pages_prefix: str = "pages/",
) -> list[SitemapEntry]:
    entries: list[SitemapEntry] = []
    pages_path = templates_dir / pages_prefix.rstrip("/")

    if not pages_path.is_dir():
        return entries

    now = datetime.now(UTC).strftime("%Y-%m-%d")

    for file in sorted(pages_path.rglob("*.jinja")):
        rel = file.relative_to(pages_path)
        route = "/" + str(rel).replace("\\", "/")

        # Remove .jinja extension
        route = route.rsplit(".jinja", 1)[0]

        # Skip error pages
        if route.endswith("/404") or route.endswith("/500"):
            continue

        # Convert [slug] to skip (dynamic routes need manual entries)
        if "[" in route:
            continue

        # /index -> /
        if route.endswith("/index"):
            route = route[: -len("/index")] or "/"

        # home.jinja at root -> /
        name = rel.stem
        if str(rel.parent) == "." and name not in ("404", "500"):
            route = "/" if name in ("home", "index") else f"/{name}"

        entries.append(SitemapEntry(loc=route, lastmod=now))

    return entries
