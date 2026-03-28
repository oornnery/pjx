"""``pjx dev`` and ``pjx run`` — development and production server commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from pjx.cli.common import DirArg, console, prepare_server

app = typer.Typer()


@app.command()
def dev(
    directory: DirArg = Path("."),
    app_path: Annotated[
        str | None, typer.Option("--app", "-a", help="ASGI app path")
    ] = None,
    host: Annotated[
        str | None, typer.Option("--host", "-h", help="Host to bind to")
    ] = None,
    port: Annotated[
        int | None, typer.Option("--port", "-p", help="Port to bind to")
    ] = None,
) -> None:
    """Start the development server with auto-reload."""
    import uvicorn

    from pjx.cli.build import run_build
    from pjx.errors import PJXError

    directory = directory.resolve()
    config, app_path = prepare_server(directory, app_path)

    try:
        count = run_build(config)
        console.print(f"Built [green]{count}[/green] components.")
    except PJXError as e:
        console.print(f"[yellow]WARNING:[/yellow] {e}")

    reload_dirs = [str(directory)]
    for tpl_dir in config.template_dirs:
        tpl = Path(tpl_dir)
        if tpl.exists():
            reload_dirs.append(str(tpl))

    console.print(f"Starting dev server: [cyan]{app_path}[/cyan]")

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
    directory: DirArg = Path("."),
    app_path: Annotated[
        str | None, typer.Option("--app", "-a", help="ASGI app path")
    ] = None,
    host: Annotated[str | None, typer.Option("--host", help="Host to bind to")] = None,
    port: Annotated[int | None, typer.Option("--port", help="Port to bind to")] = None,
    workers: Annotated[
        int, typer.Option("--workers", "-w", help="Number of workers")
    ] = 1,
) -> None:
    """Start the production server."""
    import uvicorn

    directory = directory.resolve()
    config, app_path = prepare_server(directory, app_path)

    uvicorn.run(
        app_path,
        host=host or config.host,
        port=port or config.port,
        workers=workers,
    )
