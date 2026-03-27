# Props and Validation

Props are the primary mechanism for passing data into PJX components. They are
declared in the frontmatter with types, defaults, and optional constraints.
At compile time, PJX generates a Pydantic `BaseModel` for each component's
props, enabling runtime validation with clear error messages.

---

## Declaring Props

Props are declared inside a `props { }` block in the frontmatter. Each prop
has a name, a type, and an optional default value.

```html
---
props {
  name: str,
  age: int = 0,
}
---

<div>
  <h2>{{ props.name }}</h2>
  <span>Age: {{ props.age }}</span>
</div>
```

### Syntax

```text
props {
  <name>: <type>,                    # required prop
  <name>: <type> = <default>,        # optional prop with default
}
```

- Props without a default are **required**. The component will raise an error
  if the caller omits them.
- Props with a default are **optional**. The default value is used when the
  caller does not provide the prop.
- Trailing commas are allowed and encouraged.

### Multiple Props

```python
props {
  title:    str,
  subtitle: str | None = None,
  count:    int        = 0,
  variant:  str        = "primary",
  items:    list       = [],
  config:   dict       = {},
}
```

---

## Supported Types

PJX supports all standard Python types plus Pydantic validation types.

### Primitive Types

These are available automatically with no `from` import needed.

| Type    | Description              | Example Default   |
| ------- | ------------------------ | ----------------- |
| `str`   | String                   | `"hello"`         |
| `int`   | Integer                  | `0`               |
| `bool`  | Boolean                  | `false`           |
| `float` | Floating-point number    | `0.0`             |
| `list`  | List (untyped)           | `[]`              |
| `dict`  | Dictionary (untyped)     | `{}`              |

### Generic Types

```python
props {
  tags:    list[str]       = [],
  scores:  list[int]       = [],
  meta:    dict[str, Any]  = {},
  mapping: dict[str, int]  = {},
}
```

### Union Types (Nullable)

Use the `|` operator for union types:

```python
props {
  bio:    str | None      = None,
  count:  int | None      = None,
  url:    HttpUrl | None  = None,
}
```

### `Literal` -- Constrained Choices

`Literal` restricts a prop to specific allowed values, functioning like an
inline enum:

```python
from typing import Literal

props {
  variant:  Literal["primary", "secondary", "danger"] = "primary",
  size:     Literal["sm", "md", "lg"]                 = "md",
  role:     Literal["admin", "mod", "user"]            = "user",
}
```

If a caller passes a value not in the `Literal` set, Pydantic raises a
validation error at render time.

### `Annotated` -- Constraints

`Annotated` adds validation constraints from `annotated_types` or Pydantic:

```python
from typing import Annotated
from annotated_types import Gt, Lt, Ge, Le, MinLen, MaxLen

props {
  score:    Annotated[int, Gt(0), Lt(100)]       = 50,
  username: Annotated[str, MinLen(3), MaxLen(20)] = "",
  quantity: Annotated[int, Ge(1)]                 = 1,
}
```

### Pydantic Types

These require an explicit `from` import in the frontmatter:

```python
from pydantic import EmailStr, HttpUrl

props {
  email:   EmailStr,
  website: HttpUrl | None = None,
}
```

### `Callable`

For callback props (used in advanced composition patterns):

```python
props {
  on_click:  Callable       = None,
  on_change: Callable       = None,
}
```

### Complete Type Reference

| DSL Type                      | Pydantic Equivalent     | Import Required                        |
| ----------------------------- | ----------------------- | -------------------------------------- |
| `str`, `int`, `bool`, `float` | Native types            | No                                     |
| `list`, `dict`                | Native types            | No                                     |
| `list[str]`, `dict[str, Any]` | Generic types           | No (`Any` auto)                        |
| `str \| None`                 | `Union[str, None]`      | No                                     |
| `Literal["a", "b"]`           | `Literal["a", "b"]`     | `from typing`                          |
| `Annotated[int, Gt(0)]`       | `Annotated[int, Gt(0)]` | `from typing` + `from annotated_types` |
| `EmailStr`                    | `pydantic.EmailStr`     | `from pydantic`                        |
| `HttpUrl`                     | `pydantic.HttpUrl`      | `from pydantic`                        |
| `Callable`                    | `Callable \| None`      | No                                     |

---

## Importing Types

Primitive types (`str`, `int`, `bool`, `float`, `list`, `dict`, `Callable`,
`Any`, `None`) are auto-imported and always available. All other types must
be explicitly imported using Python `from ... import ...` syntax in the
frontmatter.

### Common Imports

```python
# Standard library
from typing import Literal, Annotated

# Pydantic types
from pydantic import EmailStr, HttpUrl

# Constraints
from annotated_types import Gt, Lt, Ge, Le, MinLen, MaxLen
```

### Import Compilation

| Written                              | Internal Effect                                    |
| ------------------------------------ | -------------------------------------------------- |
| `from typing import Literal`         | Makes `Literal` available as a type in props       |
| `from pydantic import EmailStr`      | Makes `EmailStr` available as a type in props      |
| `from annotated_types import Gt, Lt` | Makes `Gt`, `Lt` available as constraints in props |

These imports do not produce any output in the compiled template. They only
affect the generated Pydantic model used for validation.

---

## Default Values

### Simple Defaults

Scalar defaults are written directly after the `=` sign:

```python
props {
  title:   str   = "Untitled",
  count:   int   = 0,
  active:  bool  = true,
  ratio:   float = 1.0,
}
```

### Nullable Defaults

Union types typically default to `None`:

```python
props {
  bio:     str | None     = None,
  avatar:  HttpUrl | None = None,
}
```

### Mutable Defaults (list, dict)

When a default value is a mutable type (`list` or `dict`), PJX automatically
uses Pydantic's `Field(default_factory=...)` to avoid the shared-mutable-default
problem.

```python
props {
  tags:   list[str]      = [],
  meta:   dict[str, Any] = {},
  scores: list[int]      = [],
}
```

This compiles to:

```python
class ComponentProps(BaseModel):
    tags: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
    scores: list[int] = Field(default_factory=list)
```

Each component instance gets its own independent copy of the default list or
dictionary.

---

## Accessing Props

In the HTML body, access props through the `props` namespace:

```html
---
props {
  title: str,
  count: int = 0,
  variant: str = "primary",
}
---

<div class="card card--{{ props.variant }}">
  <h2>{{ props.title }}</h2>
  <span>Count: {{ props.count }}</span>
</div>
```

### In Expressions

Props can be used in Jinja2 expressions, filters, and control flow:

```html
<!-- Filters -->
<h1>{{ props.title | upper }}</h1>
<p>{{ props.bio | default("No bio provided") | truncate(100) }}</p>

<!-- In let/computed -->
---
let css_class = "card card--" + props.variant
computed char_count = len(props.text)
---
```

### In Control Flow Tags

```html
<Show when="props.active">
  <span class="badge">Active</span>
</Show>

<For each="props.items" as="item">
  <li>{{ item.name }}</li>
</For>

<Switch on="props.variant">
  <Case value="primary"><div class="btn-primary">...</div></Case>
  <Case value="danger"><div class="btn-danger">...</div></Case>
</Switch>
```

### Passing Props to Child Components

When using a component, pass props as attributes:

```html
<UserCard
  name="{{ user.name }}"
  email="{{ user.email }}"
  role="admin"
  active />

<!-- Boolean props: presence = true -->
<Alert dismissible message="Saved!" />
```

---

## Attrs Passthrough

Attributes not declared in `props` are automatically collected and forwarded
to the component's root element via `{{ attrs }}`. This allows callers to
pass HTML, HTMX, and Alpine attributes without the component declaring each
one as a prop.

### Component Definition

```html
---
props {
  label: str,
  variant: str = "primary",
}
---

<button class="btn btn-{{ props.variant }}" {{ attrs }}>
  {{ props.label }}
</button>
```

### Usage

```html
<!-- class, id, and hx-get are NOT declared props -->
<Button label="Save" class="mt-4" id="save-btn" hx-get="/save" />
```

The rendered output includes all extra attributes on the `<button>` element:

```html
<button class="btn btn-primary mt-4" id="save-btn" hx-get="/save">
  Save
</button>
```

### Common Passthrough Attributes

- **HTML**: `class`, `id`, `data-*`, `aria-*`, `style`, `title`
- **HTMX**: `hx-get`, `hx-post`, `hx-target`, `hx-swap`, `hx-trigger`
- **Alpine.js**: `x-show`, `x-bind:*`, `@click`

This pattern keeps components focused on their declared API while remaining
fully extensible.

---

## Runtime Validation

When `validate_props = true` (the default), PJX validates all props against
their declared types at render time using the generated Pydantic model.

### Enabling/Disabling

In `pjx.toml`:

```toml
validate_props = true    # default: validate at render time
```

Or in Python:

```python
from pjx import PJXConfig

# Enabled (default)
config = PJXConfig(validate_props=True)

# Disabled (production performance optimization)
config = PJXConfig(validate_props=False)
```

### PropValidationError

When validation fails, PJX raises `PropValidationError` with a clear message
identifying the component, the prop, and the type mismatch:

```text
PropValidationError: Component "UserCard" prop validation failed:
  - name: field required
  - age: value is not a valid integer (got "abc")
  - role: unexpected value; permitted: 'admin', 'mod', 'user' (got "superuser")
```

### What Gets Validated

| Check               | Example                                         |
| ------------------- | ----------------------------------------------- |
| Required props      | `name: str` -- error if omitted                 |
| Type mismatches     | `age: int` passed `"abc"` -- error              |
| Literal constraints | `role: Literal["a", "b"]` passed `"c"` -- error |
| Annotated bounds    | `Annotated[int, Gt(0)]` passed `-1` -- error    |
| Pydantic validators | `EmailStr` passed `"not-an-email"` -- error     |

### Static Analysis

In addition to runtime validation, `pjx check` performs static analysis on
components without running the server:

```bash
pjx check .
```

This validates:

- **Import resolution** -- all imports resolve to existing files
- **Props checking** -- required props are passed to child components
- **Slot checking** -- slot passes match declared slots in children

---

## Internal Compilation

When PJX encounters a `props { }` block, it generates a Pydantic `BaseModel`
class that serves as the validation schema for that component.

### Example Input

```python
from typing import Literal, Annotated
from pydantic import EmailStr
from annotated_types import Gt, Lt

props {
  name:     str,
  age:      int                        = 0,
  role:     Literal["admin", "mod", "user"] = "user",
  email:    EmailStr,
  bio:      str | None                 = None,
  tags:     list[str]                  = [],
  meta:     dict[str, Any]            = {},
  score:    Annotated[int, Gt(0), Lt(100)] = 50,
}
```

### Generated Pydantic Model

```python
from typing import Literal, Annotated, Any
from pydantic import BaseModel, Field, EmailStr
from annotated_types import Gt, Lt

class ComponentNameProps(BaseModel):
    name: str
    age: int = 0
    role: Literal["admin", "mod", "user"] = "user"
    email: EmailStr
    bio: str | None = None
    tags: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
    score: Annotated[int, Gt(0), Lt(100)] = 50
```

### Key Details

- The class name is derived from the component filename (`UserCard.jinja`
  becomes `UserCardProps`).
- Mutable defaults (`[]`, `{}`) are automatically converted to
  `Field(default_factory=...)`.
- The generated model is cached per template and reused across renders.
- When `validate_props = false`, model generation is skipped entirely for
  performance.

---

## FormData Integration

PJX integrates props validation with FastAPI's form handling through
`Annotated[Model, FormData()]`. This bridges component props with server-side
form processing.

### Defining a Form Model

```python
from pydantic import BaseModel, EmailStr

class ContactForm(BaseModel):
    name: str
    email: EmailStr
    message: str = ""
```

### Using FormData in a Page Handler

```python
from typing import Annotated
from pjx import FormData

@pjx.page("/contact", methods=["GET", "POST"])
async def contact(form: Annotated[ContactForm, FormData()]):
    if form.name:
        # Process submitted form
        send_email(form.email, form.message)
        return {"success": True, "form": form}
    return {"success": False, "form": ContactForm()}
```

### How It Works

1. On **GET** requests, `FormData()` provides an empty model instance with
   defaults.
2. On **POST** requests, `FormData()` parses `request.form()` into the
   Pydantic model, validating all fields.
3. Validation errors are handled by Pydantic -- invalid submissions raise
   `ValidationError` with field-level messages.

### In the Template

```html
---
props {
  success: bool = false,
}
---

<form method="post">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}" />

  <label>Name
    <input type="text" name="name" value="{{ form.name }}" required />
  </label>

  <label>Email
    <input type="email" name="email" value="{{ form.email }}" required />
  </label>

  <label>Message
    <textarea name="message">{{ form.message }}</textarea>
  </label>

  <button type="submit">Send</button>

  <Show when="success">
    <p class="success">Message sent.</p>
  </Show>
</form>
```

### HTMX Form Submission

For partial page updates, use HTMX attributes instead of a full form post:

```html
<form action:post="/htmx/contact/submit"
      target="#form-result"
      swap="innerHTML">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}" />
  <input type="text" name="name" required />
  <input type="email" name="email" required />
  <button type="submit">Send</button>
</form>

<div id="form-result"></div>
```

The HTMX endpoint processes the form and returns an HTML fragment:

```python
@app.post("/htmx/contact/submit")
async def htmx_submit(request: Request) -> HTMLResponse:
    form = await request.form()
    # validate and process...
    return HTMLResponse(
        pjx.render("components/ContactResult.jinja", {"success": True})
    )
```

---

## See Also

- [[Component Syntax]] -- full component format and frontmatter reference
- [[FastAPI Integration]] -- page handlers, SEO, and server configuration
