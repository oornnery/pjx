"""``pjx add`` / ``pjx remove`` — npm package management."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import typer

from pjx.config import PJXConfig

app = typer.Typer()


@app.command()
def add(
    package: str = typer.Argument(help="npm package name to install"),
) -> None:
    """Install an npm package and copy its dist files to vendor."""
    _ensure_npm()
    result = subprocess.run(
        ["npm", "install", package],  # noqa: S603, S607
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        typer.echo(f"npm install failed: {result.stderr}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Installed {package}")

    # Try to copy dist files to vendor
    config = PJXConfig()
    _copy_vendor(package, config)


@app.command()
def remove(
    package: str = typer.Argument(help="npm package name to remove"),
) -> None:
    """Remove an npm package."""
    _ensure_npm()
    result = subprocess.run(
        ["npm", "uninstall", package],  # noqa: S603, S607
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        typer.echo(f"npm uninstall failed: {result.stderr}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Removed {package}")


def _ensure_npm() -> None:
    """Check that npm is available."""
    if shutil.which("npm") is None:
        typer.echo("npm not found. Please install Node.js.", err=True)
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
            typer.echo(f"  Copied {rel} → {dest}")
