from __future__ import annotations

from pathlib import Path

import pytest

from pjx.ast import (
    ComputedDirectiveNode,
    ImportNode,
    PropsDirectiveNode,
    SignalDirectiveNode,
    SlotDirectiveNode,
)
from pjx.compiler import compile_component_file
from pjx.parser import parse_component_source


def test_parse_component_source_builds_structural_ast() -> None:
    source = """
{% import css "/static/css/demo.css" %}
{% import "components/ui/Button.jinja" as Button %}
{% set DemoProps = {
  "title": str,
  "count": int = 0
} %}

{% component Demo async %}
  {% props DemoProps %}
  {% provide theme %}
  {% slot header %}{% endslot %}
  {% signal total = signal(count) %}
  {% computed label %}{{ title }}{% endcomputed %}

  <section>{{ label }}</section>
{% endcomponent %}
"""

    parsed = parse_component_source(source, Path("Demo.jinja"))

    assert parsed.imports == (
        ImportNode(kind="css", path="/static/css/demo.css", alias=None),
        ImportNode(kind="component", path="components/ui/Button.jinja", alias="Button"),
    )
    assert parsed.prop_aliases[0].name == "DemoProps"
    assert tuple(prop.name for prop in parsed.prop_aliases[0].props) == ("title", "count")
    assert parsed.component.name == "Demo"
    assert parsed.component.modifiers == ("async",)
    assert isinstance(parsed.component.directives[0], PropsDirectiveNode)
    assert isinstance(parsed.component.directives[2], SlotDirectiveNode)
    assert isinstance(parsed.component.directives[3], SignalDirectiveNode)
    assert isinstance(parsed.component.directives[4], ComputedDirectiveNode)
    assert parsed.component.body.lstrip().startswith("<section>")


def test_compile_component_file_uses_ast_directives() -> None:
    source = """
{% import css "/static/css/demo.css" %}
{% set DemoProps = {
  "title": str,
  "count": int = 0
} %}

{% component Demo %}
  {% props DemoProps %}
  {% slot header %}{% endslot %}
  {% signal total = signal(count) %}
  {% computed label %}{{ title }}{% endcomputed %}

  <section data-total="{{ total }}">{{ label }}</section>
{% endcomponent %}
"""

    compiled = compile_component_file(source, Path("Demo.jinja"))

    assert compiled.component_name == "Demo"
    assert tuple(spec.name for spec in compiled.prop_specs) == ("title", "count")
    assert "header" in compiled.slot_specs
    assert "{% set total = count %}" in compiled.jinja_source
    assert "{% set label %}{{ title }}{% endset %}" in compiled.jinja_source
    assert '<section data-total="{{ total }}">{{ label }}</section>' in compiled.jinja_source


def test_parse_component_source_rejects_trailing_top_level_content() -> None:
    source = """
{% component Demo %}
  <div>ok</div>
{% endcomponent %}
<div>extra</div>
"""

    with pytest.raises(ValueError, match="unexpected content after component declaration"):
        parse_component_source(source, Path("Demo.jinja"))


def test_compile_component_file_rejects_duplicate_slot_declarations() -> None:
    source = """
{% component Demo %}
  {% slot header %}{% endslot %}
  {% slot header %}{% endslot %}
  <div>ok</div>
{% endcomponent %}
"""

    with pytest.raises(ValueError, match="Duplicate slot declaration: header"):
        compile_component_file(source, Path("Demo.jinja"))
