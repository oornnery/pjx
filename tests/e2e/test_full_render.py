"""E2E test — parse → compile → render → assert HTML."""

from pathlib import Path

import pytest

from pjx.compiler import Compiler
from pjx.engine import Jinja2Engine
from pjx.parser import parse


class TestFullRender:
    """End-to-end: source → parse → compile → engine render → HTML."""

    def test_simple_component_renders(self) -> None:
        source = """<div class="greeting">
  <h1>Hello {{ name }}</h1>
</div>"""
        component = parse(source, path=Path("Greeting.jinja"))
        compiler = Compiler()
        compiled = compiler.compile(component)

        engine = Jinja2Engine()
        engine.add_template("Greeting.jinja", compiled.jinja_source)
        html = engine.render("Greeting.jinja", {"name": "World"})

        assert "Hello World" in html
        assert "<h1>" in html

    def test_component_with_state_and_show(self) -> None:
        source = """---
state count = 0
---

<div reactive>
  <Show when="count > 0">
    <p>Count: {{ count }}</p>
  </Show>
</div>"""
        component = parse(source, path=Path("Counter.jinja"))
        compiler = Compiler()
        compiled = compiler.compile(component)

        assert "x-data" in compiled.jinja_source
        assert "{% if count > 0 %}" in compiled.jinja_source

        engine = Jinja2Engine()
        engine.add_template("Counter.jinja", compiled.jinja_source)
        # With count > 0
        html = engine.render("Counter.jinja", {"count": 5})
        assert "Count: 5" in html

    def test_component_with_for_loop(self) -> None:
        source = """<ul>
  <For each="items" as="item">
    <li>{{ item }}</li>
  </For>
</ul>"""
        component = parse(source, path=Path("List.jinja"))
        compiler = Compiler()
        compiled = compiler.compile(component)

        engine = Jinja2Engine()
        engine.add_template("List.jinja", compiled.jinja_source)
        html = engine.render("List.jinja", {"items": ["a", "b", "c"]})

        assert "<li>a</li>" in html
        assert "<li>b</li>" in html
        assert "<li>c</li>" in html

    def test_component_with_scoped_css(self) -> None:
        source = """<style scoped>
.card { color: red; }
</style>

<div class="card">hello</div>"""
        component = parse(source, path=Path("Card.jinja"))
        compiler = Compiler()
        compiled = compiler.compile(component)

        assert compiled.css is not None
        assert "data-pjx-" in compiled.css.source
        assert compiled.scope_hash in compiled.css.hash

    def test_component_with_htmx_attrs(self) -> None:
        source = '<button action:post="/api/save" swap="outerHTML" target="#result">Save</button>'
        component = parse(source, path=Path("Save.jinja"))
        compiler = Compiler()
        compiled = compiler.compile(component)

        assert 'hx-post="/api/save"' in compiled.jinja_source
        assert 'hx-swap="outerHTML"' in compiled.jinja_source
        assert 'hx-target="#result"' in compiled.jinja_source

    def test_component_with_alpine_bindings(self) -> None:
        source = """---
state query = ""
---

<div reactive>
  <input bind:model="query" />
  <span bind:text="query"></span>
</div>"""
        component = parse(source, path=Path("Search.jinja"))
        compiler = Compiler()
        compiled = compiler.compile(component)

        assert 'x-model="query"' in compiled.jinja_source
        assert 'x-text="query"' in compiled.jinja_source
        assert "x-data" in compiled.jinja_source

    @pytest.mark.e2e
    def test_full_pipeline_with_fixtures(
        self, parsed_component: object, compiled_component: str
    ) -> None:
        """Use conftest fixtures for a complete pipeline test."""
        assert "{% set css_class" in compiled_component
        assert "{% if" in compiled_component
        assert "{{ props.text }}" in compiled_component
