from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ast import (
    ActionDirectiveNode,
    ComputedDirectiveNode,
    InjectDirectiveNode,
    PropDeclNode,
    PropsDirectiveNode,
    ProvideDirectiveNode,
    SignalDirectiveNode,
    SlotDirectiveNode,
)
from .markup import (
    ElementNode,
    RawNode,
    attr_value_to_expr,
    extract_named_slots,
    parse_markup,
    split_children_by_tag,
)
from .models import AssetImport, CompiledComponent, PropSpec, SlotSpec
from .parser import parse_component_source


@dataclass(slots=True)
class TransformContext:
    component_imports: dict[str, str]
    counter: int = 0

    def next_name(self, prefix: str) -> str:
        self.counter += 1
        return f"__pjx_{prefix}_{self.counter}"


def compile_component_file(source: str, path: Path) -> CompiledComponent:
    parsed = parse_component_source(source, path)
    component_imports: dict[str, str] = {}
    assets: list[AssetImport] = []

    for import_node in parsed.imports:
        if import_node.kind == "component":
            component_imports[import_node.alias or ""] = import_node.path
            continue
        assets.append(AssetImport(kind=import_node.kind, path=import_node.path))

    prop_aliases = {
        alias.name: [_prop_spec_from_decl(item) for item in alias.props]
        for alias in parsed.prop_aliases
    }

    (
        prop_specs,
        inject_names,
        provide_names,
        slot_specs,
        action_names,
        preamble,
    ) = _compile_component_directives(parsed.component.directives, prop_aliases)

    transform_ctx = TransformContext(component_imports=component_imports)
    transformed_body = transform_markup(parsed.component.body, transform_ctx)
    jinja_source = f"{preamble}{transformed_body}"

    return CompiledComponent(
        path=str(path),
        component_name=parsed.component.name,
        source_path=path,
        assets=tuple(assets),
        component_imports=component_imports,
        prop_specs=tuple(prop_specs),
        slot_specs={item.name: item for item in slot_specs},
        inject_names=tuple(inject_names),
        provide_names=tuple(provide_names),
        action_names=tuple(action_names),
        modifiers=frozenset(parsed.component.modifiers),
        jinja_source=jinja_source,
    )


def transform_markup(source: str, ctx: TransformContext) -> str:
    nodes = parse_markup(source)
    return _emit_nodes(nodes, ctx)


def _compile_component_directives(
    directives: tuple[
        PropsDirectiveNode
        | InjectDirectiveNode
        | ProvideDirectiveNode
        | ComputedDirectiveNode
        | SlotDirectiveNode
        | SignalDirectiveNode
        | ActionDirectiveNode,
        ...,
    ],
    prop_aliases: dict[str, list[PropSpec]],
) -> tuple[list[PropSpec], list[str], list[str], list[SlotSpec], list[str], str]:
    props: list[PropSpec] = []
    inject_names: list[str] = []
    provide_names: list[str] = []
    slot_specs: list[SlotSpec] = []
    action_names: list[str] = []
    preamble_chunks: list[str] = []
    props_seen = False
    slot_names: set[str] = set()

    for directive in directives:
        if isinstance(directive, PropsDirectiveNode):
            if props_seen:
                raise ValueError("Only one props block is allowed per component")
            props = _resolve_props_directive(directive, prop_aliases)
            props_seen = True
            continue
        if isinstance(directive, InjectDirectiveNode):
            inject_names.extend(directive.names)
            continue
        if isinstance(directive, ProvideDirectiveNode):
            provide_names.extend(directive.names)
            continue
        if isinstance(directive, ComputedDirectiveNode):
            preamble_chunks.append(
                f"{{% set {directive.name} %}}{directive.body}{{% endset %}}\n"
            )
            continue
        if isinstance(directive, SlotDirectiveNode):
            if directive.name in slot_names:
                raise ValueError(f"Duplicate slot declaration: {directive.name}")
            slot_names.add(directive.name)
            slot_specs.append(SlotSpec(name=directive.name, params=directive.params))
            continue
        if isinstance(directive, SignalDirectiveNode):
            preamble_chunks.append(f"{{% set {directive.name} = {directive.expr} %}}\n")
            continue
        if isinstance(directive, ActionDirectiveNode):
            action_names.append(directive.name)
            continue

    return (
        props,
        inject_names,
        provide_names,
        slot_specs,
        action_names,
        "".join(preamble_chunks),
    )


def _emit_nodes(nodes: list[Any], ctx: TransformContext) -> str:
    rendered: list[str] = []
    for node in nodes:
        if isinstance(node, RawNode):
            rendered.append(node.source)
            continue
        if node.name == "If":
            rendered.append(_emit_if(node, ctx))
            continue
        if node.name == "For":
            rendered.append(_emit_for(node, ctx))
            continue
        if node.name == "Switch":
            rendered.append(_emit_switch(node, ctx))
            continue
        if node.name and node.name[0].isupper():
            rendered.append(_emit_component_call(node, ctx))
            continue
        rendered.append(_emit_html_element(node, ctx))
    return "".join(rendered)


def _emit_if(node: ElementNode, ctx: TransformContext) -> str:
    when_expr = _lookup_attr(node.attrs, "when", force_expression=True)
    truthy_children, else_children = split_children_by_tag(node.children, "Else")
    rendered = [f"{{% if {when_expr} %}}", _emit_nodes(truthy_children, ctx)]
    if else_children is not None:
        rendered.extend(["{% else %}", _emit_nodes(else_children, ctx)])
    rendered.append("{% endif %}")
    return "".join(rendered)


def _emit_for(node: ElementNode, ctx: TransformContext) -> str:
    each_expr = _lookup_attr(node.attrs, "each", force_expression=True)
    loop_var = _lookup_attr(node.attrs, "as", force_expression=False).strip("'\"")
    index_name = _optional_attr(node.attrs, "index")
    truthy_children, empty_children = split_children_by_tag(node.children, "Empty")

    rendered = [f"{{% for {loop_var} in {each_expr} %}}"]
    if index_name:
        clean_index = index_name.strip("\"'")
        rendered.append(f"{{% set {clean_index} = loop.index0 %}}")
    rendered.append(_emit_nodes(truthy_children, ctx))
    if empty_children is not None:
        rendered.extend(["{% else %}", _emit_nodes(empty_children, ctx)])
    rendered.append("{% endfor %}")
    return "".join(rendered)


def _emit_switch(node: ElementNode, ctx: TransformContext) -> str:
    value_expr = _lookup_attr(node.attrs, "value", force_expression=True)
    temp_name = ctx.next_name("switch")
    chunks = [f"{{% set {temp_name} = {value_expr} %}}"]
    first_case = True
    default_children: list[Any] | None = None

    for child in node.children:
        if not isinstance(child, ElementNode):
            continue
        if child.name == "Case":
            case_expr = _lookup_attr(child.attrs, "when", force_expression=True)
            prefix = "{% if " if first_case else "{% elif "
            chunks.append(prefix + f"{temp_name} == {case_expr}" + " %}")
            chunks.append(_emit_nodes(child.children, ctx))
            first_case = False
        elif child.name == "Default":
            default_children = child.children

    if default_children is not None:
        chunks.append("{% else %}")
        chunks.append(_emit_nodes(default_children, ctx))
    chunks.append("{% endif %}")
    return "".join(chunks)


def _emit_component_call(node: ElementNode, ctx: TransformContext) -> str:
    template_path = ctx.component_imports.get(node.name)
    if template_path is None:
        raise ValueError(f"Unknown component import alias: {node.name}")

    default_children, slot_entries = extract_named_slots(node.children)
    content_name = ctx.next_name("content")
    attrs_expr = _attrs_dict_expr(node.attrs)
    slot_names: list[str] = []
    chunks: list[str] = []

    for slot_name, params, slot_children in slot_entries:
        macro_name = ctx.next_name(f"slot_{slot_name}")
        signature = ", ".join(params)
        chunks.append(f"{{% macro {macro_name}({signature}) %}}")
        chunks.append(_emit_nodes(slot_children, ctx))
        chunks.append("{% endmacro %}")
        slot_names.append(f"{slot_name!r}: {macro_name}")

    chunks.append(f"{{% set {content_name} %}}")
    chunks.append(_emit_nodes(default_children, ctx))
    chunks.append("{% endset %}")
    slots_expr = "{" + ", ".join(slot_names) + "}" if slot_names else "{}"
    chunks.append(
        "{{ __pjx_render_component("
        f"{template_path!r}, "
        f"{attrs_expr}, "
        f"{content_name}, "
        f"{slots_expr}"
        ") }}"
    )
    return "".join(chunks)


def _emit_html_element(node: ElementNode, ctx: TransformContext) -> str:
    if _needs_raw_tag_passthrough(node):
        if node.self_closing:
            return node.raw_open
        return node.raw_open + _emit_nodes(node.children, ctx) + f"</{node.name}>"

    attrs_expr = _attrs_dict_expr(node.attrs)
    if _optional_attr(node.attrs, "jx-text") is not None:
        node_children = [
            RawNode(
                f"{{{{ {_lookup_attr(node.attrs, 'jx-text', force_expression=True)} }}}}"
            )
        ]
    elif _optional_attr(node.attrs, "jx-html") is not None:
        node_children = [
            RawNode(
                f"{{{{ {_lookup_attr(node.attrs, 'jx-html', force_expression=True)}|safe }}}}"
            )
        ]
    else:
        node_children = node.children

    start = f"<{node.name}{{{{ __pjx_render_attrs({node.name!r}, {attrs_expr}) }}}}"
    if node.self_closing:
        return start + " />"
    return start + ">" + _emit_nodes(node_children, ctx) + f"</{node.name}>"


def _needs_raw_tag_passthrough(node: ElementNode) -> bool:
    if "jx-" in node.raw_open:
        return False
    return "{%" in node.raw_open or "{{" in node.raw_open


def _attrs_dict_expr(attrs: list[tuple[str, str | None]]) -> str:
    items: list[str] = []
    for key, value in attrs:
        force_expression = (
            key in {"when", "each"}
            or key.startswith("jx-bind:")
            or key in {"jx-class", "jx-show", "jx-text", "jx-html"}
        )
        items.append(
            f"{key!r}: {attr_value_to_expr(value, force_expression=force_expression)}"
        )
    return "{" + ", ".join(items) + "}"


def _lookup_attr(
    attrs: list[tuple[str, str | None]], name: str, *, force_expression: bool
) -> str:
    for key, value in attrs:
        if key == name:
            return attr_value_to_expr(value, force_expression=force_expression)
    raise ValueError(f"Missing attribute {name!r}")


def _optional_attr(attrs: list[tuple[str, str | None]], name: str) -> str | None:
    for key, value in attrs:
        if key == name:
            return value
    return None


def _resolve_props_directive(
    directive: PropsDirectiveNode,
    prop_aliases: dict[str, list[PropSpec]],
) -> list[PropSpec]:
    if directive.alias_name is not None:
        try:
            return prop_aliases[directive.alias_name]
        except KeyError as exc:
            raise ValueError(f"Unknown props alias {directive.alias_name!r}") from exc
    return [_prop_spec_from_decl(item) for item in directive.props]


def _prop_spec_from_decl(prop: PropDeclNode) -> PropSpec:
    return PropSpec(
        name=prop.name,
        type_expr=prop.type_expr,
        default_expr=prop.default_expr,
    )
