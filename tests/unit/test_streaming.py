"""Tests for pjx.streaming — streaming HTML with HTMX OOB swaps."""

import pytest

from pjx.streaming import AwaitBlock, StreamingRenderer, streaming_placeholder


class TestStreamingPlaceholder:
    def test_basic_placeholder(self) -> None:
        html = streaming_placeholder("block-1")
        assert html == '<div id="block-1"></div>'

    def test_placeholder_with_fallback(self) -> None:
        html = streaming_placeholder("block-1", "<p>Loading...</p>")
        assert html == '<div id="block-1"><p>Loading...</p></div>'


class TestStreamingRenderer:
    @pytest.mark.asyncio
    async def test_stream_shell_only(self) -> None:
        renderer = StreamingRenderer("<h1>Hello</h1>")
        chunks = []
        async for chunk in renderer._stream():
            chunks.append(chunk)
        assert len(chunks) == 1
        assert chunks[0] == "<h1>Hello</h1>"

    @pytest.mark.asyncio
    async def test_stream_with_async_block(self) -> None:
        async def resolve():
            return "<p>Loaded!</p>"

        renderer = StreamingRenderer(
            '<div id="b1">Loading...</div>',
            blocks=[AwaitBlock(block_id="b1", resolve=resolve)],
        )
        chunks = []
        async for chunk in renderer._stream():
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == '<div id="b1">Loading...</div>'
        assert 'hx-swap-oob="innerHTML"' in chunks[1]
        assert "<p>Loaded!</p>" in chunks[1]

    @pytest.mark.asyncio
    async def test_stream_with_sync_block(self) -> None:
        def resolve():
            return "<p>Sync!</p>"

        renderer = StreamingRenderer(
            "<main></main>",
            blocks=[AwaitBlock(block_id="sync-b", resolve=resolve)],
        )
        chunks = []
        async for chunk in renderer._stream():
            chunks.append(chunk)

        assert len(chunks) == 2
        assert "<p>Sync!</p>" in chunks[1]

    @pytest.mark.asyncio
    async def test_stream_multiple_blocks(self) -> None:
        async def resolve_a():
            return "A"

        async def resolve_b():
            return "B"

        renderer = StreamingRenderer(
            "<main></main>",
            blocks=[
                AwaitBlock(block_id="a", resolve=resolve_a),
                AwaitBlock(block_id="b", resolve=resolve_b),
            ],
        )
        chunks = []
        async for chunk in renderer._stream():
            chunks.append(chunk)

        # Shell + 2 blocks
        assert len(chunks) == 3
        all_content = "".join(chunks)
        assert ">A</div>" in all_content
        assert ">B</div>" in all_content

    @pytest.mark.asyncio
    async def test_failed_block_yields_nothing(self) -> None:
        async def failing():
            msg = "boom"
            raise RuntimeError(msg)

        renderer = StreamingRenderer(
            "<main></main>",
            blocks=[AwaitBlock(block_id="fail", resolve=failing)],
        )
        chunks = []
        async for chunk in renderer._stream():
            chunks.append(chunk)

        # Only shell — failed block produces no OOB swap
        assert len(chunks) == 1

    def test_add_block_returns_id(self) -> None:
        renderer = StreamingRenderer("<main></main>")
        bid = renderer.add_block(lambda: "content", block_id="custom-id")
        assert bid == "custom-id"
        assert len(renderer._blocks) == 1

    def test_add_block_auto_id(self) -> None:
        renderer = StreamingRenderer("<main></main>")
        bid = renderer.add_block(lambda: "content")
        assert bid.startswith("pjx-await-")

    def test_response_returns_streaming(self) -> None:
        renderer = StreamingRenderer("<h1>Test</h1>")
        response = renderer.response()
        assert response.media_type == "text/html"
