"""PJX SSE (Server-Sent Events) helpers."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Request
from fastapi.responses import StreamingResponse

from pjx.engine import EngineProtocol


class EventStream:
    """Async context for sending SSE events.

    Args:
        request: The FastAPI request object.
        engine: Optional template engine for rendering HTML fragments.
    """

    def __init__(
        self,
        request: Request,
        engine: EngineProtocol | None = None,
    ) -> None:
        self._request = request
        self._engine = engine
        self._queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def send(self, event: str, data: str) -> None:
        """Send a raw SSE event.

        Args:
            event: Event name.
            data: Event data (string).
        """
        msg = f"event: {event}\ndata: {data}\n\n"
        await self._queue.put(msg)

    async def send_html(
        self,
        event: str,
        template: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Render a template and send it as an SSE event.

        Args:
            event: Event name.
            template: Template source string.
            context: Template context variables.
        """
        if self._engine is None:
            msg = "engine required for send_html"
            raise RuntimeError(msg)
        html = self._engine.render_string(template, context or {})
        await self.send(event, html)

    async def close(self) -> None:
        """Signal the stream to close."""
        await self._queue.put(None)

    async def _generate(self) -> AsyncGenerator[str, None]:
        """Generate SSE messages from the queue."""
        while True:
            if await self._request.is_disconnected():
                break
            msg = await self._queue.get()
            if msg is None:
                break
            yield msg

    def response(self) -> StreamingResponse:
        """Create a StreamingResponse for this event stream."""
        return StreamingResponse(
            self._generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
