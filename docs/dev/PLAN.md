# PJX — Implementation Plan

> Technical roadmap with phases, dependencies, and completion criteria.
> Full DSL reference in `IDEA.md`. Technical specification in `SPEC.md`.

---

## Phase Overview

| Phase | Name             | Modules                                         | Depends on  | Status |
| ----- | ---------------- | ----------------------------------------------- | ----------- | ------ |
| 1     | Core             | errors, ast_nodes, lexer, parser, compiler, css | —           | ✅     |
| 2     | Component System | config, registry, props, slots                  | Phase 1     | ✅     |
| 3     | Runtime          | engine, integration, log, sse                   | Phases 1-2  | ✅     |
| 4     | CLI              | cli/* , assets                                  | Phases 1-3  | ✅     |
| 5     | Frontend Tooling | npm integration, vendor build, tailwind         | Phase 4     |        |
| 6     | Improvements     | attrs, validation, assets, inline, check, AST   | Phases 1-4  | ✅     |

---

## Phase 1 — Core ✅

Goal: parse a `.jinja` file and compile to Jinja2 + Alpine + HTMX.

### 1.1 `errors.py` — Exception Hierarchy

**Responsibility**: Base exceptions with location (file, line, column).

**Deliverables**:

- `PJXError(Exception)` — base
- `ParseError(PJXError)` — syntax error in `.jinja`
- `LexError(ParseError)` — error in frontmatter tokenization
- `CompileError(PJXError)` — error in AST → output compilation
- `PropValidationError(PJXError)` — prop validation
- `ImportResolutionError(PJXError)` — import not found
- `ConfigError(PJXError)` — invalid configuration

All must include `path: Path | None`, `line: int | None`,
`col: int | None` for rich error messages.

**Tests**:

- Instantiation with and without location
- Message formatting with path:line:col
- Correct inheritance between exceptions

**Done criteria**: All exceptions documented, tested, and importable.

### 1.2 `ast_nodes.py` — Intermediate Representation

**Responsibility**: Immutable dataclasses representing a parsed component.

**Deliverables**:

```python
# Root node
Component(path, extends, from_imports, imports, props, slots, stores,
          variables, states, computed, body, style)

# Frontmatter declarations
ExtendsDecl(source)
FromImportDecl(module, names)
ImportDecl(names, source, alias, wildcard)
PropsDecl(name, fields)
PropField(name, type_expr, default)
SlotDecl(name, fallback)
StoreDecl(name, value)
LetDecl(name, expr) / ConstDecl(name, expr)
StateDecl(name, value)
ComputedDecl(name, expr)

# Body nodes
ElementNode(tag, attrs, children, self_closing)
TextNode(content)
ExprNode(expr)
ShowNode(when, body, fallback)
ForNode(each, as_var, body, empty)
SwitchNode(on, cases, default)
CaseNode(value, body)
PortalNode(target, swap, body)
ErrorBoundaryNode(fallback, body, error_slot)
AwaitNode(src, trigger, loading, error)
TransitionNode(enter, leave, body)
TransitionGroupNode(tag, enter, leave, move, body)
FragmentNode(children)
TeleportNode(to, body)
ComponentNode(name, attrs, children, slots, spread)
SlotRenderNode(name, fallback)
SlotPassNode(name, content)

# Output
CompiledComponent(jinja_source, css, alpine_data, scope_hash)
ScopedStyle(source, hash)
```

All with `@dataclass(frozen=True, slots=True)`.
`Node` as type alias union of all node types.

**Tests**:

- Instantiation of each dataclass
- Immutability (frozen)
- Correct type union

**Done criteria**: All spec dataclasses representable, tested.

### 1.3 `lexer.py` — Tokenizer

**Responsibility**: Tokenize the frontmatter content into tokens.

**Deliverables**:

- `TokenKind(StrEnum)` — EXTENDS, IMPORT, FROM, AS, PROPS, SLOT, STORE,
  LET, CONST, STATE, COMPUTED, IDENT, STRING, NUMBER, LBRACE, RBRACE,
  LBRACKET, RBRACKET, LPAREN, RPAREN, COMMA, COLON, EQUALS, PIPE, STAR,
  DOT, ELLIPSIS, NEWLINE, EOF
- `Token(kind, value, line, col)` — frozen dataclass
- `tokenize(source: str) -> list[Token]` — hand-written single-pass lexer

**Design**:

- Each line starts with a keyword → lexer identifies by prefix
- Strings: `"..."` and `'...'`
- Numbers: integers and floats
- Identifiers: `[a-zA-Z_][a-zA-Z0-9_]*`
- Comments: `#` until end of line (ignored)
- Errors: `LexError` with position

**Tests**:

- `test_tokenize_extends`
- `test_tokenize_from_import`
- `test_tokenize_import_default`
- `test_tokenize_import_named`
- `test_tokenize_import_wildcard`
- `test_tokenize_import_alias`
- `test_tokenize_props_simple`
- `test_tokenize_props_pydantic_types` (Literal, Annotated, EmailStr)
- `test_tokenize_slot`
- `test_tokenize_store`
- `test_tokenize_let_const_state_computed`
- `test_tokenize_string_escapes`
- `test_tokenize_comments_ignored`
- `test_tokenize_error_unterminated_string`
- `test_tokenize_error_invalid_char`

**Done criteria**: Tokenizes all examples from IDEA.md without errors.

### 1.4 `parser.py` — Full Parser

**Responsibility**: Parse a complete `.jinja` file into a `Component` AST.

**Deliverables**:

- `parse(source: str, path: Path) -> Component`
- `parse_file(path: Path) -> Component`
- `_extract_blocks(source) -> tuple[str | None, str | None, str]`
  — separates script, style, body
- `_parse_script(tokens) -> ScriptDeclarations`
  — recursive descent LL(1)
- `_parse_body(html, known_components) -> list[Node]`
  — subclass of `html.parser.HTMLParser`

**Body parser design**:

- Uppercase tags (`<Show>`, `<For>`, `<Switch>`, etc.) → control flow nodes
- Registered PascalCase tags → ComponentNode
- Lowercase tags → ElementNode
- `<Slot:name>` → SlotRenderNode
- `<slot:name>` → SlotPassNode
- `{{ expr }}` → ExprNode
- Free text → TextNode
- Attributes preserved as `dict[str, str | bool]` for the compiler

**Tests**:

- `test_parse_empty_component` (body only, no frontmatter)
- `test_parse_full_component` (frontmatter + style + body)
- `test_extract_blocks_*` (with/without frontmatter, with/without style)
- `test_parse_extends`
- `test_parse_from_import`
- `test_parse_script_imports_*` (default, named, wildcard, alias)
- `test_parse_script_props_pydantic` (Literal, Annotated, EmailStr)
- `test_parse_script_slots_*` (with/without fallback)
- `test_parse_script_store`
- `test_parse_script_variables_*` (let, const, state, computed)
- `test_parse_body_show` / `test_parse_body_show_fallback`
- `test_parse_body_for` / `test_parse_body_for_empty`
- `test_parse_body_switch`
- `test_parse_body_portal`
- `test_parse_body_transition_group`
- `test_parse_body_nested_control_flow`
- `test_parse_body_component_with_slots`
- `test_parse_body_component_with_spread`
- `test_parse_body_self_closing_component`
- `test_parse_error_*` (unterminated tags, unknown keywords, etc.)

**Done criteria**: Parses the complete Dashboard example (IDEA.md §16)
producing correct AST.

### 1.5 `css.py` — Scoped CSS

**Responsibility**: Extract and scope CSS from components.

**Deliverables**:

- `generate_scope_hash(path: Path) -> str` — sha256[:7]
- `scope_css(css_source: str, scope_hash: str) -> str`
  — regex-based selector prefixing

**Rewrite rules**:

```text
.alert { ... }           → [data-pjx-a1b2c3] .alert { ... }
#main { ... }            → [data-pjx-a1b2c3] #main { ... }
div.card { ... }         → [data-pjx-a1b2c3] div.card { ... }
.a .b { ... }            → [data-pjx-a1b2c3] .a .b { ... }
.a, .b { ... }           → [data-pjx-a1b2c3] .a, [data-pjx-a1b2c3] .b { ... }
@media (...) { .a {} }   → @media (...) { [data-pjx-a1b2c3] .a {} }
```

**Tests**:

- `test_scope_hash_deterministic`
- `test_scope_hash_unique_per_path`
- `test_scope_css_class_selector`
- `test_scope_css_id_selector`
- `test_scope_css_compound_selector`
- `test_scope_css_multiple_selectors` (comma)
- `test_scope_css_media_query`
- `test_scope_css_nested_rules`
- `test_scope_css_preserves_properties`

**Done criteria**: All common CSS patterns scoped correctly.

### 1.6 `compiler.py` — AST to Output

**Responsibility**: Compile `Component` AST into Jinja2 + Alpine + HTMX.

**Deliverables**:

- `Compiler(registry: ComponentRegistry)`
- `Compiler.compile(component: Component) -> CompiledComponent`
- `_compile_preamble(component) -> str` — `{% set %}` for let/const/computed
- `_compile_node(node: Node) -> str` — recursive walker
- `_compile_attrs(attrs: dict) -> str` — transforms DSL attrs

**Attribute rules** (consolidated from SPEC.md §§9-13):

| Prefix/name         | Transformation             |
| ------------------- | -------------------------- |
| `bind:text`         | `x-text`                   |
| `bind:model[.mod]`  | `x-model[.mod]`            |
| `bind:show`         | `x-show`                   |
| `bind:html`         | `x-html`                   |
| `bind:cloak`        | `x-cloak`                  |
| `bind:ref`          | `x-ref`                    |
| `bind:transition`   | `x-transition`             |
| `bind:init`         | `x-init`                   |
| `bind:{attr}`       | `:{attr}`                  |
| `on:{event}[.mods]` | `@{event}[.mods]`          |
| `action:{verb}`     | `hx-{verb}`                |
| `swap`              | `hx-swap`                  |
| `target`            | `hx-target`                |
| `trigger`           | `hx-trigger`               |
| `select`            | `hx-select`                |
| `select-oob`        | `hx-select-oob`            |
| `confirm`           | `hx-confirm`               |
| `indicator`         | `hx-indicator`             |
| `push-url`          | `hx-push-url`              |
| `replace-url`       | `hx-replace-url`           |
| `vals`              | `hx-vals`                  |
| `headers`           | `hx-headers`               |
| `encoding`          | `hx-encoding`              |
| `preserve`          | `hx-preserve`              |
| `sync`              | `hx-sync`                  |
| `disabled-elt`      | `hx-disabled-elt`          |
| `boost`             | `hx-boost="true"`          |
| `live`              | `hx-ext="sse" sse-connect` |
| `channel`           | `sse-swap`                 |
| `close`             | `sse-close`                |
| `socket`            | `hx-ext="ws" ws-connect`   |
| `send`              | `ws-send`                  |
| `reactive`          | `x-data="..."`             |
| `loading:*`         | HTMX indicator patterns    |

**Tests**:

- `test_compile_let_const` → `{% set %}`
- `test_compile_state_to_alpine_data`
- `test_compile_extends` → `{% extends %}` + `{% block %}`
- `test_compile_store` → `Alpine.store()` init script
- `test_compile_show` / `test_compile_show_fallback`
- `test_compile_for` / `test_compile_for_empty`
- `test_compile_switch`
- `test_compile_portal`
- `test_compile_await`
- `test_compile_fragment`
- `test_compile_transition_group`
- `test_compile_attrs_bind_*`
- `test_compile_attrs_on_*`
- `test_compile_attrs_action_*`
- `test_compile_attrs_htmx_*` (swap, target, trigger, etc.)
- `test_compile_attrs_sse`
- `test_compile_attrs_websocket`
- `test_compile_attrs_reactive`
- `test_compile_attrs_loading`
- `test_compile_component_include`
- `test_compile_component_spread`
- `test_compile_scoped_css`
- `test_compile_builtins` (has_slot, url_for, static)
- `test_compile_dashboard_example` (IDEA.md §17 end-to-end)

**Done criteria**: Compiles the Dashboard from IDEA.md to valid Jinja2.

---

## Phase 2 — Component System ✅

Goal: resolve imports, validate props, resolve slots, load config.

### 2.1 `config.py` — Configuration

**Responsibility**: Load config from `pjx.toml` and env vars.

**Deliverables**:

```python
class PJXConfig(BaseSettings):
    engine: Literal["jinja2", "minijinja", "auto"] = "jinja2"
    debug: bool = False
    template_dirs: list[Path] = [Path("templates")]
    static_dir: Path = Path("static")
    pages_dir: Path = Path("templates/pages")
    components_dir: Path = Path("templates/components")
    layouts_dir: Path = Path("templates/layouts")
    ui_dir: Path = Path("templates/ui")
    vendor_templates_dir: Path = Path("templates/vendor")
    vendor_static_dir: Path = Path("static/vendor")
    host: str = "127.0.0.1"
    port: int = 8000
    alpine: bool = True
    htmx: bool = True
    tailwind: bool = False
```

**Tests**: Load from TOML, env override, defaults.

**Done criteria**: Config loads from pjx.toml and env vars correctly.

### 2.2 `registry.py` — Component Registry

**Responsibility**: Resolve imports, cache components, detect
circular imports.

**Deliverables**:

- `ComponentRegistry(root_dirs: list[Path])`
- `resolve(import_decl, from_path) -> list[ResolvedComponent]`
- `get(name) -> Component | None`
- `register(name, component)`
- `compile_all(entry: Path) -> dict[str, CompiledComponent]`

**Design**:

- Cache: `dict[str, Component]` (by name) + `dict[Path, Component]` (by path)
- Resolution: relative to the importing file
- Circular: set of paths "being resolved" → `ImportResolutionError`
- Invalidation (dev): check mtime before serving from cache

**Tests**:

- `test_resolve_relative_import`
- `test_resolve_named_import_from_dir`
- `test_resolve_wildcard_import`
- `test_resolve_alias`
- `test_circular_import_detection`
- `test_cache_hit`
- `test_cache_invalidation_mtime`

**Done criteria**: Resolves all import patterns from IDEA.md §2.

### 2.3 `props.py` — Props to Pydantic

**Responsibility**: Generate dynamic `BaseModel` from `PropsDecl`.

**Deliverables**:

- `generate_props_model(decl: PropsDecl) -> type[BaseModel]`
- `validate_props(model, data) -> BaseModel`

**Mapping** (DSL uses native Pydantic types):

| DSL                            | Generated BaseModel                              |
| ------------------------------ | ------------------------------------------------ |
| `name: str`                    | `name: str`                                      |
| `age: int = 0`                 | `age: int = 0`                                   |
| `role: Literal["a","b"] = "a"` | `role: Literal["a","b"] = "a"`                   |
| `email: EmailStr`              | `email: EmailStr`                                |
| `bio: str \| None = None`      | `bio: str \| None = None`                        |
| `tags: list[str] = []`         | `tags: list[str] = Field(default_factory=list)`  |
| `score: Annotated[int, Gt(0)]` | `score: Annotated[int, Gt(0)]`                   |
| `url: HttpUrl \| None = None`  | `url: HttpUrl \| None = None`                    |

**Tests**:

- `test_generate_required_field`
- `test_generate_optional_field`
- `test_generate_literal_choices`
- `test_generate_pydantic_type` (EmailStr, HttpUrl)
- `test_generate_annotated_constraints`
- `test_generate_nullable`
- `test_generate_list_factory`
- `test_generate_callable`
- `test_validate_props_valid`
- `test_validate_props_missing_required`
- `test_validate_props_invalid_choice`
- `test_validate_props_constraint_violation`

**Done criteria**: Generates models for all prop examples from IDEA.md §3.

### 2.4 `slots.py` — Slot Resolution

**Responsibility**: Resolve declared slots with content passed by the parent.

**Deliverables**:

- `resolve_slots(declarations, passed_slots, children) -> dict[str, str]`

**Tests**:

- `test_resolve_slot_with_content`
- `test_resolve_slot_fallback`
- `test_resolve_slot_default_children`
- `test_resolve_slot_empty`

**Done criteria**: Resolves all slot patterns from IDEA.md §5.

---

## Phase 3 — Runtime ✅

Goal: render templates and integrate with FastAPI.

### 3.1 `log.py` — Logging

**Responsibility**: Configure logging with Rich.

**Deliverables**:

- `setup_logging(debug: bool) -> None`
- `logger = logging.getLogger("pjx")`

**Done criteria**: Logs formatted with Rich, configurable levels.

### 3.2 `engine.py` — Template Engine

**Responsibility**: Unified interface over Jinja2 and MiniJinja.

**Deliverables**:

- `EngineProtocol` (Protocol)
- `Jinja2Engine` — wrapper over `jinja2.Environment`
- `MiniJinjaEngine` — wrapper over `minijinja.Environment`
- `create_engine(config) -> EngineProtocol`

**Design**:

- `auto` → Jinja2 (current default)
- Both implement: `render`, `render_string`, `add_template`, `add_global`
- Compiled templates are registered via `add_template`

**Tests**:

- `test_jinja2_engine_render`
- `test_jinja2_engine_render_string`
- `test_minijinja_engine_render`
- `test_create_engine_auto_returns_jinja2`
- `test_create_engine_explicit`

**Done criteria**: Both engines render templates compiled by the
compiler.

### 3.3 `integration.py` — FastAPI

**Responsibility**: Decorators `@pjx.page` and `@pjx.component`, mounting
of static files.

**Deliverables**:

- `PJX(app, template_dirs?, config?)`
- `PJX.page(path, template, **kwargs) -> decorator`
- `PJX.component(template) -> decorator`
- `PJX.render(request, template, context) -> HTMLResponse`

**Flow**:

1. Decorator registers route in FastAPI
2. Handler → context dict
3. Registry resolves template (with cache)
4. Props validated via Pydantic
5. Engine renders
6. Returns HTMLResponse

**Tests**:

- `test_page_decorator_registers_route`
- `test_page_decorator_renders_template`
- `test_component_decorator_renders_partial`
- `test_props_validation_error_response`
- `test_render_manual`
- Integration tests with `httpx.AsyncClient` + FastAPI TestClient

**Done criteria**: A page and a partial component render
correctly via FastAPI.

### 3.4 `sse.py` — Server-Sent Events

**Responsibility**: Helpers for SSE endpoints.

**Deliverables**:

- `EventStream` — async context with `send(event, data)` and
  `send_html(event, template, context)`
- `PJX.sse(path) -> decorator`

**Tests**:

- `test_sse_stream_sends_event`
- `test_sse_stream_renders_template`

**Done criteria**: SSE endpoint works with `live="/url"` in the template.

---

## Phase 4 — CLI ✅

Goal: complete CLI for development.

### 4.1 `cli/__init__.py` — Typer App

**Deliverables**:

- `app = typer.Typer(name="pjx")`
- Entry point in pyproject.toml: `[project.scripts] pjx = "pjx.cli:app"`

### 4.2 `cli/init.py` — `pjx init`

Scaffolds directory structure, creates `pjx.toml`, `package.json` with
Alpine + HTMX.

### 4.3 `cli/dev.py` — `pjx dev` / `pjx run`

- `dev`: `uvicorn app:app --reload --host --port` (from config)
- `run`: `uvicorn app:app --host --port --workers N`

### 4.4 `cli/build.py` — `pjx build` / `check` / `format`

- `build`: Compiles all `.jinja` + bundle CSS + `npm run build`
- `check`: Parses all `.jinja`, reports errors with location
- `format`: Re-emits `.jinja` with consistent formatting

### 4.5 `cli/packages.py` — `pjx add` / `remove`

- `add <pkg>`: `npm install <pkg>` + copies dist to `static/vendor/`
- `remove <pkg>`: `npm uninstall <pkg>` + cleans vendor

### 4.6 `assets.py` — Static Files

**Responsibility**: Discover and manage static files, copy
vendor builds.

**Tests for the entire CLI**:

- `test_cli_init_creates_dirs`
- `test_cli_check_valid_files`
- `test_cli_check_reports_errors`
- `test_cli_add_runs_npm`
- `test_cli_build_compiles_all`

**Done criteria**: All commands execute without errors and produce correct
output.

---

## Phase 5 — Frontend Tooling

Goal: integration with npm, build pipeline, Tailwind.

### 5.1 npm Integration

- `pjx init` creates `package.json` with Alpine.js + HTMX as deps
- `pjx add <pkg>` → `npm install <pkg>`
- `pjx remove <pkg>` → `npm uninstall <pkg>`
- `pjx build` → `npm run build` (configured with script in package.json)

### 5.2 Vendor Build

- ESLint for custom JS linting
- Build script copies dist files to `static/vendor/`:
  - `node_modules/alpinejs/dist/cdn.min.js` → `static/vendor/alpine.min.js`
  - `node_modules/htmx.org/dist/htmx.min.js` → `static/vendor/htmx.min.js`

### 5.3 Tailwind CSS (optional)

- If `tailwind = true` in config:
  - `pjx init` adds `tailwindcss` to package.json
  - `pjx build` runs `npx tailwindcss -i input.css -o static/css/tailwind.css`
  - Base template includes `<link>` for tailwind.css

**Done criteria**: `pjx init && pjx add alpinejs && pjx build` produces
functional vendor/.

---

## Phase 6 — Improvements (completed)

Goal: close critical gaps for production — attrs passthrough, asset
pipeline, runtime validation, inline rendering, and static analysis.

### 6.1 Attrs Passthrough ✅

- `separate_attrs()` in `src/pjx/props.py` — separates props from extras
- Compiler resolves child's `PropsDecl` via registry
- Extras rendered as `{% set attrs %}...{% endset %}`
- 6 tests in `tests/unit/test_props.py::TestSeparateAttrs`
- 4 tests in `tests/unit/test_compiler.py::TestComponentAttrsPassthrough`

### 6.2 Runtime Prop Validation ✅

- `validate_props: bool = True` in `PJXConfig`
- Cache of Pydantic models in `PJX._props_models`
- Validation before render — `PropValidationError` with clear message
- 4 tests in `tests/integration/test_integration.py::TestRuntimePropValidation`

### 6.3 Asset Pipeline ✅

- `AssetDecl(kind, path)` in `ast_nodes.py`
- Tokens `CSS`/`JS` in lexer, `_parse_asset()` in parser
- `AssetCollector` in `src/pjx/assets.py` — dedup, render `<link>`/`<script>`
- `pjx_assets` global available in templates
- 7 tests in `tests/unit/test_assets.py`
- 4 tests in `tests/unit/test_parser.py::TestAssetDeclarations`

### 6.4 Inline Render Mode ✅

- `render_mode: Literal["include", "inline"]` in `PJXConfig`
- `Compiler.inline_includes()` — substitutes `{% include %}` recursively
- MiniJinja inline: 10-74x faster than Jinja2 ad-hoc
- 5 tests in `tests/unit/test_compiler.py::TestInlineIncludes`
- 1 test in `tests/integration/test_integration.py::TestInlineRenderMode`

### 6.5 Static Analysis (`pjx check`) ✅

- `src/pjx/checker.py` — `check_imports`, `check_props`, `check_slots`
- `_walk_nodes()` — recursive AST walker
- CLI `pjx check` updated with 2 phases: parse+register, then check
- 10 tests in `tests/unit/test_checker.py`

### 6.6 AST Node Compiler Coverage ✅

- Tests for `ErrorBoundaryNode`, `AwaitNode`, `TransitionNode`, `StoreDecl`
- 10 tests added in `tests/unit/test_compiler.py`

**Total: 300 tests passing** (364 with benchmarks).

---

## Testing Strategy

### Structure

```text
tests/
├── conftest.py                # Global fixtures
├── unit/
│   ├── test_errors.py
│   ├── test_ast_nodes.py
│   ├── test_lexer.py
│   ├── test_parser.py
│   ├── test_compiler.py
│   ├── test_css.py
│   ├── test_props.py
│   ├── test_slots.py
│   ├── test_registry.py
│   ├── test_engine.py
│   ├── test_config.py
│   ├── test_checker.py        # Static analysis
│   └── test_assets.py         # Asset pipeline
├── integration/
│   ├── test_integration.py    # FastAPI + PJX decorators
│   ├── test_sse.py
│   └── test_cli.py
├── benchmark/
│   └── test_engine_benchmark.py  # Jinja2 vs MiniJinja (64 tests)
└── e2e/
    └── test_full_render.py    # Parse → compile → render → assert HTML
```

### Fixtures (conftest.py)

- `sample_component_source` — `.jinja` string with full frontmatter
- `parsed_component` — ready `Component` AST
- `compiled_component` — ready `CompiledComponent`
- `pjx_app` — FastAPI app with PJX mounted
- `test_client` — `httpx.AsyncClient` with the app
- `tmp_templates` — temporary directory with example `.jinja` files

### Conventions

- Names: `test_<unit>_<scenario>_<expected>`
- Parametrize to cover variants (e.g.: all bind:* types)
- Markers: `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.e2e`
- Minimum coverage: 90% for core (lexer, parser, compiler)
- Property-based (Hypothesis): generate random valid/invalid frontmatter
  for lexer and parser fuzzing

---

## Example Components

Create in `examples/` for validation and documentation:

| File                       | Covers                                     |
| -------------------------- | ------------------------------------------ |
| `Counter.jinja`            | state, on:click, bind:text, reactive       |
| `TodoItem.jinja`           | props, slots, Show, For, scoped CSS        |
| `UserCard.jinja`           | Pydantic types (EmailStr, Literal)         |
| `Dashboard.jinja`          | Full example from IDEA.md §17              |
| `TreeNode.jinja`           | Recursive component                        |
| `layouts/Base.jinja`       | Base layout with head/content/footer slots |
| `pages/Home.jinja`         | extends, slot:head, prop spreading         |
| `errors/404.jinja`         | Error page with extends                    |

These examples serve as test fixtures and real usage documentation.

---

## Directory Restructuring

The current `src/main.py` structure needs to migrate to `src/pjx/`:

```text
# Before
src/
├── __init__.py
└── main.py

# After
src/
└── pjx/
    ├── __init__.py
    ├── __main__.py
    ├── errors.py
    ├── ast_nodes.py
    ├── lexer.py
    ├── parser.py
    ├── compiler.py
    ├── css.py
    ├── config.py
    ├── registry.py
    ├── props.py
    ├── slots.py
    ├── engine.py
    ├── integration.py
    ├── checker.py       # Static analysis
    ├── assets.py        # Asset pipeline + collector
    ├── sse.py
    ├── log.py
    └── cli/
        ├── __init__.py
        ├── init.py
        ├── dev.py
        ├── build.py
        └── packages.py
```

Update `pyproject.toml` with `[project.scripts]` for the CLI entry point.

---

## Implementation Order (dependencies)

```text
Phase 1 (parallel where possible):
  errors.py ──────┐
  ast_nodes.py ───┤
  css.py ─────────┼──→ lexer.py ──→ parser.py ──→ compiler.py
                  │
Phase 2:          │
  config.py ──────┤
  props.py ───────┤
  slots.py ───────┼──→ registry.py
                  │
Phase 3:          │
  log.py ─────────┤
  engine.py ──────┼──→ integration.py ──→ sse.py
                  │
Phase 4:          │
  assets.py ──────┼──→ cli/*
                  │
Phase 5:          └──→ frontend tooling
```

---

## End-to-End Validation

At the end of each phase, validate with:

```bash
rtk uv run ruff format --check .
rtk uv run ruff check .
rtk uv run ty check
rtk uv run pytest -v
rtk uv run rumdl check .
```

### Final E2E Test (after Phase 3)

1. Create a `TodoItem.jinja` component with props, state, slots
2. Create a `Home.jinja` page that uses `TodoItem`
3. Mount FastAPI app with `PJX`
4. Verify that GET `/` returns valid HTML with:
   - Correct `{% if %}` / `{% for %}`
   - `x-data` with states
   - `hx-get` / `hx-post` with URLs
   - Scoped CSS with `data-pjx-*`
   - Resolved slots
