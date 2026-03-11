from __future__ import annotations

from dataclasses import dataclass, field
import re


@dataclass(slots=True)
class RawNode:
    source: str


@dataclass(slots=True)
class ElementNode:
    name: str
    attrs: list[tuple[str, str | None]]
    children: list["Node"] = field(default_factory=list)
    self_closing: bool = False
    raw_open: str = ""


Node = RawNode | ElementNode


_SLOT_START_RE = re.compile(
    r"^\s*\{%\s*slot\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*?)\))?\s*%\}\s*$", re.DOTALL
)
_SLOT_END_RE = re.compile(r"^\s*\{%\s*endslot\s*%\}\s*$")
_JINJA_EXPR_RE = re.compile(r"^\s*\{\{\s*(.*?)\s*\}\}\s*$", re.DOTALL)


def parse_markup(source: str) -> list[Node]:
    root: list[Node] = []
    stack: list[ElementNode] = []
    pos = 0
    length = len(source)

    while pos < length:
        if source.startswith("{{", pos):
            raw, pos = _read_delimited(source, pos, "{{", "}}")
            _current_children(root, stack).append(RawNode(raw))
            continue
        if source.startswith("{%", pos):
            raw, pos = _read_delimited(source, pos, "{%", "%}")
            _current_children(root, stack).append(RawNode(raw))
            continue
        if source.startswith("{#", pos):
            raw, pos = _read_delimited(source, pos, "{#", "#}")
            _current_children(root, stack).append(RawNode(raw))
            continue
        if source[pos] == "<" and _looks_like_tag(source, pos):
            tag, pos = _read_tag(source, pos)
            if tag is None:
                _current_children(root, stack).append(RawNode(source[pos]))
                pos += 1
                continue
            kind, name, attrs, self_closing, raw_open = tag
            if kind == "close":
                while stack:
                    node = stack.pop()
                    if node.name == name:
                        break
                continue
            element = ElementNode(
                name=name,
                attrs=attrs,
                self_closing=self_closing,
                raw_open=raw_open,
            )
            _current_children(root, stack).append(element)
            if not self_closing:
                stack.append(element)
            continue

        next_pos = _next_special(source, pos)
        _current_children(root, stack).append(RawNode(source[pos:next_pos]))
        pos = next_pos

    return root


def extract_named_slots(
    children: list[Node],
) -> tuple[list[Node], list[tuple[str, tuple[str, ...], list[Node]]]]:
    default_children: list[Node] = []
    slots: list[tuple[str, tuple[str, ...], list[Node]]] = []
    index = 0
    while index < len(children):
        node = children[index]
        if isinstance(node, RawNode):
            match = _SLOT_START_RE.match(node.source)
            if match:
                slot_name = match.group(1)
                params = tuple(
                    item.strip()
                    for item in (match.group(2) or "").split(",")
                    if item.strip()
                )
                index += 1
                slot_children: list[Node] = []
                while index < len(children):
                    candidate = children[index]
                    if isinstance(candidate, RawNode) and _SLOT_END_RE.match(
                        candidate.source
                    ):
                        break
                    slot_children.append(candidate)
                    index += 1
                slots.append((slot_name, params, slot_children))
                index += 1
                continue
        default_children.append(node)
        index += 1
    return default_children, slots


def attr_value_to_expr(value: str | None, *, force_expression: bool = False) -> str:
    if value is None:
        return "True"
    expr_match = _JINJA_EXPR_RE.match(value)
    if expr_match:
        return expr_match.group(1).strip()
    if force_expression:
        return value.strip()
    return repr(value)


def split_children_by_tag(
    children: list[Node], tag_name: str
) -> tuple[list[Node], list[Node] | None]:
    before: list[Node] = []
    after: list[Node] | None = None
    for child in children:
        if isinstance(child, ElementNode) and child.name == tag_name:
            after = child.children
            continue
        if after is None:
            before.append(child)
        else:
            after.append(child)
    return before, after


def _current_children(root: list[Node], stack: list[ElementNode]) -> list[Node]:
    if not stack:
        return root
    return stack[-1].children


def _read_delimited(
    source: str, start: int, open_delim: str, close_delim: str
) -> tuple[str, int]:
    end = source.find(close_delim, start + len(open_delim))
    if end == -1:
        raise ValueError(f"Missing closing delimiter {close_delim!r}")
    end += len(close_delim)
    return source[start:end], end


def _looks_like_tag(source: str, pos: int) -> bool:
    if pos + 1 >= len(source):
        return False
    next_char = source[pos + 1]
    return next_char.isalpha() or next_char == "/"


def _next_special(source: str, start: int) -> int:
    indices = [source.find(token, start) for token in ("<", "{{", "{%", "{#")]
    valid = [index for index in indices if index != -1]
    return min(valid) if valid else len(source)


def _read_tag(
    source: str,
    start: int,
) -> tuple[tuple[str, str, list[tuple[str, str | None]], bool, str] | None, int]:
    pos = start + 1
    closing = False
    if source[pos] == "/":
        closing = True
        pos += 1

    name_start = pos
    while pos < len(source) and (
        source[pos].isalnum() or source[pos] in {"-", "_", ":"}
    ):
        pos += 1
    name = source[name_start:pos]
    if not name:
        return None, start

    attrs: list[tuple[str, str | None]] = []
    self_closing = False

    while pos < len(source):
        while pos < len(source) and source[pos].isspace():
            pos += 1
        if pos >= len(source):
            break
        if source[pos] == ">":
            pos += 1
            break
        if source[pos] == "/" and pos + 1 < len(source) and source[pos + 1] == ">":
            self_closing = True
            pos += 2
            break

        attr_start = pos
        while (
            pos < len(source)
            and not source[pos].isspace()
            and source[pos] not in {"=", ">", "/"}
        ):
            pos += 1
        attr_name = source[attr_start:pos]
        attr_value: str | None = None

        while pos < len(source) and source[pos].isspace():
            pos += 1
        if pos < len(source) and source[pos] == "=":
            pos += 1
            while pos < len(source) and source[pos].isspace():
                pos += 1
            if pos < len(source) and source[pos] in {'"', "'"}:
                quote = source[pos]
                pos += 1
                value_start = pos
                while pos < len(source) and source[pos] != quote:
                    pos += 1
                attr_value = source[value_start:pos]
                pos += 1
            else:
                value_start = pos
                while (
                    pos < len(source)
                    and not source[pos].isspace()
                    and source[pos] not in {">", "/"}
                ):
                    pos += 1
                attr_value = source[value_start:pos]
        attrs.append((attr_name, attr_value))

    kind = "close" if closing else "open"
    return (kind, name, attrs, self_closing, source[start:pos]), pos
