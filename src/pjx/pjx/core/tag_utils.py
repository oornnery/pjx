from __future__ import annotations

from pjx.core.scanner import TagAttribute


def format_attr(name: str, value: str | None, is_expression: bool) -> str:
    if value is None:
        return name
    if is_expression:
        return f'{name}="{{{{ {value} }}}}"'
    return f'{name}="{value}"'


def format_original_attr(attr: TagAttribute) -> str:
    if attr.is_spread:
        if attr.value:
            return f"...{{{attr.value}}}"
        return "..."
    prefix = "?" if attr.is_conditional else ""
    if attr.value is None:
        return f"{prefix}{attr.name}"
    if attr.is_expression:
        return f"{prefix}{attr.name}={{{attr.value}}}"
    return f'{prefix}{attr.name}="{attr.value}"'


def rebuild_tag(tag_name: str, attrs: list[str], self_closing: bool) -> str:
    attr_str = ""
    if attrs:
        attr_str = " " + " ".join(attrs)
    if self_closing:
        return f"<{tag_name}{attr_str} />"
    return f"<{tag_name}{attr_str}>"
