# Slots

## What are Slots

Slots are content injection points that allow parent components to pass
arbitrary HTML into predefined regions of a child component. If you have used
Vue `<slot>` elements or Svelte `<slot>` tags, the concept is identical: a
component declares *where* external content can appear, and the consumer
decides *what* that content is.

Slots solve a fundamental composition problem. Without them a component can
only accept data through [[Component Syntax|props]]. Props work well for
scalar values and lists, but they are awkward for rich HTML fragments. Slots
let you keep the structural skeleton inside the component while delegating
the actual markup to the call-site.

PJX slots have three capabilities:

- **Named regions** -- each slot has an explicit name so multiple injection
  points can coexist in one component.
- **Fallback content** -- a slot can declare default markup that renders when
  the parent does not supply anything.
- **Conditional rendering** -- the component can check whether a slot was
  provided and adjust its layout accordingly.

---

## Declaring Slots

Slots are declared in the component **frontmatter** (the `---` block at the
top of a `.jinja` file). Each declaration starts with the keyword `slot`
followed by a name.

### Required slot (no fallback)

```python
slot header
slot actions
```

If the parent does not pass content for a required slot, the slot region
renders as empty. No error is raised -- the slot simply produces no output.

### Slot with default content

```python
slot footer = <span>Copyright 2025 PJX</span>
```

The `= <fallback>` portion provides inline HTML that will render when the
parent does not supply content for that slot. This is useful for footers,
sidebars, and other regions that have sensible defaults but should remain
overridable.

### Multiple slot declarations

You can declare as many slots as your component needs:

```python
slot header
slot sidebar
slot actions
slot footer = <p>Default footer</p>
```

Each name must be unique within the component.

---

## Rendering Slots

Inside the component body (the HTML below the frontmatter), you render a
slot with the `<Slot:name />` syntax. The uppercase `S` distinguishes slot
rendering from slot passing (which uses a lowercase `s`).

### Self-closing form

```html
<Slot:header />
```

If the parent provided content for `header`, it renders here. Otherwise
nothing is output.

### Block form with inline fallback

```html
<Slot:header>
    <h2>Default title</h2>
</Slot:header>
```

When written in block form, the children of `<Slot:header>` act as fallback
content. This inline fallback takes precedence over the frontmatter fallback
if both are present.

### Placement

`<Slot:name />` tags can appear anywhere regular HTML is valid. You can
place them inside `<div>` wrappers, inside control-flow tags like
`<Show>`, or at the top level of the component body.

```html
<article class="card">
    <header>
        <Slot:header />
    </header>
    <div class="card-body">
        <Slot:body />
    </div>
    <footer>
        <Slot:footer />
    </footer>
</article>
```

---

## Default Slot

Every component has an implicit **default slot**. When a parent passes
children to a component without wrapping them in a `<slot:name>` tag, those
children are collected into the default slot.

```html
<Card title="Hello">
    <p>This paragraph goes to the default slot.</p>
    <p>So does this one.</p>
</Card>
```

Inside the `Card` component, the default slot content is rendered wherever
`<Slot:default />` appears -- or, if the component does not explicitly
declare a default slot, the children are available as the implicit body.

You do not need to declare `slot default` in the frontmatter. It exists
automatically. However, you can declare it if you want to attach fallback
content:

```python
slot default = <p>No content provided.</p>
```

---

## Named Slots from Parent

When using a component, the parent passes content to a named slot by
wrapping it in a `<slot:name>` tag (lowercase `s`):

```html
<Card title="Dashboard">
    <!-- Named slots -->
    <slot:header>
        <h1>Custom Header</h1>
    </slot:header>

    <slot:footer>
        <button on:click="save()">Save</button>
        <button on:click="cancel()">Cancel</button>
    </slot:footer>

    <!-- Everything else goes to the default slot -->
    <p>This is the card body.</p>
</Card>
```

Key rules:

- The tag name is `slot:` followed by the slot name, all lowercase.
- Content between the opening and closing tags is the injected HTML.
- Named slot tags can appear in any order relative to default content.
- You can pass zero, some, or all named slots. Unprovided slots render
  their fallback (or nothing).

You can pass multiple named slots in a single component call -- they can
appear in any order relative to the default content.

---

## Slot Fallback Content

Fallback content is what renders when the parent does not provide anything
for a given slot. There are two places to define it:

### 1. Frontmatter fallback

```python
slot footer = <span>Copyright 2025 PJX</span>
```

This is the canonical location for fallback content. It is concise and
visible alongside the rest of the component's interface.

### 2. Inline fallback in the body

```html
<Slot:footer>
    <span>Copyright 2025 PJX</span>
</Slot:footer>
```

The block form of `<Slot:name>` uses its children as fallback. This is
useful when the fallback contains complex markup that would be awkward to
write on a single line in the frontmatter.

### Precedence

| Parent provides content? | Inline fallback present? | Frontmatter fallback? | What renders           |
| ------------------------ | ------------------------ | --------------------- | ---------------------- |
| Yes                      | --                       | --                    | Parent content         |
| No                       | Yes                      | --                    | Inline fallback        |
| No                       | No                       | Yes                   | Frontmatter fallback   |
| No                       | No                       | No                    | Nothing (empty string) |

Parent content always wins. When no parent content is given, inline fallback
takes priority over frontmatter fallback.

---

## Conditional Slot Rendering

A common pattern is to render a wrapper element only when a slot has content.
Without this, you get empty `<header>` or `<footer>` tags in the output.

PJX provides the `has_slot()` function for this purpose:

```html
<Show when="has_slot('header')">
    <header class="card-header">
        <Slot:header />
    </header>
</Show>
```

The `<Show>` tag compiles to a Jinja2 `{% if %}` block, so the entire
`<header>` wrapper is omitted when no header content is provided.

Apply this pattern to every optional slot wrapper in a component to keep
the rendered HTML clean -- no empty wrapper divs appear when a slot is
unused. See the complete example below for a full demonstration.

---

## Complete Example

### Card component (`components/Card.jinja`)

```html
---
props {
  title:   str,
  variant: str = "default",
}

slot header
slot actions
slot footer = <p class="text-muted">No footer provided.</p>
---

<div class="card card--{{ props.variant }}">
    <Show when="has_slot('header')">
        <div class="card-header">
            <Slot:header />
        </div>
    </Show>

    <Show when="props.title">
        <h3 class="card-title">{{ props.title }}</h3>
    </Show>

    <div class="card-body">
        <Slot:default>
            <p>This card has no content.</p>
        </Slot:default>
    </div>

    <Show when="has_slot('actions')">
        <div class="card-actions">
            <Slot:actions />
        </div>
    </Show>

    <div class="card-footer">
        <Slot:footer />
    </div>
</div>
```

### Parent page using the Card

```html
---
import Card from "./components/Card.jinja"
import Button from "./components/Button.jinja"
---

<Card title="User Profile" variant="primary">
    <slot:header>
        <div class="flex items-center gap-2">
            <img src="/avatar.png" alt="Avatar" class="w-8 h-8 rounded-full" />
            <span>Jane Doe</span>
        </div>
    </slot:header>

    <!-- Default slot: card body -->
    <p>Email: jane@example.com</p>
    <p>Role: Administrator</p>

    <slot:actions>
        <Button label="Edit" variant="secondary" />
        <Button label="Delete" variant="danger" />
    </slot:actions>

    <slot:footer>
        <p>Last login: 2025-12-01</p>
    </slot:footer>
</Card>

<!-- Minimal usage -- fallback footer renders -->
<Card title="Empty Card">
    <p>Just some body text.</p>
</Card>
```

In the second `<Card>` usage, no `header`, `actions`, or `footer` slots are
provided. The `header` and `actions` wrappers are omitted entirely (thanks
to the `<Show when="has_slot(...)">` guards), and the `footer` renders its
frontmatter fallback: `<p class="text-muted">No footer provided.</p>`.

---

## Compilation Output

Under the hood, the PJX compiler transforms slot syntax into standard Jinja2
constructs. The primary mechanisms are `{% with %}` for passing variables
and `{% include %}` for rendering sub-templates.

### Slot rendering

| PJX syntax                            | Compiled Jinja2                                                        |
| ------------------------------------- | ---------------------------------------------------------------------- |
| `<Slot:header />`                     | `{{ _slot_header \| default('') }}`                                    |
| `<Slot:header>fallback</Slot:header>` | `{% if _slot_header %}{{ _slot_header }}{% else %}fallback{% endif %}` |
| `has_slot('header')`                  | `_slot_header is defined and _slot_header`                             |

### Slot passing

| PJX syntax                              | Compiled Jinja2                                                |
| --------------------------------------- | -------------------------------------------------------------- |
| `<slot:header>content</slot:header>`    | Captures `content` into the variable `_slot_header`            |
| Children (no `<slot:*>` wrapper)        | Captured into `_slot_default`                                  |

### Full component call

When a parent uses a component with slots, the compiler generates a
`{% with %}` block that passes each slot as a variable:

```jinja2
{% with _slot_header=_captured_header, _slot_footer=_captured_footer, _slot_default=_captured_body %}
    {% include "components/Card.jinja" %}
{% endwith %}
```

Props are merged into the same `{% with %}` block alongside slot variables:

```jinja2
{% with title="User Profile", variant="primary", _slot_header=..., _slot_default=... %}
    {% include "components/Card.jinja" %}
{% endwith %}
```

This approach keeps slot values scoped to the included template and avoids
polluting the outer template namespace.

---

## See also

- [[Component Syntax]] -- full component structure and frontmatter reference
- [[Imports and Composition]] -- how to import and use components
- [[Layout Components]] -- built-in layout primitives that use slots internally
