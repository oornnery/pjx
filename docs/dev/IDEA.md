# PJX DSL — Complete Specification

> Python DSL for reactive `.jinja` components, inspired by SolidJS, Svelte and Vue.
> Compiles to Jinja2 + HTMX + Alpine.js + SSE.

---

## 1. `.jinja` Component Structure

Every component is a `.jinja` file with a declarative frontmatter delimited
by `---` at the top and reactive HTML in the body.

```html
---
import Button from "./Button.jinja"
import Badge from "../shared/Badge.jinja"
import { CardHeader, CardBody } from "./Card.jinja"

props {
  id:       int,
  text:     str,
  done:     bool      = false,
  priority: str       = "medium"  ["high", "medium", "low"],
  tags:     list[str] = [],
}

slot actions
slot footer = <span>Default footer</span>

let css_class = "todo-" + props.priority
const MAX_LENGTH = 140

state count = 0
state editing = false
state hover = false

computed remaining = MAX_LENGTH - len(props.text)
computed is_valid = remaining >= 0
---

<li id="todo-{{ props.id }}" class="{{ css_class }}" reactive>
    <!-- component body -->
</li>
```

---

## 2. Imports

### Import components

```python
# ── Import component (name = file name) ──────────────────
import Button from "./Button.jinja"
import Modal from "../shared/Modal.jinja"

# ── Alias ─────────────────────────────────────────────────
import Button from "./Button.jinja" as PrimaryButton

# ── Import multiple from a directory ──────────────────────
import { Card, Badge, Avatar } from "./components/"

# ── Import sub-components from a multi-export file ────────
import { CardHeader, CardBody, CardFooter } from "./Card.jinja"

# ── Wildcard (all from directory) ─────────────────────────
import * from "./ui/"
```

### Import Python/Pydantic types

Primitive types (`str`, `int`, `bool`, `float`, `list`, `dict`, `Callable`,
`Any`, `None`) are auto-imported. Pydantic types and constraints require
explicit import with Python syntax:

```python
from typing import Literal, Annotated
from pydantic import EmailStr, HttpUrl
from annotated_types import Gt, Lt, Ge, Le, MinLen, MaxLen
```

### Extends (layout inheritance)

```python
extends "layouts/Base.jinja"
```

Indicates that the page inherits from a layout. The page body is injected into
the layout's `<Slot:content />`. See section 18 (Layouts).

### Compilation

| Written                               | Internal effect                                            |
| ------------------------------------- | ---------------------------------------------------------- |
| `import Button from "./Button.jinja"` | Registers `Button` in the preprocessor, loads the template |
| `import Button from "..." as Btn`     | Registers as `Btn`                                         |
| `import { A, B } from "./dir/"`       | Loads `dir/A.jinja` and `dir/B.jinja`                      |
| `from pydantic import EmailStr`       | Makes `EmailStr` available as a type in props              |
| `extends "layouts/Base.jinja"`        | Wraps the page in the layout (template inheritance)        |

---

## 3. Props

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
```

**Supported Pydantic types:**

| DSL type                      | Pydantic         |
| ----------------------------- | ---------------- |
| `str`, `int`, `bool`, `float` | Native types     |
| `str \| None`                 | Union / Optional |
| `list[str]`, `dict[str, Any]` | Generics         |
| `Literal["a", "b"]`           | Inline enum      |
| `EmailStr`, `HttpUrl`         | Pydantic types   |
| `Annotated[int, Gt(0)]`       | Constraints      |
| `Callable`                    | Callbacks        |

**Access in template:**

```html
<span>{{ props.name }}</span>
<span>{{ props.role }}</span>
```

**Internal compilation:**

```python
# Automatically generates a BaseModel:
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

---

## 4. Variables

```python
# ── let — server-side variable (available in template) ────
let greeting = "Hello, " + props.name
let item_count = len(props.items)
let css_class = "card card--" + props.variant

# ── const — immutable constant ────────────────────────────
const MAX_ITEMS = 50
const API_URL = "/api/v1"

# ── state — CLIENT-SIDE reactive variable (Alpine.js) ─────
state count = 0
state open = false
state search = ""
state selected = []
state form = { name: "", email: "" }

# ── computed — reactive derived (recalculates when deps change) ─
computed total = len(props.items)
computed done_count = len([i for i in props.items if i.done])
computed progress = (done_count / total * 100) if total > 0 else 0
computed is_empty = total == 0
```

**Compilation:**

| Written                 | Server (Jinja2)          | Client (Alpine.js)            |
| ----------------------- | ------------------------ | ----------------------------- |
| `let x = 1`             | `{% set x = 1 %}`        | —                             |
| `const X = 1`           | `{% set X = 1 %}`        | —                             |
| `state count = 0`       | `{{ count }}` for SSR    | `x-data` includes `count: 0`  |
| `computed total = expr` | `{% set total = expr %}` | —                             |

---

## 5. Slots

```python
# ── Declare slot in frontmatter ───────────────────────────
slot header                                    # slot without fallback
slot footer = <span>© 2025 PJX</span>         # with fallback
slot actions                                   # empty slot if not provided
```

**Render slot in template:**

```html
<!-- Self-closing: renders or empty -->
<Slot:header />

<!-- With inline fallback -->
<Slot:header>
    <h2>Default title</h2>
</Slot:header>

<!-- Slot with conditional -->
<Show when="has_slot('header')">
    <header><Slot:header /></header>
</Show>
```

**Pass slot when using component:**

```html
<Card title="Hello">
    <!-- children = default slot -->
    <p>Card body</p>

    <!-- named slot -->
    <slot:header>
        <h1>Custom Header</h1>
    </slot:header>

    <slot:footer>
        <button on:click="cancel()">Cancel</button>
        <button on:click="confirm()">Confirm</button>
    </slot:footer>
</Card>
```

**Compilation:**

| Written                          | Result                                                           |
| -------------------------------- | ---------------------------------------------------------------- |
| `<Slot:header />`                | `{{ _slot_header \| default('') }}`                              |
| `<Slot:header>fb</Slot:header>`  | `{% if _slot_header %}{{ _slot_header }}{% else %}fb{% endif %}` |
| `<slot:name>content</slot:name>` | Passes `content` as a named slot to the parent component         |

---

## 6. Control Flow — HTML Tags

### `<Show>` — Conditional

```html
<!-- Simple -->
<Show when="user.is_admin">
    <button>Delete</button>
</Show>

<!-- With fallback -->
<Show when="items" fallback="<p>No items.</p>">
    <ul>...</ul>
</Show>

<!-- Negation -->
<Show when="not loading">
    <div>Content loaded</div>
</Show>

<!-- Complex expression -->
<Show when="user.age >= 18 and user.verified">
    <span>Access granted</span>
</Show>
```

| Written                                    | Compiled                                |
| ------------------------------------------ | --------------------------------------- |
| `<Show when="x">...body...</Show>`         | `{% if x %}...body...{% endif %}`       |
| `<Show when="x" fallback="fb">body</Show>` | `{% if x %}body{% else %}fb{% endif %}` |

---

### `<For>` — Iteration

```html
<!-- Basic -->
<For each="users" as="user">
    <li>{{ user.name }}</li>
</For>

<!-- With index (uses Jinja2's loop.index0) -->
<For each="items" as="item">
    <li>{{ loop.index }}. {{ item }}</li>
</For>

<!-- With empty fallback -->
<For each="results" as="result">
    <div>{{ result.title }}</div>
<Empty>
    <p>No results found.</p>
</Empty>
</For>

<!-- Nested -->
<For each="categories" as="cat">
    <h3>{{ cat.name }}</h3>
    <For each="cat.products" as="product">
        <span>{{ product.name }}</span>
    </For>
</For>

<!-- With inline filter -->
<For each="users | selectattr('active')" as="user">
    <li>{{ user.name }}</li>
</For>
```

| Written                 | Compiled           |
| ----------------------- | ------------------ |
| `<For each="x" as="i">` | `{% for i in x %}` |
| `<Empty>`               | `{% else %}`       |
| `</For>`                | `{% endfor %}`     |

**Available loop variables (inherited from Jinja2):**

| Variable              | Description                 |
| --------------------- | --------------------------- |
| `loop.index`          | Current iteration (1-based) |
| `loop.index0`         | Current iteration (0-based) |
| `loop.first`          | `true` if first item        |
| `loop.last`           | `true` if last item         |
| `loop.length`         | Total items                 |
| `loop.cycle('a','b')` | Alternates between values   |

---

### `<Switch>` / `<Case>` / `<Default>` — Multi-branch

```html
<Switch on="status">
    <Case value="active">
        <Badge text="Active" variant="success" />
    </Case>
    <Case value="pending">
        <Badge text="Pending" variant="warning" />
    </Case>
    <Case value="blocked">
        <Badge text="Blocked" variant="danger" />
    </Case>
    <Default>
        <Badge text="Unknown" variant="muted" />
    </Default>
</Switch>

<!-- Switch with numbers -->
<Switch on="props.level">
    <Case value="1"><h1>{{ title }}</h1></Case>
    <Case value="2"><h2>{{ title }}</h2></Case>
    <Case value="3"><h3>{{ title }}</h3></Case>
    <Default><p>{{ title }}</p></Default>
</Switch>
```

| Written                   | Compiled                |
| ------------------------- | ----------------------- |
| `<Switch on="x">`         | `{% set _sw = x %}`     |
| `<Case value="v">` (1st)  | `{% if _sw == "v" %}`   |
| `<Case value="v">` (2nd+) | `{% elif _sw == "v" %}` |
| `<Default>`               | `{% else %}`            |
| `</Switch>`               | `{% endif %}`           |

---

### `<Portal>` — Out-of-Band Swap (HTMX OOB)

```html
<!-- Teleports content to another place in the DOM via HTMX OOB -->
<Portal target="notifications">
    <div class="toast toast-success">Item saved!</div>
</Portal>

<!-- Replace sidebar -->
<Portal target="sidebar" swap="outerHTML">
    <nav>Updated menu</nav>
</Portal>
```

| Written                                 | Compiled                                |
| --------------------------------------- | --------------------------------------- |
| `<Portal target="id">`                  | `<div id="id" hx-swap-oob="true">`      |
| `<Portal target="id" swap="outerHTML">` | `<div id="id" hx-swap-oob="outerHTML">` |
| `</Portal>`                             | `</div>`                                |

---

### `<Component>` — Component Rendering

```html
<!-- Self-closing (no children) -->
<Badge text="Novo" variant="success" />

<!-- With children -->
<Card title="Welcome" variant="primary">
    <p>Card content.</p>
</Card>

<!-- With named slots -->
<Modal title="Confirm">
    <p>Are you sure?</p>

    <slot:footer>
        <button on:click="cancel()">Cancel</button>
        <button on:click="confirm()">Confirm</button>
    </slot:footer>
</Modal>

<!-- Dynamic component -->
<Component is="{{ widget_type }}" data="{{ widget_data }}" />

<!-- Prop spreading — spreads dict as props -->
<Button ...btn_props />
<Button ...btn_props label="Override" />

<!-- Recursive component (tree) -->
<TreeNode node="{{ child }}" />
```

---

### `<ErrorBoundary>` — Error Handling

```html
<ErrorBoundary fallback="<p>Something went wrong.</p>">
    <UserProfile user="{{ user }}" />
</ErrorBoundary>

<!-- With custom error component -->
<ErrorBoundary>
    <RiskyComponent />
    <slot:error>
        <div class="error-box">
            <h3>Error loading</h3>
            <button action:get="/retry" target="closest div" swap="outerHTML">
                Try again
            </button>
        </div>
    </slot:error>
</ErrorBoundary>
```

| Written                                             | Compiled                                            |
| --------------------------------------------------- | --------------------------------------------------- |
| `<ErrorBoundary fallback="fb">body</ErrorBoundary>` | `try/except` wrapper that renders fallback on error |

---

### `<Await>` — Async Loading

```html
<!-- Placeholder while loading via HTMX -->
<Await src="/api/users" trigger="load">
    <slot:loading>
        <div class="skeleton">Loading...</div>
    </slot:loading>

    <slot:error>
        <p>Error loading data.</p>
    </slot:error>
</Await>
```

| Written                             | Compiled                                                                  |
| ----------------------------------- | ------------------------------------------------------------------------- |
| `<Await src="/url" trigger="load">` | `<div hx-get="/url" hx-trigger="load" hx-swap="innerHTML">` with skeleton |

---

### `<Transition>` — Animations

```html
<Transition enter="fade-in 300ms" leave="fade-out 200ms">
    <Show when="visible">
        <div class="modal">Content</div>
    </Show>
</Transition>

<!-- List transition -->
<TransitionGroup tag="ul" enter="slide-in" leave="slide-out" move="shuffle">
    <For each="items" as="item">
        <li key="{{ item.id }}">{{ item.name }}</li>
    </For>
</TransitionGroup>
```

| Written                            | Compiled                                                     |
| ---------------------------------- | ------------------------------------------------------------ |
| `<Transition enter="x" leave="y">` | Wrapper with `x-transition:enter="x" x-transition:leave="y"` |

---

### `<Fragment>` — Wrapper without DOM element

```html
<!-- Renders children without creating a wrapper element -->
<Fragment>
    <li>Item 1</li>
    <li>Item 2</li>
    <li>Item 3</li>
</Fragment>
```

---

### `<Teleport>` — Render in another DOM location (client-side)

```html
<!-- Different from Portal (server OOB): Teleport is client-side via Alpine -->
<Teleport to="#modal-root">
    <div class="modal">Teleported content</div>
</Teleport>
```

---

## 7. Reactive Attributes (Alpine.js)

### `reactive` — Initializes x-data

```html
<!-- Bare: generates x-data with all declared state -->
<div reactive>

<!-- Explicit: custom x-data -->
<div reactive="{ count: 0, open: false }">

<!-- With store scope -->
<div reactive:store="todos">
```

| Written                 | Compiled                        |
| ----------------------- | ------------------------------- |
| `reactive`              | `x-data="{{ alpine_data }}"`    |
| `reactive="{ x: 0 }"`   | `x-data="{ x: 0 }"`             |
| `reactive:store="name"` | `x-data="Alpine.store('name')"` |

---

### `bind:` — Data Binding

```html
<span bind:text="count">0</span>              <!-- x-text -->
<div bind:html="richContent"></div>             <!-- x-html -->
<div bind:show="isVisible"></div>               <!-- x-show -->
<input bind:model="name" />                     <!-- x-model -->
<input bind:model.lazy="email" />               <!-- x-model.lazy -->
<input bind:model.number="age" />               <!-- x-model.number -->
<input bind:model.debounce.500ms="search" />    <!-- x-model.debounce.500ms -->
<div bind:class="{ 'active': isActive }"></div> <!-- :class -->
<div bind:style="{ color: textColor }"></div>   <!-- :style -->
<img bind:src="imageUrl" />                     <!-- :src -->
<a bind:href="link"></a>                        <!-- :href -->
<button bind:disabled="!isValid"></button>      <!-- :disabled -->
<div bind:id="'item-' + id"></div>              <!-- :id -->

<!-- Cloak (prevents flash of unrendered content) -->
<div bind:cloak></div>                          <!-- x-cloak -->

<!-- Ref (element reference) -->
<input bind:ref="searchInput" />                <!-- x-ref -->

<!-- Transition -->
<div bind:transition></div>                     <!-- x-transition -->
<div bind:transition.opacity></div>             <!-- x-transition.opacity -->
<div bind:transition.duration.500ms></div>      <!-- x-transition.duration.500ms -->

<!-- Init (executes on initialization) -->
<div bind:init="fetchData()"></div>             <!-- x-init -->
```

| Written                         | Compiled                     |
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

---

## 8. Events

### `on:` — Event Handlers (Alpine.js client-side)

```html
<!-- Basic -->
<button on:click="count++">+</button>
<button on:click="handleClick()">Click</button>

<!-- Modifiers -->
<form on:submit.prevent="save()">
<a on:click.prevent.stop="navigate()">
<div on:click.outside="open = false">
<input on:keydown.enter="submit()">
<input on:keydown.escape="cancel()">
<div on:scroll.window="handleScroll()">

<!-- Timing modifiers -->
<button on:click.throttle.500ms="save()">
<input on:input.debounce.300ms="search()">
<button on:click.once="init()">

<!-- Self (only if target is the element itself) -->
<div on:click.self="close()">
```

| Written                       | Compiled                    |
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

## 9. HTMX — Server Interaction

### `action:` — HTTP Verbs

```html
<button action:get="/api/items">Load</button>
<form action:post="/api/items">Create</form>
<button action:put="/api/items/1">Update</button>
<button action:patch="/api/items/1/toggle">Toggle</button>
<button action:delete="/api/items/1">Delete</button>
```

| Written                | Compiled           |
| ---------------------- | ------------------ |
| `action:get="/url"`    | `hx-get="/url"`    |
| `action:post="/url"`   | `hx-post="/url"`   |
| `action:put="/url"`    | `hx-put="/url"`    |
| `action:patch="/url"`  | `hx-patch="/url"`  |
| `action:delete="/url"` | `hx-delete="/url"` |

---

### Swap / Target / Trigger

```html
<div swap="innerHTML">            <!-- default -->
<div swap="outerHTML">             <!-- replaces the entire element -->
<div swap="beforebegin">           <!-- inserts before the element -->
<div swap="afterbegin">            <!-- inserts at the beginning (first child) -->
<div swap="beforeend">             <!-- inserts at the end (last child) -->
<div swap="afterend">              <!-- inserts after the element -->
<div swap="delete">                <!-- removes the element -->
<div swap="none">                  <!-- no swap (fire-and-forget) -->

<!-- With modifiers -->
<div swap="innerHTML transition:true">
<div swap="innerHTML settle:300ms">
<div swap="innerHTML scroll:top">
<div swap="innerHTML show:top">
<div swap="innerHTML focus-scroll:true">

<!-- Target -->
<button target="#result">          <!-- where to place the response -->
<button target="closest li">      <!-- relative CSS selector -->
<button target="next .panel">
<button target="previous .item">
<button target="find .content">   <!-- within the element -->

<!-- Trigger -->
<div trigger="load">               <!-- fires on load -->
<div trigger="revealed">           <!-- fires when visible (viewport) -->
<div trigger="intersect">          <!-- IntersectionObserver -->
<div trigger="every 5s">           <!-- polling -->
<input trigger="input changed delay:300ms">
<form trigger="submit">
<div trigger="click[ctrlKey]">     <!-- with JS filter -->

<!-- Select (which part of the response to use) -->
<div select=".content">            <!-- picks only .content from the response -->
<div select-oob="#sidebar">        <!-- additional OOB swap -->

<!-- Into (shorthand for target + swap) -->
<button into="#result">             <!-- hx-target="#result" hx-swap="innerHTML" -->
<button into="#result:outerHTML">   <!-- hx-target="#result" hx-swap="outerHTML" -->
```

| Written                          | Compiled                               |
| -------------------------------- | -------------------------------------- |
| `swap="x"`                       | `hx-swap="x"`                          |
| `target="x"`                     | `hx-target="x"`                        |
| `trigger="x"`                    | `hx-trigger="x"`                       |
| `select="x"`                     | `hx-select="x"`                        |
| `select-oob="x"`                 | `hx-select-oob="x"`                    |
| `confirm="x"`                    | `hx-confirm="x"`                       |
| `indicator="x"`                  | `hx-indicator="x"`                     |
| `push-url`                       | `hx-push-url="true"`                   |
| `push-url="/path"`               | `hx-push-url="/path"`                  |
| `replace-url`                    | `hx-replace-url="true"`                |
| `vals='{"k":"v"}'`               | `hx-vals='{"k":"v"}'`                  |
| `headers='{"X-Custom":"v"}'`     | `hx-headers='{"X-Custom":"v"}'`        |
| `encoding="multipart/form-data"` | `hx-encoding="multipart/form-data"`    |
| `preserve`                       | `hx-preserve="true"`                   |
| `sync="closest form:abort"`      | `hx-sync="closest form:abort"`         |
| `disabled-elt="this"`            | `hx-disabled-elt="this"`               |
| `into="#sel"`                    | `hx-target="#sel" hx-swap="innerHTML"` |
| `into="#sel:outerHTML"`          | `hx-target="#sel" hx-swap="outerHTML"` |

---

### Compound Trigger Modifiers

```html
<!-- once — fires only once -->
<div trigger="load once">
<button trigger="click once">

<!-- delay -->
<input trigger="input changed delay:500ms">

<!-- throttle -->
<button trigger="click throttle:1s">

<!-- queue -->
<button trigger="click queue:first">
<button trigger="click queue:last">
<button trigger="click queue:all">

<!-- from (listen to event from another element) -->
<div trigger="click from:#other-button">

<!-- Combine triggers -->
<div trigger="load, click, keyup[key=='Enter'] from:body">
```

| Written            | Compiled                                  |
| ------------------ | ----------------------------------------- |
| `once`             | adds `once` to `hx-trigger`               |
| `debounce="500ms"` | adds `delay:500ms` to `hx-trigger`        |
| `throttle="500ms"` | adds `throttle:500ms` to `hx-trigger`     |

---

### `boost` — Boost (Progressive Enhancement)

```html
<!-- Transforms links/forms into AJAX automatically -->
<nav boost>
    <a href="/about">About</a>    <!-- becomes hx-get="/about" -->
    <a href="/contact">Contact</a>
</nav>

<form boost action="/submit" method="post">
    <!-- becomes hx-post="/submit" -->
</form>
```

| Written | Compiled          |
| ------- | ----------------- |
| `boost` | `hx-boost="true"` |

---

## 10. SSE — Server-Sent Events

Requires `sse-starlette` dependency. Layouts must load the HTMX SSE extension
(`htmx-ext-sse@2`) via a `<script>` tag.

```html
<!-- Connect to an SSE endpoint -->
<div live="/events/dashboard">
    <!-- Receive specific events -->
    <span channel="user-count">0</span>
    <div channel="notifications" swap="beforeend"></div>
    <div channel="stats-update" swap="outerHTML"></div>
</div>

<!-- Close connection on condition -->
<div live="/events/chat" close="closeChat">
```

| Written                    | Compiled                          |
| -------------------------- | --------------------------------- |
| `live="/url"`              | `hx-ext="sse" sse-connect="/url"` |
| `channel="event"`          | `sse-swap="event"`                |
| `channel="event" swap="x"` | `sse-swap="event" hx-swap="x"`    |
| `close="event"`            | `sse-close="event"`               |

---

## 11. WebSocket

```html
<!-- Connect via WebSocket -->
<div socket="/ws/chat">
    <div channel="message" swap="beforeend"></div>
    <form send="message">
        <input name="text" />
    </form>
</div>
```

| Written         | Compiled                        |
| --------------- | ------------------------------- |
| `socket="/url"` | `hx-ext="ws" ws-connect="/url"` |
| `send="event"`  | `ws-send="event"`               |

---

## 12. Loading States

```html
<!-- Global indicator -->
<button action:post="/api/save"
        indicator="#spinner">
    Save
</button>
<span id="spinner" class="htmx-indicator">⏳</span>

<!-- Inline indicator with DSL -->
<button action:post="/api/save" loading>
    <span loading:hide>Save</span>
    <span loading:show>Saving...</span>
</button>

<!-- Classes during request -->
<button action:post="/api/save"
        loading:class="opacity-50 cursor-wait"
        loading:disabled>
    Save
</button>

<!-- Disable during request -->
<button action:post="/api/save"
        disabled-elt="this">
    Save
</button>

<!-- Skeleton loading -->
<div action:get="/api/data"
     trigger="load"
     loading:aria-busy="true">
    <div class="skeleton"></div>
</div>
```

| Written                    | Compiled                           |
| -------------------------- | ---------------------------------- |
| `loading`                  | Adds `htmx-indicator` class        |
| `loading:show`             | Element visible during request     |
| `loading:hide`             | Element hidden during request      |
| `loading:class="x"`        | Adds classes during request        |
| `loading:disabled`         | `disabled` during request          |
| `loading:aria-busy="true"` | `aria-busy` during request         |
| `disabled-elt="this"`      | `hx-disabled-elt="this"`           |

---

## 13. Forms

```html
<!-- Reactive form with client-side validation -->
<form action:post="/api/users"
      swap="outerHTML"
      reactive="{ valid: false }">

    <input name="name"
           bind:model="name"
           required
           minlength="3"
           on:input="valid = $el.form.checkValidity()" />

    <input name="email"
           bind:model="email"
           type="email"
           required />

    <button type="submit"
            bind:disabled="!valid"
            loading:class="opacity-50"
            disabled-elt="this">
        <span loading:hide>Create user</span>
        <span loading:show>Creating...</span>
    </button>
</form>

<!-- File upload -->
<form action:post="/api/upload"
      encoding="multipart/form-data"
      swap="none">
    <input type="file" name="file" />
    <button type="submit">Upload</button>
</form>
```

---

## 14. CSS Scoping

```html
---
import Button from "./Button.jinja"
props { type: str = "info" }
---

<!-- Styles with automatic scoping (data-pjx-HASH attribute on component) -->
<style scoped>
  .alert { padding: 1rem; border-radius: 8px; }
  .alert-success { background: #d1fae5; color: #065f46; }
  .alert-error { background: #fee2e2; color: #991b1b; }
</style>

<div class="alert alert-{{ props.type }}">
    {{ children }}
</div>
```

---

## 15. Asset Includes — JS, CSS and Static Files

Components can declare external file dependencies (scripts, stylesheets,
fonts) using `<script>` and `<link>` tags in the body. PJX collects
all dependencies and deduplicates them in the final HTML.

### External CSS include

```html
<link rel="stylesheet" href="/static/css/datepicker.css" />
```

### External JS include

```html
<script src="/static/vendor/chart.js" defer></script>
```

### Directory structure for assets

```text
project-root/
├── templates/
│   ├── pages/           # Pages (extends layouts)
│   ├── components/      # Reusable components
│   ├── layouts/         # Base layouts
│   └── ui/              # UI library
├── static/
│   ├── vendor/          # Third-party JS/CSS (Alpine, HTMX, etc.)
│   │   ├── alpine.min.js
│   │   └── htmx.min.js
│   ├── css/             # Compiled CSS (Tailwind, PJX bundles)
│   │   └── pjx-components.css
│   ├── js/              # Project JS
│   └── images/          # Images and other assets
├── pjx.toml             # Project configuration
└── app.py               # FastAPI application
```

### Base layout with includes

The base layout (`templates/layouts/Base.jinja`) is responsible for including
global assets (Alpine.js, HTMX, base CSS). Pages extend this layout:

```html
<!-- templates/layouts/Base.jinja -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{{ seo.title|default(title)|default("PJX App") }}</title>
  <link rel="icon" href="{{ favicon|default('/static/images/favicon.svg') }}" type="image/svg+xml" />

  {# SEO meta tags #}
  {% if seo.description %}<meta name="description" content="{{ seo.description }}" />{% endif %}
  {% if seo.og_title or seo.title %}<meta property="og:title" content="{{ seo.og_title|default(seo.title) }}" />{% endif %}
  {% if seo.og_description or seo.description %}<meta property="og:description" content="{{ seo.og_description|default(seo.description) }}" />{% endif %}

  {# Stylesheets #}
  <link rel="stylesheet" href="/static/css/base.css" />
  {% for css in head_css|default([]) %}
    <link rel="stylesheet" href="{{ css }}" />
  {% endfor %}

  {# Scripts #}
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
  <script src="https://unpkg.com/htmx.org@2/dist/htmx.min.js"></script>
  {% for js in head_scripts|default([]) %}
    <script src="{{ js }}"></script>
  {% endfor %}
</head>
<body>
  {{ body|default("") }}
  {% for js in body_scripts|default([]) %}
    <script src="{{ js }}"></script>
  {% endfor %}
  <script src="/static/js/app.js"></script>
</body>
</html>
```

### Component with its own assets

Components can include inline or external scripts and styles. The `<script>`
in the body is passed directly to the HTML (not processed by the frontmatter):

```html
---
props {
  data: list = [],
  type: str = "bar",
}
---

<style scoped>
.chart-container { width: 100%; height: 300px; }
</style>

<div class="chart-container">
  <canvas id="chart-{{ props.type }}"></canvas>
</div>

<script src="/static/js/chart-init.js" defer></script>
```

### `pjx build` and CSS bundling

The `pjx build` command compiles all components and generates a unified CSS
bundle at `static/css/pjx-components.css` containing all scoped styles.
This file can be included in the base layout.

### Directory configuration (`pjx.toml`)

```toml
engine = "hybrid"
debug = true

template_dirs = ["templates"]
static_dir = "static"
```

---

## 16. Complete Compilation Table

### Control Flow

| DSL                                                                    | Jinja2                                          |
| ---------------------------------------------------------------------- | ----------------------------------------------- |
| `<Show when="x">body</Show>`                                           | `{% if x %}body{% endif %}`                     |
| `<Show when="x" fallback="fb">body</Show>`                             | `{% if x %}body{% else %}fb{% endif %}`         |
| `<For each="xs" as="x">body</For>`                                     | `{% for x in xs %}body{% endfor %}`             |
| `<For each="xs" as="x">body<Empty>fb</Empty></For>`                    | `{% for x in xs %}body{% else %}fb{% endfor %}` |
| `<Switch on="v"><Case value="a">A</Case><Default>?</Default></Switch>` | `{% if v=="a" %}A{% else %}?{% endif %}`        |
| `<ErrorBoundary fallback="fb">body</ErrorBoundary>`                    | `try/except` wrapper                            |
| `<Fragment>body</Fragment>`                                            | `body` (no wrapper)                             |
| `<Portal target="id">body</Portal>`                                    | `<div id="id" hx-swap-oob="true">body</div>`    |
| `<Component is="name" />`                                              | Dynamic rendering by name                       |
| `<Await src="/url">`                                                   | `<div hx-get="/url" hx-trigger="load">`         |

### Variables

| DSL                 | Effect                                  |
| ------------------- | --------------------------------------- |
| `let x = val`       | `{% set x = val %}` (server)            |
| `const X = val`     | `{% set X = val %}` (immutable, server) |
| `state x = val`     | Alpine `x-data` includes `x: val`       |
| `computed x = expr` | `{% set x = expr %}` + reactive         |

### Alpine (client)

| DSL                             | HTML                         |
| ------------------------------- | ---------------------------- |
| `reactive`                      | `x-data="{{ alpine_data }}"` |
| `reactive="{ x: 0 }"`           | `x-data="{ x: 0 }"`          |
| `bind:text="x"`                 | `x-text="x"`                 |
| `bind:html="x"`                 | `x-html="x"`                 |
| `bind:show="x"`                 | `x-show="x"`                 |
| `bind:model="x"`                | `x-model="x"`                |
| `bind:model.lazy="x"`           | `x-model.lazy="x"`           |
| `bind:model.number="x"`         | `x-model.number="x"`         |
| `bind:model.debounce.500ms="x"` | `x-model.debounce.500ms="x"` |
| `bind:{attr}="x"`               | `:{attr}="x"`                |
| `bind:cloak`                    | `x-cloak`                    |
| `bind:ref="x"`                  | `x-ref="x"`                  |
| `bind:transition`               | `x-transition`               |
| `bind:init="x"`                 | `x-init="x"`                 |
| `on:event="x"`                  | `@event="x"`                 |
| `on:event.modifier="x"`         | `@event.modifier="x"`        |

### HTMX (server)

| DSL                    | HTML                    |
| ---------------------- | ----------------------- |
| `action:get="/url"`    | `hx-get="/url"`         |
| `action:post="/url"`   | `hx-post="/url"`        |
| `action:put="/url"`    | `hx-put="/url"`         |
| `action:patch="/url"`  | `hx-patch="/url"`       |
| `action:delete="/url"` | `hx-delete="/url"`      |
| `swap="x"`             | `hx-swap="x"`           |
| `target="x"`           | `hx-target="x"`         |
| `trigger="x"`          | `hx-trigger="x"`        |
| `select="x"`           | `hx-select="x"`         |
| `select-oob="x"`       | `hx-select-oob="x"`     |
| `confirm="x"`          | `hx-confirm="x"`        |
| `indicator="x"`        | `hx-indicator="x"`      |
| `push-url`             | `hx-push-url="true"`    |
| `replace-url`          | `hx-replace-url="true"` |
| `vals='json'`          | `hx-vals='json'`        |
| `headers='json'`       | `hx-headers='json'`     |
| `encoding="x"`         | `hx-encoding="x"`       |
| `preserve`             | `hx-preserve="true"`    |
| `sync="x"`             | `hx-sync="x"`           |
| `disabled-elt="x"`     | `hx-disabled-elt="x"`   |
| `boost`                | `hx-boost="true"`       |

### SSE / WebSocket

| DSL               | HTML                              |
| ----------------- | --------------------------------- |
| `live="/url"`     | `hx-ext="sse" sse-connect="/url"` |
| `channel="event"` | `sse-swap="event"`                |
| `close="event"`   | `sse-close="event"`               |
| `socket="/url"`   | `hx-ext="ws" ws-connect="/url"`   |
| `send="event"`    | `ws-send="event"`                 |

---

## 17. Complete Example — Dashboard

```html
---
import { Card, Badge, Avatar } from "./ui/"
import DataTable from "./DataTable.jinja"
import Chart from "./Chart.jinja"
import Modal from "./Modal.jinja"

props {
  user:    dict,
  stats:   list[dict],
  orders:  list[dict],
  team:    list[dict],
}

slot header
slot sidebar

let total_revenue = sum(o.amount for o in props.orders)
let active_orders = [o for o in props.orders if o.status == "active"]

state selected_order = null
state show_modal = false
state filter = "all"
state search = ""

computed filtered_orders = active_orders if filter == "active" else props.orders
---

<style scoped>
  .dashboard { display: grid; grid-template-columns: 1fr 300px; gap: 1.5rem; }
  .stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
</style>

<div class="dashboard" reactive>

    <!-- Header slot -->
    <Slot:header>
        <header>
            <h1>Dashboard</h1>
            <p>Welcome, {{ props.user.name }}</p>
        </header>
    </Slot:header>

    <!-- Stats with SSE live -->
    <section class="stat-grid" live="/events/stats" channel="stats-update">
        <For each="props.stats" as="stat">
            <Card variant="stat">
                <span class="stat-value">{{ stat.value }}</span>
                <span class="stat-label">{{ stat.label }}</span>
                <Switch on="stat.trend">
                    <Case value="up">
                        <Badge text="↑ {{ stat.delta }}%" variant="success" />
                    </Case>
                    <Case value="down">
                        <Badge text="↓ {{ stat.delta }}%" variant="danger" />
                    </Case>
                    <Default></Default>
                </Switch>
            </Card>
        </For>
    </section>

    <!-- Main content -->
    <main>
        <!-- Search & Filter -->
        <div class="toolbar">
            <input type="search"
                   placeholder="Search orders..."
                   bind:model.debounce.300ms="search"
                   action:get="/api/orders"
                   trigger="input changed delay:300ms"
                   target="#orders-table"
                   swap="innerHTML" />

            <div class="filter-group">
                <For each="['all', 'active', 'completed', 'cancelled']" as="f">
                    <button bind:class="filter === '{{ f }}' && 'active'"
                            on:click="filter = '{{ f }}'"
                            action:get="/api/orders?filter={{ f }}"
                            target="#orders-table"
                            swap="innerHTML">
                        {{ f | capitalize }}
                    </button>
                </For>
            </div>
        </div>

        <!-- Orders Table -->
        <DataTable id="orders-table"
                   rows="{{ filtered_orders }}"
                   searchable="true"
                   paginated="true">
            <slot:empty>
                <p class="empty">No orders found.</p>
            </slot:empty>
        </DataTable>

        <!-- Chart -->
        <Show when="props.orders">
            <Chart type="line"
                   data="{{ props.orders }}"
                   x="date"
                   y="amount"
                   title="Revenue" />
        </Show>
    </main>

    <!-- Sidebar -->
    <aside>
        <Slot:sidebar>
            <h3>Team Online</h3>
            <For each="props.team" as="member">
                <div class="team-member"
                     on:click="selected_order = null"
                     action:get="/api/users/{{ member.id }}"
                     target="#user-detail"
                     swap="innerHTML">
                    <Avatar src="{{ member.avatar }}" size="32" />
                    <span>{{ member.name }}</span>
                    <Switch on="member.status">
                        <Case value="online">
                            <Badge text="●" variant="success" />
                        </Case>
                        <Case value="away">
                            <Badge text="●" variant="warning" />
                        </Case>
                        <Default>
                            <Badge text="●" variant="muted" />
                        </Default>
                    </Switch>
                </div>
            <Empty>
                <p>Nobody online.</p>
            </Empty>
            </For>
            <div id="user-detail"></div>
        </Slot:sidebar>
    </aside>

    <!-- Modal -->
    <Show when="show_modal">
        <Modal title="Order Details">
            <div id="order-detail"
                 live="/events/order"
                 channel="order-update">
                Select an order.
            </div>
            <slot:footer>
                <button on:click="show_modal = false">Close</button>
                <button action:post="/api/orders/approve"
                        swap="none"
                        loading:disabled
                        loading:class="opacity-50">
                    <span loading:hide>Approve</span>
                    <span loading:show>Approving...</span>
                </button>
            </slot:footer>
        </Modal>
    </Show>
</div>
```

---

## 18. Framework Comparison

| Concept     | PJX                     | SolidJS            | Svelte              | Vue                |
| ----------- | ----------------------- | ------------------ | ------------------- | ------------------ |
| Conditional | `<Show when="x">`       | `<Show when={x}>`  | `{#if x}`           | `v-if="x"`         |
| Loop        | `<For each="x" as="i">` | `<For each={x}>`   | `{#each x as i}`    | `v-for="i in x"`   |
| Switch      | `<Switch on="x">`       | `<Switch>/<Match>` | —                   | —                  |
| Slot        | `<Slot:name />`         | `props.children`   | `<slot name="">`    | `<slot name="">`   |
| Slot pass   | `<slot:name>`           | —                  | `<svelte:fragment>` | `<template #name>` |
| Reactivity  | `state x = 0`           | `createSignal()`   | `let x = 0`         | `ref(0)`           |
| Computed    | `computed x = expr`     | `createMemo()`     | `$: x = expr`       | `computed()`       |
| Binding     | `bind:model="x"`        | —                  | `bind:value={x}`    | `v-model="x"`      |
| Event       | `on:click="fn()"`       | `onClick={fn}`     | `on:click={fn}`     | `@click="fn()"`    |
| HTTP        | `action:post="/url"`    | `fetch()`          | `fetch()`           | `axios`            |
| SSE         | `live="/url"`           | custom             | custom              | custom             |
| CSS scoped  | `<style scoped>`        | CSS modules        | `<style>` (auto)    | `<style scoped>`   |

---

## 19. Layouts and Inheritance

PJX supports two layout mechanisms:

1. **Runtime layout** via `PJX(layout=...)` — wraps `{{ body }}` in the template
2. **Template inheritance** via `extends` — static inheritance in frontmatter

### Runtime Layout (`PJX(layout=...)`)

Defined on the PJX instance, the runtime layout automatically wraps all
pages. The rendered content is injected into the `{{ body }}` variable:

```python
from pjx import PJX, PJXConfig, SEO

pjx = PJX(
    app,
    config=PJXConfig(toml_path="pjx.toml"),
    layout="layouts/Base.jinja",
    seo=SEO(title="My App", description="Default description."),
)
```

The layout receives all page context variables, plus:

| Variable       | Type     | Description                    |
| -------------- | -------- | ------------------------------ |
| `body`         | `Markup` | Rendered HTML of the page      |
| `seo`          | `SEO`    | Merged SEO (global + per-page) |
| `head_css`     | `list`   | Extra CSS for `<head>`         |
| `head_scripts` | `list`   | Extra JS for `<head>`          |
| `body_scripts` | `list`   | Extra JS before `</body>`      |
| `favicon`      | `str`    | Favicon path                   |

To disable the layout on a specific page:

```python
@pjx.page("/api-docs", layout=None)
async def api_docs():
    return {"raw": True}
```

### Template Inheritance (`extends`)

Layouts define the base page structure (html, head, body, nav, footer).
Pages inherit from layouts via `extends`.

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

### Page that inherits from the layout

```html
---
extends "layouts/Base.jinja"
from pydantic import EmailStr

props {
  user: dict,
  items: list[dict],
}
---

<slot:head>
    <meta property="og:title" content="Home — {{ props.user.name }}" />
    <link rel="canonical" href="/" />
</slot:head>

<h1>Welcome, {{ props.user.name }}</h1>
<For each="props.items" as="item">
    <p>{{ item.title }}</p>
</For>
```

The page body (outside `<slot:*>`) is automatically injected into the
layout's `<Slot:content />`.

---

## 20. Prop Spreading

Spread a dict as component props.

```html
---
let btn_props = {
  variant: "primary",
  size: "lg",
  disabled: false,
}
---

<!-- Spread all props -->
<Button ...btn_props />

<!-- Spread + override -->
<Button ...btn_props label="Save" disabled="true" />
```

Explicit props take priority over the spread. The spread is resolved at
compile-time if the value is static, or at runtime if dynamic.

| Written                         | Compiled                                                    |
| ------------------------------- | ----------------------------------------------------------- |
| `<Button ...props />`           | Merges `props` with explicit attrs, passes via `{% with %}` |
| `<Button ...props label="x" />` | `label="x"` overrides `props.label`                         |

---

## 21. Global State (Alpine Stores)

### Declare store

```html
---
store todos = {
  items: [],
  filter: "all",
  add(text) { this.items.push({ text, done: false }) },
  toggle(index) { this.items[index].done = !this.items[index].done },
}
---
```

### Use store in components

```html
<div reactive:store="todos">
    <input bind:model="$store.todos.filter" />
    <For each="$store.todos.items" as="item">
        <li>{{ item.text }}</li>
    </For>
</div>
```

| Written                       | Compiled                                           |
| ----------------------------- | -------------------------------------------------- |
| `store name = { ... }`        | `Alpine.store('name', { ... })` in the init script |
| `reactive:store="name"`       | `x-data="Alpine.store('name')"`                    |
| `$store.name.prop`            | Direct access to the Alpine store                  |

Stores are initialized via a `<script>` generated in the base layout, fed
with data from the server.

---

## 22. Built-in Template Functions

Functions available in expressions within the template body:

| Function                | Description                                  |
| ----------------------- | -------------------------------------------- |
| `has_slot('name')`      | `true` if slot `name` was provided by parent |
| `len(x)`                | Length of list/string                        |
| `range(n)`              | Generates sequence 0..n-1                    |
| `enumerate(x)`          | (index, item) pairs                          |
| `url_for('route_name')` | Generates reverse URL for FastAPI route      |
| `static('path')`        | Generates URL for static file                |

```html
<Show when="has_slot('header')">
    <header><Slot:header /></header>
</Show>

<img src="{{ static('images/logo.png') }}" />
<a href="{{ url_for('user_profile', user_id=user.id) }}">Profile</a>
```

---

## 23. Error Pages

### Custom pages

```html
---
extends "layouts/Base.jinja"

props {
  path: str,
}
---

<div class="error-page">
    <h1>404</h1>
    <p>Page <code>{{ props.path }}</code> not found.</p>
    <a href="/">Back to home</a>
</div>
```

### Registration via FastAPI

```python
@pjx.error(404, "errors/404.jinja")
async def not_found(request: Request):
    return {"path": request.url.path}

@pjx.error(500, "errors/500.jinja")
async def server_error(request: Request):
    return {}
```

---

## 24. Recursive Components

Components can import themselves to render tree structures.

```html
---
import TreeNode from "./TreeNode.jinja"

props {
  node: dict,
  depth: int = 0,
  max_depth: int = 10,
}
---

<div class="tree-node" style="margin-left: {{ props.depth * 16 }}px">
    <span>{{ props.node.label }}</span>
    <Show when="props.node.children and props.depth < props.max_depth">
        <For each="props.node.children" as="child">
            <TreeNode
                node="{{ child }}"
                depth="{{ props.depth + 1 }}"
                max_depth="{{ props.max_depth }}" />
        </For>
    </Show>
</div>
```

The compiler detects circular imports and limits depth via
`max_depth` (default: 10). Exceeding the limit raises `CompileError`.

---

## 25. File-Based Routing

PJX supports file system-based routing, inspired by Next.js and
SvelteKit. The `pjx.auto_routes()` method scans the `pages/` directory and
generates FastAPI routes automatically.

### Activation

```python
pjx = PJX(app, config=PJXConfig(toml_path="pjx.toml"))
pjx.auto_routes()
```

### File conventions

| File pattern                   | Generated route                | Description                       |
| ------------------------------ | ------------------------------ | --------------------------------- |
| `pages/index.jinja`            | `/`                            | Root page                         |
| `pages/about.jinja`            | `/about`                       | Static route                      |
| `pages/blog/index.jinja`       | `/blog`                        | Directory index                   |
| `pages/blog/[slug].jinja`      | `/blog/{slug}`                 | Dynamic parameter                 |
| `pages/docs/[...slug].jinja`   | `/docs/{slug:path}`            | Catch-all (variable segments)     |
| `pages/(auth)/login.jinja`     | `/login`                       | Route group (no prefix in URL)    |
| `pages/layout.jinja`           | —                              | Shared layout                     |
| `pages/loading.jinja`          | —                              | Loading skeleton                  |
| `pages/error.jinja`            | —                              | Directory error page              |

### Special files

- **`layout.jinja`** — Automatically wraps all pages and subdirectories
  at the same level. Nested layouts: `pages/layout.jinja` wraps
  `pages/blog/layout.jinja` which wraps `pages/blog/[slug].jinja`.
- **`loading.jinja`** — Skeleton displayed via HTMX `hx-indicator` while the
  page loads.
- **`error.jinja`** — Rendered when a handler returns an error. Receives
  `status_code` and `message` in the context.
- **Route groups `(name)/`** — Directories in parentheses group pages without
  affecting the URL. Useful for applying layouts/middleware to a subset of routes.

### Colocated Handlers

Python handlers can be placed alongside templates using
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

# JSON endpoint served under /api/
api = APIRoute()

@api.get
async def list_items():
    return {"items": await fetch_items()}
```

---

## 26. Middleware

### Declaration in frontmatter

Components and pages can declare middleware:

```html
---
middleware "auth", "rate_limit"
---
```

Accepts one or more comma-separated strings. Each string references a
middleware registered in the PJX runtime.

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
    response = await call_next(request)
    return response
```

Middleware declared in the frontmatter is applied in declaration order.
Layout middleware is applied before page middleware.

---

## 27. Security and Production

### CSRF Protection

PJX includes CSRF middleware based on double-submit cookie with HMAC
signature. Enabled via `csrf=True` in the `PJX` constructor:

```python
pjx = PJX(
    app,
    csrf=True,
    csrf_secret="your-secret-key",
    csrf_exempt_paths={"/api/webhooks", "/sse/clock"},
)
```

The middleware:

1. Generates a signed CSRF token and sets it as a `_csrf` cookie on every response
2. On unsafe methods (POST, PUT, DELETE, PATCH), validates that the token sent
   via `X-CSRFToken` header or `csrf_token` form field matches the cookie
3. Rejects with HTTP 403 if the token does not match or is missing

For HTMX, just add `hx-headers` in the layout:

```html
<body hx-headers='{"X-CSRFToken": "{{ csrf_token() }}"}'>
```

For traditional forms:

```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

### Signed Sessions

Use Starlette's `SessionMiddleware` for signed cookies with
`itsdangerous`. Never store sensitive data in plain-text cookies:

```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ["PJX_SECRET_KEY"],
    session_cookie="session",
    max_age=3600,
    https_only=True,
    same_site="lax",
)
```

Access via `request.session["user"]` in handlers.

### Rate Limiting

Recommended on authentication and mutation endpoints. The example uses `slowapi`:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request): ...
```

### SSE Connection Limits

`EventStream` supports per-IP limits and maximum duration to prevent DoS:

```python
stream = EventStream(
    request,
    max_connections_per_ip=10,
    max_duration=3600,
)
```

Connections beyond the limit receive HTTP 429.

### Health Checks

For container orchestration (Kubernetes, ECS), enable with
`health=True`:

- `/health` — liveness probe (`{"status": "ok"}`)
- `/ready` — readiness probe (verifies that template directories exist)

### CORS

Configured via `pjx.toml`. When `cors_origins` is non-empty, Starlette's
`CORSMiddleware` is registered automatically:

```toml
cors_origins = ["https://example.com"]
cors_methods = ["GET", "POST"]
cors_headers = ["Authorization"]
cors_credentials = true
```

### Structured Logging

For production, enable JSON logging for integration with ELK, Datadog or
CloudWatch:

```toml
log_json = true
log_level = "WARNING"
```

---

## 28. Layout Components (Built-ins)

PJX includes built-in layout components inspired by Chakra UI. They are
compiled directly by the compiler (no import needed).

| Component       | Description                                 | Main props                        |
| --------------- | ------------------------------------------- | --------------------------------- |
| `<Center>`      | Centers content horizontally and vertically | `w`, `h`                          |
| `<HStack>`      | Horizontal stack with gap                   | `gap`, `align`, `justify`, `wrap` |
| `<VStack>`      | Vertical stack with gap                     | `gap`, `align`, `justify`         |
| `<Grid>`        | Responsive CSS grid                         | `cols`, `gap`, `min`, `max`       |
| `<Spacer>`      | Flexible space between items                | —                                 |
| `<Container>`   | Centered maximum width                      | `max`, `px`                       |
| `<Divider>`     | Divider line                                | `orientation`, `color`            |
| `<Wrap>`        | Flex wrap with gap                          | `gap`, `align`, `justify`         |
| `<AspectRatio>` | Maintains content aspect ratio              | `ratio`                           |
| `<Hide>`        | Hides content by breakpoint                 | `below`, `above`                  |

### Example

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

## 29. Frontmatter — Parsing Rules

The frontmatter is delimited by `---` on the **first line** and closed by
the next `---` on an isolated line. Rules:

- `---` must be **alone on the line** (no spaces before/after)
- Strings inside the frontmatter can contain `---` without ambiguity:
  `let x = "foo --- bar"` is valid
- Comments: `#` until end of line (ignored by the lexer)
- Blank lines are ignored
- Multi-line: props blocks (`{ ... }`) can span multiple lines
- The closing `---` marks the beginning of the HTML body + `<style scoped>`

```text
---                       ← opening (line 1 of the file)
import ...
from pydantic import ...
extends "..."
props [Name =] { ... }
slot ...
let/const/state/computed
store ...
css "path/to/style.css"
js "path/to/script.js"
middleware "name", ...
---                       ← closing (next isolated ---)
<style scoped>...</style> ← optional
<div>...</div>            ← HTML body
```

### Assets in Frontmatter

Components can declare CSS and JS dependencies:

```html
---
css "components/card.css"
js "components/card.js"
---
```

Assets are collected recursively (including imports), deduplicated by
`(kind, path)`, and made available in the template via `{{ pjx_assets.render() }}`.
CSS is rendered as `<link>`, JS as `<script type="module">`.
