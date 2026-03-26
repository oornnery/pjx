"""Example PJX + FastAPI application.

Demonstrates:
- File-based routing with ``pjx.auto_routes()``
- Explicit page routing with ``@pjx.page()``
- ``pjx.partial()`` for rendering components (no ``Markup()`` needed)
- Layout components (``<VStack>``, ``<HStack>``, ``<Grid>``, etc.)
- Middleware (``@pjx.middleware("auth")``)
- Attrs passthrough (``data-user-id`` on UserCard → ``{{ attrs }}``)
- Asset pipeline (``css``/``js`` in frontmatter → ``{{ pjx_assets.render() }}``)
- Runtime prop validation (``validate_props = true`` in pjx.toml)

Run with::

    uv run examples/app.py
    # or
    cd examples && pjx dev .

Validate components::

    cd examples && pjx check .
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from pjx import PJX, SEO, PJXConfig

app = FastAPI()


@app.middleware("http")
async def no_cache_static(request: Request, call_next):  # noqa: ANN001
    """Disable browser cache for static files in dev mode."""
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
    return response


pjx = PJX(
    app,
    config=PJXConfig(toml_path=Path(__file__).parent / "pjx.toml"),
    seo=SEO(
        title="PJX App",
        description="Example application built with PJX.",
        og_type="website",
    ),
)


# -- Middleware ---------------------------------------------------------------


@pjx.middleware("auth")
async def require_auth(request: Request) -> None:
    """Check if user is logged in. Redirects to /login if not."""
    if not request.cookies.get("session"):
        raise HTTPException(status_code=303, headers={"Location": "/login"})


# -- Models -------------------------------------------------------------------


class User(BaseModel):
    """User card data."""

    id: int
    name: str
    email: str
    avatar: str = "/static/images/default.svg"


class Todo(BaseModel):
    """Single todo entry."""

    text: str
    done: bool = False


# -- In-memory data -----------------------------------------------------------

USERS = [
    User(
        id=1, name="Alice", email="alice@example.com", avatar="/static/images/alice.svg"
    ),
    User(id=2, name="Bob", email="bob@example.com", avatar="/static/images/bob.svg"),
    User(
        id=3,
        name="Charlie",
        email="charlie@example.com",
        avatar="/static/images/charlie.svg",
    ),
]

todos_db: list[dict[str, object]] = [
    {"text": "Learn PJX", "done": True},
    {"text": "Build components", "done": False},
    {"text": "Ship it", "done": False},
]

messages_db: list[dict[str, str]] = []

server_counter: dict[str, int] = {"count": 0}


# -- Rendering helpers --------------------------------------------------------

EMPTY_LABELS = {
    "all": "No todos yet. Add one above!",
    "done": "No completed todos.",
    "pending": "No pending todos.",
}


def _filter_todos(status: str = "all") -> list[dict[str, object]]:
    """Return filtered todos with their original index."""
    return [
        {"idx": i, "text": t["text"], "done": t["done"]}
        for i, t in enumerate(todos_db)
        if status == "all"
        or (status == "done" and t["done"])
        or (status == "pending" and not t["done"])
    ]


def _todo_list_html(status: str = "all") -> str:
    """Render the TodoList component as an HTML fragment."""
    return pjx.partial(
        "components/TodoList.jinja",
        todos=_filter_todos(status),
        empty_message=EMPTY_LABELS.get(status, EMPTY_LABELS["all"]),
        done_count=sum(1 for t in todos_db if t["done"]),
        total_count=len(todos_db),
    )


def _search_html(query: str) -> str:
    """Render the SearchResults component as an HTML fragment."""
    q = query.strip().lower()
    matches = (
        [
            {"name": u.name, "email": u.email, "avatar": u.avatar}
            for u in USERS
            if q in u.name.lower() or q in u.email.lower()
        ]
        if q
        else []
    )
    return pjx.partial("components/SearchResults.jinja", results=matches, query=query)


def _clock_html() -> str:
    """Render the Clock component with current server time."""
    now = datetime.now(timezone.utc).astimezone()
    return pjx.partial(
        "components/Clock.jinja",
        time=now.strftime("%H:%M:%S"),
        date=now.strftime("%d %b %Y"),
        weekday=now.strftime("%A"),
        timezone=now.strftime("%Z (UTC%z)"),
    )


def _counter_html() -> str:
    """Render the ServerCounter component as an HTML fragment."""
    return pjx.partial("components/ServerCounter.jinja", count=server_counter["count"])


# -- Pages --------------------------------------------------------------------


@pjx.page("/", template="pages/Dashboard.jinja", title="Dashboard — PJX")
async def index() -> dict[str, object]:
    """Dashboard with user cards and message buttons."""
    return {
        "title": "Dashboard",
        "users": [u.model_dump() for u in USERS],
    }


@pjx.page("/counter", template="pages/CounterDemo.jinja", title="Counter — PJX")
async def counter() -> dict[str, object]:
    """Counter demo — Alpine.js (client) vs HTMX (server) side by side."""
    return {"server_count": server_counter["count"]}


@pjx.page("/todos", template="pages/TodoDemo.jinja", title="Todos — PJX")
async def todos() -> dict[str, object]:
    """Todo list — HTMX CRUD."""
    return {"todo_list": _todo_list_html()}


@pjx.page("/search", template="pages/SearchDemo.jinja", title="Search — PJX")
async def search() -> dict[str, object]:
    """Search users — HTMX debounce."""
    return {"search_results": _search_html("")}


@pjx.page("/clock", template="pages/ClockDemo.jinja", title="Clock — PJX")
async def clock() -> dict[str, object]:
    """Live clock — SSE streaming."""
    return {"clock": _clock_html()}


@pjx.page("/login", template="pages/Login.jinja", title="Login — PJX")
async def login() -> dict[str, object]:
    """Login page — no layout, standalone."""
    return {}


@pjx.page("/protected", template="pages/Protected.jinja", title="Protected — PJX")
async def protected(request: Request) -> dict[str, object]:
    """Protected page — requires auth cookie."""
    user = request.cookies.get("session", "Guest")
    return {"user": user}


# -- Auth endpoints -----------------------------------------------------------


@app.post("/auth/login")
async def auth_login(request: Request) -> Response:
    """Handle login form — set session cookie and redirect."""
    form = await request.form()
    username = str(form.get("username", "")).strip()
    is_htmx = request.headers.get("HX-Request") == "true"
    if not username:
        return HTMLResponse(
            pjx.partial(
                "components/Toast.jinja",
                message="Username is required",
                variant="error",
            )
        )
    if is_htmx:
        # HTMX: use HX-Redirect for full-page navigation
        response = HTMLResponse("", headers={"HX-Redirect": "/protected"})
    else:
        response = RedirectResponse("/protected", status_code=303)
    response.set_cookie("session", username, max_age=3600)
    return response


@app.post("/auth/logout")
async def auth_logout(request: Request) -> Response:
    """Clear session cookie and redirect to login."""
    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        response = HTMLResponse("", headers={"HX-Redirect": "/login"})
    else:
        response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("session")
    return response


# -- SSE endpoints -----------------------------------------------------------


async def _clock_generator():
    """Yield clock HTML every second as SSE events."""
    while True:
        yield {"event": "clock", "data": _clock_html()}
        await asyncio.sleep(1)


@app.get("/sse/clock")
async def sse_clock():
    """SSE endpoint — streams the clock component every second."""
    return EventSourceResponse(_clock_generator())


# -- HTMX partials (HTML fragments) ------------------------------------------


@app.post("/htmx/counter/increment")
async def htmx_counter_increment() -> HTMLResponse:
    """Increment the server counter."""
    server_counter["count"] += 1
    return HTMLResponse(_counter_html())


@app.post("/htmx/counter/decrement")
async def htmx_counter_decrement() -> HTMLResponse:
    """Decrement the server counter."""
    server_counter["count"] -= 1
    return HTMLResponse(_counter_html())


@app.post("/htmx/counter/reset")
async def htmx_counter_reset() -> HTMLResponse:
    """Reset the server counter."""
    server_counter["count"] = 0
    return HTMLResponse(_counter_html())


@app.post("/htmx/todos/add")
async def htmx_add_todo(request: Request) -> HTMLResponse:
    """Add a new todo from form data."""
    form = await request.form()
    text = str(form.get("text", "")).strip()
    status = str(form.get("status", "all"))
    if text:
        todos_db.append({"text": text, "done": False})
    return HTMLResponse(_todo_list_html(status))


@app.post("/htmx/todos/{idx}/toggle")
async def htmx_toggle_todo(idx: int, request: Request) -> HTMLResponse:
    """Toggle a todo's done state."""
    if 0 <= idx < len(todos_db):
        todos_db[idx]["done"] = not todos_db[idx]["done"]
    form = await request.form()
    status = str(form.get("status", "all"))
    return HTMLResponse(_todo_list_html(status))


@app.get("/htmx/todos/filter")
async def htmx_filter_todos(status: str = "all") -> HTMLResponse:
    """Filter todos by status — returns HTML fragment."""
    return HTMLResponse(_todo_list_html(status))


@app.delete("/htmx/todos/{idx}")
async def htmx_delete_todo(idx: int, request: Request) -> HTMLResponse:
    """Delete a todo."""
    if 0 <= idx < len(todos_db):
        todos_db.pop(idx)
    form = await request.form()
    status = str(form.get("status", "all"))
    return HTMLResponse(_todo_list_html(status))


@app.put("/htmx/todos/{idx}")
async def htmx_edit_todo(idx: int, request: Request) -> HTMLResponse:
    """Edit a todo's text from form data."""
    form = await request.form()
    text = str(form.get("text", "")).strip()
    status = str(form.get("status", "all"))
    if 0 <= idx < len(todos_db) and text:
        todos_db[idx]["text"] = text
    return HTMLResponse(_todo_list_html(status))


@app.get("/htmx/search")
async def htmx_search(query: str = "") -> HTMLResponse:
    """Search users — returns HTML fragment."""
    return HTMLResponse(_search_html(query))


@app.post("/htmx/message/{user_id}")
async def htmx_message(user_id: int) -> HTMLResponse:
    """Send a message — returns toast notification via Toast component."""
    user = next((u for u in USERS if u.id == user_id), None)
    if not user:
        return HTMLResponse(
            pjx.partial(
                "components/Toast.jinja", message="User not found", variant="error"
            )
        )
    messages_db.append({"to": user.name, "text": "Hello!"})
    return HTMLResponse(
        pjx.partial(
            "components/Toast.jinja",
            message=f"Message sent to {user.name}!",
            variant="success",
        )
    )


# -- JSON API -----------------------------------------------------------------


@app.get("/api/users")
async def api_users() -> list[User]:
    """Return all users as JSON."""
    return USERS


@app.get("/api/todos")
async def api_todos() -> list[dict[str, object]]:
    """Return all todos as JSON."""
    return todos_db


# -- Entrypoint ---------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
