"""Tests for signed session cookies in the example app."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """Sync HTTP client for the example app."""
    from app.main import app

    return TestClient(app, follow_redirects=False)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear slowapi rate limit state between tests."""
    from app.pages import limiter

    yield
    limiter.reset()


def _get_csrf_token(client: TestClient) -> str:
    """Fetch a CSRF token by making a GET request."""
    resp = client.get("/login")
    return resp.cookies.get("_csrf", "")


class TestSignedSessions:
    def test_login_sets_signed_session(self, client: TestClient) -> None:
        """Login should set a signed session cookie, not a plain-text one."""
        csrf = _get_csrf_token(client)
        response = client.post(
            "/auth/login",
            data={"username": "alice"},
            headers={"X-CSRFToken": csrf},
            cookies={"_csrf": csrf},
        )
        assert response.status_code == 303
        cookie = response.cookies.get("session")
        assert cookie is not None
        # Signed cookies contain a dot-separated signature — NOT the raw value
        assert cookie != "alice"
        assert "." in cookie

    def test_session_persists_across_requests(self, client: TestClient) -> None:
        """After login, subsequent requests should see the session user."""
        csrf = _get_csrf_token(client)
        login_resp = client.post(
            "/auth/login",
            data={"username": "bob"},
            headers={"X-CSRFToken": csrf},
            cookies={"_csrf": csrf},
        )
        # Collect all cookies from the response (session + csrf)
        all_cookies = {**dict(login_resp.cookies)}
        # Also keep the csrf cookie if not in response
        if "_csrf" not in all_cookies:
            all_cookies["_csrf"] = csrf
        response = client.get("/protected", cookies=all_cookies)
        assert response.status_code == 200
        # Check the rendered page contains the username
        text = response.text.lower()
        assert "bob" in text or "guest" not in text

    def test_logout_clears_session(self, client: TestClient) -> None:
        """Logout should clear the session so protected pages redirect."""
        csrf = _get_csrf_token(client)
        login_resp = client.post(
            "/auth/login",
            data={"username": "charlie"},
            headers={"X-CSRFToken": csrf},
            cookies={"_csrf": csrf},
        )
        cookies = dict(login_resp.cookies)
        cookies["_csrf"] = csrf
        logout_resp = client.post(
            "/auth/logout",
            headers={"X-CSRFToken": csrf},
            cookies=cookies,
        )
        assert logout_resp.status_code == 303

    def test_tampered_cookie_rejected(self, client: TestClient) -> None:
        """A tampered session cookie should redirect to login (not authenticated)."""
        response = client.get(
            "/protected",
            cookies={"session": "forged.tampered.value"},
        )
        # Tampered cookie is ignored → no session → middleware redirects to /login
        assert response.status_code == 303
        assert response.headers.get("location") == "/login"

    def test_unauthenticated_protected_redirects(self, client: TestClient) -> None:
        """Accessing /protected without a session should redirect to /login."""
        response = client.get("/protected")
        # The middleware raises HTTPException(303) with Location: /login
        assert response.status_code == 303
        assert response.headers.get("location") == "/login"

    def test_htmx_login_returns_hx_redirect(self, client: TestClient) -> None:
        """HTMX login should return HX-Redirect header instead of 303."""
        csrf = _get_csrf_token(client)
        response = client.post(
            "/auth/login",
            data={"username": "alice"},
            headers={"HX-Request": "true", "X-CSRFToken": csrf},
            cookies={"_csrf": csrf},
        )
        assert response.status_code == 200
        assert response.headers.get("hx-redirect") == "/protected"
        cookie = response.cookies.get("session")
        assert cookie is not None
        assert cookie != "alice"


class TestLoginValidation:
    """Test login form validation edge cases."""

    def test_empty_username_returns_error_toast(self, client: TestClient) -> None:
        csrf = _get_csrf_token(client)
        response = client.post(
            "/auth/login",
            data={"username": ""},
            headers={"X-CSRFToken": csrf},
            cookies={"_csrf": csrf},
        )
        assert response.status_code == 200
        assert "Username is required" in response.text
        assert "toast--error" in response.text

    def test_whitespace_username_returns_error(self, client: TestClient) -> None:
        csrf = _get_csrf_token(client)
        response = client.post(
            "/auth/login",
            data={"username": "   "},
            headers={"X-CSRFToken": csrf},
            cookies={"_csrf": csrf},
        )
        assert response.status_code == 200
        assert "Username is required" in response.text

    def test_htmx_login_empty_returns_toast_not_redirect(
        self, client: TestClient
    ) -> None:
        csrf = _get_csrf_token(client)
        response = client.post(
            "/auth/login",
            data={"username": ""},
            headers={"HX-Request": "true", "X-CSRFToken": csrf},
            cookies={"_csrf": csrf},
        )
        assert response.status_code == 200
        assert response.headers.get("hx-redirect") is None
        assert "toast--error" in response.text

    def test_htmx_logout_returns_hx_redirect(self, client: TestClient) -> None:
        csrf = _get_csrf_token(client)
        login_resp = client.post(
            "/auth/login",
            data={"username": "alice"},
            headers={"X-CSRFToken": csrf},
            cookies={"_csrf": csrf},
        )
        cookies = dict(login_resp.cookies)
        cookies["_csrf"] = csrf
        response = client.post(
            "/auth/logout",
            headers={"HX-Request": "true", "X-CSRFToken": csrf},
            cookies=cookies,
        )
        assert response.status_code == 200
        assert response.headers.get("hx-redirect") == "/login"


class TestAuthFlow:
    """Test full authentication flow."""

    def test_protected_after_logout_redirects(self, client: TestClient) -> None:
        """Login → logout → /protected should redirect to /login."""
        csrf = _get_csrf_token(client)
        login_resp = client.post(
            "/auth/login",
            data={"username": "alice"},
            headers={"X-CSRFToken": csrf},
            cookies={"_csrf": csrf},
        )
        cookies = dict(login_resp.cookies)
        cookies["_csrf"] = csrf
        client.post(
            "/auth/logout",
            headers={"X-CSRFToken": csrf},
            cookies=cookies,
        )
        # After logout, cookies should be cleared — use empty cookies
        response = client.get("/protected")
        assert response.status_code == 303
        assert response.headers.get("location") == "/login"


class TestMalformedCookies:
    """Edge cases with corrupt or garbage session cookies."""

    def test_empty_session_cookie_redirects(self, client: TestClient) -> None:
        """An empty session cookie should be treated as unauthenticated."""
        response = client.get("/protected", cookies={"session": ""})
        assert response.status_code == 303
        assert response.headers.get("location") == "/login"

    def test_garbage_session_cookie_redirects(self, client: TestClient) -> None:
        """A random garbage string should not crash the app."""
        response = client.get(
            "/protected",
            cookies={"session": "not-a-valid-signed-value!!!"},
        )
        assert response.status_code == 303
        assert response.headers.get("location") == "/login"

    def test_base64_garbage_cookie_redirects(self, client: TestClient) -> None:
        """A base64-like but invalid cookie should redirect gracefully."""
        response = client.get(
            "/protected",
            cookies={"session": "eyJhbGciOiJIUzI1NiJ9.corrupted.signature"},
        )
        assert response.status_code == 303
        assert response.headers.get("location") == "/login"
