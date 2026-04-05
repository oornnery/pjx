# PJX Skill

PJX is a Jinja2 preprocessor with JSX-like syntax for FastAPI + HTMX + Stimulus.

## What PJX Does

PJX transforms declarative template syntax into standard Jinja2 at load time.
You write `<For>`, `<Show>`, `htmx:post` — PJX generates `{% for %}`, `{% if %}`, `hx-post`.

## Architecture

Modular monorepo with 4 packages:

- **pjx** — core preprocessor, router, CLI
- **pjx-htmx** — `htmx:*` and `sse:*` aliases (optional)
- **pjx-stimulus** — `stimulus:*` aliases (optional)
- **pjx-tailwind** — `cn()` class merging (optional)

Pipeline: `Frontmatter -> Vars -> Component -> ControlFlow -> [HTMX]* -> [Stimulus]* -> Attrs -> Expression`

Extras are discovered via `importlib.metadata.entry_points`.

## Key Files

- `src/pjx/pjx/core/pipeline.py` — pipeline orchestration + entry point discovery
- `src/pjx/pjx/core/frontmatter.py` — parses `---` blocks (imports, props, vars, computed, slots)
- `src/pjx/pjx/core/scanner.py` — HTML tokenizer (state machine, supports `?attr`, `...{spread}`)
- `src/pjx/pjx/router.py` — PJXRouter (page, fragment, action, stream)
- `src/pjx/pjx/checker.py` — static analysis (imports, cycles, undefined vars)
- `src/pjx/pjx/formatter.py` — frontmatter canonicalization
- `src/pjx/pjx/cache.py` — mtime-based template cache
- `src/pjx/pjx/seo.py` — sitemap/robots generation

## Best Practices

### DO

- Use `from __future__ import annotations` in all files
- Use `@dataclass(frozen=True, slots=True)` for immutable data
- Use `tuple` (not `list`) in frozen dataclasses
- Keep processors stateless — each receives a string, returns a string
- Use the `Processor` protocol from `pjx.core.types`
- Register extras via entry points, not hard-coded imports
- Use `tag_utils.py` helpers for shared tag formatting
- Validate paths in `resolve_import()` — reject `..` and `/`
- Use `_validate_method()` for HTTP method dispatch
- Catch `jinja2.TemplateError`, not bare `Exception`
- Namespace `request.state` keys with `_pjx_` prefix
- Write golden file tests for preprocessor changes
- Keep frontmatter in canonical order: imports, props, vars, computed, slots

### DON'T

- Don't use `{% %}` syntax in PJX templates — use DSL (`<Show>`, `<For>`, etc.)
- Don't use lazy imports inside `__init__` — use `types.py` to break cycles
- Don't hardcode processors in the pipeline — use entry points
- Don't catch `Exception` broadly in rendering paths
- Don't store mutable objects (`list`) in frozen dataclasses
- Don't use `getattr(self, method)` without an allowlist
- Don't create new `ComponentProcessor()` instances for recursion — use `self`
- Don't accept user-uploaded templates (import resolution can include files)
- Don't skip autoescape — it's on by default for a reason

## References

- [Syntax and DSL](references/syntax.md)
- [Router Patterns](references/router.md)
- [Testing Guide](references/testing.md)
