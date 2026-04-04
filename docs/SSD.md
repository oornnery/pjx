# PJX — System Design Document (SSD)

**Version:** 0.2.0
**Date:** 2026-04-04
**Status:** MVP Implemented

---

## 1. General Architecture

PJX operates as a preprocessor integrated into Jinja2 via a custom Loader.

```
Template .jinja (PJX syntax)
        │
        ▼
┌─ PJXEnvironment (extends jinja2.Environment) ─┐
│                                                │
│  PJXLoader (wraps inner loader)                │
│    │                                           │
│    ▼                                           │
│  PreprocessorPipeline                          │
│    1. FrontmatterProcessor                     │
│    2. ComponentProcessor                       │
│    3. ControlFlowProcessor                     │
│    4. AliasProcessor                           │
│    5. ExpressionProcessor                      │
│    │                                           │
│    ▼                                           │
│  Pure Jinja2 source → native parser → cache    │
└────────────────────────────────────────────────┘
        │
        ▼
   Rendered HTML
```

### Principles

1. **Preprocessing via Loader** — uses `BaseLoader.get_source()` (public API), not `_parse` (private)
2. **Sequential pipeline** — each processor receives a string, returns a string
3. **Opaque expressions** — PJX does not parse Python, passes it straight to Jinja2
4. **Autoescape by default** — `select_autoescape(["jinja", "html", "htm"])`

---

## 2. Module Structure

```
pjx/
├── __init__.py         # Exports: PJXEnvironment, PJXLoader
├── environment.py      # PJXLoader, PJXEnvironment
├── router.py           # PJXRouter (extends APIRouter)
├── models.py           # ImportDecl, PropDecl, SlotDecl, TemplateMetadata
├── errors.py           # SourceLocation, Diagnostic, PJXError, PJXRenderError, SourceMap
├── cli.py              # CLI entrypoint (pjx check)
└── core/
    ├── __init__.py     # Exports: PreprocessorPipeline, PreprocessResult
    ├── pipeline.py     # PreprocessorPipeline, ProcessorContext, ProcessorResult
    ├── scanner.py      # Scanner, ScanToken, ScanTokenType, TagAttribute
    ├── frontmatter.py  # FrontmatterProcessor
    ├── flow.py         # ControlFlowProcessor
    ├── aliases.py      # AliasProcessor
    ├── components.py   # ComponentProcessor
    └── expressions.py  # ExpressionProcessor
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

The `filename` passed to the pipeline is the relative template name (not the absolute filesystem path), so that import resolution works correctly.

### PJXEnvironment

```python
class PJXEnvironment(Environment):
    def __init__(self, loader=None, **kwargs):
        kwargs.setdefault("autoescape", select_autoescape(["jinja", "html", "htm"]))
        pjx_loader = PJXLoader(loader) if loader else None
        super().__init__(loader=pjx_loader, **kwargs)

    def get_preprocessed_source(self, template_name):
        """Returns the intermediate Jinja2 for debugging."""
        ...
```

---

## 4. Preprocessor Pipeline

### Processor Order

| # | Processor | Input | Output |
|---|-----------|-------|--------|
| 1 | FrontmatterProcessor | Source with `---` | Source without frontmatter + metadata |
| 2 | ComponentProcessor | Source with `<Component>` | Source with `{% include %}` |
| 3 | ControlFlowProcessor | Source with `<For>/<Show>/<Switch>` | Source with `{% for/if %}` |
| 4 | AliasProcessor | Source with `htmx:*/stimulus:*/sse:*` | Source with `hx-*/data-*/sse-*` |
| 5 | ExpressionProcessor | Source with `{expr}` in attrs | Source with `{{ expr }}` |

### ProcessorContext

Shared between processors. The FrontmatterProcessor populates `ctx.metadata`, which the ComponentProcessor uses to resolve imports.

```python
@dataclass
class ProcessorContext:
    filename: str | None = None
    metadata: TemplateMetadata | None = None
```

---

## 5. Detailed Processors

### 5.1 FrontmatterProcessor

Parses the `---` block at the top. Extracts `ImportDecl`, `PropDecl`, `SlotDecl`. Removes the frontmatter from the source.

Supports:
- `from ..module import Name` (relative imports)
- `from module import Name` (absolute imports)
- `props:` block with `name: type = default`
- `slot name`

### 5.2 ComponentProcessor

Imported uppercase tags are compiled to `{% include %}`:

**Self-closing** (`<Card title="x" />`):
```jinja2
{% with title="x" %}{% include "components/Card.jinja" %}{% endwith %}
```

**With children** (`<Base title="x">...content...</Base>`):
```jinja2
{% set content %}...content...{% endset %}
{% with title="x", content=content %}{% include "layouts/Base.jinja" %}{% endwith %}
```

Children are processed recursively (nested components work).

### Import Resolution

```
from ..layouts import Base     → layouts/Base.jinja (relative)
from .partials import Header   → pages/partials/Header.jinja (same dir)
from components import Card    → components/Card.jinja (absolute)
```

### 5.3 ControlFlowProcessor

| PJX | Jinja2 |
|-----|--------|
| `<For each={items} as="item">` | `{% for item in items %}` |
| `</For>` | `{% endfor %}` |
| `<Show when={cond}>` | `{% if cond %}` |
| `<Else>` | `{% else %}` |
| `</Show>` | `{% endif %}` |
| `<Switch expr={x}><Case value="a">` | `{% if x == "a" %}` |
| `<Case value="b">` | `{% elif x == "b" %}` |
| `<Default>` | `{% else %}` |
| `</Switch>` | `{% endif %}` |

### 5.4 AliasProcessor

**HTMX:** `htmx:{name}` → `hx-{name}` (all attributes)

**Stimulus:**

| Input | Output |
|-------|--------|
| `stimulus:controller="name"` | `data-controller="name"` |
| `stimulus:action="..."` | `data-action="..."` |
| `stimulus:target="name"` | `data-{ctrl}-target="name"` |
| `stimulus:target.{ctrl}="name"` | `data-{ctrl}-target="name"` (multi-controller) |
| `stimulus:value-{key}="val"` | `data-{ctrl}-{key}-value="val"` |

The processor maintains a controller stack. In multi-controller scope, the short form is rejected with an error — explicit selection via `.{ctrl}` is required.

**SSE:** `sse:{name}` → `sse-{name}`

### 5.5 ExpressionProcessor

`{expr}` in attributes → `{{ expr }}`:

```
attr={value}  →  attr="{{ value }}"
```

Does not affect `{{ }}` in text (pass-through) nor attributes with string literals.

---

## 6. PJXRouter

Extends `fastapi.APIRouter`. Accepted by `app.include_router()`.

```python
class PJXRouter(APIRouter):
    def __init__(self, templates, **kwargs):
        super().__init__(**kwargs)
        self._templates = templates
```

### Template Context

All decorators inject into the context:

```python
context = {
    "request": request,
    "props": props,        # BaseModel returned by the handler
    "params": dict(request.path_params),  # URL path params
}
```

### Decorators

**`page(path, response_template)`** — GET + HTMLResponse
- Uses `@wraps(func)` to preserve Depends
- Sets `response_model=None` to avoid OpenAPI conflict
- Registers via `self.get(path)`

**`fragment(path, response_template, method=)`** — any method + HTMLResponse
- Same as page, but with configurable method
- Propagates `__htmx_headers__` if present in props

**`action(path, form=, success_template=, error_template=, method=)`** — form validation
- Uses `_build_action_wrapper` to expose `Depends` without exposing `data`
- Validates form via `form.model_validate(payload)`
- 422: renders `error_template` with `errors` and `form_data`
- 200: renders `success_template` with `props`
- Supports `ActionResult(data, status)` for custom status

**`stream(path, response_template)`** — SSE
- Async generator that yields props or `SSEEvent`
- `_format_sse_data` prefixes each line with `data:`
- Supports `id:` and `event:` via `SSEEvent`

**`render(response_template, context)`** — public helper
- For use outside of decorators (error pages, emails, etc.)

### Dependency Injection

`@ui.page` and `@ui.fragment` use `@wraps(func)`, so `Depends()` works naturally.

`@ui.action` uses `_build_action_wrapper` which copies the `Depends` parameters from the original handler to the wrapper, excluding `request` and `data`:

```python
def _build_action_wrapper(func):
    sig = inspect.signature(func)
    dep_params = [p for name, p in sig.parameters.items() if name not in ("request", "data")]
    new_params = [Parameter("request", ..., annotation=Request)] + dep_params
    wrapper.__signature__ = sig.replace(parameters=new_params)
```

---

## 7. Error System

### Categories

| Code | Category |
|------|----------|
| `PJX0xx` | General preprocessor (frontmatter) |
| `PJX1xx` | Control flow |
| `PJX2xx` | Components |
| `PJX3xx` | Imports |
| `PJX4xx` | Aliases (Stimulus) |
| `PJX5xx` | Runtime/Decorators |
| `PJX9xx` | Internal |

### PJXError

Preprocessing error with source location:

```
error[PJX101]: Tag <For> requires attribute 'each'
  --> templates/pages/dashboard.jinja:15:5
  = hint: use <For each={items} as="item">
```

### PJXRenderError

Render-time error with template and phase:

```
PJXRenderError (render)
  template: pages/home.jinja
  cause: UndefinedError("'props' is undefined")
```

---

## 8. Scanner

State machine that tokenizes HTML-like syntax:

- `OPEN_TAG`, `CLOSE_TAG`, `SELF_CLOSING_TAG`
- `TEXT`, `COMMENT`
- Attributes with namespace (`htmx:get`, `stimulus:controller`)
- Expressions in attributes (`{expr}`)
- Strings inside expressions (does not break on `}` inside `"..."`)

Does not build a tree — emits a linear sequence of tokens.

---

## 9. Testing Strategy

```
tests/
├── conftest.py                    # Golden file fixtures
├── preprocessor/
│   ├── test_pipeline.py           # Golden files + pipeline e2e
│   ├── test_frontmatter.py        # Frontmatter parsing
│   ├── test_control_flow.py       # <For>, <Show>, <Switch>
│   ├── test_aliases.py            # htmx, stimulus, sse
│   ├── test_components.py         # Components + imports
│   └── test_expressions.py        # {expr} → {{ expr }}
├── fastapi/
│   └── test_decorators.py         # @ui.page/fragment/action
└── fixtures/
    ├── basic/                     # input.jinja + expected.jinja
    ├── for_loop/
    ├── show_else/
    ├── switch/
    ├── htmx_aliases/
    ├── stimulus_aliases/
    ├── frontmatter/
    └── expressions/
```

---

## 10. Design Decisions

### D-01: Custom Loader (not `_parse`)

Uses `BaseLoader.get_source()` — a public and stable API. Ensures compatibility with future Jinja2 versions.

### D-02: PJXRouter extends APIRouter

`PJXRouter` is a valid `APIRouter`. Accepted by `app.include_router()`. No separate wrapper class needed.

### D-03: Autoescape by default

`select_autoescape(["jinja", "html", "htm"])`. XSS impossible without explicit `| safe`.

### D-04: Opaque expressions

PJX does not parse Python. `{expr}` and `{{ expr }}` are opaque strings passed to Jinja2. Validation happens at render-time.

### D-05: Components via include

Components use `{% include %}` + `{% with %}`. Children use `{% set content %}`. Recursive (components inside components).

### D-06: Scanner (not global regex)

State machine for parsing tags and attributes. Regex does not handle nested expressions and strings well.

### D-07: Depends in @ui.action

`_build_action_wrapper` copies `Depends` parameters from the handler to the wrapper, excluding `data`. FastAPI resolves the dependencies normally.

### D-08: response_model=None on PJX routes

Prevents FastAPI from trying to generate a JSON schema for Props (which are internal, not a response). OpenAPI `/docs` works without errors.

### D-09: params in context

`request.path_params` is automatically injected as `params` into the template context. Enables the `[slug]` convention in file names.
