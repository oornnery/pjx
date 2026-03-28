"""Application setup helpers — static files, middleware, health, logging."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from pjx.config import PJXConfig


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

    secret = secret or "pjx-csrf-change-me"
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


def setup_logging(config: PJXConfig) -> None:
    """Configure application logging from PJX config."""
    from pjx.log import setup_logging as _setup

    _setup(
        debug=config.debug,
        json_output=config.log_json,
        level=config.log_level,
    )
