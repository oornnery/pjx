# PJX

Jinja2 preprocessor with JSX-like syntax for FastAPI + HTMX + Stimulus.

PJX brings component-style templates, control flow tags, frontmatter, and a
unified extension system to server-rendered Python apps, while still compiling
to normal Jinja2 at template load time.

## Installation

```bash
pip install pjx                    # core only
pip install pjx[htmx]             # + HTMX/SSE aliases
pip install pjx[htmx,stimulus]    # + Stimulus aliases
pip install pjx[tailwind]         # + cn() class merging
pip install pjx[all]              # everything
pip install pjx[demo]             # + demo app dependencies
```

Run the CLI without a global install:

```bash
uvx pjx --help
uvx pjx demo
uvx pjx check templates/
uvx pjx check templates/ --fix
uvx pjx skills --claude
uvx pjx assets build static/vendor/pjx
uvx pjx assets add alpinejs@3 --dist alpinejs/dist/cdn.min.js --out js/alpine.min.js
uvx pjx assets list
```

## Quick Example

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


@ui.page("/", "pages/home.jinja")
async def home(request: Request) -> HomeProps:
    return HomeProps()
```

```html
---
from ..layouts import BaseLayout
from ..components import UserCard

props:
  users: list = []
---

<BaseLayout title="Dashboard">
  <For each={props.users} as="user">
    <UserCard name={user.name} />
  </For>
</BaseLayout>
```

## Packages

- Core: [`pjx`](src/pjx/README.md)
- HTMX aliases: [`pjx-htmx`](src/pjx-htmx/README.md)
- Stimulus aliases: [`pjx-stimulus`](src/pjx-stimulus/README.md)
- Tailwind helper: [`pjx-tailwind`](src/pjx-tailwind/README.md)
- Demo app: run `pjx demo` or `uvx pjx demo`

## Documentation

- Wiki home: <https://github.com/oornnery/pjx/wiki>
- Getting started: <https://github.com/oornnery/pjx/wiki/Getting-Started>
- Core syntax: <https://github.com/oornnery/pjx/wiki/Core-Syntax>
- Frontmatter: <https://github.com/oornnery/pjx/wiki/Frontmatter>
- Router: <https://github.com/oornnery/pjx/wiki/PJXRouter>
- CLI: <https://github.com/oornnery/pjx/wiki/CLI>
- Architecture: <https://github.com/oornnery/pjx/wiki/Architecture>

## Extension System

Extensions subclass `PJXExtension` and provide three hooks: `get_processors()`,
`get_jinja_globals()`, and `get_asset_provider()`. Register explicitly or let
PJX discover them via the `pjx.extensions` entry point:

```python
from pjx import PJXEnvironment

# Auto-discovery (installed extras register via entry points)
env = PJXEnvironment(loader=FileSystemLoader("templates"))

# Explicit registration
from pjx_htmx.extension import HTMXExtension
env = PJXEnvironment(
    loader=FileSystemLoader("templates"),
    extensions=[HTMXExtension()],
)
```

## Features

- Components with uppercase tags like `<UserCard />`
- Control flow with `<For>`, `<Show>`, `<Switch>`, and `<Fragment>`
- Frontmatter with `props:`, `vars:`, `computed:`, and slots
- Conditional and spread attributes
- Unified `PJXExtension` ABC for processors, globals, and asset providers
- HTMX and SSE aliases via `pjx-htmx` (`HTMXExtension`)
- Stimulus aliases via `pjx-stimulus` (`StimulusExtension`)
- `cn()` Tailwind class merging via `pjx-tailwind` (`TailwindExtension`)
- Browser asset injection (CDN or vendor mode)
- FastAPI helpers via `PJXRouter`
- CLI: `check`, `check --fix`, `format`, `sitemap`, `skills`, `assets build`, `assets add`, `assets list`, `assets remove`, `demo`

## CLI

```bash
pjx check templates/
pjx check templates/ --fix
pjx format templates/
pjx sitemap templates/ --base-url https://example.com
pjx skills --claude
pjx assets build static/vendor/pjx
pjx assets add alpinejs@3 --dist alpinejs/dist/cdn.min.js --out js/alpine.min.js
pjx assets list
pjx assets remove alpinejs
pjx demo
```

`pjx check --fix` applies safe technical autofixes.
`pjx format` handles formatting and frontmatter layout.
`pjx assets build` vendors browser assets via npm, merging extension and manifest packages.
`pjx assets add` adds an npm package to the `pjx-assets.json` manifest.
`pjx assets list` shows all assets from extensions and the manifest.
`pjx assets remove` removes a package from the manifest.
`pjx demo` launches the bundled demo application.

## Monorepo

```text
src/
  pjx/              # Core package (includes bundled demo)
  pjx-htmx/         # HTMXExtension: HTMX + SSE aliases and asset injection
  pjx-stimulus/     # StimulusExtension: Stimulus aliases and asset injection
  pjx-tailwind/     # TailwindExtension: cn() global and asset injection
skills/             # Bundled PJX skill
```

## Requirements

- Python >= 3.12

## License

MIT
