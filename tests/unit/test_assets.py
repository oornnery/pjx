"""Tests for pjx.assets — AssetCollector and asset management."""

from pjx.ast_nodes import AssetDecl
from pjx.assets import AssetCollector


class TestAssetCollector:
    def test_add_css(self) -> None:
        collector = AssetCollector()
        collector.add(AssetDecl(kind="css", path="/static/css/card.css"))
        result = collector.render_css()
        assert '<link rel="stylesheet" href="/static/css/card.css" />' in result

    def test_add_js(self) -> None:
        collector = AssetCollector()
        collector.add(AssetDecl(kind="js", path="/static/js/modal.js"))
        result = collector.render_js()
        assert '<script src="/static/js/modal.js" type="module"></script>' in result

    def test_js_no_module(self) -> None:
        collector = AssetCollector()
        collector.add(AssetDecl(kind="js", path="/static/js/app.js"))
        result = collector.render_js(module=False)
        assert '<script src="/static/js/app.js"></script>' in result
        assert "module" not in result

    def test_dedup(self) -> None:
        collector = AssetCollector()
        collector.add(AssetDecl(kind="css", path="/static/css/base.css"))
        collector.add(AssetDecl(kind="css", path="/static/css/base.css"))
        result = collector.render_css()
        assert result.count("base.css") == 1

    def test_render_css_before_js(self) -> None:
        collector = AssetCollector()
        collector.add(AssetDecl(kind="js", path="/static/js/app.js"))
        collector.add(AssetDecl(kind="css", path="/static/css/base.css"))
        result = str(collector.render())
        css_pos = result.index("base.css")
        js_pos = result.index("app.js")
        assert css_pos < js_pos

    def test_empty_render(self) -> None:
        collector = AssetCollector()
        assert collector.render() == ""

    def test_multiple_assets_ordered(self) -> None:
        collector = AssetCollector()
        collector.add(AssetDecl(kind="css", path="/a.css"))
        collector.add(AssetDecl(kind="css", path="/b.css"))
        collector.add(AssetDecl(kind="js", path="/x.js"))
        result = str(collector.render())
        assert result.index("a.css") < result.index("b.css")
        assert result.index("b.css") < result.index("x.js")
