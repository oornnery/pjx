from __future__ import annotations

from collections.abc import Iterable

from pjx.assets import BrowserAssetProvider
from pjx.core.types import Processor
from pjx.extension import PJXExtension
from pjx_htmx.assets import HTMXBrowserAssetProvider
from pjx_htmx.processor import HTMXAliasProcessor


class HTMXExtension(PJXExtension):
    @property
    def name(self) -> str:
        return "htmx"

    def get_processors(self) -> Iterable[tuple[int, Processor]]:
        return [(40, HTMXAliasProcessor())]

    def get_asset_provider(self) -> BrowserAssetProvider:
        return HTMXBrowserAssetProvider()
