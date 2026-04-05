from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pjx.assets import BrowserAssetProvider
from pjx.extension import PJXExtension
from pjx_tailwind.assets import TailwindBrowserAssetProvider
from pjx_tailwind.cn import cn


class TailwindExtension(PJXExtension):
    @property
    def name(self) -> str:
        return "tailwind"

    def get_jinja_globals(self) -> dict[str, Callable[..., Any]]:
        return {"cn": cn}

    def get_asset_provider(self) -> BrowserAssetProvider:
        return TailwindBrowserAssetProvider()
