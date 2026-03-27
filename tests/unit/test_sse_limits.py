"""Tests for SSE connection limiting in pjx.sse."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pjx.sse import (
    EventStream,
    _acquire_connection,
    _active_connections,
    _release_connection,
    check_sse_limit,
)


@pytest.fixture(autouse=True)
def _clear_connections():
    """Reset global connection tracker between tests."""
    _active_connections.clear()
    yield
    _active_connections.clear()


def _make_request(client_ip: str = "127.0.0.1") -> MagicMock:
    """Create a mock Request with the given client IP."""
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = client_ip
    request.is_disconnected = AsyncMock(return_value=False)
    return request


class TestConnectionTracking:
    @pytest.mark.asyncio
    async def test_acquire_and_release(self) -> None:
        assert await _acquire_connection("1.2.3.4", 5)
        assert _active_connections["1.2.3.4"] == 1
        await _release_connection("1.2.3.4")
        assert "1.2.3.4" not in _active_connections

    @pytest.mark.asyncio
    async def test_acquire_respects_limit(self) -> None:
        for _ in range(3):
            assert await _acquire_connection("1.2.3.4", 3)
        # 4th should fail
        assert not await _acquire_connection("1.2.3.4", 3)

    @pytest.mark.asyncio
    async def test_different_ips_independent(self) -> None:
        assert await _acquire_connection("1.1.1.1", 1)
        assert await _acquire_connection("2.2.2.2", 1)
        # Same IP again should fail
        assert not await _acquire_connection("1.1.1.1", 1)

    @pytest.mark.asyncio
    async def test_release_decrements(self) -> None:
        await _acquire_connection("1.2.3.4", 5)
        await _acquire_connection("1.2.3.4", 5)
        assert _active_connections["1.2.3.4"] == 2
        await _release_connection("1.2.3.4")
        assert _active_connections["1.2.3.4"] == 1

    @pytest.mark.asyncio
    async def test_release_nonexistent_safe(self) -> None:
        # Should not raise
        await _release_connection("9.9.9.9")


class TestEventStreamLimits:
    @pytest.mark.asyncio
    async def test_stream_acquires_and_releases(self) -> None:
        request = _make_request("10.0.0.1")
        # Disconnect after first message
        request.is_disconnected = AsyncMock(side_effect=[False, True])

        stream = EventStream(request, max_connections_per_ip=5)
        await stream.send("test", "data")

        messages = []
        async for msg in stream._generate():
            messages.append(msg)

        assert len(messages) == 1
        # Connection should be released
        assert "10.0.0.1" not in _active_connections

    @pytest.mark.asyncio
    async def test_stream_rejects_over_limit(self) -> None:
        request = _make_request("10.0.0.2")

        # Fill up the limit
        for _ in range(2):
            await _acquire_connection("10.0.0.2", 2)

        stream = EventStream(request, max_connections_per_ip=2)
        messages = []
        async for msg in stream._generate():
            messages.append(msg)

        # Should get an error message
        assert len(messages) == 1
        assert "Too many connections" in messages[0]


class TestCheckSSELimit:
    def test_under_limit_passes(self) -> None:
        request = _make_request("5.5.5.5")
        # Should not raise
        check_sse_limit(request, max_per_ip=10)

    def test_at_limit_raises_429(self) -> None:
        _active_connections["5.5.5.5"] = 10
        request = _make_request("5.5.5.5")
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            check_sse_limit(request, max_per_ip=10)
        assert exc_info.value.status_code == 429
