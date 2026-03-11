from __future__ import annotations

from collections.abc import Callable


def directive(name: str) -> Callable[[Callable], Callable]:
    def decorator(fn: Callable) -> Callable:
        setattr(fn, "__pjx_directive_name__", name)
        return fn

    return decorator
