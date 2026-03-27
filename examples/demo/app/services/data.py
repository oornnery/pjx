"""Business logic — in-memory data and rendering helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.schemas import User

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


def filter_todos(status: str = "all") -> list[dict[str, object]]:
    """Return filtered todos with their original index."""
    return [
        {"idx": i, "text": t["text"], "done": t["done"]}
        for i, t in enumerate(todos_db)
        if status == "all"
        or (status == "done" and t["done"])
        or (status == "pending" and not t["done"])
    ]


def clock_context() -> dict[str, str]:
    """Return current time context for the Clock component."""
    now = datetime.now(timezone.utc).astimezone()
    return {
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%d %b %Y"),
        "weekday": now.strftime("%A"),
        "timezone": now.strftime("%Z (UTC%z)"),
    }
