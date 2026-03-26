"""PJX static analysis — validate imports, props, and slots at check time."""

from __future__ import annotations

from pjx.ast_nodes import Component, ComponentNode, Node
from pjx.errors import PJXError
from pjx.registry import ComponentRegistry


def check_imports(component: Component, registry: ComponentRegistry) -> list[PJXError]:
    """Verify that all imports in the component resolve to files."""
    errors: list[PJXError] = []
    for imp in component.imports:
        try:
            registry.resolve(imp, component.path)
        except PJXError as exc:
            errors.append(exc)
    return errors


def check_props(component: Component, registry: ComponentRegistry) -> list[PJXError]:
    """Verify that required props are passed to child components."""
    errors: list[PJXError] = []
    for node in _walk_nodes(component.body):
        if not isinstance(node, ComponentNode):
            continue
        child = registry.get(node.name)
        if child is None or child.props is None:
            continue
        passed = set(node.attrs.keys())
        for field in child.props.fields:
            if field.default is None and field.name not in passed:
                errors.append(
                    PJXError(
                        f"<{node.name}> missing required prop {field.name!r}",
                        path=component.path,
                    )
                )
    return errors


def check_slots(component: Component, registry: ComponentRegistry) -> list[PJXError]:
    """Verify that slot passes match declared slots in child components."""
    errors: list[PJXError] = []
    for node in _walk_nodes(component.body):
        if not isinstance(node, ComponentNode):
            continue
        child = registry.get(node.name)
        if child is None:
            continue
        declared_slots = {s.name for s in child.slots} | {"default"}
        for slot_name in node.slots:
            if slot_name not in declared_slots:
                errors.append(
                    PJXError(
                        f"<{node.name}> passes unknown slot {slot_name!r}",
                        path=component.path,
                    )
                )
    return errors


def check_all(component: Component, registry: ComponentRegistry) -> list[PJXError]:
    """Run all static checks on a component."""
    errors: list[PJXError] = []
    errors.extend(check_imports(component, registry))
    errors.extend(check_props(component, registry))
    errors.extend(check_slots(component, registry))
    return errors


def _walk_nodes(nodes: tuple[Node, ...]) -> list[Node]:
    """Recursively walk all nodes in the body tree."""
    result: list[Node] = []
    for node in nodes:
        result.append(node)
        # Walk children for nodes that have them
        for attr in ("children", "body", "cases", "fallback"):
            children = getattr(node, attr, None)
            if isinstance(children, tuple):
                result.extend(_walk_nodes(children))
    return result
