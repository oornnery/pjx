"""Tests for pjx.cli.analyze — route and bundle analysis."""

from pjx.cli.analyze import _fmt_size


class TestFmtSize:
    def test_zero(self) -> None:
        assert _fmt_size(0) == "0 B"

    def test_bytes(self) -> None:
        assert _fmt_size(512) == "512 B"

    def test_kilobytes(self) -> None:
        assert _fmt_size(2048) == "2.0 KB"

    def test_megabytes(self) -> None:
        assert _fmt_size(1048576) == "1.0 MB"

    def test_fractional_kb(self) -> None:
        assert _fmt_size(1536) == "1.5 KB"
