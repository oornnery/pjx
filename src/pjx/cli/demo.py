"""``pjx demo`` — run the bundled demo application."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import typer


def demo(
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
) -> None:
    """Launch the bundled PJX demo application."""
    import importlib.resources
    import sys

    import uvicorn

    from pjx.cli.build import run_build
    from pjx.config import PJXConfig
    from pjx.errors import PJXError

    # Locate the bundled demo: installed wheel or dev checkout
    pkg_root = Path(str(importlib.resources.files("pjx")))
    demo_src = pkg_root / "examples" / "demo"

    if not demo_src.exists():
        # Dev layout: src/pjx → project root is two levels up
        project_root = pkg_root.parent.parent
        demo_src = project_root / "examples" / "demo"

    if not demo_src.exists():
        typer.echo(
            "Demo not found. Reinstall pjx or run from the project root.", err=True
        )
        raise typer.Exit(1)

    # Copy to a temp dir so the demo can write build artifacts
    tmp = Path(tempfile.mkdtemp(prefix="pjx-demo-"))
    demo_dir = tmp / "demo"
    shutil.copytree(demo_src, demo_dir)

    typer.echo(f"PJX Demo — http://{host}:{port}")
    typer.echo(f"Working dir: {demo_dir}")

    # Build templates
    toml_path = demo_dir / "pjx.toml"
    config = PJXConfig(toml_path=toml_path)

    try:
        count = run_build(config)
        typer.echo(f"Built {count} components.")
    except PJXError as e:
        typer.echo(f"Build warning: {e}", err=True)

    # Make the demo importable
    dir_str = str(demo_dir)
    if dir_str not in sys.path:
        sys.path.insert(0, dir_str)

    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=True,
            reload_dirs=[dir_str],
            reload_includes=["*.py", "*.jinja", "*.css", "*.js", "*.toml"],
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
