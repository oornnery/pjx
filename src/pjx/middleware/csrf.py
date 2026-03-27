"""CSRF protection middleware — double-submit cookie pattern.

Works with HTMX out of the box: set ``hx-headers`` on ``<body>`` to
forward the token automatically on every HTMX request::

    <body hx-headers='{"X-CSRFToken": "{{ csrf_token() }}"}'>

For regular HTML forms, include a hidden field::

    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger("pjx.csrf")

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def _generate_token() -> str:
    """Generate a cryptographically random CSRF token."""
    return os.urandom(32).hex()


def _sign_token(token: str, secret_key: str) -> str:
    """Create an HMAC signature for a token."""
    return hmac.new(
        secret_key.encode(),
        token.encode(),
        hashlib.sha256,
    ).hexdigest()


def _make_signed_token(secret_key: str) -> str:
    """Generate a token with its HMAC signature."""
    token = _generate_token()
    sig = _sign_token(token, secret_key)
    return f"{token}.{sig}"


def _verify_signed_token(signed_token: str, secret_key: str) -> bool:
    """Verify a signed token's HMAC signature."""
    parts = signed_token.split(".", 1)
    if len(parts) != 2:
        return False
    token, sig = parts
    expected = _sign_token(token, secret_key)
    return hmac.compare_digest(sig, expected)


def _tokens_match(cookie_token: str, request_token: str) -> bool:
    """Check that the cookie token and request token are the same."""
    if not cookie_token or not request_token:
        return False
    cookie_parts = cookie_token.split(".", 1)
    request_parts = request_token.split(".", 1)
    if len(cookie_parts) != 2 or len(request_parts) != 2:
        return False
    return hmac.compare_digest(cookie_parts[0], request_parts[0])


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie CSRF protection.

    On every response, sets a signed CSRF cookie. On unsafe methods
    (POST, PUT, DELETE, PATCH), validates that the token from the
    ``X-CSRFToken`` header or ``csrf_token`` form field matches the
    cookie value.

    Args:
        app: The ASGI application.
        secret_key: Secret key for signing tokens.
        cookie_name: Name of the CSRF cookie.
        header_name: Name of the header to check for the token.
        form_field: Name of the form field to check for the token.
        max_age: Cookie max-age in seconds.
        exempt_paths: Set of URL paths to exempt from CSRF checks.
    """

    def __init__(
        self,
        app: ASGIApp,
        secret_key: str,
        cookie_name: str = "_csrf",
        header_name: str = "X-CSRFToken",
        form_field: str = "csrf_token",
        max_age: int = 3600,
        exempt_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._secret_key = secret_key
        self._cookie_name = cookie_name
        self._header_name = header_name
        self._form_field = form_field
        self._max_age = max_age
        self._exempt_paths = exempt_paths or set()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Validate CSRF token on unsafe methods, set cookie on responses."""
        # Skip CSRF check for safe methods and exempt paths
        if request.method in _SAFE_METHODS or request.url.path in self._exempt_paths:
            response = await call_next(request)
            self._ensure_cookie(request, response)
            return response

        # Validate token on unsafe methods
        cookie_token = request.cookies.get(self._cookie_name, "")
        if not cookie_token or not _verify_signed_token(cookie_token, self._secret_key):
            logger.warning("CSRF: missing or invalid cookie on %s", request.url.path)
            return Response("CSRF token missing", status_code=403)

        # Get token from header or form field
        request_token = request.headers.get(self._header_name, "")
        if not request_token:
            # Try form field — only if content type is form data
            content_type = request.headers.get("content-type", "")
            if "form" in content_type:
                form = await request.form()
                request_token = str(form.get(self._form_field, ""))

        if not _tokens_match(cookie_token, request_token):
            logger.warning("CSRF: token mismatch on %s", request.url.path)
            return Response("CSRF token mismatch", status_code=403)

        response = await call_next(request)
        self._ensure_cookie(request, response)
        return response

    def _ensure_cookie(self, request: Request, response: Response) -> None:
        """Set CSRF cookie if not already present."""
        if self._cookie_name not in request.cookies:
            # Reuse token already generated by get_token() during rendering,
            # so the cookie value matches what was placed in hx-headers.
            if hasattr(request.state, "_csrf_token"):
                token = request.state._csrf_token  # noqa: SLF001
            else:
                token = _make_signed_token(self._secret_key)
                request.state._csrf_token = token  # noqa: SLF001
            response.set_cookie(
                self._cookie_name,
                token,
                max_age=self._max_age,
                httponly=False,  # Must be readable by JavaScript for HTMX
                samesite="lax",
                secure=request.url.scheme == "https",
            )
        elif not hasattr(request.state, "_csrf_token"):
            request.state._csrf_token = request.cookies[self._cookie_name]  # noqa: SLF001

    def get_token(self, request: Request) -> str:
        """Get the current CSRF token for template rendering."""
        if hasattr(request.state, "_csrf_token"):
            return request.state._csrf_token  # type: ignore[no-any-return]
        # Reuse the existing cookie token so the HTML matches what the
        # browser will send back on POST requests.
        cookie_token = request.cookies.get(self._cookie_name, "")
        if cookie_token and _verify_signed_token(cookie_token, self._secret_key):
            token = cookie_token
        else:
            token = _make_signed_token(self._secret_key)
        request.state._csrf_token = token  # noqa: SLF001
        return token
