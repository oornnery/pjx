"""Performance benchmarks — Jinja2 vs MiniJinja engine comparison.

Run with:
    uv run pytest tests/benchmark/ -v --benchmark-group-by=func
    uv run pytest tests/benchmark/ -v --benchmark-sort=mean
    uv run pytest tests/benchmark/ -v --benchmark-compare
"""

from __future__ import annotations

import pytest

from pjx.engine import HybridEngine, Jinja2Engine, MiniJinjaEngine

# ---------------------------------------------------------------------------
# Template sources (shared across benchmarks)
# ---------------------------------------------------------------------------

SIMPLE_TEMPLATE = "Hello {{ name }}!"

VARIABLE_HEAVY = "\n".join(f"{{{{ var_{i} }}}}" for i in range(50))

VARIABLE_HEAVY_CTX = {f"var_{i}": f"value_{i}" for i in range(50)}

CONDITIONAL_TEMPLATE = """\
{% if show_header %}<h1>{{ title }}</h1>{% endif %}
{% if items %}
<ul>
{% for item in items %}
  <li>{{ item.name }} — {{ item.price }}</li>
{% endfor %}
</ul>
{% else %}
<p>No items.</p>
{% endif %}
{% if show_footer %}<footer>{{ footer_text }}</footer>{% endif %}"""

CONDITIONAL_CTX = {
    "show_header": True,
    "title": "Products",
    "items": [{"name": f"Item {i}", "price": f"${i}.99"} for i in range(10)],
    "show_footer": True,
    "footer_text": "End of list",
}

LOOP_SMALL = """\
<ul>
{% for item in items %}
  <li>{{ item }}</li>
{% endfor %}
</ul>"""

LOOP_SMALL_CTX = {"items": list(range(10))}

LOOP_LARGE = LOOP_SMALL
LOOP_LARGE_CTX = {"items": list(range(1000))}

NESTED_LOOP = """\
<table>
{% for row in rows %}
  <tr>
  {% for cell in row %}
    <td>{{ cell }}</td>
  {% endfor %}
  </tr>
{% endfor %}
</table>"""

NESTED_LOOP_CTX = {"rows": [[f"r{r}c{c}" for c in range(20)] for r in range(50)]}

FILTER_TEMPLATE = """\
{{ name|upper }}
{{ name|lower }}
{{ name|title }}
{{ tag_list|length }}
{{ tag_list|join(", ") }}
{{ tag_list|first }}
{{ tag_list|last }}"""

FILTER_CTX = {
    "name": "hello world example",
    "tag_list": ["python", "jinja2", "htmx", "alpine", "pjx"],
}

LAYOUT_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><title>{{ title }}</title></head>
<body>
  <nav>{% for link in nav_links %}<a href="{{ link.href }}">{{ link.text }}</a>{% endfor %}</nav>
  <main>{{ body }}</main>
  <footer>{{ footer }}</footer>
</body>
</html>"""

LAYOUT_CTX = {
    "title": "My Page",
    "nav_links": [
        {"href": "/", "text": "Home"},
        {"href": "/about", "text": "About"},
        {"href": "/contact", "text": "Contact"},
    ],
    "body": "<h1>Welcome</h1><p>Content here.</p>",
    "footer": "2026 PJX",
}

COMPONENT_TEMPLATE = """\
<div class="card {{ modifier }}">
  <div class="card__header">
    <h2>{{ title }}</h2>
    {% if subtitle %}<p class="card__subtitle">{{ subtitle }}</p>{% endif %}
  </div>
  <div class="card__body">
    {% for section in sections %}
    <section>
      <h3>{{ section.heading }}</h3>
      <p>{{ section.text }}</p>
      {% if section.entries %}
      <ul>
        {% for item in section.entries %}
        <li>{{ item }}</li>
        {% endfor %}
      </ul>
      {% endif %}
    </section>
    {% endfor %}
  </div>
  {% if actions %}
  <div class="card__actions">
    {% for action in actions %}
    <button class="btn btn-{{ action.variant }}">{{ action.label }}</button>
    {% endfor %}
  </div>
  {% endif %}
</div>"""

COMPONENT_CTX = {
    "modifier": "card--elevated",
    "title": "Dashboard",
    "subtitle": "Overview of your data",
    "sections": [
        {
            "heading": f"Section {i}",
            "text": f"Description for section {i}",
            "entries": [f"item-{i}-{j}" for j in range(5)],
        }
        for i in range(5)
    ],
    "actions": [
        {"variant": "primary", "label": "Save"},
        {"variant": "secondary", "label": "Cancel"},
        {"variant": "danger", "label": "Delete"},
    ],
}

HTMX_PAGE = """\
<div id="app">
  <form hx-post="/todos" hx-target="#todo-list" hx-swap="innerHTML">
    <input name="text" placeholder="New todo" />
    <button type="submit">Add</button>
  </form>
  <div id="todo-list">
    {% for todo in todos %}
    <div class="todo{% if todo.done %} todo--done{% endif %}" id="todo-{{ todo.id }}">
      <input type="checkbox" hx-post="/todos/{{ todo.id }}/toggle"
             hx-target="#todo-{{ todo.id }}" hx-swap="outerHTML"
             {% if todo.done %}checked{% endif %} />
      <span>{{ todo.text }}</span>
      <button hx-delete="/todos/{{ todo.id }}" hx-target="#todo-{{ todo.id }}"
              hx-swap="outerHTML">X</button>
    </div>
    {% endfor %}
  </div>
</div>"""

HTMX_CTX = {
    "todos": [
        {"id": i, "text": f"Todo item {i}", "done": i % 3 == 0} for i in range(30)
    ],
}

DEEP_NESTING = """\
{% for a in items %}
  <div class="level-1">{{ a.name }}
  {% for b in a.children %}
    <div class="level-2">{{ b.name }}
    {% for c in b.children %}
      <div class="level-3">{{ c.name }}</div>
    {% endfor %}
    </div>
  {% endfor %}
  </div>
{% endfor %}"""

DEEP_NESTING_CTX = {
    "items": [
        {
            "name": f"L1-{a}",
            "children": [
                {
                    "name": f"L2-{a}-{b}",
                    "children": [{"name": f"L3-{a}-{b}-{c}"} for c in range(5)],
                }
                for b in range(5)
            ],
        }
        for a in range(5)
    ],
}

STRING_ESCAPE_TEMPLATE = """\
{% for item in items %}
<div title="{{ item.title }}">{{ item.body }}</div>
{% endfor %}"""

STRING_ESCAPE_CTX = {
    "items": [
        {"title": f'Item "with" <special> & chars {i}', "body": f"<b>Bold {i}</b>"}
        for i in range(50)
    ],
}

MINIMAL_TEMPLATE = """\
<div>
  <span>{{ name }}</span>
</div>"""

MINIMAL_CTX = {"name": "x"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ENGINE_IDS = ["jinja2", "minijinja", "hybrid"]


@pytest.fixture(params=[Jinja2Engine, MiniJinjaEngine, HybridEngine], ids=ENGINE_IDS)
def engine(
    request: pytest.FixtureRequest,
) -> Jinja2Engine | MiniJinjaEngine | HybridEngine:
    """Parametrized engine fixture — each benchmark runs for both engines."""
    return request.param()


# ---------------------------------------------------------------------------
# Benchmarks — render_string (ad-hoc template compilation + render)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="render_string-simple")
def test_render_string_simple(benchmark, engine) -> None:
    """Single variable interpolation."""
    benchmark(engine.render_string, SIMPLE_TEMPLATE, {"name": "World"})


@pytest.mark.benchmark(group="render_string-variables")
def test_render_string_many_variables(benchmark, engine) -> None:
    """50 variable interpolations."""
    benchmark(engine.render_string, VARIABLE_HEAVY, VARIABLE_HEAVY_CTX)


@pytest.mark.benchmark(group="render_string-conditionals")
def test_render_string_conditionals(benchmark, engine) -> None:
    """Conditionals with nested loops."""
    benchmark(engine.render_string, CONDITIONAL_TEMPLATE, CONDITIONAL_CTX)


@pytest.mark.benchmark(group="render_string-loop-small")
def test_render_string_loop_small(benchmark, engine) -> None:
    """Loop over 10 items."""
    benchmark(engine.render_string, LOOP_SMALL, LOOP_SMALL_CTX)


@pytest.mark.benchmark(group="render_string-loop-large")
def test_render_string_loop_large(benchmark, engine) -> None:
    """Loop over 1000 items."""
    benchmark(engine.render_string, LOOP_LARGE, LOOP_LARGE_CTX)


@pytest.mark.benchmark(group="render_string-nested-loops")
def test_render_string_nested_loops(benchmark, engine) -> None:
    """Nested loops: 50 rows x 20 cols."""
    benchmark(engine.render_string, NESTED_LOOP, NESTED_LOOP_CTX)


@pytest.mark.benchmark(group="render_string-filters")
def test_render_string_filters(benchmark, engine) -> None:
    """Built-in filters (upper, lower, join, truncate, length)."""
    benchmark(engine.render_string, FILTER_TEMPLATE, FILTER_CTX)


@pytest.mark.benchmark(group="render_string-layout")
def test_render_string_layout(benchmark, engine) -> None:
    """Full HTML page layout with nav loop."""
    benchmark(engine.render_string, LAYOUT_TEMPLATE, LAYOUT_CTX)


@pytest.mark.benchmark(group="render_string-component")
def test_render_string_component(benchmark, engine) -> None:
    """Complex component with nested sections and actions."""
    benchmark(engine.render_string, COMPONENT_TEMPLATE, COMPONENT_CTX)


@pytest.mark.benchmark(group="render_string-htmx-page")
def test_render_string_htmx_page(benchmark, engine) -> None:
    """HTMX page with 30 todo items, conditionals, dynamic attributes."""
    benchmark(engine.render_string, HTMX_PAGE, HTMX_CTX)


@pytest.mark.benchmark(group="render_string-deep-nesting")
def test_render_string_deep_nesting(benchmark, engine) -> None:
    """Three levels of nested loops (5x5x5 = 125 leaf nodes)."""
    benchmark(engine.render_string, DEEP_NESTING, DEEP_NESTING_CTX)


@pytest.mark.benchmark(group="render_string-escaping")
def test_render_string_html_escaping(benchmark, engine) -> None:
    """50 items with HTML special characters to escape."""
    benchmark(engine.render_string, STRING_ESCAPE_TEMPLATE, STRING_ESCAPE_CTX)


@pytest.mark.benchmark(group="render_string-empty-ctx")
def test_render_string_minimal_template(benchmark, engine) -> None:
    """Template with missing variables (all falsy branches)."""
    benchmark(engine.render_string, MINIMAL_TEMPLATE, MINIMAL_CTX)


# ---------------------------------------------------------------------------
# Benchmarks — render (pre-registered template, render only)
# ---------------------------------------------------------------------------


def _make_engine_with_templates(
    engine_cls: type,
) -> Jinja2Engine | MiniJinjaEngine:
    """Create engine with all benchmark templates pre-registered."""
    eng = engine_cls()
    templates = {
        "simple": SIMPLE_TEMPLATE,
        "variables": VARIABLE_HEAVY,
        "conditionals": CONDITIONAL_TEMPLATE,
        "loop_small": LOOP_SMALL,
        "loop_large": LOOP_LARGE,
        "nested_loop": NESTED_LOOP,
        "filters": FILTER_TEMPLATE,
        "layout": LAYOUT_TEMPLATE,
        "component": COMPONENT_TEMPLATE,
        "htmx_page": HTMX_PAGE,
        "deep_nesting": DEEP_NESTING,
        "escaping": STRING_ESCAPE_TEMPLATE,
        "minimal": MINIMAL_TEMPLATE,
    }
    for name, source in templates.items():
        eng.add_template(name, source)
    return eng


@pytest.fixture(
    params=[Jinja2Engine, MiniJinjaEngine, HybridEngine],
    ids=ENGINE_IDS,
)
def preloaded_engine(
    request: pytest.FixtureRequest,
) -> Jinja2Engine | MiniJinjaEngine | HybridEngine:
    """Engine with all templates pre-registered."""
    return _make_engine_with_templates(request.param)


@pytest.mark.benchmark(group="render-simple")
def test_render_simple(benchmark, preloaded_engine) -> None:
    benchmark(preloaded_engine.render, "simple", {"name": "World"})


@pytest.mark.benchmark(group="render-variables")
def test_render_many_variables(benchmark, preloaded_engine) -> None:
    benchmark(preloaded_engine.render, "variables", VARIABLE_HEAVY_CTX)


@pytest.mark.benchmark(group="render-conditionals")
def test_render_conditionals(benchmark, preloaded_engine) -> None:
    benchmark(preloaded_engine.render, "conditionals", CONDITIONAL_CTX)


@pytest.mark.benchmark(group="render-loop-small")
def test_render_loop_small(benchmark, preloaded_engine) -> None:
    benchmark(preloaded_engine.render, "loop_small", LOOP_SMALL_CTX)


@pytest.mark.benchmark(group="render-loop-large")
def test_render_loop_large(benchmark, preloaded_engine) -> None:
    benchmark(preloaded_engine.render, "loop_large", LOOP_LARGE_CTX)


@pytest.mark.benchmark(group="render-nested-loops")
def test_render_nested_loops(benchmark, preloaded_engine) -> None:
    benchmark(preloaded_engine.render, "nested_loop", NESTED_LOOP_CTX)


@pytest.mark.benchmark(group="render-filters")
def test_render_filters(benchmark, preloaded_engine) -> None:
    benchmark(preloaded_engine.render, "filters", FILTER_CTX)


@pytest.mark.benchmark(group="render-layout")
def test_render_layout(benchmark, preloaded_engine) -> None:
    benchmark(preloaded_engine.render, "layout", LAYOUT_CTX)


@pytest.mark.benchmark(group="render-component")
def test_render_component(benchmark, preloaded_engine) -> None:
    benchmark(preloaded_engine.render, "component", COMPONENT_CTX)


@pytest.mark.benchmark(group="render-htmx-page")
def test_render_htmx_page(benchmark, preloaded_engine) -> None:
    benchmark(preloaded_engine.render, "htmx_page", HTMX_CTX)


@pytest.mark.benchmark(group="render-deep-nesting")
def test_render_deep_nesting(benchmark, preloaded_engine) -> None:
    benchmark(preloaded_engine.render, "deep_nesting", DEEP_NESTING_CTX)


@pytest.mark.benchmark(group="render-escaping")
def test_render_html_escaping(benchmark, preloaded_engine) -> None:
    benchmark(preloaded_engine.render, "escaping", STRING_ESCAPE_CTX)


@pytest.mark.benchmark(group="render-empty-ctx")
def test_render_minimal_template(benchmark, preloaded_engine) -> None:
    benchmark(preloaded_engine.render, "minimal", MINIMAL_CTX)


# ---------------------------------------------------------------------------
# Benchmarks — add_template (template registration / compilation)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="add_template-simple")
def test_add_template_simple(benchmark, engine) -> None:
    """Cost of registering a simple template."""
    i = 0

    def add_one():
        nonlocal i
        engine.add_template(f"t_{i}", SIMPLE_TEMPLATE)
        i += 1

    benchmark(add_one)


@pytest.mark.benchmark(group="add_template-complex")
def test_add_template_complex(benchmark, engine) -> None:
    """Cost of registering a complex component template."""
    i = 0

    def add_one():
        nonlocal i
        engine.add_template(f"c_{i}", COMPONENT_TEMPLATE)
        i += 1

    benchmark(add_one)


# ---------------------------------------------------------------------------
# Benchmarks — add_global
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="add_global")
def test_add_global(benchmark, engine) -> None:
    """Cost of adding a global variable."""
    i = 0

    def add_one():
        nonlocal i
        engine.add_global(f"g_{i}", f"value_{i}")
        i += 1

    benchmark(add_one)


# ---------------------------------------------------------------------------
# Benchmarks — has_template
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="has_template")
def test_has_template(benchmark, preloaded_engine) -> None:
    """Lookup cost for template existence check."""
    benchmark(preloaded_engine.has_template, "component")


# ---------------------------------------------------------------------------
# Benchmarks — throughput (many renders in sequence)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="throughput-100-renders")
def test_throughput_100_renders(benchmark, preloaded_engine) -> None:
    """Render the component template 100 times sequentially."""

    def batch():
        for _ in range(100):
            preloaded_engine.render("component", COMPONENT_CTX)

    benchmark(batch)


@pytest.mark.benchmark(group="throughput-mixed-templates")
def test_throughput_mixed_templates(benchmark, preloaded_engine) -> None:
    """Cycle through all template types to simulate real workload."""
    workload = [
        ("simple", {"name": "World"}),
        ("conditionals", CONDITIONAL_CTX),
        ("loop_small", LOOP_SMALL_CTX),
        ("component", COMPONENT_CTX),
        ("htmx_page", HTMX_CTX),
        ("layout", LAYOUT_CTX),
        ("deep_nesting", DEEP_NESTING_CTX),
    ]

    def batch():
        for name, ctx in workload:
            preloaded_engine.render(name, ctx)

    benchmark(batch)
