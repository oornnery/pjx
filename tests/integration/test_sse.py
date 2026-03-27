"""Tests for pjx.sse — Server-Sent Events helpers."""

import pytest

from pjx.engine import Jinja2Engine
from pjx.sse import EventStream


class MockClient:
    """Minimal mock of a client address."""

    host: str = "127.0.0.1"


class MockRequest:
    """Minimal mock of a FastAPI Request for SSE testing."""

    def __init__(self) -> None:
        self._disconnected = False
        self.client = MockClient()

    async def is_disconnected(self) -> bool:
        return self._disconnected

    def disconnect(self) -> None:
        self._disconnected = True


@pytest.mark.asyncio
class TestEventStream:
    async def test_send_event(self) -> None:
        request = MockRequest()
        stream = EventStream(request)  # type: ignore[arg-type]

        await stream.send("update", "hello")
        await stream.close()

        messages = []
        async for msg in stream._generate():
            messages.append(msg)

        assert len(messages) == 1
        assert "event: update" in messages[0]
        assert "data: hello" in messages[0]

    async def test_send_html(self) -> None:
        request = MockRequest()
        engine = Jinja2Engine()
        stream = EventStream(request, engine=engine)  # type: ignore[arg-type]

        await stream.send_html("render", "Hello {{ name }}", {"name": "World"})
        await stream.close()

        messages = []
        async for msg in stream._generate():
            messages.append(msg)

        assert len(messages) == 1
        assert "Hello World" in messages[0]

    async def test_send_html_no_engine_raises(self) -> None:
        request = MockRequest()
        stream = EventStream(request)  # type: ignore[arg-type]

        with pytest.raises(RuntimeError, match="engine required"):
            await stream.send_html("render", "template", {})

    async def test_response_type(self) -> None:
        request = MockRequest()
        stream = EventStream(request)  # type: ignore[arg-type]
        resp = stream.response()
        assert resp.media_type == "text/event-stream"
