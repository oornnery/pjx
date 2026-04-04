from pjx.core.expressions import ExpressionProcessor
from pjx.core.pipeline import ProcessorContext


def test_attr_expression():
    proc = ExpressionProcessor()
    source = "<a href={'/users/' + str(id)}>Link</a>"
    result = proc.process(source, ProcessorContext())
    assert "href=\"{{ '/users/' + str(id) }}\"" in result.source


def test_jinja_expression_passthrough():
    proc = ExpressionProcessor()
    source = "<h1>{{ title }}</h1>"
    result = proc.process(source, ProcessorContext())
    assert result.source == source


def test_static_attr_passthrough():
    proc = ExpressionProcessor()
    source = '<span class="foo">text</span>'
    result = proc.process(source, ProcessorContext())
    assert result.source == source


def test_multiple_expressions():
    proc = ExpressionProcessor()
    source = "<a href={url} class={cls}>Link</a>"
    result = proc.process(source, ProcessorContext())
    assert 'href="{{ url }}"' in result.source
    assert 'class="{{ cls }}"' in result.source
