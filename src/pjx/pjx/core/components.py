from __future__ import annotations

import re

from pjx.core.scanner import Scanner, ScanToken, ScanTokenType
from pjx.core.types import ProcessorContext, ProcessorResult
from pjx.errors import PJXError, SourceLocation

SLOT_TAG = "Slot"


class ComponentProcessor:
    def process(self, source: str, ctx: ProcessorContext) -> ProcessorResult:
        if ctx.metadata is None:
            return ProcessorResult(source=source)

        imported_names = ctx.metadata.imported_names()
        if not imported_names:
            return ProcessorResult(source=source)

        scanner = Scanner(source)
        tokens = scanner.scan()
        result: list[str] = []
        i = 0

        while i < len(tokens):
            token = tokens[i]

            # Self-closing component: <Card title="x" />
            if token.type == ScanTokenType.SELF_CLOSING_TAG and token.tag_name in imported_names:
                result.append(self._compile_component(token, None, ctx, imported_names))
                i += 1
                continue

            # Open component: <Card title="x"> ... </Card>
            if token.type == ScanTokenType.OPEN_TAG and token.tag_name in imported_names:
                children_tokens, end_idx = self._collect_children(tokens, i, token.tag_name)
                children_source = "".join(t.value for t in children_tokens)
                # Strip <Slot> wrappers from children
                children_source = self._strip_slots(children_source)
                # Recursively process nested components in children
                nested = self.process(children_source, ctx)
                children_source = nested.source
                result.append(self._compile_component(token, children_source, ctx, imported_names))
                i = end_idx + 1  # skip past </Component>
                continue

            # Skip stray </Component> (shouldn't happen but be safe)
            if token.type == ScanTokenType.CLOSE_TAG and token.tag_name in imported_names:
                i += 1
                continue

            result.append(token.value)
            i += 1

        return ProcessorResult(source="".join(result))

    def _collect_children(
        self,
        tokens: list[ScanToken],
        start_idx: int,
        tag_name: str,
    ) -> tuple[list[ScanToken], int]:
        """Collect all tokens between <Component> and </Component>, handling nesting."""
        children: list[ScanToken] = []
        depth = 1
        i = start_idx + 1

        while i < len(tokens):
            token = tokens[i]
            if token.type == ScanTokenType.OPEN_TAG and token.tag_name == tag_name:
                depth += 1
            elif token.type == ScanTokenType.CLOSE_TAG and token.tag_name == tag_name:
                depth -= 1
                if depth == 0:
                    return children, i
            children.append(token)
            i += 1

        return children, i

    def _compile_component(
        self,
        token: ScanToken,
        children: str | None,
        ctx: ProcessorContext,
        imported_names: set[str],
    ) -> str:
        name = token.tag_name or ""
        assert ctx.metadata is not None
        template_path = ctx.metadata.resolve_import(name, ctx.filename)
        if template_path is None:
            raise PJXError(
                f"Componente '{name}' nao pode ser resolvido",
                SourceLocation(ctx.filename, token.line, token.col),
                code="PJX201",
            )

        props = self._extract_props(token)

        if children and children.strip():
            # Component with children: capture children as `content` variable
            parts: list[str] = []
            parts.append("{% set content %}")
            parts.append(children)
            parts.append("{% endset %}")
            with_pairs = [f"{k}={v}" for k, v in props]
            with_pairs.append("content=content")
            parts.append(f"{{% with {', '.join(with_pairs)} %}}")
            parts.append(f'{{% include "{template_path}" %}}')
            parts.append("{% endwith %}")
            return "".join(parts)
        else:
            # Self-closing or empty component
            with_clause = ", ".join(f"{k}={v}" for k, v in props)
            parts: list[str] = []
            if with_clause:
                parts.append(f"{{% with {with_clause} %}}")
            parts.append(f'{{% include "{template_path}" %}}')
            if with_clause:
                parts.append("{% endwith %}")
            return "".join(parts)

    def _strip_slots(self, source: str) -> str:
        """Remove <Slot> and </Slot> wrapper tags from children content."""
        result = re.sub(r"<Slot\s+[^>]*>", "", source)
        result = re.sub(r"<Slot\s*/>", "", result)
        result = result.replace("</Slot>", "")
        return result

    def _extract_props(self, token: ScanToken) -> list[tuple[str, str]]:
        props: list[tuple[str, str]] = []
        for attr in token.attributes:
            if attr.value is None:
                props.append((attr.name, "true"))
            elif attr.is_expression:
                props.append((attr.name, attr.value))
            else:
                props.append((attr.name, f'"{attr.value}"'))
        return props
