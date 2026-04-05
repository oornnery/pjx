from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pjx.checker import check_directory
from pjx.errors import DiagnosticLevel


def cmd_check(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"error: path not found: {path}", file=sys.stderr)
        return 1

    results = check_directory(path, verbose=getattr(args, "verbose", False))

    errors = 0
    warnings = 0

    for result in results:
        if not result.diagnostics:
            if getattr(args, "verbose", False):
                print(f"  ok: {result.template}")
            continue

        for diag in result.diagnostics:
            loc = f"{diag.loc.file or '<unknown>'}:{diag.loc.line}:{diag.loc.col}"
            msg = f"{diag.level.value}[{diag.code}]: {diag.message}"
            print(f"{msg}\n  --> {loc}", file=sys.stderr)
            if diag.hint:
                print(f"  = hint: {diag.hint}", file=sys.stderr)
            print(file=sys.stderr)

            if diag.level == DiagnosticLevel.ERROR:
                errors += 1
            else:
                warnings += 1

    total = sum(1 for r in results if not r.diagnostics)
    if errors:
        print(
            f"\n{errors} error(s), {warnings} warning(s) in {len(results)} template(s).",
            file=sys.stderr,
        )
        return 1

    if warnings:
        print(f"{total} ok, {warnings} warning(s) in {len(results)} template(s).")
    else:
        print(f"All {len(results)} template(s) valid.")
    return 0


def cmd_format(args: argparse.Namespace) -> int:
    from pjx.formatter import check_format, format_file

    path = Path(args.path)
    if not path.exists():
        print(f"error: path not found: {path}", file=sys.stderr)
        return 1

    files = [path] if path.is_file() else sorted(path.rglob("*.jinja"))

    if not files:
        print(f"No .jinja files found in {path}")
        return 0

    check_only = getattr(args, "check", False)
    changed = 0

    for file in files:
        if check_only:
            if not check_format(file):
                print(f"Would reformat: {file}")
                changed += 1
            elif getattr(args, "verbose", False):
                print(f"  ok: {file}")
        else:
            if format_file(file):
                print(f"Reformatted: {file}")
                changed += 1
            elif getattr(args, "verbose", False):
                print(f"  ok: {file}")

    if check_only and changed:
        print(f"\n{changed} file(s) would be reformatted.", file=sys.stderr)
        return 1

    if not check_only:
        if changed:
            print(f"\n{changed} file(s) reformatted.")
        else:
            print(f"All {len(files)} file(s) already formatted.")

    return 0


def cmd_sitemap(args: argparse.Namespace) -> int:
    from pjx.seo import discover_pages, generate_robots, generate_sitemap

    path = Path(args.path)
    if not path.is_dir():
        print(f"error: directory not found: {path}", file=sys.stderr)
        return 1

    base_url = args.base_url
    entries = discover_pages(path)

    if not entries:
        print(f"No pages found in {path}")
        return 0

    output_dir = Path(args.output) if args.output else path.parent / "static"
    output_dir.mkdir(parents=True, exist_ok=True)

    sitemap = generate_sitemap(entries, base_url)
    sitemap_path = output_dir / "sitemap.xml"
    sitemap_path.write_text(sitemap)
    print(f"Generated: {sitemap_path} ({len(entries)} URLs)")

    robots = generate_robots(
        base_url,
        disallow=args.disallow.split(",") if args.disallow else None,
    )
    robots_path = output_dir / "robots.txt"
    robots_path.write_text(robots)
    print(f"Generated: {robots_path}")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pjx",
        description="PJX template toolkit",
    )
    subparsers = parser.add_subparsers(dest="command")

    # check
    check_parser = subparsers.add_parser(
        "check",
        help="Validate PJX templates (imports, props, cycles, undefined vars)",
    )
    check_parser.add_argument("path", help="File or directory to check")
    check_parser.add_argument("--verbose", "-v", action="store_true")

    # format
    fmt_parser = subparsers.add_parser(
        "format",
        help="Format PJX template frontmatter",
    )
    fmt_parser.add_argument("path", help="File or directory to format")
    fmt_parser.add_argument(
        "--check",
        action="store_true",
        help="Check only, exit 1 if changes needed (CI mode)",
    )
    fmt_parser.add_argument("--verbose", "-v", action="store_true")

    # sitemap
    sitemap_parser = subparsers.add_parser(
        "sitemap",
        help="Generate sitemap.xml and robots.txt from templates",
    )
    sitemap_parser.add_argument(
        "path",
        help="Templates directory (with pages/ subdirectory)",
    )
    sitemap_parser.add_argument(
        "--base-url",
        required=True,
        help="Base URL (e.g. https://example.com)",
    )
    sitemap_parser.add_argument(
        "--output",
        "-o",
        help="Output directory (default: static/)",
    )
    sitemap_parser.add_argument(
        "--disallow",
        help="Comma-separated disallow paths for robots.txt",
    )

    args = parser.parse_args()

    commands = {
        "check": cmd_check,
        "format": cmd_format,
        "sitemap": cmd_sitemap,
    }

    handler = commands.get(args.command)
    if handler:
        sys.exit(handler(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
