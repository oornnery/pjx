# PJX — Plano de Implementação

> Roadmap técnico com fases, dependências e critérios de conclusão.
> Referência completa da DSL em `IDEA.md`. Especificação técnica em `SPEC.md`.

---

## Visão Geral das Fases

| Fase | Nome             | Módulos                                         | Depende de |
| ---- | ---------------- | ----------------------------------------------- | ---------- |
| 1    | Core             | errors, ast_nodes, lexer, parser, compiler, css | —          |
| 2    | Component System | config, registry, props, slots                  | Fase 1     |
| 3    | Runtime          | engine, integration, log, sse                   | Fases 1-2  |
| 4    | CLI              | cli/* , assets                                  | Fases 1-3  |
| 5    | Frontend Tooling | npm integration, vendor build, tailwind         | Fase 4     |

---

## Fase 1 — Core

Objetivo: parsear um arquivo `.jinja` e compilar para Jinja2 + Alpine + HTMX.

### 1.1 `errors.py` — Hierarquia de Exceções

**Responsabilidade**: Exceções base com localização (arquivo, linha, coluna).

**Entregáveis**:

- `PJXError(Exception)` — base
- `ParseError(PJXError)` — erro de sintaxe no `.jinja`
- `LexError(ParseError)` — erro na tokenização do frontmatter
- `CompileError(PJXError)` — erro na compilação AST → output
- `PropValidationError(PJXError)` — validação de props
- `ImportResolutionError(PJXError)` — import não encontrado
- `ConfigError(PJXError)` — configuração inválida

Todas devem incluir `path: Path | None`, `line: int | None`,
`col: int | None` para mensagens de erro ricas.

**Testes**:

- Instanciação com e sem localização
- Formatação da mensagem com path:line:col
- Herança correta entre exceções

**Critério de done**: Todas as exceções documentadas, testadas e importáveis.

### 1.2 `ast_nodes.py` — Representação Intermediária

**Responsabilidade**: Dataclasses imutáveis que representam um componente
parseado.

**Entregáveis**:

```python
# Nó raiz
Component(path, extends, from_imports, imports, props, slots, stores,
          variables, states, computed, body, style)

# Declarações do frontmatter
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

# Nodes do body
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

Todos com `@dataclass(frozen=True, slots=True)`.
`Node` como type alias union de todos os node types.

**Testes**:

- Instanciação de cada dataclass
- Imutabilidade (frozen)
- Type union correta

**Critério de done**: Todas as dataclasses da spec representáveis, testadas.

### 1.3 `lexer.py` — Tokenizer

**Responsabilidade**: Tokenizar o conteúdo do frontmatter em tokens.

**Entregáveis**:

- `TokenKind(StrEnum)` — EXTENDS, IMPORT, FROM, AS, PROPS, SLOT, STORE,
  LET, CONST, STATE, COMPUTED, IDENT, STRING, NUMBER, LBRACE, RBRACE,
  LBRACKET, RBRACKET, LPAREN, RPAREN, COMMA, COLON, EQUALS, PIPE, STAR,
  DOT, ELLIPSIS, NEWLINE, EOF
- `Token(kind, value, line, col)` — frozen dataclass
- `tokenize(source: str) -> list[Token]` — hand-written single-pass lexer

**Design**:

- Cada linha começa com keyword → lexer identifica por prefixo
- Strings: `"..."` e `'...'`
- Números: inteiros e floats
- Identifiers: `[a-zA-Z_][a-zA-Z0-9_]*`
- Comentários: `#` até fim da linha (ignorados)
- Erros: `LexError` com posição

**Testes**:

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

**Critério de done**: Tokeniza todos os exemplos do IDEA.md sem erro.

### 1.4 `parser.py` — Parser Completo

**Responsabilidade**: Parsear um arquivo `.jinja` completo em `Component` AST.

**Entregáveis**:

- `parse(source: str, path: Path) -> Component`
- `parse_file(path: Path) -> Component`
- `_extract_blocks(source) -> tuple[str | None, str | None, str]`
  — separa script, style, body
- `_parse_script(tokens) -> ScriptDeclarations`
  — recursive descent LL(1)
- `_parse_body(html, known_components) -> list[Node]`
  — subclass de `html.parser.HTMLParser`

**Design do body parser**:

- Tags uppercase (`<Show>`, `<For>`, `<Switch>`, etc.) → control flow nodes
- Tags PascalCase registradas → ComponentNode
- Tags lowercase → ElementNode
- `<Slot:name>` → SlotRenderNode
- `<slot:name>` → SlotPassNode
- `{{ expr }}` → ExprNode
- Texto livre → TextNode
- Atributos preservados como `dict[str, str | bool]` para o compiler

**Testes**:

- `test_parse_empty_component` (só body, sem frontmatter)
- `test_parse_full_component` (frontmatter + style + body)
- `test_extract_blocks_*` (com/sem frontmatter, com/sem style)
- `test_parse_extends`
- `test_parse_from_import`
- `test_parse_script_imports_*` (default, named, wildcard, alias)
- `test_parse_script_props_pydantic` (Literal, Annotated, EmailStr)
- `test_parse_script_slots_*` (com/sem fallback)
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

**Critério de done**: Parseia o exemplo completo do Dashboard (IDEA.md §16)
produzindo AST correto.

### 1.5 `css.py` — Scoped CSS

**Responsabilidade**: Extrair e escopar CSS de componentes.

**Entregáveis**:

- `generate_scope_hash(path: Path) -> str` — sha256[:7]
- `scope_css(css_source: str, scope_hash: str) -> str`
  — regex-based selector prefixing

**Regras de rewrite**:

```text
.alert { ... }           → [data-pjx-a1b2c3] .alert { ... }
#main { ... }            → [data-pjx-a1b2c3] #main { ... }
div.card { ... }         → [data-pjx-a1b2c3] div.card { ... }
.a .b { ... }            → [data-pjx-a1b2c3] .a .b { ... }
.a, .b { ... }           → [data-pjx-a1b2c3] .a, [data-pjx-a1b2c3] .b { ... }
@media (...) { .a {} }   → @media (...) { [data-pjx-a1b2c3] .a {} }
```

**Testes**:

- `test_scope_hash_deterministic`
- `test_scope_hash_unique_per_path`
- `test_scope_css_class_selector`
- `test_scope_css_id_selector`
- `test_scope_css_compound_selector`
- `test_scope_css_multiple_selectors` (comma)
- `test_scope_css_media_query`
- `test_scope_css_nested_rules`
- `test_scope_css_preserves_properties`

**Critério de done**: Todos os padrões CSS comuns escopados corretamente.

### 1.6 `compiler.py` — AST para Output

**Responsabilidade**: Compilar `Component` AST em Jinja2 + Alpine + HTMX.

**Entregáveis**:

- `Compiler(registry: ComponentRegistry)`
- `Compiler.compile(component: Component) -> CompiledComponent`
- `_compile_preamble(component) -> str` — `{% set %}` para let/const/computed
- `_compile_node(node: Node) -> str` — recursive walker
- `_compile_attrs(attrs: dict) -> str` — transforma DSL attrs

**Regras de atributos** (consolidadas da SPEC.md §§9-13):

| Prefixo/nome        | Transformação              |
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

**Testes**:

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

**Critério de done**: Compila o Dashboard do IDEA.md para Jinja2 válido.

---

## Fase 2 — Component System

Objetivo: resolver imports, validar props, resolver slots, carregar config.

### 2.1 `config.py` — Configuração

**Responsabilidade**: Carregar config de `pjx.toml` e env vars.

**Entregáveis**:

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

**Testes**: Load from TOML, env override, defaults.

**Critério de done**: Config carrega de pjx.toml e env vars corretamente.

### 2.2 `registry.py` — Component Registry

**Responsabilidade**: Resolver imports, cachear componentes, detectar
circular imports.

**Entregáveis**:

- `ComponentRegistry(root_dirs: list[Path])`
- `resolve(import_decl, from_path) -> list[ResolvedComponent]`
- `get(name) -> Component | None`
- `register(name, component)`
- `compile_all(entry: Path) -> dict[str, CompiledComponent]`

**Design**:

- Cache: `dict[str, Component]` (por nome) + `dict[Path, Component]` (por path)
- Resolução: relativa ao arquivo importador
- Circular: set de paths "em resolução" → `ImportResolutionError`
- Invalidação (dev): check mtime antes de servir do cache

**Testes**:

- `test_resolve_relative_import`
- `test_resolve_named_import_from_dir`
- `test_resolve_wildcard_import`
- `test_resolve_alias`
- `test_circular_import_detection`
- `test_cache_hit`
- `test_cache_invalidation_mtime`

**Critério de done**: Resolve todos os padrões de import do IDEA.md §2.

### 2.3 `props.py` — Props para Pydantic

**Responsabilidade**: Gerar `BaseModel` dinâmico a partir de `PropsDecl`.

**Entregáveis**:

- `generate_props_model(decl: PropsDecl) -> type[BaseModel]`
- `validate_props(model, data) -> BaseModel`

**Mapping** (DSL usa tipos Pydantic nativos):

| DSL                            | BaseModel gerado                                 |
| ------------------------------ | ------------------------------------------------ |
| `name: str`                    | `name: str`                                      |
| `age: int = 0`                 | `age: int = 0`                                   |
| `role: Literal["a","b"] = "a"` | `role: Literal["a","b"] = "a"`                   |
| `email: EmailStr`              | `email: EmailStr`                                |
| `bio: str \| None = None`      | `bio: str \| None = None`                        |
| `tags: list[str] = []`         | `tags: list[str] = Field(default_factory=list)`  |
| `score: Annotated[int, Gt(0)]` | `score: Annotated[int, Gt(0)]`                   |
| `url: HttpUrl \| None = None`  | `url: HttpUrl \| None = None`                    |

**Testes**:

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

**Critério de done**: Gera models para todos os exemplos de props do IDEA.md §3.

### 2.4 `slots.py` — Resolução de Slots

**Responsabilidade**: Resolver slots declarados com conteúdo passado pelo pai.

**Entregáveis**:

- `resolve_slots(declarations, passed_slots, children) -> dict[str, str]`

**Testes**:

- `test_resolve_slot_with_content`
- `test_resolve_slot_fallback`
- `test_resolve_slot_default_children`
- `test_resolve_slot_empty`

**Critério de done**: Resolve todos os padrões de slot do IDEA.md §5.

---

## Fase 3 — Runtime

Objetivo: renderizar templates e integrar com FastAPI.

### 3.1 `log.py` — Logging

**Responsabilidade**: Configurar logging com Rich.

**Entregáveis**:

- `setup_logging(debug: bool) -> None`
- `logger = logging.getLogger("pjx")`

**Critério de done**: Logs formatados com Rich, níveis configuráveis.

### 3.2 `engine.py` — Template Engine

**Responsabilidade**: Interface unificada sobre Jinja2 e MiniJinja.

**Entregáveis**:

- `EngineProtocol` (Protocol)
- `Jinja2Engine` — wrapper sobre `jinja2.Environment`
- `MiniJinjaEngine` — wrapper sobre `minijinja.Environment`
- `create_engine(config) -> EngineProtocol`

**Design**:

- `auto` → Jinja2 (padrão atual)
- Ambos implementam: `render`, `render_string`, `add_template`, `add_global`
- Templates compilados são registrados via `add_template`

**Testes**:

- `test_jinja2_engine_render`
- `test_jinja2_engine_render_string`
- `test_minijinja_engine_render`
- `test_create_engine_auto_returns_jinja2`
- `test_create_engine_explicit`

**Critério de done**: Ambos engines renderizam templates compilados pelo
compiler.

### 3.3 `integration.py` — FastAPI

**Responsabilidade**: Decorators `@pjx.page` e `@pjx.component`, mounting
de static files.

**Entregáveis**:

- `PJX(app, template_dirs?, config?)`
- `PJX.page(path, template, **kwargs) -> decorator`
- `PJX.component(template) -> decorator`
- `PJX.render(request, template, context) -> HTMLResponse`

**Fluxo**:

1. Decorator registra rota no FastAPI
2. Handler → context dict
3. Registry resolve template (com cache)
4. Props validados via Pydantic
5. Engine renderiza
6. Retorna HTMLResponse

**Testes**:

- `test_page_decorator_registers_route`
- `test_page_decorator_renders_template`
- `test_component_decorator_renders_partial`
- `test_props_validation_error_response`
- `test_render_manual`
- Testes de integração com `httpx.AsyncClient` + FastAPI TestClient

**Critério de done**: Uma página e um componente parcial renderizam
corretamente via FastAPI.

### 3.4 `sse.py` — Server-Sent Events

**Responsabilidade**: Helpers para endpoints SSE.

**Entregáveis**:

- `EventStream` — async context com `send(event, data)` e
  `send_html(event, template, context)`
- `PJX.sse(path) -> decorator`

**Testes**:

- `test_sse_stream_sends_event`
- `test_sse_stream_renders_template`

**Critério de done**: SSE endpoint funciona com `live="/url"` no template.

---

## Fase 4 — CLI

Objetivo: CLI completa para desenvolvimento.

### 4.1 `cli/__init__.py` — App Typer

**Entregáveis**:

- `app = typer.Typer(name="pjx")`
- Entry point no pyproject.toml: `[project.scripts] pjx = "pjx.cli:app"`

### 4.2 `cli/init.py` — `pjx init`

Scaffolda estrutura de diretórios, cria `pjx.toml`, `package.json` com
Alpine + HTMX.

### 4.3 `cli/dev.py` — `pjx dev` / `pjx run`

- `dev`: `uvicorn app:app --reload --host --port` (do config)
- `run`: `uvicorn app:app --host --port --workers N`

### 4.4 `cli/build.py` — `pjx build` / `check` / `format`

- `build`: Compila todos os `.jinja` + bundle CSS + `npm run build`
- `check`: Parseia todos os `.jinja`, reporta erros com localização
- `format`: Re-emite `.jinja` com formatting consistente

### 4.5 `cli/packages.py` — `pjx add` / `remove`

- `add <pkg>`: `npm install <pkg>` + copia dist para `static/vendor/`
- `remove <pkg>`: `npm uninstall <pkg>` + limpa vendor

### 4.6 `assets.py` — Static Files

**Responsabilidade**: Descobrir e gerenciar arquivos estáticos, copiar
vendor builds.

**Testes para toda a CLI**:

- `test_cli_init_creates_dirs`
- `test_cli_check_valid_files`
- `test_cli_check_reports_errors`
- `test_cli_add_runs_npm`
- `test_cli_build_compiles_all`

**Critério de done**: Todos os comandos executam sem erro e produzem output
correto.

---

## Fase 5 — Frontend Tooling

Objetivo: integração com npm, build pipeline, Tailwind.

### 5.1 npm Integration

- `pjx init` cria `package.json` com Alpine.js + HTMX como deps
- `pjx add <pkg>` → `npm install <pkg>`
- `pjx remove <pkg>` → `npm uninstall <pkg>`
- `pjx build` → `npm run build` (configurado com script no package.json)

### 5.2 Vendor Build

- ESLint para lint do JS customizado
- Script de build copia dist files para `static/vendor/`:
  - `node_modules/alpinejs/dist/cdn.min.js` → `static/vendor/alpine.min.js`
  - `node_modules/htmx.org/dist/htmx.min.js` → `static/vendor/htmx.min.js`

### 5.3 Tailwind CSS (opcional)

- Se `tailwind = true` no config:
  - `pjx init` adiciona `tailwindcss` ao package.json
  - `pjx build` roda `npx tailwindcss -i input.css -o static/css/tailwind.css`
  - Template base inclui `<link>` para tailwind.css

**Critério de done**: `pjx init && pjx add alpinejs && pjx build` produz
vendor/ funcional.

---

## Estratégia de Testes

### Estrutura

```text
tests/
├── conftest.py                # Fixtures globais
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
│   └── test_config.py
├── integration/
│   ├── test_integration.py    # FastAPI + PJX decorators
│   ├── test_sse.py
│   └── test_cli.py
└── e2e/
    └── test_full_render.py    # Parse → compile → render → assert HTML
```

### Fixtures (conftest.py)

- `sample_component_source` — string `.jinja` com frontmatter completo
- `parsed_component` — `Component` AST pronto
- `compiled_component` — `CompiledComponent` pronto
- `pjx_app` — FastAPI app com PJX montado
- `test_client` — `httpx.AsyncClient` com a app
- `tmp_templates` — diretório temporário com `.jinja` de exemplo

### Convenções

- Nomes: `test_<unit>_<scenario>_<expected>`
- Parametrize para cobrir variantes (ex: todos os tipos de bind:*)
- Markers: `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.e2e`
- Coverage mínima: 90% para core (lexer, parser, compiler)
- Property-based (Hypothesis): gerar frontmatter válido/inválido random
  para fuzz do lexer e parser

---

## Componentes de Exemplo

Criar em `examples/` para validação e documentação:

| Arquivo                    | Cobre                                      |
| -------------------------- | ------------------------------------------ |
| `Counter.jinja`            | state, on:click, bind:text, reactive       |
| `TodoItem.jinja`           | props, slots, Show, For, scoped CSS        |
| `UserCard.jinja`           | Pydantic types (EmailStr, Literal)         |
| `Dashboard.jinja`          | Exemplo completo do IDEA.md §17            |
| `TreeNode.jinja`           | Componente recursivo                       |
| `layouts/Base.jinja`       | Layout base com slots head/content/footer  |
| `pages/Home.jinja`         | extends, slot:head, prop spreading         |
| `errors/404.jinja`         | Página de erro com extends                 |

Estes exemplos servem como test fixtures e documentação de uso real.

---

## Reestruturação de Diretório

A estrutura atual `src/main.py` precisa migrar para `src/pjx/`:

```text
# Antes
src/
├── __init__.py
└── main.py

# Depois
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
    ├── sse.py
    ├── assets.py
    ├── log.py
    └── cli/
        ├── __init__.py
        ├── init.py
        ├── dev.py
        ├── build.py
        └── packages.py
```

Atualizar `pyproject.toml` com `[project.scripts]` para o CLI entry point.

---

## Ordem de Implementação (dependências)

```text
Fase 1 (paralelo onde possível):
  errors.py ──────┐
  ast_nodes.py ───┤
  css.py ─────────┼──→ lexer.py ──→ parser.py ──→ compiler.py
                  │
Fase 2:           │
  config.py ──────┤
  props.py ───────┤
  slots.py ───────┼──→ registry.py
                  │
Fase 3:           │
  log.py ─────────┤
  engine.py ──────┼──→ integration.py ──→ sse.py
                  │
Fase 4:           │
  assets.py ──────┼──→ cli/*
                  │
Fase 5:           └──→ frontend tooling
```

---

## Validação End-to-End

Ao final de cada fase, validar com:

```bash
rtk uv run ruff format --check .
rtk uv run ruff check .
rtk uv run ty check
rtk uv run pytest -v
rtk uv run rumdl check .
```

### Teste E2E final (após Fase 3)

1. Criar um componente `TodoItem.jinja` com props, state, slots
2. Criar uma página `Home.jinja` que usa `TodoItem`
3. Montar FastAPI app com `PJX`
4. Verificar que GET `/` retorna HTML válido com:
   - `{% if %}` / `{% for %}` corretos
   - `x-data` com states
   - `hx-get` / `hx-post` com URLs
   - CSS escopado com `data-pjx-*`
   - Slots resolvidos
