from __future__ import annotations

from exemples.catalog import catalog
from exemples.data import get_dashboard_context, get_status_context


def test_render_dashboard_page_smoke() -> None:
    html = catalog.render_string(
        template="@/pages/dashboard.jinja",
        context=get_dashboard_context(),
    )

    assert "Ola, Ana" in html
    assert "Staff Engineer" in html
    assert 'data-tooltip="Atualiza a lista de alertas"' in html
    assert html.count('<link rel="stylesheet"') == 4
    assert "status-badge status-ready" in html


def test_render_status_overview_with_switch_and_scoped_slots() -> None:
    html = catalog.render_string(
        template="@/pages/status_overview.jinja",
        context=get_status_context(),
    )

    assert "Build em andamento." in html
    assert "frontend-build" in html
    assert "worker-tests" in html
    assert "<strong class='ok'>ok</strong>" in html


def test_render_partial_fragment_by_target() -> None:
    fragment = catalog.render_string(
        template="@/pages/signals_counter.jinja",
        context={"initial_count": 3},
        partial=True,
        target="counter-value",
    )

    assert fragment.startswith("<strong")
    assert 'id="counter-value"' in fragment
    assert ">3<" in fragment


def test_render_studio_page_smoke() -> None:
    html = catalog.render_string(
        template="@/pages/studio.jinja",
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
    assert 'id="studio-count-pill"' in html
    assert 'class="studio-input"' in html
    assert "Rendered Preview" in html
