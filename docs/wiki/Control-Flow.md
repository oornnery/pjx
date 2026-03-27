# Control Flow

PJX provides a set of HTML-like tags for control flow in templates. These
tags compile to standard Jinja2 template logic (`{% if %}`, `{% for %}`,
etc.) but offer a cleaner, more readable syntax that mirrors the component
model.

---

## Table of Contents

1. [Conditional Rendering](#conditional-rendering)
2. [Show with Else](#show-with-else)
3. [Show with Fallback](#show-with-fallback)
4. [Loops](#loops)
5. [Loop Variables](#loop-variables)
6. [Empty State](#empty-state)
7. [Multi-Branch](#multi-branch)
8. [Fragments](#fragments)
9. [Error Boundaries](#error-boundaries)
10. [Nesting](#nesting)
11. [Compilation Reference](#compilation-reference)

---

## Conditional Rendering

The `<Show>` tag renders its children only when the `when` attribute
evaluates to a truthy value. It compiles to a Jinja2 `{% if %}` block.

### Basic usage

```html
<Show when="user.is_admin">
    <button>Delete</button>
</Show>
```

Compiles to:

```html
{% if user.is_admin %}
    <button>Delete</button>
{% endif %}
```

### Negation

Use Python-style `not` in the expression.

```html
<Show when="not loading">
    <div>Content loaded</div>
</Show>
```

Compiles to:

```html
{% if not loading %}
    <div>Content loaded</div>
{% endif %}
```

### Complex expressions

Any valid Jinja2 expression can appear in the `when` attribute.

```html
<Show when="user.age >= 18 and user.verified">
    <span>Access granted</span>
</Show>
```

Compiles to:

```html
{% if user.age >= 18 and user.verified %}
    <span>Access granted</span>
{% endif %}
```

### Truthiness

The `when` expression follows Jinja2 truthiness rules. Empty lists, empty
strings, `None`, `0`, and `false` are all falsy.

```html
<Show when="items">
    <p>There are items to display.</p>
</Show>
```

---

## Show with Else

Use the `<Else>` tag as a child of `<Show>` to provide alternate content
when the condition is false.

```html
<Show when="user">
    <p>Welcome, {{ user.name }}!</p>
<Else>
    <p>Please log in.</p>
</Else>
</Show>
```

Compiles to:

```html
{% if user %}
    <p>Welcome, {{ user.name }}!</p>
{% else %}
    <p>Please log in.</p>
{% endif %}
```

The `<Else>` tag must be a direct child of `<Show>` and there can be at most
one per `<Show>` block.

### Practical example

```html
<Show when="notifications | length > 0">
    <ul>
        <For each="notifications" as="note">
            <li>{{ note.message }}</li>
        </For>
    </ul>
<Else>
    <p class="text-muted">No new notifications.</p>
</Else>
</Show>
```

---

## Show with Fallback

The `fallback` attribute provides inline alternate content as a string. This
is a shorthand for simple fallback cases where a full `<Else>` block is not
needed.

```html
<Show when="items" fallback="<p>No items.</p>">
    <ul>
        <For each="items" as="item">
            <li>{{ item.name }}</li>
        </For>
    </ul>
</Show>
```

Compiles to:

```html
{% if items %}
    <ul>
        {% for item in items %}
            <li>{{ item.name }}</li>
        {% endfor %}
    </ul>
{% else %}
    <p>No items.</p>
{% endif %}
```

### When to use `fallback` vs `<Else>`

Use `fallback` when the alternate content is a single short HTML snippet.
Use `<Else>` when the alternate content is complex, spans multiple lines,
or contains other PJX components.

| Approach    | Best for                           |
| ----------- | ---------------------------------- |
| `fallback`  | Simple inline HTML strings         |
| `<Else>`    | Multi-line content, nested tags    |

---

## Loops

The `<For>` tag iterates over a collection, rendering its children once per
item. It compiles to a Jinja2 `{% for %}` block.

### Basic usage

```html
<For each="users" as="user">
    <li>{{ user.name }}</li>
</For>
```

Compiles to:

```html
{% for user in users %}
    <li>{{ user.name }}</li>
{% endfor %}
```

### With index

Access the current iteration index via Jinja2's built-in `loop` variable.

```html
<For each="items" as="item">
    <li>{{ loop.index }}. {{ item }}</li>
</For>
```

### Nested loops

Loops can be nested. Each level has its own `loop` variable. To access the
outer loop from an inner loop, use Jinja2's `loop` context (the inner `loop`
shadows the outer one).

```html
<For each="categories" as="cat">
    <h3>{{ cat.name }}</h3>
    <For each="cat.products" as="product">
        <span>{{ product.name }}</span>
    </For>
</For>
```

Compiles to:

```html
{% for cat in categories %}
    <h3>{{ cat.name }}</h3>
    {% for product in cat.products %}
        <span>{{ product.name }}</span>
    {% endfor %}
{% endfor %}
```

### Inline filters

Jinja2 filters can be applied directly in the `each` attribute to filter or
transform the collection before iteration.

```html
<For each="users | selectattr('active')" as="user">
    <li>{{ user.name }}</li>
</For>
```

Compiles to:

```html
{% for user in users | selectattr('active') %}
    <li>{{ user.name }}</li>
{% endfor %}
```

Other useful filter patterns:

```html
<!-- Sort before iterating -->
<For each="items | sort(attribute='name')" as="item">
    <li>{{ item.name }}</li>
</For>

<!-- Reverse order -->
<For each="items | reverse" as="item">
    <li>{{ item.name }}</li>
</For>

<!-- First N items -->
<For each="items[:5]" as="item">
    <li>{{ item.name }}</li>
</For>
```

---

## Loop Variables

Inside a `<For>` block, Jinja2 provides a `loop` object with useful
metadata about the current iteration.

| Variable              | Type     | Description                              |
| --------------------- | -------- | ---------------------------------------- |
| `loop.index`          | `int`    | Current iteration, 1-based               |
| `loop.index0`         | `int`    | Current iteration, 0-based               |
| `loop.first`          | `bool`   | `true` if this is the first item         |
| `loop.last`           | `bool`   | `true` if this is the last item          |
| `loop.length`         | `int`    | Total number of items in the collection  |
| `loop.cycle('a','b')` | `str`    | Alternates between the given values      |

### Practical examples

Striped table rows:

```html
<table>
    <For each="rows" as="row">
        <tr class="{{ loop.cycle('bg-white', 'bg-gray-50') }}">
            <td>{{ loop.index }}</td>
            <td>{{ row.name }}</td>
        </tr>
    </For>
</table>
```

Comma-separated list:

```html
<For each="tags" as="tag">
    <span>{{ tag }}</span>
    <Show when="not loop.last">, </Show>
</For>
```

First and last item styling:

```html
<For each="steps" as="step">
    <div class="step
        {{ 'step-first' if loop.first else '' }}
        {{ 'step-last' if loop.last else '' }}">
        {{ step.title }}
    </div>
</For>
```

---

## Empty State

The `<Empty>` tag is a child of `<For>` that renders when the collection is
empty. It compiles to Jinja2's `{% else %}` clause on the `for` loop.

```html
<For each="results" as="result">
    <div>{{ result.title }}</div>
<Empty>
    <p>No results found.</p>
</Empty>
</For>
```

Compiles to:

```html
{% for result in results %}
    <div>{{ result.title }}</div>
{% else %}
    <p>No results found.</p>
{% endfor %}
```

The `<Empty>` tag must be a direct child of `<For>`. There can be at most
one `<Empty>` per `<For>` block.

### Detailed empty state

```html
<For each="orders" as="order">
    <div class="order-card">
        <h3>Order #{{ order.id }}</h3>
        <p>{{ order.total | currency }}</p>
    </div>
<Empty>
    <div class="empty-state">
        <h3>No orders yet</h3>
        <p>When you place an order, it will appear here.</p>
        <a href="/products">Browse products</a>
    </div>
</Empty>
</For>
```

---

## Multi-Branch

The `<Switch>` / `<Case>` / `<Default>` tags provide multi-branch
conditional logic, similar to a switch statement. The first `<Case>` compiles
to `{% if %}`, subsequent cases to `{% elif %}`, and `<Default>` to
`{% else %}`.

### Basic usage

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
```

Compiles to:

```html
{% set _sw = status %}
{% if _sw == "active" %}
    <Badge text="Active" variant="success" />
{% elif _sw == "pending" %}
    <Badge text="Pending" variant="warning" />
{% elif _sw == "blocked" %}
    <Badge text="Blocked" variant="danger" />
{% else %}
    <Badge text="Unknown" variant="muted" />
{% endif %}
```

### Numeric values

```html
<Switch on="props.level">
    <Case value="1"><h1>{{ title }}</h1></Case>
    <Case value="2"><h2>{{ title }}</h2></Case>
    <Case value="3"><h3>{{ title }}</h3></Case>
    <Default><p>{{ title }}</p></Default>
</Switch>
```

### Without Default

The `<Default>` tag is optional. If omitted and no case matches, nothing is
rendered.

```html
<Switch on="theme">
    <Case value="dark">
        <link rel="stylesheet" href="/css/dark.css" />
    </Case>
    <Case value="light">
        <link rel="stylesheet" href="/css/light.css" />
    </Case>
</Switch>
```

### Compilation reference

| Written                   | Compiled                |
| ------------------------- | ----------------------- |
| `<Switch on="x">`         | `{% set _sw = x %}`     |
| `<Case value="v">` (1st)  | `{% if _sw == "v" %}`   |
| `<Case value="v">` (2nd+) | `{% elif _sw == "v" %}` |
| `<Default>`               | `{% else %}`            |
| `</Switch>`               | `{% endif %}`           |

---

## Fragments

The `<Fragment>` tag groups multiple elements without introducing a wrapper
element in the DOM. It renders its children directly.

```html
<Fragment>
    <li>Item 1</li>
    <li>Item 2</li>
    <li>Item 3</li>
</Fragment>
```

Compiles to:

```html
    <li>Item 1</li>
    <li>Item 2</li>
    <li>Item 3</li>
```

### When to use Fragments

Use `<Fragment>` when a PJX construct requires a single root element but you
need to render multiple sibling elements.

```html
<Show when="show_actions">
    <Fragment>
        <button>Edit</button>
        <button>Delete</button>
        <button>Archive</button>
    </Fragment>
</Show>
```

Without `<Fragment>`, you would need a wrapping `<div>` that may break your
layout or styling.

---

## Error Boundaries

The `<ErrorBoundary>` tag wraps content in a try/except block. If an error
occurs during rendering, the fallback content is displayed instead of
crashing the page.

### With fallback attribute

```html
<ErrorBoundary fallback="<p>Something went wrong.</p>">
    <UserProfile user="{{ user }}" />
</ErrorBoundary>
```

If `UserProfile` raises an error during rendering, the user sees
"Something went wrong." instead of a server error.

### With error slot

For more control over the error display, use the `slot:error` named slot.

```html
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

### Compilation

| Written                                             | Compiled                                            |
| --------------------------------------------------- | --------------------------------------------------- |
| `<ErrorBoundary fallback="fb">body</ErrorBoundary>` | `try/except` wrapper that renders fallback on error |

### Guidelines

- Wrap components that depend on external data or user input.
- Keep fallback content simple and static.
- Use the error slot when you need retry logic or detailed error messages.
- Error boundaries catch rendering errors only, not client-side JavaScript
  errors (those are handled by Alpine.js or the browser).

---

## Nesting

Control flow tags can be freely nested to build complex template logic.

### Show inside For

Conditionally render items within a loop.

```html
<For each="users" as="user">
    <div class="user-row">
        <span>{{ user.name }}</span>
        <Show when="user.is_admin">
            <span class="badge">Admin</span>
        </Show>
    </div>
</For>
```

### For inside Show

Render a list only when data is available.

```html
<Show when="category.products">
    <h2>{{ category.name }}</h2>
    <ul>
        <For each="category.products" as="product">
            <li>{{ product.name }} -- {{ product.price }}</li>
        </For>
    </ul>
<Else>
    <p>This category has no products.</p>
</Else>
</Show>
```

### Switch inside For

Apply different rendering per item based on a property.

```html
<For each="notifications" as="note">
    <Switch on="note.type">
        <Case value="info">
            <div class="alert alert-info">{{ note.message }}</div>
        </Case>
        <Case value="warning">
            <div class="alert alert-warning">{{ note.message }}</div>
        </Case>
        <Case value="error">
            <div class="alert alert-danger">{{ note.message }}</div>
        </Case>
    </Switch>
</For>
```

### For inside Switch

Render different lists depending on the active view.

```html
<Switch on="view">
    <Case value="grid">
        <div class="grid">
            <For each="items" as="item">
                <div class="card">{{ item.name }}</div>
            </For>
        </div>
    </Case>
    <Case value="list">
        <ul>
            <For each="items" as="item">
                <li>{{ item.name }}</li>
            </For>
        </ul>
    </Case>
</Switch>
```

### Deep nesting with ErrorBoundary

Protect sections of deeply nested content.

```html
<For each="sections" as="section">
    <ErrorBoundary fallback="<p>Failed to load section.</p>">
        <h2>{{ section.title }}</h2>
        <Show when="section.items">
            <For each="section.items" as="item">
                <div>{{ item.content }}</div>
            </For>
        <Else>
            <p>No content in this section.</p>
        </Else>
        </Show>
    </ErrorBoundary>
</For>
```

---

## Compilation Reference

Complete mapping of control flow tags to their Jinja2 output.

### Show (conditional)

| PJX                                     | Jinja2                                  |
| --------------------------------------- | --------------------------------------- |
| `<Show when="x">`                       | `{% if x %}`                            |
| `</Show>`                               | `{% endif %}`                           |
| `<Show when="x" fallback="fb">body`     | `{% if x %}body{% else %}fb{% endif %}` |
| `<Else>`                                | `{% else %}`                            |

### For (iteration)

| PJX                     | Jinja2             |
| ----------------------- | ------------------ |
| `<For each="x" as="i">` | `{% for i in x %}` |
| `<Empty>`               | `{% else %}`       |
| `</For>`                | `{% endfor %}`     |

### Switch (multi-branch)

| PJX                             | Jinja2                  |
| ------------------------------- | ----------------------- |
| `<Switch on="x">`               | `{% set _sw = x %}`     |
| `<Case value="v">` (first)      | `{% if _sw == "v" %}`   |
| `<Case value="v">` (subsequent) | `{% elif _sw == "v" %}` |
| `<Default>`                     | `{% else %}`            |
| `</Switch>`                     | `{% endif %}`           |

### Other

| PJX                                                 | Output                                   |
| --------------------------------------------------- | ---------------------------------------- |
| `<Fragment>...children...</Fragment>`               | `...children...` (no wrapper element)    |
| `<ErrorBoundary fallback="fb">body</ErrorBoundary>` | `try/except` rendering fallback on error |

---

## See also

- [[Component Syntax]] -- component structure, props, slots, imports
- [[State and Reactivity]] -- client-side state, bindings, Alpine.js integration
- [[Compilation Reference]] -- full compilation tables for all PJX features
