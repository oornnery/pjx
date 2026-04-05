from __future__ import annotations

import contextlib
from dataclasses import dataclass
from pathlib import Path

from pjx.core.types import PreprocessResult


@dataclass(slots=True)
class CacheEntry:
    result: PreprocessResult
    mtime: float


class TemplateCache:
    """Mtime-based preprocess cache. Invalidates when source file changes."""

    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}

    def get(self, template: str, filename: str | None = None) -> PreprocessResult | None:
        entry = self._entries.get(template)
        if entry is None:
            return None
        if filename:
            try:
                current_mtime = Path(filename).stat().st_mtime
                if current_mtime > entry.mtime:
                    return None
            except OSError:
                return None
        return entry.result

    def put(self, template: str, result: PreprocessResult, filename: str | None = None) -> None:
        mtime = 0.0
        if filename:
            with contextlib.suppress(OSError):
                mtime = Path(filename).stat().st_mtime
        self._entries[template] = CacheEntry(result=result, mtime=mtime)

    def invalidate(self, template: str) -> None:
        self._entries.pop(template, None)

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
