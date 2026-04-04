from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class ScanTokenType(Enum):
    OPEN_TAG = auto()
    CLOSE_TAG = auto()
    SELF_CLOSING_TAG = auto()
    TEXT = auto()
    COMMENT = auto()


@dataclass(slots=True)
class TagAttribute:
    name: str
    namespace: str | None
    value: str | None
    is_expression: bool
    loc_line: int
    loc_col: int


@dataclass(slots=True)
class ScanToken:
    type: ScanTokenType
    value: str
    tag_name: str | None = None
    attributes: list[TagAttribute] = field(default_factory=list)
    line: int = 1
    col: int = 1


class Scanner:
    def __init__(self, source: str):
        self._source = source
        self._pos = 0
        self._line = 1
        self._col = 1

    def scan(self) -> list[ScanToken]:
        tokens: list[ScanToken] = []
        while self._pos < len(self._source):
            if self._source[self._pos : self._pos + 4] == "<!--":
                tokens.append(self._scan_comment())
            elif self._source[self._pos : self._pos + 2] == "</":
                tokens.append(self._scan_close_tag())
            elif self._source[self._pos] == "<" and self._peek_tag_start():
                tokens.append(self._scan_open_tag())
            else:
                tokens.append(self._scan_text())
        return tokens

    def _peek_tag_start(self) -> bool:
        if self._pos + 1 >= len(self._source):
            return False
        ch = self._source[self._pos + 1]
        return ch.isalpha() or ch == "_"

    def _scan_comment(self) -> ScanToken:
        line, col = self._line, self._col
        start = self._pos
        end = self._source.find("-->", self._pos + 4)
        if end == -1:
            end = len(self._source)
        else:
            end += 3
        self._advance_to(end)
        return ScanToken(
            ScanTokenType.COMMENT, self._source[start:end], line=line, col=col
        )

    def _scan_close_tag(self) -> ScanToken:
        line, col = self._line, self._col
        start = self._pos
        self._advance(2)  # </
        self._skip_whitespace()
        tag_name = self._read_ident()
        self._skip_whitespace()
        if self._pos < len(self._source) and self._source[self._pos] == ">":
            self._advance(1)
        return ScanToken(
            ScanTokenType.CLOSE_TAG,
            self._source[start : self._pos],
            tag_name=tag_name,
            line=line,
            col=col,
        )

    def _scan_open_tag(self) -> ScanToken:
        line, col = self._line, self._col
        start = self._pos
        self._advance(1)  # <
        tag_name = self._read_ident()
        attrs = self._scan_attributes()
        self._skip_whitespace()
        self_closing = False
        if self._pos < len(self._source) and self._source[self._pos] == "/":
            self_closing = True
            self._advance(1)
        if self._pos < len(self._source) and self._source[self._pos] == ">":
            self._advance(1)
        token_type = (
            ScanTokenType.SELF_CLOSING_TAG if self_closing else ScanTokenType.OPEN_TAG
        )
        return ScanToken(
            token_type,
            self._source[start : self._pos],
            tag_name=tag_name,
            attributes=attrs,
            line=line,
            col=col,
        )

    def _scan_attributes(self) -> list[TagAttribute]:
        attrs: list[TagAttribute] = []
        while self._pos < len(self._source):
            self._skip_whitespace()
            if self._pos >= len(self._source):
                break
            ch = self._source[self._pos]
            if ch in (">", "/"):
                break
            if not (ch.isalpha() or ch == "_" or ch == "@"):
                break
            attrs.append(self._scan_one_attribute())
        return attrs

    def _scan_one_attribute(self) -> TagAttribute:
        line, col = self._line, self._col
        name = self._read_attr_name()
        namespace = None
        if ":" in name:
            parts = name.split(":", 1)
            namespace = parts[0]
            name_full = name
        else:
            name_full = name

        self._skip_whitespace()
        if self._pos < len(self._source) and self._source[self._pos] == "=":
            self._advance(1)
            self._skip_whitespace()
            value, is_expr = self._read_attr_value()
            return TagAttribute(name_full, namespace, value, is_expr, line, col)
        return TagAttribute(name_full, namespace, None, False, line, col)

    def _read_attr_value(self) -> tuple[str, bool]:
        if self._pos >= len(self._source):
            return ("", False)
        ch = self._source[self._pos]
        if ch == "{":
            return self._read_expression_value()
        if ch in ('"', "'"):
            return self._read_quoted_value(ch)
        return self._read_unquoted_value()

    def _read_expression_value(self) -> tuple[str, bool]:
        self._advance(1)  # {
        depth = 1
        start = self._pos
        while self._pos < len(self._source) and depth > 0:
            ch = self._source[self._pos]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            elif ch in ('"', "'"):
                self._skip_string(ch)
                continue
            self._advance(1)
        value = self._source[start : self._pos]
        if self._pos < len(self._source):
            self._advance(1)  # }
        return (value, True)

    def _read_quoted_value(self, quote: str) -> tuple[str, bool]:
        self._advance(1)
        start = self._pos
        while self._pos < len(self._source) and self._source[self._pos] != quote:
            self._advance(1)
        value = self._source[start : self._pos]
        if self._pos < len(self._source):
            self._advance(1)
        return (value, False)

    def _read_unquoted_value(self) -> tuple[str, bool]:
        start = self._pos
        while self._pos < len(self._source) and self._source[self._pos] not in (
            " ",
            "\t",
            "\n",
            ">",
            "/",
        ):
            self._advance(1)
        return (self._source[start : self._pos], False)

    def _read_ident(self) -> str:
        start = self._pos
        while self._pos < len(self._source):
            ch = self._source[self._pos]
            if ch.isalnum() or ch in ("_", "-", "."):
                self._advance(1)
            else:
                break
        return self._source[start : self._pos]

    def _read_attr_name(self) -> str:
        start = self._pos
        while self._pos < len(self._source):
            ch = self._source[self._pos]
            if ch.isalnum() or ch in ("_", "-", ":", ".", "@"):
                self._advance(1)
            else:
                break
        return self._source[start : self._pos]

    def _skip_string(self, quote: str) -> None:
        self._advance(1)
        while self._pos < len(self._source) and self._source[self._pos] != quote:
            if self._source[self._pos] == "\\":
                self._advance(1)
            self._advance(1)
        if self._pos < len(self._source):
            self._advance(1)

    def _skip_whitespace(self) -> None:
        while self._pos < len(self._source) and self._source[self._pos] in (
            " ",
            "\t",
            "\n",
            "\r",
        ):
            self._advance(1)

    def _scan_text(self) -> ScanToken:
        line, col = self._line, self._col
        start = self._pos
        while self._pos < len(self._source):
            if self._source[self._pos : self._pos + 4] == "<!--":
                break
            if self._source[self._pos : self._pos + 2] == "</":
                break
            if self._source[self._pos] == "<" and self._peek_tag_start():
                break
            self._advance(1)
        return ScanToken(
            ScanTokenType.TEXT, self._source[start : self._pos], line=line, col=col
        )

    def _advance(self, count: int = 1) -> None:
        for _ in range(count):
            if self._pos < len(self._source):
                if self._source[self._pos] == "\n":
                    self._line += 1
                    self._col = 1
                else:
                    self._col += 1
                self._pos += 1

    def _advance_to(self, pos: int) -> None:
        while self._pos < pos:
            self._advance(1)
