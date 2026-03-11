from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from pjx.cli import app


runner = CliRunner()


def test_cli_check_supports_import_target_and_json_output() -> None:
    result = runner.invoke(app, ["check", "exemples.main:pjx", "--format", "json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["errors"] == 0
    assert payload["files_checked"] >= 1
    assert payload["routes_checked"] >= 1
    assert any(path.endswith("exemples/templates") for path in payload["template_roots"])


def test_cli_check_renders_numbered_validation_codes(tmp_path: Path) -> None:
    template_path = tmp_path / "Broken.jinja"
    template_path.write_text(
        '{% import "components/Missing.jinja" as Missing %}\n'
        "{% component Broken %}\n"
        "<Missing />\n"
        "{% endcomponent %}\n"
    )

    result = runner.invoke(app, ["check", str(template_path)])

    assert result.exit_code == 1
    assert "[105] missing_import" in result.stdout
    assert "Validation map:" in result.stdout


def test_cli_format_can_check_and_write_template_file(tmp_path: Path) -> None:
    template_path = tmp_path / "Demo.jinja"
    template_path.write_text(
        '{% component Demo %}\n'
        '{% props title: str, count: int = 0 %}\n'
        '<section>{{ title }}</section>\n'
        '{% endcomponent %}\n'
    )

    check_result = runner.invoke(app, ["format", str(template_path), "--check"])

    assert check_result.exit_code == 1
    assert "would format" in check_result.stdout

    write_result = runner.invoke(app, ["format", str(template_path)])

    assert write_result.exit_code == 0
    assert "formatted" in write_result.stdout
    assert template_path.read_text() == (
        "{% component Demo %}\n\n"
        "  {% props\n"
        "    title: str,\n"
        "    count: int = 0\n"
        "  %}\n\n"
        "<section>{{ title }}</section>\n"
        "{% endcomponent %}\n"
    )

    stable_result = runner.invoke(app, ["format", str(template_path), "--check"])

    assert stable_result.exit_code == 0
    assert "Changed: 0" in stable_result.stdout
