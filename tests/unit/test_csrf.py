"""Tests for pjx.middleware.csrf — CSRF protection middleware."""

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from pjx.middleware.csrf import (
    CSRFMiddleware,
    _generate_token,
    _make_signed_token,
    _sign_token,
    _tokens_match,
    _verify_signed_token,
)


# -- Token helpers -----------------------------------------------------------


class TestTokenHelpers:
    def test_generate_token_uniqueness(self) -> None:
        t1 = _generate_token()
        t2 = _generate_token()
        assert t1 != t2
        assert len(t1) == 64  # 32 bytes hex

    def test_sign_and_verify(self) -> None:
        token = _generate_token()
        sig = _sign_token(token, "secret")
        signed = f"{token}.{sig}"
        assert _verify_signed_token(signed, "secret")

    def test_verify_rejects_wrong_secret(self) -> None:
        signed = _make_signed_token("secret1")
        assert not _verify_signed_token(signed, "secret2")

    def test_verify_rejects_tampered_token(self) -> None:
        signed = _make_signed_token("secret")
        tampered = "a" * 64 + signed[64:]
        assert not _verify_signed_token(tampered, "secret")

    def test_verify_rejects_no_dot(self) -> None:
        assert not _verify_signed_token("nodot", "secret")

    def test_tokens_match_same_token(self) -> None:
        signed = _make_signed_token("secret")
        assert _tokens_match(signed, signed)

    def test_tokens_match_rejects_different(self) -> None:
        t1 = _make_signed_token("secret")
        t2 = _make_signed_token("secret")
        assert not _tokens_match(t1, t2)

    def test_tokens_match_rejects_empty(self) -> None:
        assert not _tokens_match("", "token.sig")
        assert not _tokens_match("token.sig", "")


# -- Middleware integration --------------------------------------------------


@pytest.fixture()
def csrf_app():
    """Create a FastAPI app with CSRF middleware."""
    app = FastAPI()

    @app.get("/")
    async def home() -> PlainTextResponse:
        return PlainTextResponse("ok")

    @app.post("/submit")
    async def submit() -> PlainTextResponse:
        return PlainTextResponse("submitted")

    @app.post("/exempt")
    async def exempt() -> PlainTextResponse:
        return PlainTextResponse("exempt ok")

    app.add_middleware(
        CSRFMiddleware,
        secret_key="test-secret",
        exempt_paths={"/exempt"},
    )
    return app


@pytest.fixture()
def client(csrf_app):
    return TestClient(csrf_app)


class TestCSRFMiddleware:
    def test_get_sets_csrf_cookie(self, client: TestClient) -> None:
        """GET request should set a CSRF cookie."""
        response = client.get("/")
        assert response.status_code == 200
        assert "_csrf" in response.cookies

    def test_post_without_cookie_returns_403(self, client: TestClient) -> None:
        """POST without CSRF cookie should be rejected."""
        response = client.post("/submit")
        assert response.status_code == 403
        assert "missing" in response.text.lower()

    def test_post_with_valid_token_succeeds(self, client: TestClient) -> None:
        """POST with matching cookie and header token should succeed."""
        # First GET to get the CSRF cookie
        get_resp = client.get("/")
        csrf_token = get_resp.cookies["_csrf"]
        # POST with the token in header
        response = client.post(
            "/submit",
            headers={"X-CSRFToken": csrf_token},
            cookies={"_csrf": csrf_token},
        )
        assert response.status_code == 200
        assert response.text == "submitted"

    def test_post_with_mismatched_token_returns_403(self, client: TestClient) -> None:
        """POST with different cookie and header tokens should be rejected."""
        get_resp = client.get("/")
        csrf_cookie = get_resp.cookies["_csrf"]
        different_token = _make_signed_token("test-secret")
        response = client.post(
            "/submit",
            headers={"X-CSRFToken": different_token},
            cookies={"_csrf": csrf_cookie},
        )
        assert response.status_code == 403
        assert "mismatch" in response.text.lower()

    def test_post_with_tampered_cookie_returns_403(self, client: TestClient) -> None:
        """POST with tampered CSRF cookie should be rejected."""
        response = client.post(
            "/submit",
            headers={"X-CSRFToken": "fake.token"},
            cookies={"_csrf": "fake.token"},
        )
        assert response.status_code == 403

    def test_exempt_path_skips_csrf(self, client: TestClient) -> None:
        """Exempt paths should not require CSRF tokens."""
        response = client.post("/exempt")
        assert response.status_code == 200
        assert response.text == "exempt ok"

    def test_safe_methods_skip_csrf(self, client: TestClient) -> None:
        """GET requests should not require CSRF tokens."""
        response = client.get("/")
        assert response.status_code == 200

    def test_post_with_form_field_succeeds(self) -> None:
        """POST with CSRF token in form field should succeed."""
        app = FastAPI()

        @app.post("/form")
        async def form_handler() -> PlainTextResponse:
            return PlainTextResponse("form ok")

        app.add_middleware(CSRFMiddleware, secret_key="test-secret")
        client = TestClient(app)

        # Get CSRF cookie
        get_resp = client.get("/form")
        csrf_token = get_resp.cookies.get("_csrf")
        if csrf_token is None:
            # Cookie may not be set on 405, so make a GET route
            @app.get("/form")
            async def form_get() -> PlainTextResponse:
                return PlainTextResponse("form page")

            client = TestClient(app)
            get_resp = client.get("/form")
            csrf_token = get_resp.cookies["_csrf"]

        response = client.post(
            "/form",
            data={"csrf_token": csrf_token, "name": "test"},
            cookies={"_csrf": csrf_token},
        )
        assert response.status_code == 200
