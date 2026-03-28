"""Application setup helpers — static files, middleware, health, logging."""

from __future__ import annotations

import logging
import secrets
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from pjx.config import PJXConfig

logger = logging.getLogger("pjx")


def setup_static(app: FastAPI, config: PJXConfig) -> None:
    """Mount the static files directory if it exists."""
    static_dir = config.static_dir
    if static_dir.exists():
        from fastapi.staticfiles import StaticFiles

        app.mount("/static", StaticFiles(directory=static_dir), name="static")


def setup_csrf(
    app: FastAPI,
    secret: str | None = None,
    exempt_paths: set[str] | None = None,
) -> Any | None:
    """Add CSRF middleware and return the middleware instance."""
    from pjx.middleware.csrf import CSRFMiddleware

    if not secret:
        secret = secrets.token_urlsafe(32)
        logger.warning(
            "CSRF secret not set — using random key (sessions won't survive restarts). "
            "Set csrf_secret in PJX() or PJX_SECRET_KEY env var for production."
        )
    mw = CSRFMiddleware(
        app,
        secret_key=secret,
        exempt_paths=exempt_paths or set(),
    )
    app.add_middleware(
        CSRFMiddleware,  # ty: ignore[invalid-argument-type]
        secret_key=secret,
        exempt_paths=exempt_paths or set(),
    )
    return mw


def setup_cors(app: FastAPI, config: PJXConfig) -> None:
    """Add CORS middleware if origins are configured."""
    if config.cors_origins:
        from starlette.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware,  # ty: ignore[invalid-argument-type]
            allow_origins=config.cors_origins,
            allow_methods=config.cors_methods,
            allow_headers=config.cors_headers,
            allow_credentials=config.cors_credentials,
        )


def setup_cache(app: FastAPI, config: PJXConfig) -> None:
    """Add ETag middleware if configured."""
    if config.cache_etag:
        from pjx.caching import ETagMiddleware

        app.add_middleware(ETagMiddleware)  # ty: ignore[invalid-argument-type]


def setup_health(app: FastAPI, config: PJXConfig) -> None:
    """Register health check endpoints."""
    from pjx.health import health_routes

    health_routes(app, config)


def setup_security_headers(app: FastAPI, config: PJXConfig) -> None:
    """Add security headers to all responses."""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response as StarletteResponse

    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Any) -> StarletteResponse:
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            if not config.debug:
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains"
                )
            return response

    app.add_middleware(SecurityHeadersMiddleware)  # ty: ignore[invalid-argument-type]


def setup_error_handlers(app: FastAPI, config: PJXConfig) -> None:
    """Register exception handlers that hide internal details in production."""
    from pjx.errors import CompileError, ParseError, RenderError

    async def _safe_error(request: Request, exc: Exception) -> HTMLResponse:
        logger.error("unhandled %s: %s", type(exc).__name__, exc, exc_info=True)
        if config.debug:
            return HTMLResponse(
                f"<h1>500 Internal Server Error</h1><pre>{exc}</pre>",
                status_code=500,
            )
        return HTMLResponse(
            "<h1>500 Internal Server Error</h1><p>An unexpected error occurred.</p>",
            status_code=500,
        )

    for exc_cls in (RenderError, CompileError, ParseError):
        app.add_exception_handler(exc_cls, _safe_error)

    async def _generic_500(request: Request, exc: Exception) -> HTMLResponse:
        logger.error("unhandled exception: %s", exc, exc_info=True)
        if config.debug:
            return HTMLResponse(
                f"<h1>500 Internal Server Error</h1><pre>{type(exc).__name__}: {exc}</pre>",
                status_code=500,
            )
        return HTMLResponse(
            "<h1>500 Internal Server Error</h1><p>An unexpected error occurred.</p>",
            status_code=500,
        )

    app.add_exception_handler(500, _generic_500)


def setup_logging(config: PJXConfig) -> None:
    """Configure application logging from PJX config."""
    from pjx.log import setup_logging as _setup

    _setup(
        debug=config.debug,
        json_output=config.log_json,
        level=config.log_level,
    )
