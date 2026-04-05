from pjx.core.pipeline import PreprocessorPipeline


def test_vars_in_pipeline():
    pipeline = PreprocessorPipeline()
    source = """---
vars:
  color: "blue"
---

<div class={color}>test</div>
"""
    result = pipeline.process(source)
    assert '{% set color = "blue" %}' in result.source
    assert 'class="{{ color }}"' in result.source


def test_computed_in_pipeline():
    pipeline = PreprocessorPipeline()
    source = """---
props:
  name: str

computed:
  greeting: "Hello " ~ name
---

<span>{{ greeting }}</span>
"""
    result = pipeline.process(source, filename="test.jinja")
    assert '{% set greeting = "Hello " ~ name %}' in result.source
    assert "<span>{{ greeting }}</span>" in result.source


def test_fragment_in_pipeline():
    pipeline = PreprocessorPipeline()
    source = "<Fragment><span>A</span><span>B</span></Fragment>"
    result = pipeline.process(source)
    assert "<Fragment>" not in result.source
    assert "</Fragment>" not in result.source
    assert "<span>A</span>" in result.source


def test_conditional_attr_in_pipeline():
    pipeline = PreprocessorPipeline()
    source = "<div ?hidden={not visible}>text</div>"
    result = pipeline.process(source)
    assert "{% if not visible %}" in result.source
    assert "{% endif %}" in result.source
    assert 'hidden="{{ not visible }}"' in result.source


def test_spread_attr_in_pipeline():
    pipeline = PreprocessorPipeline()
    source = "<div ...{attrs}>text</div>"
    result = pipeline.process(source)
    assert "{{ attrs | xmlattr }}" in result.source


def test_full_template_with_new_features():
    pipeline = PreprocessorPipeline()
    source = """---
props:
  items: list = []
  show_header: bool = true

vars:
  base_class: "container mx-auto"

computed:
  has_items: items | length > 0
---

<div class={base_class}>
  <Show when={show_header}>
    <Fragment>
      <h1>Title</h1>
      <p>Subtitle</p>
    </Fragment>
  </Show>
  <ul ?hidden={not has_items}>
    <For each={items} as="item">
      <li>{{ item }}</li>
    </For>
  </ul>
</div>
"""
    result = pipeline.process(source, filename="test.jinja")
    # vars
    assert '{% set base_class = "container mx-auto" %}' in result.source
    # computed
    assert "{% set has_items = items | length > 0 %}" in result.source
    # expressions
    assert 'class="{{ base_class }}"' in result.source
    # Fragment removed
    assert "<Fragment>" not in result.source
    assert "</Fragment>" not in result.source
    assert "<h1>Title</h1>" in result.source
    # Conditional attr
    assert "{% if not has_items %}" in result.source
    assert "{% endif %}" in result.source
    # Control flow
    assert "{% if show_header %}" in result.source
    assert "{% for item in items %}" in result.source
