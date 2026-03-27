"""PJX props — generate Pydantic BaseModel from PropsDecl AST."""

from __future__ import annotations

import ast
from typing import Any

from pydantic import BaseModel, Field, create_model

from pjx.ast_nodes import PropsDecl
from pjx.errors import PropValidationError

# Types that are auto-imported (no `from` statement needed)
_BUILTIN_TYPES: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "None": type(None),
    "Any": Any,
}


def _resolve_type(expr: str, namespace: dict[str, Any]) -> Any:
    """Safely resolve a type expression without eval().

    Supports simple names (``str``), generic subscripts (``list[str]``),
    union syntax (``str | None``), and nested combinations.

    Args:
        expr: Type expression string from the DSL.
        namespace: Allowed type names to resolve against.

    Returns:
        The resolved Python type.

    Raises:
        PropValidationError: If the expression uses unsupported syntax.
    """
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise PropValidationError(f"invalid type expression: {expr!r}") from exc

    return _eval_type_node(tree.body, namespace, expr)


def _eval_type_node(node: ast.expr, namespace: dict[str, Any], expr: str) -> Any:
    """Recursively resolve an AST node to a Python type."""
    if isinstance(node, ast.Name):
        if node.id not in namespace:
            raise PropValidationError(
                f"unknown type {node.id!r} in expression: {expr!r}"
            )
        return namespace[node.id]

    if isinstance(node, ast.Subscript):
        # e.g. list[str], dict[str, int]
        origin = _eval_type_node(node.slice, namespace, expr)
        base = _eval_type_node(node.value, namespace, expr)
        return base[origin]

    if isinstance(node, ast.Tuple):
        # e.g. dict[str, int] — the slice is a Tuple
        return tuple(_eval_type_node(elt, namespace, expr) for elt in node.elts)

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        # e.g. str | None (PEP 604 union)
        left = _eval_type_node(node.left, namespace, expr)
        right = _eval_type_node(node.right, namespace, expr)
        return left | right

    if isinstance(node, ast.Constant) and node.value is None:
        return type(None)

    raise PropValidationError(f"unsupported syntax in type expression: {expr!r}")


# DSL uses JavaScript-style booleans; map to Python before literal_eval
_DSL_CONSTANTS: dict[str, str] = {
    "true": "True",
    "false": "False",
    "null": "None",
}


def _safe_eval_default(expr: str) -> Any:
    """Safely evaluate a default value expression using ast.literal_eval.

    Only allows Python literals: strings, numbers, bools, None, lists, dicts,
    tuples, sets. Also accepts DSL-style ``true``/``false``/``null``.
    No function calls, attribute access, or arbitrary code.

    Args:
        expr: Default value expression from the DSL.

    Returns:
        The evaluated Python literal value.

    Raises:
        PropValidationError: If the expression is not a safe literal.
    """
    # Normalize DSL constants (true → True, false → False, null → None)
    normalized = _DSL_CONSTANTS.get(expr, expr)
    try:
        return ast.literal_eval(normalized)
    except (ValueError, SyntaxError) as exc:
        raise PropValidationError(
            f"unsafe default value expression: {expr!r} — "
            f"only literals (strings, numbers, bools, None, lists, dicts) are allowed"
        ) from exc


def generate_props_model(
    decl: PropsDecl,
    extra_types: dict[str, Any] | None = None,
) -> type[BaseModel]:
    """Generate a Pydantic BaseModel from a PropsDecl AST node.

    Args:
        decl: The parsed props declaration.
        extra_types: Additional types to resolve (from ``from`` imports).

    Returns:
        A dynamically created Pydantic BaseModel class.
    """
    namespace: dict[str, Any] = {**_BUILTIN_TYPES}
    if extra_types:
        namespace.update(extra_types)

    field_definitions: dict[str, Any] = {}

    for field in decl.fields:
        field_type = _resolve_type(field.type_expr, namespace)

        if field.default is not None:
            default_value = _safe_eval_default(field.default)

            # Use Field(default_factory=...) for mutable defaults
            if isinstance(default_value, (list, dict, set)):
                field_definitions[field.name] = (
                    field_type,
                    Field(default_factory=lambda v=default_value: type(v)(v)),
                )
            else:
                field_definitions[field.name] = (field_type, default_value)
        else:
            field_definitions[field.name] = (field_type, ...)

    return create_model(decl.name or "Props", **field_definitions)


def separate_attrs(
    props_decl: PropsDecl | None,
    all_attrs: dict[str, str | bool],
) -> tuple[dict[str, str | bool], dict[str, str | bool]]:
    """Split component attributes into declared props and extra passthrough attrs.

    Args:
        props_decl: The component's props declaration. If ``None``, all
            attributes are treated as props (backwards compatible).
        all_attrs: All attributes passed on the component tag.

    Returns:
        A ``(props, extras)`` tuple. *props* contains attributes matching
        declared prop names; *extras* contains the rest.
    """
    if props_decl is None:
        return dict(all_attrs), {}

    declared = {f.name for f in props_decl.fields}
    props: dict[str, str | bool] = {}
    extras: dict[str, str | bool] = {}
    for name, value in all_attrs.items():
        if name in declared:
            props[name] = value
        else:
            extras[name] = value
    return props, extras


def validate_props(model: type[BaseModel], data: dict[str, Any]) -> BaseModel:
    """Validate a props dict against a generated model.

    Args:
        model: The Pydantic model class.
        data: Raw props data.

    Returns:
        Validated model instance.

    Raises:
        PropValidationError: When validation fails.
    """
    try:
        return model(**data)
    except Exception as exc:
        raise PropValidationError(f"props validation failed: {exc}") from exc
