"""Tests for pjx.typegen — TypeScript stub generation for Alpine.js stores."""

from pathlib import Path

from pjx.typegen import (
    _infer_fields_from_value,
    _infer_ts_type,
    generate_state_types,
    generate_store_types,
    write_types,
)


class TestInferTsType:
    def test_boolean(self) -> None:
        assert _infer_ts_type(False) == "boolean"

    def test_number_int(self) -> None:
        assert _infer_ts_type(42) == "number"

    def test_number_float(self) -> None:
        assert _infer_ts_type(3.14) == "number"

    def test_string(self) -> None:
        assert _infer_ts_type("hello") == "string"

    def test_list(self) -> None:
        assert _infer_ts_type([1, 2]) == "any[]"

    def test_dict(self) -> None:
        assert _infer_ts_type({"a": 1}) == "Record<string, any>"

    def test_none(self) -> None:
        assert _infer_ts_type(None) == "any"


class TestInferFieldsFromValue:
    def test_simple_object(self) -> None:
        fields = _infer_fields_from_value('{ dark: false, accent: "blue" }')
        names = [f[0] for f in fields]
        assert "dark" in names
        assert "accent" in names

    def test_json_object(self) -> None:
        fields = _infer_fields_from_value('{ "count": 0, "active": true }')
        assert ("count", "number") in fields
        assert ("active", "boolean") in fields

    def test_empty_object(self) -> None:
        fields = _infer_fields_from_value("{}")
        assert fields == []

    def test_non_object(self) -> None:
        fields = _infer_fields_from_value("[]")
        assert fields == []


class TestGenerateStoreTypes:
    def test_generates_from_template(self, tmp_path: Path) -> None:
        tpl = tmp_path / "Theme.jinja"
        tpl.write_text(
            '---\nstore theme = { dark: false, accent: "blue" }\n---\n<div>theme</div>'
        )

        result = generate_store_types(tmp_path)
        assert "interface AlpineStores" in result
        assert "theme:" in result
        assert "dark:" in result

    def test_empty_dir(self, tmp_path: Path) -> None:
        assert generate_store_types(tmp_path) == ""

    def test_nonexistent_dir(self, tmp_path: Path) -> None:
        assert generate_store_types(tmp_path / "nope") == ""


class TestGenerateStateTypes:
    def test_generates_from_state(self, tmp_path: Path) -> None:
        tpl = tmp_path / "Counter.jinja"
        tpl.write_text("---\nstate count = 0\n---\n<div>{{ count }}</div>")

        result = generate_state_types(tmp_path)
        assert "CounterState" in result
        assert "count:" in result

    def test_empty_dir(self, tmp_path: Path) -> None:
        assert generate_state_types(tmp_path) == ""


class TestWriteTypes:
    def test_writes_file(self, tmp_path: Path) -> None:
        tpl_dir = tmp_path / "templates"
        tpl_dir.mkdir()
        (tpl_dir / "Store.jinja").write_text(
            '---\nstore app = { version: "1.0" }\n---\n<div>app</div>'
        )

        out = tmp_path / "types"
        path = write_types(tpl_dir, out)

        assert path is not None
        assert path.exists()
        assert "AlpineStores" in path.read_text()

    def test_returns_none_when_no_stores(self, tmp_path: Path) -> None:
        tpl_dir = tmp_path / "templates"
        tpl_dir.mkdir()
        (tpl_dir / "Plain.jinja").write_text("---\n---\n<div>plain</div>")

        path = write_types(tpl_dir, tmp_path / "types")
        assert path is None
