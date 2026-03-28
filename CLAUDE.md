# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

PJX is a Python DSL for reactive `.jinja` components, inspired by JSX, Svelte,
SolidJS, and the Next.js App Router. It compiles a declarative component syntax
(props, state, slots, imports, control flow) down to Jinja2 + HTMX + Alpine.js,
with server actions, HTTP caching, SSG, streaming HTML, and SEO helpers. The full
DSL specification lives in `docs/dev/IDEA.md`, technical spec in `docs/dev/SPEC.md`.

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
rtk uv run task format               # Format (ruff)
rtk uv run task lint                 # Lint + autofix (ruff)
rtk uv run task check                # Format + lint + markdown lint
rtk uv run task typecheck            # Type check (ty)
rtk uv run task test                 # Run all tests
rtk uv run task cov                  # Tests with coverage report
rtk uv run task ci                   # Full CI: check + typecheck + test
rtk uv run pytest tests/test_foo.py::test_bar -v  # Single test
rtk uv run pjx analyze examples/demo    # Route and bundle analysis
rtk uv run pjx sitemap examples/demo    # Generate sitemap.xml
rtk uv run pjx robots examples/demo     # Generate robots.txt
rtk uv run pjx inject . --claude    # Inject skills + CLAUDE.md
```

## Validation (run in order, fail fast)

```bash
rtk uv run task ci
```

Or manually:

```bash
rtk uv run task check
rtk uv run task typecheck
rtk uv run task test
```

## Skills

On-demand knowledge modules in `skills/`. Load the relevant skill
when working in its domain.

| Skill             | When to use                                          |
| ----------------- | ---------------------------------------------------- |
| `pjx/SKILL.md`   | PJX DSL, components, routing, FastAPI integration    |

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
- Update `docs/dev/IDEA.md` if the implementation diverges from the spec
