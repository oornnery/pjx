from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from jinja2 import DictLoader

from pjx import PJXEnvironment, PJXExtension
from pjx.assets import BrowserAsset, BrowserAssetProvider
from pjx.core.types import Processor, ProcessorContext, ProcessorResult
from pjx.extension import ExtensionRegistry


class _DummyProcessor:
    def process(self, source: str, ctx: ProcessorContext) -> ProcessorResult:
        return ProcessorResult(source=source.replace("HELLO", "hello"))


class _DummyAssetProvider:
    name = "dummy"

    def matches(self, html: str) -> bool:
        return "data-dummy" in html

    def get_assets(self) -> tuple[BrowserAsset, ...]:
        return (
            BrowserAsset(
                name="dummy",
                kind="script",
                placement="head",
                cdn_url="https://cdn.example.com/dummy.js",
            ),
        )


class DummyExtension(PJXExtension):
    @property
    def name(self) -> str:
        return "dummy"

    def get_processors(self) -> Iterable[tuple[int, Processor]]:
        return [(40, _DummyProcessor())]

    def get_jinja_globals(self) -> dict[str, Callable[..., Any]]:
        return {"dummy_fn": lambda: "dummy"}

    def get_asset_provider(self) -> BrowserAssetProvider:
        return _DummyAssetProvider()


class MinimalExtension(PJXExtension):
    @property
    def name(self) -> str:
        return "minimal"


def test_extension_abc_requires_name():
    try:
        PJXExtension()  # type: ignore[abstract]
        assert False, "Should raise TypeError"
    except TypeError:
        pass


def test_minimal_extension_defaults():
    ext = MinimalExtension()
    assert ext.name == "minimal"
    assert list(ext.get_processors()) == []
    assert ext.get_jinja_globals() == {}
    assert ext.get_asset_provider() is None


def test_registry_register_and_deduplicate():
    registry = ExtensionRegistry()
    ext1 = DummyExtension()
    ext2 = DummyExtension()

    registry.register(ext1)
    registry.register(ext2)

    assert len(registry.extensions) == 1
    assert registry.extensions[0] is ext1


def test_explicit_extension_provides_processor():
    env = PJXEnvironment(
        loader=DictLoader({"test.jinja": "HELLO world"}),
        extensions=[DummyExtension()],
    )

    html = env.get_template("test.jinja").render()
    assert "hello world" in html


def test_explicit_extension_provides_jinja_global():
    env = PJXEnvironment(
        loader=DictLoader({"test.jinja": "{{ dummy_fn() }}"}),
        extensions=[DummyExtension()],
    )

    html = env.get_template("test.jinja").render()
    assert "dummy" in html


def test_explicit_extension_provides_asset_injection():
    env = PJXEnvironment(
        loader=DictLoader(
            {
                "page.jinja": (
                    "<!DOCTYPE html><html><head></head>"
                    '<body><div data-dummy></div></body></html>'
                )
            }
        ),
        extensions=[DummyExtension()],
        asset_mode="cdn",
    )

    html = env.get_template("page.jinja").render()
    assert 'data-pjx-asset="dummy"' in html
    assert "cdn.example.com/dummy.js" in html


def test_installed_extensions_discovered_via_entry_points():
    env = PJXEnvironment(
        loader=DictLoader(
            {
                "page.jinja": (
                    "<!DOCTYPE html><html><head></head>"
                    '<body><button hx-get="/test">Click</button></body></html>'
                )
            }
        ),
        asset_mode="cdn",
    )

    html = env.get_template("page.jinja").render()
    assert 'data-pjx-asset="htmx"' in html


def test_explicit_extension_suppresses_legacy_duplicate():
    from pjx_htmx import HTMXExtension

    registry = ExtensionRegistry()
    registry.register(HTMXExtension())
    registry.discover()

    htmx_count = sum(1 for ext in registry.extensions if "htmx" in ext.name)
    assert htmx_count == 1


def test_multiple_extensions():
    env = PJXEnvironment(
        loader=DictLoader({"test.jinja": "{{ dummy_fn() }}"}),
        extensions=[DummyExtension(), MinimalExtension()],
    )

    assert "dummy_fn" in env.globals
    html = env.get_template("test.jinja").render()
    assert "dummy" in html
