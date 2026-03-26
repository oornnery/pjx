"""Tests for pjx.props — dynamic Pydantic model generation."""

import pytest

from pjx.ast_nodes import PropField, PropsDecl
from pjx.errors import PropValidationError
from pjx.props import generate_props_model, separate_attrs, validate_props


class TestGeneratePropsModel:
    def test_required_field(self) -> None:
        decl = PropsDecl(name="P", fields=(PropField("name", "str"),))
        model = generate_props_model(decl)
        inst = model(name="Alice")
        assert inst.name == "Alice"

    def test_optional_field(self) -> None:
        decl = PropsDecl(name="P", fields=(PropField("age", "int", default="0"),))
        model = generate_props_model(decl)
        inst = model()
        assert inst.age == 0

    def test_nullable_field(self) -> None:
        decl = PropsDecl(
            name="P", fields=(PropField("bio", "str | None", default="None"),)
        )
        model = generate_props_model(decl)
        inst = model()
        assert inst.bio is None

    def test_list_factory(self) -> None:
        decl = PropsDecl(
            name="P", fields=(PropField("tags", "list[str]", default="[]"),)
        )
        model = generate_props_model(decl)
        inst1 = model()
        inst2 = model()
        assert inst1.tags == []
        # Verify they're different instances (not shared)
        assert inst1.tags is not inst2.tags

    def test_multiple_fields(self) -> None:
        decl = PropsDecl(
            name="UserProps",
            fields=(
                PropField("name", "str"),
                PropField("age", "int", default="0"),
                PropField("active", "bool", default="True"),
            ),
        )
        model = generate_props_model(decl)
        inst = model(name="Bob")
        assert inst.name == "Bob"
        assert inst.age == 0
        assert inst.active is True


class TestValidateProps:
    def test_valid(self) -> None:
        decl = PropsDecl(name="P", fields=(PropField("name", "str"),))
        model = generate_props_model(decl)
        result = validate_props(model, {"name": "Alice"})
        assert result.name == "Alice"

    def test_missing_required(self) -> None:
        decl = PropsDecl(name="P", fields=(PropField("name", "str"),))
        model = generate_props_model(decl)
        with pytest.raises(PropValidationError, match="validation failed"):
            validate_props(model, {})

    def test_invalid_type(self) -> None:
        decl = PropsDecl(name="P", fields=(PropField("age", "int"),))
        model = generate_props_model(decl)
        with pytest.raises(PropValidationError):
            validate_props(model, {"age": "not_a_number"})


class TestInvalidTypeExpr:
    def test_bad_type_expr(self) -> None:
        decl = PropsDecl(name="P", fields=(PropField("x", "InvalidType123"),))
        with pytest.raises(PropValidationError, match="invalid type"):
            generate_props_model(decl)


class TestSeparateAttrs:
    def test_no_props_decl_all_to_props(self) -> None:
        attrs = {"class": "btn", "id": "x"}
        props, extras = separate_attrs(None, attrs)
        assert props == {"class": "btn", "id": "x"}
        assert extras == {}

    def test_separates_declared_from_extras(self) -> None:
        decl = PropsDecl(
            name="P",
            fields=(
                PropField("variant", "str", default='"primary"'),
                PropField("size", "str", default='"md"'),
            ),
        )
        attrs = {"variant": "danger", "size": "lg", "class": "extra", "id": "btn1"}
        props, extras = separate_attrs(decl, attrs)
        assert props == {"variant": "danger", "size": "lg"}
        assert extras == {"class": "extra", "id": "btn1"}

    def test_all_declared_no_extras(self) -> None:
        decl = PropsDecl(name="P", fields=(PropField("title", "str"),))
        attrs = {"title": "Hello"}
        props, extras = separate_attrs(decl, attrs)
        assert props == {"title": "Hello"}
        assert extras == {}

    def test_all_extras_no_declared(self) -> None:
        decl = PropsDecl(name="P", fields=())
        attrs = {"class": "btn", "on:click": "go()"}
        props, extras = separate_attrs(decl, attrs)
        assert props == {}
        assert extras == {"class": "btn", "on:click": "go()"}

    def test_empty_attrs(self) -> None:
        decl = PropsDecl(name="P", fields=(PropField("x", "str"),))
        props, extras = separate_attrs(decl, {})
        assert props == {}
        assert extras == {}

    def test_generate_props_model_anonymous(self) -> None:
        decl = PropsDecl(fields=(PropField("name", "str"),))
        model = generate_props_model(decl)
        assert model.__name__ == "Props"
        instance = model(name="test")
        assert instance.name == "test"

    def test_boolean_attrs_separated(self) -> None:
        decl = PropsDecl(name="P", fields=(PropField("active", "bool"),))
        attrs = {"active": True, "disabled": True}
        props, extras = separate_attrs(decl, attrs)
        assert props == {"active": True}
        assert extras == {"disabled": True}
