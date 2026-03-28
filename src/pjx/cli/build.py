"""``pjx build``, ``pjx check``, ``pjx format`` — build and validation commands."""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from pjx.compiler import Compiler
from pjx.config import PJXConfig
from pjx.errors import PJXError
from pjx.parser import parse_file
from pjx.registry import ComponentRegistry

app = typer.Typer()

log = logging.getLogger("pjx.build")


def run_build(config: PJXConfig) -> int:
    """Compile all .jinja components and bundle CSS.

    Args:
        config: Resolved PJX configuration.

    Returns:
        Number of compiled components.

    Raises:
        PJXError: If any template fails to parse or compile.
    """
    registry = ComponentRegistry([Path(d) for d in config.template_dirs])
    compiler = Compiler(registry=registry)

    css_parts: list[str] = []
    count = 0

    for tpl_dir in config.template_dirs:
        tpl_path = Path(tpl_dir)
        if not tpl_path.exists():
            continue
        for jinja_file in sorted(tpl_path.rglob("*.jinja")):
            component = parse_file(jinja_file)
            compiled = compiler.compile(component)
            if compiled.css:
                css_parts.append(compiled.css.source)
            count += 1

    if css_parts:
        css_dir = config.static_dir / "css"
        css_dir.mkdir(parents=True, exist_ok=True)
        bundle_path = css_dir / "pjx-components.css"
        bundle_path.write_text("\n".join(css_parts))
        log.info("Bundled CSS → %s", bundle_path)

    return count


@app.command()
def build(
    directory: Path = typer.Argument(Path("."), help="Project directory"),
    output: Path = typer.Option(None, "--output", "-o", help="SSG output directory"),
) -> None:
    """Compile all .jinja components and bundle CSS.

    With ``--output``, also generates static HTML files for eligible routes.
    """
    config = PJXConfig()
    try:
        count = run_build(config)
    except PJXError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1) from e
    typer.echo(f"Compiled {count} components.")

    if output:
        _run_ssg(config, output)


def _run_ssg(config: PJXConfig, output: Path) -> None:
    """Run static site generation for all eligible routes."""
    from fastapi import FastAPI

    from pjx.integration import PJX
    from pjx.router import FileRouter
    from pjx.static import StaticGenerator

    ssg_app = FastAPI()
    pjx = PJX(ssg_app, config=config)

    router = FileRouter(config.pages_dir, [Path(d) for d in config.template_dirs])
    routes = router.scan()

    output.mkdir(parents=True, exist_ok=True)
    generator = StaticGenerator(pjx, output)
    pages = generator.generate(routes)

    typer.echo(f"Generated {len(pages)} static pages → {output}")


@app.command()
def sitemap(
    directory: Path = typer.Argument(Path("."), help="Project directory"),
    output: Path = typer.Option(Path("."), "--output", "-o", help="Output directory"),
    base_url: str = typer.Option("", "--base-url", "-b", help="Site base URL"),
) -> None:
    """Generate sitemap.xml from the route table."""
    from pjx.router import FileRouter
    from pjx.seo import write_sitemap

    config = PJXConfig()
    url = base_url or config.seo_base_url
    if not url:
        typer.echo("ERROR: --base-url or seo_base_url config required", err=True)
        raise typer.Exit(1)

    router = FileRouter(config.pages_dir, [Path(d) for d in config.template_dirs])
    routes = router.scan()

    path = write_sitemap(routes, url, output)
    typer.echo(f"Generated {path}")


@app.command()
def robots(
    directory: Path = typer.Argument(Path("."), help="Project directory"),
    output: Path = typer.Option(Path("."), "--output", "-o", help="Output directory"),
) -> None:
    """Generate robots.txt from configuration."""
    from pjx.seo import write_robots

    config = PJXConfig()
    sitemap_url = ""
    if config.seo_base_url and config.seo_sitemap_url:
        sitemap_url = f"{config.seo_base_url.rstrip('/')}{config.seo_sitemap_url}"

    path = write_robots(
        output,
        sitemap_url=sitemap_url,
        disallow=config.seo_robots_disallow,
        allow=config.seo_robots_allow,
    )
    typer.echo(f"Generated {path}")


@app.command()
def check(
    directory: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Parse all .jinja files, validate imports, props, and slots."""
    from pjx.checker import check_all

    config = PJXConfig()
    registry = ComponentRegistry([Path(d) for d in config.template_dirs])
    parse_errors = 0
    check_errors: list[PJXError] = []
    count = 0

    # Phase 1: parse all components and register them
    components = []
    for tpl_dir in config.template_dirs:
        tpl_path = Path(tpl_dir)
        if not tpl_path.exists():
            continue
        for jinja_file in sorted(tpl_path.rglob("*.jinja")):
            try:
                component = parse_file(jinja_file)
                registry.register(jinja_file.stem, component)
                components.append(component)
                count += 1
            except PJXError as e:
                typer.echo(f"ERROR: {e}", err=True)
                parse_errors += 1

    # Phase 2: run static checks on all components
    for component in components:
        check_errors.extend(check_all(component, registry))

    for err in check_errors:
        typer.echo(f"WARNING: {err}", err=True)

    total_errors = parse_errors + len(check_errors)
    if total_errors:
        typer.echo(
            f"Found {parse_errors} parse error(s) and {len(check_errors)} "
            f"check warning(s) in {count + parse_errors} files.",
            err=True,
        )
        if parse_errors:
            raise typer.Exit(1)
    else:
        typer.echo(f"Checked {count} files — no errors.")


@app.command(name="format")
def format_cmd(
    directory: Path = typer.Argument(Path("."), help="Project directory"),
    check: bool = typer.Option(
        False, "--check", help="Check only, exit 1 if files would change"
    ),
) -> None:
    """Re-format .jinja files with consistent frontmatter style."""
    from pjx.formatter import format_file

    config = PJXConfig()
    count = 0
    changed = 0
    errors = 0

    for tpl_dir in config.template_dirs:
        tpl_path = Path(tpl_dir)
        if not tpl_path.exists():
            continue
        for jinja_file in sorted(tpl_path.rglob("*.jinja")):
            try:
                formatted, did_change = format_file(jinja_file)
                count += 1
                if did_change:
                    changed += 1
                    if check:
                        typer.echo(f"Would reformat: {jinja_file}")
                    else:
                        jinja_file.write_text(formatted, encoding="utf-8")
                        typer.echo(f"Reformatted: {jinja_file}")
            except PJXError as e:
                typer.echo(f"ERROR: {e}", err=True)
                errors += 1

    if check:
        if changed:
            typer.echo(f"{changed} file(s) would be reformatted.")
            raise typer.Exit(1)
        typer.echo(f"{count} file(s) already formatted.")
    else:
        typer.echo(f"Formatted {count} files ({changed} changed).")
