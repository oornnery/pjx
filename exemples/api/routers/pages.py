from typing import Any

from fastapi import Request

from exemples.data import (
    get_counter_context,
    get_catalog_context,
    get_dashboard_context,
    get_data_views_context,
    get_forms_context,
    get_patterns_context,
    get_showcase_context,
    get_status_context,
    get_studio_context,
)
from pjx import PJXRouter


pages = PJXRouter()


@pages.page("/", template="pages/showcase.jinja")
def showcase_page() -> dict[str, object]:
    return get_showcase_context()


@pages.page("/dashboard", template="pages/dashboard.jinja")
def dashboard_page() -> dict[str, Any]:
    return get_dashboard_context()


@pages.page("/status", template="pages/status_overview.jinja")
def status_overview_page() -> dict[str, Any]:
    return get_status_context()


@pages.page("/signals", template="pages/signals_counter.jinja", target="counter-value")
def signals_counter_page() -> dict[str, Any]:
    return get_counter_context()


@pages.page("/studio", template="pages/studio.jinja", target="studio-shell")
def studio_page() -> dict[str, Any]:
    return get_studio_context()


@pages.page("/patterns", template="pages/patterns.jinja")
def patterns_page() -> dict[str, object]:
    return get_patterns_context()


@pages.page("/data", template="pages/data_views.jinja")
def data_views_page() -> dict[str, object]:
    return get_data_views_context()


@pages.page("/forms", template="pages/forms_playground.jinja")
def forms_playground_page() -> dict[str, object]:
    return get_forms_context()


@pages.page("/catalog", template="pages/catalog.jinja")
def catalog_page(request: Request) -> dict[str, object]:
    return get_catalog_context(request.app.state.pjx_catalog)


__all__ = ["pages"]
