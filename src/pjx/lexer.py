"""Hand-written single-pass lexer for PJX frontmatter.

Produces a flat list of :class:`Token` values that the parser consumes via
recursive descent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pjx.errors import LexError

# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------

_KEYWORDS: dict[str, TokenKind] = {}


class TokenKind(StrEnum):
    """Every token kind the lexer can emit."""

    # Keywords
    EXTENDS = "extends"
    IMPORT = "import"
    FROM = "from"
    AS = "as"
    PROPS = "props"
    SLOT = "slot"
    STORE = "store"
    LET = "let"
    CONST = "const"
    STATE = "state"
    COMPUTED = "computed"

    # Literals / identifiers
    IDENT = "IDENT"
    STRING = "STRING"
    NUMBER = "NUMBER"

    # Punctuation
    LBRACE = "{"
    RBRACE = "}"
    LBRACKET = "["
    RBRACKET = "]"
    LPAREN = "("
    RPAREN = ")"
    COMMA = ","
    COLON = ":"
    EQUALS = "="
    PIPE = "|"
    STAR = "*"
    DOT = "."
    ELLIPSIS = "..."

    # Structural
    NEWLINE = "NEWLINE"
    EOF = "EOF"


# Build keyword lookup after the enum is defined.
_KEYWORDS.update(
    {
        "extends": TokenKind.EXTENDS,
        "import": TokenKind.IMPORT,
        "from": TokenKind.FROM,
        "as": TokenKind.AS,
        "props": TokenKind.PROPS,
        "slot": TokenKind.SLOT,
        "store": TokenKind.STORE,
        "let": TokenKind.LET,
        "const": TokenKind.CONST,
        "state": TokenKind.STATE,
        "computed": TokenKind.COMPUTED,
    }
)


@dataclass(frozen=True, slots=True)
class Token:
    """Single lexer token with source location."""

    kind: TokenKind
    value: str
    line: int
    col: int


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------


def tokenize(source: str) -> list[Token]:
    """Tokenize PJX frontmatter source into a list of tokens.

    Args:
        source: The raw frontmatter text (without ``---`` delimiters).

    Returns:
        Flat list of tokens ending with ``EOF``.

    Raises:
        LexError: On unterminated strings or unexpected characters.
    """
    tokens: list[Token] = []
    pos = 0
    line = 1
    col = 1
    length = len(source)

    while pos < length:
        ch = source[pos]

        # Whitespace (not newline)
        if ch in " \t\r":
            pos += 1
            col += 1
            continue

        # Newline
        if ch == "\n":
            tokens.append(Token(TokenKind.NEWLINE, "\n", line, col))
            pos += 1
            line += 1
            col = 1
            continue

        # Comment — skip to end of line
        if ch == "#":
            while pos < length and source[pos] != "\n":
                pos += 1
            continue

        # Ellipsis (must check before DOT)
        if source[pos : pos + 3] == "...":
            tokens.append(Token(TokenKind.ELLIPSIS, "...", line, col))
            pos += 3
            col += 3
            continue

        # Single-char punctuation
        _SINGLE: dict[str, TokenKind] = {
            "{": TokenKind.LBRACE,
            "}": TokenKind.RBRACE,
            "[": TokenKind.LBRACKET,
            "]": TokenKind.RBRACKET,
            "(": TokenKind.LPAREN,
            ")": TokenKind.RPAREN,
            ",": TokenKind.COMMA,
            ":": TokenKind.COLON,
            "=": TokenKind.EQUALS,
            "|": TokenKind.PIPE,
            "*": TokenKind.STAR,
            ".": TokenKind.DOT,
        }
        if ch in _SINGLE:
            tokens.append(Token(_SINGLE[ch], ch, line, col))
            pos += 1
            col += 1
            continue

        # Strings
        if ch in ('"', "'"):
            start_col = col
            quote = ch
            pos += 1
            col += 1
            buf: list[str] = []
            while pos < length:
                c = source[pos]
                if c == "\n":
                    raise LexError(
                        "unterminated string literal", line=line, col=start_col
                    )
                if c == "\\":
                    pos += 1
                    col += 1
                    if pos >= length:
                        raise LexError(
                            "unterminated string literal", line=line, col=start_col
                        )
                    esc = source[pos]
                    _ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "'": "'"}
                    buf.append(_ESCAPES.get(esc, f"\\{esc}"))
                    pos += 1
                    col += 1
                    continue
                if c == quote:
                    pos += 1
                    col += 1
                    break
                buf.append(c)
                pos += 1
                col += 1
            else:
                raise LexError("unterminated string literal", line=line, col=start_col)
            tokens.append(Token(TokenKind.STRING, "".join(buf), line, start_col))
            continue

        # Numbers
        if ch.isdigit() or (
            ch == "-" and pos + 1 < length and source[pos + 1].isdigit()
        ):
            start_col = col
            start = pos
            if ch == "-":
                pos += 1
                col += 1
            while pos < length and source[pos].isdigit():
                pos += 1
                col += 1
            if pos < length and source[pos] == ".":
                pos += 1
                col += 1
                while pos < length and source[pos].isdigit():
                    pos += 1
                    col += 1
            tokens.append(Token(TokenKind.NUMBER, source[start:pos], line, start_col))
            continue

        # Identifiers / keywords
        if ch.isalpha() or ch == "_":
            start_col = col
            start = pos
            while pos < length and (source[pos].isalnum() or source[pos] == "_"):
                pos += 1
                col += 1
            word = source[start:pos]
            kind = _KEYWORDS.get(word, TokenKind.IDENT)
            tokens.append(Token(kind, word, line, start_col))
            continue

        raise LexError(f"unexpected character {ch!r}", line=line, col=col)

    tokens.append(Token(TokenKind.EOF, "", line, col))
    return tokens
