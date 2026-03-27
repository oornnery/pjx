# File-Based Routing

## Overview

PJX supports automatic file-based routing inspired by Next.js and SvelteKit.
Instead of manually registering every route with `@pjx.page()`, you organize
`.jinja` templates inside a `pages/` directory and PJX derives the URL
structure from the filesystem. Dynamic parameters, catch-all segments, route
groups, nested layouts, and colocated Python handlers are all supported.

Call `pjx.auto_routes()` once after constructing the `PJX` instance, and the
router walks the pages directory, builds a sorted route table, and registers
every discovered route on the underlying FastAPI application.

```text
pages/
  index.jinja           ->  /
  about.jinja           ->  /about
  blog/
    index.jinja         ->  /blog
    [slug].jinja        ->  /blog/{slug}
    [slug].py           ->  colocated handler
  docs/
    [...slug].jinja     ->  /docs/{slug:path}
  (auth)/
    login.jinja         ->  /login
    register.jinja      ->  /register
```

Every `.jinja` file becomes a page. Every `.py` file in `pages/api/` becomes a
JSON API route. Python files next to templates (same stem, different extension)
become colocated handlers that supply template context.

---

## Enabling Auto-Routes

### Default pages directory

If `pages_dir` is configured in `pjx.toml` (or defaults to `templates/pages`),
a single call is all you need:

```python
from fastapi import FastAPI
from pjx import PJX, PJXConfig

app = FastAPI()
pjx = PJX(app, config=PJXConfig(toml_path="pjx.toml"))

# Scan pages/ and register all routes
pjx.auto_routes()
```

### Custom pages directory

Pass a path to scan a different directory:

```python
pjx.auto_routes(pages_dir="src/views")
```

The argument accepts a `str` or `pathlib.Path`. When omitted, PJX uses
`config.pages_dir`.

### Mixing auto-routes with explicit routes

`auto_routes()` and `@pjx.page()` can coexist. Explicit routes registered
before `auto_routes()` take priority -- the file router will not overwrite
them.

```python
# Explicit route registered first
@pjx.page("/", template="pages/Home.jinja", title="Home")
async def home():
    return {"featured": await get_featured()}

# File-based routes fill in the rest
pjx.auto_routes()
```

---

## File Conventions

The table below summarizes how filesystem paths map to URL patterns.

| File path                     | URL pattern         | Description                  |
| ----------------------------- | ------------------- | ---------------------------- |
| `pages/index.jinja`           | `/`                 | Root page                    |
| `pages/about.jinja`           | `/about`            | Static route                 |
| `pages/blog/index.jinja`      | `/blog`             | Directory index              |
| `pages/blog/[slug].jinja`     | `/blog/{slug}`      | Dynamic parameter            |
| `pages/docs/[...slug].jinja`  | `/docs/{slug:path}` | Catch-all route              |
| `pages/(auth)/login.jinja`    | `/login`            | Route group, prefix stripped |
| `pages/(auth)/register.jinja` | `/register`         | Route group, prefix stripped |
| `pages/api/users.py`          | `/api/users`        | API route (JSON)             |

### Naming rules

- **`index.jinja`** in any directory becomes the index route for that segment
  (the filename is stripped, leaving only the directory path).
- **Files starting with `_`** (e.g. `_helpers.jinja`, `_draft.jinja`) are
  ignored by the scanner. Use this for partials, utilities, or work in
  progress.
- **Special files** (`layout.jinja`, `loading.jinja`, `error.jinja`) are never
  registered as routes. They serve structural roles described in
  [[#Special Files]].

---

## Dynamic Parameters

Wrap a path segment in square brackets to create a dynamic URL parameter:

```text
pages/blog/[slug].jinja    ->  /blog/{slug}
pages/users/[id].jinja     ->  /users/{id}
```

PJX converts `[slug]` to the FastAPI path parameter `{slug}`. The value is
passed to the handler (or directly to the template context) as a keyword
argument.

### Accessing the parameter in a colocated handler

```python
# pages/blog/[slug].py
from pjx import RouteHandler

handler = RouteHandler()

@handler.get
async def get(request, slug: str):
    post = await fetch_post(slug)
    return {"post": post, "slug": slug}
```

### Accessing the parameter in the template

When no colocated handler exists, the path parameter is injected directly into
the template context:

```html
---
props {
  slug: str,
}
---

<h1>Post: {{ slug }}</h1>
```

### Multiple dynamic segments

Nest directories to create multi-segment dynamic routes:

```text
pages/users/[user_id]/posts/[post_id].jinja
->  /users/{user_id}/posts/{post_id}
```

Both `user_id` and `post_id` are available as separate parameters.

---

## Catch-All Routes

Prefix the parameter name with `...` inside brackets to capture multiple path
segments:

```text
pages/docs/[...slug].jinja    ->  /docs/{slug:path}
```

PJX converts `[...slug]` to FastAPI's `{slug:path}` converter, which matches
one or more path segments separated by `/`.

### Examples

| Request path           | `slug` value        |
| ---------------------- | ------------------- |
| `/docs/getting-started`| `getting-started`   |
| `/docs/api/reference`  | `api/reference`     |
| `/docs/a/b/c/d`        | `a/b/c/d`           |

### Accessing the catch-all in a handler

```python
# pages/docs/[...slug].py
from pjx import RouteHandler

handler = RouteHandler()

@handler.get
async def get(request, slug: str):
    # slug = "api/reference" for /docs/api/reference
    segments = slug.split("/")
    doc = await load_doc(segments)
    return {"doc": doc, "breadcrumbs": segments}
```

### Template access

```html
---
props {
  slug: str,
}
---

<nav class="breadcrumbs">
  <For each="slug.split('/')" as="segment">
    <span>{{ segment }}</span>
  </For>
</nav>
```

### Sorting behavior

Catch-all routes are always registered **last** in their directory. Static and
single-dynamic routes take priority, so `/docs/changelog` matches a
`pages/docs/changelog.jinja` file before falling through to
`pages/docs/[...slug].jinja`.

---

## Route Groups

Directories wrapped in parentheses create **route groups**. The group name is
stripped from the URL, keeping it purely organizational:

```text
pages/(auth)/login.jinja       ->  /login
pages/(auth)/register.jinja    ->  /register
pages/(dashboard)/stats.jinja  ->  /stats
```

### Use cases

- **Organizing by feature**: group related pages without adding a URL prefix.
- **Shared layouts**: place a `layout.jinja` inside the group directory to wrap
  only that group's pages.
- **Shared middleware**: colocate middleware configuration that applies to the
  group.

### Nesting

Groups can be nested, and all group prefixes are stripped:

```text
pages/(admin)/(settings)/profile.jinja  ->  /profile
```

---

## Special Files

Three filenames have special meaning inside the pages directory. They are
**never** registered as routes.

### `layout.jinja` -- Layout wrapper

A `layout.jinja` file wraps all pages in its directory and all subdirectories.
The rendered page content is injected as `{{ body }}`.

```html
<!-- pages/layout.jinja -->
---
import Navbar from "../components/Navbar.jinja"
slot default
---

<!DOCTYPE html>
<html lang="en">
<head><title>{{ seo.title }}</title></head>
<body>
  <Navbar />
  <main>{{ body }}</main>
</body>
</html>
```

The file router discovers layouts by walking from the page's directory up to
the pages root, collecting every `layout.jinja` it encounters. See
[[#Nested Layouts]] for chaining behavior.

### `loading.jinja` -- Loading state

A `loading.jinja` template provides a skeleton or loading indicator shown
during HTMX transitions. PJX resolves the nearest `loading.jinja` by walking
up from the page's directory.

```html
<!-- pages/blog/loading.jinja -->
<div class="loading-skeleton">
  <div class="skeleton-title"></div>
  <div class="skeleton-line"></div>
  <div class="skeleton-line"></div>
  <div class="skeleton-line short"></div>
</div>
```

The loading template is stored on the `RouteEntry` and can be referenced in
HTMX attributes for `hx-indicator` patterns.

### `error.jinja` -- Error boundary

An `error.jinja` template is rendered when a handler raises an error or returns
an error status. It receives `status_code` and `message` in the template
context.

```html
<!-- pages/error.jinja -->
<div class="error-page">
  <h1>{{ status_code }}</h1>
  <p>{{ message }}</p>
  <a href="/">Go home</a>
</div>
```

Like `loading.jinja`, PJX resolves the nearest `error.jinja` by walking up the
directory tree. You can place one at the root level for a global error page, and
override it in specific directories.

For both `loading.jinja` and `error.jinja`, the scanner walks from the page's
parent directory upward to the pages root. The first match wins. If no file is
found, the field is `None`.

---

## Nested Layouts

Layout files chain from the pages root down to the page's own directory.
The file router collects every `layout.jinja` encountered while walking
**upward** from the page, then reverses the list so the root layout comes
first and the innermost layout comes last.

### Example

```text
pages/
  layout.jinja              # Root layout (HTML shell)
  blog/
    layout.jinja            # Blog layout (sidebar + content area)
    [slug].jinja            # Blog post page
```

When rendering `pages/blog/[slug].jinja`, the layout chain is:

1. `pages/layout.jinja` (root -- outermost)
2. `pages/blog/layout.jinja` (innermost)

The innermost layout in the chain is used as the active layout for the page
route. It receives the rendered page as `{{ body }}`, and it can itself be
wrapped by importing the parent layout:

```html
<!-- pages/blog/layout.jinja -->
---
import RootLayout from "../layout.jinja"
---

<RootLayout>
  <div class="blog-layout">
    <aside class="sidebar">...</aside>
    <main>{{ body }}</main>
  </div>
</RootLayout>
```

The chain can be arbitrarily deep. Each layout wraps the next by importing its
parent and placing `{{ body }}` inside a `<Slot />`. A `layout.jinja` inside a
route group applies only to that group's pages.

---

## Colocated Handlers

Place a `.py` file next to a `.jinja` template (same stem) to define server
logic for that page. The file router loads the handler automatically.

### Page handlers with `RouteHandler`

`RouteHandler` maps HTTP verbs to functions whose return dicts become template
context.

```python
# pages/blog/[slug].py
from typing import Annotated

from pydantic import BaseModel

from pjx import FormData, RouteHandler

handler = RouteHandler()


class CommentForm(BaseModel):
    author: str
    body: str


@handler.get
async def get(request, slug: str):
    """Load the blog post and its comments."""
    post = await fetch_post(slug)
    comments = await fetch_comments(slug)
    return {"post": post, "comments": comments}


@handler.post
async def post(request, slug: str, form: Annotated[CommentForm, FormData()]):
    """Add a new comment and reload."""
    await add_comment(slug, form.author, form.body)
    post = await fetch_post(slug)
    comments = await fetch_comments(slug)
    return {"post": post, "comments": comments}
```

The module **must** export a variable named `handler`. The router inspects
`handler.methods` to determine which HTTP methods to register. Each decorated
method (`.get`, `.post`, `.put`, `.patch`, `.delete`) adds itself to the
methods list automatically.

### API routes with `APIRoute`

For JSON endpoints, use `APIRoute` in files under `pages/api/`. The module
must export a variable named `route`.

```python
# pages/api/users.py
from pjx import APIRoute

route = APIRoute()


@route.get
async def get(request):
    """List all users."""
    users = await fetch_users()
    return {"users": users}


@route.post
async def post(request):
    """Create a new user."""
    data = await request.json()
    user = await create_user(data)
    return {"user": user, "created": True}


@route.delete
async def delete(request):
    """Delete a user by ID (query param)."""
    user_id = request.query_params["id"]
    await remove_user(user_id)
    return {"deleted": user_id}
```

API routes return `JSONResponse` automatically. No template is rendered.

### Handler resolution

The file router resolves handlers in this order:

1. Look for a `.py` file with the same stem as the `.jinja` file.
2. Load the module and look for a `handler` attribute (`RouteHandler`).
3. Inspect `handler._handlers` for registered verb functions.
4. If no `RouteHandler` is found, check if `handler` is a bare callable.

For API routes, the router looks for a `route` attribute (`APIRoute`) instead.

---

## Explicit vs File-Based

The `@pjx.page()` decorator and `pjx.auto_routes()` serve the same purpose --
registering URL routes that render templates -- but they suit different
situations.

### When to use file-based routing

- **Content-heavy applications** with many pages that follow a regular URL
  structure (blogs, docs, dashboards).
- **Convention-over-configuration** preference -- the filesystem *is* the route
  table.
- **Teams** that want new pages to be discoverable by looking at the directory
  tree.
- **Dynamic/catch-all routes** where the URL structure mirrors a content
  hierarchy.

### When to use `@pjx.page()`

- **Complex handler logic** that benefits from being inline with the route
  registration (dependency injection, multiple models, complex validation).
- **Routes with non-standard patterns** that don't map cleanly to a filesystem
  hierarchy.
- **Programmatic route generation** (e.g., registering routes in a loop from a
  database).
- **Gradual adoption** -- start with explicit routes and migrate to file-based
  as the application grows.

Both approaches coexist. Explicit routes registered before `auto_routes()`
take priority. The file router logs every registered route at the `INFO` level.

---

## See Also

- [[Layouts and Inheritance]] -- Runtime layout and template inheritance
- [[FastAPI Integration]] -- `@pjx.page()`, `pjx.render()`, SEO, and FormData
- [[Project Structure]] -- Recommended directory layout for PJX applications
