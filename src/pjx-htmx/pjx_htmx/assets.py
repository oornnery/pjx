from __future__ import annotations

import re

from pjx.assets import BrowserAsset, BrowserAssetFile

_HTMX_ATTR_RE = re.compile(r"\s(?:data-)?hx-[a-z0-9-]+\s*=", re.IGNORECASE)
_SSE_ATTR_RE = re.compile(r"\ssse-[a-z0-9-]+\s*=", re.IGNORECASE)


class HTMXBrowserAssetProvider:
    name = "htmx"

    def matches(self, html: str) -> bool:
        return bool(_HTMX_ATTR_RE.search(html) or _SSE_ATTR_RE.search(html))

    def get_assets(self) -> tuple[BrowserAsset, ...]:
        return (
            BrowserAsset(
                name="htmx",
                kind="script",
                placement="head",
                cdn_url="https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js",
                vendor_file=BrowserAssetFile(
                    relative_path="js/htmx.min.js",
                    source_url="https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js",
                    npm_package="htmx.org@2.0.4",
                    npm_dist_path="htmx.org/dist/htmx.min.js",
                ),
                presence_tokens=(
                    "htmx.org",
                    "htmx.min.js",
                ),
            ),
        )


__all__ = ["HTMXBrowserAssetProvider"]
