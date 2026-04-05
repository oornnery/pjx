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
