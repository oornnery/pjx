import pytest

from pjx.core.components import ComponentProcessor
from pjx.core.pipeline import ProcessorContext
from pjx.models import ImportDecl, TemplateMetadata


@pytest.fixture
def processor():
    return ComponentProcessor()


def test_no_metadata(processor):
    ctx = ProcessorContext()
    source = "<UserCard />"
    result = processor.process(source, ctx)
    assert result.source == source


def test_self_closing_component(processor):
    metadata = TemplateMetadata(
        imports=[ImportDecl(source="components", names=("Card",))],
    )
    ctx = ProcessorContext(filename="pages/test.jinja", metadata=metadata)
    source = '<Card title="hello" />'
    result = processor.process(source, ctx)
    assert '{% include "components/Card.jinja" %}' in result.source
    assert "{% with" in result.source
    assert "{% endwith %}" in result.source


def test_component_with_expression_props(processor):
    metadata = TemplateMetadata(
        imports=[ImportDecl(source="components", names=("Badge",))],
    )
    ctx = ProcessorContext(filename="pages/test.jinja", metadata=metadata)
    source = "<Badge type={user.role} />"
    result = processor.process(source, ctx)
    assert '{% include "components/Badge.jinja" %}' in result.source
    assert "type=user.role" in result.source


def test_component_open_close(processor):
    metadata = TemplateMetadata(
        imports=[ImportDecl(source="components", names=("Card",))],
    )
    ctx = ProcessorContext(filename="pages/test.jinja", metadata=metadata)
    source = '<Card title="test"><p>content</p></Card>'
    result = processor.process(source, ctx)
    assert '{% include "components/Card.jinja" %}' in result.source


def test_relative_import_resolution(processor):
    metadata = TemplateMetadata(
        imports=[ImportDecl(source="..components", names=("UserCard",))],
    )
    ctx = ProcessorContext(filename="pages/dashboard.jinja", metadata=metadata)
    source = "<UserCard />"
    result = processor.process(source, ctx)
    assert '{% include "components/UserCard.jinja" %}' in result.source


def test_slot_tags_removed(processor):
    metadata = TemplateMetadata(
        imports=[ImportDecl(source="components", names=("Card",))],
    )
    ctx = ProcessorContext(filename="pages/test.jinja", metadata=metadata)
    source = '<Card title="x"><Slot name="actions"><button>Edit</button></Slot></Card>'
    result = processor.process(source, ctx)
    assert "<Slot" not in result.source
    assert "</Slot>" not in result.source
