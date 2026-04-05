import argparse
import tempfile
from pathlib import Path

from pjx.cli import cmd_check, cmd_format, cmd_sitemap

FIXTURES = str(Path(__file__).parent / "fixtures")


def test_check_valid_fixtures():
    args = argparse.Namespace(path=f"{FIXTURES}/basic", verbose=False)
    exit_code = cmd_check(args)
    assert exit_code == 0


def test_check_valid_fixtures_verbose():
    args = argparse.Namespace(path=f"{FIXTURES}/basic", verbose=True)
    exit_code = cmd_check(args)
    assert exit_code == 0


def test_check_single_file():
    args = argparse.Namespace(path=f"{FIXTURES}/basic/input.jinja", verbose=False)
    exit_code = cmd_check(args)
    assert exit_code == 0


def test_check_nonexistent_path():
    args = argparse.Namespace(path=f"{FIXTURES}/does_not_exist", verbose=False)
    exit_code = cmd_check(args)
    assert exit_code == 1


def test_check_all_fixtures():
    args = argparse.Namespace(path=FIXTURES, verbose=False)
    exit_code = cmd_check(args)
    assert exit_code == 0


def test_format_check_mode():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "test.jinja"
        p.write_text("<h1>no frontmatter</h1>")
        args = argparse.Namespace(path=str(p), check=True, verbose=False)
        assert cmd_format(args) == 0


def test_format_applies():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "test.jinja"
        source = "---\nprops:\n  x: int\n\nfrom a import B\n---\n<h1>hi</h1>\n"
        p.write_text(source)
        args = argparse.Namespace(path=str(p), check=False, verbose=False)
        assert cmd_format(args) == 0
        result = p.read_text()
        lines = result.split("\n")
        import_idx = next(i for i, ln in enumerate(lines) if "from" in ln)
        props_idx = next(i for i, ln in enumerate(lines) if ln.strip() == "props:")
        assert import_idx < props_idx


def test_format_nonexistent():
    args = argparse.Namespace(path="/nonexistent", check=False, verbose=False)
    assert cmd_format(args) == 1


def test_sitemap_generates():
    with tempfile.TemporaryDirectory() as tmpdir:
        pages = Path(tmpdir) / "pages"
        pages.mkdir()
        (pages / "home.jinja").write_text("<h1>Home</h1>")
        (pages / "about.jinja").write_text("<h1>About</h1>")

        output = Path(tmpdir) / "out"
        args = argparse.Namespace(
            path=tmpdir,
            base_url="https://example.com",
            output=str(output),
            disallow=None,
        )
        assert cmd_sitemap(args) == 0
        assert (output / "sitemap.xml").exists()
        assert (output / "robots.txt").exists()

        xml = (output / "sitemap.xml").read_text()
        assert "https://example.com/" in xml
        assert "https://example.com/about" in xml
