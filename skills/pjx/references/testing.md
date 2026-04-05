# PJX Testing Guide

## Test Structure

```text
src/pjx/tests/
  conftest.py              # Golden file fixtures
  fastapi/
    test_decorators.py     # Router integration tests
  preprocessor/
    test_pipeline.py       # Golden files + e2e
    test_frontmatter.py    # Frontmatter parsing
    test_control_flow.py   # <For>, <Show>, <Switch>
    test_components.py     # Components + imports
    test_expressions.py    # {expr} -> {{ expr }}
    test_scanner.py        # Scanner edge cases
    test_vars.py           # vars: and computed:
    test_attrs.py          # ?attr and ...{spread}
    test_fragment.py       # <Fragment>
    test_pipeline_new.py   # Full pipeline with new features
  test_checker.py          # Static analysis
  test_formatter.py        # Frontmatter formatting
  test_cache.py            # Template cache
  test_seo.py              # Sitemap/robots generation
  test_cli.py              # CLI commands
  test_path_traversal.py   # Security tests
  fixtures/                # Golden file fixtures
```

## Golden File Testing

Each fixture has `input.jinja` and `expected.jinja`:

```python
def test_golden_files(golden_fixture):
    pipeline = PreprocessorPipeline()
    result = pipeline.process(
        golden_fixture["input"],
        filename=str(golden_fixture["dir"] / "input.jinja"),
    )
    assert result.source.strip() == golden_fixture["expected"].strip()
```

## Unit Testing Processors

```python
from pjx.core.types import ProcessorContext

def test_for_basic():
    proc = ControlFlowProcessor()
    source = '<For each={items} as="item"><li>{{ item }}</li></For>'
    result = proc.process(source, ProcessorContext())
    assert "{% for item in items %}" in result.source
```

## Testing Router Decorators

```python
import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

app = FastAPI()
# ... setup templates, router, handlers ...
app.include_router(ui)

@pytest.fixture
def client():
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )

@pytest.mark.anyio
async def test_page_renders(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "Home" in response.text
```

## Testing Checker

```python
from pjx.checker import check_template
from pjx.core.pipeline import PreprocessorPipeline

def test_computed_cycle():
    source = "---\ncomputed:\n  a: b + 1\n  b: a + 1\n---\n<span>{{ a }}</span>"
    result = check_template(source, "test.jinja", PreprocessorPipeline())
    assert any("Circular dependency" in d.message for d in result.diagnostics)
```

## Key Rules

- Use `ProcessorContext()` for unit tests
- Use `("Card",)` not `["Card"]` for `ImportDecl.names` (tuple, not list)
- Use `Path(__file__)` for fixture paths (not relative strings)
- Use `pytest.mark.anyio` for async tests
- Test both success and error paths for router decorators
- Golden files test the full pipeline; unit tests test individual processors
