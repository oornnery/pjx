"""PJX Demo — full-featured example application.

Demonstrates:
- Structured project layout (app/, pages/, api/, models/, services/, middleware/)
- Page routing with ``@pjx.page()``
- ``pjx.partial()`` for HTMX HTML fragments
- Layout components (``<VStack>``, ``<HStack>``, ``<Grid>``, etc.)
- PJX middleware (``@pjx.middleware("auth")``)
- Attrs passthrough (``data-user-id`` on UserCard → ``{{ attrs }}``)
- Asset pipeline (``css``/``js`` in frontmatter → ``{{ pjx_assets.render() }}``)
- CSRF protection, signed sessions, rate limiting
- Basecoat UI component showcase

Run with::

    cd examples/demo && pjx dev .
"""

from __future__ import annotations

from pathlib import Path

from fastapi import Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from fastapi import FastAPI

from pjx import PJX, PJXConfig, SEO

from app.core.config import settings
from app.middleware import generic_exception_handler, require_auth, security_headers
from app.services import USERS, server_counter

app = FastAPI(title=settings.PROJECT_NAME)

# -- Rate limiting -----------------------------------------------------------
from app.pages import limiter  # noqa: E402

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# -- Middleware --------------------------------------------------------------

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
    max_age=3600,
    https_only=False,
    same_site="lax",
)

app.middleware("http")(security_headers)
app.add_exception_handler(Exception, generic_exception_handler)

# -- PJX setup ---------------------------------------------------------------

pjx = PJX(
    app,
    config=PJXConfig(toml_path=Path(__file__).parents[1] / "pjx.toml"),
    seo=SEO(
        title=settings.PROJECT_NAME,
        description="Example application built with PJX.",
        og_type="website",
    ),
    csrf=True,
    csrf_secret=settings.SECRET_KEY,
    csrf_exempt_paths={
        "/sse/clock",
        "/api/v1/users",
        "/api/v1/todos",
        "/health",
        "/ready",
    },
    health=True,
)

pjx.middleware("auth")(require_auth)

# -- Routers -----------------------------------------------------------------

from app.pages import router as pages_router  # noqa: E402
from app.api.v1 import router as api_router  # noqa: E402

app.include_router(pages_router)
app.include_router(api_router, prefix="/api/v1")

# -- Pages (PJX template routes) --------------------------------------------


@pjx.page("/", template="pages/Dashboard.jinja", title="Dashboard — PJX")
async def index() -> dict[str, object]:
    return {"title": "Dashboard", "users": [u.model_dump() for u in USERS]}


@pjx.page("/counter", template="pages/CounterDemo.jinja", title="Counter — PJX")
async def counter() -> dict[str, object]:
    return {"server_count": server_counter["count"]}


@pjx.page("/todos", template="pages/TodoDemo.jinja", title="Todos — PJX")
async def todos() -> dict[str, object]:
    from app.pages import _todo_list_html

    return {"todo_list": _todo_list_html()}


@pjx.page("/search", template="pages/SearchDemo.jinja", title="Search — PJX")
async def search() -> dict[str, object]:
    from app.pages import _search_html

    return {"search_results": _search_html("")}


@pjx.page("/clock", template="pages/ClockDemo.jinja", title="Clock — PJX")
async def clock() -> dict[str, object]:
    from app.pages import _clock_html

    return {"clock": _clock_html()}


@pjx.page(
    "/components", template="pages/ComponentsDemo.jinja", title="Components — PJX"
)
async def components() -> dict[str, object]:
    return {}


@pjx.page("/login", template="pages/Login.jinja", title="Login — PJX")
async def login() -> dict[str, object]:
    return {}


@pjx.page("/protected", template="pages/Protected.jinja", title="Protected — PJX")
async def protected(request: Request) -> dict[str, object]:
    user = request.session.get("user", "Guest")
    return {"user": user}


# -- Entrypoint --------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
