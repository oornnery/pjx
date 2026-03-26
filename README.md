# PJX

A Python DSL for reactive `.jinja` components — compiles to
Jinja2 + HTMX + Alpine.js.

Inspired by JSX, Svelte and SolidJS, PJX lets you write server-rendered
components with props, slots, reactive state and HTMX interactions using
a declarative syntax in `.jinja` files.

## Stack

| Layer              | Technology                                 |
| ------------------ | ------------------------------------------ |
| Language           | Python 3.14+                               |
| Template engine    | HybridEngine (default), Jinja2, MiniJinja  |
| Server framework   | FastAPI + Uvicorn                          |
| Reactivity         | Alpine.js (client-side)                    |
| Server interaction | HTMX                                       |
| SSE streaming      | sse-starlette                              |
| Validation         | Pydantic                                   |
| CLI                | Typer + Rich                               |
| CSS                | Scoped per component (optional)            |

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
engine = "hybrid"
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

props {
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

| Keyword      | Description                         |
| ------------ | ----------------------------------- |
| `import`     | Import components (`.jinja` files)  |
| `from`       | Import Python/Pydantic types        |
| `extends`    | Inherit from a layout               |
| `props`      | Declare typed props (name optional) |
| `slot`       | Declare named slots                 |
| `state`      | Reactive state (Alpine.js `x-data`) |
| `let`        | Local variable                      |
| `const`      | Constant                            |
| `computed`   | Computed value                      |
| `store`      | Alpine global store                 |
| `css`        | CSS asset declaration               |
| `js`         | JS asset declaration                |
| `middleware` | Middleware chain for the component  |

### Reactive Attributes

| PJX                 | Compiles to             | Framework |
| ------------------- | ----------------------- | --------- |
| `reactive`          | `x-data="{ ... }"`      | Alpine.js |
| `on:click="..."`    | `@click="..."`          | Alpine.js |
| `bind:model="..."`  | `x-model="..."`         | Alpine.js |
| `action:get="..."`  | `hx-get="..."`          | HTMX      |
| `action:post="..."` | `hx-post="..."`         | HTMX      |
| `target="..."`      | `hx-target="..."`       | HTMX      |
| `swap="..."`        | `hx-swap="..."`         | HTMX      |
| `into="#sel"`       | `hx-target` + `hx-swap` | HTMX      |
| `trigger="..."`     | `hx-trigger="..."`      | HTMX      |

The `into=` shorthand combines `hx-target` and `hx-swap` in a single attribute:

```html
<button into="#result">              <!-- hx-target="#result" hx-swap="innerHTML" -->
<button into="#result:outerHTML">    <!-- hx-target="#result" hx-swap="outerHTML" -->
```

### Control Flow

```html
<Show when="user.active">...</Show>
<Show when="user.active"><Else>Not active</Else></Show>
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

## File-Based Routing

PJX supports automatic file-based routing, inspired by Next.js and SvelteKit.
Call `pjx.auto_routes()` to scan the `pages/` directory and generate FastAPI
routes from the filesystem:

```python
pjx = PJX(app, config=PJXConfig(toml_path="pjx.toml"))
pjx.auto_routes()
```

### File conventions

| File pattern                    | Route               | Description                    |
| ------------------------------- | ------------------- | ------------------------------ |
| `pages/index.jinja`             | `/`                 | Root page                      |
| `pages/about.jinja`             | `/about`            | Static route                   |
| `pages/blog/[slug].jinja`       | `/blog/{slug}`      | Dynamic parameter              |
| `pages/docs/[...slug].jinja`    | `/docs/{slug:path}` | Catch-all (variable segments)  |
| `pages/(auth)/login.jinja`      | `/login`            | Route group (no URL prefix)    |

### Special files

- **`layout.jinja`** — Wraps all pages and subdirectories at the same level.
  Layouts nest: `pages/layout.jinja` wraps `pages/blog/layout.jinja` wraps
  `pages/blog/[slug].jinja`.
- **`loading.jinja`** — Loading skeleton shown via HTMX `hx-indicator`.
- **`error.jinja`** — Rendered when a handler returns an error. Receives
  `status_code` and `message` in the template context.

### Colocated Handlers

Python handlers can live alongside their templates using `RouteHandler` and
`APIRoute`:

```python
from pjx.routing import RouteHandler, APIRoute

handler = RouteHandler()

@handler.get
async def get():
    return {"items": await fetch_items()}

@handler.post
async def post(form: Annotated[ItemForm, FormData()]):
    await create_item(form)
    return {"items": await fetch_items()}

# JSON API endpoint (served under /api/ prefix)
api = APIRoute()

@api.get
async def list_items():
    return {"items": await fetch_items()}
```

## Layout Components

PJX includes built-in layout components (no import needed), inspired by
Chakra UI:

| Component      | Description                          | Key props                         |
| -------------- | ------------------------------------ | --------------------------------- |
| `<Center>`     | Center content both axes             | `w`, `h`                          |
| `<HStack>`     | Horizontal stack with gap            | `gap`, `align`, `justify`, `wrap` |
| `<VStack>`     | Vertical stack with gap              | `gap`, `align`, `justify`         |
| `<Grid>`       | Responsive CSS grid                  | `cols`, `gap`, `min`, `max`       |
| `<Spacer>`     | Flexible space between items         | —                                 |
| `<Container>`  | Max-width centered wrapper           | `max`, `px`                       |
| `<Divider>`    | Horizontal/vertical rule             | `orientation`, `color`            |
| `<Wrap>`       | Flex wrap with gap                   | `gap`, `align`, `justify`         |
| `<AspectRatio>`| Maintain content aspect ratio        | `ratio`                           |
| `<Hide>`       | Hide content by breakpoint           | `below`, `above`                  |

```html
<Container max="1200px">
  <VStack gap="1rem">
    <HStack gap="0.5rem" justify="space-between">
      <h1>Dashboard</h1>
      <Spacer />
      <Button label="Settings" />
    </HStack>
    <Divider />
    <Grid cols="3" gap="1rem" min="300px">
      <Card title="Users" />
      <Card title="Revenue" />
      <Card title="Orders" />
    </Grid>
    <Hide below="md">
      <AspectRatio ratio="16/9">
        <img src="/chart.png" />
      </AspectRatio>
    </Hide>
  </VStack>
</Container>
```

## Middleware

Components and pages can declare middleware in the frontmatter:

```html
---
middleware "auth", "rate_limit"
---
```

Register middleware handlers in the PJX runtime:

```python
@pjx.middleware("auth")
async def auth_middleware(request: Request, call_next):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401)
    response = await call_next(request)
    return response

@pjx.middleware("rate_limit")
async def rate_limit_middleware(request: Request, call_next):
    response = await call_next(request)
    return response
```

Middleware declared in the frontmatter runs in declaration order. Layout
middleware runs before page middleware.

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

## Attrs Passthrough

Attributes not declared as props are passed through to the component's root
element via `{{ attrs }}`. This enables HTML, HTMX, and Alpine attributes
without declaring each one as a prop:

```html
---
props {
  label: str,
  variant: str = "primary",
}
---

<button class="btn btn-{{ props.variant }}" {{ attrs }}>
  {{ props.label }}
</button>
```

Usage — `class` and `hx-get` are extras, not declared props:

```html
<Button label="Save" class="mt-4" hx-get="/save" />
```

## Asset Pipeline

Components declare CSS/JS dependencies in frontmatter. PJX collects,
deduplicates, and renders `<link>`/`<script>` tags automatically:

```html
---
css "components/card.css"
js "components/card.js"
---

<div class="card">...</div>
```

In the layout, render collected assets with `{{ pjx_assets.render() }}`:

```html
<head>
  {{ pjx_assets.render() }}
</head>
```

## Runtime Prop Validation

When `validate_props = true` (default), PJX validates props against their
declared types at render time using Pydantic models. Missing required props
or type mismatches raise `PropValidationError` with clear messages:

```python
config = PJXConfig(validate_props=True)  # default
```

Disable in production for performance:

```python
config = PJXConfig(validate_props=False)
```

## Static Analysis

`pjx check` validates components statically without running the server:

- **Import resolution** — verifies all imports resolve to existing files
- **Props checking** — verifies required props are passed to child components
- **Slot checking** — verifies slot passes match declared slots in children

```bash
pjx check .
```

## Render Modes

PJX supports two render modes, configurable via `render_mode`:

| Mode      | How it works                                              | Best for  |
| --------- | --------------------------------------------------------- | --------- |
| `include` | Standard `{% include %}` (default)                        | Jinja2    |
| `inline`  | Inlines all includes into a flat template at compile time | MiniJinja |

Inline mode eliminates `{% include %}` overhead, enabling MiniJinja's
`render_string` path which is 10-67x faster than Jinja2's ad-hoc compilation:

```python
config = PJXConfig(engine="minijinja", render_mode="inline")
```

## CLI

```bash
pjx init <dir>          # Scaffold project
pjx dev <dir>           # Dev server with hot reload
pjx build               # Compile all .jinja + bundle CSS
pjx check               # Validate imports, props, and slots
pjx format              # Re-format .jinja files
pjx add <pkg>           # Install JS package + copy to vendor/
```

## Benchmarks — Jinja2 vs MiniJinja

Measured with `pytest-benchmark` on Python 3.14 (64 tests, WSL2 Linux).

### Pre-registered templates (`render`) — production path

Templates are compiled once at startup and reused. This is the hot path.

| Scenario              | Jinja2      | MiniJinja    | Winner          |
| --------------------- | ----------- | ------------ | --------------- |
| Minimal template      | 8.9 us      | **3.1 us**   | MiniJinja 2.9x  |
| Simple variable       | 8.4 us      | **3.1 us**   | MiniJinja 2.7x  |
| Loop (10 items)       | 14.6 us     | **7.5 us**   | MiniJinja 1.9x  |
| Loop (1000 items)     | 592 us      | **439 us**   | MiniJinja 1.3x  |
| HTMX page (30 todos)  | 228 us      | **169 us**   | MiniJinja 1.3x  |
| Layout                | **17.1 us** | 20.2 us      | Jinja2 1.2x     |
| Filters               | **18.2 us** | 23.6 us      | Jinja2 1.3x     |
| Conditionals          | **30.1 us** | 48.3 us      | Jinja2 1.6x     |
| Deep nesting          | **170 us**  | 426 us       | Jinja2 2.5x     |
| HTML escaping (50)    | **110 us**  | 221 us       | Jinja2 2x       |
| Variables (50)        | **40.6 us** | 79.8 us      | Jinja2 2x       |
| Complex component     | **46.7 us** | 96 us        | Jinja2 2.1x     |
| Throughput (100x)     | **4.7 ms**  | 9.4 ms       | Jinja2 2x       |
| Nested loops (50x20)  | **489 us**  | 1,536 us     | Jinja2 3.1x     |

### Ad-hoc compilation (`render_string`) — inline render path

This is the path used by inline render mode (`render_mode = "inline"`),
where MiniJinja's Rust parser dominates.

| Scenario              | Jinja2       | MiniJinja    | Winner              |
| --------------------- | ------------ | ------------ | ------------------- |
| Minimal template      | 326 us       | **4.4 us**   | MiniJinja **74x**   |
| Simple variable       | 303 us       | **4.4 us**   | MiniJinja **69x**   |
| Loop (10 items)       | 561 us       | **9.8 us**   | MiniJinja **57x**   |
| Filters               | 1,503 us     | **29 us**    | MiniJinja **52x**   |
| Layout                | 960 us       | **24.4 us**  | MiniJinja **39x**   |
| Variables (50)        | 3,716 us     | **101 us**   | MiniJinja **37x**   |
| Conditionals          | 1,455 us     | **55.8 us**  | MiniJinja **26x**   |
| Complex component     | 2,390 us     | **105 us**   | MiniJinja **23x**   |
| HTMX page (30 todos)  | 1,932 us     | **179 us**   | MiniJinja **11x**   |
| Deep nesting          | 1,593 us     | **432 us**   | MiniJinja **3.7x**  |
| HTML escaping (50)    | 797 us       | **212 us**   | MiniJinja **3.8x**  |
| Loop (1000 items)     | 1,150 us     | **453 us**   | MiniJinja **2.5x**  |
| Nested loops (50x20)  | **1,363 us** | 1,538 us     | Jinja2 1.1x         |

### Recommendation

**Default:** HybridEngine (`engine = "hybrid"`) — automatically selects the
optimal engine per template. Uses Jinja2 bytecode cache for pre-registered
templates and MiniJinja's Rust parser for ad-hoc/inline compilation.

**Jinja2 only:** `engine = "jinja2"` with `render_mode = "include"` — bytecode
cache wins on throughput for pre-registered templates (2-3x faster).

**Inline mode:** MiniJinja with `render_mode = "inline"` — Rust parser
dominates ad-hoc compilation (10-74x faster). Best for on-the-fly rendering
and dynamic content where templates change frequently.

Run benchmarks: `uv run pytest tests/benchmark/ -v --benchmark-sort=mean`

## Performance Optimizations

### Mtime-based template caching

`_compile_template()` checks each file's mtime before recompilation. If the
source has not changed since the last compile, the cached result is returned
immediately. Cold compile takes ~33 ms; cached lookups take ~2.7 ms (12x
speedup).

### Diamond import deduplication

A `_seen` set in the compilation pipeline prevents shared dependencies from
being compiled more than once. In a diamond dependency graph
(A->B->D, A->C->D), template D is compiled exactly once.

### Lexer constant hoisting

The `_SINGLE` and `_ESCAPES` lookup dicts used by the lexer are now
module-level constants instead of being rebuilt on every loop iteration.

### O(1) tag recovery

Tag-recovery regexes are compiled once per tag name and cached. The search
resumes from the last matched position instead of re-scanning the entire
source string.

## Roadmap

### Done

- [x] Attrs passthrough — extra HTML/HTMX/Alpine attributes pass through
      to child components via `{{ attrs }}`
- [x] Asset pipeline — `css`/`js` frontmatter declarations, `AssetCollector`
      with dedup, `{{ pjx_assets.render() }}` in layouts
- [x] Runtime prop validation — Pydantic models cached per template,
      validated at render time with `PropValidationError`
- [x] Inline render mode — `inline_includes()` flattens `{% include %}` at
      compile time for MiniJinja's 10-74x faster `render_string` path
- [x] Static analysis — `pjx check` validates imports, props, and slots
- [x] `pjx build` — compile all templates + bundle scoped CSS
- [x] `pjx format` — re-format `.jinja` files
- [x] File-based routing — `pjx.auto_routes()`, dynamic `[slug]` and
      catch-all `[...slug]` params, route groups `(name)/`, nested layouts
- [x] Layout components — built-in `<Center>`, `<HStack>`, `<VStack>`,
      `<Grid>`, `<Spacer>`, `<Container>`, `<Divider>`, `<Wrap>`,
      `<AspectRatio>`, `<Hide>`
- [x] Middleware — frontmatter `middleware "auth"` + `@pjx.middleware("auth")`
- [x] Colocated handlers — `RouteHandler` and `APIRoute` helpers

### Planned

- [ ] Hot reload — watch `.jinja` files and recompile on change (dev mode)
- [ ] Tailwind CSS integration via `pjx add tailwind`
- [x] SSE streaming with `PJX.sse()` decorator — `sse-starlette` backend,
      `live=`/`channel=` attributes, SSE clock demo at `/clock`
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
