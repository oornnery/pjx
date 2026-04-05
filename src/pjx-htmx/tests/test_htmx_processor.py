from pjx.core.types import ProcessorContext
from pjx_htmx import HTMXAliasProcessor


def test_htmx_aliases():
    proc = HTMXAliasProcessor()
    source = '<button htmx:post="/users" htmx:target="#list" htmx:swap="innerHTML">Go</button>'
    result = proc.process(source, ProcessorContext())
    assert 'hx-post="/users"' in result.source
    assert 'hx-target="#list"' in result.source
    assert 'hx-swap="innerHTML"' in result.source
    assert "htmx:" not in result.source


def test_sse_aliases():
    proc = HTMXAliasProcessor()
    source = '<div htmx:ext="sse" sse:connect="/events" sse:swap="message">X</div>'
    result = proc.process(source, ProcessorContext())
    assert 'hx-ext="sse"' in result.source
    assert 'sse-connect="/events"' in result.source
    assert 'sse-swap="message"' in result.source


def test_passthrough_normal_attrs():
    proc = HTMXAliasProcessor()
    source = '<div class="foo" id="bar">X</div>'
    result = proc.process(source, ProcessorContext())
    assert 'class="foo"' in result.source
    assert 'id="bar"' in result.source


def test_self_closing_with_htmx():
    proc = HTMXAliasProcessor()
    source = '<input htmx:get="/check" />'
    result = proc.process(source, ProcessorContext())
    assert 'hx-get="/check"' in result.source
    assert "/>" in result.source
