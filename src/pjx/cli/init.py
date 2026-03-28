"""``pjx init`` — scaffold a new PJX project with a working example app."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from pjx.assets import ensure_project_dirs
from pjx.cli.common import console, err_console  # noqa: F401
from pjx.config import PJXConfig

app = typer.Typer()

# ---------------------------------------------------------------------------
# pjx.toml
# ---------------------------------------------------------------------------

_TOML_TEMPLATE = """\
engine = "hybrid"
debug = true

template_dirs = ["app/templates"]
static_dir = "app/static"
pages_dir = "app/templates/pages"
components_dir = "app/templates/components"
layouts_dir = "app/templates/layouts"
ui_dir = "app/templates/ui"
vendor_templates_dir = "app/templates/vendor"
vendor_static_dir = "app/static/vendor"
"""

# ---------------------------------------------------------------------------
# app/core/config.py
# ---------------------------------------------------------------------------

_CORE_CONFIG_TEMPLATE = """\
\"\"\"Application settings — loaded from environment variables.\"\"\"

import os


class Settings:
    PROJECT_NAME: str = "{project_name}"
    SECRET_KEY: str = os.environ.get("PJX_SECRET_KEY", "change-me-in-production")
    HOST: str = "127.0.0.1"
    PORT: int = 8000


settings = Settings()
"""

# ---------------------------------------------------------------------------
# app/main.py
# ---------------------------------------------------------------------------

_MAIN_TEMPLATE = """\
\"\"\"Application entrypoint.

Run with::

    cd {project_name} && pjx dev .
\"\"\"

from pathlib import Path

from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware

from pjx import PJX, PJXConfig, SEO

from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
    max_age=3600,
    same_site="lax",
)

pjx = PJX(
    app,
    config=PJXConfig(toml_path=Path(__file__).parents[1] / "pjx.toml"),
    seo=SEO(title=settings.PROJECT_NAME, description="Built with PJX."),
    csrf=True,
    csrf_secret=settings.SECRET_KEY,
    health=True,
)

# -- Routers -----------------------------------------------------------------
from app.pages.routes import router as pages_router  # noqa: E402

app.include_router(pages_router)


# -- Pages -------------------------------------------------------------------


@pjx.page("/", template="pages/Home.jinja", title="Home — {project_name}")
async def home() -> dict[str, object]:
    from app.services.counter import counter_state

    return {{"count": counter_state["count"]}}


@pjx.page("/about", template="pages/About.jinja", title="About — {project_name}")
async def about() -> dict[str, object]:
    return {{}}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
"""

# ---------------------------------------------------------------------------
# app/services/counter.py
# ---------------------------------------------------------------------------

_SERVICES_COUNTER_TEMPLATE = """\
\"\"\"Counter service — in-memory state.\"\"\"

counter_state: dict[str, int] = {"count": 0}
"""

# ---------------------------------------------------------------------------
# app/pages/routes.py
# ---------------------------------------------------------------------------

_PAGES_ROUTES_TEMPLATE = """\
\"\"\"Page routes — HTMX partials and server-side actions.\"\"\"

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.services.counter import counter_state

router = APIRouter()


def _pjx():
    \"\"\"Lazy import to avoid circular dependency.\"\"\"
    from app.main import pjx

    return pjx


def _counter_html() -> str:
    return _pjx().partial(
        "components/Counter.jinja", count=counter_state["count"]
    )


@router.post("/htmx/counter/increment")
async def htmx_counter_increment() -> HTMLResponse:
    counter_state["count"] += 1
    return HTMLResponse(_counter_html())


@router.post("/htmx/counter/decrement")
async def htmx_counter_decrement() -> HTMLResponse:
    counter_state["count"] -= 1
    return HTMLResponse(_counter_html())


@router.post("/htmx/counter/reset")
async def htmx_counter_reset() -> HTMLResponse:
    counter_state["count"] = 0
    return HTMLResponse(_counter_html())
"""

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_LAYOUT_TEMPLATE = """\
---
props {{
  title: str = "{project_name}",
}}

slot default

css "/static/css/style.css"
---

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{{{{ seo.title|default(props.title) }}}}</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚡</text></svg>" />

  {{{{ pjx_assets.render_css() }}}}

  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
  <script src="https://unpkg.com/htmx.org@2/dist/htmx.min.js"></script>
</head>
<body hx-headers='{{% if csrf_token is defined %}}{{"X-CSRFToken": "{{{{ csrf_token() }}}}"}}{{% endif %}}'>
  <nav class="navbar">
    <a href="/" class="navbar__brand">⚡ {project_name}</a>
    <div class="navbar__links">
      <a href="/">Home</a>
      <a href="/about">About</a>
    </div>
  </nav>

  <main class="container">
    <Slot />
  </main>

  <footer class="footer">
    <p>Built with <a href="https://github.com/oornnery/pjx">PJX</a></p>
  </footer>

  {{{{ pjx_assets.render_js() }}}}
</body>
</html>
"""

_HOME_TEMPLATE = """\
---
import Layout from "../layouts/Base.jinja"
import Counter from "../components/Counter.jinja"

state count = 0
---

<Layout title="Home">
  <div class="hero">
    <h1>Welcome to PJX</h1>
    <p class="hero__subtitle">
      Reactive components for Python — Jinja2 + HTMX + Alpine.js
    </p>
  </div>

  <section class="section">
    <h2>Client-side Counter (Alpine.js)</h2>
    <p>This counter runs entirely in the browser — no server calls.</p>

    <div class="counter" reactive>
      <button class="btn btn--danger" on:click="count--">−</button>
      <span class="counter__value" x-text="count">0</span>
      <button class="btn btn--success" on:click="count++">+</button>
      <button class="btn btn--secondary" on:click="count = 0">Reset</button>
    </div>
  </section>

  <section class="section">
    <h2>Server-side Counter (HTMX)</h2>
    <p>This counter talks to the server on every click.</p>
    <Counter count="{{ count }}" />
  </section>
</Layout>
"""

_ABOUT_TEMPLATE = """\
---
import Layout from "../layouts/Base.jinja"
---

<Layout title="About">
  <div class="section">
    <h1>About {project_name}</h1>
    <p>This project was scaffolded with <code>pjx init</code>.</p>

    <h2>What's inside?</h2>
    <ul>
      <li><strong>FastAPI</strong> — async Python web framework</li>
      <li><strong>PJX</strong> — reactive component DSL for Jinja2</li>
      <li><strong>Alpine.js</strong> — lightweight client-side reactivity</li>
      <li><strong>HTMX</strong> — server-driven UI updates</li>
    </ul>

    <h2>Project Structure</h2>
    <pre><code>{project_name}/
├── pjx.toml             # Configuration
├── app/
│   ├── main.py           # FastAPI + PJX entrypoint
│   ├── core/config.py    # Settings
│   ├── pages/routes.py   # HTMX endpoints
│   ├── services/         # Business logic
│   ├── templates/
│   │   ├── pages/        # Page templates
│   │   ├── components/   # Reusable components
│   │   └── layouts/      # Base layouts
│   └── static/
│       └── css/style.css # Styles</code></pre>

    <h2>Next steps</h2>
    <ol>
      <li>Edit <code>app/templates/pages/Home.jinja</code> to customize the home page</li>
      <li>Create new components in <code>app/templates/components/</code></li>
      <li>Add HTMX endpoints in <code>app/pages/routes.py</code></li>
      <li>Run <code>pjx check</code> to validate your components</li>
    </ol>
  </div>
</Layout>
"""

_COUNTER_COMPONENT = """\
---
props {
  count: int = 0,
}
---

<div id="server-counter" class="counter">
  <button class="btn btn--danger"
    action:post="/htmx/counter/decrement"
    target="#server-counter"
    swap="outerHTML">\u2212</button>
  <span class="counter__value">{{ props.count }}</span>
  <button class="btn btn--success"
    action:post="/htmx/counter/increment"
    target="#server-counter"
    swap="outerHTML">+</button>
  <button class="btn btn--secondary"
    action:post="/htmx/counter/reset"
    target="#server-counter"
    swap="outerHTML">Reset</button>
</div>
"""

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_STYLE_CSS = """\
/* ── Reset ────────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: system-ui, -apple-system, sans-serif;
  line-height: 1.6;
  color: #1a1a2e;
  background: #f8f9fa;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

a { color: #6c63ff; text-decoration: none; }
a:hover { text-decoration: underline; }

code, pre {
  font-family: "JetBrains Mono", "Fira Code", monospace;
  background: #e9ecef;
  border-radius: 4px;
}
code { padding: 0.15em 0.4em; font-size: 0.9em; }
pre { padding: 1rem; overflow-x: auto; font-size: 0.85em; }

ul, ol { padding-left: 1.5rem; }
li { margin-bottom: 0.25rem; }

/* ── Navbar ───────────────────────────────────────────────────────────── */
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 2rem;
  background: #1a1a2e;
  color: #fff;
}

.navbar__brand {
  font-size: 1.25rem;
  font-weight: 700;
  color: #fff;
}
.navbar__brand:hover { text-decoration: none; }

.navbar__links { display: flex; gap: 1.5rem; }
.navbar__links a { color: #ccc; transition: color 0.2s; }
.navbar__links a:hover { color: #fff; text-decoration: none; }

/* ── Container ────────────────────────────────────────────────────────── */
.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  flex: 1;
}

/* ── Hero ─────────────────────────────────────────────────────────────── */
.hero {
  text-align: center;
  padding: 3rem 0 2rem;
}

.hero h1 {
  font-size: 2.5rem;
  background: linear-gradient(135deg, #6c63ff, #e94560);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero__subtitle {
  margin-top: 0.5rem;
  font-size: 1.1rem;
  color: #666;
}

/* ── Section ──────────────────────────────────────────────────────────── */
.section {
  margin-bottom: 2.5rem;
}

.section h2 {
  font-size: 1.4rem;
  margin-bottom: 0.5rem;
  color: #1a1a2e;
}

.section p {
  color: #555;
  margin-bottom: 1rem;
}

/* ── Counter ──────────────────────────────────────────────────────────── */
.counter {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  width: fit-content;
}

.counter__value {
  font-size: 1.5rem;
  font-weight: 700;
  min-width: 3rem;
  text-align: center;
  color: #1a1a2e;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.1s, box-shadow 0.2s;
}
.btn:hover { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,0.12); }
.btn:active { transform: translateY(0); }

.btn--success { background: #10b981; color: #fff; }
.btn--danger  { background: #ef4444; color: #fff; }
.btn--secondary { background: #e5e7eb; color: #374151; }

/* ── Footer ───────────────────────────────────────────────────────────── */
.footer {
  text-align: center;
  padding: 1.5rem;
  color: #999;
  font-size: 0.85rem;
  border-top: 1px solid #e5e7eb;
}
"""

# ---------------------------------------------------------------------------
# Package __init__.py stubs
# ---------------------------------------------------------------------------

_CORE_INIT = '"""Core — configuration, security, shared dependencies."""\n'
_MODELS_INIT = '"""Data models — Pydantic schemas and domain objects."""\n'
_SERVICES_INIT = """\
\"\"\"Business logic — pure functions and service classes.\"\"\"

from app.services.counter import counter_state

__all__ = ["counter_state"]
"""
_PAGES_INIT = """\
\"\"\"Page routes.\"\"\"

from app.pages.routes import router

__all__ = ["router"]
"""
_API_INIT = ""
_API_V1_INIT = """\
\"\"\"API v1 — JSON endpoints.\"\"\"

from fastapi import APIRouter

router = APIRouter(tags=["v1"])
"""
_MIDDLEWARE_INIT = '"""Custom middleware."""\n'

# ---------------------------------------------------------------------------
# Scaffold structure
# ---------------------------------------------------------------------------

_APP_PACKAGES: list[tuple[str, str]] = [
    ("core", _CORE_INIT),
    ("models", _MODELS_INIT),
    ("services", _SERVICES_INIT),
    ("pages", _PAGES_INIT),
    ("api", _API_INIT),
    ("api/v1", _API_V1_INIT),
    ("middleware", _MIDDLEWARE_INIT),
]


def _write_if_missing(path: Path, content: str) -> bool:
    """Write *content* to *path* only if it doesn't already exist."""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return True


@app.command()
def init(
    directory: Annotated[
        Path, typer.Argument(help="Directory to scaffold the project in")
    ] = Path("."),
) -> None:
    """Scaffold a new PJX project with a working example app."""
    directory.mkdir(parents=True, exist_ok=True)
    project_name = directory.resolve().name

    # pjx.toml at project root
    toml_path = directory / "pjx.toml"
    if _write_if_missing(toml_path, _TOML_TEMPLATE):
        console.print(f"  Created {toml_path}")

    config = PJXConfig(toml_path=toml_path)

    # Template + static directories
    dirs = ensure_project_dirs(config)

    # app/ package with submodules
    app_dir = directory / "app"
    _write_if_missing(app_dir / "__init__.py", "")

    for subpackage, init_content in _APP_PACKAGES:
        pkg_dir = app_dir / subpackage
        pkg_dir.mkdir(parents=True, exist_ok=True)
        _write_if_missing(pkg_dir / "__init__.py", init_content)

    # Core config
    if _write_if_missing(
        app_dir / "core" / "config.py",
        _CORE_CONFIG_TEMPLATE.format(project_name=project_name),
    ):
        console.print("  Created app/core/config.py")

    # Main application
    if _write_if_missing(
        app_dir / "main.py",
        _MAIN_TEMPLATE.format(project_name=project_name),
    ):
        console.print("  Created app/main.py")

    # Counter service
    if _write_if_missing(
        app_dir / "services" / "counter.py",
        _SERVICES_COUNTER_TEMPLATE,
    ):
        console.print("  Created app/services/counter.py")

    # Page routes
    if _write_if_missing(
        app_dir / "pages" / "routes.py",
        _PAGES_ROUTES_TEMPLATE,
    ):
        console.print("  Created app/pages/routes.py")

    # Layout
    layout = config.layouts_dir / "Base.jinja"
    if _write_if_missing(layout, _LAYOUT_TEMPLATE.format(project_name=project_name)):
        console.print(f"  Created {layout}")

    # Home page
    home = config.pages_dir / "Home.jinja"
    if _write_if_missing(home, _HOME_TEMPLATE):
        console.print(f"  Created {home}")

    # About page
    about = config.pages_dir / "About.jinja"
    if _write_if_missing(about, _ABOUT_TEMPLATE.format(project_name=project_name)):
        console.print(f"  Created {about}")

    # Counter component
    counter = config.components_dir / "Counter.jinja"
    if _write_if_missing(counter, _COUNTER_COMPONENT):
        console.print(f"  Created {counter}")

    # CSS
    css_file = config.static_dir / "css" / "style.css"
    if _write_if_missing(css_file, _STYLE_CSS):
        console.print(f"  Created {css_file}")

    for d in dirs:
        console.print(f"  {d}/")

    console.print(f"\n✨ PJX project initialized in {directory}/")
    console.print(f"\n  cd {directory} && pjx dev .")
    console.print("  Open http://localhost:8000")
