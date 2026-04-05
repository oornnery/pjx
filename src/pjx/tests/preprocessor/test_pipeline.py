from pjx.core.pipeline import PreprocessorPipeline
from pjx.extension import ExtensionRegistry


def _make_pipeline():
    """Create a pipeline with all installed extension processors."""
    pipeline = PreprocessorPipeline()
    registry = ExtensionRegistry()
    registry.discover()
    for ext in registry.extensions:
        for slot, processor in ext.get_processors():
            pipeline.register_processor(slot, processor)
    return pipeline


def test_golden_files(golden_fixture):
    pipeline = _make_pipeline()
    result = pipeline.process(
        golden_fixture["input"],
        filename=str(golden_fixture["dir"] / "input.jinja"),
    )
    assert result.source.strip() == golden_fixture["expected"].strip()


def test_plain_jinja_passthrough():
    pipeline = PreprocessorPipeline()
    source = "<h1>{{ title }}</h1>"
    result = pipeline.process(source)
    assert result.source == source
    assert result.metadata is None


def test_frontmatter_propagates_to_context():
    pipeline = PreprocessorPipeline()
    source = """---
from components import Card

props:
  title: str = "Test"
---

<h1>{{ props.title }}</h1>
"""
    result = pipeline.process(source, filename="pages/test.jinja")
    assert result.metadata is not None
    assert len(result.metadata.imports) == 1
    assert result.metadata.imports[0].source == "components"
    assert result.metadata.imports[0].names == ("Card",)
    assert len(result.metadata.props) == 1
    assert result.metadata.props[0].name == "title"
