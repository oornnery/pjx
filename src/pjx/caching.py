"""HTTP response caching — route-level cache, ETag, request-scoped memoization.

Provides three caching layers inspired by Next.js:

1. **Route cache** — ``@cache(ttl=3600)`` decorator caches full HTML responses
2. **ETag middleware** — automatic ETag generation and 304 responses
3. **Request memo** — ``@memo`` caches function results within a single request
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections import OrderedDict
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response as StarletteResponse

logger = logging.getLogger("pjx")

# ---------------------------------------------------------------------------
# Route-level response cache
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    """Single cached response."""

    body: bytes
    content_type: str
    status_code: int
    created_at: float
    ttl: int
    revalidate: int


class ResponseCache:
    """In-memory LRU cache for full HTTP responses.

    Args:
        max_size: Maximum number of cached entries.
    """

    def __init__(self, max_size: int = 1000) -> None:
        self._store: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._max_size = max_size

    def get(self, key: str) -> _CacheEntry | None:
        """Retrieve a cached entry, returning None if missing or expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        age = time.monotonic() - entry.created_at
        if age > entry.ttl:
            # Expired — check if within revalidate window (stale-while-revalidate)
            if entry.revalidate > 0 and age < entry.ttl + entry.revalidate:
                return entry  # stale but usable
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return entry

    def put(self, key: str, entry: _CacheEntry) -> None:
        """Store a cache entry, evicting LRU if over capacity."""
        self._store[key] = entry
        self._store.move_to_end(key)
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def invalidate(self, key: str) -> None:
        """Remove a specific cache entry."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all cache entries."""
        self._store.clear()

    @property
    def size(self) -> int:
        """Current number of cached entries."""
        return len(self._store)


# Global response cache instance
_response_cache = ResponseCache()


def get_response_cache() -> ResponseCache:
    """Get the global response cache instance."""
    return _response_cache


def cache_key(request: Request) -> str:
    """Generate a cache key from the request method + URL."""
    return f"{request.method}:{request.url.path}?{request.url.query}"


# ---------------------------------------------------------------------------
# @cache() decorator
# ---------------------------------------------------------------------------

_CACHE_META_ATTR = "_pjx_cache_meta"


@dataclass(frozen=True, slots=True)
class CacheMeta:
    """Cache configuration attached to a route handler."""

    ttl: int
    revalidate: int


def cache(ttl: int = 3600, revalidate: int = 0) -> Callable:
    """Decorator to enable response caching on a page route.

    Args:
        ttl: Time-to-live in seconds for the cached response.
        revalidate: Stale-while-revalidate window in seconds (ISR-like).
            During this window, stale content is served while a background
            revalidation occurs.
    """

    def decorator[F: Callable](func: F) -> F:
        setattr(func, _CACHE_META_ATTR, CacheMeta(ttl=ttl, revalidate=revalidate))
        return func

    return decorator


def get_cache_meta(func: Callable) -> CacheMeta | None:
    """Extract cache metadata from a decorated function."""
    return getattr(func, _CACHE_META_ATTR, None)


# ---------------------------------------------------------------------------
# ETag middleware
# ---------------------------------------------------------------------------


class ETagMiddleware(BaseHTTPMiddleware):
    """Middleware that adds ETag headers and returns 304 Not Modified.

    For GET responses with a body, computes an ETag from the response
    content hash.  If the request includes ``If-None-Match`` matching
    the ETag, returns 304 with no body.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        response = await call_next(request)

        if request.method != "GET" or response.status_code != 200:
            return response

        # Read body for ETag computation
        body = b""
        async for chunk in response.body_iterator:  # ty: ignore[unresolved-attribute]
            body += chunk if isinstance(chunk, bytes) else chunk.encode()

        etag = f'"{hashlib.md5(body).hexdigest()}"'  # noqa: S324

        # Check If-None-Match
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match == etag:
            return Response(status_code=304, headers={"ETag": etag})

        return Response(
            content=body,
            status_code=response.status_code,
            headers={**dict(response.headers), "ETag": etag},
            media_type=response.media_type,
        )


# ---------------------------------------------------------------------------
# Request-scoped memoization
# ---------------------------------------------------------------------------

_request_memo: ContextVar[dict[str, Any]] = ContextVar("pjx_request_memo")


def memo(func: Callable) -> Callable:
    """Decorator to memoize function results within a single request.

    Uses ``contextvars`` so each request gets its own memo store.
    The memo key is derived from the function name and arguments.

    Example::

        @memo
        async def get_user(user_id: int):
            return await db.fetch_user(user_id)
    """
    import inspect

    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        store = _request_memo.get({})
        key = f"{func.__qualname__}:{args}:{kwargs}"  # ty: ignore[unresolved-attribute]
        if key in store:
            return store[key]
        result = await func(*args, **kwargs)
        store[key] = result
        _request_memo.set(store)
        return result

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        store = _request_memo.get({})
        key = f"{func.__qualname__}:{args}:{kwargs}"  # ty: ignore[unresolved-attribute]
        if key in store:
            return store[key]
        result = func(*args, **kwargs)
        store[key] = result
        _request_memo.set(store)
        return result

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def reset_request_memo() -> None:
    """Reset the request-scoped memo store. Called at request start."""
    _request_memo.set({})
