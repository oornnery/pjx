"""Custom middleware — security headers, auth."""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

logger = logging.getLogger("pjx.demo")


async def security_headers(request: Request, call_next):  # noqa: ANN001
    """Add security headers and disable static file caching in dev mode."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self'"
    )
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
    return response


async def require_auth(request: Request) -> None:
    """Check if user is logged in. Redirects to /login if not."""
    if not request.session.get("user"):
        raise HTTPException(status_code=303, headers={"Location": "/login"})


async def generic_exception_handler(request: Request, exc: Exception) -> HTMLResponse:
    """Return a safe error page; show details only in debug mode."""
    from app.main import pjx

    logger.exception("unhandled error on %s", request.url.path)
    if pjx.config.debug:
        detail = f"<pre>{type(exc).__name__}: {exc}</pre>"
    else:
        detail = "<p>Something went wrong.</p>"
    return HTMLResponse(
        f"<h1>500 — Internal Server Error</h1>{detail}",
        status_code=500,
    )
