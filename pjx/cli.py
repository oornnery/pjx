from __future__ import annotations

import sys
from typing import Annotated

import typer
from rich.console import Console

from .tooling import (
    check_project,
    format_project,
    render_check_report,
    render_format_report,
)


app = typer.Typer(
    help="PJX template tooling",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
    rich_markup_mode="rich",
)
console = Console()
error_console = Console(stderr=True)


@app.command("check")
def check_command(
    target: Annotated[
        str | None,
        typer.Argument(
            help="Project path, template path, or import target like package.module:pjx",
        ),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            help="Output format: text or json",
            show_default=True,
        ),
    ] = "text",
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Fail on warnings too"),
    ] = False,
) -> None:
    normalized = output_format.lower()
    if normalized not in {"text", "json"}:
        error_console.print("Invalid --format. Use 'text' or 'json'.")
        raise typer.Exit(code=2)

    report = check_project(target)
    console.print(render_check_report(report, output_format=normalized), markup=False)
    if report.errors > 0:
        raise typer.Exit(code=1)
    if strict and report.warnings > 0:
        raise typer.Exit(code=1)


@app.command("format")
def format_command(
    target: Annotated[
        str | None,
        typer.Argument(
            help="Project path, template path, or import target like package.module:pjx",
        ),
    ] = None,
    check: Annotated[
        bool,
        typer.Option(
            "--check", help="Report files that would change without writing them"
        ),
    ] = False,
) -> None:
    results = format_project(target, check=check)
    console.print(render_format_report(results, check=check), markup=False)
    if check and any(r.changed for r in results):
        raise typer.Exit(code=1)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        app(args=args, prog_name="pjx", standalone_mode=False)
    except typer.Exit as exc:
        return exc.exit_code
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    return 0
