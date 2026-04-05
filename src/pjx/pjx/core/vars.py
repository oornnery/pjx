from __future__ import annotations

from pjx.core.types import ProcessorContext, ProcessorResult


class VarsProcessor:
    def process(self, source: str, ctx: ProcessorContext) -> ProcessorResult:
        if ctx.metadata is None:
            return ProcessorResult(source=source)

        lines: list[str] = []

        for var in ctx.metadata.vars:
            if isinstance(var.value, dict):
                pairs = ", ".join(f'"{k}": "{v}"' for k, v in var.value.items())
                lines.append(f"{{% set {var.name} = {{{pairs}}} %}}")
            else:
                lines.append(f'{{% set {var.name} = "{var.value}" %}}')

        for comp in ctx.metadata.computed:
            lines.append(f"{{% set {comp.name} = {comp.expression} %}}")

        if not lines:
            return ProcessorResult(source=source)

        prefix = "\n".join(lines) + "\n"
        return ProcessorResult(source=prefix + source)
