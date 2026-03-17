from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from exemples.api.routers.actions import actions
from exemples.api.routers.pages import pages
from pjx import Pjx

BASE_DIR = Path(__file__).parent

pjx = Pjx(
    templates_dir=str(BASE_DIR / "templates"),
    auto_reload=True,
    cache=True,
    browser=["htmx", "alpine"],
    css="pjx",
    static_dir=str(BASE_DIR / "static"),
    bundle=True,
)
pjx.include_router(pages)
pjx.include_router(actions)

app = FastAPI(title="PJX Showcase")
pjx.init_app(app)

__all__ = ["app", "pjx"]
