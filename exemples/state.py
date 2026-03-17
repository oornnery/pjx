"""Server-side state classes for the PJX showcase app."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from pjx import Component, state


class Counter(Component):
    """Thread-safe server-side counter bound to the counter template."""

    count = state(0)

    @classmethod
    def increment(cls) -> None:
        with cls._pjx_lock:
            cls.count += 1

    @classmethod
    def decrement(cls) -> None:
        with cls._pjx_lock:
            cls.count -= 1


@dataclass
class TodoItem:
    id: int
    text: str
    done: bool = False


class Todo:
    """Server-side todo list state."""

    _lock: Lock = Lock()
    _items: list[TodoItem] = []
    _next_id: int = 1

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)

    @classmethod
    def _init(cls) -> None:
        if not hasattr(cls, "_items") or not isinstance(cls._items, list):
            cls._items = []
            cls._next_id = 1

    @classmethod
    def add(cls, text: str) -> None:
        cls._init()
        with cls._lock:
            cls._items.append(TodoItem(id=cls._next_id, text=text.strip()))
            cls._next_id += 1

    @classmethod
    def toggle(cls, todo_id: int) -> None:
        cls._init()
        with cls._lock:
            for item in cls._items:
                if item.id == todo_id:
                    item.done = not item.done
                    break

    @classmethod
    def delete(cls, todo_id: int) -> None:
        cls._init()
        with cls._lock:
            cls._items = [i for i in cls._items if i.id != todo_id]

    @classmethod
    def context(cls) -> dict:
        cls._init()
        return {
            "todos": list(cls._items),
            "todo_total": len(cls._items),
            "todo_done": sum(1 for i in cls._items if i.done),
        }
