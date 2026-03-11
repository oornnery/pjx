from urllib.parse import parse_qs

from exemples.catalog import render_page
from exemples.data import (
    decrement_studio_count,
    get_counter_context,
    get_dashboard_context,
    get_studio_context,
    get_status_context,
    increment_studio_count,
    update_studio_prompt,
)
from pjx.web import APIRouter, Request

router = APIRouter()


@router.get("/")
async def dashboard_page(request: Request):
    return render_page(
        request,
        "@/pages/dashboard.jinja",
        **get_dashboard_context(),
    )


@router.get("/status")
async def status_overview_page(request: Request):
    return render_page(
        request,
        "@/pages/status_overview.jinja",
        **get_status_context(),
    )


@router.get("/signals")
async def signals_counter_page(request: Request):
    return render_page(
        request,
        "@/pages/signals_counter.jinja",
        **get_counter_context(),
    )


@router.get("/studio")
async def studio_page(request: Request):
    return render_page(
        request,
        "@/pages/studio.jinja",
        **get_studio_context(),
    )


@router.post("/studio/inc")
async def studio_count_up(request: Request):
    return render_page(
        request,
        "@/pages/studio.jinja",
        **increment_studio_count(),
    )


@router.post("/studio/dec")
async def studio_count_down(request: Request):
    return render_page(
        request,
        "@/pages/studio.jinja",
        **decrement_studio_count(),
    )


@router.post("/studio/prompt")
async def studio_prompt_submit(request: Request):
    form_payload = parse_qs((await request.body()).decode())
    prompt = form_payload.get("prompt", [""])[0]
    return render_page(
        request,
        "@/pages/studio.jinja",
        **update_studio_prompt(prompt),
    )
