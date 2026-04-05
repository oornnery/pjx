from pjx.core.flow import ControlFlowProcessor
from pjx.core.types import ProcessorContext


def test_fragment_removed():
    proc = ControlFlowProcessor()
    source = "<Fragment>\n  <span>A</span>\n  <span>B</span>\n</Fragment>"
    result = proc.process(source, ProcessorContext())
    assert "<Fragment>" not in result.source
    assert "</Fragment>" not in result.source
    assert "<span>A</span>" in result.source
    assert "<span>B</span>" in result.source


def test_self_closing_fragment():
    proc = ControlFlowProcessor()
    source = "<Fragment />"
    result = proc.process(source, ProcessorContext())
    assert "<Fragment" not in result.source


def test_fragment_nested_in_show():
    proc = ControlFlowProcessor()
    source = (
        "<Show when={visible}>\n"
        "  <Fragment>\n"
        "    <span>A</span>\n"
        "    <span>B</span>\n"
        "  </Fragment>\n"
        "</Show>"
    )
    result = proc.process(source, ProcessorContext())
    assert "{% if visible %}" in result.source
    assert "{% endif %}" in result.source
    assert "<Fragment>" not in result.source
    assert "</Fragment>" not in result.source
    assert "<span>A</span>" in result.source


def test_no_fragment_passthrough():
    proc = ControlFlowProcessor()
    source = "<div>no fragment here</div>"
    result = proc.process(source, ProcessorContext())
    assert result.source == source
