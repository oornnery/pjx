# PJX

Jinja2 preprocessor with JSX-like syntax for FastAPI + HTMX + Stimulus.

PJX extends Jinja2 with declarative syntax — components, control flow,
template variables, conditional attributes — that compiles transparently
to standard Jinja2 at template load time. No build step, no runtime
overhead.

## Installation

```bash
pip install pjx                    # core only
pip install pjx[htmx]             # + HTMX/SSE aliases
pip install pjx[htmx,stimulus]    # + Stimulus aliases
pip install pjx[all]              # + Tailwind utilities (cn)
```

## Core (`pip install pjx`)

The core package gives you: components, control flow tags,
frontmatter (props, vars, computed), conditional attributes,
spread attributes, Fragment, expressions, and the PJXRouter
for FastAPI.

### Setup

```python
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

### Template (core features only)

```html
---
from ..layouts import BaseLayout
from ..components import UserCard

props:
  title: str = "Dashboard"
  users: list = []
  show_header: bool = true

vars:
  card_class: "rounded shadow p-4"
  roles:
    admin: "badge-red"
    user: "badge-gray"

computed:
  has_users: props.users | length > 0
  greeting: "Welcome to " ~ props.title
---

<BaseLayout title={props.title}>
  <h1>{{ greeting }}</h1>

  <Show when={show_header}>
    <Fragment>
      <h2>User List</h2>
      <p>Manage your users below.</p>
    </Fragment>
  </Show>

  <div ?hidden={not has_users}>
    <For each={props.users} as="user">
      <UserCard
        name={user.name}
        role={user.role}
        class={card_class}
        ...{user.extra_attrs}
      />
    </For>
  </div>

  <Show when={not has_users}>
    <p>No users yet.</p>
  </Show>
</BaseLayout>
```

What the core gives you:

| Feature           | Syntax                        | Compiles to                                   |
| ----------------- | ----------------------------- | --------------------------------------------- |
| Control flow      | `<For>`, `<Show>`, `<Switch>` | `{% for %}`, `{% if %}`, `{% if/elif %}`      |
| Fragment          | `<Fragment>...</Fragment>`    | children only (no wrapper)                    |
| Components        | `<UserCard name={x} />`       | `{% include %}` + `{% with %}`                |
| Expressions       | `href={"/users/" ~ id}`       | `href="{{ '/users/' ~ id }}"`                 |
| Conditional attrs | `?hidden={not visible}`       | `{% if not visible %}hidden="..."{% endif %}` |
| Spread attrs      | `...{extra_attrs}`            | `{{ extra_attrs \| xmlattr }}`                |
| Vars              | `vars: color: "blue"`         | `{% set color = "blue" %}`                    |
| Computed          | `computed: full: a ~ b`       | `{% set full = a ~ b %}`                      |
| Props             | `props: title: str = "Hi"`    | metadata for type checking                    |
| Slots             | `slot actions`                | named content slots                           |

---

## Add HTMX (`pip install pjx[htmx]`)

Installs `pjx-htmx`. Adds `htmx:*` and `sse:*` alias processors
to the pipeline automatically via entry points.

```html
<!-- Before: raw hx- attributes -->
<button hx-post="/users" hx-target="#list" hx-swap="innerHTML">Save</button>

<!-- After: with pjx[htmx] -->
<button htmx:post="/users" htmx:target="#list" htmx:swap="innerHTML">
  Save
</button>
```

SSE aliases (bundled with htmx):

```html
<div sse:connect="/events" sse:swap="message"></div>
<!-- compiles to: -->
<div sse-connect="/events" sse-swap="message"></div>
```

Combined with core features:

```html
---
from ..components import UserCard

props:
  users: list = []

computed:
  has_users: props.users | length > 0
---

<form htmx:post="/users" htmx:target="#user-list" htmx:swap="beforeend">
  <input type="text" name="name" ?required={true}>
  <button type="submit">Add</button>
</form>

<div id="user-list" ?hidden={not has_users}>
  <For each={props.users} as="user">
    <UserCard name={user.name} />
  </For>
</div>
```

No Python code changes needed — just install the package and the aliases work.

---

## Add Stimulus (`pip install pjx[htmx,stimulus]`)

Installs `pjx-stimulus`. Adds the `stimulus:*` alias processor
with controller scope tracking.

```html
<div stimulus:controller="dropdown">
  <button stimulus:action="click->dropdown#toggle">Menu</button>
  <div stimulus:target="menu" ?hidden={true}>
    <a href="/profile">Profile</a>
    <a href="/logout">Logout</a>
  </div>
</div>
```

Compiles to:

```html
<div data-controller="dropdown">
  <button data-action="click->dropdown#toggle">Menu</button>
  <div data-dropdown-target="menu" {% if true %}hidden="..."{% endif %}>
    <a href="/profile">Profile</a>
    <a href="/logout">Logout</a>
  </div>
</div>
```

Multi-controller requires explicit selection:

```html
<div stimulus:controller="dropdown modal">
  <button stimulus:target.dropdown="trigger">Open</button>
  <button stimulus:action="click->modal#open">Show Modal</button>
</div>
```

Stimulus values, classes, and outlets:

```html
<div stimulus:controller="editor">
  <input stimulus:value-content="hello" />
  <!-- compiles to: data-editor-content-value="hello" -->
</div>
```

---

## Add Tailwind (`pip install pjx[all]`)

Installs `pjx-tailwind`. Registers `cn()` as a Jinja2 global function
via entry points. Filters falsy values and deduplicates classes.

```html
---
props:
  variant: str = "primary"
  size: str = "md"
  disabled: bool = false

vars:
  base: "inline-flex items-center rounded-md font-medium"
  sizes:
    sm: "h-8 px-3 text-xs"
    md: "h-10 px-4 text-sm"
    lg: "h-12 px-6 text-base"
  variants:
    primary: "bg-blue-600 text-white hover:bg-blue-700"
    secondary: "bg-gray-200 text-gray-900 hover:bg-gray-300"
    danger: "bg-red-600 text-white hover:bg-red-700"

computed:
  btn_class: cn(base, sizes[props.size], variants[props.variant],
    props.disabled and "opacity-50 pointer-events-none")
---

<button class={btn_class} ?disabled={props.disabled}>
  {{ content }}
</button>
```

`cn()` in Jinja2:

```text
cn("foo", "bar")                   -> "foo bar"
cn("base", false, "extra")        -> "base extra"
cn("base", cond and "active")     -> "base active" or "base"
cn("a b", "b c")                   -> "a b c"  (deduped)
```

---

## PJXRouter

`PJXRouter` extends `APIRouter`. All decorators inject `props`,
`params`, `request` into the template context.

### @ui.page

```python
@ui.page("/", "pages/home.jinja")
async def home(request: Request) -> HomeProps:
    return HomeProps(title="Home")
```

### @ui.fragment

```python
@ui.fragment("/users/{id}/edit", "partials/edit.jinja")
async def edit_form(request: Request, id: int) -> EditProps:
    return EditProps(user=get_user(id))
```

### @ui.action

```python
from pjx.router import FormData

@ui.action(
    "/users",
    success_template="partials/user_card.jinja",
    error_template="partials/form_error.jinja",
)
async def create_user(
    request: Request,
    data: CreateUserForm = FormData(CreateUserForm),
    svc: UserService = Depends(get_user_service),
) -> UserCardProps:
    return UserCardProps(**svc.create(data).model_dump())
```

`FormData(Model)` is a `Depends()` wrapper.
Validation errors render `error_template` (422).

### @ui.stream

```python
from pjx.router import SSEEvent

@ui.stream("/notifications", "partials/notification.jinja")
async def notifications(request: Request):
    async for event in event_source():
        yield SSEEvent(
            props=NotificationProps(message=event.text),
            id=str(event.id),
        )
```

### ui.render

```python
@app.exception_handler(404)
async def not_found(request, exc):
    return HTMLResponse(ui.render("pages/404.jinja"), status_code=404)
```

---

## CLI

### pjx check — Static Analysis

Validates imports, computed cycles, undefined variables.
Inspired by ruff/ty — fast, actionable diagnostics:

```bash
pjx check templates/
pjx check templates/ -v

# Example output:
# error[PJX301]: Cannot resolve import 'Ghost' from '..missing'
#   --> pages/home.jinja:1:1
# warning[PJX304]: Possibly undefined variable: 'unknown'
#   --> pages/home.jinja:1:1
#   = hint: Define in props:, vars:, or computed:
```

### pjx format — Frontmatter Formatter

Canonicalizes frontmatter section order
(imports -> props -> vars -> computed -> slots):

```bash
pjx format templates/             # apply formatting
pjx format templates/ --check     # CI mode (exit 1 if changes needed)
```

### pjx sitemap — SEO Generation

Discovers pages and generates sitemap.xml + robots.txt:

```bash
pjx sitemap templates/ --base-url https://example.com
pjx sitemap templates/ --base-url https://example.com -o static/
pjx sitemap templates/ --base-url https://example.com --disallow /admin,/api
```

Skips error pages (404/500) and dynamic routes (`[slug]`).

## Development

```bash
uv run task check      # lint + typecheck + test
uv run task test       # pytest
uv run task lint       # ruff
uv run task typecheck  # ty
uv run task demo       # run demo app
uv run task fmt        # ruff format
```

## Monorepo

```text
src/
  pjx/              # Core: preprocessor, router, CLI
  pjx-htmx/         # HTMX + SSE alias processor (entry point)
  pjx-stimulus/     # Stimulus alias processor (entry point)
  pjx-tailwind/     # cn() function (jinja global entry point)
demo/               # Demo CRUD app using all features
docs/               # PRD, SDD
```

Pipeline (with all extras installed):

```text
Frontmatter -> Vars -> Component -> ControlFlow ->
  [HTMX]* -> [Stimulus]* -> Attrs -> Expression
```

*Discovered via entry points — only loaded when installed.

## Template Cache

`PJXLoader` includes an mtime-based cache. Preprocessed templates
are cached in memory and invalidated when the source file changes.
No configuration needed — works automatically in dev and production.

## Security

- **Autoescape ON** by default — XSS impossible without `| safe`
- Import resolution validates paths to prevent directory traversal
- HTTP method dispatch uses an explicit allowlist
- Templates must be developer-controlled (not user-uploaded)
- Form data preserves multi-values (checkboxes, multi-select)
- CSRF and auth are your middleware's responsibility

## Requirements

- Python >= 3.13
- jinja2 >= 3.1.6
- fastapi >= 0.135.3
- pydantic >= 2.12.5

## License

MIT
