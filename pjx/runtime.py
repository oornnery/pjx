from __future__ import annotations

from dataclasses import dataclass
import html
from typing import Any, Literal, Optional, Union, cast, get_args, get_origin

from jinja2 import Environment, StrictUndefined, pass_context
from markupsafe import Markup

from .assets import AssetsView, render_assets
from .compiler import compile_component_file
from .models import AttrBag, CompiledComponent, RenderState, SlotAccessor


SAFE_TYPE_GLOBALS = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "Literal": Literal,
    "Optional": Optional,
    "None": None,
}


@dataclass(slots=True)
class ComponentInstance:
    component: CompiledComponent
    template: Any
    source_mtime_ns: int


class Runtime:
    def __init__(self, catalog: Any) -> None:
        self.catalog = catalog
        self.environment = Environment(
            autoescape=True,
            trim_blocks=False,
            lstrip_blocks=False,
            undefined=StrictUndefined,
        )
        globals_map = cast(dict[str, Any], self.environment.globals)
        globals_map["__pjx_render_component"] = self.render_component
        globals_map["__pjx_render_attrs"] = self.render_attrs
        self._template_cache: dict[str, ComponentInstance] = {}
        self._expr_cache: dict[str, Any] = {}

    def get_component_instance(self, template_path: str) -> ComponentInstance:
        source_path = self.catalog.resolve_path(template_path)
        cache_key = str(source_path)
        source_mtime_ns = source_path.stat().st_mtime_ns
        cached = self._template_cache.get(cache_key)
        if cached is not None:
            if (
                not self.catalog.auto_reload
                or cached.source_mtime_ns == source_mtime_ns
            ):
                return cached
        component = compile_component_file(source_path.read_text(), source_path)
        template = self.environment.from_string(component.jinja_source)
        instance = ComponentInstance(
            component=component,
            template=template,
            source_mtime_ns=source_mtime_ns,
        )
        self._template_cache[cache_key] = instance
        return instance

    def evaluate_expr(self, expr: str, context: dict[str, Any]) -> Any:
        compiled = self._expr_cache.get(expr)
        if compiled is None:
            compiled = self.environment.compile_expression(expr)
            self._expr_cache[expr] = compiled
        return compiled(**context)

    def render_root(
        self,
        template_path: str,
        context: dict[str, Any],
        *,
        request: Any = None,
        partial: bool = False,
        target: str | None = None,
    ) -> str:
        instance = self.get_component_instance(template_path)
        state = context.get("__pjx_render_state")
        if state is None:
            state = RenderState(
                catalog=self.catalog, request=request, partial=partial, target=target
            )
            context = dict(context)
            context["__pjx_render_state"] = state
        context["assets"] = AssetsView(state)
        self._collect_template_assets(instance.component, state, seen=set())
        html_output = self._render_component_instance(
            instance,
            props=context,
            extra_attrs={},
            content="",
            slots={},
            inherited_context=context,
            provides={},
            render_state=state,
        )

        if partial and target:
            return extract_fragment_by_id(html_output, target)
        if partial:
            return html_output
        if state.assets_rendered:
            return html_output
        assets_html = render_assets(state.assets)
        return f"{assets_html}{html_output}"

    def _collect_template_assets(
        self,
        component: CompiledComponent,
        render_state: RenderState,
        *,
        seen: set[str],
    ) -> None:
        if component.path in seen:
            return
        seen.add(component.path)
        render_state.register_assets(tuple(self.catalog.base_assets))
        render_state.register_assets(component.assets)
        for template_path in component.component_imports.values():
            child_instance = self.get_component_instance(template_path)
            self._collect_template_assets(
                child_instance.component, render_state, seen=seen
            )

    def _render_component_instance(
        self,
        instance: ComponentInstance,
        *,
        props: dict[str, Any],
        extra_attrs: dict[str, Any],
        content: Any,
        slots: dict[str, Any],
        inherited_context: dict[str, Any],
        provides: dict[str, Any],
        render_state: RenderState,
    ) -> str:
        component = instance.component
        render_state.register_assets(component.assets)

        local_context = dict(inherited_context)
        local_context.update(self._resolve_props(instance, props, local_context))

        for injected in component.inject_names:
            if injected in provides:
                local_context[injected] = provides[injected]
            else:
                local_context[injected] = None

        local_provides = dict(provides)
        for provided in component.provide_names:
            local_provides[provided] = local_context.get(provided)

        local_context.update(
            {
                "attrs": AttrBag(
                    self.catalog.apply_directives_to_attrs(
                        component.component_name, extra_attrs, render_state
                    )
                ),
                "content": Markup(content or ""),
                "slot": SlotAccessor(component.slot_specs, slots),
                "__pjx_provides": local_provides,
                "__pjx_render_state": render_state,
                "__pjx_component": component,
            }
        )
        return instance.template.render(**local_context)

    def _resolve_props(
        self,
        instance: ComponentInstance,
        received: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for spec in instance.component.prop_specs:
            if spec.name in received:
                value = received[spec.name]
            elif spec.default_expr is not None:
                value = self.evaluate_expr(spec.default_expr, {**context, **resolved})
            else:
                raise ValueError(
                    f"{instance.component.component_name}: missing required prop {spec.name!r}"
                )
            if spec.type_expr and not _matches_type(spec.type_expr, value):
                raise TypeError(
                    f"{instance.component.component_name}.{spec.name}: "
                    f"expected {spec.type_expr}, got {type(value).__name__}"
                )
            resolved[spec.name] = value
        return resolved

    @pass_context
    def render_component(
        self,
        jinja_ctx: Any,
        template_path: str,
        attrs: dict[str, Any],
        content: Any,
        slots: dict[str, Any],
    ) -> Markup:
        instance = self.get_component_instance(template_path)
        component = instance.component
        props: dict[str, Any] = {}
        extra_attrs: dict[str, Any] = {}
        prop_names = {spec.name for spec in component.prop_specs}

        for key, value in attrs.items():
            if key in prop_names:
                props[key] = value
            else:
                extra_attrs[key] = value

        render_state = _lookup_render_state(jinja_ctx)
        parent_provides = jinja_ctx.get("__pjx_provides", {})
        html_output = self._render_component_instance(
            instance,
            props=props,
            extra_attrs=extra_attrs,
            content=content,
            slots=slots,
            inherited_context=dict(jinja_ctx.get_all()),
            provides=parent_provides,
            render_state=render_state,
        )
        return Markup(html_output)

    @pass_context
    def render_attrs(
        self, jinja_ctx: Any, tag_name: str, attrs: dict[str, Any]
    ) -> Markup:
        render_state = _lookup_render_state(jinja_ctx)
        rendered_attrs = self.catalog.apply_directives_to_attrs(
            tag_name, attrs, render_state
        )
        if not rendered_attrs:
            return Markup("")
        chunks: list[str] = []
        for key, value in rendered_attrs.items():
            if value is True:
                chunks.append(f" {html.escape(key)}")
                continue
            if value in (False, None):
                continue
            chunks.append(f' {html.escape(key)}="{html.escape(str(value))}"')
        return Markup("".join(chunks))


def extract_fragment_by_id(html_source: str, target_id: str) -> str:
    marker = f'id="{target_id}"'
    start = html_source.find(marker)
    if start == -1:
        marker = f"id='{target_id}'"
        start = html_source.find(marker)
    if start == -1:
        raise ValueError(f"Could not find fragment with id {target_id!r}")

    open_start = html_source.rfind("<", 0, start)
    if open_start == -1:
        raise ValueError(f"Invalid HTML around fragment {target_id!r}")
    open_end = html_source.find(">", start)
    if open_end == -1:
        raise ValueError(f"Unclosed tag for fragment {target_id!r}")
    tag_name = _tag_name_from_open_tag(html_source[open_start : open_end + 1])
    cursor = open_end + 1
    depth = 1

    while cursor < len(html_source):
        next_open = html_source.find(f"<{tag_name}", cursor)
        next_close = html_source.find(f"</{tag_name}>", cursor)
        if next_close == -1:
            raise ValueError(f"Unclosed fragment tag {tag_name!r}")
        if next_open != -1 and next_open < next_close:
            depth += 1
            cursor = next_open + 1
            continue
        depth -= 1
        cursor = next_close + len(tag_name) + 3
        if depth == 0:
            return html_source[open_start:cursor]
    raise ValueError(f"Could not extract fragment {target_id!r}")


def _lookup_render_state(jinja_ctx: Any) -> RenderState:
    try:
        return jinja_ctx.get_all()["__pjx_render_state"]
    except KeyError as exc:
        raise RuntimeError("Missing PJX render state") from exc


def _matches_type(type_expr: str, value: Any) -> bool:
    annotation = eval(type_expr, {"__builtins__": {}}, SAFE_TYPE_GLOBALS)
    return _matches_annotation(annotation, value)


def _matches_annotation(annotation: Any, value: Any) -> bool:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is None:
        if annotation is Any:
            return True
        if annotation is None:
            return value is None
        return isinstance(value, annotation)
    if origin is Literal:
        return value in args
    if origin is list:
        return isinstance(value, list)
    if origin is dict:
        return isinstance(value, dict)
    if origin in (Union, getattr(__import__("types"), "UnionType", object())):
        return any(_matches_annotation(arg, value) for arg in args)
    return True


def _tag_name_from_open_tag(tag: str) -> str:
    body = tag[1:].split(None, 1)[0]
    return body.rstrip(">")
