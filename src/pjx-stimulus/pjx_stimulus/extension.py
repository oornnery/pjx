from __future__ import annotations

from collections.abc import Iterable

from pjx.assets import BrowserAssetProvider
from pjx.core.types import Processor
from pjx.extension import PJXExtension
from pjx_stimulus.assets import StimulusBrowserAssetProvider
from pjx_stimulus.processor import StimulusAliasProcessor


class StimulusExtension(PJXExtension):
    @property
    def name(self) -> str:
        return "stimulus"

    def get_processors(self) -> Iterable[tuple[int, Processor]]:
        return [(40, StimulusAliasProcessor())]

    def get_asset_provider(self) -> BrowserAssetProvider:
        return StimulusBrowserAssetProvider()
