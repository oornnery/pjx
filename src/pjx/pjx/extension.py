from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from importlib.metadata import entry_points
from typing import Any

from pjx.assets import BrowserAssetProvider
from pjx.core.types import Processor

logger = logging.getLogger("pjx.extensions")


class PJXExtension(ABC):
    """Base class for PJX extensions.

    Subclass and override any hook to contribute processors,
    Jinja2 globals, or browser asset providers.
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    def get_processors(self) -> Iterable[tuple[int, Processor]]:
        return ()

    def get_jinja_globals(self) -> dict[str, Callable[..., Any]]:
        return {}

    def get_asset_provider(self) -> BrowserAssetProvider | None:
        return None


class ExtensionRegistry:
    """Collects extensions from explicit registration and entry-point discovery."""

    def __init__(self) -> None:
        self._extensions: dict[str, PJXExtension] = {}

    def register(self, ext: PJXExtension) -> None:
        if ext.name in self._extensions:
            logger.debug("Extension %r already registered, skipping", ext.name)
            return
        self._extensions[ext.name] = ext

    def discover(self) -> None:
        for ep in entry_points(group="pjx.extensions"):
            try:
                obj = ep.load()
                ext = obj() if isinstance(obj, type) else obj
                if not isinstance(ext, PJXExtension):
                    logger.warning("Entry point %r is not a PJXExtension, skipping", ep.name)
                    continue
                self.register(ext)
            except Exception:
                logger.exception("Failed to load extension %r", ep.name)

    @property
    def extensions(self) -> list[PJXExtension]:
        return list(self._extensions.values())


__all__ = [
    "ExtensionRegistry",
    "PJXExtension",
]
