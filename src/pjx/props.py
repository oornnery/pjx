"""PJX props — generate Pydantic BaseModel from PropsDecl AST."""

from __future__ import annotations

import builtins
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

    # Also make builtins available for eval
    namespace["__builtins__"] = builtins.__dict__

    field_definitions: dict[str, Any] = {}

    for field in decl.fields:
        try:
            field_type = eval(field.type_expr, namespace)  # noqa: S307
        except Exception as exc:
            raise PropValidationError(
                f"invalid type expression: {field.type_expr!r}"
            ) from exc

        if field.default is not None:
            try:
                default_value = eval(field.default, namespace)  # noqa: S307
            except Exception:
                default_value = field.default

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

    return create_model(decl.name, **field_definitions)


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
