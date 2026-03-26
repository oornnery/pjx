# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

PJX is a Python DSL for reactive `.jinja` components, inspired by JSX, Svelte
and SolidJS. It compiles a declarative component syntax (props, state, slots,
imports, control flow) down to Jinja2 + HTMX + Alpine.js. The full DSL
specification lives in `docs/IDEA.md`, technical spec in `docs/SPEC.md`.

## Stack

- **Language**: Python 3.14+
- **Package manager**: uv
- **Linter/Formatter**: ruff
- **Type checker**: ty
- **Test runner**: pytest
- **Markdown lint**: rumdl
- **Runtime deps**: FastAPI, Jinja2, minijinja, Pydantic, Rich, Typer, Uvicorn

## Quick Commands

```bash
rtk uv sync                          # Install deps from lockfile
rtk uv run ruff format .             # Format
rtk uv run ruff check . --fix        # Lint
rtk uv run ty check                  # Type check
rtk uv run pytest -v                 # Test all
rtk uv run pytest tests/test_foo.py::test_bar -v  # Single test
rtk uv run rumdl check .             # Markdown lint
```

## Validation (run in order, fail fast)

```bash
rtk uv run ruff format --check .
rtk uv run ruff check .
rtk uv run rumdl check .
rtk uv run ty check
rtk uv run pytest -v
```

## Skills

On-demand knowledge modules in `.agents/skills/`. Load the relevant skill
when working in its domain.

| Skill               | When to use                                       |
| ------------------- | ------------------------------------------------- |
| `python/SKILL.md`   | Python code, conventions, async, uv toolchain     |
| `fastapi/SKILL.md`  | FastAPI routes, dependencies, middleware          |
| `jx/SKILL.md`       | Jinja server-rendered components (JX patterns)    |
| `frontend/SKILL.md` | JS/CSS tooling, Tailwind, Alpine.js, HTMX         |
| `commit/SKILL.md`   | Small logical commits with conventional messages  |
| `refactor/SKILL.md` | Code audit, clean code, SOLID, security review    |

Each skill has a `references/` folder with detailed submodules. Load on demand.

## Conventions

- Use `pathlib` over `os.path`
- f-strings only
- `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE` constants
- Type all public functions
- Use `Annotated` style for FastAPI parameters and dependencies
- `logging` for app logs, `rich` for CLI output — never `print`
- Pydantic `BaseModel` for validation, `dataclass` for plain data
- IO at edges only — services and domain must be pure
- Prefer `uv` over direct `pip` workflows
- Never commit code that fails `ruff check`

## Code Quality

- **Clean Code**: small single-responsibility functions, descriptive names
  that make comments unnecessary, no dead or duplicated code
- **Pythonic**: use language idioms (comprehensions, context managers,
  itertools, `enumerate`, unpacking) — avoid C-style loops
- **SOLID**: each module/class has a single reason to change (SRP), depend
  on abstractions not concrete implementations (DIP), prefer composition
  over inheritance
- **Type safety**: type hints on all public functions and models; use
  `Protocol` / `ABC` for contracts between layers

## Tests

- All new or changed code must include tests
- Keep coverage high — cover happy path, edge cases, and expected errors
- Unit tests for pure logic, integration tests for IO and endpoints
- Descriptive test names: `test_<unit>_<scenario>_<expected>`
- Use fixtures and parametrize to avoid repetition

## Documentation

- Update docstrings (Google style) on all public functions/classes created
  or modified
- Keep `README.md` up to date when installation, usage, or architecture changes
- Add usage examples in `examples/` for each public feature — short
  self-contained scripts that demonstrate real API usage
- Update `docs/IDEA.md` if the implementation diverges from the spec
