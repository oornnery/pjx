"""SEO helpers — sitemap, robots.txt, and metadata decorator.

Generates ``sitemap.xml`` and ``robots.txt`` from the route table and
project configuration. The ``@metadata`` decorator simplifies per-page
SEO by merging handler return dicts with the ``seo`` key automatically.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import fields as dc_fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

from pjx.router import RouteEntry

logger = logging.getLogger("pjx")


def generate_sitemap(
    routes: list[RouteEntry],
    base_url: str,
    *,
    default_changefreq: str = "weekly",
    default_priority: float = 0.5,
) -> str:
    """Generate a ``sitemap.xml`` string from discovered routes.

    Args:
        routes: List of route entries from the file router.
        base_url: Base URL for the site (e.g. ``https://example.com``).
        default_changefreq: Default change frequency for all URLs.
        default_priority: Default priority for all URLs.

    Returns:
        XML string with the sitemap.
    """
    base_url = base_url.rstrip("/")

    urlset = Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for route in routes:
        # Skip API routes and dynamic routes (contain {param})
        if route.is_api:
            continue
        if "{" in route.url_pattern:
            continue

        url_el = SubElement(urlset, "url")
        loc = SubElement(url_el, "loc")
        loc.text = f"{base_url}{route.url_pattern}"

        lastmod = SubElement(url_el, "lastmod")
        lastmod.text = now

        changefreq = SubElement(url_el, "changefreq")
        changefreq.text = default_changefreq

        priority_el = SubElement(url_el, "priority")
        # Homepage gets higher priority
        if route.url_pattern == "/":
            priority_el.text = "1.0"
        else:
            priority_el.text = str(default_priority)

    xml_bytes = tostring(urlset, encoding="unicode", xml_declaration=False)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_bytes}\n'


def generate_robots(
    *,
    sitemap_url: str = "",
    disallow: list[str] | None = None,
    allow: list[str] | None = None,
    user_agent: str = "*",
) -> str:
    """Generate a ``robots.txt`` string.

    Args:
        sitemap_url: Full URL to the sitemap (e.g. ``https://example.com/sitemap.xml``).
        disallow: List of paths to disallow.
        allow: List of paths to explicitly allow.
        user_agent: User-agent directive. Defaults to ``*``.

    Returns:
        robots.txt content string.
    """
    lines: list[str] = [f"User-agent: {user_agent}"]

    for path in disallow or []:
        lines.append(f"Disallow: {path}")

    for path in allow or []:
        lines.append(f"Allow: {path}")

    if not disallow and not allow:
        lines.append("Disallow:")

    if sitemap_url:
        lines.append("")
        lines.append(f"Sitemap: {sitemap_url}")

    lines.append("")
    return "\n".join(lines)


def write_sitemap(
    routes: list[RouteEntry],
    base_url: str,
    output: Path,
    **kwargs: Any,
) -> Path:
    """Generate and write ``sitemap.xml`` to a file.

    Args:
        routes: Route entries from the file router.
        base_url: Base URL for the site.
        output: Directory to write the sitemap into.
        **kwargs: Extra arguments passed to ``generate_sitemap()``.

    Returns:
        Path to the written sitemap file.
    """
    output.mkdir(parents=True, exist_ok=True)
    sitemap_path = output / "sitemap.xml"
    content = generate_sitemap(routes, base_url, **kwargs)
    sitemap_path.write_text(content, encoding="utf-8")
    logger.info("sitemap → %s (%d routes)", sitemap_path, content.count("<url>"))
    return sitemap_path


def write_robots(
    output: Path,
    **kwargs: Any,
) -> Path:
    """Generate and write ``robots.txt`` to a file.

    Args:
        output: Directory to write robots.txt into.
        **kwargs: Arguments passed to ``generate_robots()``.

    Returns:
        Path to the written robots.txt file.
    """
    output.mkdir(parents=True, exist_ok=True)
    robots_path = output / "robots.txt"
    content = generate_robots(**kwargs)
    robots_path.write_text(content, encoding="utf-8")
    logger.info("robots  → %s", robots_path)
    return robots_path


def metadata(func: Callable) -> Callable:
    """Decorator that marks a page handler as providing SEO metadata.

    The handler's return dict is expected to contain an ``seo`` key with
    either an ``SEO`` dataclass or a plain dict. If a dict is provided,
    it is converted to an ``SEO`` instance automatically.

    This decorator is a no-op marker — the actual merging happens in
    ``PJX.render()`` via ``_merge_seo()``. The decorator simply sets
    a ``_pjx_metadata`` attribute so the framework can detect it.

    Args:
        func: The page handler function.

    Returns:
        The same function with ``_pjx_metadata = True`` set.
    """
    func._pjx_metadata = True  # type: ignore[attr-defined]
    return func


def dict_to_seo(data: dict[str, Any]) -> Any:
    """Convert a plain dict to an SEO dataclass instance.

    Args:
        data: Dict with SEO field names as keys.

    Returns:
        An SEO instance with the provided values.
    """
    from pjx.integration import SEO

    valid_fields = {f.name for f in dc_fields(SEO)}
    filtered = {k: v for k, v in data.items() if k in valid_fields}
    return SEO(**filtered)
