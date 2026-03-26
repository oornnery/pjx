"""Tests for pjx.lexer — frontmatter tokenizer."""

import pytest

from pjx.errors import LexError
from pjx.lexer import Token, TokenKind, tokenize


def _kinds(tokens: list[Token]) -> list[TokenKind]:
    """Extract just the token kinds (drop trailing EOF)."""
    return [t.kind for t in tokens if t.kind not in (TokenKind.NEWLINE, TokenKind.EOF)]


def _values(tokens: list[Token]) -> list[str]:
    return [t.value for t in tokens if t.kind not in (TokenKind.NEWLINE, TokenKind.EOF)]


class TestKeywords:
    def test_tokenize_extends(self) -> None:
        toks = tokenize('extends "layouts/Base.jinja"')
        assert _kinds(toks) == [TokenKind.EXTENDS, TokenKind.STRING]
        assert _values(toks) == ["extends", "layouts/Base.jinja"]

    def test_tokenize_from_import(self) -> None:
        toks = tokenize("from pydantic import EmailStr, HttpUrl")
        assert _kinds(toks) == [
            TokenKind.FROM,
            TokenKind.IDENT,
            TokenKind.IMPORT,
            TokenKind.IDENT,
            TokenKind.COMMA,
            TokenKind.IDENT,
        ]

    def test_tokenize_import_default(self) -> None:
        toks = tokenize('import Button from "./Button.jinja"')
        assert _kinds(toks) == [
            TokenKind.IMPORT,
            TokenKind.IDENT,
            TokenKind.FROM,
            TokenKind.STRING,
        ]

    def test_tokenize_import_named(self) -> None:
        toks = tokenize('import { CardHeader, CardBody } from "./Card.jinja"')
        kinds = _kinds(toks)
        assert kinds[:5] == [
            TokenKind.IMPORT,
            TokenKind.LBRACE,
            TokenKind.IDENT,
            TokenKind.COMMA,
            TokenKind.IDENT,
        ]

    def test_tokenize_import_wildcard(self) -> None:
        toks = tokenize('import * from "./ui/"')
        assert _kinds(toks) == [
            TokenKind.IMPORT,
            TokenKind.STAR,
            TokenKind.FROM,
            TokenKind.STRING,
        ]

    def test_tokenize_import_alias(self) -> None:
        toks = tokenize('import Button from "./Button.jinja" as Btn')
        assert TokenKind.AS in _kinds(toks)
        assert "Btn" in _values(toks)


class TestProps:
    def test_tokenize_props_simple(self) -> None:
        src = "props UserProps = {\n  name: str,\n  age: int = 0,\n}"
        toks = tokenize(src)
        kinds = _kinds(toks)
        assert kinds[0] == TokenKind.PROPS
        assert TokenKind.LBRACE in kinds
        assert TokenKind.RBRACE in kinds
        assert TokenKind.COLON in kinds
        assert TokenKind.EQUALS in kinds

    def test_tokenize_props_pydantic_types(self) -> None:
        src = 'props P = {\n  role: Literal["admin", "user"] = "user",\n}'
        toks = tokenize(src)
        vals = _values(toks)
        assert "Literal" in vals
        assert "admin" in vals
        assert "user" in vals


class TestDeclarations:
    def test_tokenize_slot(self) -> None:
        toks = tokenize("slot actions")
        assert _kinds(toks) == [TokenKind.SLOT, TokenKind.IDENT]

    def test_tokenize_store(self) -> None:
        src = "store theme = { dark: false }"
        toks = tokenize(src)
        kinds = _kinds(toks)
        assert kinds[0] == TokenKind.STORE
        assert TokenKind.LBRACE in kinds

    def test_tokenize_let_const_state_computed(self) -> None:
        lines = [
            'let css_class = "todo"',
            "const MAX = 140",
            "state count = 0",
            "computed doubled = count * 2",
        ]
        for line_src in lines:
            toks = tokenize(line_src)
            first = _kinds(toks)[0]
            assert first in (
                TokenKind.LET,
                TokenKind.CONST,
                TokenKind.STATE,
                TokenKind.COMPUTED,
            )


class TestLiterals:
    def test_tokenize_string_double_quotes(self) -> None:
        toks = tokenize('"hello world"')
        assert _values(toks) == ["hello world"]
        assert _kinds(toks) == [TokenKind.STRING]

    def test_tokenize_string_single_quotes(self) -> None:
        toks = tokenize("'hello'")
        assert _values(toks) == ["hello"]

    def test_tokenize_string_escapes(self) -> None:
        toks = tokenize(r'"line\nbreak"')
        assert _values(toks) == ["line\nbreak"]

    def test_tokenize_integer(self) -> None:
        toks = tokenize("42")
        assert _kinds(toks) == [TokenKind.NUMBER]
        assert _values(toks) == ["42"]

    def test_tokenize_float(self) -> None:
        toks = tokenize("3.14")
        assert _values(toks) == ["3.14"]

    def test_tokenize_negative_number(self) -> None:
        toks = tokenize("-5")
        assert _kinds(toks) == [TokenKind.NUMBER]
        assert _values(toks) == ["-5"]


class TestPunctuation:
    def test_tokenize_ellipsis(self) -> None:
        toks = tokenize("...my_props")
        assert _kinds(toks) == [TokenKind.ELLIPSIS, TokenKind.IDENT]

    def test_tokenize_pipe(self) -> None:
        toks = tokenize("str | None")
        assert _kinds(toks) == [TokenKind.IDENT, TokenKind.PIPE, TokenKind.IDENT]

    def test_tokenize_brackets(self) -> None:
        toks = tokenize("list[str]")
        assert _kinds(toks) == [
            TokenKind.IDENT,
            TokenKind.LBRACKET,
            TokenKind.IDENT,
            TokenKind.RBRACKET,
        ]

    def test_tokenize_dot(self) -> None:
        toks = tokenize("a.b")
        assert _kinds(toks) == [TokenKind.IDENT, TokenKind.DOT, TokenKind.IDENT]


class TestComments:
    def test_tokenize_comments_ignored(self) -> None:
        src = "# this is a comment\nslot actions"
        toks = tokenize(src)
        kinds = _kinds(toks)
        assert kinds == [TokenKind.SLOT, TokenKind.IDENT]

    def test_inline_comment(self) -> None:
        src = "state count = 0 # initial value"
        toks = tokenize(src)
        # Comment words should not appear as tokens
        assert TokenKind.IDENT not in [
            t.kind for t in toks if t.value in ("this", "initial", "value")
        ]


class TestLocations:
    def test_line_tracking(self) -> None:
        src = "let a = 1\nlet b = 2"
        toks = tokenize(src)
        first_let = toks[0]
        # Find second LET
        second_let = [t for t in toks if t.kind == TokenKind.LET][1]
        assert first_let.line == 1
        assert second_let.line == 2

    def test_col_tracking(self) -> None:
        toks = tokenize("slot actions")
        assert toks[0].col == 1  # 'slot'
        assert toks[1].col == 6  # 'actions'


class TestErrors:
    def test_unterminated_string(self) -> None:
        with pytest.raises(LexError, match="unterminated string"):
            tokenize('"hello')

    def test_unterminated_string_newline(self) -> None:
        with pytest.raises(LexError, match="unterminated string"):
            tokenize('"hello\n')

    def test_invalid_char(self) -> None:
        with pytest.raises(LexError, match="unexpected character"):
            tokenize("@invalid")

    def test_error_has_location(self) -> None:
        with pytest.raises(LexError) as exc_info:
            tokenize("  @")
        assert exc_info.value.line == 1
        assert exc_info.value.col == 3


class TestEOF:
    def test_empty_source(self) -> None:
        toks = tokenize("")
        assert len(toks) == 1
        assert toks[0].kind == TokenKind.EOF

    def test_always_ends_with_eof(self) -> None:
        toks = tokenize("slot x")
        assert toks[-1].kind == TokenKind.EOF
