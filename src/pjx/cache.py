"""Template compilation cache — mtime-based invalidation and asset collection."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TemplateCache:
    """Caches compiled template sources, CSS, assets, and props models.

    Uses file modification time (mtime) to decide when recompilation is needed.
    """

    def __init__(self) -> None:
        self._template_mtimes: dict[str, float] = {}
        self._compiled_sources: dict[str, str] = {}
        self._cached_css: dict[str, str | None] = {}
        self._cached_assets: dict[str, tuple] = {}
        self._props_models: dict[str, type[BaseModel]] = {}

    def is_stale(self, template: str, current_mtime: float) -> bool:
        """Return True if the template needs recompilation."""
        cached_mtime = self._template_mtimes.get(template)
        return cached_mtime != current_mtime or template not in self._compiled_sources

    def store(
        self,
        template: str,
        mtime: float,
        source: str,
        css: str | None,
        assets: tuple,
    ) -> None:
        """Store all compilation artifacts for a template."""
        self._compiled_sources[template] = source
        self._template_mtimes[template] = mtime
        self._cached_css[template] = css
        self._cached_assets[template] = assets

    def store_props_model(self, template: str, model: type[BaseModel]) -> None:
        """Cache a generated props validation model."""
        if template not in self._props_models:
            self._props_models[template] = model

    def get_source(self, template: str) -> str | None:
        """Return the compiled Jinja source, or None if not cached."""
        return self._compiled_sources.get(template)

    def has_source(self, template: str) -> bool:
        """Return True if a compiled source exists for this template."""
        return template in self._compiled_sources

    def get_props_model(self, template: str) -> type[BaseModel] | None:
        """Return the cached props model, or None."""
        return self._props_models.get(template)

    def collect_cached_assets(
        self,
        template: str,
        css_parts: list[str] | None,
        asset_collector: Any | None,
    ) -> None:
        """Re-collect CSS and assets from a previously compiled template."""
        cached_css = self._cached_css.get(template)
        if css_parts is not None and cached_css:
            css_parts.append(cached_css)
        if asset_collector is not None and template in self._cached_assets:
            for asset in self._cached_assets[template]:
                asset_collector.add(asset)
