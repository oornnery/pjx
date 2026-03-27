# Compilation Reference

Complete reference of what PJX DSL syntax compiles to. Each section maps PJX
input to its Jinja2, Alpine.js, or HTMX output.

---

## Frontmatter Variables

Variables declared in the `---` frontmatter block.

| PJX                                        | Server (Jinja2)                             | Client (Alpine.js)                                | Notes                                                  |
| ------------------------------------------ | ------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------ |
| `let x = val`                              | `{% set x = val %}`                         | --                                                | Local variable, available in template body             |
| `const X = val`                            | `{% set X = val %}`                         | --                                                | Same as `let` at compile time; immutable by convention |
| `state count = 0`                          | `{{ count }}` for SSR                       | `x-data` includes `count: 0`                      | Requires `reactive` on an element to generate `x-data` |
| `state open = false`                       | `{{ open }}` for SSR                        | `x-data` includes `open: false`                   | Boolean state                                          |
| `state items = []`                         | `{{ items }}` for SSR                       | `x-data` includes `items: []`                     | Array state                                            |
| `state form = { name: "", email: "" }`     | `{{ form }}` for SSR                        | `x-data` includes `form: { name: "", email: "" }` | Object state                                           |
| `computed total = expr`                    | `{% set total = expr %}`                    | --                                                | Server-side derived value                              |
| `computed progress = (done / total * 100)` | `{% set progress = (done / total * 100) %}` | --                                                | Expressions evaluated at render time                   |

### Store declarations

| PJX                                | Output                                      | Notes                                              |
| ---------------------------------- | ------------------------------------------- | -------------------------------------------------- |
| `store todos = { items: [], ... }` | `Alpine.store('todos', { items: [], ... })` | Global Alpine store, accessible via `$store.todos` |
| `reactive:store="todos"`           | `x-data="Alpine.store('todos')"`            | Binds element to a named store                     |

---

## Control Flow

PJX control flow tags compile to Jinja2 template logic.

### Show (conditionals)

| PJX                                                         | Jinja2                                                     |
| ----------------------------------------------------------- | ---------------------------------------------------------- |
| `<Show when="x">body</Show>`                                | `{% if x %}body{% endif %}`                                |
| `<Show when="x" fallback="fb">body</Show>`                  | `{% if x %}body{% else %}fb{% endif %}`                    |
| `<Show when="x"><Else>alt</Else></Show>`                    | `{% if x %}...{% else %}alt{% endif %}`                    |
| `<Show when="not loading">body</Show>`                      | `{% if not loading %}body{% endif %}`                      |
| `<Show when="user.age >= 18 and user.verified">body</Show>` | `{% if user.age >= 18 and user.verified %}body{% endif %}` |

### For (iteration)

| PJX                                                              | Jinja2                                                            |
| ---------------------------------------------------------------- | ----------------------------------------------------------------- |
| `<For each="users" as="user">body</For>`                         | `{% for user in users %}body{% endfor %}`                         |
| `<For each="items" as="item">body<Empty>fb</Empty></For>`        | `{% for item in items %}body{% else %}fb{% endfor %}`             |
| `<For each="users \| selectattr('active')" as="user">body</For>` | `{% for user in users \| selectattr('active') %}body{% endfor %}` |

#### Loop variables (inherited from Jinja2)

| Variable               | Description                |
| ---------------------- | -------------------------- |
| `loop.index`           | Current iteration, 1-based |
| `loop.index0`          | Current iteration, 0-based |
| `loop.first`           | `true` if first iteration  |
| `loop.last`            | `true` if last iteration   |
| `loop.length`          | Total number of items      |
| `loop.cycle('a', 'b')` | Alternates between values  |

### Switch / Case / Default (multi-branch)

| PJX                                        | Jinja2                      |
| ------------------------------------------ | --------------------------- |
| `<Switch on="x">`                          | `{% set _sw = x %}`         |
| `<Case value="a">body</Case>` (first)      | `{% if _sw == "a" %}body`   |
| `<Case value="b">body</Case>` (subsequent) | `{% elif _sw == "b" %}body` |
| `<Default>body</Default>`                  | `{% else %}body`            |
| `</Switch>`                                | `{% endif %}`               |

### Fragment

| PJX                         | Output |
| --------------------------- | ------ |
| `<Fragment>body</Fragment>` | `body` |

Fragment renders its children without generating a wrapper DOM element.

### ErrorBoundary

| PJX                                                                  | Output                                          |
| -------------------------------------------------------------------- | ----------------------------------------------- |
| `<ErrorBoundary fallback="fb">body</ErrorBoundary>`                  | `try/except` wrapper that renders `fb` on error |
| `<ErrorBoundary><slot:error>custom</slot:error>body</ErrorBoundary>` | `try/except` wrapper with custom error template |

### Portal (out-of-band swap)

| PJX                                                  | HTML                                              |
| ---------------------------------------------------- | ------------------------------------------------- |
| `<Portal target="id">body</Portal>`                  | `<div id="id" hx-swap-oob="true">body</div>`      |
| `<Portal target="id" swap="outerHTML">body</Portal>` | `<div id="id" hx-swap-oob="outerHTML">body</div>` |

### Await (async loading)

| PJX                                     | HTML                                                        |
| --------------------------------------- | ----------------------------------------------------------- |
| `<Await src="/url" trigger="load">`     | `<div hx-get="/url" hx-trigger="load" hx-swap="innerHTML">` |
| `<slot:loading>skeleton</slot:loading>` | Skeleton content shown before response                      |
| `<slot:error>error msg</slot:error>`    | Error content on failure                                    |

### Component

| PJX                                    | Effect                                                            |
| -------------------------------------- | ----------------------------------------------------------------- |
| `<Button label="Save" />`              | `{% include "Button.jinja" %}` with props passed via `{% with %}` |
| `<Component is="{{ widget_type }}" />` | Dynamic include resolved at render time                           |
| `<Button ...btn_props />`              | Spreads `btn_props` dict as props                                 |
| `<Button ...btn_props label="x" />`    | Spread with explicit override (`label="x"` wins)                  |

### Transition

| PJX                                             | HTML                                                                      |
| ----------------------------------------------- | ------------------------------------------------------------------------- |
| `<Transition enter="fade-in" leave="fade-out">` | Wrapper with `x-transition:enter="fade-in" x-transition:leave="fade-out"` |

---

## Slots

### Slot declaration (frontmatter)

| PJX                                  | Effect                                      |
| ------------------------------------ | ------------------------------------------- |
| `slot header`                        | Declares a named slot with no fallback      |
| `slot footer = <span>Default</span>` | Declares a named slot with fallback content |

### Slot rendering (template body)

| PJX                                   | Jinja2                                                                 |
| ------------------------------------- | ---------------------------------------------------------------------- |
| `<Slot:header />`                     | `{{ _slot_header \| default('') }}`                                    |
| `<Slot:header>fallback</Slot:header>` | `{% if _slot_header %}{{ _slot_header }}{% else %}fallback{% endif %}` |
| `<Slot />`                            | `{{ _slot_default \| default('') }}`                                   |

### Slot passing (parent to child)

| PJX                                               | Effect                                   |
| ------------------------------------------------- | ---------------------------------------- |
| `<Card>children</Card>`                           | Children become the default slot content |
| `<Card><slot:header>content</slot:header></Card>` | Named slot passed to child component     |
| `<Card><slot:footer>content</slot:footer></Card>` | Named slot passed to child component     |

### Slot conditional

| PJX                                | Jinja2                  |
| ---------------------------------- | ----------------------- |
| `<Show when="has_slot('header')">` | `{% if _slot_header %}` |

---

## Imports

### Component imports

| PJX                                                   | Effect                                                |
| ----------------------------------------------------- | ----------------------------------------------------- |
| `import Button from "./Button.jinja"`                 | Registers `Button`, loads template from relative path |
| `import Button from "./Button.jinja" as Btn`          | Registers as `Btn` (alias)                            |
| `import { Card, Badge } from "./ui/"`                 | Loads `ui/Card.jinja` and `ui/Badge.jinja`            |
| `import { CardHeader, CardBody } from "./Card.jinja"` | Imports sub-components from a multi-export file       |
| `import * from "./ui/"`                               | Loads all `.jinja` files from the directory           |

### Type imports

| PJX                                      | Effect                                       |
| ---------------------------------------- | -------------------------------------------- |
| `from typing import Literal, Annotated`  | Makes types available in `props {}`          |
| `from pydantic import EmailStr, HttpUrl` | Makes Pydantic types available in `props {}` |
| `from annotated_types import Gt, Lt`     | Makes constraints available for `Annotated`  |

### Layout inheritance

| PJX                            | Effect                                                           |
| ------------------------------ | ---------------------------------------------------------------- |
| `extends "layouts/Base.jinja"` | Page inherits from layout; body injected into `<Slot:content />` |

### Component rendering

| PJX                            | Jinja2                                                                               |
| ------------------------------ | ------------------------------------------------------------------------------------ |
| `<Button label="Save" />`      | `{% with label="Save" %}{% include "Button.jinja" %}{% endwith %}`                   |
| `<Card title="Hi">body</Card>` | `{% with title="Hi", _slot_default="body" %}{% include "Card.jinja" %}{% endwith %}` |

---

## Alpine.js (Client-Side)

### Reactive initialization

| PJX                                | HTML                                                                    |
| ---------------------------------- | ----------------------------------------------------------------------- |
| `reactive`                         | `x-data="{{ alpine_data }}"` (auto-generated from `state` declarations) |
| `reactive="{ count: 0 }"`          | `x-data="{ count: 0 }"`                                                 |
| `reactive="{ x: 0, open: false }"` | `x-data="{ x: 0, open: false }"`                                        |
| `reactive:store="todos"`           | `x-data="Alpine.store('todos')"`                                        |

### Data binding (bind:*)

| PJX                                   | HTML                              | Alpine directive              |
| ------------------------------------- | --------------------------------- | ----------------------------- |
| `bind:text="count"`                   | `x-text="count"`                  | Text content                  |
| `bind:html="richContent"`             | `x-html="richContent"`            | Inner HTML                    |
| `bind:show="isVisible"`               | `x-show="isVisible"`              | Toggle visibility             |
| `bind:model="name"`                   | `x-model="name"`                  | Two-way binding               |
| `bind:model.lazy="email"`             | `x-model.lazy="email"`            | Sync on change (not input)    |
| `bind:model.number="age"`             | `x-model.number="age"`            | Cast to number                |
| `bind:model.debounce.500ms="search"`  | `x-model.debounce.500ms="search"` | Debounced binding             |
| `bind:class="{ 'active': isActive }"` | `:class="{ 'active': isActive }"` | Dynamic class                 |
| `bind:style="{ color: textColor }"`   | `:style="{ color: textColor }"`   | Dynamic style                 |
| `bind:src="imageUrl"`                 | `:src="imageUrl"`                 | Dynamic attribute             |
| `bind:href="link"`                    | `:href="link"`                    | Dynamic attribute             |
| `bind:disabled="!isValid"`            | `:disabled="!isValid"`            | Dynamic attribute             |
| `bind:id="'item-' + id"`              | `:id="'item-' + id"`              | Dynamic attribute             |
| `bind:{attr}="expr"`                  | `:{attr}="expr"`                  | Any dynamic attribute         |
| `bind:cloak`                          | `x-cloak`                         | Hide until Alpine initializes |
| `bind:ref="searchInput"`              | `x-ref="searchInput"`             | Element reference             |
| `bind:transition`                     | `x-transition`                    | Transition                    |
| `bind:transition.opacity`             | `x-transition.opacity`            | Opacity transition            |
| `bind:transition.duration.500ms`      | `x-transition.duration.500ms`     | Timed transition              |
| `bind:init="fetchData()"`             | `x-init="fetchData()"`            | Run on initialization         |

### Event handlers (on:*)

| PJX                                  | HTML                               |
| ------------------------------------ | ---------------------------------- |
| `on:click="count++"`                 | `@click="count++"`                 |
| `on:click="handleClick()"`           | `@click="handleClick()"`           |
| `on:submit.prevent="save()"`         | `@submit.prevent="save()"`         |
| `on:click.prevent.stop="navigate()"` | `@click.prevent.stop="navigate()"` |
| `on:click.outside="open = false"`    | `@click.outside="open = false"`    |
| `on:keydown.enter="submit()"`        | `@keydown.enter="submit()"`        |
| `on:keydown.escape="cancel()"`       | `@keydown.escape="cancel()"`       |
| `on:scroll.window="handleScroll()"`  | `@scroll.window="handleScroll()"`  |
| `on:click.throttle.500ms="save()"`   | `@click.throttle.500ms="save()"`   |
| `on:input.debounce.300ms="search()"` | `@input.debounce.300ms="search()"` |
| `on:click.once="init()"`             | `@click.once="init()"`             |
| `on:click.self="close()"`            | `@click.self="close()"`            |

#### Event modifier reference

| Modifier        | Effect                                             |
| --------------- | -------------------------------------------------- |
| `.prevent`      | `event.preventDefault()`                           |
| `.stop`         | `event.stopPropagation()`                          |
| `.outside`      | Fires when clicking outside the element            |
| `.window`       | Listens on `window` instead of the element         |
| `.document`     | Listens on `document` instead of the element       |
| `.once`         | Fires only once, then removes listener             |
| `.self`         | Only fires if `event.target` is the element itself |
| `.throttle.Nms` | Throttle handler to once per N milliseconds        |
| `.debounce.Nms` | Debounce handler by N milliseconds                 |
| `.enter`        | Key modifier: Enter key                            |
| `.escape`       | Key modifier: Escape key                           |
| `.space`        | Key modifier: Space key                            |
| `.tab`          | Key modifier: Tab key                              |
| `.arrow-up`     | Key modifier: Arrow Up                             |
| `.arrow-down`   | Key modifier: Arrow Down                           |

---

## HTMX (Server-Side)

### HTTP verbs (action:*)

| PJX                    | HTML               |
| ---------------------- | ------------------ |
| `action:get="/url"`    | `hx-get="/url"`    |
| `action:post="/url"`   | `hx-post="/url"`   |
| `action:put="/url"`    | `hx-put="/url"`    |
| `action:patch="/url"`  | `hx-patch="/url"`  |
| `action:delete="/url"` | `hx-delete="/url"` |

### Swap modes

| PJX                  | HTML                    | Effect                              |
| -------------------- | ----------------------- | ----------------------------------- |
| `swap="innerHTML"`   | `hx-swap="innerHTML"`   | Replace target's children (default) |
| `swap="outerHTML"`   | `hx-swap="outerHTML"`   | Replace the entire target element   |
| `swap="beforebegin"` | `hx-swap="beforebegin"` | Insert before the target            |
| `swap="afterbegin"`  | `hx-swap="afterbegin"`  | Insert as first child               |
| `swap="beforeend"`   | `hx-swap="beforeend"`   | Insert as last child                |
| `swap="afterend"`    | `hx-swap="afterend"`    | Insert after the target             |
| `swap="delete"`      | `hx-swap="delete"`      | Remove the target element           |
| `swap="none"`        | `hx-swap="none"`        | No swap (fire-and-forget)           |

#### Swap modifiers

| PJX                                  | HTML                                    |
| ------------------------------------ | --------------------------------------- |
| `swap="innerHTML transition:true"`   | `hx-swap="innerHTML transition:true"`   |
| `swap="innerHTML settle:300ms"`      | `hx-swap="innerHTML settle:300ms"`      |
| `swap="innerHTML scroll:top"`        | `hx-swap="innerHTML scroll:top"`        |
| `swap="innerHTML show:top"`          | `hx-swap="innerHTML show:top"`          |
| `swap="innerHTML focus-scroll:true"` | `hx-swap="innerHTML focus-scroll:true"` |

### Target selectors

| PJX                       | HTML                         |
| ------------------------- | ---------------------------- |
| `target="#result"`        | `hx-target="#result"`        |
| `target="closest li"`     | `hx-target="closest li"`     |
| `target="next .panel"`    | `hx-target="next .panel"`    |
| `target="previous .item"` | `hx-target="previous .item"` |
| `target="find .content"`  | `hx-target="find .content"`  |

### Trigger events

| PJX                                      | HTML                                        |
| ---------------------------------------- | ------------------------------------------- |
| `trigger="load"`                         | `hx-trigger="load"`                         |
| `trigger="revealed"`                     | `hx-trigger="revealed"`                     |
| `trigger="intersect"`                    | `hx-trigger="intersect"`                    |
| `trigger="every 5s"`                     | `hx-trigger="every 5s"`                     |
| `trigger="input changed delay:300ms"`    | `hx-trigger="input changed delay:300ms"`    |
| `trigger="submit"`                       | `hx-trigger="submit"`                       |
| `trigger="click[ctrlKey]"`               | `hx-trigger="click[ctrlKey]"`               |
| `trigger="load once"`                    | `hx-trigger="load once"`                    |
| `trigger="click throttle:1s"`            | `hx-trigger="click throttle:1s"`            |
| `trigger="click queue:first"`            | `hx-trigger="click queue:first"`            |
| `trigger="click from:#other-button"`     | `hx-trigger="click from:#other-button"`     |
| `trigger="load, click, keyup from:body"` | `hx-trigger="load, click, keyup from:body"` |

### Into (shorthand for target + swap)

| PJX                        | HTML                                      |
| -------------------------- | ----------------------------------------- |
| `into="#result"`           | `hx-target="#result" hx-swap="innerHTML"` |
| `into="#result:outerHTML"` | `hx-target="#result" hx-swap="outerHTML"` |

### Other HTMX attributes

| PJX                              | HTML                                |
| -------------------------------- | ----------------------------------- |
| `select=".content"`              | `hx-select=".content"`              |
| `select-oob="#sidebar"`          | `hx-select-oob="#sidebar"`          |
| `confirm="Are you sure?"`        | `hx-confirm="Are you sure?"`        |
| `indicator="#spinner"`           | `hx-indicator="#spinner"`           |
| `push-url`                       | `hx-push-url="true"`                |
| `push-url="/path"`               | `hx-push-url="/path"`               |
| `replace-url`                    | `hx-replace-url="true"`             |
| `vals='{"key": "value"}'`        | `hx-vals='{"key": "value"}'`        |
| `headers='{"X-Custom": "v"}'`    | `hx-headers='{"X-Custom": "v"}'`    |
| `encoding="multipart/form-data"` | `hx-encoding="multipart/form-data"` |
| `preserve`                       | `hx-preserve="true"`                |
| `sync="closest form:abort"`      | `hx-sync="closest form:abort"`      |
| `disabled-elt="this"`            | `hx-disabled-elt="this"`            |
| `boost`                          | `hx-boost="true"`                   |

---

## SSE / WebSocket

### Server-Sent Events

| PJX                                        | HTML                                           | Notes                            |
| ------------------------------------------ | ---------------------------------------------- | -------------------------------- |
| `live="/events/dashboard"`                 | `hx-ext="sse" sse-connect="/events/dashboard"` | Opens SSE connection             |
| `channel="user-count"`                     | `sse-swap="user-count"`                        | Swaps content on named event     |
| `channel="notifications" swap="beforeend"` | `sse-swap="notifications" hx-swap="beforeend"` | SSE swap with custom swap mode   |
| `close="closeChat"`                        | `sse-close="closeChat"`                        | Closes connection on named event |

### WebSocket

| PJX                 | HTML                                | Notes                          |
| ------------------- | ----------------------------------- | ------------------------------ |
| `socket="/ws/chat"` | `hx-ext="ws" ws-connect="/ws/chat"` | Opens WebSocket connection     |
| `send="message"`    | `ws-send="message"`                 | Sends form data on named event |

---

## Loading States

| PJX                                      | HTML                              | Effect                                         |
| ---------------------------------------- | --------------------------------- | ---------------------------------------------- |
| `loading`                                | Adds `htmx-indicator` class       | Marks element as a loading indicator           |
| `loading:show`                           | Element visible during request    | Hidden by default, shown during HTMX request   |
| `loading:hide`                           | Element hidden during request     | Visible by default, hidden during HTMX request |
| `loading:class="opacity-50 cursor-wait"` | Adds classes during request       | Classes added when request is in flight        |
| `loading:disabled`                       | `disabled` during request         | Disables element while request is pending      |
| `loading:aria-busy="true"`               | `aria-busy="true"` during request | Accessibility attribute during loading         |
| `disabled-elt="this"`                    | `hx-disabled-elt="this"`          | HTMX native disable during request             |
| `indicator="#spinner"`                   | `hx-indicator="#spinner"`         | Shows the referenced indicator element         |

---

## CSS Scoping

When a component contains `<style scoped>`, PJX scopes the styles to that
component.

### Compilation steps

1. **Hash generation** -- a short hash is computed from the component file
   path (e.g., `pjx-a1b2c3`).

2. **Attribute injection** -- the component's root element receives a
   `data-pjx-a1b2c3` attribute.

3. **Selector rewriting** -- every CSS selector in the `<style scoped>` block
   is rewritten to include the scoping attribute.

### Example

**Input:**

```html
<style scoped>
  .alert { padding: 1rem; }
  .alert-success { background: #d1fae5; }
</style>

<div class="alert alert-{{ props.type }}">
    {{ children }}
</div>
```

**Compiled HTML:**

```html
<div class="alert alert-info" data-pjx-a1b2c3>
    Content here
</div>
```

**Compiled CSS:**

```css
.alert[data-pjx-a1b2c3] { padding: 1rem; }
.alert-success[data-pjx-a1b2c3] { background: #d1fae5; }
```

### CSS bundling

`pjx build` collects all scoped styles and writes a single bundled file at
`static/css/pjx-components.css`. Include it in the base layout:

```html
<link rel="stylesheet" href="/static/css/pjx-components.css" />
```

---

## Framework Comparison

Side-by-side comparison of PJX with SolidJS, Svelte, and Vue.

### Conditionals

| Framework | Syntax                       |
| --------- | ---------------------------- |
| PJX       | `<Show when="x">body</Show>` |
| SolidJS   | `<Show when={x}>body</Show>` |
| Svelte    | `{#if x}body{/if}`           |
| Vue       | `<div v-if="x">body</div>`   |

### Loops

| Framework | Syntax                                     |
| --------- | ------------------------------------------ |
| PJX       | `<For each="items" as="item">body</For>`   |
| SolidJS   | `<For each={items}>{(item) => body}</For>` |
| Svelte    | `{#each items as item}body{/each}`         |
| Vue       | `<div v-for="item in items">body</div>`    |

### Multi-branch

| Framework | Syntax                                               |
| --------- | ---------------------------------------------------- |
| PJX       | `<Switch on="x"><Case value="a">A</Case></Switch>`   |
| SolidJS   | `<Switch><Match when={x === "a"}>A</Match></Switch>` |
| Svelte    | `{#if x === "a"}A{:else if x === "b"}B{/if}`         |
| Vue       | `v-if` / `v-else-if` / `v-else` chain                |

### State

| Framework | Syntax                                      |
| --------- | ------------------------------------------- |
| PJX       | `state count = 0`                           |
| SolidJS   | `const [count, setCount] = createSignal(0)` |
| Svelte    | `let count = 0`                             |
| Vue       | `const count = ref(0)`                      |

### Computed

| Framework | Syntax                                 |
| --------- | -------------------------------------- |
| PJX       | `computed total = expr`                |
| SolidJS   | `const total = createMemo(() => expr)` |
| Svelte    | `$: total = expr`                      |
| Vue       | `const total = computed(() => expr)`   |

### Binding

| Framework | Syntax                     |
| --------- | -------------------------- |
| PJX       | `bind:model="name"`        |
| SolidJS   | Manual `value` + `onInput` |
| Svelte    | `bind:value={name}`        |
| Vue       | `v-model="name"`           |

### Events

| Framework | Syntax                 |
| --------- | ---------------------- |
| PJX       | `on:click="handler()"` |
| SolidJS   | `onClick={handler}`    |
| Svelte    | `on:click={handler}`   |
| Vue       | `@click="handler()"`   |

### HTTP requests

| Framework | Syntax                                   |
| --------- | ---------------------------------------- |
| PJX       | `action:post="/url"` (HTMX, declarative) |
| SolidJS   | `fetch()` (imperative)                   |
| Svelte    | `fetch()` (imperative)                   |
| Vue       | `axios` / `fetch()` (imperative)         |

### Server-Sent Events

| Framework | Syntax                                          |
| --------- | ----------------------------------------------- |
| PJX       | `live="/url"` + `channel="event"` (declarative) |
| SolidJS   | `new EventSource()` (manual)                    |
| Svelte    | `new EventSource()` (manual)                    |
| Vue       | `new EventSource()` (manual)                    |

### Slots

| Framework | Declare           | Pass                             |
| --------- | ----------------- | -------------------------------- |
| PJX       | `<Slot:name />`   | `<slot:name>content</slot:name>` |
| SolidJS   | `props.children`  | JSX children                     |
| Svelte    | `<slot name="x">` | `<svelte:fragment slot="x">`     |
| Vue       | `<slot name="x">` | `<template #x>`                  |

### Scoped CSS

| Framework | Syntax                                     |
| --------- | ------------------------------------------ |
| PJX       | `<style scoped>` (attribute-based scoping) |
| SolidJS   | CSS Modules (class name hashing)           |
| Svelte    | `<style>` (automatic, class-based scoping) |
| Vue       | `<style scoped>` (attribute-based scoping) |

---

## See also

- [[Component-Syntax]]
- [[State-and-Reactivity]]
- [[HTMX-Integration]]
- [[Control-Flow]]
- [[Imports-and-Composition]]
- [[Slots]]
- [[SSE-and-Realtime]]
- [[Loading-States]]
- [[CSS-and-Assets]]
