"""Tests for pjx.registry — component resolution and caching."""

from pathlib import Path

import pytest

from pjx.ast_nodes import ImportDecl
from pjx.errors import ImportResolutionError
from pjx.registry import ComponentRegistry


@pytest.fixture()
def tmp_templates(tmp_path: Path) -> Path:
    """Create a temporary templates directory with sample components."""
    tpl = tmp_path / "templates"
    tpl.mkdir()

    (tpl / "Button.jinja").write_text("<button>Click</button>")
    (tpl / "Card.jinja").write_text("<div class='card'></div>")

    ui_dir = tpl / "ui"
    ui_dir.mkdir()
    (ui_dir / "Badge.jinja").write_text("<span class='badge'></span>")
    (ui_dir / "Avatar.jinja").write_text("<img />")

    return tpl


class TestResolve:
    def test_resolve_relative_import(self, tmp_templates: Path) -> None:
        reg = ComponentRegistry([tmp_templates])
        imp = ImportDecl(names=("Card",), source="./Card.jinja")
        from_path = tmp_templates / "Button.jinja"
        components = reg.resolve(imp, from_path)
        assert len(components) == 1

    def test_resolve_named_import_from_dir(self, tmp_templates: Path) -> None:
        reg = ComponentRegistry([tmp_templates])
        imp = ImportDecl(names=("Badge", "Avatar"), source="./ui/")
        from_path = tmp_templates / "Button.jinja"
        components = reg.resolve(imp, from_path)
        assert len(components) == 2

    def test_resolve_wildcard_import(self, tmp_templates: Path) -> None:
        reg = ComponentRegistry([tmp_templates])
        imp = ImportDecl(names=(), source="./ui/", wildcard=True)
        from_path = tmp_templates / "Button.jinja"
        components = reg.resolve(imp, from_path)
        assert len(components) == 2  # Badge + Avatar

    def test_resolve_alias(self, tmp_templates: Path) -> None:
        reg = ComponentRegistry([tmp_templates])
        imp = ImportDecl(names=("Button",), source="./Button.jinja", alias="Btn")
        from_path = tmp_templates / "Card.jinja"
        reg.resolve(imp, from_path)
        assert reg.get("Btn") is not None

    def test_resolve_not_found(self, tmp_templates: Path) -> None:
        reg = ComponentRegistry([tmp_templates])
        imp = ImportDecl(names=("Missing",), source="./Missing.jinja")
        from_path = tmp_templates / "Button.jinja"
        with pytest.raises(ImportResolutionError):
            reg.resolve(imp, from_path)


class TestCache:
    def test_cache_hit(self, tmp_templates: Path) -> None:
        reg = ComponentRegistry([tmp_templates])
        imp = ImportDecl(names=("Button",), source="./Button.jinja")
        from_path = tmp_templates / "Card.jinja"
        c1 = reg.resolve(imp, from_path)
        c2 = reg.resolve(imp, from_path)
        assert c1[0] is c2[0]

    def test_cache_invalidation_mtime(self, tmp_templates: Path) -> None:
        import os
        import time

        reg = ComponentRegistry([tmp_templates])
        imp = ImportDecl(names=("Button",), source="./Button.jinja")
        from_path = tmp_templates / "Card.jinja"
        c1 = reg.resolve(imp, from_path)

        # Modify the file with different content and force mtime change
        btn_path = tmp_templates / "Button.jinja"
        btn_path.write_text("<button>Updated</button>")
        # Ensure mtime_ns differs by setting it explicitly into the future
        future_ns = time.time_ns() + 1_000_000_000
        os.utime(btn_path, ns=(future_ns, future_ns))

        c2 = reg.resolve(imp, from_path)
        # Content should differ since the file was rewritten
        assert c1[0].body != c2[0].body


class TestCircularImport:
    def test_circular_import_detection(self, tmp_path: Path) -> None:
        tpl = tmp_path / "templates"
        tpl.mkdir()

        # A imports B, B imports A
        (tpl / "A.jinja").write_text(
            '---\nimport B from "./B.jinja"\n---\n<div>A</div>'
        )
        (tpl / "B.jinja").write_text(
            '---\nimport A from "./A.jinja"\n---\n<div>B</div>'
        )

        reg = ComponentRegistry([tpl])
        with pytest.raises(ImportResolutionError, match="circular"):
            reg.compile_all(tpl / "A.jinja")
