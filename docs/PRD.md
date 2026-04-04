# PJX — Product Requirements Document (PRD)

**Version:** 0.2.0
**Date:** 2026-04-04
**Status:** MVP Implemented

---

## 1. Overview

PJX is a Python toolkit that extends Jinja2 with declarative JSX-inspired syntax for building server-rendered interfaces with FastAPI, HTMX, and Stimulus.

**PJX is not a web framework.** It is a library with two layers:

- **Preprocessor** — transforms PJX syntax (`<For>`, `<Show>`, `htmx:*`, `stimulus:*`, components) into pure Jinja2, transparently at template load time.
- **PJXRouter** — extends FastAPI's `APIRouter` with decorators for rendering templates with typed props via Pydantic.

### Value Proposition

Modern framework DX (components, typing, aliases) with pure SSR (Jinja2 + HTMX). No reactive client-side runtime, no build step, no magic — the generated Jinja2 is always inspectable.

---

## 2. Package Architecture

```
pjx/
├── __init__.py         # PJXEnvironment, PJXLoader
├── environment.py      # PJXEnvironment (extends jinja2.Environment)
├── router.py           # PJXRouter (extends APIRouter), ActionResult, SSEEvent
├── models.py           # ImportDecl, PropDecl, SlotDecl, TemplateMetadata
├── errors.py           # PJXError, PJXRenderError, SourceMap, Diagnostic
├── cli.py              # CLI (pjx check)
└── core/
    ├── pipeline.py     # PreprocessorPipeline, ProcessorContext, ProcessorResult
    ├── scanner.py      # Scanner HTML-like (state machine)
    ├── frontmatter.py  # FrontmatterProcessor
    ├── flow.py         # ControlFlowProcessor (<For>, <Show>, <Switch>)
    ├── aliases.py      # AliasProcessor (htmx:*, stimulus:*, sse:*)
    ├── components.py   # ComponentProcessor (include + children)
    └── expressions.py  # ExpressionProcessor ({expr} → {{ expr }})
```

---

## 3. FastAPI Integration

PJX integrates with FastAPI natively, without wrapper classes:

```python
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from jinja2 import FileSystemLoader
from pjx import PJXEnvironment
from pjx.router import PJXRouter

app = FastAPI()

# Standard Jinja2Templates with PJXEnvironment
templates = Jinja2Templates(
    env=PJXEnvironment(loader=FileSystemLoader("templates"))
)

# PJXRouter extends APIRouter — accepted by app.include_router()
ui = PJXRouter(templates)
app.include_router(ui)
```

### PJXEnvironment

Extends `jinja2.Environment`. Wraps the loader with `PJXLoader` which preprocesses PJX syntax before Jinja2 parses it. Enables `autoescape` by default.

### PJXRouter

Extends `fastapi.APIRouter`. Adds decorators for rendering templates:

| Decorator | Description |
|-----------|-------------|
| `@ui.page(path, response_template)` | Renders a full page (GET) |
| `@ui.fragment(path, response_template, method=)` | Renders partial HTML (HTMX) |
| `@ui.action(path, form=, success_template=, error_template=, method=)` | Validates form + renders success/error |
| `@ui.stream(path, response_template)` | SSE streaming |
| `ui.render(response_template, context)` | Manual render (error pages, etc.) |

All decorators automatically inject into the template context:
- `props` — data returned by the handler (BaseModel)
- `params` — request path params (`request.path_params`)
- `request` — Starlette Request object

---

## 4. PJX Syntax

### 4.1 Frontmatter

```
---
from ..layouts import BaseLayout
from ..components import UserCard

props:
  title: str = "Dashboard"
  users: list = []

slot actions
---
```

### 4.2 Control Flow

```html
<For each={items} as="item">
  <li>{{ item.name }}</li>
</For>

<Show when={user.active}>
  <span>Active</span>
  <Else>
    <span>Inactive</span>
  </Else>
</Show>

<Switch expr={user.role}>
  <Case value="admin"><span>Admin</span></Case>
  <Case value="user"><span>User</span></Case>
  <Default><span>Guest</span></Default>
</Switch>
```

### 4.3 HTMX Aliases

`htmx:{attr}` compiles to `hx-{attr}`:

```html
<button htmx:post="/users" htmx:target="#list" htmx:swap="innerHTML">
  Save
</button>
```

### 4.4 Stimulus Aliases

```html
<div stimulus:controller="dropdown">
  <button stimulus:action="click->dropdown#toggle">Open</button>
  <div stimulus:target="menu">Menu</div>
</div>
```

Multi-controller requires explicit selection: `stimulus:target.dropdown="menu"`

### 4.5 SSE Aliases

`sse:{attr}` compiles to `sse-{attr}`:

```html
<div sse:connect="/events" sse:swap="message"></div>
```

### 4.6 Expressions

`{expr}` in attributes compiles to `{{ expr }}`:

```html
<a href={"/users/" ~ user.id}>Link</a>
<!-- compiles to: -->
<a href="{{ '/users/' ~ user.id }}">Link</a>
```

### 4.7 Components

Uppercase tags are components. Imported via frontmatter, rendered via `{% include %}`:

```html
---
from ..components import UserCard
---

<UserCard id={user.id} name={user.name} />
```

Components with children use `{% set content %}...{% endset %}`:

```html
<BaseLayout title="Home">
  <h1>Content here</h1>
</BaseLayout>
```

### 4.8 SVG as Components

SVG icons are `.jinja` components with props:

```html
---
from ..icons import IconEdit, IconTrash
---

<button><IconEdit size="14" /> Edit</button>
<button><IconTrash size="14" /> Remove</button>
```

### 4.9 Pages with [slug]

Next.js-like convention for dynamic routes:

```python
@ui.page("/users/{user_id}", "pages/users/[id].jinja")
async def user_detail(request, user_id, svc=Depends(get_user_service)):
    return UserDetailProps(user=svc.get(user_id))
```

The file `pages/users/[id].jinja` receives `params.user_id` automatically.

---

## 5. FastAPI Decorators

### @ui.page

Renders a full page. Handler returns a `BaseModel`, decorator renders the template and returns an `HTMLResponse`.

```python
@ui.page("/", "pages/home.jinja")
async def home(request: Request, svc: UserService = Depends(get_user_service)) -> HomeProps:
    return HomeProps(users=svc.list())
```

### @ui.fragment

Renders partial HTML for HTMX swap.

```python
@ui.fragment("/users/{user_id}/edit", "partials/edit_modal.jinja")
async def edit_form(request: Request, user_id: int, svc = Depends(get_user_service)) -> UserCardProps:
    return UserCardProps(**svc.get(user_id).model_dump())
```

### @ui.action

Validates form data with Pydantic. Success renders `success_template` (200), error renders `error_template` (422).

```python
@ui.action(
    "/users",
    form=CreateUserForm,
    success_template="partials/user_card.jinja",
    error_template="partials/form_error.jinja",
)
async def create_user(request: Request, data: CreateUserForm, svc = Depends(get_user_service)) -> UserCardProps:
    user = svc.create(data)
    return UserCardProps(**user.model_dump())
```

Supports FastAPI's `Depends()` — path params and dependencies are injected normally.

### @ui.stream

SSE streaming. Handler is an async generator that yields props.

```python
@ui.stream("/notifications", "partials/notification.jinja")
async def notifications(request: Request):
    async for event in event_source():
        yield NotificationProps(message=event.message)
```

### ui.render

Helper for rendering templates outside of decorators (error pages, etc.):

```python
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return HTMLResponse(ui.render("pages/404.jinja"), status_code=404)
```

---

## 6. Security

- `PJXEnvironment` enables `autoescape` by default via `select_autoescape`
- Props containing HTML are automatically escaped (XSS impossible without `| safe`)
- `@ui.action` preserves multi-value form data (checkboxes, multi-select)
- SSE uses correct framing (`data:` per line)
- CSRF/auth are the responsibility of the user's middleware

---

## 7. CLI

```bash
pjx check <path>           # Validates templates
pjx check <path> --verbose  # Shows each validated template
```

---

## 8. Dependencies

| Package | Usage |
|---------|-------|
| `jinja2` >= 3.1 | Template engine |
| `fastapi` >= 0.100 | Web framework |
| `pydantic` >= 2.0 | Validation |
| `python-multipart` | Form parsing |

---

## 9. Recommended Project Structure

```
app/
├── main.py        # FastAPI app, mount static, include routers, error pages
├── models.py      # Pydantic models (User, Forms, Props)
├── service.py     # Business logic
├── deps.py        # FastAPI dependencies (Depends providers)
├── api.py         # APIRouter — JSON routes (/api/*)
├── views.py       # PJXRouter — HTML routes (templates)
├── templates/
│   ├── layouts/        # Layout components (BaseLayout.jinja)
│   ├── components/     # Reusable components (UserCard.jinja)
│   ├── icons/          # SVG as components (IconEdit.jinja)
│   ├── pages/          # Full pages
│   │   ├── home.jinja
│   │   ├── users/
│   │   │   └── [id].jinja    # Dynamic route
│   │   ├── 404.jinja
│   │   └── 500.jinja
│   └── partials/       # HTMX fragments (user_card.jinja, edit_modal.jinja)
└── static/
    ├── css/app.css
    └── js/app.js
```

API and Views share the same `service` via `Depends()`:

```python
# api.py — JSON
@router.get("/users")
async def list_users(svc: UserService = Depends(get_user_service)):
    return svc.list()

# views.py — HTML
@ui.page("/", "pages/home.jinja")
async def home(request, svc: UserService = Depends(get_user_service)):
    return HomeProps(users=svc.list())
```
