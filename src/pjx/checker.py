"""PJX static analysis — validate imports, props, slots, expressions, and cycles."""

from __future__ import annotations

import ast
import re

from pjx.ast_nodes import Component, ComponentNode, Node
from pjx.errors import PJXError
from pjx.registry import ComponentRegistry

# Jinja2 builtins and common globals that should not be flagged as undefined
_JINJA_BUILTINS = frozenset(
    {
        "range",
        "lipsum",
        "dict",
        "cycler",
        "joiner",
        "namespace",
        "true",
        "false",
        "none",
        "True",
        "False",
        "None",
        "loop",
        "caller",
        "varargs",
        "kwargs",
        "request",
        "session",
        "config",
        "g",
        "url_for",
        "get_flashed_messages",
        "props",
        "seo",
        "body",
        "pjx_assets",
        "csrf_token",
        "slot",
    }
)


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


def check_prop_defaults(component: Component) -> list[PJXError]:
    """Validate that prop default expressions are valid Python."""
    errors: list[PJXError] = []
    if component.props is None:
        return errors
    for field in component.props.fields:
        if field.default is None:
            continue
        try:
            ast.parse(field.default, mode="eval")
        except SyntaxError as exc:
            errors.append(
                PJXError(
                    f"invalid default for prop {field.name!r}: {exc.msg}",
                    path=component.path,
                )
            )
    return errors


def check_unused_imports(component: Component) -> list[PJXError]:
    """Warn about imported component names that are never referenced in the body."""
    errors: list[PJXError] = []
    imported_names: set[str] = set()
    for imp in component.imports:
        imported_names.update(imp.names)
    if not imported_names:
        return errors

    used_names: set[str] = set()
    for node in _walk_nodes(component.body):
        if isinstance(node, ComponentNode):
            used_names.add(node.name)

    for name in sorted(imported_names - used_names):
        errors.append(
            PJXError(
                f"imported {name!r} is never used",
                path=component.path,
            )
        )
    return errors


def check_computed_cycles(component: Component) -> list[PJXError]:
    """Detect circular dependencies among computed declarations."""
    errors: list[PJXError] = []
    if not component.computed:
        return errors

    computed_names = {c.name for c in component.computed}
    # Build adjacency: computed name → set of other computed names it references
    graph: dict[str, set[str]] = {}
    for c in component.computed:
        refs: set[str] = set()
        for name in _extract_names(c.expr):
            if name in computed_names and name != c.name:
                refs.add(name)
        graph[c.name] = refs

    # DFS cycle detection
    visited: set[str] = set()
    in_stack: set[str] = set()

    def _dfs(node: str) -> str | None:
        visited.add(node)
        in_stack.add(node)
        for dep in graph.get(node, set()):
            if dep in in_stack:
                return dep
            if dep not in visited:
                result = _dfs(dep)
                if result is not None:
                    return result
        in_stack.discard(node)
        return None

    for name in graph:
        if name not in visited:
            cycle_node = _dfs(name)
            if cycle_node is not None:
                errors.append(
                    PJXError(
                        f"circular dependency in computed {cycle_node!r}",
                        path=component.path,
                    )
                )
    return errors


def check_undefined_vars(component: Component) -> list[PJXError]:
    """Detect variables used in expressions that are not declared anywhere.

    Conservative: only flags names that appear in state/computed/let/const
    expressions and are clearly not declared as props, state, variables, etc.
    """
    errors: list[PJXError] = []

    # Collect all declared names
    declared: set[str] = set(_JINJA_BUILTINS)

    if component.props:
        for field in component.props.fields:
            declared.add(field.name)

    for s in component.states:
        declared.add(s.name)

    for v in component.variables:
        declared.add(v.name)

    for c in component.computed:
        declared.add(c.name)

    for store in component.stores:
        declared.add(store.name)

    for imp in component.imports:
        declared.update(imp.names)

    # Collect names used in expressions
    exprs: list[tuple[str, str]] = []
    for s in component.states:
        exprs.append((f"state {s.name}", s.value))
    for c in component.computed:
        exprs.append((f"computed {c.name}", c.expr))
    for v in component.variables:
        exprs.append((f"variable {v.name}", v.expr))

    for label, expr in exprs:
        for name in _extract_names(expr):
            if name not in declared:
                errors.append(
                    PJXError(
                        f"possibly undefined {name!r} in {label}",
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
    errors.extend(check_prop_defaults(component))
    errors.extend(check_unused_imports(component))
    errors.extend(check_computed_cycles(component))
    errors.extend(check_undefined_vars(component))
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


_NAME_RE = re.compile(r"\b([a-zA-Z_]\w*)\b")
_PYTHON_KEYWORDS = frozenset(
    {
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
    }
)
_PYTHON_BUILTINS = frozenset(
    {
        "len",
        "str",
        "int",
        "float",
        "bool",
        "list",
        "dict",
        "set",
        "tuple",
        "range",
        "enumerate",
        "zip",
        "map",
        "filter",
        "sorted",
        "reversed",
        "min",
        "max",
        "sum",
        "abs",
        "round",
        "print",
        "type",
        "isinstance",
        "hasattr",
        "getattr",
        "setattr",
        "any",
        "all",
        "repr",
        "format",
    }
)


def _extract_names(expr: str) -> set[str]:
    """Extract identifier names from a Python-like expression.

    Filters out keywords, builtins, and attribute access chains
    (only the root name is returned, e.g. ``props.name`` → ``props``).
    """
    names: set[str] = set()
    for match in _NAME_RE.finditer(expr):
        name = match.group(1)
        if name in _PYTHON_KEYWORDS or name in _PYTHON_BUILTINS:
            continue
        # Skip attribute names (preceded by a dot)
        start = match.start()
        if start > 0 and expr[start - 1] == ".":
            continue
        names.add(name)
    return names
