"""PJX template engine — unified interface over Jinja2 and MiniJinja."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import jinja2
import minijinja


@runtime_checkable
class EngineProtocol(Protocol):
    """Protocol that both engine wrappers implement."""

    def render(self, template_name: str, context: dict[str, Any]) -> str: ...

    def render_string(self, source: str, context: dict[str, Any]) -> str: ...

    def add_template(self, name: str, source: str) -> None: ...

    def add_global(self, name: str, value: Any) -> None: ...

    def has_template(self, name: str) -> bool: ...


class Jinja2Engine:
    """Wrapper over ``jinja2.Environment``."""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {}
        self._loader = jinja2.DictLoader(self._templates)
        self._env = jinja2.Environment(
            loader=self._loader,
            autoescape=True,
            undefined=jinja2.StrictUndefined,
        )

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        template = self._env.get_template(template_name)
        return template.render(**context)

    def render_string(self, source: str, context: dict[str, Any]) -> str:
        template = self._env.from_string(source)
        return template.render(**context)

    def add_template(self, name: str, source: str) -> None:
        self._templates[name] = source

    def add_global(self, name: str, value: Any) -> None:
        self._env.globals[name] = value

    def has_template(self, name: str) -> bool:
        return name in self._templates


class MiniJinjaEngine:
    """Wrapper over ``minijinja.Environment``."""

    def __init__(self) -> None:
        self._env = minijinja.Environment()
        self._templates: dict[str, str] = {}

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        return self._env.render_template(template_name, **context)

    def render_string(self, source: str, context: dict[str, Any]) -> str:
        self._env.add_template("__inline__", source)
        return self._env.render_template("__inline__", **context)

    def add_template(self, name: str, source: str) -> None:
        self._templates[name] = source
        self._env.add_template(name, source)

    def add_global(self, name: str, value: Any) -> None:
        self._env.add_global(name, value)

    def has_template(self, name: str) -> bool:
        return name in self._templates


def create_engine(engine_type: str = "jinja2") -> EngineProtocol:
    """Create a template engine instance.

    Args:
        engine_type: One of ``"jinja2"``, ``"minijinja"``, or ``"auto"``.

    Returns:
        An engine implementing :class:`EngineProtocol`.
    """
    if engine_type in ("jinja2", "auto"):
        return Jinja2Engine()
    if engine_type == "minijinja":
        return MiniJinjaEngine()
    msg = f"unknown engine type: {engine_type!r}"
    raise ValueError(msg)
