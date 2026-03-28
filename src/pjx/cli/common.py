"""Shared CLI utilities — config loading, validation, output."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from pjx.config import PJXConfig

console = Console()
err_console = Console(stderr=True)

# Reusable Annotated types for Typer commands
DirArg = Annotated[Path, typer.Argument(help="Project directory")]

# Default ASGI app path used by dev, run, and demo
DEFAULT_APP_PATH = "app.main:app"


def load_config(directory: Path) -> PJXConfig:
    """Load PJXConfig from a project directory.

    Resolves the directory and looks for ``pjx.toml`` inside it.
    Prints a Rich error and exits on failure.
    """
    directory = directory.resolve()
    toml_path = directory / "pjx.toml"
    try:
        return PJXConfig(toml_path=toml_path)
    except Exception as exc:
        err_console.print(f"[red]ERROR:[/red] failed to load config: {exc}")
        raise typer.Exit(1) from exc


def iter_templates(config: PJXConfig) -> Iterator[Path]:
    """Yield all ``.jinja`` files from the configured template directories."""
    for tpl_dir in config.template_dirs:
        tpl_path = Path(tpl_dir)
        if tpl_path.exists():
            yield from sorted(tpl_path.rglob("*.jinja"))


def ensure_dir(path: Path) -> Path:
    """Create directory tree if needed, return the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def discover_app(directory: Path) -> str:
    """Auto-discover the ASGI app in a directory.

    Looks for common patterns:
    - ``app/main.py`` (new scaffold) → ``app.main:app``
    - ``app.py``, ``main.py``, ``server.py`` (flat) → ``<name>:app``
    """
    if (directory / "app" / "main.py").exists():
        return "app.main:app"
    for name in ("app", "main", "server"):
        candidate = directory / f"{name}.py"
        if candidate.exists():
            return f"{name}:app"
    return DEFAULT_APP_PATH


def prepare_server(
    directory: Path,
    app_path: str | None = None,
) -> tuple[PJXConfig, str]:
    """Load config, discover app, and ensure project is importable.

    Shared setup for ``pjx dev`` and ``pjx run``.
    """
    directory = directory.resolve()
    config = load_config(directory)
    if app_path is None:
        app_path = discover_app(directory)
    dir_str = str(directory)
    if dir_str not in sys.path:
        sys.path.insert(0, dir_str)
    return config, app_path
