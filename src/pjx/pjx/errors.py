from __future__ import annotations

from dataclasses import dataclass
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
