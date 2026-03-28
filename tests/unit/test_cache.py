"""Tests for pjx.cache — template compilation cache."""

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from pjx.cache import TemplateCache


@pytest.fixture()
def cache() -> TemplateCache:
    return TemplateCache()


class TestIsStale:
    def test_unknown_template_is_stale(self, cache: TemplateCache) -> None:
        assert cache.is_stale("unknown.jinja", 1.0) is True

    def test_cached_template_same_mtime_not_stale(self, cache: TemplateCache) -> None:
        cache.store("a.jinja", 1.0, "<div>", None, ())
        assert cache.is_stale("a.jinja", 1.0) is False

    def test_cached_template_different_mtime_is_stale(
        self, cache: TemplateCache
    ) -> None:
        cache.store("a.jinja", 1.0, "<div>", None, ())
        assert cache.is_stale("a.jinja", 2.0) is True


class TestStore:
    def test_store_and_retrieve_source(self, cache: TemplateCache) -> None:
        cache.store("a.jinja", 1.0, "<div>hello</div>", None, ())
        assert cache.get_source("a.jinja") == "<div>hello</div>"
        assert cache.has_source("a.jinja") is True

    def test_get_source_returns_none_for_unknown(self, cache: TemplateCache) -> None:
        assert cache.get_source("unknown.jinja") is None
        assert cache.has_source("unknown.jinja") is False

    def test_store_overwrites_previous(self, cache: TemplateCache) -> None:
        cache.store("a.jinja", 1.0, "old", None, ())
        cache.store("a.jinja", 2.0, "new", None, ())
        assert cache.get_source("a.jinja") == "new"


class TestStorePropsModel:
    def test_store_and_retrieve_props_model(self, cache: TemplateCache) -> None:
        class MyModel(BaseModel):
            name: str = ""

        cache.store_props_model("a.jinja", MyModel)
        assert cache.get_props_model("a.jinja") is MyModel

    def test_does_not_overwrite_existing(self, cache: TemplateCache) -> None:
        class First(BaseModel):
            pass

        class Second(BaseModel):
            pass

        cache.store_props_model("a.jinja", First)
        cache.store_props_model("a.jinja", Second)
        assert cache.get_props_model("a.jinja") is First

    def test_returns_none_for_unknown(self, cache: TemplateCache) -> None:
        assert cache.get_props_model("unknown.jinja") is None


class TestCollectCachedAssets:
    def test_collects_css(self, cache: TemplateCache) -> None:
        cache.store("a.jinja", 1.0, "", ".card { color: red; }", ())
        css_parts: list[str] = []
        cache.collect_cached_assets("a.jinja", css_parts, None)
        assert css_parts == [".card { color: red; }"]

    def test_skips_none_css(self, cache: TemplateCache) -> None:
        cache.store("a.jinja", 1.0, "", None, ())
        css_parts: list[str] = []
        cache.collect_cached_assets("a.jinja", css_parts, None)
        assert css_parts == []

    def test_collects_assets(self, cache: TemplateCache) -> None:
        asset = MagicMock()
        cache.store("a.jinja", 1.0, "", None, (asset,))
        collector = MagicMock()
        cache.collect_cached_assets("a.jinja", None, collector)
        collector.add.assert_called_once_with(asset)

    def test_no_op_for_unknown(self, cache: TemplateCache) -> None:
        css_parts: list[str] = []
        cache.collect_cached_assets("unknown.jinja", css_parts, None)
        assert css_parts == []
