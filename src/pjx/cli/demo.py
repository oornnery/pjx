"""``pjx demo`` — run the bundled demo application."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Annotated

import typer

from pjx.cli.common import DEFAULT_APP_PATH, console, err_console


def demo(
    port: Annotated[int, typer.Option("--port", "-p", help="Port")] = 8000,
    host: Annotated[str, typer.Option("--host", "-h", help="Host")] = "127.0.0.1",
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
        err_console.print("Demo not found. Reinstall pjx or run from the project root.")
        raise typer.Exit(1)

    # Copy to a temp dir so the demo can write build artifacts
    tmp = Path(tempfile.mkdtemp(prefix="pjx-demo-"))
    demo_dir = tmp / "demo"
    shutil.copytree(demo_src, demo_dir)

    console.print(f"PJX Demo — http://{host}:{port}")
    console.print(f"Working dir: {demo_dir}")

    # Build templates
    toml_path = demo_dir / "pjx.toml"
    config = PJXConfig(toml_path=toml_path)

    try:
        count = run_build(config)
        console.print(f"Built {count} components.")
    except PJXError as e:
        err_console.print(f"Build warning: {e}")

    # Make the demo importable
    dir_str = str(demo_dir)
    if dir_str not in sys.path:
        sys.path.insert(0, dir_str)

    try:
        uvicorn.run(
            DEFAULT_APP_PATH,
            host=host,
            port=port,
            reload=True,
            reload_dirs=[dir_str],
            reload_includes=["*.py", "*.jinja", "*.css", "*.js", "*.toml"],
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
