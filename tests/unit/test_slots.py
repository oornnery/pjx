"""Tests for pjx.slots — slot resolution."""

from pjx.ast_nodes import SlotDecl
from pjx.slots import resolve_slots


class TestResolveSlots:
    def test_slot_with_content(self) -> None:
        decls = (SlotDecl(name="header"),)
        result = resolve_slots(decls, {"header": "<h1>Title</h1>"})
        assert result["header"] == "<h1>Title</h1>"

    def test_slot_fallback(self) -> None:
        decls = (SlotDecl(name="footer", fallback="<p>Default</p>"),)
        result = resolve_slots(decls, {})
        assert result["footer"] == "<p>Default</p>"

    def test_slot_empty_when_no_fallback(self) -> None:
        decls = (SlotDecl(name="actions"),)
        result = resolve_slots(decls, {})
        assert result["actions"] == ""

    def test_default_slot_from_children(self) -> None:
        decls = (SlotDecl(name="default"),)
        result = resolve_slots(decls, {}, children="<p>Child content</p>")
        assert result["default"] == "<p>Child content</p>"

    def test_passed_overrides_fallback(self) -> None:
        decls = (SlotDecl(name="footer", fallback="<p>Default</p>"),)
        result = resolve_slots(decls, {"footer": "<p>Custom</p>"})
        assert result["footer"] == "<p>Custom</p>"

    def test_undeclared_slots_passed_through(self) -> None:
        decls = (SlotDecl(name="header"),)
        result = resolve_slots(decls, {"header": "H", "extra": "E"})
        assert result["extra"] == "E"

    def test_implicit_default_from_children(self) -> None:
        decls = ()  # no declarations
        result = resolve_slots(decls, {}, children="<p>Implicit</p>")
        assert result["default"] == "<p>Implicit</p>"

    def test_multiple_slots(self) -> None:
        decls = (
            SlotDecl(name="header"),
            SlotDecl(name="footer", fallback="<p>Default footer</p>"),
        )
        result = resolve_slots(decls, {"header": "<h1>Hi</h1>"})
        assert result["header"] == "<h1>Hi</h1>"
        assert result["footer"] == "<p>Default footer</p>"
