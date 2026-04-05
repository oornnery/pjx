from __future__ import annotations

from jinja2 import Environment

from pjx_tailwind.cn import cn


def register_globals(env: Environment) -> None:
    """Register pjx-tailwind Jinja2 globals on the environment."""
    env.globals["cn"] = cn  # type: ignore[assignment]
