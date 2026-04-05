from __future__ import annotations

from jinja2 import DictLoader

from pjx import PJXEnvironment
from pjx import assets as assets_module
from pjx.assets import BrowserAsset, BrowserAssetFile
from pjx_tailwind.assets import TailwindBrowserAssetProvider


def test_document_injects_detected_assets_from_installed_providers():
    env = PJXEnvironment(
        loader=DictLoader(
            {
                "page.jinja": (
                    "<!DOCTYPE html>"
                    "<html><head><title>Demo</title></head>"
                    '<body><button hx-get="/users">Load</button>'
                    '<div data-controller="modal"></div></body></html>'
                )
            }
        ),
        asset_mode="cdn",
        asset_providers=["htmx", "stimulus"],
    )

    html = env.get_template("page.jinja").render()

    assert 'data-pjx-asset="htmx"' in html
    assert 'data-pjx-asset="stimulus"' in html
    assert "https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js" in html
    assert "https://unpkg.com/@hotwired/stimulus@3.2.2/dist/stimulus.umd.js" in html
    assert html.index('data-pjx-asset="htmx"') < html.index("</head>")
    assert html.index('data-pjx-asset="stimulus"') < html.index("</head>")


def test_fragments_do_not_get_browser_asset_tags():
    env = PJXEnvironment(
        loader=DictLoader({"fragment.jinja": '<button hx-get="/users">Load</button>'}),
        asset_mode="cdn",
        asset_providers=["htmx"],
    )

    html = env.get_template("fragment.jinja").render()

    assert 'data-pjx-asset="htmx"' not in html


def test_vendor_mode_uses_static_vendor_paths():
    env = PJXEnvironment(
        loader=DictLoader(
            {
                "page.jinja": (
                    "<!DOCTYPE html><html><head></head>"
                    '<body><button hx-post="/users">Save</button></body></html>'
                )
            }
        ),
        asset_mode="vendor",
        asset_base_url="/static/vendor/pjx",
        asset_providers=["htmx"],
    )

    html = env.get_template("page.jinja").render()

    assert 'src="/static/vendor/pjx/js/htmx.min.js"' in html


def test_existing_manual_asset_tag_is_not_duplicated():
    env = PJXEnvironment(
        loader=DictLoader(
            {
                "page.jinja": (
                    "<!DOCTYPE html><html><head>"
                    '<script src="https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js"></script>'
                    '</head><body><button hx-get="/users">Load</button></body></html>'
                )
            }
        ),
        asset_mode="cdn",
        asset_providers=["htmx"],
    )

    html = env.get_template("page.jinja").render()

    assert html.count("htmx.min.js") == 1


def test_generic_external_provider_can_inject_and_vendor(monkeypatch, tmp_path):
    class FakeProvider:
        name = "acme"

        def matches(self, html: str) -> bool:
            return "data-acme" in html

        def get_assets(self) -> tuple[BrowserAsset, ...]:
            return (
                BrowserAsset(
                    name="acme-runtime",
                    kind="script",
                    placement="head",
                    cdn_url="https://cdn.example.com/acme.js",
                    vendor_file=BrowserAssetFile(
                        relative_path="js/acme.js",
                        source_url="https://cdn.example.com/acme.js",
                    ),
                ),
            )

    fake_provider = FakeProvider()

    html = assets_module.inject_browser_assets(
        "<!DOCTYPE html><html><head></head><body><div data-acme></div></body></html>",
        mode="vendor",
        base_url="/static/vendor/pjx",
        providers=[fake_provider],
    )
    result = assets_module.build_vendor_assets(
        tmp_path,
        providers=[fake_provider],
        fetcher=lambda url: b"console.log('acme');",
    )

    assert 'src="/static/vendor/pjx/js/acme.js"' in html
    assert result.files_written == 1
    assert (tmp_path / "js" / "acme.js").read_text() == "console.log('acme');"


def test_tailwind_provider_detects_browser_style_usage():
    provider = TailwindBrowserAssetProvider()
    html = '<div class="bg-slate-900 text-white md:flex"></div>'

    assert provider.matches(html)
