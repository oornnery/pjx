"""E2E tests — compile REAL example templates and verify output.

Protects the parse → compile pipeline against regressions by running
the actual .jinja files through the compiler and asserting on the
generated Jinja2/Alpine/HTMX output.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pjx.compiler import Compiler
from pjx.parser import parse
from pjx.registry import ComponentRegistry

COMPONENTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "examples"
    / "demo"
    / "app"
    / "templates"
    / "components"
)


@pytest.fixture()
def registry() -> ComponentRegistry:
    """Build a registry pre-loaded with all example components."""
    reg = ComponentRegistry()
    for p in sorted(COMPONENTS_DIR.glob("*.jinja")):
        comp = parse(p.read_text(), path=p)
        reg._by_name[p.stem] = comp  # noqa: SLF001
    return reg


def _compile_component(name: str, registry: ComponentRegistry | None = None) -> str:
    """Parse and compile a component, return the jinja_source."""
    path = COMPONENTS_DIR / f"{name}.jinja"
    comp = parse(path.read_text(), path=path)
    return Compiler(registry=registry).compile(comp).jinja_source


# ---------------------------------------------------------------------------
# Smoke test: all components parse and compile without errors
# ---------------------------------------------------------------------------


class TestAllComponentsCompile:
    @pytest.mark.parametrize(
        "name",
        [p.stem for p in sorted(COMPONENTS_DIR.glob("*.jinja"))],
    )
    def test_parse_and_compile_without_error(
        self, name: str, registry: ComponentRegistry
    ) -> None:
        """Every example component must parse and compile cleanly."""
        source = _compile_component(name, registry)
        assert source  # non-empty output


# ---------------------------------------------------------------------------
# Counter (Alpine.js client-side)
# ---------------------------------------------------------------------------


class TestCounterCompilation:
    def test_alpine_state(self) -> None:
        src = _compile_component("Counter")
        assert 'x-data="{ count: 0 }"' in src

    def test_click_handlers(self) -> None:
        src = _compile_component("Counter")
        assert '@click="count--"' in src
        assert '@click="count++"' in src
        assert '@click="count = 0"' in src

    def test_text_binding(self) -> None:
        src = _compile_component("Counter")
        assert 'x-text="count"' in src


# ---------------------------------------------------------------------------
# ServerCounter (HTMX server-side)
# ---------------------------------------------------------------------------


class TestServerCounterCompilation:
    def test_htmx_post_actions(self) -> None:
        src = _compile_component("ServerCounter")
        assert 'hx-post="/htmx/counter/increment"' in src
        assert 'hx-post="/htmx/counter/decrement"' in src
        assert 'hx-post="/htmx/counter/reset"' in src

    def test_htmx_target_and_swap(self) -> None:
        src = _compile_component("ServerCounter")
        assert 'hx-target="#server-counter"' in src
        assert 'hx-swap="outerHTML"' in src

    def test_props_rendering(self) -> None:
        src = _compile_component("ServerCounter")
        assert "{{ props.count }}" in src


# ---------------------------------------------------------------------------
# TodoItem (CRUD actions + Alpine edit mode)
# ---------------------------------------------------------------------------


class TestTodoItemCompilation:
    def test_htmx_toggle(self) -> None:
        src = _compile_component("TodoItem")
        assert 'hx-post="/htmx/todos/{{ props.idx }}/toggle"' in src

    def test_htmx_delete(self) -> None:
        src = _compile_component("TodoItem")
        assert 'hx-delete="/htmx/todos/{{ props.idx }}"' in src

    def test_htmx_edit_put(self) -> None:
        src = _compile_component("TodoItem")
        assert 'hx-put="/htmx/todos/{{ props.idx }}"' in src

    def test_alpine_edit_mode(self) -> None:
        src = _compile_component("TodoItem")
        assert 'x-show="!editing"' in src
        assert 'x-show="editing"' in src
        assert '@click="editing = true"' in src
        assert '@click="editing = false"' in src

    def test_htmx_target(self) -> None:
        src = _compile_component("TodoItem")
        assert 'hx-target="#todo-list"' in src


# ---------------------------------------------------------------------------
# TodoList (control flow + imports)
# ---------------------------------------------------------------------------


class TestTodoListCompilation:
    def test_for_loop(self, registry: ComponentRegistry) -> None:
        src = _compile_component("TodoList", registry)
        assert "{% for todo in props.todos %}" in src

    def test_show_condition(self, registry: ComponentRegistry) -> None:
        src = _compile_component("TodoList", registry)
        assert "{% if props.todos %}" in src

    def test_else_empty_message(self, registry: ComponentRegistry) -> None:
        src = _compile_component("TodoList", registry)
        assert "{% else %}" in src
        assert "{{ props.empty_message }}" in src

    def test_includes_children(self, registry: ComponentRegistry) -> None:
        src = _compile_component("TodoList", registry)
        assert '{% include "' in src


# ---------------------------------------------------------------------------
# SearchResults (nested Show + For)
# ---------------------------------------------------------------------------


class TestSearchResultsCompilation:
    def test_show_conditions(self, registry: ComponentRegistry) -> None:
        src = _compile_component("SearchResults", registry)
        assert "{% if not props.query %}" in src
        assert "{% if props.results %}" in src

    def test_for_loop_over_results(self, registry: ComponentRegistry) -> None:
        src = _compile_component("SearchResults", registry)
        assert "{% for user in props.results %}" in src

    def test_no_results_message(self, registry: ComponentRegistry) -> None:
        src = _compile_component("SearchResults", registry)
        assert "{{ props.query }}" in src


# ---------------------------------------------------------------------------
# Toast (Alpine directives passthrough)
# ---------------------------------------------------------------------------


class TestToastCompilation:
    def test_alpine_directives(self) -> None:
        src = _compile_component("Toast")
        assert "x-data" in src
        assert "x-init" in src

    def test_variant_class(self) -> None:
        src = _compile_component("Toast")
        assert "toast--{{ props.variant }}" in src

    def test_message_rendering(self) -> None:
        src = _compile_component("Toast")
        assert "{{ props.message }}" in src


# ---------------------------------------------------------------------------
# UserCard (slot rendering)
# ---------------------------------------------------------------------------


class TestUserCardCompilation:
    def test_slot_render(self) -> None:
        src = _compile_component("UserCard")
        assert "slot_actions" in src

    def test_props_rendering(self) -> None:
        src = _compile_component("UserCard")
        assert "{{ props.name }}" in src
        assert "{{ props.email }}" in src
        assert "{{ props.avatar }}" in src


# ---------------------------------------------------------------------------
# SearchBox (Alpine state + HTMX combined)
# ---------------------------------------------------------------------------


class TestSearchBoxCompilation:
    def test_alpine_state(self) -> None:
        src = _compile_component("SearchBox")
        assert "x-data" in src
        assert "query" in src

    def test_model_binding(self) -> None:
        src = _compile_component("SearchBox")
        assert 'x-model="query"' in src

    def test_htmx_search_trigger(self) -> None:
        src = _compile_component("SearchBox")
        assert 'hx-get="/api/search"' in src
        assert "hx-trigger" in src
        assert 'hx-target="#search-results"' in src


# ---------------------------------------------------------------------------
# TodoStats (conditional rendering)
# ---------------------------------------------------------------------------


class TestTodoStatsCompilation:
    def test_show_when_total(self) -> None:
        src = _compile_component("TodoStats")
        assert "{% if props.total > 0 %}" in src

    def test_props_in_output(self) -> None:
        src = _compile_component("TodoStats")
        assert "{{ props.done }}" in src
        assert "{{ props.total }}" in src


# ---------------------------------------------------------------------------
# Navbar (plain HTML, no frontmatter)
# ---------------------------------------------------------------------------


class TestNavbarCompilation:
    def test_nav_structure(self) -> None:
        src = _compile_component("Navbar")
        assert '<nav class="navbar"' in src
        assert "PJX" in src

    def test_all_links_present(self) -> None:
        src = _compile_component("Navbar")
        for href in [
            "/",
            "/counter",
            "/todos",
            "/clock",
            "/search",
            "/protected",
            "/login",
        ]:
            assert f'href="{href}"' in src
