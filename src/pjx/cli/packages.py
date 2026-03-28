"""``pjx add`` / ``pjx remove`` — npm package management."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from pjx.cli.common import DirArg, console, err_console, load_config
from pjx.config import PJXConfig

app = typer.Typer()


@app.command()
def add(
    package: Annotated[str, typer.Argument(help="npm package name to install")],
    directory: DirArg = Path("."),
) -> None:
    """Install an npm package and copy its dist files to vendor."""
    _ensure_npm()
    try:
        subprocess.run(
            ["npm", "install", package],  # noqa: S603, S607
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        err_console.print(f"[red]ERROR:[/red] npm install failed: {e.stderr}")
        raise typer.Exit(1) from e
    console.print(f"Installed {package}")

    # Try to copy dist files to vendor
    config = load_config(directory)
    _copy_vendor(package, config)


@app.command()
def remove(
    package: Annotated[str, typer.Argument(help="npm package name to remove")],
    directory: DirArg = Path("."),
) -> None:
    """Remove an npm package."""
    _ensure_npm()
    try:
        subprocess.run(
            ["npm", "uninstall", package],  # noqa: S603, S607
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        err_console.print(f"[red]ERROR:[/red] npm uninstall failed: {e.stderr}")
        raise typer.Exit(1) from e
    console.print(f"Removed {package}")


def _ensure_npm() -> None:
    """Check that npm is available."""
    if shutil.which("npm") is None:
        err_console.print("[red]ERROR:[/red] npm not found. Please install Node.js.")
        raise typer.Exit(1)


_VENDOR_PATTERNS = ("*.min.js", "*.min.css", "*.cdn.css", "*.cdn.min.css")


def _copy_vendor(package: str, config: PJXConfig) -> None:
    """Copy dist files from node_modules to vendor directory."""
    dist_root = Path("node_modules") / package / "dist"
    if not dist_root.exists():
        return

    vendor_dir = config.vendor_static_dir / package
    vendor_dir.mkdir(parents=True, exist_ok=True)

    seen: set[Path] = set()
    for pattern in _VENDOR_PATTERNS:
        for dist_file in dist_root.rglob(pattern):
            if dist_file in seen:
                continue
            seen.add(dist_file)
            rel = dist_file.relative_to(dist_root)
            dest = vendor_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dist_file, dest)
            console.print(f"  Copied {rel} → {dest}")
