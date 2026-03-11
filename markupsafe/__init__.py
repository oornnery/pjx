from __future__ import annotations

import html
from string import Formatter
from typing import Any


class Markup(str):
    def __new__(cls, object: Any = "") -> "Markup":
        if hasattr(object, "__html__"):
            object = object.__html__()
        return super().__new__(cls, str(object))

    def __html__(self) -> "Markup":
        return self

    def __html_format__(self, format_spec: str) -> "Markup":
        if format_spec:
            raise ValueError("Unsupported format specification for Markup")
        return self

    def __add__(self, value: Any) -> "Markup":
        return Markup(super().__add__(str(escape(value))))

    def __radd__(self, value: Any) -> "Markup":
        return Markup(str(escape(value)) + self)

    def join(self, seq: Any) -> "Markup":
        return Markup(super().join(str(escape(item)) for item in seq))

    def format(self, *args: Any, **kwargs: Any) -> "Markup":
        formatter = EscapeFormatter()
        return Markup(formatter.vformat(self, args, kwargs))

    def unescape(self) -> str:
        return html.unescape(self)

    def striptags(self) -> str:
        return html.unescape(" ".join(self.replace(">", "> ").split("<")[0::2]))


class EscapeFormatter(Formatter):
    def format_field(self, value: Any, format_spec: str) -> str:
        if hasattr(value, "__html_format__"):
            return str(value.__html_format__(format_spec))
        if hasattr(value, "__html__"):
            return str(value.__html__())
        return super().format_field(escape(value), format_spec)


def escape(value: Any) -> Markup:
    if value is None:
        return Markup("")
    if hasattr(value, "__html__"):
        return Markup(value.__html__())
    return Markup(html.escape(str(value), quote=True))


def escape_silent(value: Any) -> Markup:
    if value is None:
        return Markup("")
    return escape(value)


def soft_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


t = None
cabc = None
string = None
annotations = None
