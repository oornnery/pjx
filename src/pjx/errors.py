"""PJX exception hierarchy with source location support."""

from __future__ import annotations

from pathlib import Path


class PJXError(Exception):
    """Base exception for all PJX errors.

    Args:
        message: Human-readable error description.
        path: Source file where the error occurred.
        line: 1-based line number.
        col: 1-based column number.
    """

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        line: int | None = None,
        col: int | None = None,
    ) -> None:
        self.path = path
        self.line = line
        self.col = col
        super().__init__(self._format(message))

    def _format(self, message: str) -> str:
        parts: list[str] = []
        if self.path is not None:
            parts.append(str(self.path))
        if self.line is not None:
            parts.append(str(self.line))
            if self.col is not None:
                parts.append(str(self.col))
        if parts:
            return f"{':'.join(parts)}: {message}"
        return message


class ParseError(PJXError):
    """Syntax error while parsing a ``.jinja`` component."""


class LexError(ParseError):
    """Error during frontmatter tokenization."""


class CompileError(PJXError):
    """Error while compiling an AST to output."""


class PropValidationError(PJXError):
    """Props failed Pydantic validation."""


class ImportResolutionError(PJXError):
    """An import could not be resolved."""


class RenderError(PJXError):
    """Error while rendering a compiled template."""


class ConfigError(PJXError):
    """Invalid PJX configuration."""
