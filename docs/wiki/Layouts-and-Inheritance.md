# Layouts and Inheritance

## Overview

PJX provides two complementary layout mechanisms for wrapping pages in shared
structure (navigation, footers, `<head>` content, etc.):

1. **Runtime layout** -- configured on the `PJX` instance via `layout=...`.
   The framework renders the page first, then injects the result into the
   layout's `{{ body }}` variable. All pages share the same layout unless
   overridden per-route.

2. **Template inheritance** -- declared in a component's frontmatter via
   `extends "layouts/Base.jinja"`. The page's content is injected into the
   layout's named `<Slot:content />`. This is static inheritance resolved at
   compile time.

Both mechanisms can coexist. Runtime layout is typically used for the
application shell (HTML skeleton, nav, footer), while template inheritance is
used for nested, section-specific layouts within the application.

---

## Runtime Layout

The runtime layout is set when creating the `PJX` instance. It automatically
wraps every page rendered through `@pjx.page()`.

### Configuration

```python
from pjx import PJX, PJXConfig, SEO

pjx = PJX(
    app,
    config=PJXConfig(toml_path="pjx.toml"),
    layout="layouts/Base.jinja",
    seo=SEO(title="My App", description="Default description."),
)
```

### Layout template

The layout is a standard `.jinja` file that receives the rendered page as the
`{{ body }}` variable:

```html
---
props {
  title: str = "My App",
}

slot head
slot footer
---

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{{ seo.title }}</title>
    <meta name="description" content="{{ seo.description }}" />
    {% for css in head_css %}
        <link rel="stylesheet" href="{{ css }}" />
    {% endfor %}
    {% for js in head_scripts %}
        <script defer src="{{ js }}"></script>
    {% endfor %}
    <link rel="icon" href="{{ favicon }}" />
</head>
<body>
    <nav>
        <a href="/">Home</a>
        <a href="/about">About</a>
    </nav>

    <main>
        {{ body }}
    </main>

    <footer>
        <p>My App</p>
    </footer>

    {% for js in body_scripts %}
        <script src="{{ js }}"></script>
    {% endfor %}
</body>
</html>
```

---

## The `{{ body }}` Variable

When a request hits a `@pjx.page()` route, PJX performs two rendering passes:

1. **Page render** -- The page template is rendered with the context dict
   returned by the route handler. This produces an HTML fragment.
2. **Layout wrap** -- The layout template is rendered with the page's HTML
   injected as the `{{ body }}` variable, along with additional context.

The layout receives all of the page's context variables plus these
framework-provided variables:

| Variable       | Type     | Description                                 |
| -------------- | -------- | ------------------------------------------- |
| `body`         | `Markup` | The rendered HTML of the page.              |
| `seo`          | `SEO`    | Merged SEO metadata (global + per-page).    |
| `head_css`     | `list`   | Extra CSS `<link>` paths for `<head>`.      |
| `head_scripts` | `list`   | Extra JS `<script>` paths for `<head>`.     |
| `body_scripts` | `list`   | Extra JS `<script>` paths before `</body>`. |
| `favicon`      | `str`    | Favicon file path.                          |

Because `body` is of type `Markup` (from Jinja2), it is not auto-escaped. The
raw HTML is inserted directly into the layout.

---

## Template Inheritance

For more structured control, pages can inherit from a layout using `extends` in
the frontmatter. This is compile-time inheritance: the PJX compiler resolves
the parent layout and injects the page content into its slots.

### Base layout

```html
---
props {
  title: str = "PJX App",
  description: str = "",
}

slot head
slot content
slot footer
---

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{{ props.title }}</title>
    <Show when="props.description">
        <meta name="description" content="{{ props.description }}" />
    </Show>
    <Slot:head />
    <link rel="stylesheet" href="/static/css/app.css" />
    <script defer src="/static/vendor/alpine.min.js"></script>
    <script defer src="/static/vendor/htmx.min.js"></script>
</head>
<body>
    <Slot:content />
    <Slot:footer>
        <footer><p>PJX App</p></footer>
    </Slot:footer>
</body>
</html>
```

The layout defines three slots:

- `<Slot:head />` -- injected into `<head>` (no default content).
- `<Slot:content />` -- the main page body (no default content).
- `<Slot:footer>` -- has default content that pages can override.

### Page that inherits

```html
---
extends "layouts/Base.jinja"

props {
  user: dict,
  items: list[dict],
}
---

<slot:head>
    <meta property="og:title" content="Home -- {{ props.user.name }}" />
    <link rel="canonical" href="/" />
</slot:head>

<h1>Welcome, {{ props.user.name }}</h1>
<For each="props.items" as="item">
    <p>{{ item.title }}</p>
</For>
```

The page body (everything outside `<slot:*>` blocks) is automatically injected
into the layout's `<Slot:content />`. Named `<slot:head>` blocks fill the
corresponding layout slots.

---

## Per-Page Layout Override

When using runtime layouts, individual routes can override or disable the
layout.

### Override with a different layout

```python
@pjx.page("/login", template="pages/Login.jinja", layout="layouts/Minimal.jinja")
async def login() -> dict[str, object]:
    return {}
```

The login page will use `layouts/Minimal.jinja` instead of the default layout
configured on the `PJX` instance.

### Disable layout entirely

```python
@pjx.page("/api-docs", layout=None)
async def api_docs() -> dict[str, object]:
    return {"raw": True}
```

Setting `layout=None` renders the page template directly with no wrapping. This
is useful for standalone pages, API documentation, or pages that define their
own complete HTML structure.

### Override with a different title

The `title` parameter on `@pjx.page()` merges into the SEO context:

```python
@pjx.page("/about", template="pages/About.jinja", title="About Us -- My App")
async def about() -> dict[str, object]:
    return {}
```

---

## File-Based Routing Layouts

When using file-based routing (`pjx.auto_routes()`), layouts are defined by
special `layout.jinja` files placed in the `pages/` directory tree.

### Convention

A `layout.jinja` file in any directory automatically wraps all pages in that
directory and all subdirectories.

```text
pages/
  layout.jinja          <-- root layout, wraps everything
  index.jinja
  about.jinja
  blog/
    layout.jinja        <-- blog layout, wraps blog/* pages
    index.jinja
    [slug].jinja
  (auth)/
    layout.jinja        <-- auth layout, wraps login/register
    login.jinja
    register.jinja
```

### Root layout

`pages/layout.jinja` applies to every page unless a subdirectory provides its
own `layout.jinja`:

```html
---
slot content
---

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>{{ seo.title }}</title>
    <link rel="stylesheet" href="/static/css/app.css" />
    <script defer src="/static/vendor/htmx.min.js"></script>
    <script defer src="/static/vendor/alpine.min.js"></script>
</head>
<body>
    <nav>
        <a href="/">Home</a>
        <a href="/blog">Blog</a>
        <a href="/about">About</a>
    </nav>
    <main>
        <Slot:content />
    </main>
    <footer>Site Footer</footer>
</body>
</html>
```

### Section layout

`pages/blog/layout.jinja` wraps only the blog pages. It is itself wrapped by
the root layout:

```html
---
slot content
slot sidebar
---

<div class="blog-layout">
    <aside>
        <Slot:sidebar>
            <h3>Recent Posts</h3>
        </Slot:sidebar>
    </aside>
    <article>
        <Slot:content />
    </article>
</div>
```

### Route groups

Directories wrapped in parentheses `(name)/` are route groups. They do not add
a URL prefix, but they can have their own `layout.jinja`. In the example above,
`pages/(auth)/login.jinja` maps to `/login` (not `/(auth)/login`), but it uses
the auth layout.

---

## Nested Layouts

Layout files chain automatically. When a request hits a page, PJX applies
layouts from the innermost directory up to the root.

### Resolution order

For `pages/blog/[slug].jinja`, the layout chain is:

1. `pages/blog/layout.jinja` (inner)
2. `pages/layout.jinja` (outer)

The page content is rendered first, then wrapped by `blog/layout.jinja`, and
that result is wrapped by the root `layout.jinja`.

### Example chain

Given this structure:

```text
pages/
  layout.jinja          <-- defines <html>, <head>, <body>, <nav>
  blog/
    layout.jinja        <-- adds sidebar + article wrapper
    [slug].jinja        <-- the actual blog post content
```

The final rendered HTML for `/blog/my-post` would be:

```html
<!DOCTYPE html>
<html lang="en">
<head>...</head>
<body>
    <nav>...</nav>
    <main>
        <!-- from blog/layout.jinja -->
        <div class="blog-layout">
            <aside>
                <h3>Recent Posts</h3>
            </aside>
            <article>
                <!-- from [slug].jinja -->
                <h1>My Post Title</h1>
                <p>Post content here...</p>
            </article>
        </div>
    </main>
    <footer>Site Footer</footer>
</body>
</html>
```

---

## Layout with Slots

Layouts use named slots to allow pages to inject content into specific
regions. This is the same [[Slots]] mechanism used by regular components.

### Layout with multiple injection points

```html
---
slot header
slot content
slot sidebar
slot footer
---

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>{{ seo.title }}</title>
</head>
<body>
    <header>
        <Slot:header>
            <nav><a href="/">Home</a></nav>
        </Slot:header>
    </header>

    <div class="page-grid">
        <main>
            <Slot:content />
        </main>
        <aside>
            <Slot:sidebar>
                <p>Default sidebar content</p>
            </Slot:sidebar>
        </aside>
    </div>

    <footer>
        <Slot:footer>
            <p>Default footer</p>
        </Slot:footer>
    </footer>
</body>
</html>
```

### Page filling the slots

```html
---
extends "layouts/Base.jinja"

props {
  articles: list[dict],
  categories: list[str],
}
---

<slot:header>
    <nav>
        <a href="/">Home</a>
        <a href="/blog">Blog</a>
        <a href="/about">About</a>
    </nav>
</slot:header>

<slot:sidebar>
    <h3>Categories</h3>
    <ul>
        <For each="props.categories" as="cat">
            <li><a href="/blog?category={{ cat }}">{{ cat }}</a></li>
        </For>
    </ul>
</slot:sidebar>

<h1>Blog</h1>
<For each="props.articles" as="article">
    <article>
        <h2>{{ article.title }}</h2>
        <p>{{ article.excerpt }}</p>
    </article>
</For>
```

The page body (the `<h1>` and `<For>` loop, outside any `<slot:*>` block) goes
into `<Slot:content />`. The named `<slot:header>` and `<slot:sidebar>` blocks
fill their corresponding layout slots. The `<Slot:footer>` keeps its default
content since the page does not provide a `<slot:footer>` block.

---

## Layout SEO

SEO metadata flows from the route handler through to the layout via the `seo`
context variable. This is a merged result of the global SEO defaults (set on
the `PJX` instance) and any per-page overrides.

### Global SEO defaults

```python
from pjx import PJX, SEO

pjx = PJX(
    app,
    layout="layouts/Base.jinja",
    seo=SEO(
        title="My App",
        description="A PJX application.",
        og_type="website",
    ),
)
```

### Per-page title override

```python
@pjx.page("/about", template="pages/About.jinja", title="About Us -- My App")
async def about() -> dict[str, object]:
    return {}
```

### Using SEO in the layout

The layout template accesses SEO fields through the `seo` variable:

```html
<head>
    <title>{{ seo.title }}</title>
    <meta name="description" content="{{ seo.description }}" />

    <Show when="seo.og_type">
        <meta property="og:type" content="{{ seo.og_type }}" />
    </Show>
    <Show when="seo.og_image">
        <meta property="og:image" content="{{ seo.og_image }}" />
    </Show>
    <Show when="seo.canonical">
        <link rel="canonical" href="{{ seo.canonical }}" />
    </Show>
</head>
```

### SEO from template inheritance

When using `extends`, pass SEO-relevant props directly:

```html
---
extends "layouts/Base.jinja"
---

<slot:head>
    <title>Blog Post Title -- My App</title>
    <meta name="description" content="A specific blog post." />
    <meta property="og:title" content="Blog Post Title" />
    <meta property="og:description" content="A specific blog post." />
</slot:head>

<h1>Blog Post Title</h1>
<p>Content...</p>
```

---

## Complete Example

A full application with a base layout, a nested blog layout, and a blog post
page.

### Base layout: `layouts/Base.jinja`

```html
---
props {
  title: str = "My App",
}

slot head
slot content
slot footer
---

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{{ seo.title }}</title>
    <meta name="description" content="{{ seo.description }}" />
    <Slot:head />
    <link rel="stylesheet" href="/static/css/app.css" />
    <script defer src="/static/vendor/alpine.min.js"></script>
    <script defer src="/static/vendor/htmx.min.js"></script>
</head>
<body class="min-h-screen flex flex-col">
    <nav class="navbar">
        <a href="/">Home</a>
        <a href="/blog">Blog</a>
        <a href="/about">About</a>
    </nav>

    <main class="flex-1">
        <Slot:content />
    </main>

    <Slot:footer>
        <footer class="py-4 text-center text-sm">
            <p>Built with PJX</p>
        </footer>
    </Slot:footer>
</body>
</html>
```

### Blog layout: `layouts/Blog.jinja`

```html
---
extends "layouts/Base.jinja"

props {
  categories: list[str] = [],
}

slot content
slot sidebar
---

<slot:content>
    <div class="blog-grid">
        <article class="blog-main">
            <Slot:content />
        </article>
        <aside class="blog-sidebar">
            <Slot:sidebar>
                <h3>Categories</h3>
                <ul>
                    <For each="props.categories" as="cat">
                        <li><a href="/blog?cat={{ cat }}">{{ cat }}</a></li>
                    </For>
                </ul>
            </Slot:sidebar>
        </aside>
    </div>
</slot:content>
```

The blog layout itself extends the base layout. It fills the base's
`<Slot:content />` with a two-column grid and defines its own `content` and
`sidebar` slots for blog pages to fill.

### Blog post page: `pages/blog/[slug].jinja`

```html
---
extends "layouts/Blog.jinja"

props {
  post: dict,
  related: list[dict] = [],
}
---

<slot:sidebar>
    <h3>Related Posts</h3>
    <ul>
        <For each="props.related" as="rel">
            <li><a href="/blog/{{ rel.slug }}">{{ rel.title }}</a></li>
        </For>
    </ul>
</slot:sidebar>

<h1>{{ props.post.title }}</h1>
<time>{{ props.post.date }}</time>
<div class="prose">
    {{ props.post.content }}
</div>
```

### Route handler

```python
@pjx.page("/blog/{slug}", template="pages/blog/[slug].jinja", title="Blog")
async def blog_post(slug: str) -> dict[str, object]:
    post = await get_post_by_slug(slug)
    related = await get_related_posts(post.id)
    return {
        "post": post.model_dump(),
        "related": [r.model_dump() for r in related],
        "categories": await get_all_categories(),
    }
```

### Resulting structure

For a request to `/blog/my-post`, the rendering chain is:

1. `pages/blog/[slug].jinja` renders the post content and sidebar.
2. `layouts/Blog.jinja` wraps it in the two-column grid.
3. `layouts/Base.jinja` wraps everything in the HTML skeleton with nav/footer.

The final HTML contains all three layers nested correctly, with each slot
filled by its respective template.

---

## See Also

- [[Component-Syntax]] -- Component structure, frontmatter, and body
- [[Slots]] -- Named and default slots in detail
- [[Project-Structure]] -- Directory conventions and file organization
- [[Quick-Start]] -- Getting started with PJX layouts
