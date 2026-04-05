import pytest

from pjx.core.frontmatter import FrontmatterProcessor
from pjx.core.pipeline import ProcessorContext
from pjx.errors import PJXError


@pytest.fixture
def processor():
    return FrontmatterProcessor()


@pytest.fixture
def ctx():
    return ProcessorContext(filename="test.jinja")


def test_no_frontmatter(processor, ctx):
    source = "<h1>Hello</h1>"
    result = processor.process(source, ctx)
    assert result.source == source
    assert result.metadata is None


def test_imports(processor, ctx):
    source = """---
from layouts import Base
from ..components import UserCard, Badge
---

<h1>Hello</h1>
"""
    result = processor.process(source, ctx)
    assert result.metadata is not None
    assert len(result.metadata.imports) == 2
    assert result.metadata.imports[0].source == "layouts"
    assert result.metadata.imports[0].names == ("Base",)
    assert result.metadata.imports[1].source == "..components"
    assert result.metadata.imports[1].names == ("UserCard", "Badge")
    assert "<h1>Hello</h1>" in result.source
    assert "---" not in result.source


def test_props(processor, ctx):
    source = """---
props:
  title: str = "Dashboard"
  users: list[UserView] = []
  active: bool
---

body
"""
    result = processor.process(source, ctx)
    assert result.metadata is not None
    assert len(result.metadata.props) == 3
    assert result.metadata.props[0].name == "title"
    assert result.metadata.props[0].type_annotation == "str"
    assert result.metadata.props[0].default == '"Dashboard"'
    assert result.metadata.props[2].name == "active"
    assert result.metadata.props[2].default is None


def test_slots(processor, ctx):
    source = """---
slot actions
slot sidebar
---

body
"""
    result = processor.process(source, ctx)
    assert result.metadata is not None
    assert len(result.metadata.slots) == 2
    assert result.metadata.slots[0].name == "actions"
    assert result.metadata.slots[1].name == "sidebar"


def test_unclosed_frontmatter(processor, ctx):
    source = """---
props:
  title: str
"""
    with pytest.raises(PJXError, match="Frontmatter nao fechado"):
        processor.process(source, ctx)


def test_full_frontmatter(processor, ctx):
    source = """---
from ..layouts import Base
from ..components import UserCard

props:
  title: str = "Dashboard"
  users: list[UserView] = []

slot actions
---

<Base title={props.title}>
  <h1>{{ props.title }}</h1>
</Base>
"""
    result = processor.process(source, ctx)
    assert result.metadata is not None
    assert len(result.metadata.imports) == 2
    assert len(result.metadata.props) == 2
    assert len(result.metadata.slots) == 1
    assert "---" not in result.source
    assert "<Base" in result.source
