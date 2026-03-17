"""Tests for pjx.runtime — template rendering end-to-end."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from pjx.exceptions import PropValidationError
from pjx.runtime import Runtime, extract_fragment_by_id


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_runtime(templates: dict[str, str]) -> tuple[Runtime, Path]:
    """Create a Runtime backed by temp files."""
    tmpdir = Path(tempfile.mkdtemp())
    for name, content in templates.items():
        (tmpdir / name).write_text(content)

    class MockCatalog:
        auto_reload = True

        def resolve_path(self, path: str) -> Path:
            return tmpdir / path

    return Runtime(MockCatalog()), tmpdir


# ── Basic rendering ───────────────────────────────────────────────────────────


def test_render_simple_template() -> None:
    runtime, _ = make_runtime(
        {
            "greeting.pjx": "<h1>Hello, {{ name }}!</h1>",
        }
    )
    html = runtime.render_root("greeting.pjx", {"name": "World"})
    assert "<h1>Hello, World!</h1>" in html


def test_render_with_prop_default() -> None:
    runtime, _ = make_runtime(
        {
            "page.pjx": '@props { title: str, subtitle: str = "" }\n<h1>{{ title }}</h1><p>{{ subtitle }}</p>',
        }
    )
    html = runtime.render_root("page.pjx", {"title": "Hello"})
    assert "<h1>Hello</h1>" in html
    assert "<p></p>" in html  # default empty string


def test_render_missing_required_prop_raises() -> None:
    runtime, _ = make_runtime(
        {"card.pjx": "@props { title: str }\n<div>{{ title }}</div>"}
    )
    with pytest.raises(PropValidationError, match="missing required prop"):
        runtime.render_root("card.pjx", {})


def test_render_pjx_id_injected() -> None:
    runtime, _ = make_runtime({"c.pjx": '<div id="{{ @id }}"></div>'})
    html = runtime.render_root("c.pjx", {})
    assert 'id="' in html
    # Each render gets a fresh UUID
    html2 = runtime.render_root("c.pjx", {})
    # Extract ids
    id1 = html.split('id="')[1].split('"')[0]
    id2 = html2.split('id="')[1].split('"')[0]
    assert id1 != id2


# ── Control structures ────────────────────────────────────────────────────────


def test_render_show_true() -> None:
    runtime, _ = make_runtime(
        {"t.pjx": '<Show when="{{ flag }}"><p>Visible</p></Show>'}
    )
    html = runtime.render_root("t.pjx", {"flag": True})
    assert "<p>Visible</p>" in html


def test_render_show_false_uses_fallback() -> None:
    runtime, _ = make_runtime(
        {
            "t.pjx": (
                '<Show when="{{ flag }}">'
                "<p>Shown</p>"
                "<:fallback><p>Hidden</p></:fallback>"
                "</Show>"
            )
        }
    )
    html = runtime.render_root("t.pjx", {"flag": False})
    assert "<p>Hidden</p>" in html
    assert "<p>Shown</p>" not in html


def test_render_for_loop() -> None:
    runtime, _ = make_runtime(
        {"t.pjx": '<For each="{{ items }}" as="x"><li>{{ x }}</li></For>'}
    )
    html = runtime.render_root("t.pjx", {"items": ["a", "b", "c"]})
    assert "<li>a</li>" in html
    assert "<li>b</li>" in html
    assert "<li>c</li>" in html


def test_render_switch() -> None:
    runtime, _ = make_runtime(
        {
            "t.pjx": (
                '<Switch on="{{ status }}">'
                '<Match value="ok"><p>OK</p></Match>'
                '<Match value="err"><p>Error</p></Match>'
                "</Switch>"
            )
        }
    )
    assert "<p>OK</p>" in runtime.render_root("t.pjx", {"status": "ok"})
    assert "<p>Error</p>" in runtime.render_root("t.pjx", {"status": "err"})


# ── Multi-component macros ────────────────────────────────────────────────────


def test_render_imported_single_component() -> None:
    """@import resolves component name from file stem (Button.pjx → Button)."""
    runtime, _ = make_runtime(
        {
            "Button.pjx": """
@component Button {
  @props { label: str, variant: str = "primary" }
  <button class="btn-{{ variant }}">{{ label }}</button>
}
""",
            "Badge.pjx": """
@component Badge {
  @props { text: str }
  <span class="badge">{{ text }}</span>
}
""",
            "page.pjx": """
@import "Button.pjx"
@import "Badge.pjx"
<div>
  <Button label="Click" />
  <Badge text="New" />
</div>
""",
        }
    )
    html = runtime.render_root("page.pjx", {})
    assert 'class="btn-primary"' in html
    assert "Click" in html
    assert 'class="badge"' in html
    assert "New" in html


def test_render_component_with_slots() -> None:
    runtime, _ = make_runtime(
        {
            "card.pjx": """
@component Card {
  @props { title: str }
  @slot footer?
  <div class="card">
    <h2>{{ title }}</h2>
    <slot />
    <footer><slot name="footer"><p>No footer</p></slot></footer>
  </div>
}
""",
            "page.pjx": """
@import "card.pjx"
<Card title="Hello">
  <p>Body content</p>
  <:footer><em>Custom footer</em></:footer>
</Card>
""",
        }
    )
    html = runtime.render_root("page.pjx", {})
    assert "<h2>Hello</h2>" in html
    assert "<p>Body content</p>" in html
    assert "<em>Custom footer</em>" in html
    assert "No footer" not in html


# ── Alpine state ──────────────────────────────────────────────────────────────


def test_alpine_state_serialized() -> None:
    runtime, _ = make_runtime(
        {"t.pjx": '@state { open: false }\n<div x-data="{{ @state }}"></div>'}
    )
    html = runtime.render_root("t.pjx", {})
    assert "x-data=" in html
    assert "open" in html


# ── Template caching ──────────────────────────────────────────────────────────


def test_template_cached_on_second_call(tmp_path: Path) -> None:
    tpl = tmp_path / "t.pjx"
    tpl.write_text("<p>v1</p>")

    class Catalog:
        auto_reload = False

        def resolve_path(self, path: str) -> Path:
            return tpl

    runtime = Runtime(Catalog())
    html1 = runtime.render_root("t.pjx", {})
    tpl.write_text("<p>v2</p>")  # modify file
    html2 = runtime.render_root("t.pjx", {})
    assert html1 == html2  # cache hit, not reloaded


def test_template_reloaded_when_auto_reload(tmp_path: Path) -> None:
    tpl = tmp_path / "t.pjx"
    tpl.write_text("<p>v1</p>")

    class Catalog:
        auto_reload = True

        def resolve_path(self, path: str) -> Path:
            return tpl

    runtime = Runtime(Catalog())
    runtime.render_root("t.pjx", {})
    import time

    time.sleep(0.01)  # ensure mtime changes
    tpl.write_text("<p>v2</p>")
    # Force mtime change
    import os

    os.utime(tpl, (tpl.stat().st_atime + 1, tpl.stat().st_mtime + 1))
    html2 = runtime.render_root("t.pjx", {})
    assert "v2" in html2


# ── Fragment extraction ───────────────────────────────────────────────────────


def test_extract_fragment_by_id() -> None:
    html = '<html><body><div id="result"><p>Content</p></div></body></html>'
    fragment = extract_fragment_by_id(html, "result")
    assert fragment == '<div id="result"><p>Content</p></div>'


def test_extract_fragment_not_found_raises() -> None:
    with pytest.raises(ValueError, match="Could not find fragment"):
        extract_fragment_by_id("<div></div>", "missing")


def test_render_partial_extracts_fragment() -> None:
    runtime, _ = make_runtime(
        {"t.pjx": '<div><div id="out"><p>{{ msg }}</p></div></div>'}
    )
    html = runtime.render_root("t.pjx", {"msg": "Hello"}, partial=True, target="out")
    assert html == '<div id="out"><p>Hello</p></div>'
