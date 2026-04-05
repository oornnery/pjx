# PJX Demo

CRUD de usuarios com FastAPI + PJX + HTMX + Stimulus.

Demonstra todas as features do PJX v0.2:

- Components (`<UserCard>`, `<BaseLayout>`, `<ConfirmModal>`)
- Control flow (`<For>`, `<Show>`, `<Switch>`)
- `<Fragment>` (wrapper-less rendering)
- Frontmatter (`props:`, `vars:`, `computed:`)
- Conditional attributes (`?hidden`, `?selected`)
- HTMX aliases (`htmx:post`, `htmx:target`, `htmx:swap`)
- Stimulus aliases (`stimulus:controller`, `stimulus:action`)
- `cn()` class-name merging (via pjx-tailwind)
- SVG icon components (`<IconPlus>`, `<IconEdit>`, etc.)
- PJXRouter decorators (`@ui.page`, `@ui.fragment`, `@ui.action`)
- FormData validation with Pydantic
- Error pages (404, 500)

## Run

```bash
uv run task demo
# or
uv run uvicorn demo.app.main:app --reload
```

Open <http://localhost:8000>

## Structure

```text
demo/
  app/
    main.py          # FastAPI app setup
    models.py        # Pydantic models (User, Forms, Props)
    service.py       # In-memory user service
    deps.py          # Depends providers
    api.py           # JSON API (/api/users)
    views.py         # PJXRouter HTML routes
    templates/
      layouts/       # BaseLayout.jinja
      components/    # UserCard.jinja, ConfirmModal.jinja
      icons/         # IconPlus, IconUser, IconEdit, IconTrash, IconX
      pages/         # home.jinja, users/[id].jinja, 404, 500
      partials/      # user_card, edit_modal, form_error
    static/
      css/app.css
      js/app.js
```

## Features Used Per Template

| Template       | Features                                      |
| -------------- | --------------------------------------------- |
| home.jinja     | `computed:`, `?hidden`, `<Fragment>`, `<For>` |
| UserCard.jinja | `vars:`, `computed:`, `cn()`, htmx aliases    |
| user_card      | `computed:`, `cn()`, `<Show>`                 |
| edit_modal     | `computed:`, `?selected`, stimulus aliases    |
| [id].jinja     | `vars:`, `computed:`, `cn()`, htmx aliases    |
