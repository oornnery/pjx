# PJX

Jinja2 preprocessor with JSX-like syntax for FastAPI + HTMX + Stimulus.

PJX extends Jinja2 with declarative syntax — components, control flow tags, HTMX/Stimulus aliases — that compiles transparently to standard Jinja2 at template load time. No build step, no runtime overhead, no magic.

## The Idea

PJX brings the DX of modern component frameworks (React, Vue, Solid) to the Python SSR ecosystem, without abandoning the simplicity of Jinja2 + HTMX.

Instead of inventing a client-side reactive runtime or a complex build system, PJX is a **preprocessor** that transforms declarative syntax into plain Jinja2. You write `<For>`, `<Show>`, `htmx:post`, `stimulus:controller` — PJX generates `{% for %}`, `{% if %}`, `hx-post`, `data-controller`. The generated Jinja2 is always inspectable.

PJX is not a framework. It's a library with two layers:
- **Preprocessor** — transforms syntax at template load time
- **PJXRouter** — extends FastAPI's `APIRouter` with typed template decorators

You bring your own FastAPI app, your own CSS strategy, your own deployment.

## Installation

```bash
pip install pjx
```

Or with `uv`:

```bash
uv add pjx
```

## Quick Start

### 1. Setup

```python
# app.py
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from jinja2 import FileSystemLoader
from pydantic import BaseModel

from pjx import PJXEnvironment
from pjx.router import PJXRouter

app = FastAPI()

templates = Jinja2Templates(
    env=PJXEnvironment(loader=FileSystemLoader("templates"))
)
ui = PJXRouter(templates)
app.include_router(ui)


class HomeProps(BaseModel):
    title: str = "Hello"
    items: list[str] = []


@ui.page("/", "home.jinja")
async def home(request: Request) -> HomeProps:
    return HomeProps(items=["Alice", "Bob", "Charlie"])
```

### 2. Template

```html
<!-- templates/home.jinja -->
<!DOCTYPE html>
<html>
<body>
  <h1>{{ props.title }}</h1>
  <ul>
    <For each={props.items} as="item">
      <li>{{ item }}</li>
    </For>
  </ul>
</body>
</html>
```

### 3. Run

```bash
fastapi dev app.py
```

## Syntax

### Control Flow

```html
<!-- Loop -->
<For each={users} as="user">
  <p>{{ user.name }}</p>
</For>

<!-- Conditional -->
<Show when={user.active}>
  <span>Active</span>
  <Else>
    <span>Inactive</span>
  </Else>
</Show>

<!-- Switch -->
<Switch expr={user.role}>
  <Case value="admin"><span class="badge">Admin</span></Case>
  <Case value="agent"><span class="badge">Agent</span></Case>
  <Default><span class="badge">User</span></Default>
</Switch>
```

### HTMX Aliases

`htmx:{attr}` compiles to `hx-{attr}`:

```html
<button
  htmx:post="/users"
  htmx:target="#user-list"
  htmx:swap="innerHTML"
  htmx:confirm="Are you sure?">
  Save
</button>

<!-- compiles to: -->
<button
  hx-post="/users"
  hx-target="#user-list"
  hx-swap="innerHTML"
  hx-confirm="Are you sure?">
  Save
</button>
```

### Stimulus Aliases

```html
<div stimulus:controller="dropdown">
  <button stimulus:action="click->dropdown#toggle">Menu</button>
  <div stimulus:target="menu">
    <a href="/profile">Profile</a>
  </div>
</div>

<!-- compiles to: -->
<div data-controller="dropdown">
  <button data-action="click->dropdown#toggle">Menu</button>
  <div data-dropdown-target="menu">
    <a href="/profile">Profile</a>
  </div>
</div>
```

Multi-controller requires explicit selection:

```html
<div stimulus:controller="dropdown modal">
  <button stimulus:target.dropdown="trigger">Open</button>
</div>
```

### SSE Aliases

```html
<div sse:connect="/events" sse:swap="message"></div>
```

### Attribute Expressions

`{expr}` compiles to `{{ expr }}`:

```html
<a href={"/users/" ~ user.id}>{{ user.name }}</a>

<!-- compiles to: -->
<a href="{{ '/users/' ~ user.id }}">{{ user.name }}</a>
```

### Components

Tags starting with uppercase are components. Imported via frontmatter:

```html
---
from ..layouts import BaseLayout
from ..components import UserCard
from ..icons import IconPlus

props:
  title: str = "Dashboard"
  users: list = []
---

<BaseLayout title={props.title}>
  <h1>{{ props.title }}</h1>

  <For each={props.users} as="user">
    <UserCard id={user.id} name={user.name} email={user.email} />
  </For>
</BaseLayout>
```

#### Layout Components

Components with children receive `{{ content }}`:

```html
<!-- layouts/BaseLayout.jinja -->
<!DOCTYPE html>
<html>
<head><title>{{ title }}</title></head>
<body>
  {{ content }}
</body>
</html>
```

#### SVG Icons

SVG icons are `.jinja` components — inline in HTML, no extra request:

```html
<!-- icons/IconEdit.jinja -->
<svg width="{{ size | default('16') }}" height="{{ size | default('16') }}" viewBox="0 0 24 24" ...>
  <path d="M11 4H4a2 2 0 0 0-2 2v14..."></path>
</svg>
```

```html
<button><IconEdit size="14" /> Edit</button>
```

### Dynamic Pages with [slug]

Next.js-like convention for dynamic routes:

```python
@ui.page("/users/{user_id}", "pages/users/[id].jinja")
async def user_detail(request, user_id: int):
    return UserDetailProps(user=get_user(user_id))
```

The template receives `params` automatically:

```html
<h1>User #{{ params.user_id }}</h1>
<p>{{ props.user.name }}</p>
```

## PJXRouter

`PJXRouter` extends `APIRouter` — accepted by `app.include_router()`:

```python
from pjx.router import PJXRouter

ui = PJXRouter(templates)
app.include_router(ui)
```

### Decorators

#### @ui.page — full page

```python
@ui.page("/", "pages/home.jinja")
async def home(request: Request) -> HomeProps:
    return HomeProps(title="Home")
```

#### @ui.fragment — HTMX partial

```python
@ui.fragment("/users/{id}/edit", "partials/edit.jinja")
async def edit_form(request: Request, id: int) -> EditProps:
    return EditProps(user=get_user(id))
```

#### @ui.action — form with validation

```python
@ui.action(
    "/users",
    form=CreateUserForm,
    success_template="partials/user_row.jinja",
    error_template="partials/form_error.jinja",
)
async def create_user(request: Request, data: CreateUserForm) -> UserProps:
    user = service.create(data)
    return UserProps(**user.model_dump())
```

- Success: renders `success_template` (200)
- Validation error: renders `error_template` (422)

#### @ui.stream — SSE

```python
from pjx.router import SSEEvent

@ui.stream("/notifications", "partials/notification.jinja")
async def notifications(request: Request):
    async for event in event_source():
        yield SSEEvent(
            props=NotificationProps(message=event.text),
            id=str(event.id),
            event="notification",
        )
```

#### ui.render — manual rendering

For error pages or rendering outside decorators:

```python
@app.exception_handler(404)
async def not_found(request, exc):
    return HTMLResponse(ui.render("pages/404.jinja"), status_code=404)
```

### Template Context

All decorators automatically inject:

| Variable | Content |
|----------|---------|
| `props` | BaseModel returned by the handler |
| `params` | URL path params (`request.path_params`) |
| `request` | Starlette Request object |

### Dependency Injection

FastAPI's `Depends()` works normally:

```python
@ui.page("/", "pages/home.jinja")
async def home(
    request: Request,
    svc: UserService = Depends(get_user_service),
) -> HomeProps:
    return HomeProps(users=svc.list())
```

## Recommended Project Structure

```
app/
├── main.py          # FastAPI app, mount static, include routers
├── models.py        # Pydantic models
├── service.py       # Business logic
├── deps.py          # Depends providers
├── api.py           # APIRouter — JSON (/api/*)
├── views.py         # PJXRouter — HTML (templates)
├── templates/
│   ├── layouts/     # BaseLayout.jinja
│   ├── components/  # UserCard.jinja
│   ├── icons/       # IconEdit.jinja, IconTrash.jinja
│   ├── pages/       # home.jinja, users/[id].jinja, 404.jinja
│   └── partials/    # user_card.jinja, edit_modal.jinja
└── static/
    ├── css/
    └── js/
```

API and Views share the same service via `Depends()`:

```python
# api.py
router = APIRouter(prefix="/api", tags=["api"])

@router.get("/users")
async def list_users(svc: UserService = Depends(get_user_service)):
    return svc.list()

# views.py
ui = PJXRouter(templates)

@ui.page("/", "pages/home.jinja")
async def home(request, svc: UserService = Depends(get_user_service)):
    return HomeProps(users=svc.list())

# main.py
app.include_router(api_router)
app.include_router(ui)
```

## CLI

Validate PJX templates:

```bash
pjx check templates/
pjx check templates/ --verbose
```

## Security

- **Autoescape ON** by default — XSS impossible without `| safe`
- Form data preserves multi-values (checkboxes, multi-select)
- SSE with correct framing (`data:` per line)
- CSRF and auth are your middleware's responsibility

## Requirements

- Python >= 3.13
- jinja2 >= 3.1
- fastapi >= 0.100
- pydantic >= 2.0

## License

MIT
