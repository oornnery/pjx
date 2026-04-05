from pjx.formatter import format_template


def test_reorders_sections():
    source = """---
props:
  title: str

from ..layouts import Base

computed:
  greeting: "Hi " ~ title

vars:
  color: "blue"
---

<h1>{{ greeting }}</h1>
"""
    result = format_template(source)
    lines = result.split("\n")
    # imports should come first, then props, then vars, then computed
    import_idx = next(i for i, ln in enumerate(lines) if "from" in ln)
    props_idx = next(i for i, ln in enumerate(lines) if ln.strip() == "props:")
    vars_idx = next(i for i, ln in enumerate(lines) if ln.strip() == "vars:")
    computed_idx = next(i for i, ln in enumerate(lines) if ln.strip() == "computed:")
    assert import_idx < props_idx < vars_idx < computed_idx


def test_no_frontmatter_passthrough():
    source = "<h1>Hello</h1>"
    assert format_template(source) == source


def test_already_formatted():
    source = """---
from ..layouts import Base

props:
  title: str

vars:
  color: "blue"

computed:
  greeting: "Hi " ~ title
---

<h1>{{ greeting }}</h1>
"""
    result = format_template(source)
    # Should remain stable (idempotent)
    assert format_template(result) == result


def test_slots_come_last():
    source = """---
slot actions

props:
  title: str

from ..layouts import Base
---

<h1>test</h1>
"""
    result = format_template(source)
    lines = result.split("\n")
    import_idx = next(i for i, ln in enumerate(lines) if "from" in ln)
    slot_idx = next(i for i, ln in enumerate(lines) if "slot " in ln)
    assert import_idx < slot_idx
