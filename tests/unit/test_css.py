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

    def test_pseudo_class_scoped(self) -> None:
        result = scope_css(".card:hover { color: blue; }", "a1b2c3d")
        assert ".card:hover[data-pjx-a1b2c3d]" in result

    def test_pseudo_element_scoped(self) -> None:
        result = scope_css(".card::before { content: ''; }", "a1b2c3d")
        assert ".card::before[data-pjx-a1b2c3d]" in result

    def test_child_combinator_scoped(self) -> None:
        result = scope_css(".parent > .child { color: red; }", "a1b2c3d")
        assert ".parent[data-pjx-a1b2c3d]" in result
        assert ".child[data-pjx-a1b2c3d]" in result

    def test_keyframes_not_scoped(self) -> None:
        css = "@keyframes fade { from { opacity: 0; } to { opacity: 1; } }"
        result = scope_css(css, "a1b2c3d")
        assert "@keyframes fade" in result
        assert "opacity: 0;" in result
        assert "opacity: 1;" in result
        assert "data-pjx" not in result.split("@keyframes")[1]

    def test_nested_media_query(self) -> None:
        css = "@media (min-width: 768px) { .card { display: flex; } .card .title { font-size: 2rem; } }"
        result = scope_css(css, "a1b2c3d")
        assert "@media (min-width: 768px)" in result
        assert ".card[data-pjx-a1b2c3d]" in result
        assert ".title[data-pjx-a1b2c3d]" in result

    def test_pseudo_class_with_arguments(self) -> None:
        result = scope_css(".card:nth-child(2) { color: red; }", "a1b2c3d")
        assert ".card:nth-child(2)[data-pjx-a1b2c3d]" in result

    def test_child_combinator_no_spaces(self) -> None:
        """`.a>.b` (no spaces around >) should scope both parts."""
        result = scope_css(".a>.b { color: red; }", "a1b2c3d")
        assert ".a[data-pjx-a1b2c3d]" in result
        assert ".b[data-pjx-a1b2c3d]" in result
