from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jinja2 import FileSystemLoader

from pjx.environment import PJXEnvironment
from pjx.errors import PJXError


def cmd_check(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"error: {path} nao encontrado", file=sys.stderr)
        return 1

    if path.is_file():
        base_dir = path.parent
        files = [path]
    else:
        base_dir = path
        files = sorted(path.rglob("*.jinja"))

    if not files:
        print(f"Nenhum arquivo .jinja encontrado em {path}")
        return 0

    env = PJXEnvironment(loader=FileSystemLoader(str(base_dir)))
    errors = 0

    for file in files:
        template_name = str(file.relative_to(base_dir))
        try:
            env.get_template(template_name)
            if args.verbose:
                print(f"  ok: {file}")
        except PJXError as e:
            print(e.format(), file=sys.stderr)
            errors += 1
        except Exception as e:
            print(f"error: {file}: {e}", file=sys.stderr)
            errors += 1

    if errors:
        print(f"\n{errors} erro(s) encontrado(s).", file=sys.stderr)
        return 1

    print(f"Todos os {len(files)} template(s) validos.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="pjx", description="PJX template toolkit")
    subparsers = parser.add_subparsers(dest="command")

    check_parser = subparsers.add_parser("check", help="Validate PJX templates")
    check_parser.add_argument("path", help="File or directory to check")
    check_parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if args.command == "check":
        sys.exit(cmd_check(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
