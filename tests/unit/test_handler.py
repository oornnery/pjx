"""Tests for RouteHandler and APIRoute helpers."""

from __future__ import annotations

from pjx.handler import APIRoute, RouteHandler


class TestRouteHandler:
    """Test RouteHandler decorator registration."""

    def test_default_methods(self) -> None:
        handler = RouteHandler()
        assert handler.methods == ["GET"]

    def test_get_decorator(self) -> None:
        handler = RouteHandler()

        @handler.get
        async def get_fn():
            return {"data": True}

        assert "GET" in handler._handlers
        assert handler._handlers["GET"] is get_fn

    def test_post_decorator_adds_method(self) -> None:
        handler = RouteHandler()

        @handler.post
        async def post_fn():
            return {}

        assert "POST" in handler.methods
        assert handler._handlers["POST"] is post_fn

    def test_multiple_verbs(self) -> None:
        handler = RouteHandler()

        @handler.get
        async def get_fn():
            return {}

        @handler.post
        async def post_fn():
            return {}

        @handler.delete
        async def delete_fn():
            return {}

        assert set(handler.methods) == {"GET", "POST", "DELETE"}
        assert len(handler._handlers) == 3

    def test_put_decorator(self) -> None:
        handler = RouteHandler()

        @handler.put
        async def put_fn():
            return {}

        assert "PUT" in handler.methods

    def test_patch_decorator(self) -> None:
        handler = RouteHandler()

        @handler.patch
        async def patch_fn():
            return {}

        assert "PATCH" in handler.methods

    def test_no_duplicate_methods(self) -> None:
        handler = RouteHandler()

        @handler.get
        async def get_fn():
            return {}

        assert handler.methods.count("GET") == 1


class TestAPIRoute:
    """Test APIRoute decorator registration."""

    def test_empty_handlers(self) -> None:
        route = APIRoute()
        assert route._handlers == {}

    def test_get_decorator(self) -> None:
        route = APIRoute()

        @route.get
        async def get_fn():
            return []

        assert "GET" in route._handlers

    def test_multiple_verbs(self) -> None:
        route = APIRoute()

        @route.get
        async def get_fn():
            return []

        @route.post
        async def post_fn():
            return {"created": True}

        assert len(route._handlers) == 2
        assert "GET" in route._handlers
        assert "POST" in route._handlers

    def test_decorator_returns_original_function(self) -> None:
        route = APIRoute()

        @route.get
        async def get_fn():
            return []

        # The decorator should return the original function
        assert get_fn is route._handlers["GET"]
