from pjx.core.frontmatter import FrontmatterProcessor
from pjx.core.types import ProcessorContext
from pjx.core.vars import VarsProcessor


def test_scalar_var():
    source = """---
vars:
  color: "blue"
---

<div>test</div>
"""
    ctx = ProcessorContext(filename="test.jinja")
    fm = FrontmatterProcessor()
    result = fm.process(source, ctx)
    assert result.metadata is not None
    assert len(result.metadata.vars) == 1
    assert result.metadata.vars[0].name == "color"
    assert result.metadata.vars[0].value == "blue"

    ctx.metadata = result.metadata
    vp = VarsProcessor()
    final = vp.process(result.source, ctx)
    assert '{% set color = "blue" %}' in final.source
    assert "<div>test</div>" in final.source


def test_map_var():
    source = """---
vars:
  sizes:
    sm: "h-8 px-3"
    md: "h-10 px-4"
    lg: "h-12 px-6"
---

<div>test</div>
"""
    ctx = ProcessorContext(filename="test.jinja")
    fm = FrontmatterProcessor()
    result = fm.process(source, ctx)
    assert result.metadata is not None
    assert len(result.metadata.vars) == 1
    assert result.metadata.vars[0].name == "sizes"
    assert isinstance(result.metadata.vars[0].value, dict)
    assert result.metadata.vars[0].value["sm"] == "h-8 px-3"
    assert result.metadata.vars[0].value["lg"] == "h-12 px-6"

    ctx.metadata = result.metadata
    vp = VarsProcessor()
    final = vp.process(result.source, ctx)
    assert "{% set sizes = {" in final.source
    assert '"sm": "h-8 px-3"' in final.source


def test_mixed_vars():
    source = """---
vars:
  base: "flex items-center"
  variants:
    primary: "bg-blue"
    secondary: "bg-gray"
---

<div>test</div>
"""
    ctx = ProcessorContext(filename="test.jinja")
    fm = FrontmatterProcessor()
    result = fm.process(source, ctx)
    assert result.metadata is not None
    assert len(result.metadata.vars) == 2
    assert result.metadata.vars[0].name == "base"
    assert result.metadata.vars[0].value == "flex items-center"
    assert result.metadata.vars[1].name == "variants"
    assert isinstance(result.metadata.vars[1].value, dict)


def test_computed_basic():
    source = """---
props:
  first: str
  last: str

computed:
  full_name: first ~ " " ~ last
  is_long: first | length > 10
---

<span>{{ full_name }}</span>
"""
    ctx = ProcessorContext(filename="test.jinja")
    fm = FrontmatterProcessor()
    result = fm.process(source, ctx)
    assert result.metadata is not None
    assert len(result.metadata.computed) == 2
    assert result.metadata.computed[0].name == "full_name"
    assert result.metadata.computed[0].expression == 'first ~ " " ~ last'
    assert result.metadata.computed[1].name == "is_long"

    ctx.metadata = result.metadata
    vp = VarsProcessor()
    final = vp.process(result.source, ctx)
    assert '{% set full_name = first ~ " " ~ last %}' in final.source
    assert "{% set is_long = first | length > 10 %}" in final.source


def test_vars_and_computed_together():
    source = """---
vars:
  base: "inline-flex"

computed:
  cls: base ~ " extra"
---

<div class={cls}>test</div>
"""
    ctx = ProcessorContext(filename="test.jinja")
    fm = FrontmatterProcessor()
    result = fm.process(source, ctx)
    assert result.metadata is not None
    assert len(result.metadata.vars) == 1
    assert len(result.metadata.computed) == 1

    ctx.metadata = result.metadata
    vp = VarsProcessor()
    final = vp.process(result.source, ctx)
    assert '{% set base = "inline-flex" %}' in final.source
    assert '{% set cls = base ~ " extra" %}' in final.source


def test_no_vars_passthrough():
    source = "<h1>hello</h1>"
    ctx = ProcessorContext(filename="test.jinja")
    vp = VarsProcessor()
    result = vp.process(source, ctx)
    assert result.source == source
