import pytest

from pjx.core.flow import ControlFlowProcessor
from pjx.core.pipeline import ProcessorContext
from pjx.errors import PJXError


@pytest.fixture
def processor():
    return ControlFlowProcessor()


@pytest.fixture
def ctx():
    return ProcessorContext()


def test_for_basic(processor, ctx):
    source = '<For each={items} as="item"><li>{{ item }}</li></For>'
    result = processor.process(source, ctx)
    assert "{% for item in items %}" in result.source
    assert "{% endfor %}" in result.source


def test_for_missing_each(processor, ctx):
    source = '<For as="item">content</For>'
    with pytest.raises(PJXError, match="requer atributo 'each'"):
        processor.process(source, ctx)


def test_for_missing_as(processor, ctx):
    source = "<For each={items}>content</For>"
    with pytest.raises(PJXError, match="requer atributo 'as'"):
        processor.process(source, ctx)


def test_show_basic(processor, ctx):
    source = "<Show when={active}><span>Yes</span></Show>"
    result = processor.process(source, ctx)
    assert "{% if active %}" in result.source
    assert "{% endif %}" in result.source


def test_show_with_else(processor, ctx):
    source = "<Show when={x}><span>A</span><Else><span>B</span></Else></Show>"
    result = processor.process(source, ctx)
    assert "{% if x %}" in result.source
    assert "{% else %}" in result.source
    assert "{% endif %}" in result.source


def test_show_missing_when(processor, ctx):
    source = "<Show><span>Yes</span></Show>"
    with pytest.raises(PJXError, match="requer atributo 'when'"):
        processor.process(source, ctx)


def test_switch_basic(processor, ctx):
    source = """<Switch expr={role}>
  <Case value="admin">
    <span>Admin</span>
  </Case>
  <Case value="user">
    <span>User</span>
  </Case>
  <Default>
    <span>Guest</span>
  </Default>
</Switch>"""
    result = processor.process(source, ctx)
    assert '{% if role == "admin" %}' in result.source
    assert '{% elif role == "user" %}' in result.source
    assert "{% else %}" in result.source
    assert "{% endif %}" in result.source


def test_switch_missing_expr(processor, ctx):
    source = '<Switch>\n  <Case value="a">A</Case>\n</Switch>'
    with pytest.raises(PJXError, match="requer atributo 'expr'"):
        processor.process(source, ctx)


def test_nested_control_flow(processor, ctx):
    source = """<For each={users} as="user">
  <Show when={user.active}>
    <span>{{ user.name }}</span>
  </Show>
</For>"""
    result = processor.process(source, ctx)
    assert "{% for user in users %}" in result.source
    assert "{% if user.active %}" in result.source
    assert "{% endif %}" in result.source
    assert "{% endfor %}" in result.source
