"""Tests for pjx.compiler — AST to Jinja2 + Alpine + HTMX compilation."""

from pathlib import Path

from pjx.ast_nodes import (
    AwaitNode,
    CaseNode,
    Component,
    ComponentNode,
    ComputedDecl,
    ConstDecl,
    ElementNode,
    ExtendsDecl,
    ForNode,
    FragmentNode,
    ImportDecl,
    LetDecl,
    PortalNode,
    ShowNode,
    SlotRenderNode,
    StateDecl,
    StoreDecl,
    SwitchNode,
    TeleportNode,
    TextNode,
    TransitionGroupNode,
)
from pjx.compiler import Compiler


def _minimal_component(**kwargs: object) -> Component:
    """Helper to create a minimal Component for testing."""
    defaults: dict[str, object] = {
        "path": Path("test.jinja"),
        "body": (TextNode(content="hello"),),
    }
    defaults.update(kwargs)
    return Component(**defaults)  # type: ignore[arg-type]


def _compile(component: Component) -> str:
    """Compile and return jinja_source."""
    return Compiler().compile(component).jinja_source


# ---------------------------------------------------------------------------
# Preamble: let, const, computed
# ---------------------------------------------------------------------------


class TestPreamble:
    def test_compile_let_const(self) -> None:
        comp = _minimal_component(
            variables=(LetDecl("x", '"hello"'), ConstDecl("MAX", "100")),
        )
        result = _compile(comp)
        assert '{% set x = "hello" %}' in result
        assert "{% set MAX = 100 %}" in result

    def test_compile_computed(self) -> None:
        comp = _minimal_component(
            computed=(ComputedDecl("doubled", "count * 2"),),
        )
        result = _compile(comp)
        assert "{% set doubled = count * 2 %}" in result


# ---------------------------------------------------------------------------
# State → Alpine x-data
# ---------------------------------------------------------------------------


class TestState:
    def test_compile_state_to_alpine_data(self) -> None:
        comp = _minimal_component(
            states=(StateDecl("count", "0"), StateDecl("editing", "false")),
            body=(ElementNode(tag="div", attrs={"reactive": True}),),
        )
        result = _compile(comp)
        assert "x-data" in result
        assert "count: 0" in result
        assert "editing: false" in result


# ---------------------------------------------------------------------------
# Extends
# ---------------------------------------------------------------------------


class TestExtends:
    def test_compile_extends(self) -> None:
        comp = _minimal_component(
            extends=ExtendsDecl("layouts/Base.jinja"),
        )
        result = _compile(comp)
        assert '{% extends "layouts/Base.jinja" %}' in result


# ---------------------------------------------------------------------------
# Stores
# ---------------------------------------------------------------------------


class TestStores:
    def test_compile_store(self) -> None:
        comp = _minimal_component(
            stores=(StoreDecl("theme", '{ dark: false, accent: "blue" }'),),
        )
        result = _compile(comp)
        assert "Alpine.store" in result
        assert "'theme'" in result


# ---------------------------------------------------------------------------
# Control flow
# ---------------------------------------------------------------------------


class TestShow:
    def test_compile_show(self) -> None:
        comp = _minimal_component(
            body=(ShowNode(when="visible", body=(TextNode("yes"),)),),
        )
        result = _compile(comp)
        assert "{% if visible %}" in result
        assert "yes" in result
        assert "{% endif %}" in result

    def test_compile_show_fallback(self) -> None:
        comp = _minimal_component(
            body=(
                ShowNode(
                    when="visible",
                    body=(TextNode("yes"),),
                    fallback=(TextNode("no"),),
                ),
            ),
        )
        result = _compile(comp)
        assert "{% else %}" in result
        assert "no" in result


class TestFor:
    def test_compile_for(self) -> None:
        comp = _minimal_component(
            body=(ForNode(each="items", as_var="item", body=(TextNode("x"),)),),
        )
        result = _compile(comp)
        assert "{% for item in items %}" in result
        assert "{% endfor %}" in result

    def test_compile_for_empty(self) -> None:
        comp = _minimal_component(
            body=(
                ForNode(
                    each="items",
                    as_var="item",
                    body=(TextNode("x"),),
                    empty=(TextNode("none"),),
                ),
            ),
        )
        result = _compile(comp)
        assert "{% else %}" in result
        assert "none" in result


class TestSwitch:
    def test_compile_switch(self) -> None:
        comp = _minimal_component(
            body=(
                SwitchNode(
                    on="status",
                    cases=(
                        CaseNode(value='"active"', body=(TextNode("Active"),)),
                        CaseNode(value='"inactive"', body=(TextNode("Inactive"),)),
                    ),
                    default=(TextNode("Unknown"),),
                ),
            ),
        )
        result = _compile(comp)
        assert '{% if status == "active" %}' in result
        assert '{% elif status == "inactive" %}' in result
        assert "{% else %}" in result
        assert "{% endif %}" in result


class TestPortal:
    def test_compile_portal(self) -> None:
        comp = _minimal_component(
            body=(PortalNode(target="/api/data", body=(TextNode("loading..."),)),),
        )
        result = _compile(comp)
        assert 'hx-get="/api/data"' in result
        assert 'hx-swap="innerHTML"' in result


class TestAwait:
    def test_compile_await(self) -> None:
        comp = _minimal_component(
            body=(AwaitNode(src="/api/data", trigger="load"),),
        )
        result = _compile(comp)
        assert 'hx-get="/api/data"' in result
        assert 'hx-trigger="load"' in result


class TestFragment:
    def test_compile_fragment(self) -> None:
        comp = _minimal_component(
            body=(FragmentNode(children=(TextNode("a"), TextNode("b"))),),
        )
        result = _compile(comp)
        assert "ab" in result


class TestTransitionGroup:
    def test_compile_transition_group(self) -> None:
        comp = _minimal_component(
            body=(
                TransitionGroupNode(
                    tag="ul",
                    enter="fade-in",
                    leave="fade-out",
                    move="slide",
                    body=(TextNode("<li>x</li>"),),
                ),
            ),
        )
        result = _compile(comp)
        assert "<ul " in result
        assert 'x-transition:enter="fade-in"' in result
        assert "</ul>" in result


# ---------------------------------------------------------------------------
# Attributes
# ---------------------------------------------------------------------------


class TestAttrs:
    def test_compile_attrs_bind_text(self) -> None:
        comp = _minimal_component(
            body=(ElementNode(tag="span", attrs={"bind:text": "name"}),),
        )
        result = _compile(comp)
        assert 'x-text="name"' in result

    def test_compile_attrs_bind_model(self) -> None:
        comp = _minimal_component(
            body=(
                ElementNode(
                    tag="input", attrs={"bind:model": "query"}, self_closing=True
                ),
            ),
        )
        result = _compile(comp)
        assert 'x-model="query"' in result

    def test_compile_attrs_bind_model_modifier(self) -> None:
        comp = _minimal_component(
            body=(
                ElementNode(
                    tag="input", attrs={"bind:model.lazy": "query"}, self_closing=True
                ),
            ),
        )
        result = _compile(comp)
        assert 'x-model.lazy="query"' in result

    def test_compile_attrs_bind_generic(self) -> None:
        comp = _minimal_component(
            body=(ElementNode(tag="div", attrs={"bind:class": "cls"}),),
        )
        result = _compile(comp)
        assert ':class="cls"' in result

    def test_compile_attrs_on_click(self) -> None:
        comp = _minimal_component(
            body=(ElementNode(tag="button", attrs={"on:click": "increment()"}),),
        )
        result = _compile(comp)
        assert '@click="increment()"' in result

    def test_compile_attrs_on_with_mods(self) -> None:
        comp = _minimal_component(
            body=(ElementNode(tag="form", attrs={"on:submit.prevent": "save()"}),),
        )
        result = _compile(comp)
        assert '@submit.prevent="save()"' in result

    def test_compile_attrs_action_get(self) -> None:
        comp = _minimal_component(
            body=(ElementNode(tag="button", attrs={"action:get": "/api/data"}),),
        )
        result = _compile(comp)
        assert 'hx-get="/api/data"' in result

    def test_compile_attrs_action_post(self) -> None:
        comp = _minimal_component(
            body=(ElementNode(tag="form", attrs={"action:post": "/api/submit"}),),
        )
        result = _compile(comp)
        assert 'hx-post="/api/submit"' in result

    def test_compile_attrs_htmx_swap(self) -> None:
        comp = _minimal_component(
            body=(ElementNode(tag="div", attrs={"swap": "outerHTML"}),),
        )
        result = _compile(comp)
        assert 'hx-swap="outerHTML"' in result

    def test_compile_attrs_htmx_target(self) -> None:
        comp = _minimal_component(
            body=(ElementNode(tag="div", attrs={"target": "#result"}),),
        )
        result = _compile(comp)
        assert 'hx-target="#result"' in result

    def test_compile_attrs_htmx_trigger(self) -> None:
        comp = _minimal_component(
            body=(ElementNode(tag="div", attrs={"trigger": "click"}),),
        )
        result = _compile(comp)
        assert 'hx-trigger="click"' in result

    def test_compile_attrs_sse(self) -> None:
        comp = _minimal_component(
            body=(
                ElementNode(tag="div", attrs={"live": "/events", "channel": "updates"}),
            ),
        )
        result = _compile(comp)
        assert 'hx-ext="sse"' in result
        assert 'sse-connect="/events"' in result
        assert 'sse-swap="updates"' in result

    def test_compile_attrs_websocket(self) -> None:
        comp = _minimal_component(
            body=(ElementNode(tag="div", attrs={"socket": "/ws", "send": True}),),
        )
        result = _compile(comp)
        assert 'hx-ext="ws"' in result
        assert 'ws-connect="/ws"' in result
        assert "ws-send" in result

    def test_compile_attrs_reactive(self) -> None:
        comp = _minimal_component(
            states=(StateDecl("count", "0"),),
            body=(ElementNode(tag="div", attrs={"reactive": True}),),
        )
        result = _compile(comp)
        assert 'x-data="{ count: 0 }"' in result

    def test_compile_attrs_boost(self) -> None:
        comp = _minimal_component(
            body=(ElementNode(tag="a", attrs={"boost": True}),),
        )
        result = _compile(comp)
        assert 'hx-boost="true"' in result


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------


class TestComponents:
    def test_compile_component_include(self) -> None:
        comp = _minimal_component(
            imports=(ImportDecl(names=("Button",), source="./Button.jinja"),),
            body=(ComponentNode(name="Button", attrs={"variant": "primary"}),),
        )
        result = _compile(comp)
        assert '{% include "./Button.jinja" %}' in result
        assert '{% set variant = "primary" %}' in result

    def test_compile_component_spread(self) -> None:
        comp = _minimal_component(
            imports=(ImportDecl(names=("Button",), source="./Button.jinja"),),
            body=(ComponentNode(name="Button", spread="my_props"),),
        )
        result = _compile(comp)
        assert "{% set _spread = my_props %}" in result


# ---------------------------------------------------------------------------
# Scoped CSS
# ---------------------------------------------------------------------------


class TestScopedCSS:
    def test_compile_scoped_css(self) -> None:
        comp = _minimal_component(
            style=".card { color: red; }",
            body=(ElementNode(tag="div", attrs={"reactive": True}),),
        )
        compiled = Compiler().compile(comp)
        assert compiled.css is not None
        assert "data-pjx-" in compiled.css.source
        assert compiled.scope_hash in compiled.css.hash


# ---------------------------------------------------------------------------
# Slot rendering
# ---------------------------------------------------------------------------


class TestSlots:
    def test_compile_slot_render(self) -> None:
        comp = _minimal_component(
            body=(SlotRenderNode(name="header"),),
        )
        result = _compile(comp)
        assert '{{ slot_header|default("") }}' in result

    def test_compile_slot_render_fallback(self) -> None:
        comp = _minimal_component(
            body=(SlotRenderNode(name="footer", fallback=(TextNode("Default"),)),),
        )
        result = _compile(comp)
        assert "{% if slot_footer is defined %}" in result
        assert "{{ slot_footer }}" in result
        assert "{% else %}Default{% endif %}" in result


# ---------------------------------------------------------------------------
# Teleport
# ---------------------------------------------------------------------------


class TestTeleport:
    def test_compile_teleport(self) -> None:
        comp = _minimal_component(
            body=(TeleportNode(to="head", body=(TextNode("<title>Hi</title>"),)),),
        )
        result = _compile(comp)
        assert "{% block teleport_head %}" in result
        assert "{% endblock %}" in result
