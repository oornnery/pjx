"""Static site generation (SSG) — pre-render pages to HTML files.

Scans the route table, identifies static candidates, renders them,
and writes ``.html`` files to a build output directory.

Routes are static if:
- They have no dynamic segments (no ``{param}`` in the URL), OR
- A colocated handler defines ``@handler.static_params`` providing
  all parameter combinations.

ISR (Incremental Static Regeneration) is handled at runtime via the
``@cache(revalidate=N)`` decorator from ``pjx.caching``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pjx.integration import PJX
    from pjx.router import RouteEntry

logger = logging.getLogger("pjx")


@dataclass(frozen=True, slots=True)
class StaticPage:
    """A single pre-rendered page."""

    url: str
    output_path: Path
    template: str


class StaticGenerator:
    """Generates static HTML files from route entries.

    Args:
        pjx: PJX application instance (for rendering).
        output_dir: Directory to write HTML files into.
    """

    def __init__(self, pjx: PJX, output_dir: Path) -> None:
        self._pjx = pjx
        self._output_dir = output_dir

    def generate(self, routes: list[RouteEntry]) -> list[StaticPage]:
        """Generate static HTML files for all eligible routes.

        Returns:
            List of generated pages.
        """
        pages: list[StaticPage] = []

        for entry in routes:
            if entry.is_api:
                continue

            if _is_static_route(entry.url_pattern):
                page = self._render_static(entry.url_pattern, entry.template)
                if page:
                    pages.append(page)
            elif entry.handler_path:
                static_params = _load_static_params(entry.handler_path)
                if static_params:
                    for params in static_params:
                        url = _interpolate_url(entry.url_pattern, params)
                        page = self._render_static(url, entry.template, params)
                        if page:
                            pages.append(page)

        # Write manifest
        if pages:
            self._write_manifest(pages)

        return pages

    def _render_static(
        self,
        url: str,
        template: str,
        params: dict[str, Any] | None = None,
    ) -> StaticPage | None:
        """Render a single page to a static HTML file."""
        context: dict[str, Any] = params or {}

        try:
            html = str(self._pjx.render(template, context))
        except Exception:
            logger.warning("failed to render static page: %s", url, exc_info=True)
            return None

        # Compute output path
        output_path = self._url_to_path(url)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")

        logger.info("static %s → %s", url, output_path)

        return StaticPage(url=url, output_path=output_path, template=template)

    def _url_to_path(self, url: str) -> Path:
        """Convert a URL to an output file path."""
        if url == "/":
            return self._output_dir / "index.html"
        clean = url.strip("/")
        return self._output_dir / clean / "index.html"

    def _write_manifest(self, pages: list[StaticPage]) -> None:
        """Write a _routes.json manifest for deployment."""
        manifest = {
            "version": 1,
            "routes": [{"url": p.url, "file": str(p.output_path)} for p in pages],
        }
        manifest_path = self._output_dir / "_routes.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _is_static_route(url_pattern: str) -> bool:
    """Check if a URL pattern has no dynamic segments."""
    return "{" not in url_pattern


def _interpolate_url(pattern: str, params: dict[str, Any]) -> str:
    """Replace {param} placeholders with actual values."""
    url = pattern
    for key, value in params.items():
        url = url.replace(f"{{{key}}}", str(value))
        url = url.replace(f"{{{key}:path}}", str(value))
    return url


def _load_static_params(handler_path: Path) -> list[dict[str, Any]] | None:
    """Load static_params from a colocated handler file.

    Looks for ``handler.static_params_fn`` (set by ``@handler.static_params``).
    """
    import importlib.util

    try:
        spec = importlib.util.spec_from_file_location("_handler", handler_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        handler = getattr(module, "handler", None)
        if handler is None:
            return None
        fn = getattr(handler, "_static_params_fn", None)
        if fn is None:
            return None
        import asyncio
        import inspect

        if inspect.iscoroutinefunction(fn):
            return asyncio.run(fn())
        return fn()
    except Exception:
        logger.warning("failed to load static_params: %s", handler_path, exc_info=True)
        return None
