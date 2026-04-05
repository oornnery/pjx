from pjx.core.pipeline import PreprocessorPipeline


def test_golden_files(golden_fixture):
    pipeline = PreprocessorPipeline()
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
