# PJX — Technical Specification

> Python DSL that compiles reactive `.jinja` components to
> Jinja2 + HTMX + Alpine.js + SSE.

## 1. Overview

PJX is a compiler and runtime that transforms a component syntax inspired by
JSX/SolidJS/Svelte into standard Jinja2 templates, enriched with HTMX
(server-side interaction) and Alpine.js (client-side reactivity).

### Stack

| Layer              | Technology                                     |
| ------------------ | ---------------------------------------------- |
| Language           | Python 3.14+                                   |
| Template engine    | HybridEngine (default), Jinja2, MiniJinja      |
| Server framework   | FastAPI + Uvicorn                              |
| Client reactivity  | Alpine.js                                      |
| Server interaction | HTMX                                           |
| Realtime           | SSE / WebSocket (via HTMX extensions)          |
| CSS                | Scoped per component + Tailwind CSS (optional) |
| Validation         | Pydantic                                       |
| CLI                | Typer + Rich                                   |
| Frontend tooling   | npm (Alpine, HTMX, Tailwind → vendor/)         |

### Target Audience

Python developers who want to build reactive server-rendered UIs without
writing JavaScript, while maintaining the productivity of a modern component
framework.

---

## 2. Anatomy of a Component

Every component is a `.jinja` file with up to three blocks:

```text
┌──────────────────────────────────┐
│ ---                              │  ← Frontmatter (declarative DSL)
│   extends, from, import,         │
│   props, slot, store,            │
│   let, const, state, computed    │
│ ---                              │
├──────────────────────────────────┤
│ <style scoped>                   │  ← CSS with automatic scoping (optional)
│   .card { ... }                  │
│ </style>                         │
├──────────────────────────────────┤
│ <div reactive>                   │  ← HTML body with attribute DSL
│   <Show when="x">...</Show>     │
│   <Button ...spread_props />    │
│ </div>                           │
└──────────────────────────────────┘
```

- The frontmatter (`---`) is **required** if the component has props, state
  or imports. It can be omitted in purely static components.
- The `<style scoped>` block is **optional**.
- The **HTML body** is required.

---

## 3. Frontmatter Grammar

The frontmatter (`---`) accepts 12 types of declaration. Each line starts with
a keyword, making the grammar LL(1).

### 3.1 EBNF

```ebnf
script        = { statement } ;
statement     = extends_stmt | import_stmt | from_import_stmt
              | props_stmt | slot_stmt | store_stmt
              | let_stmt | const_stmt | state_stmt | computed_stmt
              | css_stmt | js_stmt | middleware_stmt ;

extends_stmt  = "extends" STRING ;

import_stmt   = "import" ( default_import | named_import | wildcard_import ) ;
default_import = IDENT "from" STRING [ "as" IDENT ] ;
named_import  = "{" IDENT { "," IDENT } "}" "from" STRING ;
wildcard_import = "*" "from" STRING ;

from_import_stmt = "from" MODULE "import" IDENT { "," IDENT } ;

props_stmt    = "props" [ IDENT "=" ] "{" prop_field { "," prop_field } "}" ;
prop_field    = IDENT ":" type_expr [ "=" expr ] ;
type_expr     = pydantic_type [ "|" type_expr ] ;
pydantic_type = IDENT [ "[" type_expr { "," type_expr } "]" ]
              | "Literal" "[" expr { "," expr } "]"
              | "Annotated" "[" type_expr { "," expr } "]" ;

slot_stmt     = "slot" IDENT [ "=" html_fragment ] ;
store_stmt    = "store" IDENT "=" "{" js_object "}" ;

let_stmt      = "let" IDENT "=" expr ;
const_stmt    = "const" IDENT "=" expr ;
state_stmt    = "state" IDENT "=" expr ;
computed_stmt = "computed" IDENT "=" expr ;

css_stmt      = "css" STRING ;
js_stmt       = "js" STRING ;

middleware_stmt = "middleware" STRING { "," STRING } ;

(* Body: spread syntax in components *)
component_use = "<" IDENT { attr | spread } [ "/" ] ">" ;
spread        = "..." IDENT ;
```

### 3.2 Supported types in props

The DSL accepts native Pydantic types directly:

| DSL Type                      | Pydantic model           |
| ----------------------------- | ------------------------ |
| `str`, `int`, `bool`, `float` | Native types             |
| `str \| None`                 | `str \| None` (Optional) |
| `list[str]`, `dict[str, Any]` | Generics                 |
| `Literal["a", "b"]`           | Inline enum              |
| `EmailStr`, `HttpUrl`         | Pydantic types           |
| `Annotated[int, Gt(0)]`       | Constraints              |
| `Callable`                    | `Callable \| None`       |

---

## 4. Imports

### Importing components

```python
# Default — name = file name
import Button from "./Button.jinja"

# Alias
import Button from "./Button.jinja" as PrimaryButton

# Named — multiple from a file or directory
import { CardHeader, CardBody } from "./Card.jinja"
import { Card, Badge, Avatar } from "./components/"

# Wildcard — all from directory
import * from "./ui/"
```

### Importing Python/Pydantic types

Primitive types (`str`, `int`, `bool`, `float`, `list`, `dict`, `Callable`,
`Any`, `None`) are auto-imported. Pydantic types require explicit import:

```python
from typing import Literal, Annotated
from pydantic import EmailStr, HttpUrl
from annotated_types import Gt, Lt, Ge, Le, MinLen, MaxLen
```

### Extends (layout inheritance)

```python
extends "layouts/Base.jinja"
```

Indicates that the page inherits from a layout. The body is injected into
the layout's `<Slot:content />`. See section 25 (Layouts).

### Path resolution

| Pattern                   | Resolution                                        |
| ------------------------- | ------------------------------------------------- |
| `"./Button.jinja"`        | Relative to the importing file                    |
| `"../shared/Modal.jinja"` | Relative upward directory traversal               |
| `"./components/"`         | Directory: looks for `{Name}.jinja` for each name |
| `"./ui/"` with wildcard   | Glob `*.jinja` in the directory                   |

### Compilation and composition

The compiler registers each import in the `ComponentRegistry`. When it finds
`<Button />` in the body, it resolves to `{% include %}` with context via
`{% with %}`:

```jinja2
{# <Button label="Salvar" variant="primary" /> compiles to: #}
{% with _props_label="Salvar", _props_variant="primary" %}
{% include "components/Button.jinja" %}
{% endwith %}

{# <Card title="Hello"><p>Body</p><slot:footer>F</slot:footer></Card> #}
{% with _props_title="Hello", _slot_default="<p>Body</p>", _slot_footer="F" %}
{% include "components/Card.jinja" %}
{% endwith %}

{# <Button ...btn_props label="Override" /> compiles to: #}
{% with _spread=btn_props, _props_label="Override" %}
{% include "components/Button.jinja" %}
{% endwith %}
```

Explicit props always override spread values.

---

## 5. Props

Typed declaration using native Pydantic types.

```python
props {
  name:     str,                                        # required
  age:      int                        = 0,             # optional
  role:     Literal["admin", "mod", "user"] = "user",   # choices via Literal
  email:    EmailStr,                                    # Pydantic type
  bio:      str | None                 = None,           # nullable
  tags:     list[str]                  = [],             # list factory
  meta:     dict[str, Any]            = {},              # dict factory
  score:    Annotated[int, Gt(0), Lt(100)] = 50,         # constraints
  url:      HttpUrl | None             = None,           # validated URL
  on_click: Callable                   = None,           # callback
}

# Named form is still supported:
# props UserCardProps = { name: str, age: int = 0 }
```

### Supported types

| DSL Type                      | Pydantic         |
| ----------------------------- | ---------------- |
| `str`, `int`, `bool`, `float` | Native types     |
| `str \| None`                 | Union / Optional |
| `list[str]`, `dict[str, Any]` | Generics         |
| `Literal["a", "b"]`           | Inline enum      |
| `EmailStr`, `HttpUrl`         | Pydantic types   |
| `Annotated[int, Gt(0)]`       | Constraints      |
| `Callable`                    | Callbacks        |

### Access in the template

```html
<span>{{ props.name }}</span>
```

### Internal compilation

Each `PropsDecl` generates a dynamic `pydantic.BaseModel` via
`pydantic.create_model()`:

```python
class UserCardProps(BaseModel):
    name: str
    age: int = 0
    role: Literal["admin", "mod", "user"] = "user"
    email: EmailStr
    bio: str | None = None
    tags: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
    score: Annotated[int, Gt(0), Lt(100)] = 50
    url: HttpUrl | None = None
    on_click: Callable | None = None
```

Validation occurs at render time: the context passed by the FastAPI route
is validated against the model before reaching the template engine.

---

## 6. Variables

| Keyword    | Scope              | Mutable  | Compilation          |
| ---------- | ------------------ | -------- | -------------------- |
| `let`      | Server (Jinja2)    | Yes      | `{% set x = expr %}` |
| `const`    | Server (Jinja2)    | No       | `{% set X = expr %}` |
| `state`    | Client (Alpine.js) | Yes      | Included in `x-data` |
| `computed` | Server (Jinja2)    | Derived  | `{% set x = expr %}` |

### Examples

```python
let greeting = "Hello, " + props.name
const MAX_ITEMS = 50
state count = 0
state form = { name: "", email: "" }
computed total = len(props.items)
computed progress = (done_count / total * 100) if total > 0 else 0
```

### State and x-data

All `state` declarations are collected and emitted as the `x-data` object
of the element marked with `reactive`:

```html
<!-- DSL -->
<div reactive>

<!-- Compiled -->
<div x-data="{ count: 0, form: { name: '', email: '' } }">
```

---

## 7. Slots

### Declaration

```python
slot header                                  # no fallback
slot footer = <span>© 2025 PJX</span>       # with fallback
```

### Rendering in the template

```html
<!-- Self-closing -->
<Slot:header />

<!-- With inline fallback -->
<Slot:header>
    <h2>Default title</h2>
</Slot:header>

<!-- Conditional -->
<Show when="has_slot('header')">
    <header><Slot:header /></header>
</Show>
```

### Passing when using a component

```html
<Card title="Hello">
    <p>Body (default slot)</p>
    <slot:header><h1>Custom</h1></slot:header>
    <slot:footer><button>Close</button></slot:footer>
</Card>
```

### Compilation

| DSL                               | Jinja2                                                             |
| --------------------------------- | ------------------------------------------------------------------ |
| `<Slot:name />`                   | `{{ _slot_name \| default('') }}`                                  |
| `<Slot:name>fallback</Slot:name>` | `{% if _slot_name %}{{ _slot_name }}{% else %}fallback{% endif %}` |
| `<slot:name>content</slot:name>`  | Passes `content` as variable `_slot_name` via `{% with %}`         |

---

## 8. Control Flow Tags

### 8.1 `<Show>` — Conditional

```html
<Show when="user.is_admin">
    <button>Delete</button>
</Show>

<Show when="items">
    <ul>...</ul>
    <Else><p>No items.</p></Else>
</Show>
```

| DSL                                         | Jinja2                                  |
| ------------------------------------------- | --------------------------------------- |
| `<Show when="x">body</Show>`                | `{% if x %}body{% endif %}`             |
| `<Show when="x">body<Else>fb</Else></Show>` | `{% if x %}body{% else %}fb{% endif %}` |

### 8.2 `<For>` — Iteration

```html
<For each="users" as="user">
    <li>{{ user.name }}</li>
<Empty>
    <p>No results.</p>
</Empty>
</For>
```

| DSL                               | Jinja2                             |
| --------------------------------- | ---------------------------------- |
| `<For each="x" as="i">body</For>` | `{% for i in x %}body{% endfor %}` |
| `<Empty>fallback</Empty>`         | `{% else %}fallback`               |

Loop variables inherited from Jinja2: `loop.index`, `loop.index0`,
`loop.first`, `loop.last`, `loop.length`, `loop.cycle()`.

### 8.3 `<Switch>` / `<Case>` / `<Default>`

```html
<Switch on="status">
    <Case value="active"><Badge variant="success" /></Case>
    <Case value="pending"><Badge variant="warning" /></Case>
    <Default><Badge variant="muted" /></Default>
</Switch>
```

| DSL                      | Jinja2                  |
| ------------------------ | ----------------------- |
| `<Switch on="x">`        | `{% set _sw = x %}`     |
| `<Case value="v">` (1st) | `{% if _sw == "v" %}`   |
| `<Case value="v">` (2nd+)| `{% elif _sw == "v" %}` |
| `<Default>`              | `{% else %}`            |
| `</Switch>`              | `{% endif %}`           |

### 8.4 `<Portal>` — Out-of-Band (HTMX OOB)

```html
<Portal target="notifications">
    <div class="toast">Item saved!</div>
</Portal>
```

| DSL                                     | HTML                                    |
| --------------------------------------- | --------------------------------------- |
| `<Portal target="id">`                  | `<div id="id" hx-swap-oob="true">`      |
| `<Portal target="id" swap="outerHTML">` | `<div id="id" hx-swap-oob="outerHTML">` |

### 8.5 `<ErrorBoundary>`

```html
<ErrorBoundary fallback="<p>Something went wrong.</p>">
    <UserProfile user="{{ user }}" />
</ErrorBoundary>
```

Compilation: `try/except` wrapper that renders the fallback in case of error.

### 8.6 `<Await>` — Asynchronous Loading

```html
<Await src="/api/users" trigger="load">
    <slot:loading><div class="skeleton">Loading...</div></slot:loading>
    <slot:error><p>Error loading.</p></slot:error>
</Await>
```

| DSL                                 | HTML                                                        |
| ----------------------------------- | ----------------------------------------------------------- |
| `<Await src="/url" trigger="load">` | `<div hx-get="/url" hx-trigger="load" hx-swap="innerHTML">` |

### 8.7 `<Transition>` / `<TransitionGroup>`

```html
<Transition enter="fade-in 300ms" leave="fade-out 200ms">
    <Show when="visible"><div>Content</div></Show>
</Transition>

<!-- List with transitions -->
<TransitionGroup tag="ul" enter="slide-in" leave="slide-out" move="shuffle">
    <For each="items" as="item">
        <li key="{{ item.id }}">{{ item.name }}</li>
    </For>
</TransitionGroup>
```

| DSL                                             | HTML                                            |
| ----------------------------------------------- | ----------------------------------------------- |
| `<Transition enter="x" leave="y">`              | `x-transition:enter="x" x-transition:leave="y"` |
| `<TransitionGroup tag="ul" enter="x" move="y">` | `<ul>` with transition classes per item         |
| `key="{{ id }}"`                                | Identifier for list diffing                     |

### 8.8 `<Fragment>` — No DOM wrapper

```html
<Fragment>
    <li>Item 1</li>
    <li>Item 2</li>
</Fragment>
```

Compilation: renders only the children, without a wrapper element.

### 8.9 `<Teleport>` — Client-side (Alpine)

```html
<Teleport to="#modal-root">
    <div class="modal">Content</div>
</Teleport>
```

Unlike Portal (server OOB): Teleport uses Alpine.js to move
elements in the client-side DOM.

### 8.10 `<Component>` — Dynamic Rendering

```html
<Component is="{{ widget_type }}" data="{{ widget_data }}" />
```

Resolves the component by name at runtime via registry.

---

## 9. Reactive Attributes (Alpine.js)

### 9.1 `reactive` — Initializes x-data

| DSL                     | HTML                            |
| ----------------------- | ------------------------------- |
| `reactive`              | `x-data="{ ...states }"`        |
| `reactive="{ x: 0 }"`   | `x-data="{ x: 0 }"`             |
| `reactive:store="name"` | `x-data="Alpine.store('name')"` |

### 9.2 `bind:` — Data Binding

| DSL                             | HTML                         |
| ------------------------------- | ---------------------------- |
| `bind:text="x"`                 | `x-text="x"`                 |
| `bind:html="x"`                 | `x-html="x"`                 |
| `bind:show="x"`                 | `x-show="x"`                 |
| `bind:model="x"`                | `x-model="x"`                |
| `bind:model.lazy="x"`           | `x-model.lazy="x"`           |
| `bind:model.number="x"`         | `x-model.number="x"`         |
| `bind:model.debounce.500ms="x"` | `x-model.debounce.500ms="x"` |
| `bind:class="x"`                | `:class="x"`                 |
| `bind:style="x"`                | `:style="x"`                 |
| `bind:{attr}="x"`               | `:{attr}="x"`                |
| `bind:cloak`                    | `x-cloak`                    |
| `bind:ref="x"`                  | `x-ref="x"`                  |
| `bind:transition`               | `x-transition`               |
| `bind:init="x"`                 | `x-init="x"`                 |

### 9.3 `on:` — Event Handlers

| DSL                           | HTML                        |
| ----------------------------- | --------------------------- |
| `on:click="x"`                | `@click="x"`                |
| `on:click.prevent="x"`        | `@click.prevent="x"`        |
| `on:click.stop="x"`           | `@click.stop="x"`           |
| `on:click.outside="x"`        | `@click.outside="x"`        |
| `on:click.once="x"`           | `@click.once="x"`           |
| `on:click.throttle.500ms="x"` | `@click.throttle.500ms="x"` |
| `on:input.debounce.300ms="x"` | `@input.debounce.300ms="x"` |
| `on:keydown.enter="x"`        | `@keydown.enter="x"`        |
| `on:scroll.window="x"`        | `@scroll.window="x"`        |

---

## 10. HTMX — Server Interaction

### 10.1 `action:` — HTTP Verbs

| DSL                    | HTML               |
| ---------------------- | ------------------ |
| `action:get="/url"`    | `hx-get="/url"`    |
| `action:post="/url"`   | `hx-post="/url"`   |
| `action:put="/url"`    | `hx-put="/url"`    |
| `action:patch="/url"`  | `hx-patch="/url"`  |
| `action:delete="/url"` | `hx-delete="/url"` |

### 10.2 Swap, Target, Trigger

| DSL                | HTML                                   |
| ------------------ | -------------------------------------- |
| `swap="x"`         | `hx-swap="x"`                          |
| `target="x"`       | `hx-target="x"`                        |
| `trigger="x"`      | `hx-trigger="x"`                       |
| `select="x"`       | `hx-select="x"`                        |
| `select-oob="x"`   | `hx-select-oob="x"`                    |
| `confirm="x"`      | `hx-confirm="x"`                       |
| `indicator="x"`    | `hx-indicator="x"`                     |
| `push-url`         | `hx-push-url="true"`                   |
| `replace-url`      | `hx-replace-url="true"`                |
| `vals='json'`      | `hx-vals='json'`                       |
| `headers='json'`   | `hx-headers='json'`                    |
| `encoding="x"`     | `hx-encoding="x"`                      |
| `preserve`         | `hx-preserve="true"`                   |
| `sync="x"`         | `hx-sync="x"`                          |
| `into="#sel"`      | `hx-target="#sel" hx-swap="innerHTML"` |
| `into="#sel:swap"` | `hx-target="#sel" hx-swap="swap"`      |
| `disabled-elt="x"` | `hx-disabled-elt="x"`                  |
| `boost`            | `hx-boost="true"`                      |

### 10.3 Swap values

`innerHTML` (default), `outerHTML`, `beforebegin`, `afterbegin`,
`beforeend`, `afterend`, `delete`, `none`.

Modifiers: `transition:true`, `settle:300ms`, `scroll:top`, `show:top`,
`focus-scroll:true`.

### 10.4 Trigger modifiers

`once`, `delay:Nms`, `throttle:Ns`, `queue:first|last|all`,
`from:#selector`.

---

## 11. SSE — Server-Sent Events

Requires `sse-starlette` (`uv add sse-starlette`). Layouts must load the
HTMX SSE extension (`htmx-ext-sse@2`).

```html
<div live="/events/dashboard">
    <span channel="user-count">0</span>
    <div channel="notifications" swap="beforeend"></div>
</div>
```

| DSL               | HTML                              |
| ----------------- | --------------------------------- |
| `live="/url"`     | `hx-ext="sse" sse-connect="/url"` |
| `channel="event"` | `sse-swap="event"`                |
| `close="event"`   | `sse-close="event"`               |

---

## 12. WebSocket

```html
<div socket="/ws/chat">
    <div channel="message" swap="beforeend"></div>
    <form send="message"><input name="text" /></form>
</div>
```

| DSL             | HTML                            |
| --------------- | ------------------------------- |
| `socket="/url"` | `hx-ext="ws" ws-connect="/url"` |
| `send="event"`  | `ws-send="event"`               |

---

## 13. Loading States

| DSL                        | Effect                           |
| -------------------------- | -------------------------------- |
| `loading`                  | `htmx-indicator` class           |
| `loading:show`             | Visible during request           |
| `loading:hide`             | Hidden during request            |
| `loading:class="x"`        | Adds classes during request      |
| `loading:disabled`         | `disabled` during request        |
| `loading:aria-busy="true"` | `aria-busy` during request       |

---

## 14. Forms

```html
<form action:post="/api/users" swap="outerHTML" reactive="{ valid: false }">
    <input name="name" bind:model="name" required minlength="3"
           on:input="valid = $el.form.checkValidity()" />
    <button type="submit" bind:disabled="!valid"
            loading:class="opacity-50" disabled-elt="this">
        <span loading:hide>Create</span>
        <span loading:show>Creating...</span>
    </button>
</form>
```

Upload with `encoding="multipart/form-data"`.

---

## 15. CSS Scoping

```html
<style scoped>
  .alert { padding: 1rem; }
  .alert-success { background: #d1fae5; }
</style>
```

### Compilation

1. Generate deterministic hash from the component path: `sha256(path)[:7]`
2. Prefix each selector: `.alert` → `[data-pjx-a1b2c3] .alert`
3. Add `data-pjx-a1b2c3` to the component's root element
4. Collect CSS from all components in the final build

---

## 16. Template Engine

### Protocol

```python
class EngineProtocol(Protocol):
    def render(self, template_name: str, context: dict[str, Any]) -> str: ...
    def render_string(self, source: str, context: dict[str, Any]) -> str: ...
    def add_template(self, name: str, source: str) -> None: ...
    def add_global(self, name: str, value: Any) -> None: ...
```

### Engines

| Engine                    | When to use                                                  |
| ------------------------- | ------------------------------------------------------------ |
| **HybridEngine** (default)| Automatically selects the optimal engine per template        |
| **Jinja2**                | Maximum compatibility, mature ecosystem, 1.5x faster         |
| **MiniJinja**             | Rust-based, better for free-threaded Python 3.14             |

Configurable via `pjx.toml`:

```toml
[pjx]
engine = "hybrid"  # "hybrid" | "jinja2" | "minijinja"
```

`hybrid` → HybridEngine (default). Automatically selects the optimal engine
per template.

### MiniJinja Limitations

- No access to Python methods (`x.items()`)
- No `varargs`/`kwargs` in macros
- No `%` string formatting
- Tuples become lists

The PJX compiler generates standard Jinja2 syntax compatible with both engines.

---

## 17. FastAPI Integration

### Main class

```python
from pjx import PJX, PJXConfig, SEO

app = FastAPI()
pjx = PJX(
    app,
    config=PJXConfig(toml_path="pjx.toml"),
    layout="layouts/Base.jinja",
    seo=SEO(
        title="My App",
        description="Default SEO for all pages.",
        og_type="website",
    ),
    csrf=True,
    csrf_secret="your-secret-key",
    csrf_exempt_paths={"/api/webhooks"},
    health=True,
)
```

`PJX` parameters:

| Param               | Type        | Description                                         |
| ------------------- | ----------- | --------------------------------------------------- |
| `app`               | `FastAPI`   | FastAPI instance                                    |
| `config`            | `PJXConfig` | Configuration loaded from `pjx.toml` (optional)     |
| `layout`            | `str`       | Default layout template, wraps all pages            |
| `seo`               | `SEO`       | Global SEO — pages inherit, can override per field  |
| `csrf`              | `bool`      | Enables CSRF middleware (double-submit cookie)      |
| `csrf_secret`       | `str`       | Secret key for signing CSRF tokens                  |
| `csrf_exempt_paths` | `set[str]`  | Routes exempt from CSRF validation (webhooks, APIs) |
| `health`            | `bool`      | Registers `/health` and `/ready` endpoints          |

`PJX` auto-mounts `/static` from `config.static_dir`.

When `csrf=True`, the middleware injects `csrf_token()` as a Jinja2 global.
Use in the layout: `<body hx-headers='{"X-CSRFToken": "{{ csrf_token() }}"}'>`.

When `health=True`, two endpoints are registered:

- `/health` — liveness probe (`{"status": "ok"}`)
- `/ready` — readiness probe (verifies that `template_dirs` exist)

### SEO

`SEO` is a dataclass with fields for `<title>`, `<meta>` tags, Open Graph and
Twitter Card. The global SEO defined in `PJX(seo=...)` is applied to all
pages. To override per page, use `title=` in the decorator or return
`seo` in the handler:

```python
# Via decorator (most common)
@pjx.page("/about", title="About — My App")

# Via handler (full control)
@pjx.page("/about")
async def about():
    return {"seo": SEO(title="About", description="Custom description.")}
```

Non-empty page fields override the global; empty ones use the fallback.

### Decorators

```python
# Page with template, title and methods
@pjx.page(
    "/search",
    template="pages/Search.jinja",
    title="Search — My App",
    methods=["GET", "POST"],
)
async def search(form: Annotated[SearchForm, FormData()]):
    results = do_search(form.query)
    return {"query": form.query, "results": results}

# Partial component (no layout, returns HTML fragment)
@pjx.component("components/ItemList.jinja")
async def item_list(request: Request):
    return {"items": await get_items()}
```

### FormData and Annotated

Page handlers can receive Pydantic models as parameters. Use
`Annotated[Model, FormData()]` to parse form data (POST) or query params
(GET) automatically:

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

Parameters without `FormData` are injected normally by FastAPI (`request`,
`Depends`, etc.).

### HTMX Partials

Endpoints that return HTML fragments for HTMX don't need a layout.
Use regular FastAPI routes with `HTMLResponse`:

```python
@app.post("/htmx/todos/add")
async def htmx_add_todo(request: Request) -> HTMLResponse:
    form = await request.form()
    todos_db.append({"text": form["text"], "done": False})
    return HTMLResponse(render_todo_list())
```

### Flow per request

1. FastAPI calls the handler → receives `dict` of context
2. PJX merges SEO: decorator `title=` → handler `seo` → global default
3. Compiles template and imports (with cache)
4. Engine renders compiled Jinja2 with context + `props` namespace
5. Wraps in layout (if configured) with `{{ body }}` as Markup
6. Returns `HTMLResponse`

### SSE Decorator

```python
@pjx.sse("/events/stats")
async def stats_stream(stream: EventStream):
    while True:
        stats = await get_stats()
        await stream.send_html("stats-update", "partials/stats.jinja", stats)
        await asyncio.sleep(5)
```

---

## 18. CLI

Available commands via `pjx` (Typer + Rich):

| Command            | Description                                                  |
| ------------------ | ------------------------------------------------------------ |
| `pjx init`         | Scaffolds project: dirs, config, package.json                |
| `pjx dev`          | Dev server with hot reload (uvicorn --reload)                |
| `pjx run`          | Production server                                            |
| `pjx build`        | Compiles all `.jinja` + bundles CSS + npm build              |
| `pjx check`        | Checks syntax of all `.jinja` (like ruff check)              |
| `pjx format`       | Auto-formats `.jinja` (normalizes whitespace, sorts imports) |
| `pjx add <pkg>`    | Installs JS package via npm + copies to vendor/              |
| `pjx remove <pkg>` | Removes JS package via npm                                   |

### Logging

All commands use `logging` with `rich.logging.RichHandler`:

- `DEBUG` — parse/compile details (flag `--verbose`)
- `INFO` — normal progress (files processed, server started)
- `WARNING` — deprecations, fallbacks
- `ERROR` — parse/compile errors with location (file:line:column)

---

## 19. Project Structure (generated by `pjx init`)

```text
project/
├── pjx.toml                  # PJX configuration
├── package.json               # npm for JS deps
├── templates/
│   ├── pages/                 # Full page components
│   ├── components/            # Reusable components
│   ├── ui/                    # UI primitives (Button, Badge, etc.)
│   ├── layouts/               # Base layouts (header, footer, nav)
│   └── vendor/                # Third-party templates
├── static/
│   ├── vendor/                # Compiled JS/CSS from npm (alpine, htmx)
│   ├── js/                    # Custom JavaScript
│   └── css/                   # Custom CSS + compiled scoped CSS
└── src/
    └── app.py                 # FastAPI app with PJX
```

---

## 20. Configuration (`pjx.toml`)

PJX uses a **flat** TOML file (no `[pjx]` tables) loaded via
`PJXConfig`:

```toml
engine = "hybrid"           # "hybrid" | "jinja2" | "minijinja"
debug = false

template_dirs = ["templates"]
static_dir = "static"
pages_dir = "templates/pages"
components_dir = "templates/components"
layouts_dir = "templates/layouts"
ui_dir = "templates/ui"
vendor_templates_dir = "templates/vendor"
vendor_static_dir = "static/vendor"

host = "127.0.0.1"
port = 8000

alpine = true               # Include Alpine.js by default
htmx = true                 # Include HTMX by default
tailwind = false             # Tailwind CSS opt-in

# Logging
log_json = false             # JSON output for production (ELK, Datadog)
log_level = "INFO"           # DEBUG | INFO | WARNING | ERROR | CRITICAL

# CORS (empty = disabled)
cors_origins = []            # ["https://example.com"]
cors_methods = ["GET"]       # Allowed methods
cors_headers = []            # Extra allowed headers
cors_credentials = false     # Allow cross-origin cookies
```

### Loading

```python
from pjx import PJXConfig

# Explicit path — paths resolved relative to the .toml directory
config = PJXConfig(toml_path="examples/demo/pjx.toml")

# CWD
config = PJXConfig()  # looks for pjx.toml in the current directory
```

Environment variables with the `PJX_` prefix override TOML values
(via `pydantic-settings`). Priority: init kwargs > env vars > TOML.

All relative paths in the TOML are resolved against the directory of the
`pjx.toml` file, not against the CWD.

---

## 21. Compilation Pipeline

```text
.jinja file
  │
  ├─ [1] parser._extract_blocks()
  │      Separates: frontmatter, <style scoped> body, HTML body
  │
  ├─ [2] lexer.tokenize(script)
  │      Generates token stream (keyword-driven)
  │
  ├─ [3] parser._parse_script(tokens)
  │      Produces: extends, from_imports, imports, props, slots, store,
  │              let/const, state, computed
  │
  ├─ [4] parser._parse_body(html, known_components)
  │      html.parser.HTMLParser → Node tree
  │      Recognizes: <Show>, <For>, <Switch>, <Portal>, etc.
  │      Recognizes registered components (PascalCase)
  │
  ├─ [5] Component AST (ast_nodes.Component)
  │
  ├─ [6] compiler.compile(component)
  │      ├─ Emits {% set %} for let/const/computed
  │      ├─ Collects state → alpine_data dict
  │      ├─ Transforms nodes recursively:
  │      │   ShowNode → {% if %}
  │      │   ForNode → {% for %}
  │      │   SwitchNode → {% if/elif/else %}
  │      │   ElementNode → transforms attrs (bind:→x-, on:→@, action:→hx-)
  │      │   ComponentNode → {% with %}{% include %}{% endwith %}
  │      │   PortalNode → <div hx-swap-oob>
  │      │   AwaitNode → <div hx-get hx-trigger="load">
  │      └─ css.scope_css() if <style scoped> present
  │
  ├─ [7] CompiledComponent
  │      .jinja_source  → valid Jinja2 template
  │      .css           → scoped CSS
  │      .alpine_data   → dict for x-data
  │      .scope_hash    → scope identifier
  │
  └─ [8] engine.render(jinja_source, context) → final HTML
```

---

## 22. Module Architecture

```text
src/pjx/
├── errors.py          # Exception hierarchy
├── ast_nodes.py       # AST dataclasses (IR)
├── lexer.py           # Frontmatter tokenizer
├── parser.py          # .jinja → Component AST
├── compiler.py        # AST → Jinja2 + Alpine + HTMX
├── css.py             # Scoped CSS
├── config.py          # PydanticSettings
├── registry.py        # Component registry + imports
├── props.py           # Props → Pydantic models
├── slots.py           # Slot resolution
├── engine.py          # Template engine wrapper
├── integration.py     # FastAPI decorators
├── sse.py             # SSE helpers
├── assets.py          # Static files + vendor
├── log.py             # Rich logging
├── __init__.py        # Public API
├── __main__.py        # python -m pjx → CLI
└── cli/
    ├── __init__.py    # Typer app
    ├── init.py        # pjx init
    ├── dev.py         # pjx dev, run
    ├── build.py       # pjx build, check, format
    └── packages.py    # pjx add, remove
```

### Dependency graph

```text
errors (leaf)
ast_nodes (leaf)
css (leaf)
log (leaf)
config (leaf)
lexer → errors
parser → lexer, ast_nodes, errors
props → ast_nodes, errors
slots → ast_nodes
compiler → ast_nodes, registry, css, errors
registry → ast_nodes, parser, errors
engine → config
integration → registry, compiler, engine, props, config
sse → engine, integration
assets → config
cli/* → config, registry, compiler, engine, log
```

---

## 23. Layouts and Inheritance

Layouts define the base page structure. Pages inherit via `extends`.

### Base layout (`layouts/Base.jinja`)

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
<html lang="pt-BR">
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
        <footer><p>© 2025 PJX</p></footer>
    </Slot:footer>
</body>
</html>
```

### Page that inherits

```html
---
extends "layouts/Base.jinja"
from pydantic import EmailStr

props {
  user: dict,
}
---

<slot:head>
    <meta property="og:title" content="Home — {{ props.user.name }}" />
</slot:head>

<h1>Welcome, {{ props.user.name }}</h1>
```

The page body (outside of `<slot:*>`) is automatically injected into the
layout's `<Slot:content />`.

### Compilation

```jinja2
{# extends "layouts/Base.jinja" compiles to: #}
{% extends "layouts/Base.jinja" %}
{% block content %}
  <h1>Welcome, {{ props.user.name }}</h1>
{% endblock %}
{% block head %}
  <meta property="og:title" content="Home — {{ props.user.name }}" />
{% endblock %}
```

---

## 24. Prop Spreading

Spread a dict as a component's props:

```html
<Button ...btn_props />
<Button ...btn_props label="Override" />
```

Explicit props override spread values. Compilation:

```jinja2
{% with _spread=btn_props, _props_label="Override" %}
{% include "components/Button.jinja" %}
{% endwith %}
```

---

## 25. Global State (Alpine Stores)

### Declaration in frontmatter

```python
store todos = {
  items: [],
  filter: "all",
  add(text) { this.items.push({ text, done: false }) },
}
```

### Usage in components

```html
<div reactive:store="todos">
    <input bind:model="$store.todos.filter" />
</div>
```

### Compilation

| Written                 | Compiled                                       |
| ----------------------- | ---------------------------------------------- |
| `store name = { ... }`  | `Alpine.store('name', { ... })` in init script |
| `reactive:store="name"` | `x-data="Alpine.store('name')"`                |

---

## 26. Built-in Template Functions

| Function                | Description                               |
| ----------------------- | ----------------------------------------- |
| `has_slot('name')`      | `true` if the slot was provided by parent |
| `len(x)`                | Length of list/string                     |
| `range(n)`              | Sequence 0..n-1                           |
| `enumerate(x)`          | Pairs (index, item)                       |
| `url_for('route_name')` | Reverse URL for FastAPI route             |
| `static('path')`        | URL for static file                       |

### Implementation

Registered as globals in the template engine via `engine.add_global()`.
`has_slot('name')` checks whether `_slot_{name}` is defined in the context.

---

## 27. Error Pages

### Error template

```html
---
extends "layouts/Base.jinja"

props {
  path: str,
}
---

<h1>404</h1>
<p>Page <code>{{ props.path }}</code> not found.</p>
```

### Registration via FastAPI

```python
@pjx.error(404, "errors/404.jinja")
async def not_found(request: Request):
    return {"path": request.url.path}
```

Internally, registers an `exception_handler` on FastAPI that renders
the template with the returned context.

---

## 28. Recursive Components

Components can import themselves for tree structures:

```html
---
import TreeNode from "./TreeNode.jinja"

props {
  node: dict,
  depth: int = 0,
  max_depth: int = 10,
}
---

<div style="margin-left: {{ props.depth * 16 }}px">
    <span>{{ props.node.label }}</span>
    <Show when="props.node.children and props.depth < props.max_depth">
        <For each="props.node.children" as="child">
            <TreeNode node="{{ child }}" depth="{{ props.depth + 1 }}" />
        </For>
    </Show>
</div>
```

The registry detects self-imports and allows up to `max_depth` levels.
Exceeding it generates a `CompileError`.

---

## 29. Frontmatter — Parsing Rules

- `---` must be **alone on the line** (no spaces)
- First `---` opens, next isolated `---` closes
- Strings in the frontmatter can contain `---`:
  `let x = "foo --- bar"` is valid
- Comments: `#` until end of line
- Blank lines are ignored
- Props blocks `{ ... }` can span multiple lines

Recommended order of declarations:

```text
extends → from → import → props → slot → store → let/const → state → computed
```

---

## 30. Error Format

Errors follow the format `file:line:column: Type: message`:

```text
templates/Card.jinja:15:3: ParseError: Unclosed <Show> tag
templates/Home.jinja:3:1: ImportError: Component "Missing.jinja" not found
templates/Form.jinja:8:12: PropValidationError: Field "email" expected EmailStr
```

### `pjx check` output

```text
✗ templates/Card.jinja
  15:3  error  Unclosed <Show> tag
  42:5  error  Prop "status" required but has no default

✗ templates/Home.jinja
  3:1   error  Component "Missing.jinja" not found

✓ templates/Layout.jinja
✓ templates/Button.jinja

Found 3 errors in 2 files (checked 4 files)
```

---

## 31. `pjx format` — Formatting Rules

- **Frontmatter**: normalizes indentation (0 spaces), spacing around `=`
  and `:`, groups declarations by type (extends → imports → props → etc.)
- **Imports**: sorts alphabetically, groups `from` imports separate from
  `import` components
- **Props**: aligns `:` and `=` by column, one field per line
- **Body HTML**: normalizes indentation (2 spaces), self-closing with `/>`
- **Attributes**: one per line if more than 3 attributes
- **Style**: preserves original CSS (does not reformat)

---

## 32. Asset Pipeline

Components declare CSS/JS dependencies in the frontmatter:

```html
---
css "components/card.css"
js "components/card.js"
---
```

### AST

```python
@dataclass(frozen=True, slots=True)
class AssetDecl:
    kind: str  # "css" or "js"
    path: str
```

`Component` and `CompiledComponent` have `assets: tuple[AssetDecl, ...]`.

### `AssetCollector`

`src/pjx/assets.py` — collects, deduplicates and renders tags:

- `add(asset)` — adds to the ordered set (dedup by `(kind, path)`)
- `render_css()` — generates `<link rel="stylesheet">` tags
- `render_js(module=True)` — generates `<script type="module">` tags
- `render()` — CSS + JS

Available in the template as `{{ pjx_assets.render() }}`.

---

## 33. Attrs Passthrough

Attributes not declared as props are separated and made available as
`{{ attrs }}` in the child component's template.

### Flow

1. Compiler resolves the child component's `PropsDecl` via registry
2. `separate_attrs(props_decl, all_attrs)` separates props from extras
3. Declared props → `{% set name = value %}`
4. Extras → `{% set attrs %}class="x" id="y"{% endset %}`

### `separate_attrs()`

```python
def separate_attrs(
    props_decl: PropsDecl | None,
    all_attrs: dict[str, str | bool],
) -> tuple[dict[str, str | bool], dict[str, str | bool]]:
```

If `props_decl` is `None` → everything goes to props (backwards compatible).

---

## 34. Runtime Prop Validation

When `validate_props = true` in `PJXConfig`, PJX validates props at
runtime using cached Pydantic models:

1. In `_compile_template()`: generates and caches model via `generate_props_model()`
2. In `render()`: before rendering, calls `validate_props(model, context)`
3. `PropValidationError` with clear message (which prop, expected type)

---

## 35. Inline Render Mode

`render_mode: Literal["include", "inline"] = "include"` in `PJXConfig`.

### `inline_includes()`

```python
@staticmethod
def inline_includes(
    source: str,
    compiled_templates: dict[str, str],
    *,
    max_depth: int = 50,
) -> str:
```

Recursively replaces `{% include "X" %}` with the compiled source of `X`.
Produces a flat template without external dependencies, ideal for
`engine.render_string()` where MiniJinja is 10-74x faster.

### Flow

1. Compile component + imports → `_compiled_sources`
2. `inline_includes(source, _compiled_sources)` → flat template
3. `engine.render_string(flat, context)` — no template I/O

---

## 36. Compilation Caching & Performance

### Mtime-based template cache

`_compile_template()` stores each compiled template alongside its source
file's `mtime`. On subsequent calls, if the file's mtime has not changed the
cached `CompiledComponent` is returned without re-parsing or re-compiling.

- Cold compile: ~33 ms
- Cached hit: ~2.7 ms (12x speedup)

### Diamond import deduplication

The compilation pipeline maintains a `_seen: set[str]` of already-compiled
template paths. In a diamond dependency graph (A->B->D, A->C->D), template D
is compiled exactly once regardless of how many parents import it.

### Lexer constant hoisting

The `_SINGLE` and `_ESCAPES` lookup dicts in `lexer.py` are module-level
constants. Previously they were rebuilt on every loop iteration inside the
tokenizer.

### O(1) tag recovery

Tag-recovery regexes are compiled once per tag name and cached in a
module-level dict. The regex search starts from the last matched position
rather than re-scanning the entire source string from the beginning.

---

## 37. Static Analysis (`checker.py`)

Static checks without running the server:

### `check_imports(component, registry)`

Verifies that all imports resolve to existing files.

### `check_props(component, registry)`

For each `ComponentNode` in the body, verifies that required props
(without default) are present in the attrs.

### `check_slots(component, registry)`

Verifies that slots passed to child components exist in the child's
declaration. `default` is always valid.

### `check_all(component, registry)`

Runs all checks and returns a consolidated list of `PJXError`.

### `_walk_nodes(nodes)`

Recursive walker that traverses `children`, `body`, `cases`, `fallback`.

---

## 38. File-Based Routing

PJX supports automatic routing based on the file system, inspired by
Next.js and SvelteKit. `pjx.auto_routes()` scans the `pages/` directory and
generates FastAPI routes automatically.

### Activation

```python
pjx = PJX(app, config=PJXConfig(toml_path="pjx.toml"))
pjx.auto_routes()
```

### File conventions

| File pattern                   | Generated route                | Description                           |
| ------------------------------ | ------------------------------ | ------------------------------------- |
| `pages/index.jinja`            | `/`                            | Root page                             |
| `pages/about.jinja`            | `/about`                       | Static route                          |
| `pages/blog/index.jinja`       | `/blog`                        | Directory index                       |
| `pages/blog/[slug].jinja`      | `/blog/{slug}`                 | Dynamic parameter                     |
| `pages/docs/[...slug].jinja`   | `/docs/{slug:path}`            | Catch-all (variable segments)         |
| `pages/(auth)/login.jinja`     | `/login`                       | Route group (no prefix in URL)        |
| `pages/layout.jinja`           | —                              | Shared directory layout               |
| `pages/loading.jinja`          | —                              | Loading skeleton                      |
| `pages/error.jinja`            | —                              | Directory error page                  |

### Special files

- **`layout.jinja`** — Automatically wraps all pages and sub-directories
  at the same level. Layouts are nested: `pages/layout.jinja` wraps
  `pages/blog/layout.jinja` which wraps `pages/blog/[slug].jinja`.
- **`loading.jinja`** — Skeleton shown via HTMX `hx-indicator` while the
  page loads. Optional.
- **`error.jinja`** — Rendered when a handler returns an error. Receives
  `status_code` and `message` in the context. Optional.
- **Route groups `(name)/`** — Directories in parentheses group pages without
  affecting the URL. Useful for applying layouts/middleware to a subset of routes.

### Colocated Handlers

Python handlers can be colocated alongside templates using
`RouteHandler` and `APIRoute`:

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
```

`APIRoute` allows defining JSON API endpoints colocated alongside the template,
served under the `/api/` prefix:

```python
api = APIRoute()

@api.get
async def list_items():
    return {"items": await fetch_items()}
```

---

## 39. Middleware

### Declaration in frontmatter

Components and pages can declare middleware in the frontmatter:

```html
---
middleware "auth", "rate_limit"
---
```

The declaration accepts one or more comma-separated strings. Each string
references a middleware registered in the PJX runtime.

### Registration in the runtime

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
    # Rate limiting logic
    response = await call_next(request)
    return response
```

Middleware declared in the frontmatter is applied in declaration order.
Layout middleware is applied before page middleware.

---

## 40. Layout Components (Built-ins)

PJX includes built-in layout components inspired by Chakra UI. They are
compiled directly by the compiler (no import needed).

### Available components

| Component       | Description                                    | Main props                        |
| --------------- | ---------------------------------------------- | --------------------------------- |
| `<Center>`      | Centers content horizontally and vertically    | `w`, `h`                          |
| `<HStack>`      | Horizontal stack with gap                      | `gap`, `align`, `justify`, `wrap` |
| `<VStack>`      | Vertical stack with gap                        | `gap`, `align`, `justify`         |
| `<Grid>`        | Responsive CSS grid                            | `cols`, `gap`, `min`, `max`       |
| `<Spacer>`      | Flexible space between items                   | —                                 |
| `<Container>`   | Centered maximum width                         | `max`, `px`                       |
| `<Divider>`     | Dividing line                                  | `orientation`, `color`            |
| `<Wrap>`        | Flex wrap with gap                             | `gap`, `align`, `justify`         |
| `<AspectRatio>` | Maintains content aspect ratio                 | `ratio`                           |
| `<Hide>`        | Hides content by breakpoint                    | `below`, `above`                  |

### Examples

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

### Compilation

Layout components are compiled to HTML + utility CSS:

| DSL                          | Compiled HTML                                                             |
| ---------------------------- | ------------------------------------------------------------------------- |
| `<Center>`                   | `<div style="display:flex;align-items:center;justify-content:center">`    |
| `<HStack gap="1rem">`        | `<div style="display:flex;flex-direction:row;gap:1rem">`                  |
| `<VStack gap="1rem">`        | `<div style="display:flex;flex-direction:column;gap:1rem">`               |
| `<Grid cols="3" gap="1rem">` | `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem">` |
| `<Spacer />`                 | `<div style="flex:1">`                                                    |
| `<Container max="1200px">`   | `<div style="max-width:1200px;margin:0 auto">`                            |
| `<Hide below="md">`          | `<div class="pjx-hide-below-md">`                                         |
| `<AspectRatio ratio="16/9">` | `<div style="aspect-ratio:16/9">`                                         |

---

## 41. Non-Goals

- **Not a frontend JS framework** — Alpine.js handles client reactivity
- **Does not compile to React/Vue/Solid** — the target is Jinja2 + HTMX
- **Not a full JS bundler** — npm + simple build for vendor/
- **Does not support TypeScript** — the DSL is Python-typed
- **Does not do SSG** — focus on dynamic server-rendered
- **Does not replace Jinja2** — compiles *to* Jinja2

---

## 42. References

- [HTMX](https://htmx.org/docs/)
- [Alpine.js](https://alpinejs.dev/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [MiniJinja](https://github.com/mitsuhiko/minijinja)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic](https://docs.pydantic.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
