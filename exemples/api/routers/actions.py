from exemples.catalog import render_fragment
from exemples.data import decrement_counter, increment_counter
from pjx.web import APIRouter, Request

router = APIRouter()


@router.post("/counter/inc")
async def increment_counter_action(request: Request):
    state = increment_counter()
    return render_fragment(
        request,
        "@/pages/signals_counter.jinja",
        target="counter-value",
        initial_count=state["count"],
    )


@router.post("/counter/dec")
async def decrement_counter_action(request: Request):
    state = decrement_counter()
    return render_fragment(
        request,
        "@/pages/signals_counter.jinja",
        target="counter-value",
        initial_count=state["count"],
    )
