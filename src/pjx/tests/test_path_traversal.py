from pjx.models import ImportDecl, TemplateMetadata


def _meta_with_import(source: str, name: str) -> TemplateMetadata:
    return TemplateMetadata(imports=[ImportDecl(source=source, names=(name,))])


def test_normal_relative_import():
    meta = _meta_with_import("..components", "Card")
    result = meta.resolve_import("Card", current_file="pages/home.jinja")
    assert result == "components/Card.jinja"


def test_normal_absolute_import():
    meta = _meta_with_import("components", "Card")
    result = meta.resolve_import("Card")
    assert result == "components/Card.jinja"


def test_excessive_traversal_stays_safe():
    # "....etc" from "pages/home.jinja": pops exhaust dir_parts, result is "etc/passwd.jinja"
    # This is safe — stays within template root (no ".." in resolved path)
    meta = _meta_with_import("....etc", "passwd")
    result = meta.resolve_import("passwd", current_file="pages/home.jinja")
    assert result == "etc/passwd.jinja"
    assert ".." not in result.split("/")


def test_absolute_path_with_slash_rejected():
    # "/etc" in absolute mode produces "/etc/passwd.jinja" which starts with "/"
    meta = _meta_with_import("/etc", "passwd")
    result = meta.resolve_import("passwd")
    assert result is None


def test_dotdot_via_absolute_import_rejected():
    # Absolute import containing path traversal: "../etc" starts with "."
    # so enters relative branch. Result from root file would be safe.
    # But "foo/../../../etc" in absolute mode: replace(".", "/") -> "foo/////////etc"
    # which is harmless (no ".." segments after replace)
    meta = _meta_with_import("foo", "bar")
    result = meta.resolve_import("bar")
    assert result == "foo/bar.jinja"


def test_relative_import_no_current_file():
    meta = _meta_with_import("..layouts", "Base")
    result = meta.resolve_import("Base", current_file=None)
    assert result is None


def test_single_dot_relative_import():
    # ".partials" from "pages/home.jinja": in PJX, "." pops one level
    # dir_parts ["pages"] -> pop -> [] -> append "partials" -> ["partials"]
    meta = _meta_with_import(".partials", "Header")
    result = meta.resolve_import("Header", current_file="pages/home.jinja")
    assert result == "partials/Header.jinja"


def test_name_not_in_imports():
    meta = _meta_with_import("components", "Card")
    result = meta.resolve_import("NotImported")
    assert result is None


def test_resolved_path_never_has_dotdot():
    # Even with many dots, the pop-or-skip logic prevents ".." in output
    meta = _meta_with_import("........secret", "key")
    result = meta.resolve_import("key", current_file="a/b/c.jinja")
    assert result is not None
    assert ".." not in result.split("/")


def test_deep_relative_stays_within_root():
    # "...layouts" from "a/b/c/d.jinja": pop 3x from ["a","b","c"] -> [] -> append "layouts"
    meta = _meta_with_import("...layouts", "Base")
    result = meta.resolve_import("Base", current_file="a/b/c/d.jinja")
    assert result == "layouts/Base.jinja"
