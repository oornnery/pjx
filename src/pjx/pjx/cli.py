from __future__ import annotations

from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from pjx.assets import (
    ManifestEntry,
    add_manifest_entry,
    available_asset_provider_names,
    build_vendor_assets,
    discover_asset_providers,
    load_manifest,
    remove_manifest_entry,
)
from pjx.checker import apply_check_fixes, check_directory
from pjx.errors import DiagnosticLevel

app = typer.Typer(
    help="PJX template toolkit",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
assets_app = typer.Typer(
    help="Manage browser assets provided by PJX extras and third-party packages",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(assets_app, name="assets")


def _console() -> Console:
    return Console()


def _err_console() -> Console:
    return Console(stderr=True)


def _print_message(message: str, *, style: str = "") -> None:
    _console().print(Text(message, style=style))


def _print_error(message: str) -> None:
    _err_console().print(Text(f"error: {message}", style="red"))


def run_check(path: Path, *, verbose: bool = False, fix: bool = False) -> int:
    if not path.exists():
        _print_error(f"path not found: {path}")
        return 1

    if fix:
        fix_result = apply_check_fixes(path)
        if fix_result.fixes_applied:
            _print_message(
                f"Applied {fix_result.fixes_applied} technical fix(es) in "
                f"{fix_result.files_changed} file(s).",
                style="cyan",
            )
        else:
            _print_message("No autofixable technical issues found.", style="yellow")

    results = check_directory(path, verbose=verbose)

    errors = 0
    warnings = 0

    for result in results:
        if not result.diagnostics:
            if verbose:
                _print_message(f"  ok: {result.template}", style="green")
            continue

        for diag in result.diagnostics:
            loc = f"{diag.loc.file or '<unknown>'}:{diag.loc.line}:{diag.loc.col}"
            style = "red" if diag.level == DiagnosticLevel.ERROR else "yellow"
            _err_console().print(
                Text(
                    f"{diag.level.value}[{diag.code}]: {diag.message}",
                    style=style,
                )
            )
            _err_console().print(Text(f"  --> {loc}", style="dim"))
            if diag.hint:
                _err_console().print(Text(f"  = hint: {diag.hint}", style="dim"))
            _err_console().print()

            if diag.level == DiagnosticLevel.ERROR:
                errors += 1
            else:
                warnings += 1

    total_ok = sum(1 for result in results if not result.diagnostics)
    total_templates = len(results)

    if errors:
        _err_console().print(
            Text(
                f"{errors} error(s), {warnings} warning(s) in {total_templates} template(s).",
                style="red",
            )
        )
        return 1

    if warnings:
        _print_message(
            f"{total_ok} ok, {warnings} warning(s) in {total_templates} template(s).",
            style="yellow",
        )
    else:
        _print_message(f"All {total_templates} template(s) valid.", style="green")
    return 0


def run_format(path: Path, *, check_only: bool = False, verbose: bool = False) -> int:
    from pjx.formatter import check_format, format_file

    if not path.exists():
        _print_error(f"path not found: {path}")
        return 1

    files_to_format = [path] if path.is_file() else sorted(path.rglob("*.jinja"))

    if not files_to_format:
        _print_message(f"No .jinja files found in {path}", style="yellow")
        return 0

    changed = 0

    for file in files_to_format:
        if check_only:
            if not check_format(file):
                _print_message(f"Would reformat: {file}", style="yellow")
                changed += 1
            elif verbose:
                _print_message(f"  ok: {file}", style="green")
            continue

        if format_file(file):
            _print_message(f"Reformatted: {file}", style="cyan")
            changed += 1
        elif verbose:
            _print_message(f"  ok: {file}", style="green")

    if check_only and changed:
        _err_console().print(Text(f"{changed} file(s) would be reformatted.", style="yellow"))
        return 1

    if not check_only:
        if changed:
            _print_message(f"{changed} file(s) reformatted.", style="green")
        else:
            _print_message(f"All {len(files_to_format)} file(s) already formatted.", style="green")

    return 0


def run_sitemap(
    path: Path,
    *,
    base_url: str,
    output: Path | None = None,
    disallow: str | None = None,
) -> int:
    from pjx.seo import discover_pages, generate_robots, generate_sitemap

    if not path.is_dir():
        _print_error(f"directory not found: {path}")
        return 1

    entries = discover_pages(path)

    if not entries:
        _print_message(f"No pages found in {path}", style="yellow")
        return 0

    output_dir = output if output is not None else path.parent / "static"
    output_dir.mkdir(parents=True, exist_ok=True)

    sitemap = generate_sitemap(entries, base_url)
    sitemap_path = output_dir / "sitemap.xml"
    sitemap_path.write_text(sitemap)
    _print_message(f"Generated: {sitemap_path} ({len(entries)} URLs)", style="green")

    robots = generate_robots(
        base_url,
        disallow=disallow.split(",") if disallow else None,
    )
    robots_path = output_dir / "robots.txt"
    robots_path.write_text(robots)
    _print_message(f"Generated: {robots_path}", style="green")

    return 0


def _resolve_bundled_dir(name: str) -> Path | Traversable | None:
    """Resolve a directory under _bundled/ (skills/pjx, demo, etc.)."""
    bundled = files("pjx").joinpath("_bundled", *name.split("/"))
    if bundled.is_dir():
        return bundled

    # Walk up at most 6 levels to find repo-level dir
    for base in Path(__file__).resolve().parents[:6]:
        candidate = base / name
        if candidate.is_dir():
            return candidate

    return None


def _resolve_skill_source() -> Path | Traversable:
    result = _resolve_bundled_dir("skills/pjx")
    if result is not None:
        return result
    raise FileNotFoundError("Could not locate bundled PJX skill files.")


def _copy_tree(src: Path | Traversable, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            _copy_tree(item, target)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(item.read_bytes())


def run_skills(*, claude: bool = False, agents: bool = False, cwd: Path | None = None) -> int:
    targets: list[Path] = []
    base_dir = cwd or Path.cwd()

    if claude:
        targets.append(base_dir / ".claude" / "skills" / "pjx")
    if agents:
        targets.append(base_dir / ".agents" / "skills" / "pjx")

    if not targets:
        _print_error("choose at least one target with --claude and/or --agents")
        return 2

    try:
        source = _resolve_skill_source()
    except FileNotFoundError as exc:
        _print_error(str(exc))
        return 1

    for target in targets:
        _copy_tree(source, target)
        _print_message(f"Installed PJX skill to {target}", style="green")

    return 0


def run_assets_build(
    output: Path,
    *,
    providers: list[str] | None = None,
) -> int:
    selected = [name.strip() for name in (providers or []) if name.strip()]
    available = set(available_asset_provider_names())

    if selected:
        missing = sorted(set(selected) - available)
        if missing:
            known = ", ".join(sorted(available)) or "<none>"
            _print_error(
                f"unknown asset provider(s): {', '.join(missing)}. available providers: {known}"
            )
            return 2

    discovered = discover_asset_providers(names=selected or None)
    try:
        result = build_vendor_assets(output, providers=discovered)
    except OSError as exc:
        _print_error(f"could not build vendor assets: {exc}")
        return 1

    if not result.writes:
        if selected:
            _print_message(
                "No vendorable browser assets found for the selected providers.",
                style="yellow",
            )
        else:
            _print_message(
                "No vendorable browser assets found from installed providers.",
                style="yellow",
            )
        return 0

    for write in result.writes:
        _print_message(
            f"Vendored {write.provider}: {write.output_path}",
            style="cyan",
        )

    _print_message(
        f"Wrote {result.files_written} asset file(s) to {output}.",
        style="green",
    )
    return 0


def run_demo(*, host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> int:
    import sys

    try:
        import email_validator  # noqa: F401
        import uvicorn
    except ImportError:
        _print_error(
            "Demo requires extra dependencies. Install with:\n"
            "  pip install pjx[demo]   or   uvx --with 'pjx[demo]' pjx demo"
        )
        return 1

    demo_dir = _resolve_bundled_dir("demo")
    if demo_dir is None:
        _print_error("Could not locate bundled demo application.")
        return 1

    demo_root = str(demo_dir) if isinstance(demo_dir, Path) else str(demo_dir)
    if demo_root not in sys.path:
        sys.path.insert(0, demo_root)

    _print_message(f"Starting PJX demo on http://{host}:{port}", style="cyan")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)
    return 0


@app.command("check")
def check_command(
    path: Annotated[Path, typer.Argument(help="File or directory to check")],
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show templates without diagnostics"),
    ] = False,
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Apply safe technical autofixes before checking"),
    ] = False,
) -> None:
    code = run_check(path, verbose=verbose, fix=fix)
    if code:
        raise typer.Exit(code=code)


@app.command("format")
def format_command(
    path: Annotated[Path, typer.Argument(help="File or directory to format")],
    check: Annotated[
        bool,
        typer.Option("--check", help="Check only, exit 1 if changes are needed"),
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show unchanged files")] = False,
) -> None:
    code = run_format(path, check_only=check, verbose=verbose)
    if code:
        raise typer.Exit(code=code)


@app.command("sitemap")
def sitemap_command(
    path: Annotated[Path, typer.Argument(help="Templates directory (with pages/ subdirectory)")],
    base_url: Annotated[
        str,
        typer.Option("--base-url", help="Base URL, for example https://example.com"),
    ],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output directory")] = None,
    disallow: Annotated[
        str | None,
        typer.Option("--disallow", help="Comma-separated disallow paths"),
    ] = None,
) -> None:
    code = run_sitemap(path, base_url=base_url, output=output, disallow=disallow)
    if code:
        raise typer.Exit(code=code)


@app.command("skills")
def skills_command(
    claude: Annotated[
        bool,
        typer.Option("--claude", help="Copy the PJX skill to .claude/skills/pjx"),
    ] = False,
    agents: Annotated[
        bool,
        typer.Option("--agents", help="Copy the PJX skill to .agents/skills/pjx"),
    ] = False,
) -> None:
    code = run_skills(claude=claude, agents=agents)
    if code:
        raise typer.Exit(code=code)


@app.command("demo")
def demo_command(
    host: Annotated[
        str,
        typer.Option("--host", help="Bind address"),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Port number"),
    ] = 8000,
    reload: Annotated[
        bool,
        typer.Option("--reload", help="Enable auto-reload"),
    ] = False,
) -> None:
    """Run the bundled PJX demo application."""
    code = run_demo(host=host, port=port, reload=reload)
    if code:
        raise typer.Exit(code=code)


@assets_app.command("add")
def assets_add_command(
    package: Annotated[str, typer.Argument(help="npm package spec, for example alpinejs@3")],
    dist: Annotated[
        str,
        typer.Option("--dist", help="Path inside node_modules/ to the dist file"),
    ],
    output_path: Annotated[
        str,
        typer.Option(
            "--out", "-o", help="Output path relative to vendor dir, for example js/alpine.min.js"
        ),
    ],
    vendor_dir: Annotated[
        Path,
        typer.Option("--dir", "-d", help="Vendor directory containing pjx-assets.json"),
    ] = Path("static/vendor/pjx"),
    kind: Annotated[str, typer.Option("--kind", help="Asset kind: script or style")] = "script",
    placement: Annotated[str, typer.Option("--placement", help="head or body")] = "head",
) -> None:
    """Add an npm package to the local asset manifest."""
    from pjx.assets import _parse_npm_spec

    pkg_name, _ = _parse_npm_spec(package)
    entry = ManifestEntry(
        npm_package=package,
        npm_dist_path=dist,
        output_path=output_path,
        kind=kind,
        placement=placement,
    )
    add_manifest_entry(vendor_dir, pkg_name, entry)
    _print_message(f"Added {pkg_name} to {vendor_dir / 'pjx-assets.json'}", style="green")
    _print_message("Run `pjx assets build` to install.", style="dim")


@assets_app.command("remove")
def assets_remove_command(
    name: Annotated[str, typer.Argument(help="Package name to remove")],
    vendor_dir: Annotated[
        Path,
        typer.Option("--dir", "-d", help="Vendor directory containing pjx-assets.json"),
    ] = Path("static/vendor/pjx"),
) -> None:
    """Remove an npm package from the local asset manifest."""
    if remove_manifest_entry(vendor_dir, name):
        _print_message(f"Removed {name} from {vendor_dir / 'pjx-assets.json'}", style="green")
    else:
        _print_error(f"{name} not found in manifest")
        raise typer.Exit(code=1)


@assets_app.command("list")
def assets_list_command(
    vendor_dir: Annotated[
        Path,
        typer.Option("--dir", "-d", help="Vendor directory containing pjx-assets.json"),
    ] = Path("static/vendor/pjx"),
) -> None:
    """List all assets (extensions + manifest)."""
    console = _console()

    discovered = discover_asset_providers()
    if discovered:
        console.print(Text("Extensions:", style="bold"))
        for provider in discovered:
            for asset in provider.get_assets():
                vf = asset.vendor_file
                npm = vf.npm_package if vf else "-"
                console.print(Text(f"  {provider.name}/{asset.name}  npm:{npm}", style="cyan"))

    manifest = load_manifest(vendor_dir)
    if manifest:
        console.print(Text("\nManifest:", style="bold"))
        for name, entry in sorted(manifest.items()):
            console.print(
                Text(f"  {name}  npm:{entry.npm_package} -> {entry.output_path}", style="yellow")
            )

    if not discovered and not manifest:
        _print_message("No assets found.", style="dim")


@assets_app.command("build")
def assets_build_command(
    output: Annotated[
        Path,
        typer.Argument(help="Output directory, for example static/vendor/pjx"),
    ] = Path("static/vendor/pjx"),
    provider: Annotated[
        list[str] | None,
        typer.Option(
            "--provider",
            "-p",
            help="Provider name to vendor. Repeat to limit the build.",
        ),
    ] = None,
) -> None:
    code = run_assets_build(output, providers=list(provider or []))
    if code:
        raise typer.Exit(code=code)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
