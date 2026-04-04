"""API routes — JSON endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .deps import get_user_service
from .models import CreateUserForm, UpdateUserForm, User
from .service import UserService

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/users")
async def list_users(svc: UserService = Depends(get_user_service)) -> list[User]:
    return svc.list_all()


@router.post("/users", status_code=201)
async def create_user(
    data: CreateUserForm, svc: UserService = Depends(get_user_service)
) -> User:
    return svc.create(data)


@router.get("/users/{user_id}")
async def get_user(user_id: int, svc: UserService = Depends(get_user_service)) -> User:
    return svc.get(user_id)


@router.put("/users/{user_id}")
async def update_user(
    user_id: int, data: UpdateUserForm, svc: UserService = Depends(get_user_service)
) -> User:
    return svc.update(user_id, data)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int, svc: UserService = Depends(get_user_service)
) -> None:
    svc.delete(user_id)
