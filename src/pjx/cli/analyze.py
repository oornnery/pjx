"""``pjx analyze`` — route and bundle analysis."""

from __future__ import annotations

from pathlib import Path

import typer

from pjx.config import PJXConfig

app = typer.Typer()


@app.command()
def analyze(
    directory: Path = typer.Argument(Path("."), help="Project directory"),
    routes: bool = typer.Option(False, "--routes", "-r", help="Show route table"),
) -> None:
    """Analyze templates, routes, and CSS bundle sizes."""
    directory = directory.resolve()
    toml_path = directory / "pjx.toml"
    config = PJXConfig(toml_path=toml_path)

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

    typer.echo("=== PJX Analysis ===")
    typer.echo(f"Templates:    {template_count}")
    typer.echo(f"Template size: {_fmt_size(total_size)}")
    typer.echo(f"CSS bundle:   {_fmt_size(css_size)}")

    if routes:
        _show_routes(config)


def _show_routes(config: PJXConfig) -> None:
    """Display the route table from file-based routing."""
    from pjx.router import FileRouter

    router = FileRouter(config.pages_dir, [Path(d) for d in config.template_dirs])
    entries = router.scan()

    if not entries:
        typer.echo("\nNo routes found.")
        return

    typer.echo(f"\n=== Routes ({len(entries)}) ===")
    typer.echo(f"{'Method':<8} {'URL':<40} {'Template':<30} {'Type':<6}")
    typer.echo("-" * 84)

    for entry in entries:
        methods = ",".join(entry.methods)
        route_type = "API" if entry.is_api else "Page"
        typer.echo(
            f"{methods:<8} {entry.url_pattern:<40} {entry.template:<30} {route_type:<6}"
        )


def _fmt_size(size: int) -> str:
    """Format byte size to human-readable string."""
    if size == 0:
        return "0 B"
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"
