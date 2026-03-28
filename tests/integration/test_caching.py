"""Integration tests for HTTP caching — ETag middleware."""

import pytest
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from pjx.caching import ETagMiddleware


@pytest.fixture
def etag_app():
    """App with ETag middleware."""
    app = FastAPI()
    app.add_middleware(ETagMiddleware)

    @app.get("/page", response_class=HTMLResponse)
    async def page():
        return "<h1>Hello</h1>"

    @app.post("/submit")
    async def submit():
        return {"ok": True}

    return app


class TestETagMiddleware:
    def test_get_response_has_etag(self, etag_app):
        client = TestClient(etag_app)
        response = client.get("/page")
        assert response.status_code == 200
        assert "etag" in response.headers
        assert response.headers["etag"].startswith('"')

    def test_if_none_match_returns_304(self, etag_app):
        client = TestClient(etag_app)
        first = client.get("/page")
        etag = first.headers["etag"]

        second = client.get("/page", headers={"If-None-Match": etag})
        assert second.status_code == 304

    def test_different_etag_returns_200(self, etag_app):
        client = TestClient(etag_app)
        response = client.get("/page", headers={"If-None-Match": '"wrong"'})
        assert response.status_code == 200

    def test_post_no_etag(self, etag_app):
        client = TestClient(etag_app)
        response = client.post("/submit")
        assert response.status_code == 200
        assert "etag" not in response.headers
