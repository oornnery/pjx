"""Streaming HTML responses — progressive rendering with HTMX OOB swaps.

Renders the initial page shell immediately (with fallback content for
``<Await>`` blocks), then streams resolved content as chunked HTML
using HTMX out-of-band (OOB) swap fragments.

This provides a Suspense-like streaming experience:
1. User sees the page shell + loading indicators immediately
2. Each ``<Await>`` block resolves independently
3. Resolved content swaps in-place via HTMX ``hx-swap-oob``
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Any

from starlette.responses import StreamingResponse

logger = logging.getLogger("pjx")


@dataclass(frozen=True, slots=True)
class AwaitBlock:
    """A deferred block that resolves asynchronously.

    Args:
        block_id: Unique DOM ID for the block.
        resolve: Async callable that returns rendered HTML.
    """

    block_id: str
    resolve: Callable[[], Any]


class StreamingRenderer:
    """Renders a page with streaming support for deferred blocks.

    Args:
        shell_html: The initial page HTML with placeholder ``<div>`` elements
            for each ``AwaitBlock``.
        blocks: List of deferred blocks to resolve and stream.
        content_type: Response content type.
    """

    def __init__(
        self,
        shell_html: str,
        blocks: list[AwaitBlock] | None = None,
        content_type: str = "text/html",
    ) -> None:
        self._shell = shell_html
        self._blocks = blocks or []
        self._content_type = content_type

    def add_block(self, resolve: Callable[[], Any], block_id: str | None = None) -> str:
        """Add a deferred block and return its DOM ID.

        Args:
            resolve: Async or sync callable returning rendered HTML.
            block_id: Optional custom ID. Auto-generated if not provided.

        Returns:
            The block's DOM ID (for placing the placeholder).
        """
        bid = block_id or f"pjx-await-{uuid.uuid4().hex[:8]}"
        self._blocks.append(AwaitBlock(block_id=bid, resolve=resolve))
        return bid

    def response(self) -> StreamingResponse:
        """Create a StreamingResponse that sends the shell then deferred blocks."""
        return StreamingResponse(
            self._stream(),
            media_type=self._content_type,
        )

    async def _stream(self) -> AsyncGenerator[str, None]:
        """Stream the shell HTML followed by OOB swap fragments."""
        # Send the initial shell
        yield self._shell

        if not self._blocks:
            return

        # Resolve blocks concurrently and stream results as they complete
        tasks = {
            asyncio.ensure_future(self._resolve_block(block)): block
            for block in self._blocks
        }

        for coro in asyncio.as_completed(tasks):
            block_id, html = await coro
            if html is not None:
                # HTMX out-of-band swap: replaces the placeholder div
                yield (f'\n<div id="{block_id}" hx-swap-oob="innerHTML">{html}</div>')

    @staticmethod
    async def _resolve_block(block: AwaitBlock) -> tuple[str, str | None]:
        """Resolve a single block, returning (block_id, html) or (block_id, None) on error."""
        try:
            import inspect

            result = block.resolve()
            if inspect.isawaitable(result):
                result = await result
            return block.block_id, str(result)
        except Exception:
            logger.warning(
                "failed to resolve streaming block: %s",
                block.block_id,
                exc_info=True,
            )
            return block.block_id, None


def streaming_placeholder(block_id: str, fallback_html: str = "") -> str:
    """Generate a placeholder div for a streaming block.

    Args:
        block_id: The block's unique DOM ID.
        fallback_html: HTML to show while the block is loading.

    Returns:
        HTML string with the placeholder div.
    """
    return f'<div id="{block_id}">{fallback_html}</div>'
