"""PJX assets — static file discovery, vendor management, and asset collection."""

from __future__ import annotations

import shutil
from pathlib import Path

from markupsafe import Markup

from pjx.ast_nodes import AssetDecl
from pjx.config import PJXConfig


class AssetCollector:
    """Collect, deduplicate, and render CSS/JS asset tags.

    Assets are rendered in insertion order. CSS is emitted before JS.
    Repeated declarations (same kind + path) are deduplicated.
    """

    def __init__(self) -> None:
        self._css: list[str] = []
        self._js: list[str] = []
        self._seen: set[tuple[str, str]] = set()

    def add(self, asset: AssetDecl) -> None:
        """Add an asset declaration. Duplicates are ignored."""
        key = (asset.kind, asset.path)
        if key in self._seen:
            return
        self._seen.add(key)
        if asset.kind == "css":
            self._css.append(asset.path)
        else:
            self._js.append(asset.path)

    def render_css(self) -> Markup:
        """Render ``<link>`` tags for all collected CSS assets."""
        tags = [f'<link rel="stylesheet" href="{p}" />' for p in self._css]
        return Markup("\n".join(tags))

    def render_js(self, *, module: bool = True) -> Markup:
        """Render ``<script>`` tags for all collected JS assets."""
        type_attr = ' type="module"' if module else ""
        tags = [f'<script src="{p}"{type_attr}></script>' for p in self._js]
        return Markup("\n".join(tags))

    def render(self) -> Markup:
        """Render both CSS and JS tags (CSS first)."""
        parts = []
        css = self.render_css()
        if css:
            parts.append(css)
        js = self.render_js()
        if js:
            parts.append(js)
        return Markup("\n".join(parts))


def discover_static_files(config: PJXConfig) -> list[Path]:
    """Discover all static files in the configured static directory.

    Args:
        config: PJX configuration.

    Returns:
        Sorted list of static file paths.
    """
    static_dir = config.static_dir
    if not static_dir.exists():
        return []
    return sorted(static_dir.rglob("*") if static_dir.is_dir() else [])


def copy_vendor_file(src: Path, config: PJXConfig) -> Path:
    """Copy a file into the vendor static directory.

    Args:
        src: Source file path.
        config: PJX configuration.

    Returns:
        Destination path.
    """
    dest_dir = config.vendor_static_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copy2(src, dest)
    return dest


def ensure_project_dirs(config: PJXConfig) -> list[Path]:
    """Create the standard PJX project directory structure.

    Args:
        config: PJX configuration.

    Returns:
        List of directories created.
    """
    dirs = [
        config.pages_dir,
        config.components_dir,
        config.layouts_dir,
        config.ui_dir,
        config.vendor_templates_dir,
        config.static_dir,
        config.vendor_static_dir,
        config.static_dir / "js",
        config.static_dir / "css",
    ]
    created = []
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        created.append(d)
    return created
