from __future__ import annotations

import re

from pjx.assets import BrowserAsset, BrowserAssetFile

_STIMULUS_ATTR_RE = re.compile(
    r"\sdata-(?:controller|action|[a-z0-9_-]+-(?:target|value|class|outlet))\s*=",
    re.IGNORECASE,
)


class StimulusBrowserAssetProvider:
    name = "stimulus"

    def matches(self, html: str) -> bool:
        return bool(_STIMULUS_ATTR_RE.search(html))

    def get_assets(self) -> tuple[BrowserAsset, ...]:
        return (
            BrowserAsset(
                name="stimulus",
                kind="script",
                placement="head",
                cdn_url="https://unpkg.com/@hotwired/stimulus@3.2.2/dist/stimulus.umd.js",
                vendor_file=BrowserAssetFile(
                    relative_path="js/stimulus.umd.js",
                    source_url="https://unpkg.com/@hotwired/stimulus@3.2.2/dist/stimulus.umd.js",
                    npm_package="@hotwired/stimulus@3.2.2",
                    npm_dist_path="@hotwired/stimulus/dist/stimulus.umd.js",
                ),
                presence_tokens=(
                    "@hotwired/stimulus",
                    "stimulus.umd.js",
                ),
            ),
        )


__all__ = ["StimulusBrowserAssetProvider"]
