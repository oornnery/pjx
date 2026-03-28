"""``pjx inject`` — inject PJX skill files and AI agent configs into a project."""

from __future__ import annotations

import importlib.resources
import shutil
from pathlib import Path
from typing import Annotated

import typer

from pjx.cli.common import DirArg, console

app = typer.Typer()


def _skills_source() -> Path:
    """Resolve the bundled skills/ directory from the pjx package.

    In installed mode, skills are at ``pjx/skills/`` (via force-include).
    In dev mode (editable install), falls back to the project root ``skills/``.
    """
    # Installed: pjx/skills/ inside site-packages
    pkg_path = Path(str(importlib.resources.files("pjx").joinpath("skills")))
    if pkg_path.is_dir():
        return pkg_path
    # Dev: project root skills/
    src_dir = Path(str(importlib.resources.files("pjx")))
    project_root = src_dir.parent.parent  # src/pjx → src → project root
    dev_path = project_root / "skills"
    if dev_path.is_dir():
        return dev_path
    return pkg_path


_CLAUDE_MD = """\
# CLAUDE.md

## Skills

On-demand knowledge modules. Load the relevant skill when working in its domain.

| Skill           | When to use                                       |
| --------------- | ------------------------------------------------- |
| `pjx/SKILL.md` | PJX DSL, components, routing, FastAPI integration |

Each skill is in `skills/`. Load on demand with `@skills/pjx/SKILL.md`.
"""

_AGENTS_MD = """\
# .agents/ configuration

## Skills

Agent skills are available in `.agents/skills/`.

| Skill           | When to use                                       |
| --------------- | ------------------------------------------------- |
| `pjx/SKILL.md` | PJX DSL, components, routing, FastAPI integration |
"""


@app.command()
def inject(
    directory: DirArg = Path("."),
    skills: Annotated[
        bool, typer.Option("--skills/--no-skills", help="Inject skills/ directory")
    ] = True,
    claude: Annotated[
        bool, typer.Option("--claude", help="Inject .claude/ with CLAUDE.md and skills")
    ] = False,
    agents: Annotated[
        bool, typer.Option("--agents", help="Inject .agents/skills/ directory")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Overwrite existing files")
    ] = False,
) -> None:
    """Inject PJX skill files and AI agent configs into a project.

    By default, copies the PJX skill into ``skills/pjx/``.

    Use ``--claude`` to also generate a ``.claude/`` directory with
    ``CLAUDE.md`` pointing to the skill.

    Use ``--agents`` to copy skills into ``.agents/skills/`` for
    agent frameworks that use that convention.
    """
    directory = directory.resolve()
    src = _skills_source()

    if not src.exists():
        console.print(
            "[red]ERROR:[/red] bundled skills not found in pjx package", stderr=True
        )
        raise typer.Exit(1)

    total = 0

    if skills:
        dest = directory / "skills"
        total += _inject_dir(src, dest, "skills/", force)

    if claude:
        dest = directory / ".claude" / "skills"
        total += _inject_dir(src, dest, ".claude/skills/", force)

        claude_md = directory / "CLAUDE.md"
        if not claude_md.exists() or force:
            claude_md.write_text(_CLAUDE_MD, encoding="utf-8")
            console.print("  [green]created[/green] CLAUDE.md")
            total += 1
        else:
            console.print("  [yellow]skipped[/yellow] CLAUDE.md (exists, use --force)")

    if agents:
        dest = directory / ".agents" / "skills"
        total += _inject_dir(src, dest, ".agents/skills/", force)

    if total == 0:
        console.print("Nothing to inject. Use --skills, --claude, or --agents.")
    else:
        console.print(f"\nInjected {total} file(s) into {directory}")


def _inject_dir(src: Path, dest: Path, label: str, force: bool) -> int:
    """Copy skill files from src to dest, return count of created files."""
    count = 0
    for item in sorted(src.rglob("*")):
        if item.is_dir():
            continue
        rel = item.relative_to(src)
        target = dest / rel
        if target.exists() and not force:
            console.print(f"  [yellow]skipped[/yellow] {label}{rel} (exists)")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        console.print(f"  [green]created[/green] {label}{rel}")
        count += 1
    return count
