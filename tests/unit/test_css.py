"""Tests for pjx.css — scoped CSS hash generation and selector prefixing."""

from pathlib import Path

from pjx.css import generate_scope_hash, scope_css


class TestGenerateScopeHash:
    def test_deterministic(self) -> None:
        h1 = generate_scope_hash(Path("Button.jinja"))
        h2 = generate_scope_hash(Path("Button.jinja"))
        assert h1 == h2

    def test_length(self) -> None:
        h = generate_scope_hash(Path("Button.jinja"))
        assert len(h) == 7

    def test_unique_per_path(self) -> None:
        h1 = generate_scope_hash(Path("Button.jinja"))
        h2 = generate_scope_hash(Path("Card.jinja"))
        assert h1 != h2

    def test_hex_string(self) -> None:
        h = generate_scope_hash(Path("X.jinja"))
        assert all(c in "0123456789abcdef" for c in h)


class TestScopeCSS:
    def test_class_selector(self) -> None:
        result = scope_css(".card { color: red; }", "a1b2c3d")
        assert ".card[data-pjx-a1b2c3d]" in result
        assert "color: red;" in result

    def test_id_selector(self) -> None:
        result = scope_css("#main { padding: 0; }", "a1b2c3d")
        assert "#main[data-pjx-a1b2c3d]" in result

    def test_compound_selector(self) -> None:
        result = scope_css("div.card { margin: 0; }", "a1b2c3d")
        assert "div.card[data-pjx-a1b2c3d]" in result

    def test_multiple_selectors(self) -> None:
        result = scope_css(".a, .b { color: blue; }", "a1b2c3d")
        assert ".a[data-pjx-a1b2c3d]" in result
        assert ".b[data-pjx-a1b2c3d]" in result

    def test_descendant_selector(self) -> None:
        result = scope_css(".a .b { color: green; }", "a1b2c3d")
        assert ".a[data-pjx-a1b2c3d] .b[data-pjx-a1b2c3d]" in result

    def test_media_query(self) -> None:
        result = scope_css(
            "@media (max-width: 768px) { .card { display: none; } }", "a1b2c3d"
        )
        assert "@media" in result
        assert ".card[data-pjx-a1b2c3d]" in result

    def test_preserves_properties(self) -> None:
        css = ".card { color: red; font-size: 14px; }"
        result = scope_css(css, "a1b2c3d")
        assert "color: red;" in result
        assert "font-size: 14px;" in result

    def test_multiple_rules(self) -> None:
        css = ".a { color: red; }\n.b { color: blue; }"
        result = scope_css(css, "hash123")
        assert ".a[data-pjx-hash123]" in result
        assert ".b[data-pjx-hash123]" in result

    def test_empty_css(self) -> None:
        result = scope_css("", "abc")
        assert result == ""
