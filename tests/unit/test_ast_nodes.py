"""Tests for pjx.ast_nodes — immutability, instantiation, type union."""

from pathlib import Path

import pytest

from pjx.ast_nodes import (
    AwaitNode,
    CaseNode,
    CompiledComponent,
    Component,
    ComponentNode,
    ComputedDecl,
    ConstDecl,
    ElementNode,
    ErrorBoundaryNode,
    ExprNode,
    ExtendsDecl,
    ForNode,
    FragmentNode,
    FromImportDecl,
    ImportDecl,
    LetDecl,
    Node,
    PortalNode,
    PropField,
    PropsDecl,
    ScopedStyle,
    ShowNode,
    SlotDecl,
    SlotPassNode,
    SlotRenderNode,
    StateDecl,
    StoreDecl,
    SwitchNode,
    TeleportNode,
    TextNode,
    TransitionGroupNode,
    TransitionNode,
)


# ---------------------------------------------------------------------------
# Frontmatter declarations
# ---------------------------------------------------------------------------


class TestFrontmatterDecls:
    def test_extends_decl(self) -> None:
        d = ExtendsDecl(source="layouts/Base.jinja")
        assert d.source == "layouts/Base.jinja"

    def test_from_import_decl(self) -> None:
        d = FromImportDecl(module="pydantic", names=("EmailStr", "HttpUrl"))
        assert d.module == "pydantic"
        assert d.names == ("EmailStr", "HttpUrl")

    def test_import_decl_default(self) -> None:
        d = ImportDecl(names=("Button",), source="./Button.jinja")
        assert d.names == ("Button",)
        assert d.alias is None
        assert d.wildcard is False

    def test_import_decl_wildcard(self) -> None:
        d = ImportDecl(names=(), source="./ui/", wildcard=True)
        assert d.wildcard is True

    def test_import_decl_alias(self) -> None:
        d = ImportDecl(names=("Btn",), source="./Button.jinja", alias="Btn")
        assert d.alias == "Btn"

    def test_prop_field(self) -> None:
        f = PropField(name="age", type_expr="int", default="0")
        assert f.name == "age"
        assert f.default == "0"

    def test_props_decl(self) -> None:
        fields = (PropField(name="name", type_expr="str"),)
        d = PropsDecl(name="UserProps", fields=fields)
        assert d.name == "UserProps"
        assert len(d.fields) == 1

    def test_slot_decl_no_fallback(self) -> None:
        d = SlotDecl(name="actions")
        assert d.fallback is None

    def test_slot_decl_with_fallback(self) -> None:
        d = SlotDecl(name="footer", fallback="<span>Default</span>")
        assert d.fallback is not None

    def test_store_decl(self) -> None:
        d = StoreDecl(name="theme", value='{ dark: false, accent: "blue" }')
        assert d.name == "theme"

    def test_let_decl(self) -> None:
        d = LetDecl(name="css_class", expr='"todo-" + props.priority')
        assert d.name == "css_class"

    def test_const_decl(self) -> None:
        d = ConstDecl(name="MAX", expr="140")
        assert d.name == "MAX"

    def test_state_decl(self) -> None:
        d = StateDecl(name="count", value="0")
        assert d.value == "0"

    def test_computed_decl(self) -> None:
        d = ComputedDecl(name="remaining", expr="MAX - len(text)")
        assert d.expr == "MAX - len(text)"


# ---------------------------------------------------------------------------
# Body nodes
# ---------------------------------------------------------------------------


class TestBodyNodes:
    def test_text_node(self) -> None:
        n = TextNode(content="hello")
        assert n.content == "hello"

    def test_expr_node(self) -> None:
        n = ExprNode(expr="user.name")
        assert n.expr == "user.name"

    def test_element_node(self) -> None:
        n = ElementNode(tag="div", attrs={"class": "card"}, children=(TextNode("hi"),))
        assert n.tag == "div"
        assert len(n.children) == 1

    def test_element_node_self_closing(self) -> None:
        n = ElementNode(tag="br", self_closing=True)
        assert n.self_closing is True

    def test_show_node(self) -> None:
        n = ShowNode(
            when="visible", body=(TextNode("yes"),), fallback=(TextNode("no"),)
        )
        assert n.when == "visible"
        assert n.fallback is not None

    def test_for_node(self) -> None:
        n = ForNode(each="items", as_var="item", body=(TextNode("x"),))
        assert n.each == "items"
        assert n.as_var == "item"

    def test_switch_node(self) -> None:
        c = CaseNode(value="a", body=(TextNode("A"),))
        n = SwitchNode(on="status", cases=(c,), default=(TextNode("?"),))
        assert len(n.cases) == 1

    def test_portal_node(self) -> None:
        n = PortalNode(target="/api/data")
        assert n.swap == "innerHTML"

    def test_error_boundary_node(self) -> None:
        n = ErrorBoundaryNode(fallback="<p>Error</p>")
        assert n.error_slot is None

    def test_await_node(self) -> None:
        n = AwaitNode(src="/api/data")
        assert n.trigger == "load"

    def test_transition_node(self) -> None:
        n = TransitionNode(enter="fade-in", leave="fade-out")
        assert n.enter == "fade-in"

    def test_transition_group_node(self) -> None:
        n = TransitionGroupNode(tag="ul", move="slide")
        assert n.tag == "ul"

    def test_fragment_node(self) -> None:
        n = FragmentNode(children=(TextNode("a"), TextNode("b")))
        assert len(n.children) == 2

    def test_teleport_node(self) -> None:
        n = TeleportNode(to="body")
        assert n.to == "body"

    def test_slot_render_node(self) -> None:
        n = SlotRenderNode(name="header")
        assert n.fallback is None

    def test_slot_pass_node(self) -> None:
        n = SlotPassNode(name="header", content=(TextNode("title"),))
        assert len(n.content) == 1

    def test_component_node(self) -> None:
        n = ComponentNode(name="Button", attrs={"variant": "primary"}, spread="props")
        assert n.spread == "props"


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


ALL_NODE_CLASSES = [
    TextNode,
    ExprNode,
    ShowNode,
    ForNode,
    SwitchNode,
    CaseNode,
    PortalNode,
    ErrorBoundaryNode,
    AwaitNode,
    TransitionNode,
    TransitionGroupNode,
    FragmentNode,
    TeleportNode,
    SlotRenderNode,
    SlotPassNode,
]


class TestImmutability:
    def test_component_frozen(self) -> None:
        c = Component(path=Path("x.jinja"))
        with pytest.raises(AttributeError):
            c.path = Path("y.jinja")  # type: ignore[misc]

    def test_element_node_frozen(self) -> None:
        n = ElementNode(tag="div")
        with pytest.raises(AttributeError):
            n.tag = "span"  # type: ignore[misc]

    def test_component_node_frozen(self) -> None:
        n = ComponentNode(name="X")
        with pytest.raises(AttributeError):
            n.name = "Y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Type union
# ---------------------------------------------------------------------------


class TestNodeUnion:
    def test_text_node_is_node(self) -> None:
        n: Node = TextNode(content="hello")
        assert isinstance(n, TextNode)

    def test_element_node_is_node(self) -> None:
        n: Node = ElementNode(tag="div")
        assert isinstance(n, ElementNode)

    def test_component_node_is_node(self) -> None:
        n: Node = ComponentNode(name="X")
        assert isinstance(n, ComponentNode)


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------


class TestOutputTypes:
    def test_scoped_style(self) -> None:
        s = ScopedStyle(source=".card { color: red; }", hash="a1b2c3d")
        assert s.hash == "a1b2c3d"

    def test_compiled_component(self) -> None:
        cc = CompiledComponent(jinja_source="<div></div>", scope_hash="abc123")
        assert cc.css is None
        assert cc.alpine_data is None

    def test_compiled_component_frozen(self) -> None:
        cc = CompiledComponent(jinja_source="x")
        with pytest.raises(AttributeError):
            cc.jinja_source = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Root component
# ---------------------------------------------------------------------------


class TestComponent:
    def test_minimal_component(self) -> None:
        c = Component(
            path=Path("Button.jinja"), body=(TextNode("<button>Click</button>"),)
        )
        assert c.extends is None
        assert c.props is None
        assert c.style is None
        assert len(c.body) == 1

    def test_full_component(self) -> None:
        c = Component(
            path=Path("Todo.jinja"),
            extends=ExtendsDecl("layouts/Base.jinja"),
            from_imports=(FromImportDecl("pydantic", ("EmailStr",)),),
            imports=(ImportDecl(("Button",), "./Button.jinja"),),
            props=PropsDecl(name="TodoProps", fields=(PropField("text", "str"),)),
            slots=(SlotDecl("actions"),),
            stores=(StoreDecl("theme", "{ dark: false }"),),
            variables=(LetDecl("x", "1"), ConstDecl("Y", "2")),
            states=(StateDecl("count", "0"),),
            computed=(ComputedDecl("doubled", "count * 2"),),
            body=(ElementNode(tag="div"),),
            style=".card { color: red; }",
        )
        assert c.extends is not None
        assert len(c.from_imports) == 1
        assert len(c.imports) == 1
        assert c.props is not None
        assert len(c.slots) == 1
        assert len(c.stores) == 1
        assert len(c.variables) == 2
        assert len(c.states) == 1
        assert len(c.computed) == 1
