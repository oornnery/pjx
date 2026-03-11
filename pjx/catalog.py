from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    from fastapi.responses import HTMLResponse
except Exception:  # pragma: no cover - optional dependency during import
    HTMLResponse = None

from .models import DirectiveContext, Element, RenderState
from .runtime import Runtime


class Catalog:
    def __init__(self, *, root: str, aliases: dict[str, str] | None = None) -> None:
        self.root = Path(root)
        self.aliases = aliases or {}
        self.directives: dict[str, Callable[..., Any]] = {}
        self.runtime = Runtime(self)

    def resolve_path(self, template_path: str) -> Path:
        for alias, target in self.aliases.items():
            if template_path == alias:
                return Path(target)
            if template_path.startswith(f"{alias}/"):
                suffix = template_path[len(alias) + 1 :]
                return Path(target) / suffix
        return self.root / template_path

    def register_directive(self, name: str, fn: Callable[..., Any]) -> None:
        self.directives[name] = fn

    def render(
        self,
        *,
        template: str,
        context: dict[str, Any] | None = None,
        request: Any = None,
        partial: bool = False,
        target: str | None = None,
    ) -> Any:
        html_output = self.render_string(
            template=template,
            context=context,
            request=request,
            partial=partial,
            target=target,
        )
        if HTMLResponse is None:
            return html_output
        return HTMLResponse(html_output)

    def render_string(
        self,
        *,
        template: str,
        context: dict[str, Any] | None = None,
        request: Any = None,
        partial: bool = False,
        target: str | None = None,
    ) -> str:
        payload = dict(context or {})
        payload["request"] = request
        payload["__pjx_render_state"] = RenderState(
            catalog=self,
            request=request,
            partial=partial,
            target=target,
        )
        html_output = self.runtime.render_root(
            template,
            payload,
            request=request,
            partial=partial,
            target=target,
        )
        return html_output

    def apply_directives_to_attrs(
        self,
        tag_name: str,
        attrs: dict[str, Any],
        render_state: RenderState,
    ) -> dict[str, Any]:
        element = Element(name=tag_name, attrs=dict(attrs))
        self._apply_core_directives(element)
        self._apply_custom_directives(element, render_state)
        return element.attrs

    def _apply_core_directives(self, element: Element) -> None:
        attrs = dict(element.attrs)
        for key, value in attrs.items():
            if key.startswith("jx-bind:"):
                element.attrs[key.split(":", 1)[1]] = value
                element.attrs.pop(key, None)
                continue
            if key in {"jx-text", "jx-html"}:
                element.attrs.pop(key, None)
                continue
            if key == "jx-class":
                existing = element.attrs.get("class", "")
                element.attrs["class"] = _merge_classes(existing, value)
                element.attrs.pop(key, None)
                continue
            if key == "jx-show":
                if not value:
                    style = element.attrs.get("style", "")
                    if style and not style.endswith(";"):
                        style += ";"
                    style += " display: none;"
                    element.attrs["style"] = style.strip()
                element.attrs.pop(key, None)
                continue
            if key.startswith("jx-on:"):
                event_name = key.split(":", 1)[1]
                element.attrs[f"data-pjx-on-{event_name}"] = value
                element.attrs.pop(key, None)

    def _apply_custom_directives(self, element: Element, render_state: RenderState) -> None:
        for name, fn in self.directives.items():
            if name not in element.attrs:
                continue
            value = element.attrs.pop(name)
            ctx = DirectiveContext(tag_name=element.name, render_state=render_state)
            result = fn(element, value, ctx)
            if isinstance(result, Element):
                element.attrs = result.attrs


def _merge_classes(existing: Any, value: Any) -> str:
    tokens: list[str] = []
    if existing:
        tokens.extend(str(existing).split())
    if isinstance(value, dict):
        tokens.extend(name for name, enabled in value.items() if enabled)
    elif isinstance(value, (list, tuple, set)):
        tokens.extend(str(item) for item in value if item)
    elif value:
        tokens.extend(str(value).split())
    return " ".join(dict.fromkeys(tokens))
