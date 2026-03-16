"""Tests for pjx.compiler — PjxFile AST → Jinja2 source."""

from __future__ import annotations

import pytest

from pjx.compiler import compile_pjx
from pjx.exceptions import CompileError
from pjx.parser import parse


def _compile(src: str) -> str:
    return compile_pjx(parse(src))


# ── Preamble ──────────────────────────────────────────────────────────────────


def test_state_preamble() -> None:
    jinja = _compile("@state { open: false, count: 0 }\n<div/>")
    assert '{% set __pjx_state = {"open": false, "count": 0} %}' in jinja


def test_props_defaults_preamble() -> None:
    jinja = _compile("@props {\n  name: str\n  count: int = 0\n}\n<div/>")
    assert "{% if count is not defined %}" in jinja
    assert "{% set count = 0 %}" in jinja
    # Required props get no default injection
    assert "{% if name is not defined %}" not in jinja


def test_let_preamble() -> None:
    jinja = _compile("@let total = items | length\n<div/>")
    assert "{% set total = items | length %}" in jinja


# ── HTML elements ─────────────────────────────────────────────────────────────


def test_html_element_basic() -> None:
    jinja = _compile('<div class="card"><p>Hello</p></div>')
    assert '<div class="card"><p>Hello</p></div>' in jinja


def test_html_self_closing() -> None:
    jinja = _compile('<img src="test.png" />')
    assert "<img" in jinja
    assert "/>" in jinja


def test_boolean_attribute() -> None:
    jinja = _compile("<input disabled />")
    assert " disabled" in jinja


def test_dynamic_binding_colon_prefix() -> None:
    jinja = _compile('<div :class="{{ active_class }}"></div>')
    assert 'class="{{ active_class }}"' in jinja


# ── HTMX directives ───────────────────────────────────────────────────────────


def test_htmx_event_shorthand() -> None:
    jinja = _compile('<button @click.htmx="post:/api/submit">Go</button>')
    assert 'hx-post="/api/submit"' in jinja
    assert 'hx-trigger="click"' in jinja


def test_htmx_swap_modifier() -> None:
    jinja = _compile('<div @click.htmx="get:/url" @swap="outerHTML"></div>')
    assert 'hx-swap="outerHTML"' in jinja


def test_htmx_target_modifier() -> None:
    jinja = _compile('<button @click.htmx="get:/url" @target="#result">X</button>')
    assert 'hx-target="#result"' in jinja


def test_htmx_push_url_underscore() -> None:
    jinja = _compile('<a @click.htmx="get:/page" @push_url="/page">Link</a>')
    assert "hx-push-url" in jinja


# ── Alpine.js ─────────────────────────────────────────────────────────────────


def test_alpine_state_helper() -> None:
    jinja = _compile('@state { open: false }\n<div x-data="{{ @state }}"></div>')
    assert 'x-data="{{ __pjx_state | tojson }}"' in jinja


def test_alpine_event_passthrough() -> None:
    jinja = _compile('<button @click.alpine="count++">+</button>')
    assert '@click="count++"' in jinja


# ── @-helpers ─────────────────────────────────────────────────────────────────


def test_id_helper() -> None:
    jinja = _compile('<div id="{{ @id }}"></div>')
    assert 'id="{{ __pjx_id }}"' in jinja


def test_has_slot_helper() -> None:
    jinja = _compile("{{ @has_slot('header') }}")
    assert "{{ __slot_header }}" in jinja


def test_event_url_helper() -> None:
    jinja = _compile("{{ @event_url('submit') }}")
    assert "{{ __pjx_event_url('submit') }}" in jinja


# ── Control structures ────────────────────────────────────────────────────────


def test_show_compiles_to_if() -> None:
    jinja = _compile('<Show when="{{ active }}"><p>Yes</p></Show>')
    assert "{% if active %}" in jinja
    assert "{% endif %}" in jinja
    assert "<p>Yes</p>" in jinja


def test_show_fallback_compiles_to_else() -> None:
    jinja = _compile(
        '<Show when="{{ x }}"><p>T</p><:fallback><p>F</p></:fallback></Show>'
    )
    assert "{% else %}" in jinja
    assert "<p>F</p>" in jinja


def test_for_compiles_to_jinja_for() -> None:
    jinja = _compile('<For each="{{ items }}" as="item"><li>{{ item }}</li></For>')
    assert "{% for item in items %}" in jinja
    assert "{% endfor %}" in jinja


def test_for_index_var() -> None:
    jinja = _compile('<For each="{{ xs }}" as="x" index="i"><span/></For>')
    assert "{% set i = loop.index0 %}" in jinja


def test_for_empty_slot() -> None:
    jinja = _compile(
        '<For each="{{ items }}" as="i">'
        "<li>{{ i }}</li>"
        "<:empty><p>No items</p></:empty>"
        "</For>"
    )
    assert "{% else %}" in jinja
    assert "<p>No items</p>" in jinja


def test_switch_compiles_to_if_elif_else() -> None:
    src = (
        '<Switch on="{{ status }}">'
        '<Match value="ok"><p>OK</p></Match>'
        '<Match value="err"><p>Err</p></Match>'
        "<:fallback><p>?</p></:fallback>"
        "</Switch>"
    )
    jinja = _compile(src)
    assert '{% if status == "ok" %}' in jinja
    assert '{% elif status == "err" %}' in jinja
    assert "{% else %}" in jinja
    assert "{% endif %}" in jinja


# ── Slots ─────────────────────────────────────────────────────────────────────


def test_default_slot_output() -> None:
    src = "@component C { <slot /> }"
    jinja = _compile(src)
    assert "{{ __slot_default | safe }}" in jinja


def test_named_slot_output() -> None:
    src = '@component C { <slot name="header" /> }'
    jinja = _compile(src)
    assert "{{ __slot_header | safe }}" in jinja


def test_slot_with_fallback() -> None:
    src = "@component C { <slot><p>Default</p></slot> }"
    jinja = _compile(src)
    assert "{% if __slot_default %}" in jinja
    assert "<p>Default</p>" in jinja


# ── Multi-component mode ──────────────────────────────────────────────────────


def test_multi_component_emits_macros() -> None:
    src = """
@component Button {
  @props { label: str }
  <button>{{ label }}</button>
}
@component Badge {
  @props { text: str, color: str = "blue" }
  <span class="{{ color }}">{{ text }}</span>
}
"""
    jinja = _compile(src)
    assert "{% macro Button(label, __slot_default='') %}" in jinja
    assert "{% macro Badge(text, color=\"blue\", __slot_default='') %}" in jinja
    assert "{% endmacro %}" in jinja


def test_macro_includes_slot_params() -> None:
    src = """
@component Card {
  @props { title: str }
  @slot header?
  @slot footer?
  <div>{{ title }}</div>
}
"""
    jinja = _compile(src)
    assert "__slot_header=''" in jinja
    assert "__slot_footer=''" in jinja


# ── Component calls ───────────────────────────────────────────────────────────


def test_local_component_call() -> None:
    src = """
@component Btn {
  @props { label: str }
  <button>{{ label }}</button>
}
@component Page {
  <Btn label="Click" />
}
"""
    jinja = _compile(src)
    assert 'Btn(label="Click"' in jinja


def test_component_call_with_slots() -> None:
    src = """
@component Layout {
  @slot header?
  <main><slot /></main>
}
@component Page {
  <Layout>
    <:header><nav>Nav</nav></:header>
    <p>Body</p>
  </Layout>
}
"""
    jinja = _compile(src)
    assert "{% set __slot_header %}" in jinja
    assert "{% set __slot_default %}" in jinja
    assert "__slot_header=__slot_header" in jinja


def test_unknown_component_raises() -> None:
    src = "<Unknown />"
    with pytest.raises(CompileError, match="Unknown component"):
        _compile(src)


# ── Whitespace ────────────────────────────────────────────────────────────────


def test_inline_whitespace_preserved() -> None:
    jinja = _compile("<p>Hello {{ name }} world</p>")
    assert "Hello {{ name }} world" in jinja
