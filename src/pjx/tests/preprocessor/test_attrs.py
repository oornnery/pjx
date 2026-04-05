from pjx.core.attrs import AttrsProcessor
from pjx.core.types import ProcessorContext


def test_conditional_attr_with_expression():
    proc = AttrsProcessor()
    source = "<div ?hidden={not visible}>content</div>"
    result = proc.process(source, ProcessorContext())
    assert "{% if not visible %}" in result.source
    assert 'hidden="{{ not visible }}"' in result.source
    assert "{% endif %}" in result.source


def test_conditional_attr_passthrough_without_value():
    proc = AttrsProcessor()
    source = "<input ?disabled>"
    # Scanner won't see ">" inside the scan so this needs careful handling
    # ?disabled without value just outputs the attr name
    result = proc.process(source, ProcessorContext())
    assert "disabled" in result.source


def test_spread_attribute():
    proc = AttrsProcessor()
    source = "<div ...{extra_attrs}>content</div>"
    result = proc.process(source, ProcessorContext())
    assert "{{ extra_attrs | xmlattr }}" in result.source


def test_mixed_normal_and_conditional():
    proc = AttrsProcessor()
    source = '<div class="base" ?hidden={hide}>text</div>'
    result = proc.process(source, ProcessorContext())
    assert 'class="base"' in result.source
    assert "{% if hide %}" in result.source
    assert "{% endif %}" in result.source


def test_mixed_normal_and_spread():
    proc = AttrsProcessor()
    source = '<div id="main" ...{attrs}>text</div>'
    result = proc.process(source, ProcessorContext())
    assert 'id="main"' in result.source
    assert "{{ attrs | xmlattr }}" in result.source


def test_no_special_attrs_passthrough():
    proc = AttrsProcessor()
    source = '<div class="foo" id="bar">text</div>'
    result = proc.process(source, ProcessorContext())
    assert result.source == source


def test_conditional_self_closing():
    proc = AttrsProcessor()
    source = '<input type="text" ?required={is_required} />'
    result = proc.process(source, ProcessorContext())
    assert 'type="text"' in result.source
    assert "{% if is_required %}" in result.source
    assert "/>" in result.source
