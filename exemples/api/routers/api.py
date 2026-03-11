from exemples.data import (
    get_dashboard_context,
    get_studio_context,
    get_status_context,
    list_notifications,
)
from pjx.web import APIRouter

router = APIRouter()


@router.get("/dashboard")
async def dashboard_payload():
    return get_dashboard_context()


@router.get("/status")
async def status_payload():
    return get_status_context()


@router.get("/notifications")
async def notifications_payload():
    return {
        "items": list_notifications(),
    }


@router.get("/studio")
async def studio_payload():
    return get_studio_context()
