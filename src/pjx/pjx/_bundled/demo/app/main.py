"""
PJX Demo — CRUD de usuarios com HTMX

Roda com:
  fastapi dev demo/app/main.py
  uv run uvicorn demo.app.main:app --reload
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from .views import ui

_HERE = Path(__file__).parent

app = FastAPI(title="PJX Demo")
app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")
app.include_router(api_router)
app.include_router(ui)


@app.exception_handler(404)
async def not_found(request: Request, exc: Exception) -> HTMLResponse:
    return HTMLResponse(ui.render("pages/404.jinja"), status_code=404)


@app.exception_handler(500)
async def server_error(request: Request, exc: Exception) -> HTMLResponse:
    return HTMLResponse(ui.render("pages/500.jinja"), status_code=500)
