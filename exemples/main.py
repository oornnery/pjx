from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from exemples.api.routers.api import router as api_router
from exemples.api.routers.actions import actions
from exemples.api.routers.pages import pages
from exemples.directives.tooltip import tooltips
from pjx import PJX


BASE_DIR = Path(__file__).parent

pjx = PJX(
    root=BASE_DIR,
    templates="templates",
    routers=[pages, actions, tooltips],
    browser=["htmx", "alpine"],
    css="tailwind",
)

app = FastAPI(title="PJX Example App")
app.include_router(api_router)
app.mount("/", pjx.app(title="PJX Example UI"))

__all__ = ["app", "pjx"]
