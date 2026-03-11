from __future__ import annotations

from collections.abc import Callable
from inspect import signature
from typing import Any

try:  # pragma: no cover - exercised only when FastAPI is importable
    from fastapi import APIRouter as APIRouter
    from fastapi import FastAPI as FastAPI
    from fastapi import Request as Request
    from fastapi.responses import HTMLResponse as HTMLResponse
    from fastapi.responses import JSONResponse as JSONResponse
    from fastapi.responses import Response as Response
    from fastapi.testclient import TestClient as TestClient
except Exception:  # pragma: no cover - this is the expected path on Python 3.14 today
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import HTMLResponse, JSONResponse, Response
    from starlette.routing import Route
    from starlette.testclient import TestClient

    class APIRouter:
        def __init__(self) -> None:
            self.routes: list[Route] = []

        def get(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            return self._route(path, ["GET"])

        def post(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            return self._route(path, ["POST"])

        def _route(
            self,
            path: str,
            methods: list[str],
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                async def endpoint(request: Request) -> Response:
                    if _accepts_request(fn):
                        result = await fn(request)
                    else:
                        result = await fn()
                    return _coerce_response(result)

                self.routes.append(Route(path, endpoint, methods=methods))
                return fn

            return decorator

    class FastAPI(Starlette):
        def __init__(self, *args: Any, title: str = "PJX App", **kwargs: Any) -> None:
            super().__init__(routes=[])
            self.title = title

        def include_router(
            self,
            router: APIRouter,
            *,
            prefix: str = "",
            tags: list[str] | None = None,
        ) -> None:
            del tags
            for route in router.routes:
                self.router.routes.append(
                    Route(
                        prefix + route.path,
                        route.endpoint,
                        methods=list(route.methods or []),
                        name=route.name,
                    )
                )


def _accepts_request(fn: Callable[..., Any]) -> bool:
    return bool(signature(fn).parameters)


def _coerce_response(result: Any) -> Response:
    if isinstance(result, Response):
        return result
    if isinstance(result, (dict, list)):
        return JSONResponse(result)
    return HTMLResponse("" if result is None else str(result))
