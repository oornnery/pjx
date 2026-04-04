from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# --- Source Location ---


@dataclass(frozen=True, slots=True)
class SourceLocation:
    file: str | None
    line: int
    col: int


# --- Diagnostics ---


class DiagnosticLevel(Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    level: DiagnosticLevel
    code: str
    message: str
    loc: SourceLocation
    hint: str | None = None


class PJXError(Exception):
    def __init__(
        self,
        message: str,
        loc: SourceLocation,
        *,
        code: str = "PJX000",
        hint: str | None = None,
    ):
        self.diagnostic = Diagnostic(
            level=DiagnosticLevel.ERROR,
            code=code,
            message=message,
            loc=loc,
            hint=hint,
        )
        super().__init__(self.format())

    def format(self) -> str:
        d = self.diagnostic
        loc = f"{d.loc.file or '<unknown>'}:{d.loc.line}:{d.loc.col}"
        msg = f"{d.level.value}[{d.code}]: {d.message}\n  --> {loc}"
        if d.hint:
            msg += f"\n  = dica: {d.hint}"
        return msg


# --- Source Map ---


@dataclass(frozen=True, slots=True)
class SourceMapEntry:
    output_line: int
    source_line: int
    source_file: str | None = None


@dataclass
class SourceMap:
    entries: list[SourceMapEntry] = field(default_factory=list)

    def add(
        self, output_line: int, source_line: int, source_file: str | None = None
    ) -> None:
        self.entries.append(SourceMapEntry(output_line, source_line, source_file))

    def lookup(self, output_line: int) -> SourceMapEntry | None:
        for entry in reversed(self.entries):
            if entry.output_line <= output_line:
                return entry
        return self.entries[0] if self.entries else None

    @staticmethod
    def identity(line_count: int, source_file: str | None = None) -> SourceMap:
        sm = SourceMap()
        for i in range(1, line_count + 1):
            sm.add(i, i, source_file)
        return sm


# --- Render Errors ---


class PJXRenderError(Exception):
    def __init__(
        self,
        *,
        template: str | None,
        phase: str,
        cause: Exception,
        source_line: int | None = None,
    ):
        self.template = template
        self.phase = phase
        self.cause = cause
        self.source_line = source_line
        super().__init__(str(self))

    def __str__(self) -> str:
        parts = [f"PJXRenderError ({self.phase})"]
        if self.template:
            parts.append(f"  template: {self.template}")
        if self.source_line and self.template:
            parts.append(f"  source: {self.template}:{self.source_line}")
        parts.append(f"  cause: {self.cause}")
        return "\n".join(parts)


def translate_jinja_error(
    error: Exception, source_map: SourceMap | None, filename: str | None = None
) -> PJXRenderError:
    jinja_line = getattr(error, "lineno", None)
    if jinja_line and source_map:
        entry = source_map.lookup(jinja_line)
        if entry:
            return PJXRenderError(
                template=entry.source_file or filename,
                phase="render",
                cause=error,
                source_line=entry.source_line,
            )
    return PJXRenderError(template=filename, phase="render", cause=error)
