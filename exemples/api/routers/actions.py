from __future__ import annotations

from fastapi import Form

from pjx import PJXRouter

from exemples.state import Counter, Todo


actions = PJXRouter()


# ── Counter ───────────────────────────────────────────────────────────────────


@actions.action(
    "/actions/counter/inc",
    template="pages/counter.pjx",
    target="counter-display",
)
def increment_counter_action() -> dict:
    Counter.increment()
    return Counter.context()


@actions.action(
    "/actions/counter/dec",
    template="pages/counter.pjx",
    target="counter-display",
)
def decrement_counter_action() -> dict:
    Counter.decrement()
    return Counter.context()


# ── Todo ──────────────────────────────────────────────────────────────────────


@actions.action(
    "/actions/todo/add",
    template="pages/apps.pjx",
    target="todo-list",
)
def add_todo_action(text: str = Form(...)) -> dict:
    if text.strip():
        Todo.add(text)
    return Counter.context() | Todo.context()


@actions.action(
    "/actions/todo/toggle/{todo_id}",
    template="pages/apps.pjx",
    target="todo-list",
)
def toggle_todo_action(todo_id: int) -> dict:
    Todo.toggle(todo_id)
    return Counter.context() | Todo.context()


@actions.action(
    "/actions/todo/delete/{todo_id}",
    template="pages/apps.pjx",
    target="todo-list",
)
def delete_todo_action(todo_id: int) -> dict:
    Todo.delete(todo_id)
    return Counter.context() | Todo.context()


# ── Contact form ──────────────────────────────────────────────────────────────


@actions.action(
    "/actions/contact/submit",
    template="pages/apps.pjx",
    target="contact-form-wrap",
)
def contact_submit_action(
    cf_name: str = Form(""),
    cf_email: str = Form(""),
    cf_msg: str = Form(""),
) -> dict:
    # In a real app: send email, save to DB, etc.
    return {"contact_success": True, "cf_name": cf_name}


__all__ = ["actions"]
