"""``pjx dev`` and ``pjx run`` — development and production server commands."""

from __future__ import annotations

from pathlib import Path

import typer

from pjx.config import PJXConfig

app = typer.Typer()


def _discover_app(directory: Path) -> str:
    """Auto-discover the ASGI app in a directory.

    Looks for common patterns:
    - ``app/main.py`` (new scaffold) → ``app.main:app``
    - ``app.py``, ``main.py``, ``server.py`` (flat) → ``<name>:app``
    """
    # New scaffold: app/ package with main.py
    if (directory / "app" / "main.py").exists():
        return "app.main:app"
    # Flat layout
    for name in ("app", "main", "server"):
        candidate = directory / f"{name}.py"
        if candidate.exists():
            return f"{name}:app"
    return "app.main:app"


@app.command()
def dev(
    directory: Path = typer.Argument(
        Path("."), help="Project directory (containing pjx.toml)"
    ),
    app_path: str = typer.Option(
        None,
        "--app",
        "-a",
        help="ASGI app path (e.g. app:app). Auto-discovered if omitted.",
    ),
    host: str = typer.Option(None, "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(None, "--port", "-p", help="Port to bind to"),
) -> None:
    """Start the development server with auto-reload."""
    import sys

    import uvicorn

    from pjx.cli.build import run_build
    from pjx.errors import PJXError

    directory = directory.resolve()
    toml_path = directory / "pjx.toml"
    config = PJXConfig(toml_path=toml_path)

    if app_path is None:
        app_path = _discover_app(directory)

    # Auto-build templates before starting
    try:
        count = run_build(config)
        typer.echo(f"Built {count} components.")
    except PJXError as e:
        typer.echo(f"Build warning: {e}", err=True)

    # Watch templates and static dirs for reload
    reload_dirs = [str(directory)]
    for tpl_dir in config.template_dirs:
        tpl = Path(tpl_dir)
        if tpl.exists():
            reload_dirs.append(str(tpl))

    # Ensure the project directory is importable
    dir_str = str(directory)
    if dir_str not in sys.path:
        sys.path.insert(0, dir_str)

    typer.echo(f"Starting dev server: {app_path}")
    typer.echo(f"Config: {toml_path}")
    typer.echo(f"Watching: {', '.join(reload_dirs)}")

    uvicorn.run(
        app_path,
        host=host or config.host,
        port=port or config.port,
        reload=True,
        reload_dirs=reload_dirs,
        reload_includes=["*.py", "*.jinja", "*.css", "*.js", "*.toml"],
    )


@app.command()
def run(
    directory: Path = typer.Argument(
        Path("."), help="Project directory (containing pjx.toml)"
    ),
    app_path: str = typer.Option(
        None,
        "--app",
        "-a",
        help="ASGI app path (e.g. app:app). Auto-discovered if omitted.",
    ),
    host: str = typer.Option(None, "--host", help="Host to bind to"),
    port: int = typer.Option(None, "--port", help="Port to bind to"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of workers"),
) -> None:
    """Start the production server."""
    import uvicorn

    directory = directory.resolve()
    toml_path = directory / "pjx.toml"
    config = PJXConfig(toml_path=toml_path)

    if app_path is None:
        app_path = _discover_app(directory)

    import sys

    dir_str = str(directory)
    if dir_str not in sys.path:
        sys.path.insert(0, dir_str)

    uvicorn.run(
        app_path,
        host=host or config.host,
        port=port or config.port,
        workers=workers,
    )
