from __future__ import annotations

import html


def _code(src: str) -> str:
    return html.escape(src.strip())


_SNIPPET_PROPS = _code("""
@component Button {
  @props { label: str, variant: str = "default" }
  <button class="btn btn-{{ variant }}">{{ label }}</button>
}

<Button label="Primary" />
<Button label="Outline" variant="outline" />
""")

_SNIPPET_CONTROL = _code("""
<Switch on="{{ status }}">
  <Match value="ready">
    <Badge variant="ready" label="Ready" />
  </Match>
  <Match value="building">...</Match>
</Switch>

<For each="{{ items }}" as="item">
  <li>{{ item.name }}</li>
</For>

<Show when="{{ not items }}">
  <Alert message="No items." />
</Show>
""")

_SNIPPET_SLOTS = _code("""
@component Card {
  @props { title: str = "" }
  @slot default
  @slot footer?
  <div class="card">
    <Show when="{{ title }}">
      <div class="card-header">{{ title }}</div>
    </Show>
    <div class="card-body"><slot /></div>
    <Show when="{{ @has_slot('footer') }}">
      <div class="card-footer"><slot name="footer" /></div>
    </Show>
  </div>
}

<Card title="Hello">
  <p>Body content</p>
  <:footer>
    <Button label="OK" />
  </:footer>
</Card>
""")

_SNIPPET_ALPINE = _code("""
@state { open: false }

<div x-data="{{ @state }}">
  <button
    @click.alpine="open = !open"
    class="btn btn-secondary"
  >Toggle</button>
  <div x-show="open">
    Content revealed by Alpine
  </div>
</div>
""")

_SNIPPET_HTMX = _code("""
@bind from exemples.state import Counter

@props { count: int = 0 }

<div id="counter-display">
  <button
    @click.htmx="post:/actions/counter/dec"
    @target="#counter-display"
    @swap="outerHTML"
  >−</button>
  <span>{{ count }}</span>
  <button
    @click.htmx="post:/actions/counter/inc"
    @target="#counter-display"
    @swap="outerHTML"
  >+</button>
</div>
""")

_SNIPPET_MULTICOMP = _code("""
// ui.pjx — multiple components in one file

@component Stat {
  @props { label: str, value: str }
  <div class="stat-card">...</div>
}

@component Tag {
  @props { label: str, color: str = "neutral" }
  <span class="tag tag-{{ color }}">{{ label }}</span>
}

// Usage in another file:
@from components.ui.ui import Stat, Tag

<Stat label="Templates" value="6" />
<Tag label="ready" color="ready" />
""")

_SNIPPET_BIND = _code("""
# exemples/state.py
class Counter:
    _count: int = 0

    @classmethod
    def increment(cls) -> int:
        cls._count += 1
        return cls._count

    @classmethod
    def context(cls) -> dict:
        return {"count": cls._count}

# counter.pjx
@bind from exemples.state import Counter
@props { count: int = 0 }

<div id="counter-display">
  <span>{{ count }}</span>
</div>
""")


def get_showcase_context() -> dict[str, object]:
    return {
        "status": "ready",
        "items": [
            {"name": "parse()", "desc": "Parses .pjx source into a PjxFile AST"},
            {
                "name": "compile_pjx()",
                "desc": "Compiles AST to a Jinja2 template string",
            },
            {"name": "Runtime", "desc": "Renders templates with prop validation"},
        ],
        "snippet_props": _SNIPPET_PROPS,
        "snippet_control": _SNIPPET_CONTROL,
        "snippet_slots": _SNIPPET_SLOTS,
        "snippet_alpine": _SNIPPET_ALPINE,
        "snippet_htmx": _SNIPPET_HTMX,
        "snippet_multicomp": _SNIPPET_MULTICOMP,
        "snippet_bind": _SNIPPET_BIND,
    }
