"""Tests for pjx.formatter — canonical frontmatter formatting."""

from pathlib import Path
from textwrap import dedent


from pjx.formatter import format_file, format_source


class TestFormatSource:
    def test_no_frontmatter_unchanged(self) -> None:
        source = "<div>hello</div>\n"
        assert format_source(source) == source

    def test_empty_frontmatter_preserved(self) -> None:
        source = "---\n\n---\n<div>hello</div>\n"
        # Empty frontmatter after parse → preserve original
        result = format_source(source)
        assert result == source

    def test_single_import(self) -> None:
        source = dedent("""\
            ---
            import Button from "./Button.jinja"
            ---

            <Button />
        """)
        result = format_source(source)
        assert '---\nimport Button from "./Button.jinja"\n---\n' in result
        assert "<Button />" in result

    def test_canonical_order_extends_before_imports(self) -> None:
        source = dedent("""\
            ---
            import Navbar from "./Navbar.jinja"
            extends "layouts/Base.jinja"
            ---

            <Navbar />
        """)
        result = format_source(source)
        lines = result.split("---\n")[1].strip().split("\n")
        assert lines[0].startswith("extends")
        assert lines[1].startswith("import")

    def test_canonical_order_state_after_imports(self) -> None:
        source = dedent("""\
            ---
            state count = 0
            import Layout from "./Layout.jinja"
            ---

            <div />
        """)
        result = format_source(source)
        lines = result.split("---\n")[1].strip().split("\n")
        assert lines[0].startswith("import")
        assert lines[1].startswith("state")

    def test_props_single_field_inline(self) -> None:
        source = dedent("""\
            ---
            props { name: str }
            ---

            <div />
        """)
        result = format_source(source)
        assert "props { name: str }" in result

    def test_props_with_default(self) -> None:
        source = dedent("""\
            ---
            props { count: int = 0 }
            ---

            <div />
        """)
        result = format_source(source)
        assert "count: int = 0" in result

    def test_computed_and_let(self) -> None:
        source = dedent("""\
            ---
            let x = 1
            computed doubled = count * 2
            state count = 0
            ---

            <div />
        """)
        result = format_source(source)
        lines = result.split("---\n")[1].strip().split("\n")
        # Canonical order: state → computed → let
        assert lines[0].startswith("state")
        assert lines[1].startswith("computed")
        assert lines[2].startswith("let")

    def test_body_preserved_verbatim(self) -> None:
        body = "\n<div class='special'>\n  <!-- comment -->\n  {{ var }}\n</div>\n"
        source = f"---\nstate x = 0\n---\n{body}"
        result = format_source(source)
        assert result.endswith(body)

    def test_middleware(self) -> None:
        source = dedent("""\
            ---
            middleware "auth", "rate_limit"
            ---

            <div />
        """)
        result = format_source(source)
        assert 'middleware "auth", "rate_limit"' in result

    def test_assets(self) -> None:
        source = dedent("""\
            ---
            css "/static/styles.css"
            js "/static/app.js"
            ---

            <div />
        """)
        result = format_source(source)
        assert 'css "/static/styles.css"' in result
        assert 'js "/static/app.js"' in result

    def test_slot(self) -> None:
        source = dedent("""\
            ---
            slot header
            ---

            <div />
        """)
        result = format_source(source)
        assert "slot header" in result

    def test_from_import(self) -> None:
        source = dedent("""\
            ---
            from pydantic import EmailStr
            ---

            <div />
        """)
        result = format_source(source)
        assert "from pydantic import EmailStr" in result


class TestFormatFile:
    def test_unchanged_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.jinja"
        f.write_text("---\nstate x = 0\n---\n\n<div />\n")
        _, changed = format_file(f)
        assert changed is False

    def test_reordered_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.jinja"
        f.write_text(
            '---\nstate count = 0\nimport Layout from "./Layout.jinja"\n---\n\n<div />\n'
        )
        formatted, changed = format_file(f)
        assert changed is True
        assert formatted.index("import") < formatted.index("state")
