# PJX Demo

Interactive demo application showcasing PJX features: components, control flow,
frontmatter, HTMX aliases, Stimulus aliases, and `cn()` class merging.

## Running

The demo is bundled inside the `pjx` package and can be launched directly:

```bash
uvx pjx demo
# or
uv run pjx demo
```

Open <http://localhost:8000>

Options:

```bash
pjx demo --host 0.0.0.0 --port 3000
pjx demo --reload
```

## Source Location

The demo application lives in the core package at:

```text
src/pjx/pjx/_bundled/demo/app/
```

## Vendor Mode

The demo uses vendor mode by default. Browser assets (HTMX, Stimulus, Tailwind)
are pre-built and served from `static/vendor/pjx/` instead of CDN URLs.

```text
static/vendor/pjx/
  js/
    htmx.min.js
    stimulus.umd.js
    tailwind.browser.js
  package.json
  package-lock.json
```

## Features Demonstrated

- Components (`<UserCard>`, `<BaseLayout>`, `<ConfirmModal>`)
- Control flow (`<For>`, `<Show>`, `<Switch>`, `<Fragment>`)
- Frontmatter (`props:`, `vars:`, `computed:`)
- Conditional attributes (`?hidden`, `?selected`)
- HTMX aliases (`htmx:post`, `htmx:target`, `htmx:swap`)
- Stimulus aliases (`stimulus:controller`, `stimulus:action`)
- `cn()` class-name merging (via pjx-tailwind)
- PJXRouter decorators (`@ui.page`, `@ui.fragment`, `@ui.action`)
- FormData validation with Pydantic
- Error pages (404, 500)
