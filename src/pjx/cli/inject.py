"""``pjx inject`` — inject PJX skill files and AI agent configs into a project."""

from __future__ import annotations

import importlib.resources
import shutil
from pathlib import Path

import typer

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


def _copy_tree(src: Path, dest: Path) -> list[Path]:
    """Copy a directory tree, returning list of created files."""
    created: list[Path] = []
    for item in sorted(src.rglob("*")):
        if item.is_dir():
            continue
        rel = item.relative_to(src)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        created.append(target)
    return created


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
    directory: Path = typer.Argument(Path("."), help="Project directory"),
    skills: bool = typer.Option(
        True, "--skills/--no-skills", help="Inject skills/ directory"
    ),
    claude: bool = typer.Option(
        False, "--claude", help="Inject .claude/ with CLAUDE.md and skills"
    ),
    agents: bool = typer.Option(
        False, "--agents", help="Inject .agents/skills/ directory"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files"),
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
        typer.echo("ERROR: bundled skills not found in pjx package", err=True)
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
            typer.echo("  created CLAUDE.md")
            total += 1
        else:
            typer.echo("  skipped CLAUDE.md (exists, use --force)")

    if agents:
        dest = directory / ".agents" / "skills"
        total += _inject_dir(src, dest, ".agents/skills/", force)

    if total == 0:
        typer.echo("Nothing to inject. Use --skills, --claude, or --agents.")
    else:
        typer.echo(f"\nInjected {total} file(s) into {directory}")


def _inject_dir(src: Path, dest: Path, label: str, force: bool) -> int:
    """Copy skill files from src to dest, return count of created files."""
    count = 0
    for item in sorted(src.rglob("*")):
        if item.is_dir():
            continue
        rel = item.relative_to(src)
        target = dest / rel
        if target.exists() and not force:
            typer.echo(f"  skipped {label}{rel} (exists)")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        typer.echo(f"  created {label}{rel}")
        count += 1
    return count
