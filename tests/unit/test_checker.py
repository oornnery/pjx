"""Tests for pjx.checker — static analysis of components."""

from pathlib import Path

from pjx.ast_nodes import (
    Component,
    ComponentNode,
    ImportDecl,
    PropField,
    PropsDecl,
    SlotDecl,
    TextNode,
)
from pjx.checker import check_all, check_imports, check_props, check_slots
from pjx.registry import ComponentRegistry


def _component(path: str = "test.jinja", **kwargs: object) -> Component:
    defaults: dict[str, object] = {"path": Path(path), "body": ()}
    defaults.update(kwargs)
    return Component(**defaults)  # type: ignore[arg-type]


def _registry_with(*components: tuple[str, Component]) -> ComponentRegistry:
    registry = ComponentRegistry()
    for name, comp in components:
        registry._by_name[name] = comp
    return registry


class TestCheckImports:
    def test_missing_import_reported(self, tmp_path: Path) -> None:
        parent = _component(
            path=str(tmp_path / "page.jinja"),
            imports=(ImportDecl(names=("Missing",), source="./Missing.jinja"),),
        )
        registry = ComponentRegistry([tmp_path])
        errors = check_imports(parent, registry)
        assert len(errors) == 1
        assert "Missing" in str(errors[0])

    def test_valid_import_no_error(self, tmp_path: Path) -> None:
        child_path = tmp_path / "Button.jinja"
        child_path.write_text("<button>click</button>")
        parent = _component(
            path=str(tmp_path / "page.jinja"),
            imports=(ImportDecl(names=("Button",), source="./Button.jinja"),),
        )
        registry = ComponentRegistry([tmp_path])
        errors = check_imports(parent, registry)
        assert errors == []


class TestCheckProps:
    def test_missing_required_prop(self) -> None:
        child = _component(
            path="Button.jinja",
            props=PropsDecl(
                name="ButtonProps",
                fields=(PropField("label", "str"),),
            ),
        )
        registry = _registry_with(("Button", child))
        parent = _component(
            imports=(ImportDecl(names=("Button",), source="./Button.jinja"),),
            body=(ComponentNode(name="Button", attrs={}),),
        )
        errors = check_props(parent, registry)
        assert len(errors) == 1
        assert "label" in str(errors[0])

    def test_required_prop_passed(self) -> None:
        child = _component(
            path="Button.jinja",
            props=PropsDecl(
                name="ButtonProps",
                fields=(PropField("label", "str"),),
            ),
        )
        registry = _registry_with(("Button", child))
        parent = _component(
            imports=(ImportDecl(names=("Button",), source="./Button.jinja"),),
            body=(ComponentNode(name="Button", attrs={"label": "Click me"}),),
        )
        errors = check_props(parent, registry)
        assert errors == []

    def test_optional_prop_not_required(self) -> None:
        child = _component(
            path="Card.jinja",
            props=PropsDecl(
                name="CardProps",
                fields=(PropField("title", "str", default='"untitled"'),),
            ),
        )
        registry = _registry_with(("Card", child))
        parent = _component(
            imports=(ImportDecl(names=("Card",), source="./Card.jinja"),),
            body=(ComponentNode(name="Card", attrs={}),),
        )
        errors = check_props(parent, registry)
        assert errors == []

    def test_unknown_component_no_error(self) -> None:
        registry = _registry_with()
        parent = _component(
            body=(ComponentNode(name="Unknown", attrs={}),),
        )
        errors = check_props(parent, registry)
        assert errors == []


class TestCheckSlots:
    def test_unknown_slot_reported(self) -> None:
        child = _component(
            path="Card.jinja",
            slots=(SlotDecl(name="header"),),
        )
        registry = _registry_with(("Card", child))
        parent = _component(
            imports=(ImportDecl(names=("Card",), source="./Card.jinja"),),
            body=(
                ComponentNode(
                    name="Card",
                    slots={"footer": (TextNode("foot"),)},
                ),
            ),
        )
        errors = check_slots(parent, registry)
        assert len(errors) == 1
        assert "footer" in str(errors[0])

    def test_declared_slot_no_error(self) -> None:
        child = _component(
            path="Card.jinja",
            slots=(SlotDecl(name="header"),),
        )
        registry = _registry_with(("Card", child))
        parent = _component(
            imports=(ImportDecl(names=("Card",), source="./Card.jinja"),),
            body=(
                ComponentNode(
                    name="Card",
                    slots={"header": (TextNode("head"),)},
                ),
            ),
        )
        errors = check_slots(parent, registry)
        assert errors == []

    def test_default_slot_always_valid(self) -> None:
        child = _component(path="Box.jinja", slots=())
        registry = _registry_with(("Box", child))
        parent = _component(
            imports=(ImportDecl(names=("Box",), source="./Box.jinja"),),
            body=(
                ComponentNode(
                    name="Box",
                    slots={"default": (TextNode("content"),)},
                ),
            ),
        )
        errors = check_slots(parent, registry)
        assert errors == []


class TestCheckAll:
    def test_combines_all_checks(self) -> None:
        child = _component(
            path="Btn.jinja",
            props=PropsDecl(name="P", fields=(PropField("label", "str"),)),
            slots=(SlotDecl(name="icon"),),
        )
        registry = _registry_with(("Btn", child))
        parent = _component(
            imports=(ImportDecl(names=("Btn",), source="./Btn.jinja"),),
            body=(
                ComponentNode(
                    name="Btn",
                    attrs={},  # missing required 'label'
                    slots={"badge": (TextNode("!"),)},  # unknown slot
                ),
            ),
        )
        errors = check_all(parent, registry)
        messages = [str(e) for e in errors]
        assert any("label" in m for m in messages)
        assert any("badge" in m for m in messages)
