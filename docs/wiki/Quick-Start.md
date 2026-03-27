# Quick Start

This tutorial walks through creating a PJX application from scratch. By the
end you will have a working FastAPI app with a reactive counter component,
a base layout, and a home page -- all written in the PJX DSL.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager

---

## 1. Initialize the Project

Scaffold a new project with the PJX CLI:

```bash
pjx init my-app
cd my-app
```

This creates the following directory structure:

```text
my-app/
├── pjx.toml                    # Configuration
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI + PJX entrypoint
│   ├── core/config.py          # Settings
│   ├── pages/                  # Page route handlers
│   ├── api/v1/                 # JSON API endpoints
│   ├── models/                 # Pydantic schemas
│   ├── services/               # Business logic
│   ├── middleware/              # Custom middleware
│   ├── templates/
│   │   ├── pages/              # Page templates
│   │   ├── components/         # Reusable components
│   │   └── layouts/            # Base layouts
│   └── static/
│       ├── css/
│       ├── js/
│       └── images/
```

If you prefer to set things up manually, create the directories yourself:

```bash
mkdir -p my-app/app/{templates/{pages,components,layouts},static/{css,js,images}}
cd my-app
```

Install PJX into the project:

```bash
uv init
uv add pjx
```

---

## 2. Configure pjx.toml

Create `pjx.toml` in the project root. This is the minimal configuration
needed for development:

```toml
engine = "hybrid"
debug = true
validate_props = true
render_mode = "include"

template_dirs = ["app/templates"]
static_dir = "app/static"
```

### Field reference

| Field             | Type       | Description                                                                                               |
| ----------------- | ---------- | --------------------------------------------------------------------------------------------------------- |
| `engine`          | `str`      | Template engine: `"hybrid"` (auto-selects optimal engine), `"jinja2"`, or `"minijinja"`.                  |
| `debug`           | `bool`     | Enable debug mode. Shows detailed error pages and disables static file caching.                           |
| `validate_props`  | `bool`     | Validate component props against their declared types at render time using Pydantic. Disable in prod.     |
| `render_mode`     | `str`      | `"include"` uses standard Jinja2 includes. `"inline"` flattens all includes at compile time (faster).     |
| `template_dirs`   | `list`     | Directories to search for `.jinja` templates, relative to the project root.                               |
| `static_dir`      | `str`      | Directory for static assets (CSS, JS, images), served at `/static/`.                                      |

Additional fields for production (`log_json`, `log_level`, `cors_origins`,
etc.) are covered in [[Configuration]].

---

## 3. Create app/main.py

This is the FastAPI application entry point. It initializes PJX, configures
session middleware, and declares page routes.

Create `app/main.py`:

```python
import os
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from pjx import PJX, PJXConfig, SEO

app = FastAPI()

# Signed session cookies (required for CSRF and auth)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("PJX_SECRET_KEY", "change-me-in-production"),
)

# Initialize PJX
pjx = PJX(
    app,
    config=PJXConfig(toml_path=Path(__file__).resolve().parents[1] / "pjx.toml"),
    seo=SEO(title="My App", description="Built with PJX."),
    csrf=True,
    csrf_secret=os.environ.get("PJX_SECRET_KEY", "change-me-in-production"),
    health=True,
)


@pjx.page("/", template="pages/Home.jinja", title="Home -- My App")
async def home():
    return {"message": "Hello, PJX!"}
```

### What each part does

**`PJXConfig`** loads settings from `pjx.toml`. The `toml_path` argument
points to the config file at the project root (one level above `app/`).

**`SEO`** defines default metadata for all pages. The `title` and
`description` appear in `<meta>` tags. Per-page overrides are set with the
`title=` argument on `@pjx.page()` or by returning an `seo` dict from the
handler.

**`csrf=True`** enables double-submit cookie CSRF protection. All
non-GET/HEAD/OPTIONS requests are validated automatically. HTMX requests
send the token via `hx-headers` (configured in the layout).

**`health=True`** registers `/health` (liveness) and `/ready` (readiness)
endpoints.

**`@pjx.page()`** registers a FastAPI route that renders a PJX template.
The dict returned by the handler becomes the template context -- here,
`{{ message }}` will resolve to `"Hello, PJX!"`.

---

## 4. Create a Layout

Layouts are PJX components that wrap pages. They define the HTML boilerplate,
load CDN scripts, and render collected CSS/JS assets.

Create `app/templates/layouts/Base.jinja`:

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
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{{ seo.title|default(props.title) }}</title>

  <!-- SEO meta tags (populated from the SEO dataclass) -->
  <Show when="seo is defined and seo.description">
    <meta name="description" content="{{ seo.description }}" />
  </Show>

  <!-- Collected CSS assets from components -->
  {{ pjx_assets.render_css() }}

  <!-- Alpine.js for client-side reactivity -->
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
  <!-- HTMX for server interactions -->
  <script src="https://unpkg.com/htmx.org@2/dist/htmx.min.js"></script>
</head>
<body hx-headers='{"X-CSRFToken": "{{ csrf_token() }}"}'>
  <main>
    <Slot />
  </main>

  <!-- Collected JS assets from components -->
  {{ pjx_assets.render_js() }}
</body>
</html>
```

### Key concepts

**Frontmatter** (`---` delimiters) declares the component's interface. Here
it defines a `title` prop with a default value and a `default` slot.

**`<Slot />`** is where child content gets injected. When a page wraps its
content with `<Layout>...</Layout>`, everything between the tags replaces
`<Slot />`.

**`{{ pjx_assets.render_css() }}`** and **`{{ pjx_assets.render_js() }}`**
render `<link>` and `<script>` tags for all CSS and JS assets declared in
component frontmatter. PJX collects and deduplicates these automatically.

**`{{ csrf_token() }}`** in `hx-headers` ensures all HTMX requests include
the CSRF token. This is required when `csrf=True` is set in the PJX
constructor.

**`<Show when="...">`** is a PJX control flow component that conditionally
renders its children. It compiles to `{% if ... %}`.

---

## 5. Create a Component

Components are reusable `.jinja` files with their own state, props, and
behavior. The PJX DSL compiles reactive attributes into Alpine.js and HTMX
directives.

Create `app/templates/components/Counter.jinja`:

```html
---
state count = 0
---

<div class="counter" reactive>
  <button on:click="count--">-</button>
  <span x-text="count">0</span>
  <button on:click="count++">+</button>
  <button on:click="count = 0">Reset</button>
</div>
```

### DSL syntax breakdown

| PJX syntax           | Compiles to                       | Description                                        |
| -------------------- | --------------------------------- | -------------------------------------------------- |
| `state count = 0`    | Alpine.js `x-data="{ count: 0 }"` | Declares reactive client-side state.               |
| `reactive`           | `x-data="{ count: 0 }"`           | Marks the element as an Alpine.js component.       |
| `on:click="count++"` | `@click="count++"`                | Binds a click event to an Alpine expression.       |
| `x-text="count"`     | `x-text="count"`                  | Alpine directive -- displays the value of `count`. |

The `reactive` attribute on the root `<div>` tells PJX to attach all
declared `state` variables as Alpine.js `x-data`. Without it, the state
declarations have no effect on the client.

You can also declare **props** to accept data from parent components:

```html
---
props {
  label: str = "Count",
  initial: int = 0,
}

state count = props.initial
---

<div class="counter" reactive>
  <strong>{{ props.label }}:</strong>
  <button on:click="count--">-</button>
  <span x-text="count">{{ props.initial }}</span>
  <button on:click="count++">+</button>
</div>
```

Props are validated at render time when `validate_props = true`. Missing
required props or type mismatches raise a `PropValidationError` with a
clear message.

---

## 6. Create a Page

Pages import the layout and components, then compose them together. The
handler's return dict becomes the template context.

Create `app/templates/pages/Home.jinja`:

```html
---
import Layout from "../layouts/Base.jinja"
import Counter from "../components/Counter.jinja"
---

<Layout>
  <div class="page">
    <h1>{{ message }}</h1>
    <p>This counter runs entirely on the client with Alpine.js:</p>
    <Counter />
  </div>
</Layout>
```

### How imports work

**`import Layout from "../layouts/Base.jinja"`** makes the `<Layout>` tag
available in the template body. Paths are relative to the current file.

**`<Layout>...</Layout>`** wraps the page content. Everything between the
tags is passed into the layout's `<Slot />`.

**`<Counter />`** renders the Counter component as a self-closing tag. To
pass props, add them as attributes:

```html
<Counter label="Items" initial="5" />
```

**`{{ message }}`** comes from the handler's return dict. The `@pjx.page()`
handler for `/` returns `{"message": "Hello, PJX!"}`, so `{{ message }}`
resolves to that string.

---

## 7. Run the App

Start the development server:

```bash
pjx dev .
```

This launches Uvicorn with hot reload enabled. Open
[http://localhost:8000](http://localhost:8000) in your browser.

Alternatively, run directly with Uvicorn:

```bash
uvicorn app.main:app --reload
```

You should see:

- The page title "Hello, PJX!" rendered from the handler context.
- A working counter with `-`, `+`, and `Reset` buttons -- all client-side,
  no server round-trips.
- The health endpoint at [http://localhost:8000/health](http://localhost:8000/health)
  returning `{"status": "ok"}`.

### Validate your components

Before deploying, run the static analyzer to check for broken imports,
missing props, and slot mismatches:

```bash
pjx check .
```

---

## 8. What's Happening

When you run `pjx dev .`, the following compilation flow occurs:

```text
.jinja source          PJX compiler              Output
--------------    ----------------------    ----------------
Counter.jinja  -> parse frontmatter       -> state, props
               -> transform attributes    -> reactive -> x-data
                                             on:click -> @click
               -> resolve imports         -> inline or include
               -> emit Jinja2 template    -> Counter.html.j2

Home.jinja     -> parse frontmatter       -> imports
               -> resolve <Layout>        -> wraps with Base.jinja
               -> resolve <Counter />     -> include/inline Counter
               -> emit Jinja2 template    -> Home.html.j2
```

**Step 1 -- Parse frontmatter.** The PJX lexer reads the `---` block and
extracts `import`, `props`, `state`, `slot`, `css`, `js`, and other
declarations.

**Step 2 -- Transform attributes.** PJX-specific attributes are rewritten
to their framework equivalents: `reactive` becomes `x-data`, `on:click`
becomes `@click`, `action:post` becomes `hx-post`, and so on.

**Step 3 -- Resolve imports.** Component tags like `<Counter />` are
resolved to their `.jinja` files. In `include` mode, they become
`{% include "..." %}`. In `inline` mode, the component body is inlined
directly into the parent template.

**Step 4 -- Emit Jinja2.** The final output is a standard Jinja2 template
that the engine (Jinja2, MiniJinja, or HybridEngine) renders with the
context dict from the handler.

The compiled templates are cached using mtime checks -- if the source file
has not changed, the cached result is reused (cold compile ~33ms, cached
~2.7ms).

---

## 9. Next Steps

You now have a working PJX application. Here is where to go from here:

### Learn the DSL

- **[[Component Syntax]]** -- Full reference for frontmatter declarations
  (`props`, `state`, `slot`, `import`, `computed`, `store`), control flow
  tags (`<Show>`, `<For>`, `<Switch>`), and reactive attributes.

### Add more pages

- **[[File Based Routing]]** -- Automatic route generation from the
  filesystem. Supports dynamic parameters (`[slug]`), catch-all routes
  (`[...slug]`), route groups (`(auth)/`), and nested layouts.

### Connect to the server

- **[[HTMX Integration]]** -- Server interactions with `action:get`,
  `action:post`, `target`, `swap`, `into`, and `trigger` attributes.
  Render HTML fragments with `pjx.partial()`.

### Build real features

- **[[Layout Components]]** -- Built-in layout primitives (`<VStack>`,
  `<HStack>`, `<Grid>`, `<Container>`, `<Spacer>`, etc.) for composing
  page layouts without writing CSS.
- **[[Asset Pipeline]]** -- Declare `css` and `js` dependencies in
  frontmatter. PJX collects, deduplicates, and renders them automatically.
- **[[Middleware]]** -- Declare `middleware "auth"` in frontmatter and
  register handlers with `@pjx.middleware("auth")`.

### Prepare for production

- **[[Configuration]]** -- Full `pjx.toml` reference, environment variable
  overrides, engine selection, and performance tuning.
- **[[Security]]** -- CSRF protection, signed sessions, rate limiting,
  CSP headers, and SSE connection limits.

### Explore the example app

The `examples/demo/` directory contains a full working application with a
dashboard, counter demo, todo list, live clock (SSE), search with
debounce, authentication, and more:

```bash
cd examples/demo
pjx dev .
```

---

## Complete File Listing

For reference, here are all the files created in this tutorial:

### pjx.toml

```toml
engine = "hybrid"
debug = true
validate_props = true
render_mode = "include"

template_dirs = ["app/templates"]
static_dir = "app/static"
```

### app/main.py

```python
import os
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from pjx import PJX, PJXConfig, SEO

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("PJX_SECRET_KEY", "change-me-in-production"),
)

pjx = PJX(
    app,
    config=PJXConfig(toml_path=Path(__file__).resolve().parents[1] / "pjx.toml"),
    seo=SEO(title="My App", description="Built with PJX."),
    csrf=True,
    csrf_secret=os.environ.get("PJX_SECRET_KEY", "change-me-in-production"),
    health=True,
)


@pjx.page("/", template="pages/Home.jinja", title="Home -- My App")
async def home():
    return {"message": "Hello, PJX!"}
```

### app/templates/layouts/Base.jinja

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
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{{ seo.title|default(props.title) }}</title>

  <Show when="seo is defined and seo.description">
    <meta name="description" content="{{ seo.description }}" />
  </Show>

  {{ pjx_assets.render_css() }}

  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
  <script src="https://unpkg.com/htmx.org@2/dist/htmx.min.js"></script>
</head>
<body hx-headers='{"X-CSRFToken": "{{ csrf_token() }}"}'>
  <main>
    <Slot />
  </main>

  {{ pjx_assets.render_js() }}
</body>
</html>
```

### app/templates/components/Counter.jinja

```html
---
state count = 0
---

<div class="counter" reactive>
  <button on:click="count--">-</button>
  <span x-text="count">0</span>
  <button on:click="count++">+</button>
  <button on:click="count = 0">Reset</button>
</div>
```

### app/templates/pages/Home.jinja

```html
---
import Layout from "../layouts/Base.jinja"
import Counter from "../components/Counter.jinja"
---

<Layout>
  <div class="page">
    <h1>{{ message }}</h1>
    <p>This counter runs entirely on the client with Alpine.js:</p>
    <Counter />
  </div>
</Layout>
```
