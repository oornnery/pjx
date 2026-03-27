"""PJX health check endpoints for container orchestration."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from pjx.config import PJXConfig


def health_routes(app: FastAPI, config: PJXConfig) -> None:
    """Register ``/health`` and ``/ready`` endpoints on the app.

    Args:
        app: The FastAPI application instance.
        config: PJX configuration for readiness checks.
    """

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Liveness probe — always returns ok."""
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> dict[str, Any]:
        """Readiness probe — checks template directories exist."""
        checks: dict[str, bool] = {}
        for tpl_dir in config.template_dirs:
            checks[str(tpl_dir)] = tpl_dir.exists()

        all_ready = all(checks.values())
        return {
            "status": "ready" if all_ready else "not_ready",
            "checks": checks,
        }
