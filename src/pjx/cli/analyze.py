"""``pjx analyze`` — route and bundle analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from pjx.cli.common import DirArg, console, load_config
from pjx.config import PJXConfig

app = typer.Typer()


@app.command()
def analyze(
    directory: DirArg = Path("."),
    routes: Annotated[
        bool, typer.Option("--routes", "-r", help="Show route table")
    ] = False,
) -> None:
    """Analyze templates, routes, and CSS bundle sizes."""
    directory = directory.resolve()
    config = load_config(directory)

    template_count = 0
    total_size = 0
    css_size = 0

    for tpl_dir in config.template_dirs:
        tpl_path = Path(tpl_dir)
        if not tpl_path.exists():
            continue
        for jinja_file in sorted(tpl_path.rglob("*.jinja")):
            template_count += 1
            total_size += jinja_file.stat().st_size

    # Check for bundled CSS
    css_bundle = config.static_dir / "css" / "pjx-components.css"
    if css_bundle.exists():
        css_size = css_bundle.stat().st_size

    console.print("=== PJX Analysis ===")
    console.print(f"Templates:    {template_count}")
    console.print(f"Template size: {_fmt_size(total_size)}")
    console.print(f"CSS bundle:   {_fmt_size(css_size)}")

    if routes:
        _show_routes(config)


def _show_routes(config: PJXConfig) -> None:
    """Display the route table from file-based routing."""
    from pjx.router import FileRouter

    router = FileRouter(config.pages_dir, [Path(d) for d in config.template_dirs])
    entries = router.scan()

    if not entries:
        console.print("\nNo routes found.")
        return

    table = Table(title=f"Routes ({len(entries)})")
    table.add_column("Method", style="cyan")
    table.add_column("URL", style="green")
    table.add_column("Template")
    table.add_column("Type")

    for entry in entries:
        methods = ",".join(entry.methods)
        route_type = "API" if entry.is_api else "Page"
        table.add_row(methods, entry.url_pattern, entry.template, route_type)

    console.print(table)


def _fmt_size(size: int) -> str:
    """Format byte size to human-readable string."""
    if size == 0:
        return "0 B"
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"
