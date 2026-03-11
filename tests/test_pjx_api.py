from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from pjx import PJX, PJXRouter
from exemples.main import pjx
from exemples.data import get_showcase_context


def test_pjx_exposes_integration_config() -> None:
    integrations = pjx.integrations()

    assert integrations["renderer"] == "jinja2"
    assert integrations["browser"] == ["htmx", "alpine"]
    assert integrations["css"] == "tailwind"
    assert any(
        path.endswith("/exemples/templates") for path in integrations["templates"]
    )
    assert integrations["template_mounts"][0]["alias"] == "@"
    assert integrations["framework_static_url"] == "/_pjx"


def test_pjx_registers_framework_assets_and_tailwind_globs() -> None:
    asset_paths = {asset.path for asset in pjx.catalog.base_assets}

    assert "/_pjx/js/htmx.min.js" in asset_paths
    assert "/_pjx/js/alpine.min.js" in asset_paths
    assert "/_pjx/js/pjx-browser.js" in asset_paths

    globs = pjx.tailwind_content_globs()
    assert any(path.endswith("**/*.pjx") for path in globs)
    assert any(path.endswith("**/*.jinja") for path in globs)
    assert any(path.endswith("**/*.py") for path in globs)


def test_pjx_supports_prefixed_template_mounts(tmp_path: Path) -> None:
    root_templates = tmp_path / "templates" / "pages"
    admin_templates = tmp_path / "admin_templates" / "pages"
    root_templates.mkdir(parents=True)
    admin_templates.mkdir(parents=True)
    (root_templates / "Home.jinja").write_text(
        "{% component Home %}\n<section>root</section>\n{% endcomponent %}\n"
    )
    (admin_templates / "Home.jinja").write_text(
        "{% component AdminHome %}\n<section>admin</section>\n{% endcomponent %}\n"
    )

    mounted = PJX(
        root=tmp_path,
        templates=[
            "templates",
            {"prefix": "admin", "path": "admin_templates"},
        ],
    )

    assert (
        mounted.catalog.resolve_path("@admin/pages/Home.jinja")
        == admin_templates / "Home.jinja"
    )
    assert "@admin/pages/Home.jinja" in mounted.catalog.list_components()
    assert "pages/Home.jinja" in mounted.catalog.list_components()
    assert any(
        item["alias"] == "@admin" and item["prefix"] == "admin"
        for item in mounted.integrations()["template_mounts"]
    )


def test_pjx_can_mount_into_existing_fastapi_app() -> None:
    fastapi_app = FastAPI(title="Outer API")
    ui = PJXRouter()

    @ui.page("/embedded", template="pages/showcase.jinja")
    def embedded_page() -> dict[str, object]:
        return get_showcase_context()

    @ui.directive("example")
    def example_directive(element, value, ctx):
        element.attrs["data-example"] = value
        return element

    embedded = PJX(
        root=Path("exemples"),
        browser=["htmx", "alpine"],
        css="tailwind",
    )
    embedded.include_router(ui)
    pjx_app = embedded.app(title="Embedded UI")
    fastapi_app.mount("/", pjx_app)

    status_code, body = asyncio.run(_request(fastapi_app, "/embedded"))

    assert status_code == 200
    assert "PJX Showcase" in body
    assert "Server-first UI for Python" in body
    assert "/_pjx/js/htmx.min.js" in body
    assert embedded.catalog.directives["example"] is example_directive


async def _request(app: FastAPI, path: str) -> tuple[int, str]:
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(path)

    return response.status_code, response.text
