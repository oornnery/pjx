"""PJX assets — static file discovery and vendor management."""

from __future__ import annotations

import shutil
from pathlib import Path

from pjx.config import PJXConfig


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
