# PJX Template Structure

Use the demo app as the canonical example of how to organize templates and
static assets:

```text
app/
  main.py
  views.py
  templates/
    layouts/
      BaseLayout.jinja
    components/
      UserCard.jinja
      ConfirmModal.jinja
    icons/
      IconPlus.jinja
      IconEdit.jinja
    pages/
      home.jinja
      404.jinja
      500.jinja
      users/
        [id].jinja
    partials/
      user_card.jinja
      edit_modal.jinja
      form_error.jinja
  static/
    css/
      index.css
    js/
      index.js
    vendor/
      pjx/
        js/
          htmx.min.js
          stimulus.umd.js
          tailwind.browser.js
```

Inside `templates/`, the PJX structure is:

```text
templates/
  layouts/
    BaseLayout.jinja
  components/
    UserCard.jinja
    ConfirmModal.jinja
  icons/
    IconPlus.jinja
    IconEdit.jinja
  pages/
    home.jinja
    404.jinja
    500.jinja
    users/
      [id].jinja
  partials/
    user_card.jinja
    edit_modal.jinja
    form_error.jinja
```

The demo lives at `demo/app/` and shows the intended split:

- `layouts/` for page shells that render `{{ content }}`
- `components/` for reusable uppercase PJX components like `<UserCard />`
- `icons/` for SVG-style components used inside pages and components
- `pages/` for full page templates rendered by `@ui.page`
- `partials/` for fragment and action responses rendered by `@ui.fragment` and `@ui.action`
- `static/` for CSS and JavaScript served by FastAPI outside the PJX template tree

## Static Assets

PJX does not require a specific static folder layout, but the demo uses the
standard FastAPI pattern:

```python
app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")
```

In the demo, `BaseLayout.jinja` references those files directly:

```html
<link rel="stylesheet" href="/static/css/index.css">
<script src="/static/js/index.js"></script>
```

That gives you a clean split:

- PJX templates live in `templates/`
- CSS and JavaScript live in `static/`
- vendored browser assets can live in `static/vendor/pjx/` via `pjx assets build`
- layout templates usually own the shared `<link>` and `<script>` tags

## Demo Examples

`pages/home.jinja` is the main page:

```html
---
from ..layouts import BaseLayout
from ..components import UserCard, ConfirmModal
from ..icons import IconPlus
---
```

`pages/users/[id].jinja` is a nested page:

```html
---
from ...layouts import BaseLayout
from ...icons import IconUser, IconEdit, IconTrash
---
```

The imports are relative to the template file location, so deeper files use more
leading dots.

## Route-to-Template Conventions

Use `pages/` for full routes and `partials/` for HTMX swaps:

```python
@ui.page("/", "pages/home.jinja")
@ui.page("/users/{user_id}", "pages/users/[id].jinja")
@ui.fragment("/users/{user_id}/edit", "partials/edit_modal.jinja")
@ui.action("/users", success_template="partials/user_card.jinja")
```

This is the same pattern used in `demo/app/views.py`.

## Dynamic Route Files: `[id]` and `[slug]`

PJX commonly uses bracketed filenames for dynamic pages:

- `pages/users/[id].jinja`
- `pages/blog/[slug].jinja`
- `pages/orgs/[org_slug]/repos/[repo_slug].jinja`

Example:

```python
@ui.page("/users/{user_id}", "pages/users/[id].jinja")
async def user_detail(request, user_id: int):
    ...
```

Inside the template, the route params are available through `params`:

```html
<a href={"/users/" ~ params.user_id}>Profile</a>
```

Important:

- The bracketed filename is a routing convention for humans and project structure.
- The actual template context comes from FastAPI path params via `request.path_params`.
- In practice, `pages/users/[id].jinja` can be used with `/users/{user_id}`.
- `params.user_id` comes from the route declaration, not from the literal filename.

## Error Pages

Keep error pages inside `pages/`:

```text
pages/404.jinja
pages/500.jinja
```

Render them manually with `ui.render(...)` in FastAPI exception handlers.
