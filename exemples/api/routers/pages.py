from __future__ import annotations

from pjx import PJXRouter

from exemples.data import get_showcase_context
from exemples.state import Counter, Todo


pages = PJXRouter()


@pages.page("/", template="pages/showcase.pjx")
def showcase_page() -> dict:
    return get_showcase_context()


@pages.page("/counter", template="pages/counter.pjx")
def counter_page() -> dict:
    return Counter.context()


@pages.page("/components", template="pages/components.pjx")
def components_page() -> dict:
    return {}


@pages.page("/kitchen-sink", template="pages/kitchen.pjx")
def kitchen_page() -> dict:
    return {}


@pages.page("/apps", template="pages/apps.pjx")
def apps_page() -> dict:
    return Counter.context() | Todo.context()


__all__ = ["pages"]
