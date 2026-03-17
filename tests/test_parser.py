"""Tests for pjx.parser — recursive descent parser for .pjx files."""

from __future__ import annotations

import pytest

from pjx.ast import (
    ComponentCall,
    ExprNode,
    ForNode,
    FromImport,
    HtmlElement,
    ImportDirective,
    LetDirective,
    ShowNode,
    SlotNode,
    SwitchNode,
    TextNode,
)
from pjx.exceptions import ParseError
from pjx.parser import parse


# ── Directives ────────────────────────────────────────────────────────────────


def test_parse_from_import() -> None:
    ast = parse("@from myapp.utils import helper, format_date\n<div/>")
    assert len(ast.imports) == 1
    imp = ast.imports[0]
    assert isinstance(imp, FromImport)
    assert imp.module == "myapp.utils"
    assert imp.names == ("helper", "format_date")


def test_parse_import_directive() -> None:
    ast = parse('@import "components/Button.pjx"\n<div/>')
    imp = ast.imports[0]
    assert isinstance(imp, ImportDirective)
    assert imp.path == "components/Button.pjx"


def test_parse_bind_directive() -> None:
    ast = parse("@bind from myapp.components import MyComp\n<div/>")
    assert ast.bind is not None
    assert ast.bind.module == "myapp.components"
    assert ast.bind.class_name == "MyComp"


def test_parse_props_multiline() -> None:
    ast = parse("@props {\n  title: str\n  count: int = 0\n}\n<div/>")
    assert ast.props is not None
    props = ast.props.props
    assert len(props) == 2
    assert (props[0].name, props[0].type_expr, props[0].default_expr) == (
        "title",
        "str",
        None,
    )
    assert (props[1].name, props[1].type_expr, props[1].default_expr) == (
        "count",
        "int",
        "0",
    )


def test_parse_props_inline_comma_separated() -> None:
    ast = parse('@props { title: str, subtitle: str = "" }\n<div/>')
    assert ast.props is not None
    props = ast.props.props
    assert len(props) == 2
    assert props[0].name == "title"
    assert props[0].default_expr is None
    assert props[1].name == "subtitle"
    assert props[1].default_expr == '""'


def test_parse_props_complex_types() -> None:
    ast = parse('@props { items: list[str], mode: "a"|"b" = "a" }\n<div/>')
    props = ast.props.props
    assert props[0].type_expr == "list[str]"
    assert props[1].type_expr == '"a"|"b"'
    assert props[1].default_expr == '"a"'


def test_parse_slot_decl_optional() -> None:
    ast = parse("@slot header?\n<div/>")
    assert len(ast.slots) == 1
    assert ast.slots[0].name == "header"
    assert ast.slots[0].optional is True


def test_parse_slot_decl_required() -> None:
    ast = parse("@slot content\n<div/>")
    assert ast.slots[0].optional is False


def test_parse_state_block_inline() -> None:
    ast = parse("@state { open: false, count: 0 }\n<div/>")
    assert ast.state is not None
    fields = ast.state.fields
    assert len(fields) == 2
    assert (fields[0].name, fields[0].value) == ("open", "false")
    assert (fields[1].name, fields[1].value) == ("count", "0")


def test_parse_state_block_multiline() -> None:
    ast = parse("@state {\n  open: false\n  items: []\n}\n<div/>")
    fields = ast.state.fields
    assert fields[0].name == "open"
    assert fields[1].value == "[]"


def test_parse_let_directive() -> None:
    ast = parse("@let total = items | length\n<div/>")
    assert len(ast.lets) == 1
    let = ast.lets[0]
    assert isinstance(let, LetDirective)
    assert let.name == "total"
    assert let.expr == "items | length"


# ── Multi-component mode ──────────────────────────────────────────────────────


def test_multi_component_detection() -> None:
    src = """
@component Button {
  @props { label: str }
  <button>{{ label }}</button>
}
@component Card {
  @props { title: str }
  <div>{{ title }}</div>
}
"""
    ast = parse(src)
    assert ast.is_multi_component
    assert len(ast.components) == 2
    assert ast.components[0].name == "Button"
    assert ast.components[1].name == "Card"


def test_component_def_props_and_slots() -> None:
    src = """
@component Modal {
  @props { title: str, size: str = "md" }
  @slot header?
  @slot footer?
  <div>content</div>
}
"""
    ast = parse(src)
    comp = ast.components[0]
    assert comp.props.props[0].name == "title"
    assert comp.props.props[1].default_expr == '"md"'
    assert comp.slots[0].name == "header"
    assert comp.slots[0].optional is True
    assert comp.slots[1].name == "footer"


# ── Template body ─────────────────────────────────────────────────────────────


def test_parse_text_node() -> None:
    ast = parse("Hello world")
    assert len(ast.body) == 1
    assert isinstance(ast.body[0], TextNode)
    assert ast.body[0].content == "Hello world"


def test_parse_expr_node() -> None:
    ast = parse("{{ user.name }}")
    assert isinstance(ast.body[0], ExprNode)
    assert ast.body[0].content == "{{ user.name }}"


def test_parse_html_element() -> None:
    ast = parse('<div class="card" id="main"><p>Hello</p></div>')
    el = ast.body[0]
    assert isinstance(el, HtmlElement)
    assert el.tag == "div"
    assert el.attrs[0].name == "class" and el.attrs[0].value == "card"
    assert el.attrs[1].name == "id" and el.attrs[1].value == "main"
    assert isinstance(el.children[0], HtmlElement)
    assert el.children[0].tag == "p"


def test_parse_self_closing_element() -> None:
    ast = parse('<img src="test.png" />')
    el = ast.body[0]
    assert el.self_closing is True


def test_parse_void_element_is_self_closing() -> None:
    ast = parse('<br class="sep">')
    el = ast.body[0]
    assert el.self_closing is True


def test_parse_dynamic_attribute() -> None:
    ast = parse('<div :class="{{ active }}"></div>')
    el = ast.body[0]
    assert el.attrs[0].name == ":class" and el.attrs[0].value == "{{ active }}"


def test_parse_boolean_attribute() -> None:
    ast = parse("<input disabled />")
    el = ast.body[0]
    assert any(a.name == "disabled" and a.value is None for a in el.attrs)


# ── Control structures ────────────────────────────────────────────────────────


def test_parse_show_node() -> None:
    ast = parse('<Show when="{{ active }}"><p>Shown</p></Show>')
    node = ast.body[0]
    assert isinstance(node, ShowNode)
    assert node.condition == "active"
    assert isinstance(node.children[0], HtmlElement)


def test_parse_show_with_fallback() -> None:
    ast = parse(
        '<Show when="{{ x }}"><p>True</p><:fallback><p>False</p></:fallback></Show>'
    )
    node = ast.body[0]
    assert isinstance(node, ShowNode)
    assert len(node.fallback) == 1
    assert isinstance(node.fallback[0], HtmlElement)


def test_parse_for_node() -> None:
    ast = parse('<For each="{{ items }}" as="item"><span>{{ item }}</span></For>')
    node = ast.body[0]
    assert isinstance(node, ForNode)
    assert node.iterable == "items"
    assert node.variable == "item"


def test_parse_for_with_index() -> None:
    ast = parse('<For each="{{ items }}" as="x" index="i"><li/></For>')
    node = ast.body[0]
    assert node.index_var == "i"


def test_parse_switch_node() -> None:
    src = (
        '<Switch on="{{ status }}">'
        '<Match value="ok"><p>OK</p></Match>'
        '<Match value="err"><p>Error</p></Match>'
        "<:fallback><p>?</p></:fallback>"
        "</Switch>"
    )
    ast = parse(src)
    node = ast.body[0]
    assert isinstance(node, SwitchNode)
    assert node.expression == "status"
    assert len(node.cases) == 2
    assert node.cases[0].value == "ok"
    assert node.cases[1].value == "err"
    assert len(node.fallback) == 1


# ── Slots ─────────────────────────────────────────────────────────────────────


def test_parse_default_slot() -> None:
    ast = parse("<slot />")
    node = ast.body[0]
    assert isinstance(node, SlotNode)
    assert node.name == "default"
    assert len(node.fallback) == 0


def test_parse_named_slot() -> None:
    ast = parse('<slot name="header" />')
    node = ast.body[0]
    assert node.name == "header"


def test_parse_slot_with_fallback() -> None:
    ast = parse("<slot><p>Fallback content</p></slot>")
    node = ast.body[0]
    assert isinstance(node, SlotNode)
    assert len(node.fallback) == 1


# ── Component calls ───────────────────────────────────────────────────────────


def test_parse_component_call_self_closing() -> None:
    ast = parse('<Button label="Click me" />')
    node = ast.body[0]
    assert isinstance(node, ComponentCall)
    assert node.name == "Button"
    assert node.self_closing is True
    assert node.attrs[0].name == "label" and node.attrs[0].value == "Click me"


def test_parse_component_call_with_children() -> None:
    ast = parse("<Card><p>Default</p></Card>")
    node = ast.body[0]
    assert isinstance(node, ComponentCall)
    assert len(node.children) == 1


def test_parse_component_call_with_named_slots() -> None:
    src = (
        "<Card>"
        "<:header><h1>Title</h1></:header>"
        "<p>Body</p>"
        "<:footer><p>Footer</p></:footer>"
        "</Card>"
    )
    ast = parse(src)
    node = ast.body[0]
    assert isinstance(node, ComponentCall)
    assert "header" in node.named_slots
    assert "footer" in node.named_slots
    assert isinstance(node.children[0], HtmlElement)  # default slot


# ── Whitespace preservation ───────────────────────────────────────────────────


def test_inline_whitespace_preserved() -> None:
    ast = parse("<p>Hello {{ name }}!</p>")
    p = ast.body[0]
    # Children: TextNode("Hello "), ExprNode("{{ name }}"), TextNode("!")
    texts = [n for n in p.children if isinstance(n, TextNode)]
    assert any(" " in t.content for t in texts), "Space before expr should be preserved"


# ── Error cases ───────────────────────────────────────────────────────────────


def test_unclosed_props_block_raises() -> None:
    with pytest.raises(ParseError):
        parse("@props { title: str")


def test_show_without_when_raises() -> None:
    with pytest.raises(ParseError):
        parse("<Show><p>test</p></Show>")


def test_unexpected_token_in_multi_mode_raises() -> None:
    with pytest.raises(ParseError):
        parse("@component Foo { <div/> }\n<stray>tag</stray>")
