# AGENTS

Este arquivo existe para orientar outros agentes e colaboradores que entrarem no
repositorio.

## O que e este projeto

PJX e um miniframework server-first para Python com:

* FastAPI como app host real
* linguagem de componentes compilada para Jinja2 com sintaxe `@directive`
* `Pjx` e `PjxRouter` como API publica
* `pjx.init_app(app)` para registrar no FastAPI do usuario
* `render()` como Depends, `Page`/`Template` como return types
* HTMX e Alpine como enhancement
* tooling proprio com `pjx check` e `pjx format`

## Estado atual

Hoje o projeto ja entrega:

* parser estrutural para arquivos `.pjx` com sintaxe `@directive`
* compiler para built-ins e chamadas de componente
* runtime com cache por `mtime`
* template mounts com prefixo, como `@admin/...`
* assets do framework em `/_pjx`
* `context_processor` para injecao de contexto
* `PropValidationError` com exceptions customizadas
* app de exemplo funcional em `exemples/`
* CLI validando templates e formatando estrutura

Ainda nao considere o projeto "fechado" nestes pontos:

* runtime nativo de `signal` e `action`
* renderer backend alternativo a Jinja2
* parser/token stream completo do markup
* partial extraction mais forte que busca por `id`
* scoped slot `let:` bindings

## Arquitetura resumida

```text
FastAPI app
|
+-- JSON/API routes
+-- PJX routes (pages, actions) via pjx.init_app(app)
+-- /static (app static)
`-- /_pjx (framework static)
```

Fluxo principal:

```text
.pjx
|
+-- parser.py -> parse() -> PjxFile
+-- compiler.py -> compile_pjx() -> str
`-- runtime.py -> Jinja Environment.render(...)
```

## Arquivos mais importantes

* `pjx/fastapi.py`: Pjx, PjxRouter, init_app, render, Page, Template
* `pjx/catalog.py`: template mounts, aliases, directives, facade de render
* `pjx/parser.py`: parser estrutural do arquivo `.pjx`
* `pjx/compiler.py`: transforma AST em Jinja compilado
* `pjx/runtime.py`: cache, props, slots, assets, partial render
* `pjx/ast.py`: PjxFile, ComponentDef, PropDef, ForNode, etc.
* `pjx/tooling.py`: `check`, `format` e carga de projeto
* `pjx/cli.py`: CLI com Typer + Rich
* `README.md`: guia de uso
* `docs/`: arquitetura, linguagem, CLI e decisoes
* `TODO.md`: roadmap do framework

## Estrutura do exemplo

```text
exemples/
|-- main.py
|-- data.py
|-- state.py
|-- api/routers/
|-- static/css/
`-- templates/
    |-- layouts/
    `-- pages/
```

## Convencoes do projeto

### API publica

Prefira:

* `Pjx(templates_dir=..., browser=..., css=...)`
* `PjxRouter()` para pages e actions
* `pjx.init_app(app)` para registrar no FastAPI
* `render(template, layout=...)` como Depends
* `@pjx.context_processor` para injecao de contexto

Evite:

* criar wrappers paralelos do FastAPI
* reintroduzir `APIRouter` para pages HTML do PJX
* reintroduzir `Catalog` manual no app host
* usar `PJX` (alias backward compat) em codigo novo

### Templates

Prefira:

* sintaxe `@directive`: `@from`, `@import`, `@props`, `@component`
* extensao `.pjx`
* imports explicitos no topo
* `templates/` como raiz
* mounts extras com `@prefix/...`
* `prop="{{ expr }}"` como forma principal de expressao
* named slots via `<:name>...</:name>`

Evite:

* sintaxe duplicada para a mesma feature
* comportamento magico escondido em comments
* usar `{% %}` para diretivas PJX (reservado para Jinja nativo)

### Frontend

Prefira:

* HTMX para round-trips incrementais
* Alpine para estado local pequeno
* `css="pjx"` para usar o CSS built-in do framework
* `@click.htmx`, `@target`, `@swap` para HTMX

Evite:

* JS cliente pesado sem necessidade
* reatividade nativa improvisada antes do core estar fechado

## Comandos de validacao

Sempre que mexer em codigo do projeto, rode:

```bash
uv run ruff format .
uv run ruff check .
uv run ty check
uv run rumdl check README.md TODO.md docs exemples/README.md --disable MD013
uv run pytest -q
```

Quando mexer em templates ou na API do framework, rode tambem:

```bash
uv run pjx check exemples.main:pjx
uv run pjx format exemples.main:pjx --check
```

## Regras para mexer no core

1. Nao aumentar a complexidade de `fastapi.py` sem necessidade.
2. Nao espalhar resolucao de templates fora do `Catalog`.
3. Nao colocar regra de linguagem dentro do app de exemplo.
4. Se uma feature nova exigir parser novo, atualize parser, compiler, tooling e docs juntos.
5. Se mudar a API publica, atualize README, docs e exemplo na mesma rodada.

## Fonte de verdade

Se houver duvida sobre o projeto, consulte nesta ordem:

1. `README.md`
2. `docs/architecture.md`
3. `docs/template-language.md`
4. `docs/decisions.md`
5. `TODO.md`
