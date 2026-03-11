from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PropDeclNode:
    name: str
    type_expr: str | None = None
    default_expr: str | None = None


@dataclass(slots=True, frozen=True)
class ImportNode:
    kind: str
    path: str
    alias: str | None = None


@dataclass(slots=True, frozen=True)
class PropsAliasNode:
    name: str
    props: tuple[PropDeclNode, ...]


@dataclass(slots=True, frozen=True)
class PropsDirectiveNode:
    props: tuple[PropDeclNode, ...] = ()
    alias_name: str | None = None


@dataclass(slots=True, frozen=True)
class InjectDirectiveNode:
    names: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class ProvideDirectiveNode:
    names: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class ComputedDirectiveNode:
    name: str
    body: str


@dataclass(slots=True, frozen=True)
class SlotDirectiveNode:
    name: str
    params: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class SignalDirectiveNode:
    name: str
    expr: str


@dataclass(slots=True, frozen=True)
class ActionDirectiveNode:
    name: str
    body: str


type ComponentDirectiveNode = (
    PropsDirectiveNode
    | InjectDirectiveNode
    | ProvideDirectiveNode
    | ComputedDirectiveNode
    | SlotDirectiveNode
    | SignalDirectiveNode
    | ActionDirectiveNode
)


@dataclass(slots=True, frozen=True)
class ComponentNode:
    name: str
    modifiers: tuple[str, ...]
    directives: tuple[ComponentDirectiveNode, ...]
    body: str


@dataclass(slots=True, frozen=True)
class SourceFileNode:
    imports: tuple[ImportNode, ...]
    prop_aliases: tuple[PropsAliasNode, ...]
    component: ComponentNode
