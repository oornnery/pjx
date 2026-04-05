# PJX Template Syntax

## Frontmatter

Every `.jinja` file can start with a `---` block declaring metadata:

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

**Section order** (enforced by `pjx format`):
imports -> props -> vars -> computed -> slots

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

<!-- Fragment: render children without wrapper -->
<Fragment>
  <span>A</span>
  <span>B</span>
</Fragment>
```

## Expressions

`{expr}` in attributes compiles to `{{ expr }}`:

```html
<a href={"/users/" ~ user.id}>{{ user.name }}</a>
```

## Conditional Attributes

`?attr={expr}` — includes the attribute only when truthy:

```html
<div ?hidden={not visible}>content</div>
<option value="admin" ?selected={role == "admin"}>Admin</option>
<input ?required={is_required} ?disabled={is_disabled} />
```

## Spread Attributes

`...{dict}` — expands a dict as HTML attributes:

```html
<div class="base" ...{extra_attrs}>content</div>
```

## Components

Uppercase tags imported via frontmatter. Compiled to `{% include %}`:

```html
---
from ..components import UserCard
from ..icons import IconEdit
---

<!-- Self-closing -->
<UserCard id={user.id} name={user.name} />

<!-- With children (template receives {{ content }}) -->
<BaseLayout title={props.title}>
  <h1>Page content</h1>
</BaseLayout>

<!-- SVG icons are components too -->
<button><IconEdit size="14" /> Edit</button>
```

## Template Variables

### vars: — static values

```html
---
vars:
  color: "blue"
  sizes:
    sm: "h-8 px-3"
    md: "h-10 px-4"
---
<div class={sizes[props.size]}>...</div>
```

### computed: — derived values

```html
---
props:
  first: str
  last: str

computed:
  full_name: first ~ " " ~ last
  is_long: full_name | length > 20
---
<h1>{{ full_name }}</h1>
```

## HTMX Aliases (requires pjx[htmx])

```html
<button htmx:post="/users" htmx:target="#list" htmx:swap="innerHTML">
  Save
</button>

<div sse:connect="/events" sse:swap="message"></div>
```

## Stimulus Aliases (requires pjx[stimulus])

```html
<div stimulus:controller="dropdown">
  <button stimulus:action="click->dropdown#toggle">Menu</button>
  <div stimulus:target="menu">Content</div>
</div>

<!-- Multi-controller: use explicit .controller selection -->
<div stimulus:controller="dropdown modal">
  <button stimulus:target.dropdown="trigger">Open</button>
</div>
```

## cn() (requires pjx[tailwind])

Class-name merging — filters falsy, deduplicates:

```html
---
computed:
  cls: cn("btn", is_primary and "btn-primary", disabled and "opacity-50")
---
<button class={cls}>Click</button>
```

## Compilation Table

| PJX                            | Compiles to                                   |
| ------------------------------ | --------------------------------------------- |
| `<For each={items} as="item">` | `{% for item in items %}`                     |
| `<Show when={cond}>`           | `{% if cond %}`                               |
| `<Else>`                       | `{% else %}`                                  |
| `<Switch>/<Case>/<Default>`    | `{% if %}/{% elif %}/{% else %}`              |
| `<Fragment>`                   | (removed — children render directly)          |
| `<Card name={x} />`            | `{% with name=x %}{% include %}{% endwith %}` |
| `href={url}`                   | `href="{{ url }}"`                            |
| `?hidden={expr}`               | `{% if expr %}hidden="{{ expr }}"{% endif %}` |
| `...{attrs}`                   | `{{ attrs \| xmlattr }}`                      |
| `htmx:post="/url"`             | `hx-post="/url"`                              |
| `stimulus:controller="x"`      | `data-controller="x"`                         |
| `vars: color: "blue"`          | `{% set color = "blue" %}`                    |
| `computed: x: a ~ b`           | `{% set x = a ~ b %}`                         |
