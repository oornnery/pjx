# PJX

[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/pjx.svg)](https://pypi.org/project/pjx/)

**Reactive components for Python** — write declarative `.jinja` files with
props, slots, state, and control flow. PJX compiles them to
**Jinja2 + HTMX + Alpine.js**, served by **FastAPI**.

```html
---
state count = 0
---

<div class="counter" reactive>
  <button on:click="count--">-</button>
  <span x-text="count">0</span>
  <button on:click="count++">+</button>
</div>
```

Compiles to:

```html
<div class="counter" x-data="{ count: 0 }">
  <button @click="count--">-</button>
  <span x-text="count">0</span>
  <button @click="count++">+</button>
</div>
```

---

## Features

- **Component DSL** — props, slots, state, imports, and control flow in a frontmatter block
- **Reactive state** — `state` compiles to Alpine.js `x-data`; `on:click`, `bind:model` shorthand
- **HTMX integration** — `action:post`, `target`, `swap`, `into=` shorthand for `hx-*` attributes
- **File-based routing** — `pages/` filesystem maps to FastAPI routes (`[slug]`, `[...path]`, `(group)`)
- **Layout components** — `<Center>`, `<HStack>`, `<VStack>`, `<Grid>`, `<Container>` and more
- **Scoped CSS** — `<style scoped>` compiles to `[data-pjx-HASH]` attribute selectors
- **Dual engine** — HybridEngine picks Jinja2 or MiniJinja per template (up to 74x faster ad-hoc)
- **Static analysis** — `pjx check` validates imports, props, and slots at compile time
- **Production security** — CSRF, signed sessions, rate limiting, SSE limits, health checks

---

## Installation

```bash
uv add pjx
```

## Quick Start

### 1. Scaffold a project

```bash
pjx init my-app && cd my-app
```

This scaffolds:

```text
my-app/
  pjx.toml              # Configuration
  app/
    main.py              # FastAPI + PJX entrypoint
    core/config.py       # Settings
    pages/               # Page route handlers
    api/v1/              # JSON API endpoints
    models/              # Pydantic schemas
    services/            # Business logic
    middleware/           # Custom middleware
    templates/
    static/
```

### 2. Create a layout (`app/templates/layouts/Base.jinja`)

```html
---
props {
  title: str = "My App",
}

slot default
---

<!DOCTYPE html>
<html lang="en">
<head>
  <title>{{ seo.title|default(props.title) }}</title>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
  <script src="https://unpkg.com/htmx.org@2/dist/htmx.min.js"></script>
</head>
<body hx-headers='{"X-CSRFToken": "{{ csrf_token() }}"}'>
  <main><Slot /></main>
</body>
</html>
```

### 3. Create a page (`app/templates/pages/Home.jinja`)

```html
---
import Layout from "../layouts/Base.jinja"
import Counter from "../components/Counter.jinja"
---

<Layout>
  <h1>{{ message }}</h1>
  <Counter />
</Layout>
```

### 4. Run

```bash
pjx dev .
```

---

## Component Syntax

Every `.jinja` file has a frontmatter (`---`) and an HTML body:

```html
---
import Layout from "../layouts/Base.jinja"
import UserCard from "../components/UserCard.jinja"

props {
  title: str = "Dashboard",
  users: list = [],
}

state editing = false

slot actions
---

<Layout>
  <div class="dashboard" reactive>
    <h1>{{ props.title }}</h1>
    <For each="users" as="user">
      <UserCard name="{{ user.name }}">
        <Slot:actions>
          <button action:post="/api/message/{{ user.id }}" into="#toast">
            Message
          </button>
        </Slot:actions>
      </UserCard>
    </For>
  </div>
</Layout>
```

### Frontmatter Keywords

| Keyword      | Description                        |
| ------------ | ---------------------------------- |
| `import`     | Import child components (`.jinja`) |
| `props`      | Typed props with defaults          |
| `state`      | Alpine.js reactive state           |
| `computed`   | Derived values                     |
| `slot`       | Named slot declarations            |
| `css`/`js`   | Asset dependencies                 |
| `middleware` | Middleware chain for the component |

### Attribute Mapping

| PJX                 | Compiles to             | Framework |
| ------------------- | ----------------------- | --------- |
| `reactive`          | `x-data="{ ... }"`      | Alpine.js |
| `on:click="..."`    | `@click="..."`          | Alpine.js |
| `bind:model="..."`  | `x-model="..."`         | Alpine.js |
| `action:get="..."`  | `hx-get="..."`          | HTMX      |
| `action:post="..."` | `hx-post="..."`         | HTMX      |
| `target="..."`      | `hx-target="..."`       | HTMX      |
| `swap="..."`        | `hx-swap="..."`         | HTMX      |
| `into="#el:swap"`   | `hx-target` + `hx-swap` | HTMX      |
| `trigger="..."`     | `hx-trigger="..."`      | HTMX      |

### Control Flow

```html
<Show when="user.active">...</Show>
<Show when="user.active"><Else>Not active</Else></Show>
<For each="items" as="item">...</For>
<Switch on="status">
  <Case value="active">Active</Case>
  <Case value="inactive">Inactive</Case>
</Switch>
```

---

## HTMX Partials

Return HTML fragments for HTMX swaps using `pjx.render()`:

```python
@app.post("/htmx/todos/add")
async def add_todo(request: Request) -> HTMLResponse:
    form = await request.form()
    todos.append({"text": form["text"], "done": False})
    return HTMLResponse(pjx.render("components/TodoList.jinja", {"todos": todos}))
```

## FormData

Parse form data into Pydantic models:

```python
from typing import Annotated
from pydantic import BaseModel
from pjx import FormData

class SearchForm(BaseModel):
    query: str = ""

@pjx.page("/search", methods=["GET", "POST"])
async def search(form: Annotated[SearchForm, FormData()]):
    return {"results": do_search(form.query)}
```

## File-Based Routing

```python
pjx.auto_routes()  # scans templates/pages/
```

| File pattern                 | Route               |
| ---------------------------- | ------------------- |
| `pages/index.jinja`          | `/`                 |
| `pages/about.jinja`          | `/about`            |
| `pages/blog/[slug].jinja`    | `/blog/{slug}`      |
| `pages/docs/[...path].jinja` | `/docs/{path:path}` |
| `pages/(auth)/login.jinja`   | `/login`            |

Special files: `layout.jinja` (nested layouts), `loading.jinja` (HTMX indicator), `error.jinja` (error pages).

## Layout Components

Built-in components inspired by Chakra UI (no import needed):

```html
<Container max="1200px">
  <VStack gap="1rem">
    <HStack gap="0.5rem" justify="space-between">
      <h1>Dashboard</h1>
      <Spacer />
      <button>Settings</button>
    </HStack>
    <Divider />
    <Grid cols="3" gap="1rem" min="300px">
      <Card title="Users" />
      <Card title="Revenue" />
    </Grid>
  </VStack>
</Container>
```

`Center`, `HStack`, `VStack`, `Grid`, `Spacer`, `Container`, `Divider`, `Wrap`, `AspectRatio`, `Hide`

---

## CLI

```bash
pjx init <dir>      # Scaffold project
pjx dev <dir>       # Dev server with hot reload
pjx build           # Compile templates + bundle CSS
pjx check           # Validate imports, props, slots
pjx format          # Re-format .jinja files
```

## Configuration

### `pjx.toml`

```toml
engine = "hybrid"         # hybrid, jinja2, minijinja
debug = false
validate_props = true
render_mode = "include"   # include, inline

template_dirs = ["app/templates"]
static_dir = "app/static"

log_json = true
log_level = "INFO"
```

All fields can be overridden with `PJX_` prefixed environment variables:

```bash
export PJX_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
export PJX_DEBUG=false
```

### PJX Constructor

| Parameter           | Type        | Description                  |
| ------------------- | ----------- | ---------------------------- |
| `app`               | `FastAPI`   | FastAPI application instance |
| `config`            | `PJXConfig` | Configuration from `pjx.toml`|
| `layout`            | `str`       | Default layout template      |
| `seo`               | `SEO`       | Global SEO metadata          |
| `csrf`              | `bool`      | Enable CSRF middleware       |
| `csrf_secret`       | `str`       | Secret key for CSRF signing  |
| `csrf_exempt_paths` | `set[str]`  | Paths exempt from CSRF       |
| `health`            | `bool`      | Enable `/health` + `/ready`  |

---

## Security

PJX includes production security out of the box:

- **CSRF** — double-submit cookie with HTMX `hx-headers` integration
- **Signed sessions** — `SessionMiddleware` + `itsdangerous`
- **Rate limiting** — `slowapi` on auth/mutation endpoints
- **SSE limits** — per-IP connection tracking with max duration
- **Health checks** — `/health` (liveness) and `/ready` (readiness)

See [Security Guide](https://github.com/oornnery/pjx/wiki/Security) for the full production checklist.

---

## Project Structure

```text
my-app/
  pjx.toml                # Configuration
  app/
    main.py                # FastAPI + PJX entrypoint
    core/config.py         # Settings (SECRET_KEY, HOST, PORT)
    pages/                 # Page route handlers
    api/v1/                # JSON API endpoints
    models/                # Pydantic schemas
    services/              # Business logic
    middleware/             # Custom middleware
    templates/
      pages/               # PJX page templates
      components/          # Reusable components
      layouts/             # Base layouts with <Slot />
    static/
      css/
      js/
      vendor/              # Installed via pjx add
```

---

## Documentation

Full documentation is available on the [Wiki](https://github.com/oornnery/pjx/wiki):

- [Installation](https://github.com/oornnery/pjx/wiki/Installation)
- [Quick Start](https://github.com/oornnery/pjx/wiki/Quick-Start)
- [Component Syntax](https://github.com/oornnery/pjx/wiki/Component-Syntax)
- [Props and Validation](https://github.com/oornnery/pjx/wiki/Props-and-Validation)
- [State and Reactivity](https://github.com/oornnery/pjx/wiki/State-and-Reactivity)
- [HTMX Integration](https://github.com/oornnery/pjx/wiki/HTMX-Integration)
- [File-Based Routing](https://github.com/oornnery/pjx/wiki/File-Based-Routing)
- [Layout Components](https://github.com/oornnery/pjx/wiki/Layout-Components)
- [Template Engines](https://github.com/oornnery/pjx/wiki/Template-Engines)
- [Security](https://github.com/oornnery/pjx/wiki/Security)
- [Deployment](https://github.com/oornnery/pjx/wiki/Deployment)
- [CLI Reference](https://github.com/oornnery/pjx/wiki/CLI-Reference)

---

## Development

```bash
uv sync                         # Install dependencies
uv run task format              # Format (ruff)
uv run task lint                # Lint + autofix (ruff)
uv run task check               # Format + lint + markdown lint
uv run task typecheck           # Type check (ty)
uv run task test                # Run all tests (512 passing)
uv run task cov                 # Tests with coverage report
uv run task ci                  # Full CI pipeline (check + typecheck + test)
```

## License

[MIT](LICENSE) - Fabio Souza
