from __future__ import annotations

import asyncio
import json
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from exemples.main import app


def test_example_app_end_to_end() -> None:
    status_code, body = asyncio.run(_request("GET", "/"))
    assert status_code == 200
    assert "PJX Showcase" in body
    assert "Server-first UI for Python" in body
    assert "/_pjx/js/htmx.min.js" in body
    assert "/_pjx/js/alpine.min.js" in body
    assert "app-theme-select" in body
    assert "pjx-theme" in body
    assert "themePreference" in body
    assert 'option value="system"' in body

    status_code, body = asyncio.run(_request("GET", "/api/status"))
    assert status_code == 200
    assert json.loads(body)["status"] == "building"

    status_code, body = asyncio.run(
        _request(
            "POST",
            "/actions/counter/inc",
            headers=[(b"hx-request", b"true")],
        )
    )
    assert status_code == 200
    assert body.startswith("<strong")
    assert 'id="counter-value"' in body

    assert ".btn" in Path("exemples/static/css/components/ui/button.css").read_text()
    assert "htmx" in Path("pjx/static/js/htmx.min.js").read_text()

    status_code, body = asyncio.run(_request("GET", "/studio"))
    assert status_code == 200
    assert "Studio Playground" in body
    assert 'hx-post="/actions/studio/inc"' in body

    status_code, body = asyncio.run(_request("GET", "/patterns"))
    assert status_code == 200
    assert "Component Patterns" in body
    assert "Provide / inject" in body
    assert "Interactive primitives" in body
    assert "Accordion / disclosure" in body
    assert "Hover and tooltip" in body
    assert 'class="hover-card"' in body

    status_code, body = asyncio.run(_request("GET", "/data"))
    assert status_code == 200
    assert "Data Views" in body
    assert "Deployments table" in body

    status_code, body = asyncio.run(_request("GET", "/forms"))
    assert status_code == 200
    assert "Forms and Validation" in body
    assert "Server validation" in body
    assert "Interactive controls" in body
    assert 'class="switch-input"' in body
    assert "Validation modal" in body
    assert 'class="modal-root"' in body

    status_code, body = asyncio.run(_request("GET", "/catalog"))
    assert status_code == 200
    assert "Component Catalog" in body
    assert "components/ui/Button.jinja" in body

    status_code, body = asyncio.run(
        _request(
            "POST",
            "/actions/studio/prompt",
            body="prompt=Refinar+uma+landing+mais+editorial+e+calorosa",
            headers=[
                (b"content-type", b"application/x-www-form-urlencoded"),
                (b"hx-request", b"true"),
            ],
        )
    )
    assert status_code == 200
    assert 'id="studio-shell"' in body
    assert "Refinar uma landing mais editorial e calorosa" in body

    status_code, body = asyncio.run(
        _request(
            "POST",
            "/actions/forms/submit",
            body="name=Lu&email=invalido&message=curta",
            headers=[
                (b"content-type", b"application/x-www-form-urlencoded"),
                (b"hx-request", b"true"),
            ],
        )
    )
    assert status_code == 200
    assert 'id="forms-shell"' in body
    assert "Use pelo menos 3 caracteres no nome." in body
    assert "Informe um email valido para continuarmos." in body

    status_code, body = asyncio.run(
        _request(
            "POST",
            "/actions/forms/submit",
            body="name=Larissa+Moraes&email=larissa%40acme.dev&message=Quero+uma+pagina+de+onboarding+com+tabela+e+validacao+incremental.",
            headers=[
                (b"content-type", b"application/x-www-form-urlencoded"),
                (b"hx-request", b"true"),
            ],
        )
    )
    assert status_code == 200
    assert 'id="forms-shell"' in body
    assert "Payload aceito." in body
    assert "Larissa Moraes" in body

    status_code, body = asyncio.run(_request("POST", "/actions/studio/inc"))
    assert status_code == 200
    assert "Studio Playground" in body


async def _request(
    method: str,
    path: str,
    *,
    body: str = "",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, str]:
    encoded_headers = [(key.decode(), value.decode()) for key, value in (headers or [])]
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.request(
            method, path, content=body, headers=dict(encoded_headers)
        )

    return response.status_code, response.text
