from __future__ import annotations

from exemples.main import pjx
from exemples.data import (
    get_dashboard_context,
    get_forms_context,
    get_patterns_context,
    get_status_context,
)


catalog = pjx.catalog


def test_render_dashboard_page_smoke() -> None:
    html = catalog.render_string(
        template="pages/dashboard.jinja",
        context=get_dashboard_context(),
    )

    assert "Ola, Ana" in html
    assert "Staff Engineer" in html
    assert 'data-tooltip="Atualiza a lista de alertas"' in html
    assert html.count('<link rel="stylesheet"') == 5
    assert '/static/css/components/ui/icon.css' in html
    assert '/_pjx/js/htmx.min.js' in html
    assert '/_pjx/js/alpine.min.js' in html
    assert "status-badge status-ready" in html
    assert "app-theme-select" in html
    assert "pjx-theme" in html
    assert "themePreference" in html
    assert 'option value="system"' in html


def test_render_status_overview_with_switch_and_scoped_slots() -> None:
    html = catalog.render_string(
        template="pages/status_overview.jinja",
        context=get_status_context(),
    )

    assert "Build em andamento." in html
    assert "frontend-build" in html
    assert "worker-tests" in html
    assert "<strong class='ok'>ok</strong>" in html


def test_render_partial_fragment_by_target() -> None:
    fragment = catalog.render_string(
        template="pages/signals_counter.jinja",
        context={"initial_count": 3},
        partial=True,
        target="counter-value",
    )

    assert fragment.startswith("<strong")
    assert 'id="counter-value"' in fragment
    assert ">3<" in fragment


def test_render_studio_page_smoke() -> None:
    html = catalog.render_string(
        template="pages/studio.jinja",
        context={
            "initial_count": 6,
            "prompt": "Criar um studio server-first com controls e preview.",
            "status": "building",
            "energy_label": "Media",
            "preview": {
                "eyebrow": "Server rendered concept",
                "title": "Criar um studio server-first com controls e preview.",
                "summary": "Resumo vindo do servidor.",
                "lines": ["Linha A", "Linha B"],
            },
            "highlights": [{"label": "Prompt", "value": "Teste"}],
            "variants": [{"name": "Hero", "status": "ready", "description": "Descricao"}],
        },
    )

    assert "Studio Playground" in html
    assert 'id="studio-shell"' in html
    assert 'id="studio-count-pill"' in html
    assert 'class="studio-input"' in html
    assert 'hx-post="/actions/studio/prompt"' in html
    assert 'x-data="{ promptLength:' in html
    assert "Rendered Preview" in html


def test_render_forms_page_with_interactive_primitives() -> None:
    html = catalog.render_string(
        template="pages/forms_playground.jinja",
        context=get_forms_context(),
    )

    assert "Interactive controls" in html
    assert 'class="select"' in html
    assert 'class="checkbox-input"' in html
    assert 'class="switch-input"' in html
    assert 'class="accordion"' in html
    assert "Validation modal" in html
    assert 'class="modal-root"' in html
    assert 'class="tooltip tooltip-top"' in html


def test_render_patterns_page_with_disclosure_and_toggles() -> None:
    html = catalog.render_string(
        template="pages/patterns.jinja",
        context=get_patterns_context(),
    )

    assert "Interactive primitives" in html
    assert "Accordion / disclosure" in html
    assert "Hover and tooltip" in html
    assert 'class="accordion"' in html
    assert 'class="switch-input"' in html
    assert 'class="hover-card"' in html
    assert 'class="tooltip tooltip-top"' in html
