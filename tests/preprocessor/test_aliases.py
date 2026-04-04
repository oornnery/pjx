import pytest

from pjx.core.aliases import AliasProcessor
from pjx.core.pipeline import ProcessorContext
from pjx.errors import PJXError


@pytest.fixture
def processor():
    return AliasProcessor()


@pytest.fixture
def ctx():
    return ProcessorContext()


def test_htmx_aliases(processor, ctx):
    source = '<button htmx:post="/users" htmx:target="#list" htmx:swap="innerHTML">Go</button>'
    result = processor.process(source, ctx)
    assert 'hx-post="/users"' in result.source
    assert 'hx-target="#list"' in result.source
    assert 'hx-swap="innerHTML"' in result.source
    assert "htmx:" not in result.source


def test_stimulus_controller(processor, ctx):
    source = '<div stimulus:controller="dropdown">content</div>'
    result = processor.process(source, ctx)
    assert 'data-controller="dropdown"' in result.source
    assert "stimulus:" not in result.source


def test_stimulus_action(processor, ctx):
    source = '<div stimulus:controller="dropdown"><button stimulus:action="click->dropdown#toggle">X</button></div>'
    result = processor.process(source, ctx)
    assert 'data-action="click->dropdown#toggle"' in result.source


def test_stimulus_target_single_controller(processor, ctx):
    source = (
        '<div stimulus:controller="dropdown"><div stimulus:target="menu">M</div></div>'
    )
    result = processor.process(source, ctx)
    assert 'data-dropdown-target="menu"' in result.source


def test_stimulus_target_explicit_controller(processor, ctx):
    source = '<div stimulus:controller="dropdown modal"><div stimulus:target.dropdown="menu">M</div></div>'
    result = processor.process(source, ctx)
    assert 'data-dropdown-target="menu"' in result.source


def test_stimulus_target_ambiguous_multi_controller(processor, ctx):
    source = '<div stimulus:controller="dropdown modal"><div stimulus:target="menu">M</div></div>'
    with pytest.raises(PJXError, match="ambiguo"):
        processor.process(source, ctx)


def test_stimulus_target_outside_controller(processor, ctx):
    source = '<div stimulus:target="menu">M</div>'
    with pytest.raises(PJXError, match="fora de stimulus:controller"):
        processor.process(source, ctx)


def test_stimulus_value(processor, ctx):
    source = '<div stimulus:controller="editor"><input stimulus:value-content="hello" /></div>'
    result = processor.process(source, ctx)
    assert 'data-editor-content-value="hello"' in result.source


def test_sse_aliases(processor, ctx):
    source = '<div htmx:ext="sse" sse:connect="/events" sse:swap="message">X</div>'
    result = processor.process(source, ctx)
    assert 'hx-ext="sse"' in result.source
    assert 'sse-connect="/events"' in result.source
    assert 'sse-swap="message"' in result.source


def test_passthrough_normal_attrs(processor, ctx):
    source = '<div class="foo" id="bar">X</div>'
    result = processor.process(source, ctx)
    assert 'class="foo"' in result.source
    assert 'id="bar"' in result.source


def test_self_closing_with_aliases(processor, ctx):
    source = '<div stimulus:controller="tabs"><input stimulus:target="field" /></div>'
    result = processor.process(source, ctx)
    assert 'data-tabs-target="field"' in result.source
