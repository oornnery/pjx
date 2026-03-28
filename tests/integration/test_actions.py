"""Integration tests for server actions — end-to-end route registration and invocation."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from pjx.integration import PJX


@pytest.fixture
def app_with_actions(tmp_path):
    """Create a FastAPI app with PJX and registered server actions."""
    # Create minimal template dirs
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()

    from pjx.config import PJXConfig

    config = PJXConfig(template_dirs=[str(tpl_dir)])
    app = FastAPI()
    pjx = PJX(app, config=config)

    @pjx.action("greet")
    async def greet(request: Request):
        form = await request.form()
        name = form.get("name", "World")
        return f"<span>Hello {name}!</span>"

    @pjx.action("echo_json")
    async def echo_json(request: Request):
        form = await request.form()
        return {"echo": form.get("text", "")}

    return app


class TestServerActions:
    def test_action_route_returns_html(self, app_with_actions):
        client = TestClient(app_with_actions)
        response = client.post(
            "/_pjx/actions/greet",
            data={"name": "PJX"},
        )
        assert response.status_code == 200
        assert "<span>Hello PJX!</span>" in response.text

    def test_action_route_returns_json(self, app_with_actions):
        client = TestClient(app_with_actions)
        response = client.post(
            "/_pjx/actions/echo_json",
            data={"text": "hello"},
        )
        assert response.status_code == 200
        assert response.json() == {"echo": "hello"}

    def test_action_route_get_returns_405(self, app_with_actions):
        client = TestClient(app_with_actions)
        response = client.get("/_pjx/actions/greet")
        assert response.status_code == 405
