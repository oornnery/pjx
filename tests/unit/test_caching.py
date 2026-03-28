"""Tests for pjx.caching — HTTP response cache, ETag, request-scoped memo."""

import time

import pytest

from pjx.caching import (
    ResponseCache,
    _CacheEntry,
    cache,
    get_cache_meta,
    memo,
    reset_request_memo,
)


class TestResponseCache:
    def test_put_and_get(self) -> None:
        rc = ResponseCache(max_size=10)
        entry = _CacheEntry(
            body=b"hello",
            content_type="text/html",
            status_code=200,
            created_at=time.monotonic(),
            ttl=3600,
            revalidate=0,
        )
        rc.put("key1", entry)
        assert rc.get("key1") is entry

    def test_get_missing_returns_none(self) -> None:
        rc = ResponseCache()
        assert rc.get("nonexistent") is None

    def test_expired_entry_returns_none(self) -> None:
        rc = ResponseCache()
        entry = _CacheEntry(
            body=b"old",
            content_type="text/html",
            status_code=200,
            created_at=time.monotonic() - 100,
            ttl=1,
            revalidate=0,
        )
        rc.put("expired", entry)
        assert rc.get("expired") is None

    def test_stale_while_revalidate(self) -> None:
        rc = ResponseCache()
        entry = _CacheEntry(
            body=b"stale",
            content_type="text/html",
            status_code=200,
            created_at=time.monotonic() - 10,
            ttl=5,
            revalidate=60,
        )
        rc.put("swr", entry)
        # Entry is expired (age=10 > ttl=5) but within revalidate window (10 < 5+60)
        assert rc.get("swr") is entry

    def test_fully_expired_with_revalidate(self) -> None:
        rc = ResponseCache()
        entry = _CacheEntry(
            body=b"gone",
            content_type="text/html",
            status_code=200,
            created_at=time.monotonic() - 200,
            ttl=5,
            revalidate=60,
        )
        rc.put("gone", entry)
        # age=200 > ttl+revalidate=65 → truly expired
        assert rc.get("gone") is None

    def test_lru_eviction(self) -> None:
        rc = ResponseCache(max_size=2)
        for i in range(3):
            rc.put(
                f"k{i}",
                _CacheEntry(
                    body=f"v{i}".encode(),
                    content_type="text/html",
                    status_code=200,
                    created_at=time.monotonic(),
                    ttl=3600,
                    revalidate=0,
                ),
            )
        # k0 should have been evicted
        assert rc.get("k0") is None
        assert rc.get("k1") is not None
        assert rc.get("k2") is not None

    def test_invalidate(self) -> None:
        rc = ResponseCache()
        entry = _CacheEntry(
            body=b"x",
            content_type="text/html",
            status_code=200,
            created_at=time.monotonic(),
            ttl=3600,
            revalidate=0,
        )
        rc.put("del_me", entry)
        rc.invalidate("del_me")
        assert rc.get("del_me") is None

    def test_clear(self) -> None:
        rc = ResponseCache()
        for i in range(5):
            rc.put(
                f"k{i}",
                _CacheEntry(
                    body=b"x",
                    content_type="text/html",
                    status_code=200,
                    created_at=time.monotonic(),
                    ttl=3600,
                    revalidate=0,
                ),
            )
        rc.clear()
        assert rc.size == 0

    def test_size(self) -> None:
        rc = ResponseCache()
        assert rc.size == 0
        rc.put(
            "k",
            _CacheEntry(
                body=b"x",
                content_type="text/html",
                status_code=200,
                created_at=time.monotonic(),
                ttl=3600,
                revalidate=0,
            ),
        )
        assert rc.size == 1


class TestCacheDecorator:
    def test_attaches_meta(self) -> None:
        @cache(ttl=60, revalidate=10)
        async def handler():
            pass

        meta = get_cache_meta(handler)
        assert meta is not None
        assert meta.ttl == 60
        assert meta.revalidate == 10

    def test_no_meta_on_undecorated(self) -> None:
        async def handler():
            pass

        assert get_cache_meta(handler) is None

    def test_default_values(self) -> None:
        @cache()
        async def handler():
            pass

        meta = get_cache_meta(handler)
        assert meta is not None
        assert meta.ttl == 3600
        assert meta.revalidate == 0


class TestMemo:
    def test_sync_memo(self) -> None:
        call_count = 0
        reset_request_memo()

        @memo
        def expensive(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        assert expensive(5) == 10
        assert expensive(5) == 10
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_memo(self) -> None:
        call_count = 0
        reset_request_memo()

        @memo
        async def expensive(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        assert await expensive(5) == 10
        assert await expensive(5) == 10
        assert call_count == 1

    def test_different_args_not_cached(self) -> None:
        call_count = 0
        reset_request_memo()

        @memo
        def func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x

        func(1)
        func(2)
        assert call_count == 2

    def test_reset_clears_memo(self) -> None:
        call_count = 0
        reset_request_memo()

        @memo
        def func() -> int:
            nonlocal call_count
            call_count += 1
            return 42

        func()
        reset_request_memo()
        func()
        assert call_count == 2
