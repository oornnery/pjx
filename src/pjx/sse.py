"""PJX SSE (Server-Sent Events) helpers with connection limiting."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

from pjx.engine import EngineProtocol

logger = logging.getLogger("pjx.sse")

# Global connection tracker: client_ip → active connection count
_active_connections: dict[str, int] = {}
_connections_lock = asyncio.Lock()


async def _acquire_connection(client_ip: str, max_per_ip: int) -> bool:
    """Try to acquire a connection slot for the given IP.

    Args:
        client_ip: The client's IP address.
        max_per_ip: Maximum concurrent connections per IP.

    Returns:
        True if the connection was acquired, False if limit exceeded.
    """
    async with _connections_lock:
        current = _active_connections.get(client_ip, 0)
        if current >= max_per_ip:
            return False
        _active_connections[client_ip] = current + 1
        return True


async def _release_connection(client_ip: str) -> None:
    """Release a connection slot for the given IP."""
    async with _connections_lock:
        current = _active_connections.get(client_ip, 0)
        if current <= 1:
            _active_connections.pop(client_ip, None)
        else:
            _active_connections[client_ip] = current - 1


class EventStream:
    """Async context for sending SSE events with connection limiting.

    Args:
        request: The FastAPI request object.
        engine: Optional template engine for rendering HTML fragments.
        max_connections_per_ip: Maximum concurrent SSE connections per client IP.
        max_duration: Maximum stream duration in seconds (0 = unlimited).
    """

    def __init__(
        self,
        request: Request,
        engine: EngineProtocol | None = None,
        max_connections_per_ip: int = 10,
        max_duration: int = 3600,
    ) -> None:
        self._request = request
        self._engine = engine
        self._queue: asyncio.Queue[str | None] = asyncio.Queue()
        self._max_connections_per_ip = max_connections_per_ip
        self._max_duration = max_duration
        self._client_ip = request.client.host if request.client else "unknown"

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
        """Generate SSE messages from the queue with connection tracking."""
        acquired = await _acquire_connection(
            self._client_ip, self._max_connections_per_ip
        )
        if not acquired:
            logger.warning("SSE connection limit exceeded for %s", self._client_ip)
            yield "event: error\ndata: Too many connections\n\n"
            return

        start_time = time.monotonic()
        try:
            while True:
                if await self._request.is_disconnected():
                    break
                # Check duration limit
                if (
                    self._max_duration > 0
                    and time.monotonic() - start_time > self._max_duration
                ):
                    logger.info("SSE max duration reached for %s", self._client_ip)
                    break
                msg = await self._queue.get()
                if msg is None:
                    break
                yield msg
        finally:
            await _release_connection(self._client_ip)

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


def check_sse_limit(request: Request, max_per_ip: int = 10) -> None:
    """Pre-check SSE connection limit before creating a stream.

    Raises HTTPException(429) if the limit is exceeded. Use this in
    route handlers before creating an EventStream.

    Args:
        request: The FastAPI request object.
        max_per_ip: Maximum concurrent connections per IP.
    """
    client_ip = request.client.host if request.client else "unknown"
    current = _active_connections.get(client_ip, 0)
    if current >= max_per_ip:
        raise HTTPException(
            status_code=429,
            detail="Too many SSE connections",
        )
