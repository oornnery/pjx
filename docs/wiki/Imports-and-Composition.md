# Imports and Composition

## Import Syntax

Components are imported in the **frontmatter** block (between `---`
delimiters) at the top of a `.jinja` file. The default import form brings in
a single component by its file name:

```python
import Button from "./Button.jinja"
import Modal from "../shared/Modal.jinja"
```

The identifier on the left (`Button`, `Modal`) becomes available as a
custom element in the component body. The string on the right is a path to
the `.jinja` file, resolved relative to the importing file.

### Rules

- One import per line.
- The identifier must be PascalCase.
- The path must end in `.jinja` for single-file imports, or `/` for
  directory imports.
- Imports must appear before `props`, `slot`, `let`, `const`, `state`,
  `computed`, and `extends` declarations.

---

## Aliased Imports

When a component name would collide with another identifier, or when you
want a more descriptive name, use the `as` keyword:

```python
import Button from "./Button.jinja" as PrimaryButton
import Button from "../admin/Button.jinja" as AdminButton
```

After aliasing, only the alias is available in the template body. The
original name (`Button`) is not registered.

After aliasing, the components are used by their alias in the template body:

```html
<PrimaryButton label="Save" />
<AdminButton label="Delete User" />
```

---

## Named Imports

A single `.jinja` file can export multiple sub-components. Named imports
use destructuring syntax to pull specific components out of a multi-export
file:

```python
import { CardHeader, CardBody, CardFooter } from "./Card.jinja"
```

Each name corresponds to a sub-component defined within the target file.
You can import one, some, or all of them.

```html
---
import { CardHeader, CardBody, CardFooter } from "./Card.jinja"
---

<div class="card">
    <CardHeader><h2>Title</h2></CardHeader>
    <CardBody><p>Content goes here.</p></CardBody>
    <CardFooter><button>Close</button></CardFooter>
</div>
```

---

## Directory Imports

When you have a directory of component files, you can import multiple
components in a single statement by pointing to the directory path (ending
with `/`):

```python
import { Card, Badge, Avatar } from "./components/"
```

This is equivalent to writing:

```python
import Card from "./components/Card.jinja"
import Badge from "./components/Badge.jinja"
import Avatar from "./components/Avatar.jinja"
```

The compiler resolves each name by looking for a matching `.jinja` file in
the target directory. If `Badge.jinja` does not exist in `./components/`,
the compiler raises an error at build time.

Directory imports keep the frontmatter concise while making dependencies
explicit.

---

## Wildcard Imports

To import every `.jinja` file from a directory, use the wildcard form:

```python
import * from "./ui/"
```

This registers all components found in the `./ui/` directory. Each file's
name (without the `.jinja` extension) becomes the component identifier.

| File               | Registered as |
| ------------------ | ------------- |
| `ui/Button.jinja`  | `Button`      |
| `ui/Card.jinja`    | `Card`        |
| `ui/Badge.jinja`   | `Badge`       |
| `ui/Tooltip.jinja` | `Tooltip`     |

Wildcard imports are convenient for prototyping but obscure which components
are actually used. For production code, prefer explicit named or directory
imports.

---

## Python Type Imports

Props in PJX are validated with Pydantic. Primitive types (`str`, `int`,
`bool`, `float`, `list`, `dict`, `Callable`, `Any`, `None`) are
auto-imported and available without any import statement.

For Pydantic types and constraints, use standard Python import syntax:

```python
from pydantic import EmailStr, HttpUrl
from typing import Literal, Annotated
from annotated_types import Gt, Lt, Ge, Le, MinLen, MaxLen
```

These imports make the types available in `props` declarations:

```python
props {
  email:    EmailStr,
  website:  HttpUrl | None          = None,
  role:     Literal["admin", "user"] = "user",
  score:    Annotated[int, Gt(0), Lt(100)] = 50,
}
```

Python type imports use `from ... import ...` syntax (not the `import X
from "path"` syntax used for components). This distinction makes it clear
whether you are importing a template or a Python type.

---

## Layout Inheritance

The `extends` keyword declares that a page inherits from a layout template.
It must appear in the frontmatter:

```python
extends "layouts/Base.jinja"
```

### How it works

1. The compiler loads the layout template (`layouts/Base.jinja`).
2. The page body (everything outside `<slot:*>` tags) is injected into the
   layout's `<Slot:content />`.
3. Named `<slot:*>` tags in the page are passed to the corresponding named
   slots in the layout.

### Layout template

A layout is a normal PJX component that declares [[Slots]] for injectable
regions:

```html
---
props {
  title:       str = "PJX App",
  description: str = "",
}

slot head
slot content
slot footer
---

<!DOCTYPE html>
<html lang="en">
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
        <footer><p>Copyright 2025 PJX</p></footer>
    </Slot:footer>
</body>
</html>
```

### Page that inherits

```html
---
extends "layouts/Base.jinja"

props {
  user:  dict,
  items: list[dict],
}
---

<slot:head>
    <meta property="og:title" content="Home" />
    <link rel="canonical" href="/" />
</slot:head>

<h1>Welcome, {{ props.user.name }}</h1>
<For each="props.items" as="item">
    <p>{{ item.title }}</p>
</For>
```

The `<h1>` and `<For>` content (outside any `<slot:*>` tag) is
automatically assigned to the layout's `<Slot:content />`. The `<slot:head>`
content is injected into `<Slot:head />`.

### Runtime layout alternative

PJX also supports a runtime layout via `PJX(layout="layouts/Base.jinja")`.
The rendered page HTML is injected as the `{{ body }}` variable. Disable it
on a specific route with `@pjx.page("/raw", layout=None)`.

---

## Path Resolution

Import paths are resolved relative to the file that contains the import
statement.

| Path style  | Example                           | Resolves from             |
| ----------- | --------------------------------- | ------------------------- |
| `./`        | `"./Button.jinja"`                | Same directory as file    |
| `../`       | `"../shared/Modal.jinja"`         | Parent directory          |
| No prefix   | `"layouts/Base.jinja"`            | Template search dirs      |

Relative paths (`./` and `../`) are resolved against the directory of the
importing file. If `pages/home.jinja` imports `"./components/Card.jinja"`,
the compiler looks for `pages/components/Card.jinja`.

Paths without a prefix are resolved against the configured template
directories (set via `template_dirs` in the PJX config). The compiler
searches each directory in order; the first match wins. If no match is
found, a compile-time error is raised.

For directory paths (ending with `/`), the same resolution rules apply.

---

## Using Components

Once imported, a component is used as a custom HTML element in the template
body. The element name matches the import identifier:

```html
<Button label="Save" variant="primary" />
```

### Passing props

Props are passed as HTML attributes. String values use quotes; expressions
use double curly braces:

```html
<Button label="Save" />
<Button label="{{ dynamic_label }}" disabled="true" />
<UserCard name="{{ user.name }}" role="{{ user.role }}" />
```

### Children as default slot

Content between opening and closing tags is passed as the default
[[Slots|slot]]:

```html
<Card title="Hello">
    <p>This becomes the default slot content.</p>
</Card>
```

### Named slots

Named slots are passed with `<slot:name>` tags inside the component call.
See [[Slots]] for full details.

### Self-closing vs block form

Components without children use self-closing syntax (`<Button label="Save" />`).
Components with children use the block form:

```html
<Card title="Hello">
    <p>Content here.</p>
</Card>
```

---

## Prop Spreading

When you have a dictionary of prop values, you can spread them onto a
component with the `...` prefix:

```html
---
let btn_props = {
  variant: "primary",
  size: "lg",
  disabled: false,
}
---

<Button ...btn_props />
```

This passes all key-value pairs from `btn_props` as individual props to
`Button`.

### Spread with overrides

Explicit attributes take priority over spread values:

```html
<Button ...btn_props label="Save" disabled="true" />
```

Here `label` is added (not in the spread dict) and `disabled` is overridden
to `"true"` even though the spread dict sets it to `false`.

If the spread target is a `let` or `const` with a known value at compile
time, the compiler inlines the props. If the value is dynamic, the merge
happens at render time.

---

## Compilation

The PJX compiler transforms each import pattern into standard Jinja2
constructs. The following table summarizes the mapping:

| PJX syntax                            | Compiled output                                            |
| ------------------------------------- | ---------------------------------------------------------- |
| `import Button from "./Button.jinja"` | Registers `Button` in the preprocessor; loads the template |
| `import Button from "..." as Btn`     | Registers as `Btn`                                         |
| `import { A, B } from "./dir/"`       | Loads `dir/A.jinja` and `dir/B.jinja`                      |
| `import * from "./ui/"`               | Loads all `.jinja` files in `./ui/`                        |
| `import { X, Y } from "./Card.jinja"` | Loads sub-components `X` and `Y` from `Card.jinja`         |
| `from pydantic import EmailStr`       | Makes `EmailStr` available as a prop type                  |
| `extends "layouts/Base.jinja"`        | Wraps the page in the layout via template inheritance      |

### Component usage compilation

When you use a component, the compiler generates `{% with %}` + `{% include %}`:

```jinja2
{# <Button label="Save" variant="primary" /> #}
{% with label="Save", variant="primary" %}
    {% include "Button.jinja" %}
{% endwith %}

{# <Card title="Hello"><p>Body</p><slot:footer>F</slot:footer></Card> #}
{% with title="Hello", _slot_default="<p>Body</p>", _slot_footer="F" %}
    {% include "Card.jinja" %}
{% endwith %}

{# <Button ...btn_props label="Save" /> #}
{% with **btn_props, label="Save" %}
    {% include "Button.jinja" %}
{% endwith %}
```

Layout inheritance compiles to standard Jinja2 `{% extends %}` with blocks.

---

## See also

- [[Component Syntax]] -- full component structure and frontmatter reference
- [[Slots]] -- declaring, rendering, and passing slot content
- [[Layouts and Inheritance]] -- layout mechanisms in detail
