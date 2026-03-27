# Component Syntax

PJX components are `.jinja` files that combine a declarative frontmatter block
with reactive HTML. This page covers the component format, all frontmatter
keywords, variables, reactivity, and the compilation pipeline.

---

## Anatomy of a Component

Every PJX component has up to three sections in a single `.jinja` file:

```text
 ---                    <-- frontmatter open
 <frontmatter keywords>
 ---                    <-- frontmatter close

 <style scoped>         <-- optional scoped CSS
   ...
 </style>

 <div>                  <-- HTML body (required)
   ...
 </div>
```

### 1. Frontmatter (`---`)

The frontmatter block is delimited by triple dashes at the top of the file.
It declares imports, props, slots, variables, state, and metadata. The
frontmatter is parsed by the PJX compiler and stripped from the final output.

If your component needs no declarations, the frontmatter can be omitted
entirely (see [[Minimal Component|#minimal-component]] below).

### 2. Scoped CSS (`<style scoped>`)

An optional `<style scoped>` block defines CSS that is automatically scoped to
this component. PJX generates a unique attribute (e.g., `data-pjx-abc123`) and
rewrites selectors so they only match elements within the component.

```html
<style scoped>
  .card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; }
  .card h2 { margin: 0 0 0.5rem; }
</style>
```

The compiled output transforms `.card` into `.card[data-pjx-abc123]` and adds
the matching attribute to the component's root element.

### 3. HTML Body

The remaining content is the component's template. It uses standard Jinja2
syntax plus PJX extensions: component tags (`<Button />`), control-flow tags
(`<Show>`, `<For>`, `<Switch>`), and reactive attributes (`reactive`,
`on:click`, `action:post`).

---

## Frontmatter Keywords

PJX defines 13 frontmatter keywords. Each is optional; use only what your
component needs.

| Keyword      | Purpose                                       | Example                                 |
| ------------ | --------------------------------------------- | --------------------------------------- |
| `import`     | Import a `.jinja` component                   | `import Button from "./Button.jinja"`   |
| `from`       | Import Python/Pydantic types                  | `from pydantic import EmailStr`         |
| `extends`    | Inherit from a layout                         | `extends "layouts/Base.jinja"`          |
| `props`      | Declare typed props with optional defaults    | `props { name: str, age: int = 0 }`     |
| `slot`       | Declare a named slot (with optional fallback) | `slot footer = <span>Default</span>`    |
| `store`      | Declare an Alpine.js global store             | `store todos = []`                      |
| `let`        | Server-side mutable variable                  | `let greeting = "Hello, " + props.name` |
| `const`      | Server-side immutable constant                | `const MAX_ITEMS = 50`                  |
| `state`      | Client-side reactive variable (Alpine.js)     | `state count = 0`                       |
| `computed`   | Derived value (recalculates when deps change) | `computed total = len(props.items)`     |
| `css`        | Declare a CSS asset dependency                | `css "components/card.css"`             |
| `js`         | Declare a JS asset dependency                 | `js "components/card.js"`               |
| `middleware` | Attach middleware to the component            | `middleware "auth", "rate_limit"`       |

### `import`

Imports register other `.jinja` files so they can be used as component tags
in the HTML body.

```python
# Single component
import Button from "./Button.jinja"

# With alias
import Button from "./Button.jinja" as PrimaryButton

# Multiple from a directory
import { Card, Badge, Avatar } from "./components/"

# Sub-components from a multi-export file
import { CardHeader, CardBody, CardFooter } from "./Card.jinja"

# Wildcard (all from directory)
import * from "./ui/"
```

### `from`

Imports Python types for use in `props` declarations. Primitive types (`str`,
`int`, `bool`, `float`, `list`, `dict`, `Callable`, `Any`, `None`) are
available automatically.

```python
from typing import Literal, Annotated
from pydantic import EmailStr, HttpUrl
from annotated_types import Gt, Lt, MinLen, MaxLen
```

### `extends`

Declares layout inheritance. The component's body is injected into the
layout's `<Slot:content />`.

```python
extends "layouts/Base.jinja"
```

### `props`

Declares typed, validated properties. See [[Props and Validation]] for the
full reference.

```python
props {
  title: str,
  count: int = 0,
  variant: Literal["primary", "secondary"] = "primary",
}
```

### `slot`

Declares named content insertion points. See [[Slots]] for the full reference.

```python
slot header
slot footer = <span>Default footer</span>
```

### `store`

Registers an Alpine.js global store, accessible from any component via
`$store.name`.

```python
store todos = []
store theme = { mode: "light", accent: "blue" }
```

### `let` / `const`

Server-side variables evaluated during Jinja2 rendering.

```python
let css_class = "card card--" + props.variant
let item_count = len(props.items)

const MAX_LENGTH = 140
const API_URL = "/api/v1"
```

### `state`

Client-side reactive variables powered by Alpine.js. Requires the `reactive`
attribute on the target element.

```python
state count = 0
state editing = false
state search = ""
state selected = []
state form = { name: "", email: "" }
```

### `computed`

Derived values that recalculate when their dependencies change. On the server
side, these compile to Jinja2 `{% set %}` blocks.

```python
computed total = len(props.items)
computed done_count = len([i for i in props.items if i.done])
computed progress = (done_count / total * 100) if total > 0 else 0
```

### `css` / `js`

Declare external asset dependencies. PJX collects these across the component
tree, deduplicates them, and renders `<link>` / `<script>` tags via
`{{ pjx_assets.render() }}` in your layout.

```python
css "components/card.css"
js "components/card.js"
```

### `middleware`

Attach named middleware to the component. Middleware handlers are registered
in the PJX runtime and run in declaration order.

```python
middleware "auth", "rate_limit"
```

---

## Minimal Component

A component with no frontmatter is valid. It is just HTML (with Jinja2
expressions):

```html
<footer class="site-footer">
  <p>Built with PJX.</p>
</footer>
```

No `---` delimiters needed. PJX treats any `.jinja` file without frontmatter
as a plain template component.

---

## Variables

PJX provides four variable types, each with different scope and compilation
targets.

### `let` -- Server-Side Mutable

Evaluated once at render time on the server. Available in Jinja2 expressions.

```python
let greeting = "Hello, " + props.name
let css_class = "todo-" + props.priority
```

### `const` -- Server-Side Immutable

Same as `let` at runtime (Jinja2 has no enforcement of immutability), but
signals intent that the value should not change.

```python
const MAX_ITEMS = 50
const API_URL = "/api/v1"
```

### `state` -- Client-Side Reactive

Creates a reactive Alpine.js variable. The initial value is rendered
server-side for SSR, then hydrated by Alpine on the client.

```python
state count = 0
state open = false
state search = ""
```

### `computed` -- Derived Value

Calculates a value from other variables. On the server, this is a standard
Jinja2 `{% set %}`.

```python
computed remaining = MAX_LENGTH - len(props.text)
computed is_valid = remaining >= 0
```

### Compilation Table

| Declaration             | Server (Jinja2)          | Client (Alpine.js)           |
| ----------------------- | ------------------------ | ---------------------------- |
| `let x = 1`             | `{% set x = 1 %}`        | --                           |
| `const X = 1`           | `{% set X = 1 %}`        | --                           |
| `state count = 0`       | `{{ count }}` for SSR    | `x-data` includes `count: 0` |
| `computed total = expr` | `{% set total = expr %}` | --                           |

Server-side variables (`let`, `const`, `computed`) are resolved during Jinja2
rendering and do not exist in the browser. Client-side `state` variables are
injected into Alpine.js `x-data` and can be referenced with Alpine directives
such as `x-text`, `x-show`, and `@click`.

---

## The `reactive` Attribute

The `reactive` attribute enables Alpine.js on an element. When PJX encounters
`reactive` on an HTML element, it compiles it into `x-data="{ ... }"` where
the object contains all `state` variables declared in the frontmatter.

### Syntax

```html
<div class="counter" reactive>
  <span x-text="count">0</span>
</div>
```

### Compiled Output

Given `state count = 0` in the frontmatter, the above compiles to:

```html
<div class="counter" x-data="{ count: 0 }">
  <span x-text="count">0</span>
</div>
```

### When to Use

Add `reactive` to any element that needs to:

- Display or update `state` variables
- Handle Alpine.js events (`on:click`, `bind:model`)
- Use Alpine directives (`x-show`, `x-text`, `x-transition`)

You only need `reactive` on the outermost element that contains reactive
behavior. Alpine.js scopes propagate to all child elements automatically.

### Multiple Reactive Scopes

A single component can have multiple `reactive` elements, each with its own
isolated Alpine scope:

```html
---
state count = 0
state search = ""
---

<div class="counter" reactive>
  <button on:click="count++">+</button>
  <span x-text="count">0</span>
</div>

<div class="search" reactive>
  <input bind:model="search" placeholder="Search..." />
  <span x-text="search"></span>
</div>
```

---

## Reactive Attributes Reference

PJX provides shorthand attributes that compile to Alpine.js and HTMX:

| PJX Attribute       | Compiles To             | Framework |
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

The `into=` shorthand combines target and swap in a single attribute:

```html
<button into="#result">              <!-- hx-target="#result" hx-swap="innerHTML" -->
<button into="#result:outerHTML">    <!-- hx-target="#result" hx-swap="outerHTML" -->
```

---

## Full Component Example

A complete `TodoItem` component demonstrating props, state, slots, scoped CSS,
and HTMX actions:

```html
---
import Badge from "../shared/Badge.jinja"

from typing import Literal

props {
  id:       int,
  text:     str,
  done:     bool      = false,
  priority: Literal["high", "medium", "low"] = "medium",
}

slot actions

let css_class = "todo todo--" + props.priority

state editing = false
state hover = false

const MAX_LENGTH = 140
computed remaining = MAX_LENGTH - len(props.text)
---

<style scoped>
  .todo {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    border-radius: 6px;
    transition: background 0.15s;
  }
  .todo:hover { background: #f8f9fa; }
  .todo--high { border-left: 3px solid #e74c3c; }
  .todo--medium { border-left: 3px solid #f39c12; }
  .todo--low { border-left: 3px solid #2ecc71; }
  .todo__text--done { text-decoration: line-through; opacity: 0.6; }
  .todo__actions { margin-left: auto; display: flex; gap: 0.5rem; }
  .todo__chars { font-size: 0.75rem; color: #999; }
</style>

<li id="todo-{{ props.id }}"
    class="{{ css_class }}"
    reactive
    on:mouseenter="hover = true"
    on:mouseleave="hover = false">

  <input type="checkbox"
         bind:model="done"
         action:post="/htmx/todos/{{ props.id }}/toggle"
         target="#todo-{{ props.id }}"
         swap="outerHTML" />

  <Show when="not editing">
    <span class="todo__text {{ 'todo__text--done' if props.done else '' }}"
          on:dblclick="editing = true">
      {{ props.text }}
    </span>
  </Show>

  <Show when="editing">
    <input type="text"
           value="{{ props.text }}"
           on:keydown.enter="editing = false"
           on:blur="editing = false"
           action:post="/htmx/todos/{{ props.id }}/update"
           target="#todo-{{ props.id }}"
           swap="outerHTML" />
  </Show>

  <Badge text="{{ props.priority }}" />

  <span class="todo__chars" x-show="hover">
    {{ remaining }} chars left
  </span>

  <div class="todo__actions">
    <Slot:actions>
      <button action:post="/htmx/todos/{{ props.id }}/delete"
              target="#todo-{{ props.id }}"
              swap="outerHTML">
        Delete
      </button>
    </Slot:actions>
  </div>
</li>
```

### What This Component Demonstrates

- **`props`** with types, defaults, and `Literal` for constrained values
- **`slot actions`** with a fallback delete button
- **`let`** for a computed CSS class string
- **`state`** for client-side `editing` and `hover` tracking
- **`const`** and **`computed`** for derived character count
- **`reactive`** to enable Alpine.js on the root `<li>`
- **`on:mouseenter`** / **`on:mouseleave`** for Alpine event handling
- **`bind:model`** for two-way binding on the checkbox
- **`action:post`** / **`target`** / **`swap`** for HTMX server mutations
- **`<Show>`** for conditional rendering
- **`<Badge />`** as an imported child component
- **`<style scoped>`** for component-scoped CSS

---

## How Compilation Works

The PJX compiler transforms `.jinja` component files through a multi-stage
pipeline:

```text
  .jinja source
       |
       v
  1. Lexer         -- tokenizes frontmatter and HTML body
       |
       v
  2. Parser        -- builds an AST (Abstract Syntax Tree)
       |
       v
  3. Compiler      -- transforms AST nodes into output
       |
       v
  4. Output        -- Jinja2 template + Alpine.js + HTMX attributes
```

### Stage 1: Lexing

The lexer splits the source into tokens: frontmatter keywords (`import`,
`props`, `state`, etc.), HTML tags, PJX component tags (uppercase names like
`<Button>`), control-flow tags (`<Show>`, `<For>`, `<Switch>`), and reactive
attributes.

### Stage 2: Parsing

The parser consumes tokens and produces an AST. Frontmatter declarations
become prop definitions, variable declarations, slot registrations, and import
nodes. The HTML body becomes a tree of element nodes, text nodes, and
expression nodes.

### Stage 3: Compilation

Each AST node is compiled to its output form:

| AST Node            | Compiled Output                                        |
| ------------------- | ------------------------------------------------------ |
| `import`            | Registers component, loads template                    |
| `props { ... }`     | Generates Pydantic `BaseModel` class                   |
| `let x = expr`      | `{% set x = expr %}`                                   |
| `const X = expr`    | `{% set X = expr %}`                                   |
| `state x = val`     | Injected into `x-data` object                          |
| `computed x = expr` | `{% set x = expr %}`                                   |
| `slot name`         | `{{ _slot_name \| default('') }}`                      |
| `<Component />`     | `{% include "path/to/Component.jinja" %}`              |
| `<Show when="x">`   | `{% if x %}`                                           |
| `<For each="x">`    | `{% for item in x %}`                                  |
| `<Switch on="x">`   | `{% set _sw = x %}` + `{% if %}` / `{% elif %}` chain  |
| `reactive`          | `x-data="{ state_vars }"` on the element               |
| `on:click="..."`    | `@click="..."`                                         |
| `action:post="..."` | `hx-post="..."`                                        |

### Stage 4: Output

The final output is a standard Jinja2 template with Alpine.js `x-data`
attributes and HTMX `hx-*` attributes. This template is rendered by the
configured engine (Jinja2, MiniJinja, or HybridEngine).

### Render Modes

PJX supports two render modes that affect how compiled templates reference
each other:

| Mode      | Behavior                                                     |
| --------- | ------------------------------------------------------------ |
| `include` | Components use `{% include %}` (standard Jinja2, default)    |
| `inline`  | All includes are flattened into a single template at compile |

Inline mode eliminates `{% include %}` overhead, enabling MiniJinja's
`render_string` path which is 10-74x faster than Jinja2 for ad-hoc
compilation.

For the complete compilation tables, see [[Compilation Reference]].

---

## See Also

- [[Props and Validation]] -- declaring, typing, and validating component props
- [[Slots]] -- named slots, fallbacks, and slot passing
- [[State and Reactivity]] -- Alpine.js state, stores, and reactive patterns
- [[Control Flow]] -- `<Show>`, `<For>`, `<Switch>`, `<Portal>` tags
