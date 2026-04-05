# PJX — System Design Document (SDD)

**Version:** 0.2.0
**Date:** 2026-04-04
**Status:** MVP Implemented

---

## 1. General Architecture

PJX operates as a preprocessor integrated into Jinja2 via a custom Loader. The preprocessor pipeline is modular — core processors are built-in, and extras (HTMX, Stimulus, Tailwind) are discovered at runtime via entry points.

```text
Template .jinja (PJX syntax)
        |
        v
+- PJXEnvironment (extends jinja2.Environment) -+
|                                                |
|  PJXLoader (wraps inner loader)                |
|    |                                           |
|    v                                           |
|  PreprocessorPipeline (dynamic)                |
|    Core:                                       |
|      1. FrontmatterProcessor                   |
|      2. VarsProcessor                          |
|      3. ComponentProcessor                     |
|      4. ControlFlowProcessor                   |
|    Extras (via entry points):                  |
|      5. HTMXAliasProcessor*                    |
|      6. StimulusAliasProcessor*                |
|    Core:                                       |
|      7. AttrsProcessor                         |
|      8. ExpressionProcessor                    |
|    |                                           |
|    v                                           |
|  Pure Jinja2 source -> native parser -> cache  |
+------------------------------------------------+
        |
        v
   Rendered HTML
```

*Loaded only when `pjx-htmx` / `pjx-stimulus` is installed.

### Principles

1. **Preprocessing via Loader** — uses `BaseLoader.get_source()` (public API)
2. **Sequential pipeline** — each processor receives a string, returns a string
3. **Opaque expressions** — PJX does not parse Python, passes it straight to Jinja2
4. **Autoescape by default** — `select_autoescape(["jinja", "html", "htm"])`
5. **Modular extras** — alias processors are discovered via entry points, not hard-coded

---

## 2. Monorepo Structure

```text
src/
  pjx/                          # Core package
    pjx/
      __init__.py                # Exports: PJXEnvironment, PJXLoader
      environment.py             # PJXLoader, PJXEnvironment, jinja_globals discovery
      router.py                  # PJXRouter, FormData, ActionResult, SSEEvent
      models.py                  # ImportDecl, PropDecl, SlotDecl, VarDecl, ComputedDecl
      errors.py                  # SourceLocation, Diagnostic, PJXError, PJXRenderError
      cli.py                     # CLI entrypoint (pjx check)
      core/
        types.py                 # ProcessorContext, ProcessorResult, PreprocessResult, Processor
        pipeline.py              # PreprocessorPipeline, ProcessorSlot, entry point discovery
        scanner.py               # Scanner, ScanToken, TagAttribute (?attr, ...spread)
        tag_utils.py             # format_attr, format_original_attr, rebuild_tag
        frontmatter.py           # FrontmatterProcessor (imports, props, slots, vars, computed)
        vars.py                  # VarsProcessor ({% set %} emission)
        components.py            # ComponentProcessor (include + children)
        flow.py                  # ControlFlowProcessor (<For>, <Show>, <Switch>, <Fragment>)
        attrs.py                 # AttrsProcessor (?attr, ...{spread})
        expressions.py           # ExpressionProcessor ({expr} -> {{ expr }})

  pjx-htmx/                     # Extra: HTMX + SSE aliases
    pjx_htmx/
      __init__.py                # Exports: HTMXAliasProcessor
      processor.py               # htmx:* -> hx-*, sse:* -> sse-*

  pjx-stimulus/                  # Extra: Stimulus aliases
    pjx_stimulus/
      __init__.py                # Exports: StimulusAliasProcessor
      processor.py               # stimulus:* -> data-* with controller stack

  pjx-tailwind/                  # Extra: Tailwind utilities
    pjx_tailwind/
      __init__.py                # Exports: cn
      cn.py                      # cn() class-name merging function
      setup.py                   # register_globals helper
```

---

## 3. PJXLoader + PJXEnvironment

### PJXLoader

Wraps any `BaseLoader` and preprocesses the source before returning it to Jinja2:

```python
class PJXLoader(BaseLoader):
    def __init__(self, inner: BaseLoader):
        self.inner = inner
        self.pipeline = PreprocessorPipeline()
        self.preprocess_cache: dict[str, PreprocessResult] = {}

    def get_source(self, environment, template):
        source, filename, uptodate = self.inner.get_source(environment, template)
        result = self.pipeline.process(source, filename=template)
        self.preprocess_cache[template] = result
        return result.source, filename, uptodate
```

### PJXEnvironment

Requires a `loader` argument. Wraps the loader with `PJXLoader`, enables autoescape by default, and discovers Jinja2 globals via `pjx.jinja_globals` entry points:

```python
class PJXEnvironment(Environment):
    def __init__(self, loader: BaseLoader, **kwargs):
        kwargs.setdefault("autoescape", select_autoescape(["jinja", "html", "htm"]))
        pjx_loader = PJXLoader(loader)
        super().__init__(loader=pjx_loader, **kwargs)
        self._discover_jinja_globals()  # loads cn() etc. from entry points
```

---

## 4. Preprocessor Pipeline

### ProcessorSlot

Each processor has a priority slot that determines execution order:

```python
class ProcessorSlot(IntEnum):
    FRONTMATTER = 10
    VARS = 15
    COMPONENT = 20
    CONTROL_FLOW = 30
    ALIAS = 40        # Used by extras (htmx, stimulus)
    ATTRS = 45
    EXPRESSION = 50
```

### Pipeline Construction

Core processors are registered in `__init__`. Extras are discovered via `importlib.metadata.entry_points(group="pjx.processors")`:

```python
class PreprocessorPipeline:
    def __init__(self):
        self._registry = []
        # Core processors (always present)
        self._register(ProcessorSlot.FRONTMATTER, FrontmatterProcessor())
        self._register(ProcessorSlot.VARS, VarsProcessor())
        self._register(ProcessorSlot.COMPONENT, ComponentProcessor())
        self._register(ProcessorSlot.CONTROL_FLOW, ControlFlowProcessor())
        self._register(ProcessorSlot.ATTRS, AttrsProcessor())
        self._register(ProcessorSlot.EXPRESSION, ExpressionProcessor())
        # Extras via entry points
        self._discover_extras()
```

### Processor Order (with all extras installed)

| Slot | Processor              | Source       | Description                                                |
| ---- | ---------------------- | ------------ | ---------------------------------------------------------- |
| 10   | FrontmatterProcessor   | core         | Parses frontmatter (imports, props, vars, computed, slots) |
| 15   | VarsProcessor          | core         | Emits `{% set %}` for vars and computed                    |
| 20   | ComponentProcessor     | core         | PascalCase tags -> `{% include %}`                         |
| 30   | ControlFlowProcessor   | core         | `<For>`, `<Show>`, `<Switch>`, `<Fragment>`                |
| 40   | HTMXAliasProcessor     | pjx-htmx     | `htmx:*` -> `hx-*`, `sse:*` -> `sse-*`                     |
| 40   | StimulusAliasProcessor | pjx-stimulus | `stimulus:*` -> `data-*` with scope                        |
| 45   | AttrsProcessor         | core         | `?attr={expr}`, `...{spread}`                              |
| 50   | ExpressionProcessor    | core         | `{expr}` -> `{{ expr }}`                                   |

---

## 5. Detailed Processors

### 5.1 FrontmatterProcessor

Parses the `---` block. Supports:

- `from ..module import Name` (imports)
- `props:` block with `name: type = default`
- `vars:` block — scalar (`name: "value"`) and map (indented key-value pairs)
- `computed:` block — `name: expression`
- `slot name`

### 5.2 VarsProcessor

Emits `{% set %}` blocks for vars and computed values at the top of the template body:

- Scalar vars: `{% set color = "blue" %}`
- Map vars: `{% set sizes = {"sm": "h-8 px-3", "md": "h-10 px-4"} %}`
- Computed: `{% set full_name = first ~ " " ~ last %}`

### 5.3 ComponentProcessor

Imported uppercase tags compiled to `{% include %}` + `{% with %}`. Children use `{% set content %}`. Recursive.

### Import Resolution

```text
from ..layouts import Base     -> layouts/Base.jinja (relative)
from components import Card    -> components/Card.jinja (absolute)
```

Resolved paths are validated: `..` segments and `/` prefixes are rejected.

### 5.4 ControlFlowProcessor

| PJX                                 | Jinja2                               |
| ----------------------------------- | ------------------------------------ |
| `<For each={items} as="item">`      | `{% for item in items %}`            |
| `<Show when={cond}>`                | `{% if cond %}`                      |
| `<Else>`                            | `{% else %}`                         |
| `<Switch expr={x}><Case value="a">` | `{% if x == "a" %}`                  |
| `<Fragment>`                        | (removed — children render directly) |

### 5.5 HTMXAliasProcessor (pjx-htmx)

`htmx:{name}` -> `hx-{name}`, `sse:{name}` -> `sse-{name}`. Simple prefix mapping, no state.

### 5.6 StimulusAliasProcessor (pjx-stimulus)

Maintains a controller stack for scope resolution:

- `stimulus:controller="name"` -> `data-controller="name"` (enters scope)
- `stimulus:target="name"` -> `data-{ctrl}-target="name"` (resolves from stack)
- Multi-controller requires explicit: `stimulus:target.dropdown="menu"`

### 5.7 AttrsProcessor

- `?attr={expr}` -> `{% if expr %}attr="{{ expr }}"{% endif %}`
- `...{dict}` -> `{{ dict | xmlattr }}`

### 5.8 ExpressionProcessor

`{expr}` in attributes -> `{{ expr }}`. Does not affect `{{ }}` text or string literals.

---

## 6. PJXRouter

Extends `fastapi.APIRouter`. Accepted by `app.include_router()`.

```python
class PJXRouter(APIRouter):
    def __init__(self, templates: Jinja2Templates, **kwargs):
        super().__init__(**kwargs)
        self._templates = templates
```

### Template Context

All decorators build context via `_build_context()`:

```python
context = {"request": request, "props": props, "params": dict(request.path_params)}
```

### FormData() — Form Validation via Depends

```python
@ui.action("/users", success_template="...", error_template="...")
async def create_user(request: Request, data: CreateUserForm = FormData(CreateUserForm)):
    ...
```

`FormData()` returns a `Depends()` dependency that reads form data, validates with Pydantic, and stores errors on `request.state` (namespaced key `_pjx_form_validation_error`).

### HTTP Method Validation

`fragment()` and `action()` validate `method` against `_ALLOWED_HTTP_METHODS` (frozenset of standard HTTP methods) before dispatch.

### Rendering

Template rendering errors are caught as `jinja2.TemplateError` and re-raised as `PJXRenderError`.

---

## 7. Entry Points

### pjx.processors

Used by `PreprocessorPipeline._discover_extras()` to register alias processors:

```toml
# pjx-htmx/pyproject.toml
[project.entry-points."pjx.processors"]
htmx = "pjx_htmx:HTMXAliasProcessor"

# pjx-stimulus/pyproject.toml
[project.entry-points."pjx.processors"]
stimulus = "pjx_stimulus:StimulusAliasProcessor"
```

Each processor class declares a `slot` class attribute (default: `ProcessorSlot.ALIAS = 40`).

### pjx.jinja_globals

Used by `PJXEnvironment._discover_jinja_globals()` to register template functions:

```toml
# pjx-tailwind/pyproject.toml
[project.entry-points."pjx.jinja_globals"]
cn = "pjx_tailwind.cn:cn"
```

---

## 8. Static Analysis (checker.py)

`pjx check` performs compile-time validation:

- **Import resolution** (PJX301) — verifies imports can be resolved
- **File existence** (PJX302) — warns if resolved file not found on disk
- **Computed cycles** (PJX303) — detects circular dependencies in `computed:`
- **Undefined vars** (PJX304) — warns about variables not defined in props/vars/computed

Uses `check_template()` per file and `check_directory()` for batch validation.

---

## 9. Template Cache (cache.py)

`TemplateCache` provides mtime-based invalidation for preprocessed templates. Integrated into `PJXLoader`:

1. On `get_source()`, check cache for template name
2. If cached and file mtime unchanged, return cached result (skip preprocessing)
3. If miss or stale, preprocess and cache the result

No configuration needed. Transparent to users.

---

## 10. Formatter (formatter.py)

`pjx format` canonicalizes frontmatter section order:

1. imports (`from X import Y`)
2. `props:`
3. `vars:`
4. `computed:`
5. `slot` declarations

Idempotent. Supports `--check` mode for CI (exit 1 if changes needed).

---

## 11. SEO (seo.py)

Pure functions for sitemap/robots generation:

- `discover_pages(templates_dir)` — finds `.jinja` files in `pages/`, skips 404/500/dynamic routes
- `generate_sitemap(entries, base_url)` — produces XML sitemap
- `generate_robots(base_url, disallow)` — produces robots.txt

---

## 12. Error System

| Code     | Category                           |
| -------- | ---------------------------------- |
| `PJX0xx` | General preprocessor (frontmatter) |
| `PJX1xx` | Control flow                       |
| `PJX2xx` | Components                         |
| `PJX3xx` | Imports                            |
| `PJX4xx` | Aliases (Stimulus)                 |
| `PJX5xx` | Runtime/Decorators                 |
| `PJX9xx` | Internal                           |

---

## 13. Design Decisions

### D-01: Custom Loader (not `_parse`)

Uses `BaseLoader.get_source()` — stable public API.

### D-02: PJXRouter extends APIRouter

Accepted by `app.include_router()`. No wrapper class needed.

### D-03: Autoescape by default

XSS impossible without explicit `| safe`.

### D-04: Opaque expressions

PJX does not parse Python. Validation happens at render-time.

### D-05: Components via include

`{% include %}` + `{% with %}`. Children use `{% set content %}`.

### D-06: Scanner (not global regex)

State machine for tags/attributes. Supports `?attr`, `...{spread}`, nested expressions.

### D-07: FormData via Depends

No `inspect.signature` manipulation. Uses FastAPI's native DI.

### D-08: response_model=None on PJX routes

Prevents OpenAPI schema generation for internal Props.

### D-09: params in context

`request.path_params` injected as `params`. Enables `[slug]` convention.

### D-10: Path traversal protection

`resolve_import()` rejects paths with `..` segments or `/` prefix.

### D-11: HTTP method allowlist

`fragment()`/`action()` validate against explicit set, preventing arbitrary dispatch.

### D-12: Modular extras via entry points

HTMX, Stimulus, Tailwind are separate packages. Pipeline discovers them via `importlib.metadata.entry_points`. Core works standalone.

### D-13: Shared tag utilities

`format_attr`, `format_original_attr`, `rebuild_tag` in `tag_utils.py` — shared between core and extras to avoid duplication.
