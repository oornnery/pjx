"""PJX slot resolution — match declared slots with passed content."""

from __future__ import annotations

from pjx.ast_nodes import SlotDecl


def resolve_slots(
    declarations: tuple[SlotDecl, ...],
    passed_slots: dict[str, str],
    children: str = "",
) -> dict[str, str]:
    """Resolve slot declarations with passed content.

    Args:
        declarations: Slot declarations from the component.
        passed_slots: Named slot content passed by the parent.
        children: Default children content (used for unnamed/default slot).

    Returns:
        Dict mapping slot names to their resolved HTML content.
    """
    resolved: dict[str, str] = {}

    for decl in declarations:
        if decl.name in passed_slots:
            resolved[decl.name] = passed_slots[decl.name]
        elif decl.name == "default" and children:
            resolved[decl.name] = children
        elif decl.fallback is not None:
            resolved[decl.name] = decl.fallback
        else:
            resolved[decl.name] = ""

    # Pass through any slots not declared (for flexibility)
    for name, content in passed_slots.items():
        if name not in resolved:
            resolved[name] = content

    # Always include default slot from children if not explicitly declared
    if "default" not in resolved and children:
        resolved["default"] = children

    return resolved
