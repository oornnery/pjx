# PJX Syntax Reference

## Frontmatter

```html
---
from ..layouts import BaseLayout
from ..components import UserCard

props:
  title: str = "Dashboard"
  users: list = []

vars:
  card_class: "rounded shadow p-4"
  roles:
    admin: "badge-red"
    user: "badge-gray"

computed:
  has_users: props.users | length > 0
  greeting: "Welcome to " ~ props.title

slot actions
---
```

### Section Order (canonical)

1. `from X import Y` — imports
2. `props:` — typed properties with defaults
3. `vars:` — template-scoped variables (scalar or map)
4. `computed:` — derived values from props/vars
5. `slot name` — named content slots

Use `pjx format` to enforce this order.

## Control Flow

```html
<!-- Loop -->
<For each={items} as="item">
  <li>{{ item.name }}</li>
</For>

<!-- Conditional -->
<Show when={user.active}>
  <span>Active</span>
  <Else>
    <span>Inactive</span>
  </Else>
</Show>

<!-- Switch -->
<Switch expr={user.role}>
  <Case value="admin"><span>Admin</span></Case>
  <Default><span>User</span></Default>
</Switch>

<!-- Fragment (no wrapper element) -->
<Fragment>
  <span>A</span>
  <span>B</span>
</Fragment>
```

## Attributes

```html
<!-- Expression: {expr} -> {{ expr }} -->
<a href={"/users/" ~ user.id}>Link</a>

<!-- Conditional: include only when truthy -->
<div ?hidden={not visible}>content</div>
<option value="admin" ?selected={role == "admin"}>Admin</option>

<!-- Spread: expand dict as attributes -->
<div class="base" ...{extra_attrs}>content</div>
```

## Components

Uppercase tags imported via frontmatter:

```html
---
from ..components import UserCard
from ..icons import IconEdit
---

<!-- Self-closing -->
<UserCard id={user.id} name={user.name} />

<!-- With children (receives {{ content }}) -->
<BaseLayout title={props.title}>
  <h1>Body here</h1>
</BaseLayout>

<!-- SVG icons are components -->
<button><IconEdit size="14" /> Edit</button>
```

## HTMX Aliases (pjx-htmx)

```html
<button htmx:post="/users" htmx:target="#list" htmx:swap="innerHTML">
  Save
</button>
<!-- -> hx-post, hx-target, hx-swap -->

<div sse:connect="/events" sse:swap="message"></div>
<!-- -> sse-connect, sse-swap -->
```

## Stimulus Aliases (pjx-stimulus)

```html
<div stimulus:controller="dropdown">
  <button stimulus:action="click->dropdown#toggle">Menu</button>
  <div stimulus:target="menu">Content</div>
</div>

<!-- Multi-controller: explicit selection -->
<div stimulus:controller="dropdown modal">
  <button stimulus:target.dropdown="trigger">Open</button>
</div>

<!-- Values -->
<div stimulus:controller="editor">
  <input stimulus:value-content="hello" />
  <!-- -> data-editor-content-value="hello" -->
</div>
```

## cn() (pjx-tailwind)

```html
---
computed:
  btn: cn("btn", is_primary and "btn-primary", disabled and "opacity-50")
---
<button class={btn}>Click</button>
```

Filters falsy, joins with space, deduplicates.

## What Compiles to What

| PJX | Jinja2 |
|-----|--------|
| `<For each={items} as="item">` | `{% for item in items %}` |
| `<Show when={cond}>` | `{% if cond %}` |
| `<Else>` | `{% else %}` |
| `<Switch expr={x}><Case value="a">` | `{% if x == "a" %}` |
| `<Fragment>` | (removed) |
| `<UserCard name={x} />` | `{% with name=x %}{% include "..." %}{% endwith %}` |
| `href={url}` | `href="{{ url }}"` |
| `?hidden={expr}` | `{% if expr %}hidden="{{ expr }}"{% endif %}` |
| `...{attrs}` | `{{ attrs \| xmlattr }}` |
| `htmx:post="/url"` | `hx-post="/url"` |
| `stimulus:controller="x"` | `data-controller="x"` |
| `vars: color: "blue"` | `{% set color = "blue" %}` |
| `computed: x: a ~ b` | `{% set x = a ~ b %}` |
