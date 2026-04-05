from __future__ import annotations

from pjx.core.scanner import Scanner, ScanTokenType, TagAttribute
from pjx.core.types import ProcessorContext, ProcessorResult


class AttrsProcessor:
    """Processes conditional attributes (?attr) and spread attributes (...{expr}).

    Runs before ExpressionProcessor so that conditional/spread attributes
    are transformed before expression resolution.

    ?hidden={not visible}  ->  {% if not visible %}hidden{% endif %}
    ?class={active and "sel"}  ->  {% if active and "sel" %}class="..."{% endif %}
    ...{attrs}  ->  {{ attrs | xmlattr }}
    """

    def process(self, source: str, ctx: ProcessorContext) -> ProcessorResult:
        scanner = Scanner(source)
        tokens = scanner.scan()

        has_special = any(
            attr.is_conditional or attr.is_spread
            for token in tokens
            if token.type in (ScanTokenType.OPEN_TAG, ScanTokenType.SELF_CLOSING_TAG)
            for attr in token.attributes
        )
        if not has_special:
            return ProcessorResult(source=source)

        result: list[str] = []
        for token in tokens:
            if token.type not in (
                ScanTokenType.OPEN_TAG,
                ScanTokenType.SELF_CLOSING_TAG,
            ):
                result.append(token.value)
                continue

            has_any = any(a.is_conditional or a.is_spread for a in token.attributes)
            if not has_any:
                result.append(token.value)
                continue

            tag_name = token.tag_name or ""
            normal_attrs: list[str] = []
            conditional_parts: list[str] = []
            spread_parts: list[str] = []

            for attr in token.attributes:
                if attr.is_spread:
                    if attr.value:
                        spread_parts.append(f"{{{{ {attr.value} | xmlattr }}}}")
                    continue

                if attr.is_conditional:
                    conditional_parts.append(self._compile_conditional(attr))
                    continue

                normal_attrs.append(self._format_attr(attr))

            # Build tag
            parts = [f"<{tag_name}"]
            if normal_attrs:
                parts.append(" " + " ".join(normal_attrs))
            if spread_parts:
                parts.append(" " + " ".join(spread_parts))
            if conditional_parts:
                parts.append(" " + " ".join(conditional_parts))
            if token.type == ScanTokenType.SELF_CLOSING_TAG:
                parts.append(" />")
            else:
                parts.append(">")
            result.append("".join(parts))

        return ProcessorResult(source="".join(result))

    def _compile_conditional(self, attr: TagAttribute) -> str:
        name = attr.name
        if attr.value is None:
            return name
        if attr.is_expression:
            return f'{{% if {attr.value} %}}{name}="{{{{ {attr.value} }}}}"{{% endif %}}'
        return f'{name}="{attr.value}"'

    def _format_attr(self, attr: TagAttribute) -> str:
        if attr.value is None:
            return attr.name
        if attr.is_expression:
            return f"{attr.name}={{{attr.value}}}"
        return f'{attr.name}="{attr.value}"'
