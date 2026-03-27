"""API v1 — JSON endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import User
from app.services.data import USERS, todos_db

router = APIRouter(tags=["v1"])


@router.get("/users")
async def api_users() -> list[User]:
    """Return all users as JSON."""
    return USERS


@router.get("/todos")
async def api_todos() -> list[dict[str, object]]:
    """Return all todos as JSON."""
    return todos_db
