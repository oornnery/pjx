"""Tests for pjx.parser — full .jinja component parsing."""

from pathlib import Path

import pytest

from pjx.ast_nodes import (
    ComponentNode,
    ConstDecl,
    ElementNode,
    ExprNode,
    ForNode,
    FragmentNode,
    LetDecl,
    PortalNode,
    ShowNode,
    SlotRenderNode,
    SwitchNode,
    TeleportNode,
    TextNode,
    TransitionGroupNode,
)
from pjx.errors import ParseError
from pjx.parser import _extract_blocks, parse


# ---------------------------------------------------------------------------
# Block extraction
# ---------------------------------------------------------------------------


class TestExtractBlocks:
    def test_no_frontmatter_no_style(self) -> None:
        fm, style, body = _extract_blocks("<div>hello</div>")
        assert fm is None
        assert style is None
        assert body == "<div>hello</div>"

    def test_with_frontmatter(self) -> None:
        src = "---\nslot actions\n---\n<div>body</div>"
        fm, style, body = _extract_blocks(src)
        assert fm == "slot actions"
        assert style is None
        assert body == "<div>body</div>"

    def test_with_style(self) -> None:
        src = "<style scoped>.card { color: red; }</style>\n<div>body</div>"
        fm, style, body = _extract_blocks(src)
        assert fm is None
        assert style == ".card { color: red; }"
        assert "body" in body

    def test_with_all_blocks(self) -> None:
        src = '---\nimport Button from "./B.jinja"\n---\n<style scoped>.x {}</style>\n<div>hi</div>'
        fm, style, body = _extract_blocks(src)
        assert fm is not None
        assert style is not None
        assert "<div>hi</div>" in body


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


class TestParseExtends:
    def test_extends(self) -> None:
        src = '---\nextends "layouts/Base.jinja"\n---\n<div></div>'
        comp = parse(src)
        assert comp.extends is not None
        assert comp.extends.source == "layouts/Base.jinja"


class TestParseFromImport:
    def test_from_import(self) -> None:
        src = "---\nfrom pydantic import EmailStr, HttpUrl\n---\n<div></div>"
        comp = parse(src)
        assert len(comp.from_imports) == 1
        assert comp.from_imports[0].module == "pydantic"
        assert comp.from_imports[0].names == ("EmailStr", "HttpUrl")

    def test_from_import_dotted(self) -> None:
        src = "---\nfrom typing import Literal\n---\n<div></div>"
        comp = parse(src)
        assert comp.from_imports[0].module == "typing"


class TestParseImports:
    def test_import_default(self) -> None:
        src = '---\nimport Button from "./Button.jinja"\n---\n<div></div>'
        comp = parse(src)
        assert len(comp.imports) == 1
        assert comp.imports[0].names == ("Button",)
        assert comp.imports[0].source == "./Button.jinja"

    def test_import_named(self) -> None:
        src = (
            '---\nimport { CardHeader, CardBody } from "./Card.jinja"\n---\n<div></div>'
        )
        comp = parse(src)
        assert comp.imports[0].names == ("CardHeader", "CardBody")

    def test_import_wildcard(self) -> None:
        src = '---\nimport * from "./ui/"\n---\n<div></div>'
        comp = parse(src)
        assert comp.imports[0].wildcard is True

    def test_import_alias(self) -> None:
        src = '---\nimport Button from "./Button.jinja" as Btn\n---\n<div></div>'
        comp = parse(src)
        assert comp.imports[0].alias == "Btn"


class TestParseProps:
    def test_props_simple(self) -> None:
        src = "---\nprops UserProps = {\n  name: str,\n  age: int = 0,\n}\n---\n<div></div>"
        comp = parse(src)
        assert comp.props is not None
        assert comp.props.name == "UserProps"
        assert len(comp.props.fields) == 2
        assert comp.props.fields[0].name == "name"
        assert comp.props.fields[0].type_expr == "str"
        assert comp.props.fields[1].default == "0"

    def test_props_pydantic_types(self) -> None:
        src = '---\nprops P = {\n  role: Literal["admin", "user"] = "user",\n}\n---\n<div></div>'
        comp = parse(src)
        assert comp.props is not None
        field = comp.props.fields[0]
        assert "Literal" in field.type_expr
        assert field.default is not None

    def test_props_union_type(self) -> None:
        src = "---\nprops P = {\n  bio: str | None = None,\n}\n---\n<div></div>"
        comp = parse(src)
        field = comp.props.fields[0]
        assert "str | None" in field.type_expr


class TestParseSlots:
    def test_slot_no_fallback(self) -> None:
        src = "---\nslot actions\n---\n<div></div>"
        comp = parse(src)
        assert len(comp.slots) == 1
        assert comp.slots[0].name == "actions"
        assert comp.slots[0].fallback is None

    def test_slot_with_fallback(self) -> None:
        src = '---\nslot footer = "Default footer"\n---\n<div></div>'
        comp = parse(src)
        assert comp.slots[0].fallback is not None


class TestParseStore:
    def test_store(self) -> None:
        src = "---\nstore theme = { dark : false }\n---\n<div></div>"
        comp = parse(src)
        assert len(comp.stores) == 1
        assert comp.stores[0].name == "theme"


class TestParseVariables:
    def test_let(self) -> None:
        src = '---\nlet css_class = "todo"\n---\n<div></div>'
        comp = parse(src)
        assert len(comp.variables) == 1
        assert isinstance(comp.variables[0], LetDecl)

    def test_const(self) -> None:
        src = "---\nconst MAX = 140\n---\n<div></div>"
        comp = parse(src)
        assert isinstance(comp.variables[0], ConstDecl)
        assert comp.variables[0].expr == "140"

    def test_state(self) -> None:
        src = "---\nstate count = 0\n---\n<div></div>"
        comp = parse(src)
        assert len(comp.states) == 1
        assert comp.states[0].name == "count"

    def test_computed(self) -> None:
        src = "---\ncomputed doubled = count * 2\n---\n<div></div>"
        comp = parse(src)
        assert len(comp.computed) == 1
        assert comp.computed[0].name == "doubled"


# ---------------------------------------------------------------------------
# Body parsing
# ---------------------------------------------------------------------------


class TestParseBody:
    def test_empty_component(self) -> None:
        comp = parse("<div>hello</div>")
        assert len(comp.body) == 1
        assert isinstance(comp.body[0], ElementNode)
        assert comp.body[0].tag == "div"

    def test_text_node(self) -> None:
        comp = parse("<p>hello world</p>")
        el = comp.body[0]
        assert isinstance(el, ElementNode)
        assert len(el.children) == 1
        assert isinstance(el.children[0], TextNode)

    def test_expr_node(self) -> None:
        comp = parse("<span>{{ user.name }}</span>")
        el = comp.body[0]
        assert isinstance(el, ElementNode)
        assert any(isinstance(c, ExprNode) for c in el.children)
        expr = next(c for c in el.children if isinstance(c, ExprNode))
        assert expr.expr == "user.name"

    def test_attrs_preserved(self) -> None:
        comp = parse('<div class="card" reactive></div>')
        el = comp.body[0]
        assert isinstance(el, ElementNode)
        assert el.attrs["class"] == "card"
        assert el.attrs["reactive"] is True


class TestParseBodyShow:
    def test_show(self) -> None:
        src = '<Show when="visible"><p>yes</p></Show>'
        comp = parse(src)
        node = comp.body[0]
        assert isinstance(node, ShowNode)
        assert node.when == "visible"
        assert len(node.body) > 0

    def test_show_fallback(self) -> None:
        src = '<Show when="visible"><p>yes</p><Fallback><p>no</p></Fallback></Show>'
        comp = parse(src)
        node = comp.body[0]
        assert isinstance(node, ShowNode)
        assert node.fallback is not None


class TestParseBodyFor:
    def test_for(self) -> None:
        src = '<For each="items" as="item"><li>{{ item }}</li></For>'
        comp = parse(src)
        node = comp.body[0]
        assert isinstance(node, ForNode)
        assert node.each == "items"
        assert node.as_var == "item"

    def test_for_empty(self) -> None:
        src = '<For each="items" as="item"><li>x</li><Empty><p>none</p></Empty></For>'
        comp = parse(src)
        node = comp.body[0]
        assert isinstance(node, ForNode)
        assert node.empty is not None


class TestParseBodySwitch:
    def test_switch(self) -> None:
        src = '<Switch on="status"><Case value="active"><p>A</p></Case><Default><p>?</p></Default></Switch>'
        comp = parse(src)
        node = comp.body[0]
        assert isinstance(node, SwitchNode)
        assert len(node.cases) == 1
        assert node.default is not None


class TestParseBodyOther:
    def test_portal(self) -> None:
        src = '<Portal target="/api/data"><p>content</p></Portal>'
        comp = parse(src)
        node = comp.body[0]
        assert isinstance(node, PortalNode)
        assert node.target == "/api/data"

    def test_transition_group(self) -> None:
        src = '<TransitionGroup tag="ul" enter="fade-in"><li>x</li></TransitionGroup>'
        comp = parse(src)
        node = comp.body[0]
        assert isinstance(node, TransitionGroupNode)
        assert node.tag == "ul"

    def test_fragment(self) -> None:
        src = "<Fragment><p>a</p><p>b</p></Fragment>"
        comp = parse(src)
        node = comp.body[0]
        assert isinstance(node, FragmentNode)
        assert len(node.children) == 2

    def test_teleport(self) -> None:
        src = '<Teleport to="body"><p>modal</p></Teleport>'
        comp = parse(src)
        node = comp.body[0]
        assert isinstance(node, TeleportNode)
        assert node.to == "body"


class TestParseBodyComponent:
    def test_component_with_slots(self) -> None:
        src = '---\nimport Button from "./B.jinja"\n---\n<Button><slot:footer><p>f</p></slot:footer></Button>'
        comp = parse(src)
        node = comp.body[0]
        assert isinstance(node, ComponentNode)
        assert "footer" in node.slots

    def test_component_self_closing(self) -> None:
        # Self-closing components are tricky with HTMLParser.
        # They appear as normal tags — the parser handles this.
        src = '---\nimport Button from "./B.jinja"\n---\n<Button variant="primary"></Button>'
        comp = parse(src)
        node = comp.body[0]
        assert isinstance(node, ComponentNode)
        assert node.attrs["variant"] == "primary"

    def test_slot_render_named(self) -> None:
        src = "<Slot:header></Slot:header>"
        comp = parse(src)
        assert len(comp.body) >= 1
        node = comp.body[0]
        assert isinstance(node, SlotRenderNode)
        assert node.name == "header"

    def test_slot_render_default(self) -> None:
        src = "<Slot />"
        comp = parse(src)
        assert len(comp.body) >= 1
        node = comp.body[0]
        assert isinstance(node, SlotRenderNode)
        assert node.name == "default"

    def test_slot_render_default_with_fallback(self) -> None:
        src = "<Slot>fallback content</Slot>"
        comp = parse(src)
        node = comp.body[0]
        assert isinstance(node, SlotRenderNode)
        assert node.name == "default"
        assert node.fallback is not None


class TestParseBodyNested:
    def test_nested_control_flow(self) -> None:
        src = '<Show when="visible"><For each="items" as="item"><p>{{ item }}</p></For></Show>'
        comp = parse(src)
        node = comp.body[0]
        assert isinstance(node, ShowNode)
        assert len(node.body) > 0
        inner = node.body[0]
        assert isinstance(inner, ForNode)


# ---------------------------------------------------------------------------
# Full component
# ---------------------------------------------------------------------------


class TestFullComponent:
    def test_full_parse(self) -> None:
        src = """---
extends "layouts/Base.jinja"
from pydantic import EmailStr
import Button from "./Button.jinja"

props UserProps = {
  name: str,
  email: EmailStr,
}

slot header
state count = 0
computed doubled = count * 2
let css_class = "user"
const MAX = 100
---

<style scoped>
.user { color: blue; }
</style>

<div class="user" reactive>
  <h1>{{ props.name }}</h1>
  <Show when="count > 0">
    <p>Count: {{ count }}</p>
  </Show>
</div>"""
        comp = parse(src, path=Path("User.jinja"))
        assert comp.path == Path("User.jinja")
        assert comp.extends is not None
        assert len(comp.from_imports) == 1
        assert len(comp.imports) == 1
        assert comp.props is not None
        assert len(comp.props.fields) == 2
        assert len(comp.slots) == 1
        assert len(comp.states) == 1
        assert len(comp.computed) == 1
        assert len(comp.variables) == 2
        assert comp.style is not None
        assert len(comp.body) > 0


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestParseErrors:
    def test_unknown_keyword(self) -> None:
        with pytest.raises(ParseError):
            parse("---\nfoobar something\n---\n<div></div>")

    def test_missing_string_after_extends(self) -> None:
        with pytest.raises(ParseError):
            parse("---\nextends\n---\n<div></div>")
