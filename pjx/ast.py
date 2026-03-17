"""AST nodes for the PJX template language.

All nodes are frozen dataclasses — immutable after construction.
`line` and `col` carry source location for error reporting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Base ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Node:
    line: int = 0
    col: int = 0


# ── Directives ────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PropDef(Node):
    name: str = ""
    type_expr: str | None = None  # "str", "list[str]", '"a"|"b"', etc.
    default_expr: str | None = None


@dataclass(frozen=True, slots=True)
class PropsBlock(Node):
    props: tuple[PropDef, ...] = ()


@dataclass(frozen=True, slots=True)
class SlotDecl(Node):
    name: str = "default"
    optional: bool = False


@dataclass(frozen=True, slots=True)
class StateField(Node):
    name: str = ""
    value: str = "null"  # JSON-compatible literal


@dataclass(frozen=True, slots=True)
class StateBlock(Node):
    fields: tuple[StateField, ...] = ()


@dataclass(frozen=True, slots=True)
class BindDirective(Node):
    module: str = ""
    class_name: str = ""


@dataclass(frozen=True, slots=True)
class LetDirective(Node):
    name: str = ""
    expr: str = ""


@dataclass(frozen=True, slots=True)
class FromImport(Node):
    module: str = ""
    names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ImportDirective(Node):
    path: str = ""


# ── Template body nodes ───────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TextNode(Node):
    content: str = ""


@dataclass(frozen=True, slots=True)
class ExprNode(Node):
    """Raw Jinja2 expression {{ ... }} — passed through after @-substitution."""

    content: str = ""  # including the {{ }} delimiters


@dataclass(frozen=True, slots=True)
class Attribute(Node):
    name: str = ""
    value: str | None = None  # None means boolean attribute


@dataclass(frozen=True, slots=True)
class HtmlElement(Node):
    tag: str = ""
    attrs: tuple[Attribute, ...] = ()
    children: tuple[Any, ...] = ()  # tuple[TemplateNode, ...]
    self_closing: bool = False


@dataclass(frozen=True, slots=True)
class ComponentCall(Node):
    name: str = ""
    attrs: tuple[Attribute, ...] = ()
    children: tuple[Any, ...] = ()  # default slot children
    named_slots: dict[str, tuple[Any, ...]] = field(default_factory=dict)
    self_closing: bool = False


@dataclass(frozen=True, slots=True)
class SlotNode(Node):
    """<slot /> or <slot name="x" />"""

    name: str = "default"
    scope_bindings: dict[str, str] = field(default_factory=dict)
    fallback: tuple[Any, ...] = ()


@dataclass(frozen=True, slots=True)
class NamedSlotContent(Node):
    """<:header>...</:header>"""

    name: str = ""
    let_bindings: tuple[str, ...] = ()
    children: tuple[Any, ...] = ()


# ── Control structures ────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ShowNode(Node):
    condition: str = ""  # raw Jinja2 expression (no {{ }})
    children: tuple[Any, ...] = ()
    fallback: tuple[Any, ...] = ()


@dataclass(frozen=True, slots=True)
class ForNode(Node):
    iterable: str = ""  # raw Jinja2 expression
    variable: str = "item"
    index_var: str | None = None
    children: tuple[Any, ...] = ()
    empty: tuple[Any, ...] = ()


@dataclass(frozen=True, slots=True)
class MatchCase(Node):
    value: str = ""
    children: tuple[Any, ...] = ()


@dataclass(frozen=True, slots=True)
class SwitchNode(Node):
    expression: str = ""  # raw Jinja2 expression
    cases: tuple[MatchCase, ...] = ()
    fallback: tuple[Any, ...] = ()


# ── Component definition (@component Name { ... }) ────────────────────────────


@dataclass(frozen=True, slots=True)
class ComponentDef(Node):
    name: str = ""
    props: PropsBlock | None = None
    slots: tuple[SlotDecl, ...] = ()
    state: StateBlock | None = None
    lets: tuple[LetDirective, ...] = ()
    bind: BindDirective | None = None
    children: tuple[Any, ...] = ()  # template body


# ── Root ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PjxFile(Node):
    """Root AST node for a .pjx file."""

    imports: tuple[FromImport | ImportDirective, ...] = ()
    bind: BindDirective | None = None
    props: PropsBlock | None = None
    slots: tuple[SlotDecl, ...] = ()
    state: StateBlock | None = None
    lets: tuple[LetDirective, ...] = ()
    body: tuple[Any, ...] = ()  # simple-mode template body
    components: tuple[ComponentDef, ...] = ()  # multi-component mode

    @property
    def is_multi_component(self) -> bool:
        return len(self.components) > 0


# Type alias for any template body node
TemplateNode = (
    TextNode
    | ExprNode
    | HtmlElement
    | ComponentCall
    | SlotNode
    | NamedSlotContent
    | ShowNode
    | ForNode
    | SwitchNode
)
