# Template Engines

## Overview

PJX supports three template engines, each wrapping a different backend. The
default **HybridEngine** combines the strengths of both Jinja2 and MiniJinja
into a single interface. All three engines implement the same `EngineProtocol`,
so they are interchangeable at the configuration level without touching
application code.

| Engine      | Backend            | Best for                                        |
| ----------- | ------------------ | ----------------------------------------------- |
| `hybrid`    | Jinja2 + MiniJinja | Default. Optimal mix of compatibility and speed |
| `jinja2`    | Jinja2             | Full ecosystem, extensions, custom filters      |
| `minijinja` | MiniJinja (Rust)   | Maximum throughput on leaf/inline templates     |

Engine selection is a single configuration value:

```toml
# pjx.toml
engine = "hybrid"   # or "jinja2" or "minijinja"
```

Or in Python:

```python
from pjx import PJXConfig

config = PJXConfig(engine="hybrid")
```

The rest of this page describes each engine in detail, the protocol they share,
render modes, and performance characteristics.

---

## HybridEngine (Default)

`HybridEngine` delegates to **Jinja2** for `render()` (pre-registered
templates) and to **MiniJinja** for `render_string()` (ad-hoc / inline
compilation). This gives you:

- Jinja2's bytecode cache, extension system, and mature filter library on
  the production hot path where templates are compiled once at startup.
- MiniJinja's Rust-backed parser for on-the-fly rendering where Jinja2's
  Python-based compilation would otherwise be the bottleneck.

### How it works

Internally, `HybridEngine` holds two sub-engines:

```text
HybridEngine
  _jinja2     -> Jinja2Engine   (used by render, add_template, add_global)
  _minijinja  -> MiniJinjaEngine (used by render_string, add_template, add_global)
```

When you call `add_template()` or `add_global()`, the hybrid engine forwards
the call to **both** sub-engines so that either rendering path has access to
the full template and global registries.

When you call `render(name, ctx)`, the Jinja2 backend handles it. When you
call `render_string(source, ctx)`, the MiniJinja backend handles it.

### When to use

The hybrid engine is the right choice for the vast majority of projects. It is
the default for a reason: you get Jinja2 compatibility for layouts, includes,
and extensions, plus MiniJinja speed for inline-rendered content.

Use the hybrid engine unless you have a specific reason not to.

### Configuration

```toml
# pjx.toml
engine = "hybrid"
```

```python
from pjx import create_engine

engine = create_engine("hybrid")
```

The value `"auto"` is treated as an alias for `"hybrid"`.

---

## Jinja2Engine

`Jinja2Engine` wraps `jinja2.Environment` with `DictLoader`,
`StrictUndefined`, and HTML autoescape enabled by default.

### Features

- **DictLoader** -- templates are stored in an in-memory dictionary. Call
  `add_template(name, source)` to register them.
- **StrictUndefined** -- referencing an undefined variable raises an error
  immediately rather than silently rendering an empty string.
- **HTML autoescape** -- all output is escaped by default, preventing XSS.
- **Full Jinja2 API** -- custom filters, extensions, macros, block
  inheritance, and `{% include %}` all work as expected.

### When to use

Choose the Jinja2 engine when you need:

- Custom Jinja2 extensions (e.g., internationalization, Markdown rendering).
- Complex block inheritance chains that rely on Jinja2-specific semantics.
- Maximum compatibility with existing Jinja2 templates being ported to PJX.
- Filters or globals that depend on `jinja2.Environment` internals.

### Configuration

```toml
# pjx.toml
engine = "jinja2"
```

```python
from pjx import create_engine

engine = create_engine("jinja2")
```

### Internals

```python
class Jinja2Engine:
    def __init__(self) -> None:
        self._templates: dict[str, str] = {}
        self._loader = jinja2.DictLoader(self._templates)
        self._env = jinja2.Environment(
            loader=self._loader,
            autoescape=True,
            undefined=jinja2.StrictUndefined,
        )
```

Templates added via `add_template()` are placed directly into the dict that
backs the `DictLoader`. Jinja2 compiles them to Python bytecode on first
access and caches the result.

---

## MiniJinjaEngine

`MiniJinjaEngine` wraps `minijinja.Environment`, a Rust-backed Jinja2
implementation. The Rust parser and renderer bypass Python's compilation
overhead entirely, making it significantly faster for ad-hoc template
rendering.

### Features

- **Rust-backed parser** -- template compilation happens in Rust, not Python.
  This is the primary source of the 10-74x speedup on `render_string()`.
- **HTML autoescape** -- enabled by default via a custom auto-escape callback.
  Files ending in `.txt`, `.text`, or `.md` are exempt.
- **Python 3.14+ free-threading** -- MiniJinja's Rust core does not hold the
  GIL during template rendering, making it a strong fit for free-threaded
  Python builds.

### Auto-escape callback

MiniJinja uses a callback function to determine the escape mode per template:

```python
def _minijinja_auto_escape(name: str) -> str:
    if name.endswith((".txt", ".text", ".md")):
        return "none"
    return "html"
```

All templates get HTML escaping unless their name ends with a plain-text
extension.

### When to use

Choose the MiniJinja engine when:

- You are rendering leaf templates or inline content where the `render_string`
  path dominates.
- You are running on Python 3.14+ with free-threading and want to avoid GIL
  contention in the template layer.
- Your templates do not rely on Jinja2-specific extensions, macros, or block
  inheritance patterns.

### Limitations

- MiniJinja does not support Jinja2 extensions or custom Python-defined
  filters through the Jinja2 extension API.
- The `{% include %}` semantics differ slightly from Jinja2. For templates
  that rely on include, prefer the hybrid or Jinja2 engine with
  `render_mode = "include"`.
- Deep nesting and heavy iteration loops are currently slower than Jinja2 on
  the `render()` path (pre-registered templates). See the [[#Performance]]
  section for details.

### Configuration

```toml
# pjx.toml
engine = "minijinja"
render_mode = "inline"   # recommended for MiniJinja
```

```python
from pjx import create_engine

engine = create_engine("minijinja")
```

---

## Choosing an Engine

Use the following decision tree to select the right engine for your project.

```text
Start
  |
  v
Do you need Jinja2 extensions, macros, or block inheritance?
  |                                  |
  YES                                NO
  |                                  |
  v                                  v
Use "jinja2"                   Are most of your renders
engine = "jinja2"              inline / ad-hoc (render_string)?
render_mode = "include"             |                |
                                   YES               NO
                                    |                |
                                    v                v
                              Use "minijinja"    Use "hybrid" (default)
                              engine = "minijinja"  engine = "hybrid"
                              render_mode = "inline"
```

### Summary table

| Scenario                              | Engine       | Render mode |
| ------------------------------------- | ------------ | ----------- |
| General purpose (default)             | `hybrid`     | `include`   |
| Need Jinja2 extensions or macros      | `jinja2`     | `include`   |
| Maximum inline rendering performance  | `minijinja`  | `inline`    |
| Free-threaded Python, leaf templates  | `minijinja`  | `inline`    |
| Porting existing Jinja2 templates     | `jinja2`     | `include`   |

### Configuration example

```toml
# pjx.toml
[pjx]
engine = "hybrid"
render_mode = "include"
```

---

## create_engine() Factory

The `create_engine()` factory function is the standard way to instantiate an
engine in application code.

```python
from pjx import create_engine

engine = create_engine("hybrid")
```

### Signature

```python
def create_engine(engine_type: str = "hybrid") -> EngineProtocol:
```

### Parameters

| Parameter     | Type  | Default    | Description                                            |
| ------------- | ----- | ---------- | ------------------------------------------------------ |
| `engine_type` | `str` | `"hybrid"` | One of `"hybrid"`, `"auto"`, `"jinja2"`, `"minijinja"` |

- `"hybrid"` and `"auto"` both return a `HybridEngine` instance.
- `"jinja2"` returns a `Jinja2Engine` instance.
- `"minijinja"` returns a `MiniJinjaEngine` instance.
- Any other value raises `ValueError`.

### Return value

An object implementing `EngineProtocol`. The concrete type depends on the
`engine_type` argument but callers should program against the protocol.

### Example: dynamic engine selection

```python
from pjx import create_engine
from pjx.config import PJXConfig

config = PJXConfig(toml_path="pjx.toml")
engine = create_engine(config.engine)

html = engine.render("pages/Home.jinja", {"title": "Hello"})
```

---

## Engine Protocol

All three engines implement `EngineProtocol`, a `runtime_checkable` Python
`Protocol` class. This means you can use `isinstance()` checks and type
narrowing in your application code.

```python
from pjx.engine import EngineProtocol

assert isinstance(engine, EngineProtocol)
```

### Methods

| Method                                       | Description                                          |
| -------------------------------------------- | ---------------------------------------------------- |
| `render(template_name, context) -> str`      | Render a pre-registered template by name             |
| `render_string(source, context) -> str`      | Render a raw template string (ad-hoc compilation)    |
| `add_template(name, source) -> None`         | Register a template with the given name and source   |
| `add_global(name, value) -> None`            | Add a global variable available in all templates     |
| `has_template(name) -> bool`                 | Check whether a template with the given name exists  |

### Method details

**`render(template_name: str, context: dict[str, Any]) -> str`**

Renders a template that was previously registered via `add_template()`. The
`context` dict is unpacked as template variables. Raises an error if the
template name has not been registered.

**`render_string(source: str, context: dict[str, Any]) -> str`**

Compiles and renders a template from a raw source string. This is the path
used by inline render mode. On the Jinja2 engine, this invokes
`Environment.from_string()`. On MiniJinja, the source is registered under the
internal name `__inline__` and then rendered.

**`add_template(name: str, source: str) -> None`**

Registers a template by name. On Jinja2, this adds the source to the
`DictLoader` backing dict. On MiniJinja, this calls
`Environment.add_template()`. On the hybrid engine, the template is registered
in both sub-engines.

**`add_global(name: str, value: Any) -> None`**

Adds a global variable that is available in every template rendered by this
engine. Commonly used for helper functions, configuration values, or
framework-injected context (e.g., `csrf_token`).

**`has_template(name: str) -> bool`**

Returns `True` if a template with the given name has been registered. The
hybrid engine delegates this check to the Jinja2 sub-engine.

---

## Render Modes

PJX supports two render modes that control how component imports are resolved
at compile time. The render mode is orthogonal to the engine choice, though
certain combinations perform better than others.

### Include mode (default)

```toml
render_mode = "include"
```

In include mode, PJX compiles component imports to standard Jinja2
`{% include %}` tags. Each component remains a separate template file. At
render time, the engine resolves includes by looking up pre-registered
templates by name.

**Advantages:**

- Natural fit for Jinja2's template loader and bytecode cache.
- Each template is compiled and cached independently. Changing one component
  does not invalidate the cache for unrelated components.
- Supports Jinja2 block inheritance and macros across included templates.

**Disadvantages:**

- MiniJinja's `{% include %}` has slightly different semantics and performance
  characteristics than Jinja2's. Using include mode with the MiniJinja engine
  may produce unexpected results for complex template hierarchies.

### Inline mode

```toml
render_mode = "inline"
```

In inline mode, PJX resolves all component imports at compile time by
flattening (inlining) the source of every imported component directly into
the importing template. The result is a single self-contained template string
with no `{% include %}` tags.

**Advantages:**

- Eliminates `{% include %}` resolution overhead at render time.
- Enables the `render_string()` path, where MiniJinja's Rust parser delivers
  10-74x faster compilation than Jinja2.
- Simpler runtime: the engine receives a complete template with no external
  dependencies.

**Disadvantages:**

- If many components share the same dependency, inlining duplicates its source
  in each consumer (though PJX's diamond deduplication mitigates this at the
  compilation level).
- Changes to a shared component require recompilation of all templates that
  import it.

### Choosing a render mode

| Engine      | Recommended render mode | Reason                                    |
| ----------- | ----------------------- | ----------------------------------------- |
| `hybrid`    | `include`               | Jinja2 render path benefits from includes |
| `jinja2`    | `include`               | Bytecode cache, block inheritance         |
| `minijinja` | `inline`                | Unlocks Rust parser via `render_string()` |

### Configuration

```toml
# pjx.toml
[pjx]
engine = "minijinja"
render_mode = "inline"
```

```python
config = PJXConfig(engine="minijinja", render_mode="inline")
```

---

## Performance

PJX includes several compile-time and runtime optimizations that apply across
all engines.

### Mtime-based template caching

The `_compile_template()` function checks each file's modification time
(mtime) before recompilation. If the source has not changed since the last
compile, the cached result is returned immediately.

| Path          | Time      | Notes                          |
| ------------- | --------- | ------------------------------ |
| Cold compile  | ~33 ms    | First compilation of a file    |
| Cached lookup | ~2.7 ms   | 12x speedup over cold compile  |

### Diamond import deduplication

A `_seen` set in the compilation pipeline prevents shared dependencies from
being compiled more than once. In a diamond dependency graph where template A
imports B and C, and both B and C import D, template D is compiled exactly
once.

```text
    A
   / \
  B   C
   \ /
    D   <-- compiled once, not twice
```

### Lexer constant hoisting

The `_SINGLE` and `_ESCAPES` lookup dicts used by the PJX lexer are
module-level constants rather than being rebuilt on every loop iteration.
This eliminates repeated dictionary construction in the hot path of template
parsing.

### O(1) tag recovery

Tag-recovery regexes are compiled once per tag name and cached in a module-level
dict. Subsequent recoveries for the same tag reuse the compiled pattern. The
search resumes from the last matched position instead of re-scanning the entire
source string, giving O(1) amortized cost per recovery.

### Benchmark summary

Benchmarks were measured with `pytest-benchmark` on Python 3.14 (64 tests,
WSL2 Linux).

#### Pre-registered templates (render) -- production path

Templates are compiled once at startup and reused. This is the hot path.

| Scenario              | Jinja2      | MiniJinja    | Winner          |
| --------------------- | ----------- | ------------ | --------------- |
| Minimal template      | 8.9 us      | **3.1 us**   | MiniJinja 2.9x  |
| Simple variable       | 8.4 us      | **3.1 us**   | MiniJinja 2.7x  |
| Loop (10 items)       | 14.6 us     | **7.5 us**   | MiniJinja 1.9x  |
| Loop (1000 items)     | 592 us      | **439 us**   | MiniJinja 1.3x  |
| HTMX page (30 todos)  | 228 us      | **169 us**   | MiniJinja 1.3x  |
| Layout                | **17.1 us** | 20.2 us      | Jinja2 1.2x     |
| Filters               | **18.2 us** | 23.6 us      | Jinja2 1.3x     |
| Conditionals          | **30.1 us** | 48.3 us      | Jinja2 1.6x     |
| Deep nesting          | **170 us**  | 426 us       | Jinja2 2.5x     |
| HTML escaping (50)    | **110 us**  | 221 us       | Jinja2 2x       |
| Nested loops (50x20)  | **489 us**  | 1,536 us     | Jinja2 3.1x     |

Jinja2 wins on complex pre-registered templates (deep nesting, heavy
iteration, many variables). MiniJinja wins on simple and moderate templates.

#### Ad-hoc compilation (render_string) -- inline render path

This is the path used by inline render mode, where MiniJinja's Rust parser
dominates across the board.

| Scenario              | Jinja2       | MiniJinja    | Winner              |
| --------------------- | ------------ | ------------ | ------------------- |
| Minimal template      | 326 us       | **4.4 us**   | MiniJinja **74x**   |
| Simple variable       | 303 us       | **4.4 us**   | MiniJinja **69x**   |
| Loop (10 items)       | 561 us       | **9.8 us**   | MiniJinja **57x**   |
| Filters               | 1,503 us     | **29 us**    | MiniJinja **52x**   |
| Layout                | 960 us       | **24.4 us**  | MiniJinja **39x**   |
| Variables (50)        | 3,716 us     | **101 us**   | MiniJinja **37x**   |
| Complex component     | 2,390 us     | **105 us**   | MiniJinja **23x**   |
| HTMX page (30 todos)  | 1,932 us     | **179 us**   | MiniJinja **11x**   |
| Loop (1000 items)     | 1,150 us     | **453 us**   | MiniJinja **2.5x**  |
| Nested loops (50x20)  | **1,363 us** | 1,538 us     | Jinja2 1.1x         |

MiniJinja wins every scenario except nested loops, where the two engines are
nearly tied. The advantage is most pronounced on simple templates where
Jinja2's Python compilation overhead dominates.

#### Recommendations by workload

| Workload                               | Engine + mode          |
| -------------------------------------- | ---------------------- |
| General web application                | `hybrid` + `include`   |
| Lots of includes and block inheritance | `jinja2` + `include`   |
| Dynamic/inline content, SSE fragments  | `minijinja` + `inline` |
| Free-threaded Python, high concurrency | `minijinja` + `inline` |

Run benchmarks yourself:

```bash
uv run pytest tests/benchmark/ -v --benchmark-sort=mean
```

---

## See also

- [[Configuration Reference]] -- all `pjx.toml` fields including `engine` and `render_mode`
- [[Component Syntax]] -- frontmatter, props, state, slots, and control flow
- [[Deployment]] -- production configuration and server setup
