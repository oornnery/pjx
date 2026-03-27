# PJX -- Reactive Components for Python

PJX is a Python DSL for building reactive server-rendered components in `.jinja`
files. Write props, state, slots, and control flow in a declarative syntax --
PJX compiles it to Jinja2 + HTMX + Alpine.js, served by FastAPI.

---

## Features

- **Declarative component syntax** -- props, slots, state, and imports in a
  frontmatter block, HTML body below. See [[Component Syntax]].
- **Reactive state** -- `state` declarations compile to Alpine.js `x-data`,
  with `on:click`, `bind:model`, and other shorthand attributes.
  See [[State and Reactivity]].
- **HTMX integration** -- `action:get`, `action:post`, `target`, `swap`, and
  the `into=` shorthand map directly to HTMX attributes.
  See [[HTMX Integration]].
- **File-based routing** -- `pjx.auto_routes()` scans `pages/` and generates
  FastAPI routes from the filesystem, including dynamic `[slug]` and catch-all
  `[...slug]` parameters. See [[File-Based Routing]].
- **Built-in layout components** -- `<Center>`, `<HStack>`, `<VStack>`,
  `<Grid>`, `<Container>`, and more, inspired by Chakra UI.
  See [[Layout Components]].
- **Compile-time static analysis** -- `pjx check` validates imports, props,
  and slots without running the server. See [[Static Analysis]].
- **Dual template engine** -- HybridEngine selects Jinja2 or MiniJinja per
  template for optimal performance (up to 74x faster ad-hoc compilation).
  See [[Compilation Reference]].
- **Production-ready security** -- CSRF protection, signed sessions, rate
  limiting, SSE connection limits, and health checks built in.
  See [[Security]].

---

## Quick Example

A minimal counter component (`Counter.jinja`):

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

PJX compiles this to standard Jinja2 + Alpine.js:

```html
<div class="counter" x-data="{ count: 0 }">
  <button @click="count--">-</button>
  <span x-text="count">0</span>
  <button @click="count++">+</button>
</div>
```

Use it in a page:

```html
---
import Layout from "../layouts/Base.jinja"
import Counter from "../components/Counter.jinja"
---

<Layout>
  <h1>My App</h1>
  <Counter />
</Layout>
```

---

## Get Started

1. **[[Installation]]** -- Install PJX with `uv add pjx` and set up your
   project.
2. **[[Quick Start]]** -- Build your first PJX application in five minutes.

---

## Navigation by Role

**Building your first app?**
Start with [[Quick Start]] to scaffold a project, create components, and run
the dev server.

**Coming from React, Vue, or Svelte?**
PJX borrows familiar ideas -- components, props, slots, reactive state -- but
compiles to server-rendered templates instead of a client-side virtual DOM.
Read [[Component Syntax]] for the frontmatter DSL, and [[Compilation Reference]]
to understand what PJX generates.

**Already using Jinja2 + HTMX?**
PJX adds structure on top of what you already know. See [[HTMX Integration]]
for how PJX shorthand attributes map to standard `hx-*` attributes, and
[[State and Reactivity]] for the Alpine.js state layer.

**Ready for production?**
Review [[Security]] for CSRF, sessions, rate limiting, and SSE hardening.
Then see [[Deployment]] for configuration, environment variables, and
performance tuning.

---

## Stack

| Layer              | Technology                                |
| ------------------ | ----------------------------------------- |
| Language           | Python 3.14+                              |
| Template engine    | HybridEngine (default), Jinja2, MiniJinja |
| Server framework   | FastAPI + Uvicorn                         |
| Reactivity         | Alpine.js (client-side)                   |
| Server interaction | HTMX                                      |
| Validation         | Pydantic                                  |
| CLI                | Typer + Rich                              |

---

## Project Structure

```text
my-app/
  templates/
    pages/           # File-based routes
    components/      # Reusable components
    layouts/         # Base layouts with <Slot />
  static/
    css/
    js/
  app.py             # FastAPI application
  pjx.toml           # Configuration
```

---

## CLI

```bash
pjx init <dir>       # Scaffold a new project
pjx dev <dir>        # Dev server with hot reload
pjx build            # Compile templates + bundle CSS
pjx check            # Validate imports, props, and slots
pjx format           # Re-format .jinja files
```

---

## Links

- [GitHub Repository](https://github.com/oornnery/pjx)
- [PyPI Package](https://pypi.org/project/pjx/)
- [Report an Issue](https://github.com/oornnery/pjx/issues)
