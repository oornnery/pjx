# FastAPI Integration

## Overview

PJX wraps a standard FastAPI application with component rendering, SEO
metadata management, CSRF protection, static file serving, and middleware
integration. Rather than replacing FastAPI, PJX adds a thin layer on top:
templates are compiled from `.jinja` components, rendered through the
configured engine (Jinja2, MiniJinja, or HybridEngine), and returned as
`HTMLResponse` objects.

The core integration class is `PJX`, which accepts a `FastAPI` instance and
provides decorators (`@pjx.page()`, `@pjx.component()`), rendering methods
(`pjx.render()`, `pjx.partial()`), and file-based routing
(`pjx.auto_routes()`).

```python
from fastapi import FastAPI
from pjx import PJX, PJXConfig, SEO

app = FastAPI()
pjx = PJX(
    app,
    config=PJXConfig(toml_path="pjx.toml"),
    layout="layouts/Base.jinja",
    seo=SEO(title="My App", description="Built with PJX."),
    csrf=True,
    csrf_secret="your-secret-key",
    health=True,
)
```

All FastAPI features (dependency injection, middleware, OpenAPI docs, lifespan
events) remain fully available on the `app` instance.

---

## PJX Constructor

The `PJX` class is the main entry point for integrating PJX with FastAPI.

### Parameters

| Parameter           | Type               | Default       | Description                                                     |
| ------------------- | ------------------ | ------------- | --------------------------------------------------------------- |
| `app`               | `FastAPI`          | (required)    | The FastAPI application instance.                               |
| `config`            | `PJXConfig`        | `PJXConfig()` | Configuration loaded from `pjx.toml` or constructed in code.    |
| `layout`            | `str \| None`      | `None`        | Default layout template path for all `@pjx.page()` routes.      |
| `seo`               | `SEO \| None`      | `SEO()`       | Global SEO metadata applied to all pages (overridden per-page). |
| `csrf`              | `bool`             | `False`       | Enable double-submit cookie CSRF middleware.                    |
| `csrf_secret`       | `str \| None`      | `None`        | Secret key for CSRF token signing. Required when `csrf=True`.   |
| `csrf_exempt_paths` | `set[str] \| None` | `None`        | URL paths exempt from CSRF checks (e.g. webhooks, SSE).         |
| `health`            | `bool`             | `False`       | Enable `/health` (liveness) and `/ready` (readiness) endpoints. |

### Complete initialization example

```python
import os
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from pjx import PJX, PJXConfig, SEO

app = FastAPI(title="My PJX App")

# Signed session cookies
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("PJX_SECRET_KEY", "change-me-in-production"),
)

pjx = PJX(
    app,
    config=PJXConfig(toml_path=Path(__file__).parent / "pjx.toml"),
    layout="layouts/Base.jinja",
    seo=SEO(
        title="My App",
        description="A server-rendered application built with PJX.",
        og_type="website",
        twitter_card="summary_large_image",
    ),
    csrf=True,
    csrf_secret=os.environ.get("PJX_SECRET_KEY", "change-me-in-production"),
    csrf_exempt_paths={"/sse/clock", "/api/webhooks"},
    health=True,
)
```

---

## @pjx.page() Decorator

The `page()` decorator registers a route that renders a PJX template. It is
the primary way to define pages in an explicit (non-file-based) application.

### Parameters

| Parameter        | Type                | Default     | Description                                                                                                                       |
| ---------------- | ------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `path`           | `str`               | (required)  | URL path for the route (FastAPI path syntax).                                                                                     |
| `template`       | `str \| None`       | `None`      | Template path relative to `template_dirs`. Auto-discovered from the function name if omitted (e.g. `def about` -> `about.jinja`). |
| `title`          | `str \| None`       | `None`      | Page title -- shortcut for `seo=SEO(title=...)`.                                                                                  |
| `seo`            | `SEO \| None`       | `None`      | Per-page SEO overrides merged on top of the global default.                                                                       |
| `layout`         | `str \| None`       | PJX default | Layout template for this page. Pass `None` to disable layout wrapping. Uses the PJX-level `layout` if not specified.              |
| `methods`        | `list[str] \| None` | `["GET"]`   | HTTP methods for this route. Add `"POST"` for form handling.                                                                      |
| `**route_kwargs` | `Any`               | --          | Additional keyword arguments passed to `app.add_api_route()`.                                                                     |

### GET page

```python
@pjx.page("/about", template="pages/About.jinja", title="About -- My App")
async def about():
    return {"team": await fetch_team_members()}
```

### POST form handler

```python
from typing import Annotated
from pydantic import BaseModel
from pjx import FormData

class ContactForm(BaseModel):
    name: str
    email: str
    message: str

@pjx.page("/contact", template="pages/Contact.jinja", methods=["GET", "POST"])
async def contact(form: Annotated[ContactForm, FormData()]):
    if form.name:  # POST with data
        await send_contact_email(form)
        return {"sent": True, "form": form}
    return {"sent": False, "form": form}
```

### Disabling layout

Pass `layout=None` to render without wrapping:

```python
@pjx.page("/embed/widget", template="components/Widget.jinja", layout=None)
async def widget():
    return {"data": get_widget_data()}
```

When `template` is omitted, PJX uses the function name with a `.jinja`
extension (e.g. `def dashboard` looks for `dashboard.jinja`).

---

## @pjx.component() Decorator

The `component()` decorator registers a route that renders a PJX template
**without** layout wrapping. Use it for HTML partials and fragments returned
to HTMX requests.

```python
@pjx.component("components/TodoItem.jinja")
async def todo_item():
    return {"text": "New item", "done": False}
```

The decorator takes a single argument -- the template path. The handler return
dict becomes the template context. No SEO merging or layout wrapping occurs.

---

## pjx.render()

Compile and render a template manually. Returns `Markup` (safe HTML string)
that can be embedded in other templates or returned directly in an
`HTMLResponse`.

### Signature

```python
def render(
    self,
    template: str,
    context: dict[str, Any],
    layout: str | None = None,
) -> Markup:
```

### Parameters

| Parameter  | Type              | Description                                            |
| ---------- | ----------------- | ------------------------------------------------------ |
| `template` | `str`             | Template path relative to `template_dirs`.             |
| `context`  | `dict[str, Any]`  | Variables available in the template.                   |
| `layout`   | `str \| None`     | Optional layout template. Page is wrapped if provided. |

### Usage in HTMX endpoints

The most common use case is rendering PJX components for HTMX partial
responses:

```python
@app.post("/htmx/todos/add")
async def htmx_add_todo(request: Request) -> HTMLResponse:
    form = await request.form()
    todos_db.append({"text": form["text"], "done": False})
    html = pjx.render("components/TodoList.jinja", {"todos": todos_db})
    return HTMLResponse(html)
```

### With layout wrapping

```python
html = pjx.render(
    "pages/Error.jinja",
    {"status_code": 404, "message": "Page not found"},
    layout="layouts/Base.jinja",
)
```

---

## pjx.partial()

Render a component as an HTML fragment and return `Markup`. This is a
convenience wrapper around `render()` designed for embedding rendered
components inside handler return dicts.

### Signature

```python
def partial(self, template: str, **props: Any) -> Markup:
```

### Usage

```python
@pjx.page("/todos", template="pages/Todos.jinja")
async def todos():
    items = await fetch_todos()
    return {
        "todo_list": pjx.partial("components/TodoList.jinja", todos=items),
    }
```

In the template, the rendered HTML is already marked safe:

```html
<div id="todo-container">
  {{ todo_list }}
</div>
```

Because `partial()` returns `Markup`, Jinja2 will not double-escape the HTML.

---

## pjx.auto_routes()

Discover and register all file-based routes from a pages directory.

```python
pjx.auto_routes()                         # Use config.pages_dir
pjx.auto_routes(pages_dir="src/pages")    # Custom directory
```

This method is covered in detail in [[File Based Routing]]. Briefly, it:

1. Scans the directory for `.jinja` templates and `.py` handlers.
2. Converts filesystem paths to URL patterns (Next.js conventions).
3. Resolves layout chains, loading states, and error boundaries.
4. Registers all routes on the FastAPI app.

---

## Handler Conventions

### Return value

Handlers decorated with `@pjx.page()` return a `dict` that becomes the
template context. All keys are available as variables in the template.

```python
@pjx.page("/dashboard", template="pages/Dashboard.jinja")
async def dashboard():
    return {
        "user": current_user,
        "stats": await get_stats(),
        "notifications": await get_notifications(),
    }
```

### Special context keys

| Key       | Type   | Description                                                   |
| --------- | ------ | ------------------------------------------------------------- |
| `seo`     | `SEO`  | Per-page SEO override. Merged on top of the global default.   |
| `request` | --     | Automatically injected. Do not set manually.                  |
| `props`   | --     | Automatically created as a namespace from the context dict.   |

### Overriding SEO from the handler

```python
@pjx.page("/blog/{slug}", template="pages/blog/Post.jinja")
async def blog_post(request: Request):
    slug = request.path_params["slug"]
    post = await fetch_post(slug)
    return {
        "post": post,
        "seo": SEO(
            title=f"{post.title} -- My Blog",
            description=post.excerpt,
            og_image=post.cover_image,
            canonical=f"https://example.com/blog/{slug}",
        ),
    }
```

### Injecting the Request object

Declare `request: Request` as a parameter to access headers, session, cookies,
path params, and query params:

```python
from fastapi import Request

@pjx.page("/profile", template="pages/Profile.jinja")
async def profile(request: Request):
    user = request.session.get("user")
    return {"user": user}
```

### Sync and async handlers

Both sync and async handlers are supported. PJX inspects the function with
`inspect.iscoroutinefunction()` and awaits async handlers automatically.

```python
# Async handler
@pjx.page("/async-page")
async def async_page():
    data = await fetch_data()
    return {"data": data}

# Sync handler (also works)
@pjx.page("/sync-page")
def sync_page():
    return {"message": "Hello from sync handler"}
```

---

## SEO Dataclass

The `SEO` dataclass defines metadata for `<head>` tags, Open Graph, Twitter
Cards, and robots directives.

### Fields

| Field                 | Type                  | Default                 | Description                               |
| --------------------- | --------------------- | ----------------------- | ----------------------------------------- |
| `title`               | `str`                 | `""`                    | Page `<title>` and `og:title`.            |
| `description`         | `str`                 | `""`                    | Meta description and `og:description`.    |
| `keywords`            | `str`                 | `""`                    | Meta keywords (comma-separated).          |
| `canonical`           | `str`                 | `""`                    | Canonical URL (`<link rel=canonical>`).   |
| `og_title`            | `str`                 | `""`                    | Open Graph title (falls back to `title`). |
| `og_description`      | `str`                 | `""`                    | Open Graph description.                   |
| `og_image`            | `str`                 | `""`                    | Open Graph image URL.                     |
| `og_type`             | `str`                 | `"website"`             | Open Graph type.                          |
| `og_url`              | `str`                 | `""`                    | Open Graph URL.                           |
| `twitter_card`        | `str`                 | `"summary_large_image"` | Twitter card type.                        |
| `twitter_title`       | `str`                 | `""`                    | Twitter card title.                       |
| `twitter_description` | `str`                 | `""`                    | Twitter card description.                 |
| `twitter_image`       | `str`                 | `""`                    | Twitter card image URL.                   |
| `robots`              | `str`                 | `""`                    | Robots meta directive (e.g. `noindex`).   |
| `extra_meta`          | `list[dict[str,str]]` | `[]`                    | Additional `<meta>` tags as dicts.        |

### Global SEO

Set on the `PJX` constructor. Applied to all pages as the base:

```python
pjx = PJX(
    app,
    seo=SEO(
        title="My App",
        description="The default description for all pages.",
        og_type="website",
        twitter_card="summary_large_image",
    ),
)
```

### Per-page SEO

Override via the `@pjx.page()` decorator (`title=` shortcut or `seo=`
parameter), or return an `SEO` instance under the `seo` key in the handler
dict (highest priority):

```python
@pjx.page("/about", title="About Us -- My App")
async def about():
    return {}

@pjx.page("/blog/{slug}")
async def blog_post(request: Request):
    post = await fetch_post(request.path_params["slug"])
    return {
        "post": post,
        "seo": SEO(title=post.title, description=post.excerpt),
    }
```

### Merging behavior

SEO fields merge with a "non-empty wins" strategy:

1. Start with the **global** `SEO` from `PJX(seo=...)`.
2. If the `@pjx.page()` decorator has `title=` or `seo=`, overlay non-empty
   fields.
3. If the handler returns `{"seo": SEO(...)}`, overlay non-empty fields again.

For each field, the most specific non-empty value wins. Empty strings (`""`)
are treated as unset and fall through to the global default.

### Accessing SEO in templates

The merged SEO object is available as `seo` in the template context
(`{{ seo.title }}`, `{{ seo.description }}`, `{{ seo.og_image }}`, etc.).

---

## FormData

`FormData` is a marker class used with `Annotated` to declare that a handler
parameter should be parsed from form data (POST) or query params (GET).

### Basic pattern

```python
from typing import Annotated
from pydantic import BaseModel
from pjx import FormData


class SearchForm(BaseModel):
    query: str = ""
    page: int = 1
    per_page: int = 20
```

### GET handler (query params)

When the request method is GET, `FormData` parses from `request.query_params`:

```python
@pjx.page("/search", template="pages/Search.jinja", methods=["GET"])
async def search(form: Annotated[SearchForm, FormData()]):
    # GET /search?query=python&page=2
    # form.query == "python", form.page == 2
    results = await search_catalog(form.query, form.page, form.per_page)
    return {"results": results, "form": form}
```

### POST handler (form body)

When the request method is POST, `FormData` parses from `await request.form()`:

```python
class LoginForm(BaseModel):
    username: str
    password: str
    remember: bool = False

@pjx.page("/login", template="pages/Login.jinja", methods=["GET", "POST"])
async def login(form: Annotated[LoginForm, FormData()]):
    if form.username:
        user = await authenticate(form.username, form.password)
        if user:
            return {"user": user, "authenticated": True}
        return {"error": "Invalid credentials", "form": form}
    return {"form": form}
```

---

## Static File Serving

PJX automatically mounts a static file directory during construction. If
`config.static_dir` (default: `static/`) exists, it is served at `/static/`.

```python
# Automatic -- happens in PJX.__init__()
# Equivalent to:
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")
```

Reference static files in templates with `/static/css/app.css`,
`/static/js/app.js`, etc. For component-scoped CSS and JS, use the
[[CSS and Assets]] frontmatter declarations instead of manual `<link>` tags.

---

## Request Flow

When a request hits a `@pjx.page()` route, PJX processes it through these
steps:

### Step-by-step

1. **Middleware execution** -- If the template's frontmatter declares
   `middleware "auth", "rate_limit"`, PJX calls each registered middleware
   function in declaration order before the handler runs.

2. **Handler invocation** -- The decorated function is called. PJX inspects
   the function signature:
   - `request: Request` parameters receive the Starlette request object.
   - `Annotated[Model, FormData()]` parameters are parsed from form data
     (POST) or query params (GET).
   - Both sync and async handlers are supported.

3. **Context construction** -- The handler's return dict becomes the template
   context. `request` is added automatically.

4. **SEO merging** -- The global SEO defaults are merged with decorator-level
   SEO and handler-returned `seo` key. Non-empty fields from more specific
   sources override less specific ones.

5. **Template compilation** -- The template and all its imports are compiled
   (or served from mtime cache). The compiled Jinja source is registered in
   the engine. Diamond dependencies are deduplicated.

6. **Props validation** -- If `config.validate_props` is enabled, the context
   is validated against the template's props declaration using a cached
   Pydantic model.

7. **Engine rendering** -- HybridEngine selects the optimal path:
   - Leaf partials (no layout, no includes) use MiniJinja's `render_string`.
   - Templates with includes use Jinja2's pre-registered `render`.
   - Inline mode (`render_mode="inline"`) flattens all includes and uses
     `render_string`.

8. **CSS injection** -- Scoped CSS from compiled components is prepended as
   an inline `<style>` tag.

9. **Layout wrapping** -- If a layout is configured, the rendered page body is
   injected into the layout as `{{ body }}`. The layout is rendered with the
   full context (SEO, assets, CSRF token helper, etc.).

10. **HTMLResponse** -- The final HTML string is returned as a Starlette
    `HTMLResponse`.

---

## See Also

- [[File Based Routing]] -- `pjx.auto_routes()`, dynamic params, colocated handlers
- [[Middleware]] -- Application-level and component-level middleware
- [[Configuration Reference]] -- `pjx.toml` fields, environment variables, `PJXConfig`
