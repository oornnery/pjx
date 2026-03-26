"""Immutable AST nodes for PJX components.

Every node is a frozen dataclass with ``slots=True`` for memory efficiency.
``Node`` is a union type alias covering all body-level nodes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Frontmatter declarations
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExtendsDecl:
    """``extends "layouts/Base.jinja"``."""

    source: str


@dataclass(frozen=True, slots=True)
class FromImportDecl:
    """``from pydantic import EmailStr, HttpUrl``."""

    module: str
    names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ImportDecl:
    """Component import (default, named, wildcard).

    Examples::

        import Button from "./Button.jinja"
        import { A, B } from "./Card.jinja"
        import * from "./ui/"
    """

    names: tuple[str, ...]
    source: str
    alias: str | None = None
    wildcard: bool = False


@dataclass(frozen=True, slots=True)
class PropField:
    """Single field inside a ``props`` declaration."""

    name: str
    type_expr: str
    default: str | None = None


@dataclass(frozen=True, slots=True)
class PropsDecl:
    """``props { name: str }`` or ``props UserProps = { name: str }``."""

    fields: tuple[PropField, ...]
    name: str = ""


@dataclass(frozen=True, slots=True)
class SlotDecl:
    """``slot actions`` or ``slot footer = <span>Default</span>``."""

    name: str
    fallback: str | None = None


@dataclass(frozen=True, slots=True)
class StoreDecl:
    """``store theme = { dark: false, accent: "blue" }``."""

    name: str
    value: str  # raw JS object literal


@dataclass(frozen=True, slots=True)
class AssetDecl:
    """``css "styles/button.css"`` or ``js "scripts/dropdown.js"``."""

    kind: str  # "css" or "js"
    path: str


@dataclass(frozen=True, slots=True)
class LetDecl:
    """``let css_class = "todo-" + props.priority``."""

    name: str
    expr: str


@dataclass(frozen=True, slots=True)
class ConstDecl:
    """``const MAX_LENGTH = 140``."""

    name: str
    expr: str


@dataclass(frozen=True, slots=True)
class StateDecl:
    """``state count = 0``."""

    name: str
    value: str


@dataclass(frozen=True, slots=True)
class ComputedDecl:
    """``computed remaining = MAX_LENGTH - len(props.text)``."""

    name: str
    expr: str


# ---------------------------------------------------------------------------
# Body nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TextNode:
    """Raw text content."""

    content: str


@dataclass(frozen=True, slots=True)
class ExprNode:
    """``{{ expr }}`` interpolation."""

    expr: str


@dataclass(frozen=True, slots=True)
class ElementNode:
    """Standard HTML element."""

    tag: str
    attrs: dict[str, str | bool] = field(default_factory=dict)
    children: tuple[Node, ...] = ()
    self_closing: bool = False


@dataclass(frozen=True, slots=True)
class ShowNode:
    """``<Show when="condition">...</Show>``."""

    when: str
    body: tuple[Node, ...] = ()
    fallback: tuple[Node, ...] | None = None


@dataclass(frozen=True, slots=True)
class ForNode:
    """``<For each="items" as="item">...</For>``."""

    each: str
    as_var: str
    body: tuple[Node, ...] = ()
    empty: tuple[Node, ...] | None = None


@dataclass(frozen=True, slots=True)
class CaseNode:
    """Single case inside a ``<Switch>``."""

    value: str
    body: tuple[Node, ...] = ()


@dataclass(frozen=True, slots=True)
class SwitchNode:
    """``<Switch on="expr">``."""

    on: str
    cases: tuple[CaseNode, ...] = ()
    default: tuple[Node, ...] | None = None


@dataclass(frozen=True, slots=True)
class PortalNode:
    """``<Portal target="/url" swap="innerHTML">``."""

    target: str
    swap: str = "innerHTML"
    body: tuple[Node, ...] = ()


@dataclass(frozen=True, slots=True)
class ErrorBoundaryNode:
    """``<ErrorBoundary fallback="...">``."""

    fallback: str
    body: tuple[Node, ...] = ()
    error_slot: str | None = None


@dataclass(frozen=True, slots=True)
class AwaitNode:
    """``<Await src="/api/data" trigger="load">``."""

    src: str
    trigger: str = "load"
    loading: tuple[Node, ...] | None = None
    error: tuple[Node, ...] | None = None


@dataclass(frozen=True, slots=True)
class TransitionNode:
    """``<Transition enter="..." leave="...">``."""

    enter: str = ""
    leave: str = ""
    body: tuple[Node, ...] = ()


@dataclass(frozen=True, slots=True)
class TransitionGroupNode:
    """``<TransitionGroup tag="ul" enter="..." leave="..." move="...">``."""

    tag: str = "div"
    enter: str = ""
    leave: str = ""
    move: str = ""
    body: tuple[Node, ...] = ()


@dataclass(frozen=True, slots=True)
class FragmentNode:
    """``<Fragment>`` — renders children without a wrapper element."""

    children: tuple[Node, ...] = ()


@dataclass(frozen=True, slots=True)
class TeleportNode:
    """``<Teleport to="body">``."""

    to: str
    body: tuple[Node, ...] = ()


@dataclass(frozen=True, slots=True)
class SlotRenderNode:
    """``<Slot:name />`` — renders a declared slot."""

    name: str
    fallback: tuple[Node, ...] | None = None


@dataclass(frozen=True, slots=True)
class SlotPassNode:
    """``<slot:name>content</slot:name>`` — passes content to a child slot."""

    name: str
    content: tuple[Node, ...] = ()


@dataclass(frozen=True, slots=True)
class ComponentNode:
    """Usage of a PJX component: ``<Button variant="primary" ...props />``."""

    name: str
    attrs: dict[str, str | bool] = field(default_factory=dict)
    children: tuple[Node, ...] = ()
    slots: dict[str, tuple[Node, ...]] = field(default_factory=dict)
    spread: str | None = None


# ---------------------------------------------------------------------------
# Node union
# ---------------------------------------------------------------------------

Node = (
    TextNode
    | ExprNode
    | ElementNode
    | ShowNode
    | ForNode
    | SwitchNode
    | CaseNode
    | PortalNode
    | ErrorBoundaryNode
    | AwaitNode
    | TransitionNode
    | TransitionGroupNode
    | FragmentNode
    | TeleportNode
    | SlotRenderNode
    | SlotPassNode
    | ComponentNode
)

# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ScopedStyle:
    """CSS scoped to a component via hash-based attribute selector."""

    source: str
    hash: str


@dataclass(frozen=True, slots=True)
class CompiledComponent:
    """Result of compiling a Component AST."""

    jinja_source: str
    css: ScopedStyle | None = None
    alpine_data: str | None = None
    scope_hash: str = ""
    assets: tuple[AssetDecl, ...] = ()


# ---------------------------------------------------------------------------
# Root component
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Component:
    """Root AST node — a fully parsed ``.jinja`` component."""

    path: Path
    extends: ExtendsDecl | None = None
    from_imports: tuple[FromImportDecl, ...] = ()
    imports: tuple[ImportDecl, ...] = ()
    props: PropsDecl | None = None
    slots: tuple[SlotDecl, ...] = ()
    stores: tuple[StoreDecl, ...] = ()
    variables: tuple[LetDecl | ConstDecl, ...] = ()
    states: tuple[StateDecl, ...] = ()
    computed: tuple[ComputedDecl, ...] = ()
    assets: tuple[AssetDecl, ...] = ()
    body: tuple[Node, ...] = ()
    style: str | None = None
