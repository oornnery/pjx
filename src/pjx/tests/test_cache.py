import tempfile
from pathlib import Path

from pjx.cache import TemplateCache
from pjx.core.types import PreprocessResult


def _result(source: str) -> PreprocessResult:
    return PreprocessResult(source=source)


def test_put_and_get():
    cache = TemplateCache()
    cache.put("test.jinja", _result("<h1>ok</h1>"))
    result = cache.get("test.jinja")
    assert result is not None
    assert result.source == "<h1>ok</h1>"


def test_miss():
    cache = TemplateCache()
    assert cache.get("missing.jinja") is None


def test_invalidate():
    cache = TemplateCache()
    cache.put("test.jinja", _result("old"))
    cache.invalidate("test.jinja")
    assert cache.get("test.jinja") is None


def test_clear():
    cache = TemplateCache()
    cache.put("a.jinja", _result("a"))
    cache.put("b.jinja", _result("b"))
    assert len(cache) == 2
    cache.clear()
    assert len(cache) == 0


def test_mtime_invalidation():
    with tempfile.NamedTemporaryFile(suffix=".jinja", mode="w", delete=False) as f:
        f.write("<h1>v1</h1>")
        f.flush()
        path = f.name

    cache = TemplateCache()
    cache.put("test.jinja", _result("<h1>v1</h1>"), filename=path)

    # Same mtime -> cache hit
    assert cache.get("test.jinja", filename=path) is not None

    # Touch the file to change mtime
    p = Path(path)
    import time

    time.sleep(0.05)
    p.write_text("<h1>v2</h1>")

    # New mtime -> cache miss
    assert cache.get("test.jinja", filename=path) is None

    p.unlink()
