from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from httpx import ASGITransport, AsyncClient
from jinja2 import FileSystemLoader
from pydantic import BaseModel

from pjx import PJXEnvironment
from pjx.router import ActionResult, FormData, PJXRouter, SSEEvent

TEMPLATES_DIR = str(Path(__file__).parent.parent / "fixtures" / "fastapi_templates")

app = FastAPI()
templates = Jinja2Templates(env=PJXEnvironment(loader=FileSystemLoader(TEMPLATES_DIR)))
ui = PJXRouter(templates)


class HomeProps(BaseModel):
    title: str = "Home"


class UserProps(BaseModel):
    name: str


class CreateUserForm(BaseModel):
    name: str


class NotificationProps(BaseModel):
    message: str


@ui.page("/", "home.jinja")
async def home(request: Request) -> HomeProps:
    return HomeProps()


@ui.fragment("/fragment", "fragment.jinja")
async def user_fragment(request: Request) -> UserProps:
    return UserProps(name="Alice")


@ui.action(
    "/action",
    success_template="success.jinja",
    error_template="error.jinja",
)
async def create_user(
    request: Request, data: CreateUserForm = FormData(CreateUserForm)
) -> UserProps:
    return UserProps(name=data.name)


@ui.action(
    "/action-created",
    success_template="success.jinja",
    error_template="error.jinja",
)
async def create_user_201(
    request: Request, data: CreateUserForm = FormData(CreateUserForm)
) -> ActionResult:
    return ActionResult(data=UserProps(name=data.name), status=201)


@ui.stream("/stream", "stream_item.jinja")
async def notifications(request: Request):
    yield NotificationProps(message="hello")
    yield SSEEvent(props=NotificationProps(message="world"), id="2", event="update")


app.include_router(ui)


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.anyio
async def test_page_renders(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "Home" in response.text
    assert "text/html" in response.headers["content-type"]


@pytest.mark.anyio
async def test_page_autoescape(client):
    response = await client.get("/")
    assert "<script>" not in response.text


@pytest.mark.anyio
async def test_fragment_renders(client):
    response = await client.get("/fragment")
    assert response.status_code == 200
    assert "Alice" in response.text


@pytest.mark.anyio
async def test_action_success(client):
    response = await client.post(
        "/action",
        content="name=Bob",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    assert "Bob created" in response.text


@pytest.mark.anyio
async def test_action_validation_error(client):
    response = await client.post(
        "/action",
        content="",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_action_result_custom_status(client):
    response = await client.post(
        "/action-created",
        content="name=Carol",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 201
    assert "Carol created" in response.text


@pytest.mark.anyio
async def test_stream_sse(client):
    response = await client.get("/stream")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert "data:" in body
    assert "hello" in body
    assert "id: 2" in body
    assert "event: update" in body
    assert "world" in body


@pytest.mark.anyio
async def test_render_direct():
    html = ui.render("home.jinja", {"props": HomeProps(title="Direct")})
    assert "Direct" in html
