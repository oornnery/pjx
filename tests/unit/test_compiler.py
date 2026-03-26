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
    ErrorBoundaryNode,
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
    TransitionNode,
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

    def test_compile_attrs_into_default_swap(self) -> None:
        comp = _minimal_component(
            body=(ElementNode(tag="div", attrs={"into": "#target"}),),
        )
        result = _compile(comp)
        assert 'hx-target="#target"' in result
        assert 'hx-swap="innerHTML"' in result

    def test_compile_attrs_into_custom_swap(self) -> None:
        comp = _minimal_component(
            body=(ElementNode(tag="div", attrs={"into": "#target:outerHTML"}),),
        )
        result = _compile(comp)
        assert 'hx-target="#target"' in result
        assert 'hx-swap="outerHTML"' in result

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

    def test_compile_component_attrs_empty_default(self) -> None:
        """Without registry, attrs defaults to empty string."""
        comp = _minimal_component(
            imports=(ImportDecl(names=("Button",), source="./Button.jinja"),),
            body=(ComponentNode(name="Button"),),
        )
        result = _compile(comp)
        assert '{% set attrs = "" %}' in result


class TestComponentAttrsPassthrough:
    """Test attrs separation when compiler has access to a registry."""

    def _make_registry_with_child(
        self, child_name: str, child_component: Component
    ) -> "ComponentRegistry":  # noqa: F821
        from pjx.registry import ComponentRegistry

        registry = ComponentRegistry()
        # Directly populate the cache to avoid stat() on non-existent files
        registry._by_name[child_name] = child_component
        return registry

    def test_attrs_passthrough_separates_props_from_extras(self) -> None:
        """Extra attrs not in child PropsDecl go to {% set attrs %}."""
        from pjx.ast_nodes import PropField, PropsDecl

        child = _minimal_component(
            path=Path("Button.jinja"),
            props=PropsDecl(
                name="ButtonProps",
                fields=(PropField("variant", "str", default='"primary"'),),
            ),
        )
        registry = self._make_registry_with_child("Button", child)

        parent = _minimal_component(
            imports=(ImportDecl(names=("Button",), source="./Button.jinja"),),
            body=(
                ComponentNode(
                    name="Button",
                    attrs={"variant": "danger", "class": "btn-lg", "id": "my-btn"},
                ),
            ),
        )
        result = Compiler(registry=registry).compile(parent).jinja_source
        # variant is a declared prop → {% set variant = "danger" %}
        assert '{% set variant = "danger" %}' in result
        # class and id are extras → in {% set attrs %}...{% endset %}
        assert "{% set attrs %}" in result
        assert 'class="btn-lg"' in result
        assert 'id="my-btn"' in result

    def test_attrs_passthrough_transforms_reactive_attrs(self) -> None:
        """Extra reactive attrs are compiled through _compile_attr."""
        from pjx.ast_nodes import PropField, PropsDecl

        child = _minimal_component(
            path=Path("Card.jinja"),
            props=PropsDecl(
                name="CardProps",
                fields=(PropField("title", "str"),),
            ),
        )
        registry = self._make_registry_with_child("Card", child)

        parent = _minimal_component(
            imports=(ImportDecl(names=("Card",), source="./Card.jinja"),),
            body=(
                ComponentNode(
                    name="Card",
                    attrs={
                        "title": "Hello",
                        "on:click": "toggle()",
                        "action:get": "/api/data",
                    },
                ),
            ),
        )
        result = Compiler(registry=registry).compile(parent).jinja_source
        # title is a prop
        assert '{% set title = "Hello" %}' in result
        # on:click → @click in attrs
        assert '@click="toggle()"' in result
        # action:get → hx-get in attrs
        assert 'hx-get="/api/data"' in result

    def test_attrs_passthrough_no_props_decl_fallback(self) -> None:
        """Child without PropsDecl → all attrs treated as props (backwards compat)."""
        child = _minimal_component(path=Path("Box.jinja"), props=None)
        registry = self._make_registry_with_child("Box", child)

        parent = _minimal_component(
            imports=(ImportDecl(names=("Box",), source="./Box.jinja"),),
            body=(ComponentNode(name="Box", attrs={"class": "container"}),),
        )
        result = Compiler(registry=registry).compile(parent).jinja_source
        # No PropsDecl → all go to {% set %}
        assert '{% set class = "container" %}' in result
        assert '{% set attrs = "" %}' in result

    def test_attrs_passthrough_no_registry_fallback(self) -> None:
        """Without registry, all attrs go to {% set %} and attrs is empty."""
        parent = _minimal_component(
            imports=(ImportDecl(names=("Btn",), source="./Btn.jinja"),),
            body=(ComponentNode(name="Btn", attrs={"variant": "x", "class": "y"}),),
        )
        result = Compiler(registry=None).compile(parent).jinja_source
        assert '{% set variant = "x" %}' in result
        assert '{% set class = "y" %}' in result
        assert '{% set attrs = "" %}' in result


# ---------------------------------------------------------------------------
# Scoped CSS
# ---------------------------------------------------------------------------


class TestInlineIncludes:
    def test_basic_inline(self) -> None:
        source = '{% set x = 1 %}{% include "child.jinja" %}'
        templates = {"child.jinja": "<p>hello</p>"}
        result = Compiler.inline_includes(source, templates)
        assert "{% include" not in result
        assert "<p>hello</p>" in result
        assert "{% set x = 1 %}" in result

    def test_nested_inline(self) -> None:
        source = '{% include "parent.jinja" %}'
        templates = {
            "parent.jinja": '<div>{% include "child.jinja" %}</div>',
            "child.jinja": "<span>leaf</span>",
        }
        result = Compiler.inline_includes(source, templates)
        assert "{% include" not in result
        assert "<div><span>leaf</span></div>" in result

    def test_missing_template_preserved(self) -> None:
        source = '{% include "missing.jinja" %}'
        result = Compiler.inline_includes(source, {})
        assert '{% include "missing.jinja" %}' in result

    def test_max_depth_stops_recursion(self) -> None:
        # Self-referencing template — should stop at max_depth
        source = '{% include "loop.jinja" %}'
        templates = {"loop.jinja": '{% include "loop.jinja" %}'}
        result = Compiler.inline_includes(source, templates, max_depth=3)
        # After 3 levels, the innermost include is preserved
        assert '{% include "loop.jinja" %}' in result

    def test_multiple_includes(self) -> None:
        source = '{% include "a.jinja" %} | {% include "b.jinja" %}'
        templates = {"a.jinja": "AAA", "b.jinja": "BBB"}
        result = Compiler.inline_includes(source, templates)
        assert "AAA | BBB" == result


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


# ---------------------------------------------------------------------------
# ErrorBoundary
# ---------------------------------------------------------------------------


class TestErrorBoundary:
    def test_compile_error_boundary(self) -> None:
        comp = _minimal_component(
            body=(
                ErrorBoundaryNode(
                    fallback="<p>Something went wrong</p>",
                    body=(TextNode("safe content"),),
                ),
            ),
        )
        result = _compile(comp)
        assert "{% try %}" in result
        assert "safe content" in result
        assert "{% except %}" in result
        assert "<p>Something went wrong</p>" in result
        assert "{% endtry %}" in result

    def test_compile_error_boundary_with_nested_element(self) -> None:
        comp = _minimal_component(
            body=(
                ErrorBoundaryNode(
                    fallback="<span>error</span>",
                    body=(
                        ElementNode(
                            tag="div",
                            attrs={},
                            children=(TextNode("nested"),),
                        ),
                    ),
                ),
            ),
        )
        result = _compile(comp)
        assert "{% try %}" in result
        assert "<div>nested</div>" in result
        assert "{% except %}<span>error</span>{% endtry %}" in result


# ---------------------------------------------------------------------------
# Await
# ---------------------------------------------------------------------------


class TestAwait:
    def test_compile_await_basic(self) -> None:
        comp = _minimal_component(
            body=(AwaitNode(src="/api/data", trigger="load"),),
        )
        result = _compile(comp)
        assert 'hx-get="/api/data"' in result
        assert 'hx-trigger="load"' in result
        assert 'hx-swap="innerHTML"' in result

    def test_compile_await_with_loading_slot(self) -> None:
        comp = _minimal_component(
            body=(
                AwaitNode(
                    src="/api/items",
                    trigger="revealed",
                    loading=(TextNode("Loading..."),),
                ),
            ),
        )
        result = _compile(comp)
        assert 'hx-get="/api/items"' in result
        assert 'hx-trigger="revealed"' in result
        assert "Loading..." in result

    def test_compile_await_no_loading(self) -> None:
        comp = _minimal_component(
            body=(AwaitNode(src="/api/empty"),),
        )
        result = _compile(comp)
        assert 'hx-get="/api/empty"' in result
        # No loading content inside the div
        assert "></div>" in result or '">Loading' not in result


# ---------------------------------------------------------------------------
# Transition
# ---------------------------------------------------------------------------


class TestTransition:
    def test_compile_transition_enter_leave(self) -> None:
        comp = _minimal_component(
            body=(
                TransitionNode(
                    enter="fade-in",
                    leave="fade-out",
                    body=(TextNode("animated"),),
                ),
            ),
        )
        result = _compile(comp)
        assert 'x-transition:enter="fade-in"' in result
        assert 'x-transition:leave="fade-out"' in result
        assert "animated" in result

    def test_compile_transition_enter_only(self) -> None:
        comp = _minimal_component(
            body=(
                TransitionNode(
                    enter="slide-in",
                    body=(TextNode("slide"),),
                ),
            ),
        )
        result = _compile(comp)
        assert 'x-transition:enter="slide-in"' in result
        assert "x-transition:leave" not in result
        assert "slide" in result

    def test_compile_transition_leave_only(self) -> None:
        comp = _minimal_component(
            body=(
                TransitionNode(
                    leave="slide-out",
                    body=(TextNode("bye"),),
                ),
            ),
        )
        result = _compile(comp)
        assert "x-transition:enter" not in result
        assert 'x-transition:leave="slide-out"' in result
        assert "bye" in result


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class TestStore:
    def test_compile_store_declaration(self) -> None:
        comp = _minimal_component(
            stores=(StoreDecl(name="theme", value='{ dark: false, accent: "blue" }'),),
        )
        result = _compile(comp)
        assert "Alpine.store('theme'" in result
        assert '{ dark: false, accent: "blue" }' in result
        assert "alpine:init" in result

    def test_compile_multiple_stores(self) -> None:
        comp = _minimal_component(
            stores=(
                StoreDecl(name="theme", value="{ dark: false }"),
                StoreDecl(name="cart", value="{ items: [], total: 0 }"),
            ),
        )
        result = _compile(comp)
        assert "Alpine.store('theme'" in result
        assert "Alpine.store('cart'" in result
        assert "{ dark: false }" in result
        assert "{ items: [], total: 0 }" in result


# ---------------------------------------------------------------------------
# Built-in layout components
# ---------------------------------------------------------------------------


class TestLayoutBuiltins:
    """Test built-in layout components compile to {% include %} with props."""

    def test_center_includes_template(self) -> None:
        comp = _minimal_component(
            body=(ComponentNode(name="Center", children=(TextNode("hi"),)),),
        )
        result = _compile(comp)
        assert '{% include "ui/layouts/Center.jinja" %}' in result
        assert "{% set slot_default %}hi{% endset %}" in result

    def test_hstack_sets_gap_prop(self) -> None:
        comp = _minimal_component(
            body=(
                ComponentNode(
                    name="HStack",
                    attrs={"gap": "2rem"},
                    children=(TextNode("a"), TextNode("b")),
                ),
            ),
        )
        result = _compile(comp)
        assert '{% include "ui/layouts/HStack.jinja" %}' in result
        assert '{% set gap = "2rem" %}' in result

    def test_vstack_sets_align_prop(self) -> None:
        comp = _minimal_component(
            body=(
                ComponentNode(
                    name="VStack",
                    attrs={"align": "center"},
                    children=(TextNode("x"),),
                ),
            ),
        )
        result = _compile(comp)
        assert '{% include "ui/layouts/VStack.jinja" %}' in result
        assert '{% set align = "center" %}' in result

    def test_grid_sets_cols_and_min(self) -> None:
        comp = _minimal_component(
            body=(
                ComponentNode(
                    name="Grid",
                    attrs={"cols": "3", "min": "200px"},
                    children=(TextNode("card"),),
                ),
            ),
        )
        result = _compile(comp)
        assert '{% include "ui/layouts/Grid.jinja" %}' in result
        assert '{% set cols = "3" %}' in result
        assert '{% set min = "200px" %}' in result

    def test_spacer_no_slot(self) -> None:
        comp = _minimal_component(
            body=(ComponentNode(name="Spacer"),),
        )
        result = _compile(comp)
        assert '{% include "ui/layouts/Spacer.jinja" %}' in result
        assert "slot_default" not in result

    def test_container_sets_max(self) -> None:
        comp = _minimal_component(
            body=(
                ComponentNode(
                    name="Container",
                    attrs={"max": "1200px"},
                    children=(TextNode("content"),),
                ),
            ),
        )
        result = _compile(comp)
        assert '{% include "ui/layouts/Container.jinja" %}' in result
        assert '{% set max = "1200px" %}' in result

    def test_divider_includes_template(self) -> None:
        comp = _minimal_component(
            body=(ComponentNode(name="Divider"),),
        )
        result = _compile(comp)
        assert '{% include "ui/layouts/Divider.jinja" %}' in result

    def test_wrap_includes_template(self) -> None:
        comp = _minimal_component(
            body=(
                ComponentNode(
                    name="Wrap",
                    children=(TextNode("items"),),
                ),
            ),
        )
        result = _compile(comp)
        assert '{% include "ui/layouts/Wrap.jinja" %}' in result

    def test_aspect_ratio_sets_prop(self) -> None:
        comp = _minimal_component(
            body=(
                ComponentNode(
                    name="AspectRatio",
                    attrs={"ratio": "4/3"},
                    children=(TextNode("video"),),
                ),
            ),
        )
        result = _compile(comp)
        assert '{% include "ui/layouts/AspectRatio.jinja" %}' in result
        assert '{% set ratio = "4/3" %}' in result

    def test_hide_sets_below(self) -> None:
        comp = _minimal_component(
            body=(
                ComponentNode(
                    name="Hide",
                    attrs={"below": "768px"},
                    children=(TextNode("desktop only"),),
                ),
            ),
        )
        result = _compile(comp)
        assert '{% include "ui/layouts/Hide.jinja" %}' in result
        assert '{% set below = "768px" %}' in result

    def test_extra_class_passed(self) -> None:
        comp = _minimal_component(
            body=(
                ComponentNode(
                    name="Center",
                    attrs={"class": "my-custom"},
                    children=(TextNode("x"),),
                ),
            ),
        )
        result = _compile(comp)
        assert '{% set class = "my-custom" %}' in result

    def test_justify_passed_as_prop(self) -> None:
        comp = _minimal_component(
            body=(
                ComponentNode(
                    name="HStack",
                    attrs={"justify": "between"},
                    children=(TextNode("x"),),
                ),
            ),
        )
        result = _compile(comp)
        assert '{% set justify = "between" %}' in result
