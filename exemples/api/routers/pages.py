from __future__ import annotations

from pjx import PjxRouter

from exemples.data import get_showcase_context
from exemples.state import Counter, Todo


pages = PjxRouter()


@pages.page("/", template="pages/showcase.pjx")
def showcase_page() -> dict:
    return get_showcase_context()


@pages.page("/components", template="pages/components.pjx")
def components_page() -> dict:
    return {}


@pages.page("/apps", template="pages/apps.pjx")
def apps_page() -> dict:
    return Counter.context() | Todo.context()


__all__ = ["pages"]
