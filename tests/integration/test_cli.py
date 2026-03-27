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
        assert (tmp_path / "app" / "templates" / "pages").exists()
        assert (tmp_path / "app" / "templates" / "components").exists()
        assert (tmp_path / "app" / "templates" / "layouts").exists()
        assert (tmp_path / "app" / "static").exists()

    def test_creates_toml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        assert (tmp_path / "pjx.toml").exists()

    def test_creates_app_package(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        assert (tmp_path / "app" / "__init__.py").exists()
        assert (tmp_path / "app" / "main.py").exists()
        assert (tmp_path / "app" / "core" / "config.py").exists()
        assert (tmp_path / "app" / "models" / "__init__.py").exists()
        assert (tmp_path / "app" / "services" / "__init__.py").exists()
        assert (tmp_path / "app" / "pages" / "__init__.py").exists()
        assert (tmp_path / "app" / "api" / "v1" / "__init__.py").exists()
        assert (tmp_path / "app" / "middleware" / "__init__.py").exists()

    def test_creates_base_layout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        layout = tmp_path / "app" / "templates" / "layouts" / "Base.jinja"
        assert layout.exists()
        content = layout.read_text()
        assert "<Slot />" in content
        assert "props" in content

    def test_init_subdirectory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init", "myapp"])
        assert result.exit_code == 0
        assert (tmp_path / "myapp" / "pjx.toml").exists()
        assert (tmp_path / "myapp" / "app" / "main.py").exists()
        assert (tmp_path / "myapp" / "app" / "__init__.py").exists()
        assert (tmp_path / "myapp" / "app" / "core" / "config.py").exists()
        assert (tmp_path / "myapp" / "app" / "api" / "v1" / "__init__.py").exists()
        assert (
            tmp_path / "myapp" / "app" / "templates" / "pages" / "Home.jinja"
        ).exists()
        assert (
            tmp_path / "myapp" / "app" / "templates" / "layouts" / "Base.jinja"
        ).exists()

    def test_creates_example_app_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        assert (tmp_path / "app" / "services" / "counter.py").exists()
        assert (tmp_path / "app" / "pages" / "routes.py").exists()
        assert (tmp_path / "app" / "templates" / "pages" / "Home.jinja").exists()
        assert (tmp_path / "app" / "templates" / "pages" / "About.jinja").exists()
        assert (
            tmp_path / "app" / "templates" / "components" / "Counter.jinja"
        ).exists()
        assert (tmp_path / "app" / "static" / "css" / "style.css").exists()

    def test_init_existing_dir_no_overwrite(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        (tmp_path / "pjx.toml").write_text("custom = true\n")
        runner.invoke(app, ["init"])
        assert "custom" in (tmp_path / "pjx.toml").read_text()


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
