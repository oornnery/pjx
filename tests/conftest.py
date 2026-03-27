"""Shared fixtures and test configuration."""

import sys
from pathlib import Path

import pytest

# Add examples/demo to sys.path so `from app.xxx` imports work
# when running tests from the project root.
_DEMO_DIR = str(Path(__file__).resolve().parent.parent / "examples" / "demo")
if _DEMO_DIR not in sys.path:
    sys.path.insert(0, _DEMO_DIR)

from pjx.ast_nodes import (  # noqa: E402
    Component,
)
from pjx.compiler import Compiler  # noqa: E402
from pjx.parser import parse  # noqa: E402


@pytest.fixture()
def sample_component_source() -> str:
    """A complete .jinja component source with all features."""
    return """---
import Button from "./Button.jinja"

props TodoProps = {
  text: str,
  done: bool = false,
}

slot actions
state count = 0
let css_class = "todo"
---

<style scoped>
.todo { padding: 8px; }
</style>

<div class="{{ css_class }}" reactive>
  <h2>{{ props.text }}</h2>
  <Show when="not props.done">
    <p>Pending ({{ count }})</p>
  </Show>
  <Slot:actions />
</div>"""


@pytest.fixture()
def parsed_component(sample_component_source: str) -> Component:
    """A parsed Component AST."""
    return parse(sample_component_source, path=Path("TodoItem.jinja"))


@pytest.fixture()
def compiled_component(parsed_component: Component) -> str:
    """Compiled Jinja2 source from the sample component."""
    compiler = Compiler()
    result = compiler.compile(parsed_component)
    return result.jinja_source


@pytest.fixture()
def tmp_templates(tmp_path: Path) -> Path:
    """Temporary directory with sample .jinja templates."""
    tpl = tmp_path / "templates"
    tpl.mkdir()
    (tpl / "Button.jinja").write_text("<button>{{ label }}</button>")
    (tpl / "Card.jinja").write_text("<div class='card'>{{ content }}</div>")
    return tpl
