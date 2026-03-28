"""PJX template engine — unified interface over Jinja2 and MiniJinja."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import jinja2

try:
    import minijinja

    _HAS_MINIJINJA = True
except ImportError:
    _HAS_MINIJINJA = False


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


def _minijinja_auto_escape(name: str) -> str:
    """Auto-escape callback for MiniJinja — escape HTML by default."""
    if name.endswith((".txt", ".text", ".md")):
        return "none"
    return "html"


class MiniJinjaEngine:
    """Wrapper over ``minijinja.Environment``.

    Requires ``pjx[fast]`` (``pip install pjx[fast]``).
    """

    def __init__(self) -> None:
        if not _HAS_MINIJINJA:
            msg = "minijinja is not installed. Install it with: pip install pjx[fast]"
            raise ImportError(msg)
        self._env = minijinja.Environment(auto_escape_callback=_minijinja_auto_escape)  # type: ignore[possibly-undefined]
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


class HybridEngine:
    """Best-of-both: Jinja2 for ``render()``, MiniJinja for ``render_string()``.

    Falls back to pure Jinja2 if minijinja is not installed.
    """

    def __init__(self) -> None:
        self._jinja2 = Jinja2Engine()
        self._minijinja: MiniJinjaEngine | None = None
        if _HAS_MINIJINJA:
            self._minijinja = MiniJinjaEngine()

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        return self._jinja2.render(template_name, context)

    def render_string(self, source: str, context: dict[str, Any]) -> str:
        if self._minijinja is not None:
            return self._minijinja.render_string(source, context)
        return self._jinja2.render_string(source, context)

    def add_template(self, name: str, source: str) -> None:
        self._jinja2.add_template(name, source)
        if self._minijinja is not None:
            self._minijinja.add_template(name, source)

    def add_global(self, name: str, value: Any) -> None:
        self._jinja2.add_global(name, value)
        if self._minijinja is not None:
            self._minijinja.add_global(name, value)

    def has_template(self, name: str) -> bool:
        return self._jinja2.has_template(name)


def create_engine(engine_type: str = "hybrid") -> EngineProtocol:
    """Create a template engine instance.

    Args:
        engine_type: One of ``"hybrid"``, ``"jinja2"``, ``"minijinja"``, or ``"auto"``.

    Returns:
        An engine implementing :class:`EngineProtocol`.
    """
    if engine_type in ("hybrid", "auto"):
        return HybridEngine()
    if engine_type == "jinja2":
        return Jinja2Engine()
    if engine_type == "minijinja":
        return MiniJinjaEngine()
    msg = f"unknown engine type: {engine_type!r}"
    raise ValueError(msg)
