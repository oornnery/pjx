# PJX

Jinja2 preprocessor with JSX-like syntax for FastAPI + HTMX + Stimulus.

PJX extends Jinja2 with components, control flow, frontmatter, conditional
attributes, and template expressions that compile transparently to standard
Jinja2 at template load time. No build step, no runtime overhead.

## Installation

```bash
pip install pjx
pip install pjx[htmx]
pip install pjx[htmx,stimulus]
pip install pjx[all]
```

Run the CLI without installing the package globally:

```bash
uvx pjx --help
uvx pjx check templates/
uvx pjx check templates/ --fix
uvx pjx skills --claude
uvx pjx assets build static/vendor/pjx
uvx pjx assets add alpinejs@3 --dist alpinejs/dist/cdn.min.js --out js/alpine.min.js
uvx pjx assets list
```

## Quick Setup

```python
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from jinja2 import FileSystemLoader
from pydantic import BaseModel

from pjx import PJXEnvironment
from pjx.router import PJXRouter

app = FastAPI()
templates = Jinja2Templates(
    env=PJXEnvironment(loader=FileSystemLoader("templates"))
)
ui = PJXRouter(templates)
app.include_router(ui)


class HomeProps(BaseModel):
    title: str = "Hello"
    items: list[str] = []


@ui.page("/", "pages/home.jinja")
async def home(request: Request) -> HomeProps:
    return HomeProps(items=["Alice", "Bob", "Charlie"])
```

## Example Template

```html
---
from ..layouts import BaseLayout
from ..components import UserCard

props:
  title: str = "Dashboard"
  users: list = []

computed:
  has_users: props.users | length > 0
---

<BaseLayout title={props.title}>
  <h1>{{ props.title }}</h1>

  <div ?hidden={not has_users}>
    <For each={props.users} as="user">
      <UserCard name={user.name} />
    </For>
  </div>

  <Show when={not has_users}>
    <p>No users yet.</p>
  </Show>
</BaseLayout>
```

## What You Get

- JSX-like components in Jinja2 templates
- `<For>`, `<Show>`, `<Switch>`, and `<Fragment>`
- `props:`, `vars:`, `computed:`, and slots in frontmatter
- Conditional attributes like `?hidden={expr}`
- HTMX and SSE aliases via `pjx[htmx]`
- Stimulus aliases via `pjx[stimulus]`
- `cn()` Tailwind class merging via `pjx[tailwind]`
- FastAPI helpers via `PJXRouter`
- CLI commands for template validation, formatting, and sitemap generation

## Extension System

PJX uses a unified extension model. Each extension subclasses `PJXExtension`
and can provide processors, Jinja2 globals, and browser asset providers through
three hooks:

```python
from pjx.extension import PJXExtension

class MyExtension(PJXExtension):
    @property
    def name(self) -> str:
        return "my-ext"

    def get_processors(self):
        return [(40, MyProcessor())]

    def get_jinja_globals(self):
        return {"my_func": my_func}

    def get_asset_provider(self):
        return MyAssetProvider()
```

Register extensions explicitly or let them be discovered automatically:

```python
from pjx import PJXEnvironment

# Explicit registration
env = PJXEnvironment(
    loader=FileSystemLoader("templates"),
    extensions=[MyExtension()],
)

# Auto-discovery via pjx.extensions entry point
env = PJXEnvironment(loader=FileSystemLoader("templates"))
```

Third-party packages register extensions in `pyproject.toml`:

```toml
[project.entry-points."pjx.extensions"]
my-ext = "my_package.extension:MyExtension"
```

The old `pjx.processors`, `pjx.jinja_globals`, and `pjx.assets` entry point
groups no longer exist. Use `pjx.extensions` instead.

## Browser Assets

Installed extensions can provide browser assets that PJX injects automatically
on full HTML documents:

- `pjx-htmx` injects HTMX when the rendered HTML contains `hx-*` or `sse-*`
- `pjx-stimulus` injects Stimulus when Stimulus `data-*` attributes are present
- `pjx-tailwind` injects the Tailwind browser build when it detects utility
  classes or `text/tailwindcss`

CDN mode works out of the box:

```python
templates = Jinja2Templates(
    env=PJXEnvironment(loader=FileSystemLoader("templates"))
)
```

Vendor mode switches injected URLs to local static files:

```python
templates = Jinja2Templates(
    env=PJXEnvironment(
        loader=FileSystemLoader("templates"),
        asset_mode="vendor",
        asset_base_url="/static/vendor/pjx",
    )
)
```

Build vendor files with the CLI. The build generates a `package.json`, runs
`npm install`, and copies dist files into the output directory. The resulting
`package.json` and `package-lock.json` are kept for reproducibility:

```bash
pjx assets build static/vendor/pjx
pjx assets build static/vendor/pjx --provider htmx --provider stimulus
```

## CLI

```bash
pjx check templates/
pjx check templates/ --fix
pjx format templates/
pjx sitemap templates/ --base-url https://example.com
pjx skills --claude
pjx skills --agents
pjx assets build static/vendor/pjx
pjx assets add alpinejs@3 --dist alpinejs/dist/cdn.min.js --out js/alpine.min.js
pjx assets list
pjx assets remove alpinejs
pjx demo

# no global install needed
uvx pjx --help
uvx pjx demo
```

`pjx check --fix` is for safe technical autofixes.
`pjx format` stays focused on formatting and frontmatter layout.
`pjx assets build` vendors browser assets via npm, merging extension and manifest packages.
`pjx assets add` adds an npm package to the local `pjx-assets.json` manifest.
`pjx assets list` shows all assets from extensions and the manifest.
`pjx assets remove` removes a package from the manifest.
`pjx demo` launches the bundled demo application.

## Links

- Repository: <https://github.com/oornnery/pjx>
- Full README: <https://github.com/oornnery/pjx/blob/main/README.md>
