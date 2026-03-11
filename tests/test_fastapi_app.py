from __future__ import annotations

import asyncio
import json

from exemples.main import app


def test_example_app_end_to_end() -> None:
    status_code, headers, body = asyncio.run(_asgi_request(app, "GET", "/"))
    assert status_code == 200
    assert "Dashboard" in body
    assert "Ana" in body

    status_code, headers, body = asyncio.run(_asgi_request(app, "GET", "/api/status"))
    assert status_code == 200
    assert json.loads(body)["status"] == "building"

    status_code, headers, body = asyncio.run(_asgi_request(app, "POST", "/actions/counter/inc"))
    assert status_code == 200
    assert body.startswith("<strong")
    assert 'id="counter-value"' in body

    status_code, headers, body = asyncio.run(_asgi_request(app, "GET", "/static/components/ui/button.css"))
    assert status_code == 200
    assert ".btn" in body

    status_code, headers, body = asyncio.run(_asgi_request(app, "GET", "/studio"))
    assert status_code == 200
    assert "Studio Playground" in body

    status_code, headers, body = asyncio.run(
        _asgi_request(
            app,
            "POST",
            "/studio/prompt",
            body="prompt=Refinar+uma+landing+mais+editorial+e+calorosa",
            headers=[(b"content-type", b"application/x-www-form-urlencoded")],
        )
    )
    assert status_code == 200
    assert "Refinar uma landing mais editorial e calorosa" in body


async def _asgi_request(
    app,
    method: str,
    path: str,
    *,
    body: str = "",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, list[tuple[bytes, bytes]], str]:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers or [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "state": {},
    }
    messages: list[dict] = []
    body_bytes = body.encode()

    async def receive():
        return {"type": "http.request", "body": body_bytes, "more_body": False}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)

    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    headers = next(message["headers"] for message in messages if message["type"] == "http.response.start")
    body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return status, headers, body.decode()
