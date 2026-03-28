"""Tests for pjx.checker — static analysis of components."""

from pathlib import Path

from pjx.ast_nodes import (
    Component,
    ComponentNode,
    ComputedDecl,
    ImportDecl,
    LetDecl,
    PropField,
    PropsDecl,
    SlotDecl,
    StateDecl,
    TextNode,
)
from pjx.checker import (
    check_all,
    check_computed_cycles,
    check_imports,
    check_prop_defaults,
    check_props,
    check_slots,
    check_undefined_vars,
    check_unused_imports,
)
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


class TestCheckPropDefaults:
    def test_valid_default_no_error(self) -> None:
        comp = _component(
            props=PropsDecl(
                fields=(PropField("count", "int", default="0"),),
            ),
        )
        errors = check_prop_defaults(comp)
        assert errors == []

    def test_invalid_default_reported(self) -> None:
        comp = _component(
            props=PropsDecl(
                fields=(PropField("x", "str", default="def ???"),),
            ),
        )
        errors = check_prop_defaults(comp)
        assert len(errors) == 1
        assert "x" in str(errors[0])

    def test_no_props_no_error(self) -> None:
        comp = _component()
        errors = check_prop_defaults(comp)
        assert errors == []

    def test_no_default_no_error(self) -> None:
        comp = _component(
            props=PropsDecl(fields=(PropField("name", "str"),)),
        )
        errors = check_prop_defaults(comp)
        assert errors == []


class TestCheckUnusedImports:
    def test_unused_import_reported(self) -> None:
        comp = _component(
            imports=(ImportDecl(names=("Button",), source="./Button.jinja"),),
            body=(),
        )
        errors = check_unused_imports(comp)
        assert len(errors) == 1
        assert "Button" in str(errors[0])

    def test_used_import_no_error(self) -> None:
        comp = _component(
            imports=(ImportDecl(names=("Button",), source="./Button.jinja"),),
            body=(ComponentNode(name="Button", attrs={}),),
        )
        errors = check_unused_imports(comp)
        assert errors == []

    def test_no_imports_no_error(self) -> None:
        comp = _component()
        errors = check_unused_imports(comp)
        assert errors == []

    def test_partial_usage_reports_unused(self) -> None:
        comp = _component(
            imports=(
                ImportDecl(names=("Button",), source="./Button.jinja"),
                ImportDecl(names=("Card",), source="./Card.jinja"),
            ),
            body=(ComponentNode(name="Button", attrs={}),),
        )
        errors = check_unused_imports(comp)
        assert len(errors) == 1
        assert "Card" in str(errors[0])


class TestCheckComputedCycles:
    def test_no_cycle_no_error(self) -> None:
        comp = _component(
            computed=(
                ComputedDecl("a", "x + 1"),
                ComputedDecl("b", "a + 2"),
            ),
            states=(StateDecl("x", "0"),),
        )
        errors = check_computed_cycles(comp)
        assert errors == []

    def test_direct_cycle_reported(self) -> None:
        comp = _component(
            computed=(
                ComputedDecl("a", "b + 1"),
                ComputedDecl("b", "a + 1"),
            ),
        )
        errors = check_computed_cycles(comp)
        assert len(errors) >= 1
        assert any("circular" in str(e) for e in errors)

    def test_self_reference_no_false_positive(self) -> None:
        """Self-reference is excluded from the graph (not a cross-dependency)."""
        comp = _component(
            computed=(ComputedDecl("x", "x + 1"),),
        )
        errors = check_computed_cycles(comp)
        assert errors == []

    def test_no_computed_no_error(self) -> None:
        comp = _component()
        errors = check_computed_cycles(comp)
        assert errors == []

    def test_triangle_cycle(self) -> None:
        comp = _component(
            computed=(
                ComputedDecl("a", "c"),
                ComputedDecl("b", "a"),
                ComputedDecl("c", "b"),
            ),
        )
        errors = check_computed_cycles(comp)
        assert len(errors) >= 1


class TestCheckUndefinedVars:
    def test_declared_state_no_error(self) -> None:
        comp = _component(
            states=(StateDecl("count", "0"),),
            computed=(ComputedDecl("doubled", "count * 2"),),
        )
        errors = check_undefined_vars(comp)
        assert errors == []

    def test_undefined_var_in_computed(self) -> None:
        comp = _component(
            computed=(ComputedDecl("doubled", "unknown_var * 2"),),
        )
        errors = check_undefined_vars(comp)
        assert len(errors) == 1
        assert "unknown_var" in str(errors[0])

    def test_props_are_declared(self) -> None:
        comp = _component(
            props=PropsDecl(fields=(PropField("name", "str"),)),
            variables=(LetDecl("greeting", "name"),),
        )
        errors = check_undefined_vars(comp)
        assert errors == []

    def test_builtins_not_flagged(self) -> None:
        comp = _component(
            computed=(ComputedDecl("n", "len(items)"),),
            states=(StateDecl("items", "[]"),),
        )
        errors = check_undefined_vars(comp)
        assert errors == []

    def test_attribute_access_only_checks_root(self) -> None:
        comp = _component(
            props=PropsDecl(fields=(PropField("user", "dict"),)),
            computed=(ComputedDecl("name", "user.name"),),
        )
        errors = check_undefined_vars(comp)
        assert errors == []

    def test_no_expressions_no_error(self) -> None:
        comp = _component()
        errors = check_undefined_vars(comp)
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
