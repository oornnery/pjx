from pathlib import Path

from typer.testing import CliRunner

from pjx.assets import VendorAssetWrite, VendorBuildResult
from pjx.cli import app

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def test_check_valid_fixtures():
    result = runner.invoke(app, ["check", str(FIXTURES / "basic")], color=False)
    assert result.exit_code == 0
    assert "template(s) valid" in result.output


def test_check_valid_fixtures_verbose():
    result = runner.invoke(app, ["check", str(FIXTURES / "basic"), "--verbose"], color=False)
    assert result.exit_code == 0
    assert "ok:" in result.output


def test_check_single_file():
    result = runner.invoke(app, ["check", str(FIXTURES / "basic" / "input.jinja")], color=False)
    assert result.exit_code == 0


def test_check_nonexistent_path():
    result = runner.invoke(app, ["check", str(FIXTURES / "does_not_exist")], color=False)
    assert result.exit_code == 1
    assert "error: path not found" in result.output


def test_check_all_fixtures():
    result = runner.invoke(app, ["check", str(FIXTURES)], color=False)
    assert result.exit_code == 0


def test_check_fix_repairs_import_path(tmp_path):
    components = tmp_path / "components"
    pages = tmp_path / "pages"
    components.mkdir()
    pages.mkdir()

    (components / "Card.jinja").write_text("<div>Card</div>")
    template = pages / "home.jinja"
    template.write_text("---\nfrom missing import Card\n---\n\n<Card />\n")

    result = runner.invoke(app, ["check", str(tmp_path), "--fix"], color=False)
    assert result.exit_code == 0
    assert "Applied 1 technical fix" in result.output
    assert "All 2 template(s) valid." in result.output
    assert "from components import Card" in template.read_text()


def test_format_check_mode(tmp_path):
    template = tmp_path / "test.jinja"
    template.write_text("<h1>no frontmatter</h1>")

    result = runner.invoke(app, ["format", str(template), "--check"], color=False)
    assert result.exit_code == 0


def test_format_applies(tmp_path):
    template = tmp_path / "test.jinja"
    source = "---\nprops:\n  x: int\n\nfrom a import B\n---\n<h1>hi</h1>\n"
    template.write_text(source)

    result = runner.invoke(app, ["format", str(template)], color=False)
    assert result.exit_code == 0
    assert "reformatted" in result.output.lower()

    lines = template.read_text().split("\n")
    import_idx = next(i for i, line in enumerate(lines) if "from" in line)
    props_idx = next(i for i, line in enumerate(lines) if line.strip() == "props:")
    assert import_idx < props_idx


def test_format_nonexistent():
    result = runner.invoke(app, ["format", "/nonexistent"], color=False)
    assert result.exit_code == 1
    assert "error: path not found" in result.output


def test_sitemap_generates(tmp_path):
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "home.jinja").write_text("<h1>Home</h1>")
    (pages / "about.jinja").write_text("<h1>About</h1>")

    output = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "sitemap",
            str(tmp_path),
            "--base-url",
            "https://example.com",
            "--output",
            str(output),
        ],
        color=False,
    )

    assert result.exit_code == 0
    assert (output / "sitemap.xml").exists()
    assert (output / "robots.txt").exists()

    xml = (output / "sitemap.xml").read_text()
    assert "https://example.com/" in xml
    assert "https://example.com/about" in xml


def test_skills_requires_target():
    result = runner.invoke(app, ["skills"], color=False)
    assert result.exit_code == 2
    assert "choose at least one target" in result.output


def test_skills_install_claude(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["skills", "--claude"], color=False)
    assert result.exit_code == 0

    skill_dir = tmp_path / ".claude" / "skills" / "pjx"
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "references" / "cli.md").exists()
    assert "PJX Skill" in (skill_dir / "SKILL.md").read_text()


def test_skills_install_agents(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["skills", "--agents"], color=False)
    assert result.exit_code == 0

    skill_dir = tmp_path / ".agents" / "skills" / "pjx"
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "references" / "syntax.md").exists()
    assert "Template Syntax" in (skill_dir / "references" / "syntax.md").read_text()


def test_skills_install_both_targets(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["skills", "--claude", "--agents"], color=False)
    assert result.exit_code == 0

    assert (tmp_path / ".claude" / "skills" / "pjx" / "SKILL.md").exists()
    assert (tmp_path / ".agents" / "skills" / "pjx" / "SKILL.md").exists()


def test_demo_help():
    result = runner.invoke(app, ["demo", "--help"], color=False)
    assert result.exit_code == 0
    assert "demo" in result.output.lower()


def test_assets_build_unknown_provider(monkeypatch, tmp_path):
    from pjx import cli as cli_module

    monkeypatch.setattr(
        cli_module,
        "available_asset_provider_names",
        lambda: ("htmx", "stimulus"),
    )

    result = runner.invoke(
        app,
        ["assets", "build", str(tmp_path), "--provider", "missing"],
        color=False,
    )

    assert result.exit_code == 2
    assert "unknown asset provider" in result.output


def test_assets_build_writes_summary(monkeypatch, tmp_path):
    from pjx import cli as cli_module

    output_path = tmp_path / "static" / "vendor" / "pjx"
    monkeypatch.setattr(cli_module, "available_asset_provider_names", lambda: ("htmx",))
    monkeypatch.setattr(cli_module, "discover_asset_providers", lambda names=None: [])
    monkeypatch.setattr(
        cli_module,
        "build_vendor_assets",
        lambda output, providers=None: VendorBuildResult(
            writes=(
                VendorAssetWrite(
                    provider="htmx",
                    asset="htmx",
                    output_path=output_path / "js" / "htmx.min.js",
                    source_url="https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js",
                ),
            )
        ),
    )

    result = runner.invoke(app, ["assets", "build", str(output_path)], color=False)

    assert result.exit_code == 0
    assert "Vendored htmx:" in result.output
    assert "Wrote 1 asset file(s)" in result.output
