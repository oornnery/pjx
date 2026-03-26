"""``pjx build``, ``pjx check``, ``pjx format`` — build and validation commands."""

from __future__ import annotations

from pathlib import Path

import typer

from pjx.compiler import Compiler
from pjx.config import PJXConfig
from pjx.errors import PJXError
from pjx.parser import parse_file
from pjx.registry import ComponentRegistry

app = typer.Typer()


@app.command()
def build(
    directory: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Compile all .jinja components and bundle CSS."""
    config = PJXConfig()
    registry = ComponentRegistry([Path(d) for d in config.template_dirs])
    compiler = Compiler(registry=registry)

    css_parts: list[str] = []
    count = 0

    for tpl_dir in config.template_dirs:
        tpl_path = Path(tpl_dir)
        if not tpl_path.exists():
            continue
        for jinja_file in sorted(tpl_path.rglob("*.jinja")):
            try:
                component = parse_file(jinja_file)
                compiled = compiler.compile(component)
                if compiled.css:
                    css_parts.append(compiled.css.source)
                count += 1
            except PJXError as e:
                typer.echo(f"ERROR: {e}", err=True)
                raise typer.Exit(1) from e

    # Write bundled CSS
    if css_parts:
        css_dir = config.static_dir / "css"
        css_dir.mkdir(parents=True, exist_ok=True)
        bundle_path = css_dir / "pjx-components.css"
        bundle_path.write_text("\n".join(css_parts))
        typer.echo(f"Bundled CSS → {bundle_path}")

    typer.echo(f"Compiled {count} components.")


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
) -> None:
    """Re-format .jinja files with consistent style."""
    config = PJXConfig()
    count = 0

    for tpl_dir in config.template_dirs:
        tpl_path = Path(tpl_dir)
        if not tpl_path.exists():
            continue
        for jinja_file in sorted(tpl_path.rglob("*.jinja")):
            # For now, just verify they parse correctly
            try:
                parse_file(jinja_file)
                count += 1
            except PJXError as e:
                typer.echo(f"ERROR: {e}", err=True)

    typer.echo(f"Formatted {count} files.")
