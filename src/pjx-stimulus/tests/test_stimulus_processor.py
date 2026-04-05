import pytest

from pjx.core.types import ProcessorContext
from pjx.errors import PJXError
from pjx_stimulus import StimulusAliasProcessor


def test_stimulus_controller():
    proc = StimulusAliasProcessor()
    source = '<div stimulus:controller="dropdown">content</div>'
    result = proc.process(source, ProcessorContext())
    assert 'data-controller="dropdown"' in result.source
    assert "stimulus:" not in result.source


def test_stimulus_action():
    proc = StimulusAliasProcessor()
    source = (
        '<div stimulus:controller="dropdown">'
        '<button stimulus:action="click->dropdown#toggle">X</button></div>'
    )
    result = proc.process(source, ProcessorContext())
    assert 'data-action="click->dropdown#toggle"' in result.source


def test_stimulus_target_single_controller():
    proc = StimulusAliasProcessor()
    source = '<div stimulus:controller="dropdown"><div stimulus:target="menu">M</div></div>'
    result = proc.process(source, ProcessorContext())
    assert 'data-dropdown-target="menu"' in result.source


def test_stimulus_target_explicit_controller():
    proc = StimulusAliasProcessor()
    source = (
        '<div stimulus:controller="dropdown modal">'
        '<div stimulus:target.dropdown="menu">M</div></div>'
    )
    result = proc.process(source, ProcessorContext())
    assert 'data-dropdown-target="menu"' in result.source


def test_stimulus_target_ambiguous_multi_controller():
    proc = StimulusAliasProcessor()
    source = '<div stimulus:controller="dropdown modal"><div stimulus:target="menu">M</div></div>'
    with pytest.raises(PJXError, match="ambiguo"):
        proc.process(source, ProcessorContext())


def test_stimulus_target_outside_controller():
    proc = StimulusAliasProcessor()
    source = '<div stimulus:target="menu">M</div>'
    with pytest.raises(PJXError, match="fora de stimulus:controller"):
        proc.process(source, ProcessorContext())


def test_stimulus_value():
    proc = StimulusAliasProcessor()
    source = '<div stimulus:controller="editor"><input stimulus:value-content="hello" /></div>'
    result = proc.process(source, ProcessorContext())
    assert 'data-editor-content-value="hello"' in result.source


def test_self_closing_with_stimulus():
    proc = StimulusAliasProcessor()
    source = '<div stimulus:controller="tabs"><input stimulus:target="field" /></div>'
    result = proc.process(source, ProcessorContext())
    assert 'data-tabs-target="field"' in result.source
