from __future__ import annotations

from enum import IntEnum
from importlib.metadata import entry_points

from pjx.core.attrs import AttrsProcessor
from pjx.core.components import ComponentProcessor
from pjx.core.expressions import ExpressionProcessor
from pjx.core.flow import ControlFlowProcessor
from pjx.core.frontmatter import FrontmatterProcessor
from pjx.core.types import (
    Diagnostic,
    PreprocessResult,
    Processor,
    ProcessorContext,
)
from pjx.core.vars import VarsProcessor


class ProcessorSlot(IntEnum):
    FRONTMATTER = 10
    VARS = 15
    COMPONENT = 20
    CONTROL_FLOW = 30
    ALIAS = 40
    ATTRS = 45
    EXPRESSION = 50


class PreprocessorPipeline:
    def __init__(self) -> None:
        self._registry: list[tuple[int, Processor]] = []
        self._register(ProcessorSlot.FRONTMATTER, FrontmatterProcessor())
        self._register(ProcessorSlot.VARS, VarsProcessor())
        self._register(ProcessorSlot.COMPONENT, ComponentProcessor())
        self._register(ProcessorSlot.CONTROL_FLOW, ControlFlowProcessor())
        self._register(ProcessorSlot.ATTRS, AttrsProcessor())
        self._register(ProcessorSlot.EXPRESSION, ExpressionProcessor())
        self._discover_extras()

    def _discover_extras(self) -> None:
        eps = entry_points(group="pjx.processors")
        for ep in eps:
            processor_cls = ep.load()
            slot = getattr(processor_cls, "slot", ProcessorSlot.ALIAS)
            self._register(int(slot), processor_cls())

    def _register(self, slot: int, processor: Processor) -> None:
        self._registry.append((slot, processor))
        self._registry.sort(key=lambda x: x[0])

    @property
    def processors(self) -> list[Processor]:
        return [p for _, p in self._registry]

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
