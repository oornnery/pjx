from __future__ import annotations

import re
from pathlib import Path

from .ast import (
    ActionDirectiveNode,
    ComponentDirectiveNode,
    ComponentNode,
    ComputedDirectiveNode,
    ImportNode,
    InjectDirectiveNode,
    PropDeclNode,
    PropsAliasNode,
    PropsDirectiveNode,
    ProvideDirectiveNode,
    SignalDirectiveNode,
    SlotDirectiveNode,
    SourceFileNode,
)


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TAG_RE = re.compile(r"^\s*\{%\s*(.*?)\s*%\}\s*$", re.DOTALL)
_SIGNAL_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*signal\((.*)\)\s*$",
    re.DOTALL,
)


def parse_component_source(source: str, path: Path) -> SourceFileNode:
    imports: list[ImportNode] = []
    prop_aliases: list[PropsAliasNode] = []
    component: ComponentNode | None = None
    position = 0

    while True:
        position = _skip_whitespace(source, position)
        if position >= len(source):
            break
        if not source.startswith("{%", position):
            raise ValueError(f"{path}: unexpected content before component declaration")

        raw_tag, next_position = _read_tag(source, position)
        inner = _extract_tag_body(raw_tag)
        keyword, remainder = _split_keyword(inner)

        match keyword:
            case "import":
                position = _handle_top_level_import(remainder, imports, next_position)
            case "set":
                position = _handle_top_level_set(inner, prop_aliases, next_position)
            case "component":
                if component is not None:
                    raise ValueError(
                        f"{path}: multiple component declarations are not supported"
                    )
                component, position = _handle_top_level_component(
                    source,
                    next_position,
                    remainder,
                    path,
                )
                break
            case _:
                raise ValueError(f"{path}: unexpected top-level tag {keyword!r}")

    if component is None:
        raise ValueError(f"{path}: expected a component declaration")

    position = _skip_whitespace(source, position)
    if position != len(source):
        raise ValueError(f"{path}: unexpected content after component declaration")

    return SourceFileNode(
        imports=tuple(imports),
        prop_aliases=tuple(prop_aliases),
        component=component,
    )


def _parse_component(
    source: str,
    position: int,
    signature_source: str,
    path: Path,
) -> tuple[ComponentNode, int]:
    name, modifiers = _parse_component_signature(signature_source, path)
    body, end_position = _read_block(source, position, "endcomponent")
    directives, remainder = _parse_component_directives(body)
    return (
        ComponentNode(
            name=name,
            modifiers=modifiers,
            directives=tuple(directives),
            body=remainder,
        ),
        end_position,
    )


def _parse_component_signature(source: str, path: Path) -> tuple[str, tuple[str, ...]]:
    tokens = source.split()
    if not tokens:
        raise ValueError(f"{path}: component declaration requires a name")
    name = tokens[0]
    if not _IDENTIFIER_RE.fullmatch(name):
        raise ValueError(f"{path}: invalid component name {name!r}")

    modifiers = tuple(tokens[1:])
    for modifier in modifiers:
        if not _IDENTIFIER_RE.fullmatch(modifier):
            raise ValueError(f"{path}: invalid component modifier {modifier!r}")
    return name, modifiers


def _parse_component_directives(body: str) -> tuple[list[ComponentDirectiveNode], str]:
    directives: list[ComponentDirectiveNode] = []
    position = 0

    while True:
        position = _skip_whitespace(body, position)
        if not body.startswith("{%", position):
            break

        raw_tag, next_position = _read_tag(body, position)
        inner = _extract_tag_body(raw_tag)
        keyword, remainder = _split_keyword(inner)

        match keyword:
            case "props":
                directive, position = _handle_props(remainder, next_position)
            case "inject":
                directive, position = _handle_inject(remainder, next_position)
            case "provide":
                directive, position = _handle_provide(remainder, next_position)
            case "computed":
                directive, position = _handle_computed(remainder, body, next_position)
            case "slot":
                directive, position = _handle_slot(remainder, body, next_position)
            case "signal":
                directive, position = _handle_signal(remainder, next_position)
            case "action":
                directive, position = _handle_action(remainder, body, next_position)
            case _:
                break

        directives.append(directive)

    return directives, body[position:]


def _handle_top_level_import(
    source: str,
    imports: list[ImportNode],
    next_position: int,
) -> int:
    imports.append(_parse_import(source))
    return next_position


def _handle_top_level_set(
    tag_body: str,
    prop_aliases: list[PropsAliasNode],
    next_position: int,
) -> int:
    prop_aliases.append(_parse_props_alias(tag_body))
    return next_position


def _handle_top_level_component(
    source: str,
    position: int,
    signature_source: str,
    path: Path,
) -> tuple[ComponentNode, int]:
    return _parse_component(source, position, signature_source, path)


def _handle_props(source: str, next_position: int) -> tuple[PropsDirectiveNode, int]:
    return _parse_props_directive(source), next_position


def _handle_inject(source: str, next_position: int) -> tuple[InjectDirectiveNode, int]:
    return InjectDirectiveNode(names=_parse_name_list(source)), next_position


def _handle_provide(
    source: str, next_position: int
) -> tuple[ProvideDirectiveNode, int]:
    return ProvideDirectiveNode(names=_parse_name_list(source)), next_position


def _handle_computed(
    source: str,
    body: str,
    next_position: int,
) -> tuple[ComputedDirectiveNode, int]:
    block_body, position = _read_block(body, next_position, "endcomputed")
    return ComputedDirectiveNode(name=source.strip(), body=block_body), position


def _handle_slot(
    source: str,
    body: str,
    next_position: int,
) -> tuple[SlotDirectiveNode, int]:
    slot_name, params = _parse_slot_signature(source)
    _, position = _read_block(body, next_position, "endslot")
    return SlotDirectiveNode(name=slot_name, params=params), position


def _handle_signal(source: str, next_position: int) -> tuple[SignalDirectiveNode, int]:
    signal_name, expr = _parse_signal(source)
    return SignalDirectiveNode(name=signal_name, expr=expr), next_position


def _handle_action(
    source: str,
    body: str,
    next_position: int,
) -> tuple[ActionDirectiveNode, int]:
    block_body, position = _read_block(body, next_position, "endaction")
    return ActionDirectiveNode(name=source.strip(), body=block_body), position


def _parse_props_directive(source: str) -> PropsDirectiveNode:
    if _IDENTIFIER_RE.fullmatch(source):
        return PropsDirectiveNode(alias_name=source)
    return PropsDirectiveNode(props=tuple(_parse_inline_props(source)))


def _parse_name_list(source: str) -> tuple[str, ...]:
    names = tuple(item for item in source.split() if item)
    for name in names:
        if not _IDENTIFIER_RE.fullmatch(name):
            raise ValueError(f"Invalid identifier {name!r}")
    return names


def _parse_slot_signature(source: str) -> tuple[str, tuple[str, ...]]:
    match = re.match(
        r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*?)\))?$", source.strip(), re.DOTALL
    )
    if not match:
        raise ValueError(f"Invalid slot signature: {source!r}")
    params = tuple(
        item.strip() for item in (match.group(2) or "").split(",") if item.strip()
    )
    return match.group(1), params


def _parse_signal(source: str) -> tuple[str, str]:
    match = _SIGNAL_RE.match(source)
    if not match:
        raise ValueError(f"Invalid signal declaration: {source!r}")
    return match.group(1), match.group(2).strip()


def _parse_props_alias(tag_body: str) -> PropsAliasNode:
    match = re.match(
        r"set\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\{.*\})", tag_body, re.DOTALL
    )
    if not match:
        raise ValueError(f"Invalid props alias declaration: {tag_body!r}")
    name = match.group(1)
    payload = match.group(2).strip()
    if not name.endswith("Props"):
        raise ValueError(f"Props alias must end with 'Props': {name}")
    return PropsAliasNode(name=name, props=tuple(_parse_alias_entries(payload[1:-1])))


def _parse_alias_entries(source: str) -> list[PropDeclNode]:
    specs: list[PropDeclNode] = []
    for entry in _split_top_level_commas(source):
        item = entry.strip()
        if not item:
            continue
        key_match = re.match(r'["\']([^"\']+)["\']\s*:\s*(.*)$', item, re.DOTALL)
        if not key_match:
            raise ValueError(f"Invalid props alias entry: {entry!r}")
        type_expr, default_expr = _parse_type_and_default(key_match.group(2).strip())
        specs.append(
            PropDeclNode(
                name=key_match.group(1),
                type_expr=type_expr,
                default_expr=default_expr,
            )
        )
    return specs


def _parse_inline_props(source: str) -> list[PropDeclNode]:
    specs: list[PropDeclNode] = []
    for entry in _split_top_level_commas(source):
        item = entry.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(f"Invalid prop declaration: {item!r}")
        name, remainder = item.split(":", 1)
        prop_name = name.strip()
        if not _IDENTIFIER_RE.fullmatch(prop_name):
            raise ValueError(f"Invalid prop name: {prop_name!r}")
        type_expr, default_expr = _parse_type_and_default(remainder.strip())
        specs.append(
            PropDeclNode(name=prop_name, type_expr=type_expr, default_expr=default_expr)
        )
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


def _parse_import(source: str) -> ImportNode:
    asset_match = re.match(r'(css|js)\s+["\']([^"\']+)["\']$', source)
    if asset_match:
        return ImportNode(kind=asset_match.group(1), path=asset_match.group(2))

    component_match = re.match(
        r'["\']([^"\']+)["\']\s+as\s+([A-Za-z_][A-Za-z0-9_]*)$', source
    )
    if component_match:
        return ImportNode(
            kind="component",
            path=component_match.group(1),
            alias=component_match.group(2),
        )

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
    return source[position : match.start()], match.end()


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
