"""Tests for pjx.errors exception hierarchy."""

from pathlib import Path

import pytest

from pjx.errors import (
    CompileError,
    ConfigError,
    ImportResolutionError,
    LexError,
    PJXError,
    ParseError,
    PropValidationError,
)


class TestPJXError:
    def test_message_only(self) -> None:
        err = PJXError("something broke")
        assert str(err) == "something broke"
        assert err.path is None
        assert err.line is None
        assert err.col is None

    def test_with_path(self) -> None:
        p = Path("components/Button.jinja")
        err = PJXError("bad", path=p)
        assert str(err) == "components/Button.jinja: bad"

    def test_with_path_and_line(self) -> None:
        p = Path("Button.jinja")
        err = PJXError("bad", path=p, line=10)
        assert str(err) == "Button.jinja:10: bad"

    def test_with_full_location(self) -> None:
        p = Path("Button.jinja")
        err = PJXError("bad", path=p, line=10, col=5)
        assert str(err) == "Button.jinja:10:5: bad"

    def test_col_without_line_ignored(self) -> None:
        err = PJXError("bad", col=5)
        assert str(err) == "bad"


class TestHierarchy:
    def test_parse_error_is_pjx_error(self) -> None:
        assert issubclass(ParseError, PJXError)

    def test_lex_error_is_parse_error(self) -> None:
        assert issubclass(LexError, ParseError)

    def test_compile_error_is_pjx_error(self) -> None:
        assert issubclass(CompileError, PJXError)

    def test_prop_validation_error_is_pjx_error(self) -> None:
        assert issubclass(PropValidationError, PJXError)

    def test_import_resolution_error_is_pjx_error(self) -> None:
        assert issubclass(ImportResolutionError, PJXError)

    def test_config_error_is_pjx_error(self) -> None:
        assert issubclass(ConfigError, PJXError)

    @pytest.mark.parametrize(
        "exc_cls",
        [
            ParseError,
            LexError,
            CompileError,
            PropValidationError,
            ImportResolutionError,
            ConfigError,
        ],
    )
    def test_catchable_as_pjx_error(self, exc_cls: type[PJXError]) -> None:
        with pytest.raises(PJXError):
            raise exc_cls("test")

    @pytest.mark.parametrize(
        "exc_cls",
        [
            ParseError,
            LexError,
            CompileError,
            PropValidationError,
            ImportResolutionError,
            ConfigError,
        ],
    )
    def test_location_propagated(self, exc_cls: type[PJXError]) -> None:
        p = Path("test.jinja")
        err = exc_cls("msg", path=p, line=1, col=2)
        assert err.path == p
        assert err.line == 1
        assert err.col == 2
        assert "test.jinja:1:2" in str(err)
