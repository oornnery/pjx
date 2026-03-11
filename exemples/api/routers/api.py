from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from exemples.data import (
    get_dashboard_context,
    get_studio_context,
    get_status_context,
    list_notifications,
)

router = APIRouter(prefix="/api")


@router.get("/dashboard")
async def dashboard_payload() -> dict[str, Any]:
    return get_dashboard_context()


@router.get("/status")
async def status_payload() -> dict[str, Any]:
    return get_status_context()


@router.get("/notifications")
async def notifications_payload() -> dict[str, Any]:
    return {
        "items": list_notifications(),
    }


@router.get("/studio")
async def studio_payload() -> dict[str, Any]:
    return get_studio_context()


__all__ = ["router"]
