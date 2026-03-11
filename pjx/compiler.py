from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any

from .markup import (
    ElementNode,
    RawNode,
    attr_value_to_expr,
    extract_named_slots,
    parse_markup,
    split_children_by_tag,
)
from .models import AssetImport, CompiledComponent, PropSpec, SlotSpec


_COMPONENT_RE = re.compile(
    r"\{%\s*component\s+([A-Za-z_][A-Za-z0-9_]*)\s*([^%]*)%\}(.*)\{%\s*endcomponent\s*%\}",
    re.DOTALL,
)

_TAG_RE = re.compile(r"^\s*\{%\s*(.*?)\s*%\}\s*$", re.DOTALL)
_SIGNAL_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*signal\((.*)\)\s*$",
    re.DOTALL,
)


@dataclass(slots=True)
class TransformContext:
    component_imports: dict[str, str]
    counter: int = 0

    def next_name(self, prefix: str) -> str:
        self.counter += 1
        return f"__pjx_{prefix}_{self.counter}"


def compile_component_file(source: str, path: Path) -> CompiledComponent:
    component_imports: dict[str, str] = {}
    assets: list[AssetImport] = []
    prop_aliases: dict[str, list[PropSpec]] = {}
    position = 0

    while True:
        position = _skip_whitespace(source, position)
        if not source.startswith("{%", position):
            break
        raw_tag, position = _read_tag(source, position)
        inner = _extract_tag_body(raw_tag)
        keyword, remainder = _split_keyword(inner)
        if keyword == "import":
            _handle_import(remainder, assets, component_imports)
            continue
        if keyword == "set":
            name, specs = _parse_props_alias(inner)
            prop_aliases[name] = specs
            continue
        if keyword == "component":
            position -= len(raw_tag)
            break
        break

    match = _COMPONENT_RE.search(source[position:])
    if not match:
        raise ValueError(f"{path}: expected a component declaration")

    component_name = match.group(1)
    modifiers = frozenset(item.strip() for item in match.group(2).split() if item.strip())
    body = match.group(3)

    (
        prop_specs,
        inject_names,
        provide_names,
        slot_specs,
        action_names,
        preamble,
        remainder,
    ) = _parse_component_preamble(body, prop_aliases)

    transform_ctx = TransformContext(component_imports=component_imports)
    transformed_body = transform_markup(remainder, transform_ctx)
    jinja_source = f"{preamble}{transformed_body}"

    return CompiledComponent(
        path=str(path),
        component_name=component_name,
        source_path=path,
        assets=tuple(assets),
        component_imports=component_imports,
        prop_specs=tuple(prop_specs),
        slot_specs={item.name: item for item in slot_specs},
        inject_names=tuple(inject_names),
        provide_names=tuple(provide_names),
        action_names=tuple(action_names),
        modifiers=modifiers,
        jinja_source=jinja_source,
    )


def transform_markup(source: str, ctx: TransformContext) -> str:
    nodes = parse_markup(source)
    return _emit_nodes(nodes, ctx)


def _parse_component_preamble(
    body: str,
    prop_aliases: dict[str, list[PropSpec]],
) -> tuple[list[PropSpec], list[str], list[str], list[SlotSpec], list[str], str, str]:
    props: list[PropSpec] = []
    inject_names: list[str] = []
    provide_names: list[str] = []
    slot_specs: list[SlotSpec] = []
    action_names: list[str] = []
    preamble_chunks: list[str] = []
    position = 0

    while True:
        position = _skip_whitespace(body, position)
        if not body.startswith("{%", position):
            break
        raw_tag, next_position = _read_tag(body, position)
        inner = _extract_tag_body(raw_tag)
        keyword, remainder = _split_keyword(inner)

        if keyword == "props":
            props = _parse_props_block(remainder, prop_aliases)
            position = next_position
            continue
        if keyword == "inject":
            inject_names.extend(item for item in remainder.split() if item)
            position = next_position
            continue
        if keyword == "provide":
            provide_names.extend(item for item in remainder.split() if item)
            position = next_position
            continue
        if keyword == "computed":
            block_body, position = _read_block(body, next_position, "endcomputed")
            preamble_chunks.append(f"{{% set {remainder.strip()} %}}{block_body}{{% endset %}}\n")
            continue
        if keyword == "slot":
            slot_name, params = _parse_slot_signature(remainder)
            slot_specs.append(SlotSpec(name=slot_name, params=params))
            _, position = _read_block(body, next_position, "endslot")
            continue
        if keyword == "signal":
            signal_name, expr = _parse_signal(remainder)
            preamble_chunks.append(f"{{% set {signal_name} = {expr} %}}\n")
            position = next_position
            continue
        if keyword == "action":
            action_name = remainder.strip()
            action_names.append(action_name)
            _, position = _read_block(body, next_position, "endaction")
            continue
        break

    return (
        props,
        inject_names,
        provide_names,
        slot_specs,
        action_names,
        "".join(preamble_chunks),
        body[position:],
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
        node_children = [RawNode(f"{{{{ {_lookup_attr(node.attrs, 'jx-text', force_expression=True)} }}}}")]
    elif _optional_attr(node.attrs, "jx-html") is not None:
        node_children = [RawNode(f"{{{{ {_lookup_attr(node.attrs, 'jx-html', force_expression=True)}|safe }}}}")]
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
        force_expression = key in {"when", "each", "value"} or key.startswith("jx-bind:") or key in {"jx-class", "jx-show", "jx-text", "jx-html"}
        items.append(f"{key!r}: {attr_value_to_expr(value, force_expression=force_expression)}")
    return "{" + ", ".join(items) + "}"


def _lookup_attr(attrs: list[tuple[str, str | None]], name: str, *, force_expression: bool) -> str:
    for key, value in attrs:
        if key == name:
            return attr_value_to_expr(value, force_expression=force_expression)
    raise ValueError(f"Missing attribute {name!r}")


def _optional_attr(attrs: list[tuple[str, str | None]], name: str) -> str | None:
    for key, value in attrs:
        if key == name:
            return value
    return None


def _parse_slot_signature(source: str) -> tuple[str, tuple[str, ...]]:
    match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*?)\))?$", source.strip(), re.DOTALL)
    if not match:
        raise ValueError(f"Invalid slot signature: {source!r}")
    params = tuple(item.strip() for item in (match.group(2) or "").split(",") if item.strip())
    return match.group(1), params


def _parse_signal(source: str) -> tuple[str, str]:
    match = _SIGNAL_RE.match(source)
    if not match:
        raise ValueError(f"Invalid signal declaration: {source!r}")
    return match.group(1), match.group(2).strip()


def _parse_props_block(source: str, prop_aliases: dict[str, list[PropSpec]]) -> list[PropSpec]:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", source):
        try:
            return prop_aliases[source]
        except KeyError as exc:
            raise ValueError(f"Unknown props alias {source!r}") from exc
    return _parse_inline_props(source)


def _parse_props_alias(tag_body: str) -> tuple[str, list[PropSpec]]:
    match = re.match(r"set\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\{.*\})", tag_body, re.DOTALL)
    if not match:
        raise ValueError(f"Invalid props alias declaration: {tag_body!r}")
    name = match.group(1)
    payload = match.group(2).strip()
    if not name.endswith("Props"):
        raise ValueError(f"Props alias must end with 'Props': {name}")
    inner = payload[1:-1]
    entries = _split_top_level_commas(inner)
    specs: list[PropSpec] = []
    for entry in entries:
        if not entry.strip():
            continue
        key_match = re.match(r'["\']([^"\']+)["\']\s*:\s*(.*)$', entry.strip(), re.DOTALL)
        if not key_match:
            raise ValueError(f"Invalid props alias entry: {entry!r}")
        prop_name = key_match.group(1)
        type_expr, default_expr = _parse_type_and_default(key_match.group(2).strip())
        specs.append(PropSpec(name=prop_name, type_expr=type_expr, default_expr=default_expr))
    return name, specs


def _parse_inline_props(source: str) -> list[PropSpec]:
    specs: list[PropSpec] = []
    for entry in _split_top_level_commas(source):
        item = entry.strip()
        if not item:
            continue
        name, remainder = item.split(":", 1)
        type_expr, default_expr = _parse_type_and_default(remainder.strip())
        specs.append(PropSpec(name=name.strip(), type_expr=type_expr, default_expr=default_expr))
    return specs


def _parse_type_and_default(source: str) -> tuple[str | None, str | None]:
    depth = 0
    in_quote: str | None = None
    for index, char in enumerate(source):
        if in_quote:
            if char == in_quote:
                in_quote = None
            continue
        if char in {'"', "'"}:
            in_quote = char
            continue
        if char in "([{":
            depth += 1
            continue
        if char in ")]}":
            depth -= 1
            continue
        if char == "=" and depth == 0:
            return source[:index].strip(), source[index + 1 :].strip()
    return source.strip() or None, None


def _split_top_level_commas(source: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    in_quote: str | None = None
    start = 0

    for index, char in enumerate(source):
        if in_quote:
            if char == in_quote:
                in_quote = None
            continue
        if char in {'"', "'"}:
            in_quote = char
            continue
        if char in "([{":
            depth += 1
            continue
        if char in ")]}":
            depth -= 1
            continue
        if char == "," and depth == 0:
            parts.append(source[start:index])
            start = index + 1
    parts.append(source[start:])
    return parts


def _handle_import(
    source: str,
    assets: list[AssetImport],
    component_imports: dict[str, str],
) -> None:
    asset_match = re.match(r'(css|js)\s+["\']([^"\']+)["\']$', source)
    if asset_match:
        assets.append(AssetImport(kind=asset_match.group(1), path=asset_match.group(2)))
        return

    component_match = re.match(r'["\']([^"\']+)["\']\s+as\s+([A-Za-z_][A-Za-z0-9_]*)$', source)
    if component_match:
        component_imports[component_match.group(2)] = component_match.group(1)
        return

    raise ValueError(f"Invalid import declaration: {source!r}")


def _skip_whitespace(source: str, position: int) -> int:
    while position < len(source) and source[position].isspace():
        position += 1
    return position


def _read_tag(source: str, position: int) -> tuple[str, int]:
    end = source.find("%}", position)
    if end == -1:
        raise ValueError("Unclosed Jinja tag")
    end += 2
    return source[position:end], end


def _read_block(source: str, position: int, end_tag: str) -> tuple[str, int]:
    pattern = re.compile(rf"\{{%\s*{re.escape(end_tag)}\s*%\}}")
    match = pattern.search(source, position)
    if not match:
        raise ValueError(f"Missing closing block for {end_tag}")
    return source[position:match.start()], match.end()


def _extract_tag_body(raw_tag: str) -> str:
    match = _TAG_RE.match(raw_tag)
    if not match:
        raise ValueError(f"Invalid Jinja tag: {raw_tag!r}")
    return match.group(1).strip()


def _split_keyword(source: str) -> tuple[str, str]:
    parts = source.split(None, 1)
    keyword = parts[0]
    remainder = parts[1].strip() if len(parts) > 1 else ""
    return keyword, remainder
