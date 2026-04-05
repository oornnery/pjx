from __future__ import annotations

from pjx.core.scanner import Scanner, ScanTokenType
from pjx.core.tag_utils import format_attr, format_original_attr, rebuild_tag
from pjx.core.types import ProcessorContext, ProcessorResult


class HTMXAliasProcessor:
    """Processes htmx:* and sse:* attribute aliases.

    htmx:{name} -> hx-{name}
    sse:{name} -> sse-{name}
    """

    slot = 40  # ProcessorSlot.ALIAS

    def process(self, source: str, ctx: ProcessorContext) -> ProcessorResult:
        scanner = Scanner(source)
        tokens = scanner.scan()
        result: list[str] = []

        for token in tokens:
            if token.type not in (
                ScanTokenType.OPEN_TAG,
                ScanTokenType.SELF_CLOSING_TAG,
            ):
                result.append(token.value)
                continue

            tag_name = token.tag_name or ""
            new_attrs: list[str] = []
            changed = False

            for attr in token.attributes:
                if attr.namespace == "htmx":
                    attr_name = attr.name.split(":", 1)[1]
                    new_attrs.append(format_attr(f"hx-{attr_name}", attr.value, attr.is_expression))
                    changed = True
                    continue

                if attr.namespace == "sse":
                    attr_name = attr.name.split(":", 1)[1]
                    new_attrs.append(
                        format_attr(f"sse-{attr_name}", attr.value, attr.is_expression)
                    )
                    changed = True
                    continue

                new_attrs.append(format_original_attr(attr))

            if changed:
                result.append(
                    rebuild_tag(
                        tag_name,
                        new_attrs,
                        token.type == ScanTokenType.SELF_CLOSING_TAG,
                    )
                )
            else:
                result.append(token.value)

        return ProcessorResult(source="".join(result))
