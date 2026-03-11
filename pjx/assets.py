from __future__ import annotations

import html
from typing import Any

from markupsafe import Markup


def render_assets(assets: list[Any]) -> str:
    css_chunks = [
        f'<link rel="stylesheet" href="{html.escape(asset.path)}">'
        for asset in assets
        if asset.kind == "css"
    ]
    js_chunks = [
        f'<script src="{html.escape(asset.path)}" defer></script>'
        for asset in assets
        if asset.kind == "js"
    ]
    return "".join(css_chunks + js_chunks)


def render_css_assets(assets: list[Any]) -> str:
    return "".join(
        f'<link rel="stylesheet" href="{html.escape(asset.path)}">'
        for asset in assets
        if asset.kind == "css"
    )


def render_js_assets(assets: list[Any]) -> str:
    return "".join(
        f'<script src="{html.escape(asset.path)}" defer></script>'
        for asset in assets
        if asset.kind == "js"
    )


class AssetsView:
    def __init__(self, render_state: Any):
        self._render_state = render_state

    def render(self) -> Markup:
        self._render_state.assets_rendered = True
        return Markup(render_assets(self._render_state.assets))

    def render_css(self) -> Markup:
        self._render_state.assets_rendered = True
        return Markup(render_css_assets(self._render_state.assets))

    def render_js(self) -> Markup:
        self._render_state.assets_rendered = True
        return Markup(render_js_assets(self._render_state.assets))

    def collect_css(self) -> list[str]:
        return [
            asset.path for asset in self._render_state.assets if asset.kind == "css"
        ]

    def collect_js(self) -> list[str]:
        return [asset.path for asset in self._render_state.assets if asset.kind == "js"]
