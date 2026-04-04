import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from jinja2 import FileSystemLoader
from pydantic import BaseModel
from starlette.templating import Jinja2Templates

from pjx import PJXEnvironment
from pjx.router import FormData, PJXRouter

TEMPLATES_DIR = "tests/fixtures/fastapi_templates"

app = FastAPI()
templates = Jinja2Templates(env=PJXEnvironment(loader=FileSystemLoader(TEMPLATES_DIR)))
ui = PJXRouter(templates)


class HomeProps(BaseModel):
    title: str = "Home"


class UserProps(BaseModel):
    name: str


class CreateUserForm(BaseModel):
    name: str


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
