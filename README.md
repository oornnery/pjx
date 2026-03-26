# PJX

A Python DSL for reactive `.jinja` components — compiles to
Jinja2 + HTMX + Alpine.js.

Inspired by JSX, Svelte and SolidJS, PJX lets you write server-rendered
components with props, slots, reactive state and HTMX interactions using
a declarative syntax in `.jinja` files.

## Stack

| Layer              | Technology                        |
| ------------------ | --------------------------------- |
| Language           | Python 3.14+                      |
| Template engine    | Jinja2 (default), MiniJinja (opt) |
| Server framework   | FastAPI + Uvicorn                 |
| Reactivity         | Alpine.js (client-side)           |
| Server interaction | HTMX                              |
| Validation         | Pydantic                          |
| CLI                | Typer + Rich                      |
| CSS                | Scoped per component (optional)   |

## Installation

```bash
uv add pjx
```

## Quick Start

### 1. Initialize project

```bash
pjx init my-app
cd my-app
```

### 2. Configure (`pjx.toml`)

```toml
engine = "jinja2"
debug = true

template_dirs = ["templates"]
static_dir = "static"
```

### 3. Create application (`app.py`)

```python
from pathlib import Path

from fastapi import FastAPI

from pjx import PJX, PJXConfig, SEO

app = FastAPI()
pjx = PJX(
    app,
    config=PJXConfig(toml_path=Path(__file__).parent / "pjx.toml"),
    seo=SEO(title="My App", description="Built with PJX."),
)


@pjx.page("/", template="pages/Home.jinja", title="Home — My App")
async def home():
    return {"message": "Hello, PJX!"}
```

### 4. Create a layout (`templates/layouts/Base.jinja`)

Layouts are PJX components that use `<Slot />` to inject page content:

```html
---
import Navbar from "../components/Navbar.jinja"

props BaseLayoutProps = {
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
<body>
  <Navbar />
  <main><Slot /></main>
</body>
</html>
```

### 5. Create a component (`templates/components/Counter.jinja`)

```html
---
state count = 0
---

<div class="counter" reactive>
  <button on:click="count--">−</button>
  <span x-text="count">0</span>
  <button on:click="count++">+</button>
</div>
```

### 6. Create a page (`templates/pages/Home.jinja`)

Pages import the layout and wrap their content with it:

```html
---
import Layout from "../layouts/Base.jinja"
import Counter from "../components/Counter.jinja"
---

<Layout>
  <div class="page">
    <h1>{{ message }}</h1>
    <Counter />
  </div>
</Layout>
```

### 7. Run

```bash
pjx dev .
```

## Component Syntax

Every component is a `.jinja` file with a declarative frontmatter (`---`)
and an HTML body:

```html
---
import Layout from "../layouts/Base.jinja"
import UserCard from "../components/UserCard.jinja"

props DashboardProps = {
  title: str = "Dashboard",
  users: list = [],
}

state editing = false
---

<Layout>
  <div class="dashboard" reactive>
    <h1>{{ props.title }}</h1>
    <For each="users" as="user">
      <UserCard name="{{ user.name }}" avatar="{{ user.avatar }}">
        <Slot:actions>
          <button action:post="/htmx/message/{{ user.id }}"
            target="#toast" swap="beforeend">
            Message
          </button>
        </Slot:actions>
      </UserCard>
    </For>
  </div>
</Layout>
```

### Frontmatter

| Keyword    | Description                               |
| ---------- | ----------------------------------------- |
| `import`   | Import components (`.jinja` files)        |
| `from`     | Import Python/Pydantic types              |
| `extends`  | Inherit from a layout                     |
| `props`    | Declare typed props with defaults         |
| `slot`     | Declare named slots                       |
| `state`    | Reactive state (Alpine.js `x-data`)       |
| `let`      | Local variable                            |
| `const`    | Constant                                  |
| `computed` | Computed value                            |
| `store`    | Alpine global store                       |

### Reactive Attributes

| PJX                 | Compiles to        | Framework |
| ------------------- | ------------------ | --------- |
| `reactive`          | `x-data="{ ... }"` | Alpine.js |
| `on:click="..."`    | `@click="..."`     | Alpine.js |
| `bind:model="..."`  | `x-model="..."`    | Alpine.js |
| `action:get="..."`  | `hx-get="..."`     | HTMX      |
| `action:post="..."` | `hx-post="..."`    | HTMX      |
| `target="..."`      | `hx-target="..."`  | HTMX      |
| `swap="..."`        | `hx-swap="..."`    | HTMX      |
| `trigger="..."`     | `hx-trigger="..."` | HTMX      |

### Control Flow

```html
<Show when="user.active">...</Show>
<For each="items" as="item">...</For>
<Switch on="status">
  <Case value="active">...</Case>
  <Case value="inactive">...</Case>
</Switch>
```

## FastAPI Integration

### Global SEO

The `SEO` dataclass defines metadata applied to all pages. Per-page fields
(via `title=` on the decorator or `seo` in the handler return) override
the global defaults:

```python
pjx = PJX(
    app,
    config=PJXConfig(toml_path="pjx.toml"),
    seo=SEO(title="My App", description="Default SEO."),
)

@pjx.page("/about", template="pages/About.jinja", title="About — My App")
async def about():
    return {"content": "..."}
```

### FormData with Annotated

Handlers can receive Pydantic models parsed from form data (POST) or
query params (GET):

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

### HTMX Partials

Endpoints that return HTML fragments for HTMX swaps use `pjx.render()`
to render PJX components — no raw HTML in the backend:

```python
@app.post("/htmx/todos/add")
async def htmx_add(request: Request) -> HTMLResponse:
    form = await request.form()
    todos_db.append({"text": form["text"], "done": False})
    return HTMLResponse(
        pjx.render("components/TodoList.jinja", {"todos": todos_db})
    )
```

## Project Structure

```text
my-app/
├── templates/
│   ├── pages/           # Pages
│   ├── components/      # Reusable components
│   └── layouts/         # Base layouts
├── static/
│   ├── css/             # Stylesheets
│   ├── js/              # Scripts
│   └── images/          # Images
├── app.py               # FastAPI application
└── pjx.toml             # Configuration
```

## CLI

```bash
pjx init <dir>          # Scaffold project
pjx dev <dir>           # Dev server with hot reload
pjx build               # Compile all .jinja + bundle CSS
pjx check               # Check syntax
pjx add <pkg>           # Install JS package + copy to vendor/
```

## Benchmarks — Jinja2 vs MiniJinja

Measured with `pytest-benchmark` on Python 3.14 (64 tests, WSL2 Linux).

### Pre-registered templates (`render`) — production path

Templates are compiled once at startup and reused. This is the hot path.

| Scenario             | Jinja2      | MiniJinja  | Winner         |
| -------------------- | ----------- | ---------- | -------------- |
| Simple variable      | 9.1 us      | **3.2 us** | MiniJinja 2.8x |
| Loop (10 items)      | 16.1 us     | **7.8 us** | MiniJinja 2.1x |
| Loop (1000 items)    | 622 us      | **446 us** | MiniJinja 1.4x |
| HTMX page (30 todos) | 246 us      | **172 us** | MiniJinja 1.4x |
| Layout               | **17.6 us** | 20.7 us    | Jinja2 1.2x    |
| Filters              | **19 us**   | 24.5 us    | Jinja2 1.3x    |
| Conditionals         | **33 us**   | 53 us      | Jinja2 1.6x    |
| HTML escaping (50)   | **128 us**  | 218 us     | Jinja2 1.7x    |
| Variables (50)       | **44.5 us** | 90 us      | Jinja2 2x      |
| Complex component    | **48 us**   | 101 us     | Jinja2 2.1x    |
| Throughput (100x)    | **4.6 ms**  | 9.8 ms     | Jinja2 2.1x    |
| Nested loops (50x20) | **522 us**  | 1,628 us   | Jinja2 3.1x    |

### Ad-hoc compilation (`render_string`) — compile + render each call

| Scenario             | Jinja2       | MiniJinja  | Winner             |
| -------------------- | ------------ | ---------- | ------------------ |
| Simple variable      | 305 us       | **4.5 us** | MiniJinja **67x**  |
| Loop (10 items)      | 581 us       | **9.7 us** | MiniJinja **60x**  |
| Filters              | 1,474 us     | **29 us**  | MiniJinja **51x**  |
| Layout               | 992 us       | **24 us**  | MiniJinja **41x**  |
| Variables (50)       | 3,701 us     | **99 us**  | MiniJinja **37x**  |
| HTMX page (30 todos) | 1,830 us     | **178 us** | MiniJinja **10x**  |
| HTML escaping (50)   | 757 us       | **215 us** | MiniJinja **3.5x** |
| Loop (1000 items)    | 1,144 us     | **444 us** | MiniJinja **2.6x** |
| Nested loops (50x20) | **1,357 us** | 1,545 us   | Jinja2 1.1x        |

**Current default: Jinja2** — templates are pre-compiled at startup, where Jinja2's
bytecode cache wins on throughput. MiniJinja's Rust parser dominates ad-hoc
compilation (10-67x faster) and is the better choice for on-the-fly rendering.

Run benchmarks: `uv run pytest tests/benchmark/ -v --benchmark-sort=mean`

## Roadmap

- [ ] On-the-fly rendering mode — inline all `{% include %}` at compile time
      to produce flat templates, enabling `render_string` path where MiniJinja
      is 10-67x faster
- [ ] Hot reload — watch `.jinja` files and recompile on change (dev mode)
- [ ] `pjx build` — pre-compile all templates + bundle scoped CSS
- [ ] `pjx init` — scaffold project with layout, components, and config
- [ ] `pjx check` — validate component syntax without running server
- [ ] Tailwind CSS integration via `pjx add tailwind`
- [ ] SSE streaming with `PJX.sse()` decorator
- [ ] MiniJinja benchmark parity — investigate nested loop / escaping gap

## Development

```bash
uv sync
uv run ruff format .        # Format
uv run ruff check . --fix   # Lint
uv run ty check             # Type check
uv run pytest -v            # Tests
```

## Docs

- [IDEA.md](docs/IDEA.md) — Full DSL specification
- [SPEC.md](docs/SPEC.md) — Technical spec (EBNF, compilation, modules)
- [PLAN.md](docs/PLAN.md) — Implementation roadmap
