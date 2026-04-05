from __future__ import annotations

import re

from pjx.assets import BrowserAsset, BrowserAssetFile

_TAILWIND_ATTR_RE = re.compile(r'type=["\']text/tailwindcss["\']', re.IGNORECASE)
_TAILWIND_CLASS_RE = re.compile(
    r'class\s*=\s*["\'][^"\']*\b(?:'
    r'(?:sm|md|lg|xl|2xl|hover|focus|dark):'
    r'|(?:text|bg|border|rounded|flex|grid|items|justify|gap|space|p|px|py|pt|pr|pb|pl|m|mx|my|mt|mr|mb|ml|w|h|min-w|max-w|min-h|max-h|font|tracking|leading|shadow|ring|opacity|z|top|right|bottom|left|inset)-'
    r')[^"\']*["\']',
    re.IGNORECASE,
)


class TailwindBrowserAssetProvider:
    name = "tailwind"

    def matches(self, html: str) -> bool:
        return bool(_TAILWIND_ATTR_RE.search(html) or _TAILWIND_CLASS_RE.search(html))

    def get_assets(self) -> tuple[BrowserAsset, ...]:
        return (
            BrowserAsset(
                name="tailwind",
                kind="script",
                placement="head",
                cdn_url="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4",
                vendor_file=BrowserAssetFile(
                    relative_path="js/tailwind.browser.js",
                    source_url="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4",
                    npm_package="@tailwindcss/browser@4",
                    npm_dist_path="@tailwindcss/browser/dist/index.global.js",
                ),
                presence_tokens=(
                    "@tailwindcss/browser",
                    "tailwind.browser.js",
                    "cdn.tailwindcss.com",
                ),
            ),
        )


__all__ = ["TailwindBrowserAssetProvider"]
