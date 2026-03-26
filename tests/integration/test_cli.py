"""Integration tests for PJX CLI commands."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from pjx.cli import app

runner = CliRunner()


class TestInit:
    def test_creates_dirs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert "initialized" in result.output.lower()
        assert (tmp_path / "templates" / "pages").exists()
        assert (tmp_path / "templates" / "components").exists()
        assert (tmp_path / "templates" / "layouts").exists()
        assert (tmp_path / "static").exists()

    def test_creates_toml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        assert (tmp_path / "pjx.toml").exists()

    def test_creates_base_layout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        layout = tmp_path / "templates" / "layouts" / "Base.jinja"
        assert layout.exists()
        assert "Slot:content" in layout.read_text()


class TestCheck:
    def test_check_valid_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        tpl = tmp_path / "templates"
        tpl.mkdir()
        (tpl / "test.jinja").write_text("<div>hello</div>")

        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "no errors" in result.output.lower()

    def test_check_reports_errors(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        tpl = tmp_path / "templates"
        tpl.mkdir()
        # Invalid frontmatter
        (tpl / "bad.jinja").write_text("---\nfoobar xyz\n---\n<div></div>")

        result = runner.invoke(app, ["check"])
        assert result.exit_code == 1


class TestBuild:
    def test_build_compiles_all(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        tpl = tmp_path / "templates"
        tpl.mkdir()
        (tpl / "page.jinja").write_text("<div>hello</div>")

        result = runner.invoke(app, ["build"])
        assert result.exit_code == 0
        assert "compiled" in result.output.lower()

    def test_build_bundles_css(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        tpl = tmp_path / "templates"
        tpl.mkdir()
        (tpl / "styled.jinja").write_text(
            "<style scoped>.card { color: red; }</style>\n<div>hello</div>"
        )

        result = runner.invoke(app, ["build"])
        assert result.exit_code == 0
        css_file = tmp_path / "static" / "css" / "pjx-components.css"
        assert css_file.exists()
        assert "data-pjx-" in css_file.read_text()
