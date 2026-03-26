"""``pjx init`` — scaffold a new PJX project."""

from __future__ import annotations

from pathlib import Path

import typer

from pjx.assets import ensure_project_dirs
from pjx.config import PJXConfig

app = typer.Typer()


@app.command()
def init(
    directory: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Scaffold a new PJX project with the standard directory structure."""
    config = PJXConfig()
    dirs = ensure_project_dirs(config)

    # Create pjx.toml if it doesn't exist
    toml_path = directory / "pjx.toml"
    if not toml_path.exists():
        toml_path.write_text(
            '[pjx]\nengine = "jinja2"\ndebug = false\nhost = "127.0.0.1"\nport = 8000\n'
        )
        typer.echo(f"Created {toml_path}")

    # Create a basic layout
    layout = config.layouts_dir / "Base.jinja"
    if not layout.exists():
        layout.write_text(
            "<!DOCTYPE html>\n<html>\n<head>\n"
            "  <Slot:head />\n</head>\n<body>\n"
            "  <Slot:content />\n</body>\n</html>\n"
        )
        typer.echo(f"Created {layout}")

    for d in dirs:
        typer.echo(f"  {d}/")
    typer.echo("PJX project initialized.")
