"""View routes — HTML endpoints rendered with PJX templates."""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import FileSystemLoader

from pjx import PJXEnvironment
from pjx.router import FormData, PJXRouter

from .deps import get_user_service
from .models import (
    CreateUserForm,
    HomeProps,
    UpdateUserForm,
    UserCardProps,
    UserDetailProps,
)
from .service import UserService

_HERE = Path(__file__).parent

templates = Jinja2Templates(env=PJXEnvironment(loader=FileSystemLoader(str(_HERE / "templates"))))
ui = PJXRouter(templates)


@ui.page("/", "pages/home.jinja")
async def home(request: Request, svc: UserService = Depends(get_user_service)) -> HomeProps:
    return HomeProps(users=svc.list_all())


@ui.action(
    "/users",
    success_template="partials/user_card.jinja",
    error_template="partials/form_error.jinja",
)
async def create_user(
    request: Request,
    data: CreateUserForm = FormData(CreateUserForm),
    svc: UserService = Depends(get_user_service),
) -> UserCardProps:
    user = svc.create(data)
    return UserCardProps(id=user.id, name=user.name, email=user.email, role=user.role)


@ui.fragment("/users/{user_id}/edit", "partials/edit_modal.jinja")
async def edit_user_form(
    request: Request, user_id: int, svc: UserService = Depends(get_user_service)
) -> UserCardProps:
    user = svc.get(user_id)
    return UserCardProps(id=user.id, name=user.name, email=user.email, role=user.role)


@ui.action(
    "/users/{user_id}",
    success_template="partials/user_card.jinja",
    error_template="partials/form_error.jinja",
    method="PUT",
)
async def update_user(
    request: Request,
    data: UpdateUserForm = FormData(UpdateUserForm),
    svc: UserService = Depends(get_user_service),
) -> UserCardProps:
    user_id = int(request.path_params["user_id"])
    user = svc.update(user_id, data)
    return UserCardProps(id=user.id, name=user.name, email=user.email, role=user.role)


@ui.page("/users/{user_id}", "pages/users/[id].jinja")
async def user_detail(
    request: Request, user_id: int, svc: UserService = Depends(get_user_service)
) -> UserDetailProps:
    return UserDetailProps(user=svc.get(user_id))


@ui.delete("/users/{user_id}")
async def delete_user(user_id: int, svc: UserService = Depends(get_user_service)) -> HTMLResponse:
    svc.delete(user_id)
    return HTMLResponse("")
