from __future__ import annotations


from pjx.core.pipeline import ProcessorContext, ProcessorResult
from pjx.core.scanner import Scanner, ScanTokenType, TagAttribute
from pjx.errors import PJXError, SourceLocation


class AliasProcessor:
    def process(self, source: str, ctx: ProcessorContext) -> ProcessorResult:
        scanner = Scanner(source)
        tokens = scanner.scan()
        result: list[str] = []
        controller_stack: list[tuple[list[str], str]] = []  # (controllers, tag_name)

        for token in tokens:
            if token.type in (ScanTokenType.TEXT, ScanTokenType.COMMENT):
                result.append(token.value)
                continue

            if token.type == ScanTokenType.CLOSE_TAG:
                tag_name = token.tag_name or ""
                if controller_stack and controller_stack[-1][1] == tag_name:
                    controller_stack.pop()
                result.append(token.value)
                continue

            if token.type not in (
                ScanTokenType.OPEN_TAG,
                ScanTokenType.SELF_CLOSING_TAG,
            ):
                result.append(token.value)
                continue

            tag_name = token.tag_name or ""
            new_attrs: list[str] = []
            entered_scope = False
            current_controllers: list[str] = []

            for attr in token.attributes:
                if attr.name == "stimulus:controller" and attr.value is not None:
                    controllers = [c for c in attr.value.split() if c]
                    if not controllers:
                        raise PJXError(
                            "stimulus:controller vazio",
                            SourceLocation(ctx.filename, attr.loc_line, attr.loc_col),
                            code="PJX401",
                        )
                    current_controllers = controllers
                    entered_scope = True
                    new_attrs.append(
                        self._format_attr(
                            "data-controller", attr.value, attr.is_expression
                        )
                    )
                    continue

                if attr.name == "stimulus:action":
                    new_attrs.append(
                        self._format_attr("data-action", attr.value, attr.is_expression)
                    )
                    continue

                if attr.namespace == "stimulus" and self._is_controller_dependent(
                    attr.name
                ):
                    ctrl = self._resolve_controller(
                        attr.name,
                        controller_stack,
                        current_controllers,
                        ctx.filename,
                        attr.loc_line,
                        attr.loc_col,
                    )
                    html_attr = self._build_stimulus_attr(attr.name, ctrl)
                    new_attrs.append(
                        self._format_attr(html_attr, attr.value, attr.is_expression)
                    )
                    continue

                if attr.namespace == "htmx":
                    attr_name = attr.name.split(":", 1)[1]
                    new_attrs.append(
                        self._format_attr(
                            f"hx-{attr_name}", attr.value, attr.is_expression
                        )
                    )
                    continue

                if attr.namespace == "sse":
                    attr_name = attr.name.split(":", 1)[1]
                    new_attrs.append(
                        self._format_attr(
                            f"sse-{attr_name}", attr.value, attr.is_expression
                        )
                    )
                    continue

                new_attrs.append(self._format_original_attr(attr))

            if entered_scope and token.type == ScanTokenType.OPEN_TAG:
                controller_stack.append((current_controllers, tag_name))
            elif entered_scope and token.type == ScanTokenType.SELF_CLOSING_TAG:
                pass  # self-closing, no push

            result.append(
                self._rebuild_tag(
                    tag_name, new_attrs, token.type == ScanTokenType.SELF_CLOSING_TAG
                )
            )

        return ProcessorResult(source="".join(result))

    def _is_controller_dependent(self, attr_name: str) -> bool:
        base = attr_name.split(".", 1)[0] if "." in attr_name else attr_name
        return (
            base == "stimulus:target"
            or base.startswith("stimulus:value-")
            or base.startswith("stimulus:class-")
            or base.startswith("stimulus:outlet-")
        )

    def _resolve_controller(
        self,
        attr_name: str,
        controller_stack: list[tuple[list[str], str]],
        current_controllers: list[str],
        filename: str | None,
        line: int,
        col: int,
    ) -> str:
        base_attr, explicit_ctrl = self._split_stimulus_alias(attr_name)

        all_scopes = [s[0] for s in controller_stack]
        if current_controllers:
            all_scopes.append(current_controllers)

        if explicit_ctrl is not None:
            for scope in reversed(all_scopes):
                if explicit_ctrl in scope:
                    return explicit_ctrl
            raise PJXError(
                f"controller '{explicit_ctrl}' nao esta ativo para {attr_name}",
                SourceLocation(filename, line, col),
                code="PJX402",
            )

        if not all_scopes:
            raise PJXError(
                f"{attr_name} fora de stimulus:controller",
                SourceLocation(filename, line, col),
                code="PJX403",
            )

        active_scope = all_scopes[-1]
        if len(active_scope) != 1:
            names = " ".join(active_scope)
            raise PJXError(
                f"{attr_name} e ambiguo com multiplos controllers ativos: {names}",
                SourceLocation(filename, line, col),
                code="PJX404",
                hint=f"use {attr_name}.{active_scope[0]}=...",
            )
        return active_scope[0]

    def _split_stimulus_alias(self, attr_name: str) -> tuple[str, str | None]:
        if "." not in attr_name:
            return attr_name, None
        base_attr, explicit_ctrl = attr_name.rsplit(".", 1)
        if (
            base_attr == "stimulus:target"
            or base_attr.startswith("stimulus:value-")
            or base_attr.startswith("stimulus:class-")
            or base_attr.startswith("stimulus:outlet-")
        ):
            return base_attr, explicit_ctrl
        return attr_name, None

    def _build_stimulus_attr(self, attr_name: str, ctrl: str) -> str:
        base, _ = self._split_stimulus_alias(attr_name)
        if base == "stimulus:target":
            return f"data-{ctrl}-target"
        for prefix, suffix in [
            ("stimulus:value-", "-value"),
            ("stimulus:class-", "-class"),
            ("stimulus:outlet-", "-outlet"),
        ]:
            if base.startswith(prefix):
                key = base[len(prefix) :]
                return f"data-{ctrl}-{key}{suffix}"
        return f"data-{ctrl}-target"

    def _format_attr(self, name: str, value: str | None, is_expression: bool) -> str:
        if value is None:
            return name
        if is_expression:
            return f'{name}="{{{{ {value} }}}}"'
        return f'{name}="{value}"'

    def _format_original_attr(self, attr: TagAttribute) -> str:
        if attr.value is None:
            return attr.name
        if attr.is_expression:
            return f"{attr.name}={{{attr.value}}}"
        return f'{attr.name}="{attr.value}"'

    def _rebuild_tag(self, tag_name: str, attrs: list[str], self_closing: bool) -> str:
        attr_str = ""
        if attrs:
            attr_str = " " + " ".join(attrs)
        if self_closing:
            return f"<{tag_name}{attr_str} />"
        return f"<{tag_name}{attr_str}>"
