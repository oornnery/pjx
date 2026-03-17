from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.responses import HTMLResponse

from .models import AssetImport, DirectiveContext, Element, RenderState
from .runtime import Runtime


@dataclass(slots=True, frozen=True)
class TemplateMount:
    path: Path
    prefix: str | None = None

    @property
    def alias(self) -> str:
        normalized_prefix = _normalize_template_prefix(self.prefix)
        if normalized_prefix is None:
            return "@"
        return f"@{normalized_prefix}"


class Catalog:
    def __init__(
        self,
        *,
        root: str,
        aliases: dict[str, str] | None = None,
        auto_reload: bool = True,
        renderer: str = "jinja2",
        bundle: bool = False,
    ) -> None:
        self.root = Path(root)
        self.aliases = aliases or {}
        self.auto_reload = auto_reload
        self.renderer_name = renderer
        self.bundle = bundle
        self.base_assets: list[AssetImport] = []
        self.directives: dict[str, Callable[..., Any]] = {}
        self._template_mounts: list[TemplateMount] = [TemplateMount(path=self.root)]
        self.runtime = _create_runtime(renderer, self)

    @property
    def template_roots(self) -> list[Path]:
        roots: list[Path] = []
        for mount in self._template_mounts:
            if mount.path not in roots:
                roots.append(mount.path)
        return roots

    @property
    def template_mounts(self) -> tuple[TemplateMount, ...]:
        return tuple(self._template_mounts)

    def add_template_root(
        self,
        path: str | Path,
        *,
        prefix: str | None = None,
    ) -> TemplateMount:
        template_root = Path(path)
        normalized_prefix = _normalize_template_prefix(prefix)
        mount = TemplateMount(path=template_root, prefix=normalized_prefix)
        if mount not in self._template_mounts:
            self._template_mounts.append(mount)
        if normalized_prefix is not None:
            self.aliases[f"@{normalized_prefix}"] = str(template_root)
        return mount

    def resolve_path(self, template_path: str) -> Path:
        for alias, target in sorted(
            self.aliases.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            if template_path == alias:
                return Path(target)
            if template_path.startswith(f"{alias}/"):
                suffix = template_path[len(alias) + 1 :]
                return Path(target) / suffix
        for template_root in self.template_roots:
            candidate = template_root / template_path
            if candidate.exists():
                return candidate
        return self.template_roots[0] / template_path

    def register_directive(self, name: str, fn: Callable[..., Any]) -> None:
        self.directives[name] = fn

    def add_asset(self, *, kind: str, path: str) -> None:
        asset = AssetImport(kind=kind, path=path)
        if asset not in self.base_assets:
            self.base_assets.append(asset)

    def list_components(self) -> list[str]:
        components: dict[str, Path] = {}
        for mount in self._template_mounts:
            for pattern in ("*.pjx",):
                for path in mount.path.rglob(pattern):
                    if not path.is_file():
                        continue
                    relative_path = str(path.relative_to(mount.path))
                    normalized_prefix = _normalize_template_prefix(mount.prefix)
                    if normalized_prefix is None:
                        import_path = relative_path
                    else:
                        import_path = f"@{normalized_prefix}/{relative_path}"
                    components.setdefault(import_path, path)
        return sorted(components)

    def import_path_for_file(self, path: str | Path) -> str:
        resolved = Path(path).resolve()
        for mount in self._template_mounts:
            template_root = mount.path.resolve()
            if not resolved.is_relative_to(template_root):
                continue
            relative_path = str(resolved.relative_to(template_root))
            normalized_prefix = _normalize_template_prefix(mount.prefix)
            if normalized_prefix is None:
                return relative_path
            return f"@{normalized_prefix}/{relative_path}"
        return str(resolved)

    def get_signature(self, template_path: str) -> dict[str, Any]:
        instance = self.runtime.get_component_instance(template_path)
        component = instance.component
        return {
            "component": component.component_name,
            "required": [
                spec.name for spec in component.prop_specs if spec.default_expr is None
            ],
            "optional": [
                spec.name
                for spec in component.prop_specs
                if spec.default_expr is not None
            ],
            "props": [
                {
                    "name": spec.name,
                    "type": spec.type_expr,
                    "default": spec.default_expr,
                }
                for spec in component.prop_specs
            ],
            "slots": sorted(component.slot_specs),
            "css": [asset.path for asset in component.assets if asset.kind == "css"],
            "js": [asset.path for asset in component.assets if asset.kind == "js"],
        }

    def render(
        self,
        *,
        template: str,
        context: dict[str, Any] | None = None,
        request: Any = None,
        partial: bool = False,
        target: str | None = None,
    ) -> HTMLResponse:
        html_output = self.render_string(
            template=template,
            context=context,
            request=request,
            partial=partial,
            target=target,
        )
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
            if key == "jx-text":
                element.text_content = str(value)
                element.attrs.pop(key, None)
                continue
            if key == "jx-html":
                element.html_content = str(value)
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

    def _apply_custom_directives(
        self, element: Element, render_state: RenderState
    ) -> None:
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


def _normalize_template_prefix(prefix: str | None) -> str | None:
    if prefix is None:
        return None
    normalized = prefix.strip()
    if not normalized or normalized == "@":
        return None
    normalized = normalized.lstrip("@").strip("/")
    return normalized or None


def _create_runtime(renderer: str, catalog: Any) -> Any:
    """Factory for creating the appropriate runtime backend."""
    if renderer == "minijinja":
        from .runtime_minijinja import MiniJinjaRuntime
        return MiniJinjaRuntime(catalog)
    return Runtime(catalog)
