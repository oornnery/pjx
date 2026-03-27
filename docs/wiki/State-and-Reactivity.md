# State and Reactivity

PJX provides a declarative reactivity layer that compiles to
[Alpine.js](https://alpinejs.dev/). You declare **state** and **computed**
values in frontmatter, mark the root element as `reactive`, and then use
`bind:` / `on:` attributes in the template body. The compiler translates
everything into standard Alpine.js directives.

---

## Table of Contents

1. [Client-Side State](#client-side-state)
2. [Computed Values](#computed-values)
3. [The `reactive` Attribute](#the-reactive-attribute)
4. [Two-Way Binding](#two-way-binding)
5. [Text and HTML Binding](#text-and-html-binding)
6. [Visibility](#visibility)
7. [CSS Classes](#css-classes)
8. [Event Handlers](#event-handlers)
9. [Transitions](#transitions)
10. [Global Stores](#global-stores)
11. [Refs](#refs)
12. [Compilation Table](#compilation-table)
13. [Examples](#examples)

---

## Client-Side State

Use the `state` keyword in frontmatter to declare client-side reactive
variables. Each `state` declaration becomes a property inside the Alpine.js
`x-data` object generated for the component.

### Syntax

```python
state <name> = <initial_value>
```

### Supported types

```python
state count    = 0              # number
state open     = false          # boolean
state search   = ""             # string
state selected = []             # list
state form     = { name: "", email: "" }  # object
```

### How it compiles

When the compiler encounters `state` declarations it collects them into a
single `x-data` object that is attached to the root element marked with the
`reactive` attribute.

Given this frontmatter:

```html
---
state count = 0
state open = false
state search = ""
---

<div reactive>
    ...
</div>
```

The compiled output is:

```html
<div x-data="{ count: 0, open: false, search: '' }">
    ...
</div>
```

### Server-side rendering

State values are also available during SSR via Jinja2 expressions. When the
page is first rendered on the server, `{{ count }}` outputs the initial value.
Once Alpine.js hydrates on the client, the reactive system takes over.

| Written           | Server (Jinja2)        | Client (Alpine.js)           |
| ----------------- | ---------------------- | ---------------------------- |
| `state count = 0` | `{{ count }}` for SSR  | `x-data` includes `count: 0` |

---

## Computed Values

Use the `computed` keyword to declare derived values that are recalculated
whenever their dependencies change.

### Syntax

```python
computed <name> = <expression>
```

### Examples

```python
computed total      = len(props.items)
computed done_count = len([i for i in props.items if i.done])
computed progress   = (done_count / total * 100) if total > 0 else 0
computed is_empty   = total == 0
```

### How it compiles

Computed values compile to server-side Jinja2 `{% set %}` statements. They
are evaluated at render time, not reactively on the client.

| Written                 | Compiled (Jinja2)        |
| ----------------------- | ------------------------ |
| `computed total = expr` | `{% set total = expr %}` |

If you need a value that updates reactively on the client without a server
round-trip, use a JavaScript getter inside the `reactive` attribute or a
global store method instead.

---

## The `reactive` Attribute

The `reactive` attribute must appear on the **root element** of a component
to enable the Alpine.js reactive scope. Without it, `state`, `bind:`, and
`on:` directives have no effect.

### Bare form

When used without a value, the compiler auto-generates an `x-data` object
from all `state` declarations in the frontmatter.

```html
<div reactive>
    <!-- Alpine.js scope is active here -->
</div>
```

Compiles to:

```html
<div x-data="{ count: 0, open: false }">
    ...
</div>
```

### Explicit form

You can pass a custom `x-data` object directly, bypassing the automatic
generation from `state` declarations.

```html
<div reactive="{ count: 0, open: false }">
    ...
</div>
```

Compiles to:

```html
<div x-data="{ count: 0, open: false }">
    ...
</div>
```

### Store scope

Use the `reactive:store` variant to bind the component to a global Alpine
store instead of local state.

```html
<div reactive:store="todos">
    ...
</div>
```

Compiles to:

```html
<div x-data="Alpine.store('todos')">
    ...
</div>
```

### Compilation summary

| Written                 | Compiled                        |
| ----------------------- | ------------------------------- |
| `reactive`              | `x-data="{{ alpine_data }}"`    |
| `reactive="{ x: 0 }"`   | `x-data="{ x: 0 }"`             |
| `reactive:store="name"` | `x-data="Alpine.store('name')"` |

---

## Two-Way Binding

Use `bind:model` to create two-way data bindings between form inputs and
state variables. This compiles directly to Alpine.js `x-model`.

### Basic binding

```html
---
state name = ""
---

<div reactive>
    <input bind:model="name" />
    <p>Hello, <span bind:text="name"></span></p>
</div>
```

Compiles to:

```html
<div x-data="{ name: '' }">
    <input x-model="name" />
    <p>Hello, <span x-text="name"></span></p>
</div>
```

### Modifiers

`bind:model` supports modifiers that control when and how the value syncs.

| PJX                             | Alpine.js                    | Description                          |
| ------------------------------- | ---------------------------- | ------------------------------------ |
| `bind:model="x"`                | `x-model="x"`                | Syncs on every input event           |
| `bind:model.lazy="x"`           | `x-model.lazy="x"`           | Syncs on `change` instead of `input` |
| `bind:model.number="x"`         | `x-model.number="x"`         | Casts value to number                |
| `bind:model.debounce.500ms="x"` | `x-model.debounce.500ms="x"` | Debounces input by 500ms             |

### Textarea binding

```html
---
state message = ""
---

<div reactive>
    <textarea bind:model="message"></textarea>
    <p>Characters: <span bind:text="message.length"></span></p>
</div>
```

### Select binding

```html
---
state color = "red"
---

<div reactive>
    <select bind:model="color">
        <option value="red">Red</option>
        <option value="green">Green</option>
        <option value="blue">Blue</option>
    </select>
    <p bind:text="'Selected: ' + color"></p>
</div>
```

### Checkbox binding

```html
---
state agree = false
---

<div reactive>
    <label>
        <input type="checkbox" bind:model="agree" />
        I agree to the terms
    </label>
    <button bind:disabled="!agree">Submit</button>
</div>
```

---

## Text and HTML Binding

### `bind:text`

Sets the text content of an element reactively. The initial content is
replaced once Alpine.js hydrates.

```html
<span bind:text="count">0</span>
```

Compiles to:

```html
<span x-text="count">0</span>
```

The `0` is displayed during SSR. Once Alpine loads, `x-text` takes over and
updates the content whenever `count` changes.

### `bind:html`

Sets the inner HTML of an element reactively.

```html
<div bind:html="richContent"></div>
```

Compiles to:

```html
<div x-html="richContent"></div>
```

**XSS Warning**: `bind:html` renders raw HTML into the DOM. Never bind
user-supplied content directly. Always sanitize HTML on the server before
passing it to the client. Unsanitized content can lead to cross-site
scripting (XSS) attacks.

| Written          | Compiled          |
| ---------------- | ----------------- |
| `bind:text="x"`  | `x-text="x"`      |
| `bind:html="x"`  | `x-html="x"`      |

---

## Visibility

### `bind:show`

Toggles element visibility using CSS `display: none`. The element remains in
the DOM but is hidden when the expression evaluates to `false`.

```html
---
state open = false
---

<div reactive>
    <button on:click="open = !open">Toggle</button>

    <div bind:show="open">
        <p>This content is visible when open is true.</p>
    </div>
</div>
```

Compiles to:

```html
<div x-data="{ open: false }">
    <button @click="open = !open">Toggle</button>

    <div x-show="open">
        <p>This content is visible when open is true.</p>
    </div>
</div>
```

### `bind:cloak`

Prevents the flash of unstyled content (FOUC) that can occur before
Alpine.js initializes. The element is hidden until Alpine processes it.

```html
<div bind:cloak>
    <span bind:text="message"></span>
</div>
```

Compiles to:

```html
<div x-cloak>
    <span x-text="message"></span>
</div>
```

Pair this with a CSS rule in your stylesheet:

```css
[x-cloak] { display: none !important; }
```

| Written         | Compiled     |
| --------------- | ------------ |
| `bind:show="x"` | `x-show="x"` |
| `bind:cloak`    | `x-cloak`    |

---

## CSS Classes

Use `bind:class` to dynamically toggle CSS classes based on reactive state.
The value is an Alpine.js expression, typically an object where keys are class
names and values are boolean expressions.

### Object syntax

```html
<div bind:class="{ 'active': isActive }"></div>
<div bind:class="{ 'bg-red-500': hasError, 'opacity-50': isLoading }"></div>
```

Compiles to:

```html
<div :class="{ 'active': isActive }"></div>
<div :class="{ 'bg-red-500': hasError, 'opacity-50': isLoading }"></div>
```

### Combining static and dynamic classes

Static `class` and dynamic `bind:class` can coexist on the same element.
Alpine.js merges them at runtime.

```html
<button class="btn" bind:class="{ 'btn-primary': isPrimary, 'btn-disabled': !isValid }">
    Submit
</button>
```

### Style binding

`bind:style` works the same way for inline styles.

```html
<div bind:style="{ color: textColor, fontSize: size + 'px' }"></div>
```

Compiles to:

```html
<div :style="{ color: textColor, fontSize: size + 'px' }"></div>
```

### Generic attribute binding

Any attribute can be bound dynamically using `bind:{attr}`.

```html
<img bind:src="imageUrl" />
<a bind:href="link">Link</a>
<button bind:disabled="!isValid">Submit</button>
<div bind:id="'item-' + id"></div>
```

Compiles to:

```html
<img :src="imageUrl" />
<a :href="link">Link</a>
<button :disabled="!isValid">Submit</button>
<div :id="'item-' + id"></div>
```

| Written           | Compiled      |
| ----------------- | ------------- |
| `bind:class="x"`  | `:class="x"`  |
| `bind:style="x"`  | `:style="x"`  |
| `bind:{attr}="x"` | `:{attr}="x"` |

---

## Event Handlers

Use the `on:` prefix to attach client-side event handlers. The compiler
translates these to Alpine.js `@event` shorthand.

### Basic usage

```html
<button on:click="count++">Increment</button>
<button on:click="handleClick()">Click Me</button>
```

Compiles to:

```html
<button @click="count++">Increment</button>
<button @click="handleClick()">Click Me</button>
```

### Modifiers

Modifiers are chained after the event name with dots.

| Modifier   | Description                                        | Example                              |
| ---------- | -------------------------------------------------- | ------------------------------------ |
| `prevent`  | Calls `event.preventDefault()`                     | `on:submit.prevent="save()"`         |
| `stop`     | Calls `event.stopPropagation()`                    | `on:click.stop="handle()"`           |
| `outside`  | Fires when click is outside the element            | `on:click.outside="open = false"`    |
| `window`   | Listens on `window` instead of the element         | `on:scroll.window="handleScroll()"`  |
| `document` | Listens on `document` instead of the element       | `on:keydown.document="handleKey()"`  |
| `once`     | Handler fires only once, then is removed           | `on:click.once="init()"`             |
| `debounce` | Debounces the handler by a given duration          | `on:input.debounce.300ms="search()"` |
| `throttle` | Throttles the handler by a given duration          | `on:click.throttle.500ms="save()"`   |
| `self`     | Fires only if `event.target` is the element itself | `on:click.self="close()"`            |
| `camel`    | Converts event name to camelCase                   | `on:custom-event.camel="handle()"`   |
| `dot`      | Converts event name to dot notation                | `on:custom-event.dot="handle()"`     |

### Keyboard events

Key modifiers filter by specific keys.

```html
<input on:keydown.enter="submit()" />
<input on:keydown.escape="cancel()" />
<input on:keydown.shift.enter="submitAndContinue()" />
```

### Chaining modifiers

Multiple modifiers can be combined.

```html
<a on:click.prevent.stop="navigate()">Link</a>
<form on:submit.prevent="save()">
    ...
</form>
```

### Compilation reference

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

## Transitions

Use `bind:transition` to animate elements as they enter and leave the DOM
(typically paired with `bind:show`).

### Basic transition

```html
---
state open = false
---

<div reactive>
    <button on:click="open = !open">Toggle</button>

    <div bind:show="open" bind:transition>
        <p>Animated content</p>
    </div>
</div>
```

Compiles to:

```html
<div x-data="{ open: false }">
    <button @click="open = !open">Toggle</button>

    <div x-show="open" x-transition>
        <p>Animated content</p>
    </div>
</div>
```

### Transition modifiers

| PJX                                  | Alpine.js                          | Description                    |
| ------------------------------------ | ---------------------------------- | ------------------------------ |
| `bind:transition`                    | `x-transition`                     | Default fade + scale           |
| `bind:transition.opacity`            | `x-transition.opacity`             | Fade only (no scale)           |
| `bind:transition.duration.500ms`     | `x-transition.duration.500ms`      | Custom duration                |

### Enter/leave classes

For fine-grained control, use the `<Transition>` control flow tag which
allows specifying separate enter and leave animations.

```html
<Transition enter="fade-in 300ms" leave="fade-out 200ms">
    <Show when="visible">
        <div class="modal">Content</div>
    </Show>
</Transition>
```

Compiles to a wrapper with `x-transition:enter` and `x-transition:leave`
classes applied.

| Written                                | Compiled                         |
| -------------------------------------- | -------------------------------- |
| `bind:transition`                      | `x-transition`                   |
| `bind:transition.opacity`              | `x-transition.opacity`           |
| `bind:transition.duration.500ms`       | `x-transition.duration.500ms`    |

---

## Global Stores

Global stores allow multiple components to share state. Declare a store in
frontmatter with the `store` keyword.

### Declaring a store

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

The compiler generates an `Alpine.store()` call in the base layout's init
script:

```javascript
Alpine.store('todos', {
  items: [],
  filter: "all",
  add(text) { this.items.push({ text, done: false }) },
  toggle(index) { this.items[index].done = !this.items[index].done },
});
```

### Using a store in components

Bind the component to a store with `reactive:store`, then access properties
via `$store.name`.

```html
<div reactive:store="todos">
    <input bind:model="$store.todos.filter" />
    <For each="$store.todos.items" as="item">
        <li>{{ item.text }}</li>
    </For>
</div>
```

### Accessing stores from any component

Any component within the Alpine scope can read and write to a store, even
without `reactive:store`. Use `$store.name.property` directly.

```html
<div reactive>
    <span bind:text="$store.todos.items.length"></span> items
    <button on:click="$store.todos.add('New item')">Add</button>
</div>
```

### Compilation summary

| Written                  | Compiled                                            |
| ------------------------ | --------------------------------------------------- |
| `store name = { ... }`   | `Alpine.store('name', { ... })` in the init script  |
| `reactive:store="name"`  | `x-data="Alpine.store('name')"`                     |
| `$store.name.prop`       | Direct access to the Alpine store                   |

---

## Refs

Use `bind:ref` to assign a reference name to an element, making it
accessible from JavaScript expressions via `$refs`.

### Declaring a ref

```html
<input bind:ref="searchInput" placeholder="Search..." />
```

Compiles to:

```html
<input x-ref="searchInput" placeholder="Search..." />
```

### Accessing refs

Use `$refs.name` in any Alpine expression within the same `reactive` scope.

```html
---
state query = ""
---

<div reactive>
    <input bind:ref="searchInput" bind:model="query" />
    <button on:click="$refs.searchInput.focus()">Focus Search</button>
    <button on:click="$refs.searchInput.value = ''; query = ''">Clear</button>
</div>
```

### Common use cases

- Focusing an input programmatically
- Reading dimensions or scroll position of an element
- Interacting with third-party libraries that need a DOM reference

| Written           | Compiled       |
| ----------------- | -------------- |
| `bind:ref="name"` | `x-ref="name"` |
| `$refs.name`      | `$refs.name`   |

---

## Compilation Table

Complete mapping of PJX reactive attributes to their Alpine.js output.

### Data and scope

| PJX                     | Alpine.js                       |
| ----------------------- | ------------------------------- |
| `reactive`              | `x-data="{{ alpine_data }}"`    |
| `reactive="{ x: 0 }"`   | `x-data="{ x: 0 }"`             |
| `reactive:store="name"` | `x-data="Alpine.store('name')"` |
| `bind:init="expr"`      | `x-init="expr"`                 |

### Text and HTML

| PJX                | Alpine.js         |
| ------------------ | ----------------- |
| `bind:text="x"`    | `x-text="x"`      |
| `bind:html="x"`    | `x-html="x"`      |

### Visibility

| PJX             | Alpine.js    |
| --------------- | ------------ |
| `bind:show="x"` | `x-show="x"` |
| `bind:cloak`    | `x-cloak`    |

### Binding

| PJX                              | Alpine.js                      |
| -------------------------------- | ------------------------------ |
| `bind:model="x"`                 | `x-model="x"`                  |
| `bind:model.lazy="x"`            | `x-model.lazy="x"`             |
| `bind:model.number="x"`          | `x-model.number="x"`           |
| `bind:model.debounce.500ms="x"`  | `x-model.debounce.500ms="x"`   |
| `bind:class="x"`                 | `:class="x"`                   |
| `bind:style="x"`                 | `:style="x"`                   |
| `bind:{attr}="x"`                | `:{attr}="x"`                  |

### Transitions

| PJX                              | Alpine.js                     |
| -------------------------------- | ----------------------------- |
| `bind:transition`                | `x-transition`                |
| `bind:transition.opacity`        | `x-transition.opacity`        |
| `bind:transition.duration.500ms` | `x-transition.duration.500ms` |

### Refs

| PJX               | Alpine.js        |
| ----------------- | ---------------- |
| `bind:ref="x"`    | `x-ref="x"`      |

### Events

| PJX                              | Alpine.js                      |
| -------------------------------- | ------------------------------ |
| `on:click="x"`                   | `@click="x"`                   |
| `on:click.prevent="x"`           | `@click.prevent="x"`           |
| `on:click.stop="x"`              | `@click.stop="x"`              |
| `on:click.outside="x"`           | `@click.outside="x"`           |
| `on:click.once="x"`              | `@click.once="x"`              |
| `on:click.throttle.500ms="x"`    | `@click.throttle.500ms="x"`    |
| `on:input.debounce.300ms="x"`    | `@input.debounce.300ms="x"`    |
| `on:keydown.enter="x"`           | `@keydown.enter="x"`           |
| `on:scroll.window="x"`           | `@scroll.window="x"`           |

---

## Examples

### Interactive counter

A simple counter demonstrating state, events, and text binding.

```html
---
state count = 0
---

<div reactive>
    <h2>Counter</h2>
    <p>Current count: <span bind:text="count">0</span></p>

    <button on:click="count++">Increment</button>
    <button on:click="count--">Decrement</button>
    <button on:click="count = 0">Reset</button>
</div>
```

### Toggle panel

A collapsible panel using visibility and transitions.

```html
---
state open = false
---

<div reactive>
    <button on:click="open = !open" bind:text="open ? 'Hide' : 'Show'">
        Show
    </button>

    <div bind:show="open" bind:transition bind:cloak>
        <p>This panel slides open and closed.</p>
        <p>It uses x-show with x-transition for smooth animation.</p>
    </div>
</div>
```

### Search with debounce

A search input that debounces user input before filtering results.

```html
---
state search = ""
state results = []
---

<div reactive>
    <input
        type="text"
        placeholder="Search..."
        bind:model.debounce.300ms="search"
        bind:ref="searchInput"
    />

    <button on:click="$refs.searchInput.focus()">Focus</button>

    <Show when="search.length > 0">
        <p>Searching for: <span bind:text="search"></span></p>
    </Show>

    <ul>
        <For each="results" as="result">
            <li bind:text="result.name"></li>
        </For>
    </ul>
</div>
```

### Form with validation

A form demonstrating two-way binding, computed state, and conditional classes.

```html
---
state form = { name: "", email: "", message: "" }
state submitted = false

computed name_valid = form.name.length >= 2
computed email_valid = form.email.includes("@")
computed is_valid = name_valid && email_valid && form.message.length > 0
---

<form reactive on:submit.prevent="submitted = true">
    <div>
        <label>Name</label>
        <input
            bind:model="form.name"
            bind:class="{ 'border-red-500': !name_valid && form.name.length > 0, 'border-green-500': name_valid }"
        />
        <Show when="!name_valid && form.name.length > 0">
            <span class="text-red-500">Name must be at least 2 characters.</span>
        </Show>
    </div>

    <div>
        <label>Email</label>
        <input
            type="email"
            bind:model="form.email"
            bind:class="{ 'border-red-500': !email_valid && form.email.length > 0, 'border-green-500': email_valid }"
        />
    </div>

    <div>
        <label>Message</label>
        <textarea bind:model="form.message"></textarea>
    </div>

    <button type="submit" bind:disabled="!is_valid">Send</button>

    <Show when="submitted">
        <div class="text-green-500" bind:transition>
            <p>Form submitted successfully.</p>
        </div>
    </Show>
</form>
```

---

## See also

- [[Component Syntax]] -- component structure, props, slots, imports
- [[HTMX Integration]] -- server-side interactions with `action:` attributes
- [[Control Flow]] -- `<Show>`, `<For>`, `<Switch>` tags for template logic
