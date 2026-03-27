# Project Structure

PJX projects follow a convention-over-configuration layout. Every directory
has a clear role, and all paths are configurable via `pjx.toml`. This page
covers the default structure, what goes where, naming conventions, and how
to customize paths for your project.

---

## Default Structure

Running `pjx init my-app` generates the following layout:

```text
my-app/
├── pjx.toml                    # Configuration (project root)
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI + PJX entrypoint
│   ├── core/
│   │   └── config.py           # Settings (SECRET_KEY, HOST, PORT)
│   ├── pages/                  # Page route handlers
│   ├── api/v1/                 # JSON API endpoints
│   ├── models/                 # Pydantic schemas
│   ├── services/               # Business logic
│   ├── middleware/              # Custom middleware
│   ├── templates/
│   │   ├── pages/
│   │   │   └── index.jinja
│   │   ├── components/
│   │   │   └── Counter.jinja
│   │   ├── layouts/
│   │   │   └── Base.jinja
│   │   └── ui/
│   │       ├── Center.jinja
│   │       ├── HStack.jinja
│   │       ├── VStack.jinja
│   │       ├── Grid.jinja
│   │       ├── Spacer.jinja
│   │       ├── Container.jinja
│   │       ├── Divider.jinja
│   │       ├── Wrap.jinja
│   │       ├── AspectRatio.jinja
│   │       └── Hide.jinja
│   └── static/
│       ├── css/
│       ├── js/
│       └── images/
```

---

## Directory Roles

### `app/main.py`

The application entry point. Creates the FastAPI app, initializes the `PJX`
runtime, wires middleware, and includes routers. This is where `PJXConfig`
is constructed and `pjx.auto_routes()` is optionally called.

### `app/core/config.py`

Application settings (SECRET_KEY, HOST, PORT, etc.) using Pydantic Settings
or plain constants. Keeps secrets and deployment config separate from PJX
template config.

### `pjx.toml`

Project configuration file at the project root. Controls the template engine,
directory paths, debug mode, CORS, logging, and more. All relative paths in
`pjx.toml` are resolved relative to the directory containing the TOML file
itself. See [[Configuration Reference]] for the full field list.

### `app/pages/`

Page route handlers as Python modules with `APIRouter`. Keep HTTP logic
(form parsing, redirects, HTMX partials) here, separate from templates.

### `app/api/v1/`

JSON API endpoints. Organized by version for forward compatibility.

### `app/models/`

Pydantic schemas for request/response validation and data transfer objects.

### `app/services/`

Business logic and data access. Pure functions and classes that don't depend
on FastAPI or HTTP concepts. Called by page handlers and API endpoints.

### `app/middleware/`

Custom middleware (security headers, auth guards, exception handlers).

### `app/templates/pages/`

Page templates that map to URL routes. When using [[File Based Routing]] via
`pjx.auto_routes()`, each file in this directory becomes a route:

| File                           | Route               |
| ------------------------------ | ------------------- |
| `pages/index.jinja`            | `/`                 |
| `pages/about.jinja`            | `/about`            |
| `pages/blog/[slug].jinja`      | `/blog/{slug}`      |
| `pages/docs/[...slug].jinja`   | `/docs/{slug:path}` |
| `pages/(auth)/login.jinja`     | `/login`            |

Pages typically import a layout and wrap their content inside it. They receive
context variables from their corresponding route handler.

### `app/templates/components/`

Reusable components shared across pages. Components declare props, state, and
slots in their frontmatter. They are imported by pages and other components
using relative paths:

```html
---
import Counter from "../components/Counter.jinja"
---
```

### `app/templates/layouts/`

Layout templates that provide the HTML shell (doctype, head, body) and use
`<Slot />` to inject page content. Layouts can import components and declare
their own props:

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
</head>
<body>
  <Navbar />
  <main><Slot /></main>
</body>
</html>
```

When using file-based routing, a `layout.jinja` file wraps all pages and
subdirectories at the same level. Layouts nest automatically.

### `app/templates/ui/`

Built-in layout components provided by PJX. These are available without an
explicit import and include `<Center>`, `<HStack>`, `<VStack>`, `<Grid>`,
`<Spacer>`, `<Container>`, `<Divider>`, `<Wrap>`, `<AspectRatio>`, and
`<Hide>`. See [[Layout Components]] for the full API.

### `app/static/`

Static assets served by FastAPI at the `/static/` URL prefix. Organize files
into subdirectories by type:

| Subdirectory    | Contents                       |
| --------------- | ------------------------------ |
| `static/css/`   | Stylesheets (global and scoped)|
| `static/js/`    | JavaScript files               |
| `static/images/`| Images, icons, favicons        |

Components can declare CSS and JS dependencies in their frontmatter. PJX
collects and deduplicates these at render time. See [[CSS and Assets]] for
details.

### `app/static/vendor/`

JavaScript and CSS packages installed via `pjx add <pkg>`. This directory is
managed by the PJX CLI and should not be edited by hand. Vendor templates
live in `app/templates/vendor/` while vendor static assets go to
`app/static/vendor/`.

---

## Configuring Paths

All directory paths are configurable in `pjx.toml`. The scaffold sets them
to match the `app/` subpackage structure:

```toml
template_dirs = ["app/templates"]
static_dir = "app/static"
```

PJXConfig exposes the following path fields:

| Field                  | Scaffold default           | Description                              |
| ---------------------- | -------------------------- | ---------------------------------------- |
| `template_dirs`        | `["app/templates"]`        | Directories to search for templates      |
| `static_dir`           | `app/static`               | Static asset directory                   |
| `pages_dir`            | `app/templates/pages`      | Page templates (file-based routing)      |
| `components_dir`       | `app/templates/components` | Reusable component templates             |
| `layouts_dir`          | `app/templates/layouts`    | Layout templates                         |
| `ui_dir`               | `app/templates/ui`         | Built-in layout components               |
| `vendor_templates_dir` | `app/templates/vendor`     | Vendor template packages                 |
| `vendor_static_dir`    | `app/static/vendor`        | Vendor static assets                     |

### Path Resolution

All relative paths in `pjx.toml` are resolved against the **parent directory
of the TOML file**. For example, if `pjx.toml` lives at
`/home/user/my-app/pjx.toml`, then `static_dir = "static"` resolves to
`/home/user/my-app/static`.

Absolute paths are used as-is, without any resolution.

### Custom Layout Example

To use a flat layout without the `app/` subpackage:

```toml
template_dirs = ["templates"]
pages_dir = "templates/pages"
components_dir = "templates/components"
layouts_dir = "templates/layouts"
ui_dir = "templates/ui"
static_dir = "public"
```

### Environment Variable Overrides

Any config field can be overridden with a `PJX_`-prefixed environment
variable:

```bash
export PJX_STATIC_DIR="/var/www/static"
export PJX_PAGES_DIR="src/views"
```

Environment variables take precedence over TOML values. See
[[Configuration Reference]] for the full precedence order.

---

## Naming Conventions

### Components

Use **PascalCase** for component file names. The file name is the tag name
used in templates:

```text
templates/components/
├── Counter.jinja
├── UserCard.jinja
├── Navbar.jinja
└── TodoList.jinja
```

These are referenced in templates as `<Counter />`, `<UserCard />`, etc.

### Pages

Use **kebab-case** or **lowercase** for page file names. The file name
determines the URL route in file-based routing:

```text
templates/pages/
├── index.jinja          ->  /
├── about.jinja          ->  /about
├── blog-post.jinja      ->  /blog-post
└── blog/
    ├── index.jinja      ->  /blog
    └── [slug].jinja     ->  /blog/{slug}
```

### Special Files

These file names have special meaning within the `pages/` directory when
using file-based routing:

| File            | Purpose                                                      |
| --------------- | ------------------------------------------------------------ |
| `layout.jinja`  | Wraps all pages at the same level and below. Layouts nest.   |
| `loading.jinja` | Loading skeleton shown via HTMX `hx-indicator`.              |
| `error.jinja`   | Error page. Receives `status_code` and `message` in context. |

Special files apply to their directory and all subdirectories. A nested
`layout.jinja` wraps inside the parent layout, building a layout chain.

---

## Minimal Project

The absolute minimum PJX project requires these files:

```text
my-app/
├── pjx.toml
└── app/
    ├── __init__.py
    ├── main.py
    └── templates/
        └── pages/
            └── index.jinja
```

**`pjx.toml`** -- minimal configuration:

```toml
engine = "hybrid"
debug = true
template_dirs = ["app/templates"]
static_dir = "app/static"
```

**`app/main.py`** -- bare-bones application:

```python
from pathlib import Path

from fastapi import FastAPI

from pjx import PJX, PJXConfig

app = FastAPI()
pjx = PJX(
    app,
    config=PJXConfig(toml_path=Path(__file__).resolve().parents[1] / "pjx.toml"),
)


@pjx.page("/", template="pages/index.jinja")
async def home():
    return {"message": "Hello, PJX!"}
```

**`app/templates/pages/index.jinja`** -- a single page:

```html
<!DOCTYPE html>
<html>
<body>
  <h1>{{ message }}</h1>
</body>
</html>
```

Run with `pjx dev .` and visit `http://127.0.0.1:8000`.

---

## Full Project

A production-ready project with all directories populated:

```text
my-app/
├── pjx.toml
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   └── config.py
│   ├── pages/
│   │   └── __init__.py
│   ├── api/
│   │   └── v1/
│   │       └── __init__.py
│   ├── models/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   ├── middleware/
│   │   └── __init__.py
│   ├── templates/
│   │   ├── pages/
│   │   │   ├── layout.jinja
│   │   │   ├── error.jinja
│   │   │   ├── loading.jinja
│   │   │   ├── index.jinja
│   │   │   ├── about.jinja
│   │   │   ├── (auth)/
│   │   │   │   ├── login.jinja
│   │   │   │   └── register.jinja
│   │   │   └── blog/
│   │   │       ├── layout.jinja
│   │   │       ├── index.jinja
│   │   │       └── [slug].jinja
│   │   ├── components/
│   │   │   ├── Counter.jinja
│   │   │   ├── Navbar.jinja
│   │   │   ├── Footer.jinja
│   │   │   ├── UserCard.jinja
│   │   │   ├── TodoList.jinja
│   │   │   └── SearchBar.jinja
│   │   ├── layouts/
│   │   │   ├── Base.jinja
│   │   │   ├── Dashboard.jinja
│   │   │   └── Auth.jinja
│   │   ├── ui/
│   │   │   ├── Center.jinja
│   │   │   ├── HStack.jinja
│   │   │   ├── VStack.jinja
│   │   │   ├── Grid.jinja
│   │   │   ├── Spacer.jinja
│   │   │   ├── Container.jinja
│   │   │   ├── Divider.jinja
│   │   │   ├── Wrap.jinja
│   │   │   ├── AspectRatio.jinja
│   │   │   └── Hide.jinja
│   │   └── vendor/
│   │       └── (managed by pjx add)
│   └── static/
│       ├── css/
│       │   ├── global.css
│       │   └── components/
│       │       └── card.css
│       ├── js/
│       │   └── app.js
│       ├── images/
│       │   ├── logo.svg
│       │   └── favicon.ico
│       └── vendor/
│           └── (managed by pjx add)
```

### Key additions over the minimal project

- **`layout.jinja`** in `pages/` and `pages/blog/` for nested layouts
- **`error.jinja`** and **`loading.jinja`** for error handling and loading states
- **Route groups** like `(auth)/` that organize files without affecting URLs
- **Multiple layouts** in `layouts/` for different sections of the site
- **Component library** in `components/` with reusable UI pieces
- **Scoped CSS** in `static/css/components/` declared via frontmatter `css` keyword
- **Vendor directories** managed by `pjx add` for third-party packages

---

## The `pjx.toml` File

### Location

`pjx.toml` is the project root marker. Place it in the top-level directory
of your project (alongside the `app/` package). The PJX CLI and dev server
expect to find it in the working directory, and `PJXConfig` defaults to
looking for `pjx.toml` in the current directory.

To use a custom path, pass it explicitly:

```python
config = PJXConfig(toml_path=Path(__file__).parent / "pjx.toml")
```

### How Paths Resolve

All relative paths in `pjx.toml` resolve against the **directory containing
the TOML file**. This means you can place `pjx.toml` anywhere and paths
will still work correctly:

```text
/home/user/my-app/
├── pjx.toml               <-- root anchor
└── app/
    ├── templates/          <-- template_dirs = ["app/templates"] resolves here
    └── static/             <-- static_dir = "app/static" resolves here
```

If `pjx.toml` were at `/home/user/my-app/config/pjx.toml`, then
`template_dirs = ["templates"]` would resolve to
`/home/user/my-app/config/templates/`. Keep this in mind if you move the
config file out of the project root.

### Settings Precedence

PJXConfig loads values from multiple sources, with earlier sources winning:

1. **Constructor keyword arguments** -- passed directly to `PJXConfig()`
2. **Environment variables** -- `PJX_`-prefixed (e.g., `PJX_DEBUG=false`)
3. **TOML file** -- values from `pjx.toml`
4. **Field defaults** -- hardcoded in the `PJXConfig` class

### Reference Configuration

A fully annotated `pjx.toml` with all defaults shown:

```toml
engine = "hybrid"            # "hybrid", "jinja2", "minijinja", "auto"
debug = false                # Enable debug mode
validate_props = true        # Runtime prop validation via Pydantic
render_mode = "include"      # "include" or "inline"

# Directory paths (relative to this file)
template_dirs = ["app/templates"]
static_dir = "app/static"

# Logging
log_json = false             # JSON output for log aggregation
log_level = "INFO"           # DEBUG, INFO, WARNING, ERROR

# CORS (uncomment to enable)
# cors_origins = ["https://example.com"]
# cors_methods = ["GET", "POST"]
# cors_headers = []
# cors_credentials = false
```

---

## See Also

- [[Configuration Reference]] -- Full list of `pjx.toml` fields and environment variables
- [[File Based Routing]] -- How page files map to URL routes
- [[Quick Start]] -- Step-by-step guide to creating your first PJX project
