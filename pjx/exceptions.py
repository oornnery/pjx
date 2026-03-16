"""PJX exception hierarchy."""

from __future__ import annotations


class PjxError(Exception):
    """Base for all PJX errors."""

    def __init__(
        self,
        message: str,
        *,
        file: str | None = None,
        line: int | None = None,
    ) -> None:
        self.file = file
        self.line = line
        location = ""
        if file:
            location += f" in {file}"
        if line is not None:
            location += f" at line {line}"
        super().__init__(f"{message}{location}")


class ParseError(PjxError):
    """Raised when a .pjx file cannot be parsed."""


class CompileError(PjxError):
    """Raised when an AST cannot be compiled to Jinja2."""


class ComponentError(PjxError):
    """Raised for component lifecycle errors (missing props, bad bindings)."""


class ResolutionError(PjxError):
    """Raised when a component tag cannot be resolved to a template."""


class PropValidationError(PjxError):
    """Raised when a prop value fails type validation."""
