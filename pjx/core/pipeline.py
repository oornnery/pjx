from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from pjx.errors import Diagnostic
from pjx.models import TemplateMetadata


@dataclass
class ProcessorContext:
    filename: str | None = None
    metadata: TemplateMetadata | None = None


@dataclass
class ProcessorResult:
    source: str
    diagnostics: list[Diagnostic] = field(default_factory=list)
    metadata: TemplateMetadata | None = None


@dataclass
class PreprocessResult:
    source: str
    metadata: TemplateMetadata | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)


class Processor(Protocol):
    def process(self, source: str, ctx: ProcessorContext) -> ProcessorResult: ...


class PreprocessorPipeline:
    def __init__(self) -> None:
        from pjx.core.aliases import AliasProcessor
        from pjx.core.components import ComponentProcessor
        from pjx.core.expressions import ExpressionProcessor
        from pjx.core.flow import ControlFlowProcessor
        from pjx.core.frontmatter import FrontmatterProcessor

        self.processors: list[Processor] = [
            FrontmatterProcessor(),
            ComponentProcessor(),
            ControlFlowProcessor(),
            AliasProcessor(),
            ExpressionProcessor(),
        ]

    def process(self, source: str, filename: str | None = None) -> PreprocessResult:
        metadata = None
        diagnostics: list[Diagnostic] = []
        ctx = ProcessorContext(filename=filename)

        for processor in self.processors:
            result = processor.process(source, ctx)
            source = result.source
            diagnostics.extend(result.diagnostics)
            if result.metadata is not None:
                metadata = result.metadata
                ctx.metadata = result.metadata

        return PreprocessResult(
            source=source,
            metadata=metadata,
            diagnostics=diagnostics,
        )
