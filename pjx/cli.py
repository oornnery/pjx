from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from .tooling import (
    check_project,
    format_project,
    load_project,
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


@app.command("compile")
def compile_command(
    target: Annotated[
        str | None,
        typer.Argument(
            help="Project path, template path, or import target like package.module:pjx",
        ),
    ] = None,
    output: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for compiled .jinja files",
        ),
    ] = "build",
    clean: Annotated[
        bool,
        typer.Option("--clean", help="Remove output directory before compiling"),
    ] = False,
    bundle: Annotated[
        bool,
        typer.Option(
            "--bundle", help="Inline imported component macros into page templates"
        ),
    ] = False,
) -> None:
    """Compile all .pjx files to .jinja templates."""
    from .compile import compile_project, render_compile_report

    project = load_project(target)
    report = compile_project(project, Path(output), clean=clean, bundle=bundle)
    console.print(render_compile_report(report), markup=False)
    if report.files_failed > 0:
        raise typer.Exit(code=1)


@app.command("bench")
def bench_command(
    target: Annotated[
        str | None,
        typer.Argument(
            help="Project path, template path, or import target like package.module:pjx",
        ),
    ] = None,
    iterations: Annotated[
        int,
        typer.Option(
            "--iterations", "-n", help="Number of render iterations per template"
        ),
    ] = 100,
    warmup: Annotated[
        int,
        typer.Option("--warmup", help="Number of warmup iterations"),
    ] = 5,
    bundle: Annotated[
        bool,
        typer.Option(
            "--bundle",
            help="Inline component macros into page templates before benchmarking",
        ),
    ] = False,
) -> None:
    """Benchmark Jinja2 vs MiniJinja rendering performance."""
    from .bench import render_bench_report, run_bench

    project = load_project(target)
    report = run_bench(project, iterations=iterations, warmup=warmup, bundle=bundle)
    console.print(render_bench_report(report), markup=False)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        app(args=args, prog_name="pjx", standalone_mode=False)
    except typer.Exit as exc:
        return exc.exit_code
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    return 0
