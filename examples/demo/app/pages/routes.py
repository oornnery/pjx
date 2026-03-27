"""Page routes — server-rendered HTML via PJX templates."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sse_starlette.sse import EventSourceResponse

from app.services.data import (
    EMPTY_LABELS,
    USERS,
    clock_context,
    filter_todos,
    messages_db,
    server_counter,
    todos_db,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _pjx():
    """Lazy import to avoid circular dependency."""
    from app.main import pjx

    return pjx


# -- Rendering helpers --------------------------------------------------------


def _todo_list_html(status: str = "all") -> str:
    return _pjx().partial(
        "components/TodoList.jinja",
        todos=filter_todos(status),
        empty_message=EMPTY_LABELS.get(status, EMPTY_LABELS["all"]),
        done_count=sum(1 for t in todos_db if t["done"]),
        total_count=len(todos_db),
    )


def _search_html(query: str) -> str:
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
    return _pjx().partial(
        "components/SearchResults.jinja", results=matches, query=query
    )


def _clock_html() -> str:
    return _pjx().partial("components/Clock.jinja", **clock_context())


def _counter_html() -> str:
    return _pjx().partial(
        "components/ServerCounter.jinja", count=server_counter["count"]
    )


# -- Auth endpoints -----------------------------------------------------------


@router.post("/auth/login")
@limiter.limit("5/minute")
async def auth_login(request: Request) -> Response:
    """Handle login form — store username in signed session."""
    form = await request.form()
    username = str(form.get("username", "")).strip()[:100]
    is_htmx = request.headers.get("HX-Request") == "true"
    if not username:
        return HTMLResponse(
            _pjx().partial(
                "components/Toast.jinja",
                message="Username is required",
                variant="error",
            )
        )
    request.session["user"] = username
    if is_htmx:
        return HTMLResponse("", headers={"HX-Redirect": "/protected"})
    return RedirectResponse("/protected", status_code=303)


@router.post("/auth/logout")
@limiter.limit("10/minute")
async def auth_logout(request: Request) -> Response:
    """Clear signed session and redirect to login."""
    request.session.clear()
    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        return HTMLResponse("", headers={"HX-Redirect": "/login"})
    return RedirectResponse("/login", status_code=303)


# -- SSE endpoints -----------------------------------------------------------


async def _clock_generator():
    while True:
        yield {"event": "clock", "data": _clock_html()}
        await asyncio.sleep(1)


@router.get("/sse/clock")
async def sse_clock():
    """SSE endpoint — streams the clock component every second."""
    return EventSourceResponse(_clock_generator())


# -- HTMX partials -----------------------------------------------------------


@router.post("/htmx/counter/increment")
async def htmx_counter_increment() -> HTMLResponse:
    server_counter["count"] += 1
    return HTMLResponse(_counter_html())


@router.post("/htmx/counter/decrement")
async def htmx_counter_decrement() -> HTMLResponse:
    server_counter["count"] -= 1
    return HTMLResponse(_counter_html())


@router.post("/htmx/counter/reset")
async def htmx_counter_reset() -> HTMLResponse:
    server_counter["count"] = 0
    return HTMLResponse(_counter_html())


@router.post("/htmx/todos/add")
@limiter.limit("30/minute")
async def htmx_add_todo(request: Request) -> HTMLResponse:
    form = await request.form()
    text = str(form.get("text", "")).strip()[:500]
    status = str(form.get("status", "all"))[:20]
    if text:
        todos_db.append({"text": text, "done": False})
    return HTMLResponse(_todo_list_html(status))


@router.post("/htmx/todos/{idx}/toggle")
async def htmx_toggle_todo(idx: int, request: Request) -> HTMLResponse:
    if 0 <= idx < len(todos_db):
        todos_db[idx]["done"] = not todos_db[idx]["done"]
    form = await request.form()
    status = str(form.get("status", "all"))[:20]
    return HTMLResponse(_todo_list_html(status))


@router.get("/htmx/todos/filter")
async def htmx_filter_todos(status: str = "all") -> HTMLResponse:
    return HTMLResponse(_todo_list_html(status))


@router.delete("/htmx/todos/{idx}")
async def htmx_delete_todo(idx: int, request: Request) -> HTMLResponse:
    if 0 <= idx < len(todos_db):
        todos_db.pop(idx)
    form = await request.form()
    status = str(form.get("status", "all"))[:20]
    return HTMLResponse(_todo_list_html(status))


@router.put("/htmx/todos/{idx}")
async def htmx_edit_todo(idx: int, request: Request) -> HTMLResponse:
    form = await request.form()
    text = str(form.get("text", "")).strip()[:500]
    status = str(form.get("status", "all"))[:20]
    if 0 <= idx < len(todos_db) and text:
        todos_db[idx]["text"] = text
    return HTMLResponse(_todo_list_html(status))


@router.get("/htmx/search")
async def htmx_search(query: str = "") -> HTMLResponse:
    return HTMLResponse(_search_html(query[:200]))


@router.post("/htmx/message/{user_id}")
async def htmx_message(user_id: int) -> HTMLResponse:
    user = next((u for u in USERS if u.id == user_id), None)
    if not user:
        return HTMLResponse(
            _pjx().partial(
                "components/Toast.jinja", message="User not found", variant="error"
            )
        )
    messages_db.append({"to": user.name, "text": "Hello!"})
    return HTMLResponse(
        _pjx().partial(
            "components/Toast.jinja",
            message=f"Message sent to {user.name}!",
            variant="success",
        )
    )
