"""Example PJX + FastAPI application.

Demonstrates:
- Page routing with ``@pjx.page()``
- Component rendering with ``pjx.render()`` (HTMX partials)
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
from html import escape as _esc
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from markupsafe import Markup
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


def _render_todo_list(status: str = "all") -> str:
    """Render the TodoList component as an HTML fragment."""
    return pjx.render(
        "components/TodoList.jinja",
        {
            "todos": _filter_todos(status),
            "empty_message": EMPTY_LABELS.get(status, EMPTY_LABELS["all"]),
            "done_count": sum(1 for t in todos_db if t["done"]),
            "total_count": len(todos_db),
        },
    )


def _render_search_results(query: str) -> str:
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
    return pjx.render(
        "components/SearchResults.jinja",
        {"results": matches, "query": query},
    )


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
    return {"todo_list": Markup(_render_todo_list())}


@pjx.page("/search", template="pages/SearchDemo.jinja", title="Search — PJX")
async def search() -> dict[str, object]:
    """Search users — HTMX debounce."""
    return {"search_results": Markup(_render_search_results(""))}


@pjx.page("/clock", template="pages/ClockDemo.jinja", title="Clock — PJX")
async def clock() -> dict[str, object]:
    """Live clock — SSE streaming."""
    return {"clock": Markup(_render_clock())}


# -- SSE endpoints -----------------------------------------------------------


def _render_clock() -> str:
    """Render the Clock component with current server time."""
    now = datetime.now(timezone.utc).astimezone()
    return pjx.render(
        "components/Clock.jinja",
        {
            "time": now.strftime("%H:%M:%S"),
            "date": now.strftime("%d %b %Y"),
            "weekday": now.strftime("%A"),
            "timezone": now.strftime("%Z (UTC%z)"),
        },
    )


async def _clock_generator():
    """Yield clock HTML every second as SSE events."""
    while True:
        yield {"event": "clock", "data": _render_clock()}
        await asyncio.sleep(1)


@app.get("/sse/clock")
async def sse_clock():
    """SSE endpoint — streams the clock component every second."""
    return EventSourceResponse(_clock_generator())


# -- HTMX partials (HTML fragments) ------------------------------------------


def _render_server_counter() -> str:
    """Render the ServerCounter component as an HTML fragment."""
    return pjx.render(
        "components/ServerCounter.jinja", {"count": server_counter["count"]}
    )


@app.post("/htmx/counter/increment")
async def htmx_counter_increment() -> HTMLResponse:
    """Increment the server counter."""
    server_counter["count"] += 1
    return HTMLResponse(_render_server_counter())


@app.post("/htmx/counter/decrement")
async def htmx_counter_decrement() -> HTMLResponse:
    """Decrement the server counter."""
    server_counter["count"] -= 1
    return HTMLResponse(_render_server_counter())


@app.post("/htmx/counter/reset")
async def htmx_counter_reset() -> HTMLResponse:
    """Reset the server counter."""
    server_counter["count"] = 0
    return HTMLResponse(_render_server_counter())


@app.post("/htmx/todos/add")
async def htmx_add_todo(request: Request) -> HTMLResponse:
    """Add a new todo from form data."""
    form = await request.form()
    text = str(form.get("text", "")).strip()
    status = str(form.get("status", "all"))
    if text:
        todos_db.append({"text": text, "done": False})
    return HTMLResponse(_render_todo_list(status))


@app.post("/htmx/todos/{idx}/toggle")
async def htmx_toggle_todo(idx: int, request: Request) -> HTMLResponse:
    """Toggle a todo's done state."""
    if 0 <= idx < len(todos_db):
        todos_db[idx]["done"] = not todos_db[idx]["done"]
    form = await request.form()
    status = str(form.get("status", "all"))
    return HTMLResponse(_render_todo_list(status))


@app.get("/htmx/todos/filter")
async def htmx_filter_todos(status: str = "all") -> HTMLResponse:
    """Filter todos by status — returns HTML fragment."""
    return HTMLResponse(_render_todo_list(status))


@app.delete("/htmx/todos/{idx}")
async def htmx_delete_todo(idx: int, request: Request) -> HTMLResponse:
    """Delete a todo."""
    if 0 <= idx < len(todos_db):
        todos_db.pop(idx)
    form = await request.form()
    status = str(form.get("status", "all"))
    return HTMLResponse(_render_todo_list(status))


@app.put("/htmx/todos/{idx}")
async def htmx_edit_todo(idx: int, request: Request) -> HTMLResponse:
    """Edit a todo's text from form data."""
    form = await request.form()
    text = str(form.get("text", "")).strip()
    status = str(form.get("status", "all"))
    if 0 <= idx < len(todos_db) and text:
        todos_db[idx]["text"] = text
    return HTMLResponse(_render_todo_list(status))


@app.get("/htmx/search")
async def htmx_search(query: str = "") -> HTMLResponse:
    """Search users — returns HTML fragment."""
    return HTMLResponse(_render_search_results(query))


@app.post("/htmx/message/{user_id}")
async def htmx_message(user_id: int) -> HTMLResponse:
    """Send a message — returns toast notification via Toast component."""
    user = next((u for u in USERS if u.id == user_id), None)
    if not user:
        return HTMLResponse(
            pjx.render(
                "components/Toast.jinja",
                {"message": "User not found", "variant": "error"},
            )
        )
    messages_db.append({"to": user.name, "text": "Hello!"})
    return HTMLResponse(
        pjx.render(
            "components/Toast.jinja",
            {"message": f"Message sent to {_esc(user.name)}!", "variant": "success"},
        )
    )


# -- JSON API -----------------------------------------------------------------


@app.get("/api/users")
async def api_users() -> list[User]:
    """Return all users as JSON."""
    return USERS


@app.get("/api/users/{user_id}")
async def api_user(user_id: int) -> User:
    """Return a single user by ID."""
    for user in USERS:
        if user.id == user_id:
            return user
    raise HTTPException(status_code=404, detail="User not found")


@app.get("/api/todos")
async def api_todos() -> list[dict[str, object]]:
    """Return all todos as JSON."""
    return todos_db


@app.get("/api/search")
async def api_search(query: str = "") -> list[User]:
    """Search users by name or email — returns JSON."""
    if not query:
        return []
    q = query.lower()
    return [u for u in USERS if q in u.name.lower() or q in u.email.lower()]


# -- Entrypoint ---------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
