"""PJX formatter — canonical frontmatter ordering with body preserved."""

from __future__ import annotations

import re
from pathlib import Path

from pjx.ast_nodes import Component
from pjx.parser import parse

_FRONTMATTER_RE = re.compile(r"\A(\s*---\n)(.*?)(\n---\n?)", re.DOTALL)


def format_source(source: str, path: Path | None = None) -> str:
    """Format a .jinja component source with canonical frontmatter ordering.

    The body (everything after the frontmatter) is preserved verbatim.
    Returns the formatted source string.

    Args:
        source: Raw .jinja component source.
        path: Optional file path for error reporting.
    """
    fm_match = _FRONTMATTER_RE.match(source)
    if not fm_match:
        # No frontmatter — nothing to format
        return source

    body = source[fm_match.end() :]
    component = parse(source, path)
    frontmatter = _format_frontmatter(component)

    if not frontmatter:
        # Frontmatter was empty after parsing — preserve original
        return source

    return f"---\n{frontmatter}\n---\n{body}"


def format_file(path: Path) -> tuple[str, bool]:
    """Format a .jinja file. Returns (formatted_source, changed).

    Args:
        path: Path to the .jinja file.

    Returns:
        Tuple of (formatted source, whether it differs from the original).
    """
    original = path.read_text(encoding="utf-8")
    formatted = format_source(original, path)
    return formatted, formatted != original


def _format_frontmatter(component: Component) -> str:
    """Build the frontmatter section in canonical declaration order.

    Order:
        1. extends
        2. from ... import ...
        3. import ... from ...
        4. props { ... }
        5. slot ...
        6. state ...
        7. computed ...
        8. let ... / const ...
        9. store ...
        10. css ... / js ...
        11. middleware ...
    """
    lines: list[str] = []

    # 1. extends
    if component.extends:
        lines.append(f'extends "{component.extends.source}"')

    # 2. from ... import ...
    for fi in component.from_imports:
        names = ", ".join(fi.names)
        lines.append(f"from {fi.module} import {names}")

    # 3. import ... from ...
    for imp in component.imports:
        names = ", ".join(imp.names)
        lines.append(f'import {names} from "{imp.source}"')

    # 4. props { ... }
    if component.props:
        if len(component.props.fields) == 1 and not component.props.name:
            f = component.props.fields[0]
            line = f"props {{ {_format_prop_field(f)} }}"
            lines.append(line)
        else:
            header = (
                f"props {component.props.name} = {{"
                if component.props.name
                else "props {"
            )
            lines.append(header)
            for f in component.props.fields:
                lines.append(f"  {_format_prop_field(f)}")
            lines.append("}")

    # 5. slot ...
    for s in component.slots:
        if s.fallback:
            lines.append(f"slot {s.name} = {s.fallback}")
        else:
            lines.append(f"slot {s.name}")

    # 6. state ...
    for s in component.states:
        lines.append(f"state {s.name} = {s.value}")

    # 7. computed ...
    for c in component.computed:
        lines.append(f"computed {c.name} = {c.expr}")

    # 8. let / const
    for v in component.variables:
        kind = "const" if type(v).__name__ == "ConstDecl" else "let"
        lines.append(f"{kind} {v.name} = {v.expr}")

    # 9. store
    for st in component.stores:
        lines.append(f"store {st.name} = {st.value}")

    # 10. css / js assets
    for a in component.assets:
        lines.append(f'{a.kind} "{a.path}"')

    # 11. action
    for act in component.actions:
        if act.params:
            params = ", ".join(_format_prop_field(p) for p in act.params)
            lines.append(f"action {act.name}({params})")
        else:
            lines.append(f"action {act.name}()")

    # 12. middleware
    for mw in component.middleware:
        names = ", ".join(f'"{n}"' for n in mw.names)
        lines.append(f"middleware {names}")

    return "\n".join(lines)


def _format_prop_field(f: object) -> str:
    """Format a single PropField."""
    line = f"{f.name}: {f.type_expr}"  # type: ignore[attr-defined]
    if f.default is not None:  # type: ignore[attr-defined]
        line += f" = {f.default}"  # type: ignore[attr-defined]
    return line
