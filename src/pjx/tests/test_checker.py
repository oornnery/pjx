from pjx.checker import check_template
from pjx.core.pipeline import PreprocessorPipeline
from pjx.errors import DiagnosticLevel


def make_pipeline():
    return PreprocessorPipeline()


def test_valid_template():
    source = "<h1>{{ title }}</h1>"
    result = check_template(source, "test.jinja", make_pipeline())
    assert not result.has_errors


def test_unresolvable_import():
    import tempfile

    from jinja2 import FileSystemLoader

    with tempfile.TemporaryDirectory() as tmpdir:
        source = """---
from ..missing import Ghost
---

<Ghost />
"""
        loader = FileSystemLoader(tmpdir)
        result = check_template(source, "pages/test.jinja", make_pipeline(), loader)
        warnings = [d for d in result.diagnostics if d.code == "PJX302"]
        assert any("not found" in d.message for d in warnings)


def test_computed_cycle():
    source = """---
computed:
  a: b + 1
  b: a + 1
---

<span>{{ a }}</span>
"""
    result = check_template(source, "test.jinja", make_pipeline())
    errors = [d for d in result.diagnostics if d.level == DiagnosticLevel.ERROR]
    assert any("Circular dependency" in d.message for d in errors)


def test_no_cycle_linear():
    source = """---
props:
  x: int = 0

computed:
  a: x + 1
  b: a + 1
---

<span>{{ b }}</span>
"""
    result = check_template(source, "test.jinja", make_pipeline())
    cycle_errors = [d for d in result.diagnostics if d.code == "PJX303"]
    assert len(cycle_errors) == 0


def test_undefined_var_warning():
    source = """---
props:
  name: str
---

<span>{{ unknown_thing }}</span>
"""
    result = check_template(source, "test.jinja", make_pipeline())
    warnings = [d for d in result.diagnostics if d.code == "PJX304"]
    names = [d.message for d in warnings]
    assert any("unknown_thing" in m for m in names)


def test_defined_vars_no_warning():
    source = """---
props:
  title: str

vars:
  color: "blue"

computed:
  greeting: "Hello " ~ title
---

<h1 class={color}>{{ greeting }}</h1>
"""
    result = check_template(source, "test.jinja", make_pipeline())
    warnings = [d for d in result.diagnostics if d.code == "PJX304"]
    names = {d.message for d in warnings}
    assert not any("color" in m for m in names)
    assert not any("greeting" in m for m in names)
    assert not any("title" in m for m in names)
