# PJX Skill

PJX is a Jinja2 preprocessor with JSX-like syntax for FastAPI + HTMX + Stimulus.

## Install

```bash
pip install pjx[all]   # core + htmx + stimulus + tailwind
pip install pjx         # core only (no aliases)
```

## Quick Setup

```python
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from jinja2 import FileSystemLoader
from pjx import PJXEnvironment
from pjx.router import PJXRouter

app = FastAPI()
templates = Jinja2Templates(
    env=PJXEnvironment(loader=FileSystemLoader("templates"))
)
ui = PJXRouter(templates)
app.include_router(ui)
```

## How It Works

PJX compiles declarative syntax to standard Jinja2 at template load time.
No build step, no runtime overhead. The generated Jinja2 is always inspectable
via `env.get_preprocessed_source("template.jinja")`.

Extras (htmx, stimulus, tailwind) are auto-discovered via entry points —
install the package and it just works.

## When to Use PJX

- Building server-rendered apps with FastAPI + HTMX
- Want component-based DX without a JS framework
- Need typed props and template validation
- Want Stimulus integration without verbose data-* attributes

## When NOT to Use PJX

- SPA/client-rendered apps (use React/Vue instead)
- Static sites without FastAPI (use plain Jinja2)
- Projects that need Alpine.js (PJX uses Stimulus, not Alpine)

## References

- [Template Syntax](references/syntax.md) — DSL, frontmatter, components, aliases
- [Template Structure](references/structure.md) — demo-based folder layout, route files, imports
- [Router Patterns](references/router.md) — decorators, FormData, SSE, error pages
- [CLI Guide](references/cli.md) — `pjx check`, `pjx format`, and `pjx sitemap`
