# PJX — Product Requirements Document (PRD)

**Version:** 0.2.0
**Date:** 2026-04-04
**Status:** MVP Implemented

---

## 1. Overview

PJX is a Python toolkit that extends Jinja2 with declarative JSX-inspired syntax for building server-rendered interfaces with FastAPI, HTMX, and Stimulus.

**PJX is not a web framework.** It is a modular library:

- **pjx** (core) — preprocessor pipeline, FastAPI router, CLI
- **pjx-htmx** — HTMX and SSE alias processors
- **pjx-stimulus** — Stimulus alias processor with controller scope tracking
- **pjx-tailwind** — `cn()` class-name merging utility

### Value Proposition

Modern framework DX (components, typing, aliases, template variables, conditional attributes) with pure SSR (Jinja2 + HTMX). No reactive client-side runtime, no build step — the generated Jinja2 is always inspectable.

---

## 2. Package Architecture

```text
src/
  pjx/                       # Core package
    pjx/
      __init__.py             # PJXEnvironment, PJXLoader
      environment.py          # PJXEnvironment + entry point discovery
      router.py               # PJXRouter, FormData, ActionResult, SSEEvent
      models.py               # ImportDecl, PropDecl, SlotDecl, VarDecl, ComputedDecl
      errors.py               # PJXError, PJXRenderError, Diagnostic
      cli.py                  # CLI (pjx check)
      core/
        pipeline.py           # PreprocessorPipeline + ProcessorSlot + entry point discovery
        types.py              # ProcessorContext, ProcessorResult, Processor protocol
        scanner.py            # Scanner (state machine, ?attr, ...{spread})
        tag_utils.py          # Shared helpers (format_attr, rebuild_tag)
        frontmatter.py        # FrontmatterProcessor (imports, props, slots, vars, computed)
        vars.py               # VarsProcessor ({% set %} emission)
        components.py         # ComponentProcessor (include + children)
        flow.py               # ControlFlowProcessor (<For>, <Show>, <Switch>, <Fragment>)
        attrs.py              # AttrsProcessor (?attr, ...{spread})
        expressions.py        # ExpressionProcessor ({expr} -> {{ expr }})

  pjx-htmx/                  # HTMX + SSE aliases
    pjx_htmx/
      processor.py            # HTMXAliasProcessor

  pjx-stimulus/              # Stimulus aliases
    pjx_stimulus/
      processor.py            # StimulusAliasProcessor

  pjx-tailwind/              # Tailwind utilities
    pjx_tailwind/
      cn.py                   # cn() class-name merging
      setup.py                # register_globals helper
```

---

## 3. FastAPI Integration

```python
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from jinja2 import FileSystemLoader
from pjx import PJXEnvironment
from pjx.router import PJXRouter

app = FastAPI()
templates = Jinja2Templates(
    env=PJXEnvironment(loader=FileSystemLoader("templates"))
)
ui = PJXRouter(templates)
app.include_router(ui)
```

### PJXEnvironment

Extends `jinja2.Environment`. Requires a `loader` argument. Wraps the loader with `PJXLoader` which preprocesses PJX syntax before Jinja2 parses it. Enables `autoescape` by default. Discovers Jinja2 globals (like `cn()`) via `pjx.jinja_globals` entry points.

### PJXRouter

Extends `fastapi.APIRouter`. Adds decorators for rendering templates:

| Decorator                                                       | Description                                             |
| --------------------------------------------------------------- | ------------------------------------------------------- |
| `@ui.page(path, template)`                                      | Renders a full page (GET)                               |
| `@ui.fragment(path, template, method=)`                         | Renders partial HTML (HTMX)                             |
| `@ui.action(path, success_template=, error_template=, method=)` | Validates form via `FormData()` + renders success/error |
| `@ui.stream(path, template)`                                    | SSE streaming                                           |
| `ui.render(template, context)`                                  | Manual render (error pages, etc.)                       |

All decorators inject: `props`, `params`, `request`.

---

## 4. PJX Syntax

### 4.1 Frontmatter

```text
---
from ..layouts import BaseLayout
from ..components import UserCard

props:
  title: str = "Dashboard"
  users: list = []

vars:
  base_class: "container mx-auto"
  badge_styles:
    admin: "badge badge-admin"
    user: "badge badge-user"

computed:
  has_users: props.users | length > 0

slot actions
---
```

### 4.2 Control Flow

```html
<For each={items} as="item">...</For>
<Show when={condition}>...<Else>...</Else></Show>
<Switch expr={value}><Case value="a">...</Case><Default>...</Default></Switch>
```

### 4.3 Fragment

```html
<Fragment>
  <span>A</span>
  <span>B</span>
</Fragment>
```

Removes the wrapper element — children render directly.

### 4.4 Conditional Attributes

```html
<div ?hidden={not visible}>content</div>
<option value="admin" ?selected={role == "admin"}>Admin</option>
```

### 4.5 Spread Attributes

```html
<div class="base" ...{extra_attrs}>content</div>
```

### 4.6 HTMX Aliases (pjx-htmx)

`htmx:{attr}` -> `hx-{attr}`:

```html
<button htmx:post="/users" htmx:target="#list" htmx:swap="innerHTML">Save</button>
```

### 4.7 Stimulus Aliases (pjx-stimulus)

```html
<div stimulus:controller="dropdown">
  <button stimulus:action="click->dropdown#toggle">Open</button>
  <div stimulus:target="menu">Menu</div>
</div>
```

Multi-controller requires explicit selection: `stimulus:target.dropdown="menu"`

### 4.8 SSE Aliases (pjx-htmx)

`sse:{attr}` -> `sse-{attr}`:

```html
<div sse:connect="/events" sse:swap="message"></div>
```

### 4.9 Expressions

`{expr}` -> `{{ expr }}`:

```html
<a href={"/users/" ~ user.id}>Link</a>
```

### 4.10 Components

Uppercase tags imported via frontmatter, rendered via `{% include %}`:

```html
---
from ..components import UserCard
---
<UserCard id={user.id} name={user.name} />
```

### 4.11 cn() — Class-Name Merging (pjx-tailwind)

```html
---
computed:
  btn_class: cn("btn", is_primary and "btn-primary", is_disabled and "opacity-50")
---
<button class={btn_class}>Click</button>
```

---

## 5. FastAPI Decorators

### @ui.page

```python
@ui.page("/", "pages/home.jinja")
async def home(request: Request, svc = Depends(get_user_service)) -> HomeProps:
    return HomeProps(users=svc.list())
```

### @ui.fragment

```python
@ui.fragment("/users/{user_id}/edit", "partials/edit_modal.jinja")
async def edit_form(request: Request, user_id: int, svc = Depends(get_svc)) -> UserCardProps:
    return UserCardProps(**svc.get(user_id).model_dump())
```

### @ui.action

```python
from pjx.router import FormData

@ui.action("/users", success_template="partials/user_card.jinja", error_template="partials/form_error.jinja")
async def create_user(request: Request, data: CreateUserForm = FormData(CreateUserForm), svc = Depends(get_svc)) -> UserCardProps:
    user = svc.create(data)
    return UserCardProps(**user.model_dump())
```

`FormData(Model)` is a `Depends()` wrapper. On validation error, renders `error_template` (422).

### @ui.stream

```python
@ui.stream("/notifications", "partials/notification.jinja")
async def notifications(request: Request):
    async for event in event_source():
        yield SSEEvent(props=NotificationProps(message=event.text), id=str(event.id))
```

### ui.render

```python
@app.exception_handler(404)
async def not_found(request, exc):
    return HTMLResponse(ui.render("pages/404.jinja"), status_code=404)
```

---

## 6. Security

- `PJXEnvironment` enables `autoescape` by default via `select_autoescape`
- Props containing HTML are automatically escaped (XSS impossible without `| safe`)
- `@ui.action` preserves multi-value form data (checkboxes, multi-select)
- SSE uses correct framing (`data:` per line)
- Import resolution validates paths to prevent directory traversal
- HTTP method dispatch uses an explicit allowlist (no arbitrary `getattr`)
- Templates must be developer-controlled; do not use user-uploaded templates
- CSRF/auth are the responsibility of the user's middleware

---

## 7. CLI

### pjx check — Static Analysis

Validates imports, computed cycles, undefined variables:

```bash
pjx check <path>           # Full analysis
pjx check <path> --verbose  # Show ok templates too
```

Diagnostics:

| Code   | Level   | Description                     |
| ------ | ------- | ------------------------------- |
| PJX301 | error   | Cannot resolve import           |
| PJX302 | warning | Import file not found on disk   |
| PJX303 | error   | Circular dependency in computed |
| PJX304 | warning | Possibly undefined variable     |

### pjx format — Frontmatter Formatter

Canonicalizes frontmatter order (imports -> props -> vars -> computed -> slots):

```bash
pjx format <path>           # Apply formatting
pjx format <path> --check   # CI mode (exit 1 if changes needed)
```

### pjx sitemap — SEO Generation

Discovers pages and generates sitemap.xml + robots.txt:

```bash
pjx sitemap <templates_dir> --base-url https://example.com
pjx sitemap <templates_dir> --base-url https://example.com -o static/
```

---

## 8. Template Cache

`PJXLoader` includes an mtime-based `TemplateCache`. Preprocessed templates are cached in memory and automatically invalidated when the source file changes on disk.

---

## 9. Dependencies

| Package                      | Usage           |
| ---------------------------- | --------------- |
| `jinja2` >= 3.1.6            | Template engine |
| `fastapi` >= 0.135.3         | Web framework   |
| `pydantic` >= 2.12.5         | Validation      |
| `python-multipart` >= 0.0.22 | Form parsing    |
| `uvicorn` >= 0.43.0          | ASGI server     |

Optional extras install separate packages:

- `pjx[htmx]` -> `pjx-htmx` (no additional deps)
- `pjx[stimulus]` -> `pjx-stimulus` (no additional deps)
- `pjx[tailwind]` -> `pjx-tailwind` (no additional deps)
- `pjx[all]` -> all of the above
