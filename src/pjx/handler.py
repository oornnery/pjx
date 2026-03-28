"""Route handler helpers for file-based routing.

Colocated ``.py`` files use these helpers to define handlers:

Page handler::

    from pjx import RouteHandler

    handler = RouteHandler()

    @handler.get
    async def get(slug: str):
        return {"post": await fetch_post(slug)}

API route::

    from pjx import APIRoute

    route = APIRoute()

    @route.get
    async def get():
        return [{"id": 1, "name": "Alice"}]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class RouteHandler:
    """Handler for page routes with colocated ``.py`` files.

    Decorate methods to register them as HTTP verb handlers.
    The return value is passed as template context.

    Args:
        methods: HTTP methods this handler supports. Auto-populated
            from decorated methods if not set explicitly.
    """

    methods: list[str] = field(default_factory=lambda: ["GET"])
    _handlers: dict[str, Callable] = field(default_factory=dict, repr=False)
    _actions: dict[str, Callable] = field(default_factory=dict, repr=False)
    _static_params_fn: Callable | None = field(default=None, repr=False)

    def get(self, fn: Callable) -> Callable:
        """Register a GET handler."""
        self._handlers["GET"] = fn
        if "GET" not in self.methods:
            self.methods.append("GET")
        return fn

    def post(self, fn: Callable) -> Callable:
        """Register a POST handler."""
        self._handlers["POST"] = fn
        if "POST" not in self.methods:
            self.methods.append("POST")
        return fn

    def put(self, fn: Callable) -> Callable:
        """Register a PUT handler."""
        self._handlers["PUT"] = fn
        if "PUT" not in self.methods:
            self.methods.append("PUT")
        return fn

    def delete(self, fn: Callable) -> Callable:
        """Register a DELETE handler."""
        self._handlers["DELETE"] = fn
        if "DELETE" not in self.methods:
            self.methods.append("DELETE")
        return fn

    def patch(self, fn: Callable) -> Callable:
        """Register a PATCH handler."""
        self._handlers["PATCH"] = fn
        if "PATCH" not in self.methods:
            self.methods.append("PATCH")
        return fn

    def static_params(self, fn: Callable) -> Callable:
        """Register a function that returns static parameter combinations.

        Used by ``pjx build`` to pre-render pages with dynamic segments.

        Example::

            @handler.static_params
            async def get_params():
                return [{"slug": "hello"}, {"slug": "world"}]
        """
        self._static_params_fn = fn
        return fn

    def action(self, name: str) -> Callable:
        """Register a server action handler.

        Server actions are auto-registered as POST routes at
        ``/_pjx/actions/{name}``.

        Args:
            name: Action identifier matching the frontmatter ``action`` declaration.
        """

        def decorator(fn: Callable) -> Callable:
            self._actions[name] = fn
            return fn

        return decorator


@dataclass
class APIRoute:
    """Handler for API routes (JSON responses, no template rendering).

    Place in ``pages/api/*.py`` files with a module-level ``route`` variable.
    """

    _handlers: dict[str, Callable] = field(default_factory=dict, repr=False)

    def get(self, fn: Callable) -> Callable:
        """Register a GET handler."""
        self._handlers["GET"] = fn
        return fn

    def post(self, fn: Callable) -> Callable:
        """Register a POST handler."""
        self._handlers["POST"] = fn
        return fn

    def put(self, fn: Callable) -> Callable:
        """Register a PUT handler."""
        self._handlers["PUT"] = fn
        return fn

    def delete(self, fn: Callable) -> Callable:
        """Register a DELETE handler."""
        self._handlers["DELETE"] = fn
        return fn

    def patch(self, fn: Callable) -> Callable:
        """Register a PATCH handler."""
        self._handlers["PATCH"] = fn
        return fn
