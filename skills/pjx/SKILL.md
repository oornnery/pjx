# PJX Skill

PJX is a Python DSL for reactive `.jinja` components. It compiles a declarative
syntax (props, state, slots, imports, control flow) down to Jinja2 + HTMX +
Alpine.js. This skill covers everything you need to build PJX applications.

---

## Stack

| Layer            | Technology                                |
| ---------------- | ----------------------------------------- |
| Language         | Python 3.14+                              |
| Template engine  | HybridEngine (default), Jinja2, MiniJinja |
| Server framework | FastAPI + Uvicorn                         |
| Reactivity       | Alpine.js (client-side)                   |
| Server updates   | HTMX                                      |
| SSE streaming    | sse-starlette                             |
| Validation       | Pydantic                                  |
| CLI              | Typer + Rich                              |

---

## Component Anatomy

A `.jinja` file has up to three sections: **frontmatter**, **style**, and
**body**.

```jinja
---
import UserCard from "./UserCard.jinja"

props {
  title: str = "Hello",
  users: list = [],
}

state count = 0
computed total = users | length

slot actions

css "/static/css/page.css"
middleware "auth"
---

<style scoped>
.page { padding: 2rem; }
</style>

<div class="page" reactive>
  <h1>{{ props.title }}</h1>
  <For each="users" as="user">
    <UserCard name="{{ user.name }}" email="{{ user.email }}" />
  </For>
  <Slot:actions />
</div>
```

---

## Frontmatter Keywords

All declarations go between `---` delimiters at the top of the file.

### `extends`

Inherit from a base template (Jinja2 extends).

```text
extends "layouts/Base.jinja"
```

### `import`

Import components for use in the body.

```text
import Button from "./Button.jinja"
import { Card, Badge } from "./ui.jinja"
import * from "./icons/"
```

### `from ... import`

Alternative import syntax.

```text
from components import Header, Footer
```

### `props`

Typed component properties with optional defaults. Accessed via `props.name`.

```text
props {
  name: str,
  count: int = 0,
  items: list = [],
  user: dict | None = null,
}
```

**Supported types:** `str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`,
`set`, `None`, `Any`, unions (`str | None`), generics (`list[str]`).

**Defaults** are evaluated safely via `ast.literal_eval` -- no function calls
or arbitrary code allowed.

**DO:** Always type your props.
**DON'T:** Use mutable defaults directly -- PJX wraps `list`, `dict`, `set`
in `default_factory` automatically.

### `slot`

Declare named slots for content injection.

```text
slot header
slot footer = "Default footer"
```

### `state`

Alpine.js reactive state. Requires `reactive` on the container element.

```text
state count = 0
state editing = false
state query = ""
```

Compiles to `x-data="{ count: 0, editing: false, query: '' }"`.

### `computed`

Jinja2 computed variables (server-side only).

```text
computed total = items | length
computed is_empty = total == 0
```

Compiles to `{% set total = items | length %}`.

### `let` / `const`

Jinja2 variable bindings.

```text
let greeting = "Hello, " + props.name
const MAX_ITEMS = 100
```

### `store`

Alpine.js global stores.

```text
store theme = { dark: false, accent: "blue" }
```

### `css` / `js`

Declare static asset dependencies.

```text
css "/static/css/page.css"
js "/static/js/chart.js"
```

### `middleware`

Require named middleware on this page/component.

```text
middleware "auth"
middleware "auth", "rate_limit"
```

---

## DSL Attributes

PJX transforms special attributes into Alpine.js and HTMX directives.

### Alpine.js Bindings (`bind:`)

| PJX                      | Compiles to              |
| ------------------------ | ------------------------ |
| `bind:text="expr"`       | `x-text="expr"`          |
| `bind:model="field"`     | `x-model="field"`        |
| `bind:model.lazy="f"`    | `x-model.lazy="f"`       |
| `bind:show="expr"`       | `x-show="expr"`          |
| `bind:html="expr"`       | `x-html="expr"`          |
| `bind:class="expr"`      | `:class="expr"`          |
| `bind:value="expr"`      | `:value="expr"`          |
| `bind:ref="name"`        | `x-ref="name"`           |
| `bind:cloak="true"`      | `x-cloak="true"`         |
| `bind:init="expr"`       | `x-init="expr"`          |
| `bind:transition="..."`  | `x-transition="..."`     |

### Event Handlers (`on:`)

| PJX                          | Compiles to                  |
| ---------------------------- | ---------------------------- |
| `on:click="handler()"`       | `@click="handler()"`         |
| `on:submit.prevent="fn()"`   | `@submit.prevent="fn()"`     |
| `on:keyup.enter="search()"`  | `@keyup.enter="search()"`    |

### HTMX Actions (`action:`)

| PJX                              | Compiles to                    |
| -------------------------------- | ------------------------------ |
| `action:get="/api/data"`         | `hx-get="/api/data"`           |
| `action:post="/api/save"`        | `hx-post="/api/save"`          |
| `action:put="/api/update"`       | `hx-put="/api/update"`         |
| `action:delete="/api/remove"`    | `hx-delete="/api/remove"`      |
| `action:patch="/api/patch"`      | `hx-patch="/api/patch"`        |

### Target + Swap Shorthand (`into`)

| PJX                        | Compiles to                                   |
| -------------------------- | --------------------------------------------- |
| `into="#target"`           | `hx-target="#target"` + `hx-swap="innerHTML"` |
| `into="#target:outerHTML"` | `hx-target="#target"` + `hx-swap="outerHTML"` |
| `into="#list:beforeend"`   | `hx-target="#list"` + `hx-swap="beforeend"`   |

### HTMX Shorthand

These pass through with an `hx-` prefix:

| PJX           | Compiles to        |
| ------------- | ------------------ |
| `swap`        | `hx-swap`          |
| `target`      | `hx-target`        |
| `trigger`     | `hx-trigger`       |
| `select`      | `hx-select`        |
| `confirm`     | `hx-confirm`       |
| `indicator`   | `hx-indicator`     |
| `push-url`    | `hx-push-url`      |
| `replace-url` | `hx-replace-url`   |
| `vals`        | `hx-vals`          |
| `headers`     | `hx-headers`       |
| `encoding`    | `hx-encoding`      |
| `preserve`    | `hx-preserve`      |
| `sync`        | `hx-sync`          |
| `disabled-elt`| `hx-disabled-elt`  |
| `select-oob`  | `hx-select-oob`    |
| `boost`       | `hx-boost`         |
| `include`     | `hx-include`       |

### SSE (Server-Sent Events)

| PJX                 | Compiles to                                 |
| ------------------- | ------------------------------------------- |
| `live="/sse/clock"` | `hx-ext="sse"` + `sse-connect="/sse/clock"` |
| `channel="clock"`   | `sse-swap="clock"`                          |
| `close="done"`      | `sse-close="done"`                          |

### WebSocket

| PJX                 | Compiles to                             |
| ------------------- | --------------------------------------- |
| `socket="/ws/chat"` | `hx-ext="ws"` + `ws-connect="/ws/chat"` |
| `send`              | `ws-send` (boolean)                     |

### The `reactive` Attribute

Add `reactive` to a container element to inject `x-data` from `state`
declarations:

```jinja
---
state count = 0
---

<div reactive>
  <!-- x-data="{ count: 0 }" is injected here -->
  <span x-text="count">0</span>
</div>
```

**DO:** Put `reactive` on ONE container that wraps all state consumers.
**DON'T:** Put `reactive` on multiple sibling elements -- each gets its own
isolated Alpine scope.

---

## Control Flow

PJX provides PascalCase control flow tags compiled to Jinja2.

### `<Show>` / `<Else>`

Conditional rendering.

```jinja
<Show when="user">
  <p>Welcome, {{ user.name }}!</p>
  <Else>
    <p>Please log in.</p>
  </Else>
</Show>
```

Compiles to `{% if user %} ... {% else %} ... {% endif %}`.

### `<For>` / `<Empty>`

Iteration with optional empty fallback.

```jinja
<For each="items" as="item">
  <li>{{ item.name }}</li>
  <Empty>
    <li>No items found.</li>
  </Empty>
</For>
```

Compiles to `{% for item in items %} ... {% else %} ... {% endfor %}`.

### `<Switch>` / `<Case>` / `<Default>`

Pattern matching.

```jinja
<Switch on="status">
  <Case value="'active'">Active</Case>
  <Case value="'inactive'">Inactive</Case>
  <Default>Unknown</Default>
</Switch>
```

Compiles to `{% if status == 'active' %} ... {% elif %} ... {% else %} ...`.

### `<ErrorBoundary>`

Jinja2 try/except wrapper.

```jinja
<ErrorBoundary fallback="<p>Something went wrong</p>">
  {{ risky_expression }}
</ErrorBoundary>
```

### `<Portal>`

Lazy-load remote content via HTMX.

```jinja
<Portal target="/api/widget" />
```

Compiles to `<div hx-get="/api/widget" hx-swap="innerHTML" hx-trigger="load">`.

### `<Await>`

Async content loading with loading/error states.

```jinja
<Await src="/api/data" trigger="load">
  <Loading>Loading...</Loading>
</Await>
```

### `<Transition>`

Alpine.js enter/leave animations.

```jinja
<Transition enter="fade-in" leave="fade-out">
  <div>Animated content</div>
</Transition>
```

### `<Fragment>`

Group elements without a wrapper.

```jinja
<Fragment>
  <li>A</li>
  <li>B</li>
</Fragment>
```

### `<Teleport>`

Portal content to a named block.

```jinja
<Teleport to="head">
  <style>body { background: red; }</style>
</Teleport>
```

---

## Slots

### Declaring Slots (child component)

```jinja
---
slot header
slot footer = "Default footer text"
slot default
---

<div>
  <header><Slot:header /></header>
  <main><Slot /></main>
  <footer><Slot:footer /></footer>
</div>
```

- `<Slot />` renders the default slot (children).
- `<Slot:name />` renders a named slot.
- `<Slot:name>fallback</Slot:name>` renders with fallback if slot not passed.

### Passing Slots (parent component)

```jinja
<Card>
  <slot:header>
    <h1>My Title</h1>
  </slot:header>

  <!-- Default slot: everything not in a named slot -->
  <p>This goes into the default slot.</p>

  <slot:footer>
    <button>Submit</button>
  </slot:footer>
</Card>
```

---

## Built-in Layout Components

PJX ships layout primitives. No import needed.

| Component      | Props                          | Description              |
| -------------- | ------------------------------ | ------------------------ |
| `<VStack>`     | `gap`, `align`, `justify`      | Vertical flex stack      |
| `<HStack>`     | `gap`, `align`, `justify`      | Horizontal flex stack    |
| `<Grid>`       | `gap`, `min`, `cols`           | CSS grid                 |
| `<Center>`     | `class`                        | Center content           |
| `<Container>`  | `max`, `class`                 | Width-constrained box    |
| `<Wrap>`       | `gap`, `class`                 | Wrapping flex            |
| `<Spacer>`     | `class`                        | Flex spacer              |
| `<Divider>`    | `class`                        | Horizontal rule          |
| `<AspectRatio>`| `ratio`, `class`               | Maintain aspect ratio    |
| `<Hide>`       | `below`, `above`, `class`      | Responsive visibility    |

All accept `class` for extra CSS classes and pass `{{ attrs }}` through.

```jinja
<VStack gap="1.5rem">
  <h1>Title</h1>
  <HStack gap="1rem" align="center">
    <span>Left</span>
    <Spacer />
    <span>Right</span>
  </HStack>
  <Grid min="300px" gap="1rem">
    <Card />
    <Card />
    <Card />
  </Grid>
</VStack>
```

---

## FastAPI Integration

### Setup

```python
from pathlib import Path
from fastapi import FastAPI
from pjx import PJX, PJXConfig, SEO

app = FastAPI()

pjx = PJX(
    app,
    config=PJXConfig(toml_path=Path(__file__).parent / "pjx.toml"),
    seo=SEO(title="My App", description="Built with PJX."),
    csrf=True,
    csrf_secret="your-secret-key",
    csrf_exempt_paths={"/sse/clock", "/health", "/ready"},
    health=True,
)
```

### Page Routes

```python
@pjx.page("/", template="pages/Home.jinja", title="Home")
async def home():
    return {"greeting": "Hello, PJX!"}
```

The returned dict becomes the template context. `props`, `seo`,
`pjx_assets`, `csrf_token` are injected automatically.

### HTMX Partial Endpoints

Use `pjx.partial()` to render component fragments for HTMX swaps:

```python
@app.post("/htmx/counter/increment")
async def increment():
    counter["count"] += 1
    return HTMLResponse(pjx.partial("components/Counter.jinja", count=counter["count"]))
```

**DO:** Return `HTMLResponse(pjx.partial(...))` from HTMX endpoints.
**DON'T:** Return full page HTML for partial swaps.

### Middleware

```python
@pjx.middleware("auth")
async def require_auth(request: Request):
    if not request.session.get("user"):
        raise HTTPException(status_code=303, headers={"Location": "/login"})
```

Then in the template frontmatter:

```text
middleware "auth"
```

### FormData Binding

```python
from typing import Annotated
from pydantic import BaseModel
from pjx import FormData

class SearchForm(BaseModel):
    query: str
    category: str = "all"

@pjx.page("/search", methods=["GET", "POST"])
async def search(form: Annotated[SearchForm, FormData()]):
    return {"results": do_search(form.query)}
```

### SEO

```python
@pjx.page("/about", title="About Us")
async def about():
    return {
        "seo": SEO(
            description="Learn about us.",
            og_image="/images/about-og.png",
        )
    }
```

Per-page SEO merges over the global defaults set in `PJX()`.

---

## Configuration (`pjx.toml`)

```toml
engine = "hybrid"          # "hybrid" | "jinja2" | "minijinja"
debug = false
validate_props = true
render_mode = "include"    # "include" | "inline"
log_json = false
log_level = "INFO"

template_dirs = ["app/templates"]
static_dir = "app/static"
pages_dir = "app/templates/pages"
components_dir = "app/templates/components"
layouts_dir = "app/templates/layouts"

# CORS
# cors_origins = ["https://example.com"]
# cors_methods = ["GET", "POST"]
# cors_credentials = false
```

Environment variable override with `PJX_` prefix: `PJX_DEBUG=true`.

---

## File-Based Routing

Enable with `pjx.auto_routes()`. Next.js-style conventions:

| File                          | URL                   |
| ----------------------------- | --------------------- |
| `pages/index.jinja`           | `/`                   |
| `pages/about.jinja`           | `/about`              |
| `pages/blog/[slug].jinja`     | `/blog/{slug}`        |
| `pages/docs/[...path].jinja`  | `/docs/{path:path}`   |
| `pages/(auth)/login.jinja`    | `/login` (group)      |
| `pages/api/users.py`          | `/api/users` (JSON)   |

**Special files** (not routes):

- `layout.jinja` -- wraps all pages in that directory and below.
- `loading.jinja` -- loading state template.
- `error.jinja` -- error state template.

---

## CSRF Protection

PJX uses double-submit cookie CSRF. Enable with `csrf=True` in `PJX()`.

### Layout Setup

Add to your layout `<body>` tag:

```html
<body hx-headers='{% if csrf_token is defined %}{"X-CSRFToken": "{{ csrf_token() }}"}{% endif %}'>
```

**IMPORTANT:** Use single quotes on the attribute because the JSON value
contains double quotes. This is critical -- double quotes break the HTML
attribute parsing and HTMX cannot read the token.

### Standalone Pages (no layout)

For pages that don't use the base layout (like login pages), add both:

```html
<body hx-headers='{% if csrf_token is defined %}{"X-CSRFToken": "{{ csrf_token() }}"}{% endif %}'>
  <form method="post" action="/auth/login">
    {% if csrf_token is defined %}
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}" />
    {% endif %}
    ...
  </form>
</body>
```

### Exempt Paths

SSE streams, webhooks, and health checks should be exempt:

```python
csrf_exempt_paths={"/sse/clock", "/api/webhooks", "/health", "/ready"}
```

---

## SSE (Server-Sent Events)

### Template Side

```jinja
<div live="/sse/clock" channel="clock">
  <!-- initial content, replaced by SSE -->
</div>
```

### Server Side

```python
from sse_starlette.sse import EventSourceResponse

async def clock_generator():
    while True:
        yield {"event": "clock", "data": pjx.partial("components/Clock.jinja", time=now())}
        await asyncio.sleep(1)

@app.get("/sse/clock")
async def sse_clock():
    return EventSourceResponse(clock_generator())
```

---

## Scoped CSS

Add `<style scoped>` to scope CSS to the component:

```jinja
<style scoped>
.card { border: 1px solid #ccc; }
.card:hover { border-color: blue; }
</style>

<div class="card">Scoped!</div>
```

Compiles to `.card[data-pjx-a1b2c3d] { ... }` and adds
`data-pjx-a1b2c3d` to the root element. Styles cannot leak to other
components.

---

## CLI Commands

```bash
pjx init my-app           # Scaffold new project
pjx dev .                  # Dev server with auto-reload
pjx run .                  # Production server
pjx build .                # Compile templates + bundle CSS
pjx check .                # Parse and validate all components
pjx add alpinejs           # Install npm package to vendor/
pjx remove alpinejs        # Remove npm package
```

---

## Attrs Passthrough

Extra attributes on a component that are NOT declared props get collected
into `{{ attrs }}`. The child component renders them:

```jinja
<!-- Parent -->
<UserCard name="Alice" class="highlighted" data-id="5" />
```

```jinja
<!-- UserCard.jinja -->
---
props { name: str }
---
<div class="user-card" {{ attrs }}>
  <!-- attrs = 'class="highlighted" data-id="5"' -->
  {{ props.name }}
</div>
```

---

## Best Practices

### Component Design

- **One component per file.** Name the file after the component: `Button.jinja`.
- **Always type props.** Use the `props { ... }` block with types and defaults.
- **Keep components small.** Extract sub-components instead of nesting deeply.
- **Use slots for composition.** Prefer slots over deeply nested prop drilling.
- **Prefer server-side state.** Use HTMX (`action:post`) over Alpine.js (`state`)
  when the operation involves data persistence.

### State Management

- **`state`** = client-side only (Alpine.js). Use for UI toggles, modals,
  counters that don't need persistence.
- **HTMX endpoints** = server-side state. Use for data that must persist
  (todos, messages, user data).
- **DON'T** mix: don't use `state` for data fetched from the server. Let
  HTMX swap the HTML instead.

### HTMX Patterns

- **Use `into` shorthand** instead of separate `target` + `swap`:
  `into="#list:innerHTML"` instead of `target="#list" swap="innerHTML"`.
- **Return HTML fragments** from HTMX endpoints, not JSON.
- **Use `pjx.partial()`** to render component fragments.
- **Set `hx-vals`** to pass extra context (like filter state) with requests.

### Layouts

- **Use one base layout** (`layouts/Base.jinja`) with SEO, assets, CSRF.
- **Standalone pages** (login, error) can skip the layout -- just write full
  HTML with their own `<head>` and `<body>`.
- **Use built-in layout components** (`VStack`, `HStack`, `Grid`) for page
  structure instead of writing raw flexbox CSS.

### Security

- **Always enable CSRF** in production (`csrf=True`).
- **Never use `bind:html`** with user input -- it bypasses auto-escaping.
- **Use `itsdangerous`** for session signing (via `SessionMiddleware`).
- **Rate-limit auth endpoints** with `slowapi`.
- **Set security headers** (CSP, X-Frame-Options) in middleware.

---

## Common Patterns

### Toast Notifications

```jinja
<!-- Toast.jinja -->
---
props {
  message: str,
  variant: str = "success",
}
---
<div class="toast toast--{{ props.variant }}" x-data x-init="setTimeout(() => $el.remove(), 3000)">
  {{ props.message }}
</div>
```

```python
# Endpoint returns toast HTML
@app.post("/htmx/action")
async def do_action():
    return HTMLResponse(pjx.partial("components/Toast.jinja", message="Done!", variant="success"))
```

### Inline Editing

```jinja
---
props { idx: int, text: str }
---
<div x-data="{ editing: false }">
  <span x-show="!editing">{{ props.text }}</span>
  <button on:click="editing = true" x-show="!editing">Edit</button>
  <form x-show="editing" action:put="/api/items/{{ props.idx }}" into="#list">
    <input type="text" name="text" value="{{ props.text }}" />
    <button type="submit">Save</button>
    <button type="button" on:click="editing = false">Cancel</button>
  </form>
</div>
```

### Search with Debounce

```jinja
<input type="text"
  action:get="/htmx/search"
  trigger="input changed delay:300ms"
  target="#results"
  placeholder="Search..." />
<div id="results"></div>
```

### Filter Buttons (Alpine + HTMX)

```jinja
<div x-data="{ filter: 'all' }">
  <input type="hidden" id="filter" bind:value="filter" />
  <button on:click="filter = 'active'"
    bind:class="filter === 'active' && 'active'"
    action:get="/htmx/filter?status=active"
    into="#list">
    Active
  </button>
</div>
```

### SSE Live Updates

```jinja
<div live="/sse/notifications" channel="notify">
  Waiting for updates...
</div>
```

```python
async def notify_stream():
    while True:
        event = await get_next_event()
        yield {"event": "notify", "data": pjx.partial("components/Notification.jinja", **event)}

@app.get("/sse/notifications")
async def sse_notifications():
    return EventSourceResponse(notify_stream())
```

---

## What NOT to Do

- **DON'T** use `print()` -- use `logging` for app logs, `rich` for CLI.
- **DON'T** use `os.path` -- use `pathlib`.
- **DON'T** put business logic in templates -- keep templates declarative.
- **DON'T** nest `reactive` elements -- one `x-data` scope per component.
- **DON'T** use double quotes for `hx-headers` with JSON values -- use single
  quotes on the attribute.
- **DON'T** return full pages from HTMX endpoints -- return fragments only.
- **DON'T** hardcode secrets -- use environment variables.
- **DON'T** skip CSRF in production -- all POST/PUT/DELETE need it.
- **DON'T** use `bind:html` with untrusted input -- XSS risk.
- **DON'T** import components you don't use -- the checker will warn.
