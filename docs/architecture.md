# Architecture

## Objetivo

O PJX quer ser um miniframework server-first para FastAPI com:

* linguagem de componentes com sintaxe `@directive`
* compile step proprio antes do Jinja
* runtime leve no servidor
* HTMX e Alpine como enhancement, nao como base obrigatoria
* tooling de validacao e formatacao

## Camadas

```text
User app (FastAPI)
|
+-- JSON/API routes
+-- PJX routes (pages, actions)
+-- /static (app static)
`-- /_pjx (framework static)

PJX
|
+-- Pjx + PjxRouter
+-- Catalog
+-- Parser
+-- Compiler
+-- Runtime
`-- CLI tooling
```

## Modulos Principais

```text
pjx/
|-- fastapi.py    -> Pjx, PjxRouter, init_app, render, Page, Template
|-- catalog.py    -> roots, mounts, aliases, directives, render facade
|-- parser.py     -> parser estrutural do arquivo .pjx
|-- ast.py        -> AST: PjxFile, ComponentDef, PropDef, ForNode, etc.
|-- compiler.py   -> AST -> Jinja source compilado
|-- runtime.py    -> cache, render, props, slots, assets, partials
|-- assets.py     -> render de CSS/JS e view de assets
|-- models.py     -> modelos compilados, attrs, render state
|-- tooling.py    -> check/format/load_project
`-- cli.py        -> Typer + Rich
```

## Fluxo de Boot

```text
main.py
|
+-- cria Pjx(templates_dir=..., browser=..., css=...)
|   |
|   +-- resolve templates_dir e components_dir
|   +-- cria Catalog
|   +-- registra framework assets
|   `-- coleta PjxRouters via include_router
|
+-- cria FastAPI()
|
+-- pjx.init_app(app)
    |
    +-- monta StaticFiles em /static
    +-- monta StaticFiles em /_pjx
    `-- registra pages/actions como api_route no app
```

## Fluxo de Render

```text
HTTP request
|
+-- FastAPI route registrada pelo PJX
|   |
|   +-- chama endpoint Python do usuario
|   +-- converte retorno em RenderResult
|   `-- chama catalog.render_string(...)
|
`-- Catalog
    |
    +-- resolve template path
    +-- prepara RenderState
    `-- delega para Runtime.render_root(...)
        |
        +-- get_component_instance()
        |   |
        |   +-- cache por source path + mtime
        |   +-- compile_pjx(parse(...))
        |   `-- Environment.from_string(...)
        |
        +-- coleta assets transitivos
        +-- resolve props/defaults/types
        +-- renderiza slots/content/attrs
        +-- executa Jinja render
        `-- extrai fragmento por id quando partial=True
```

## Pipeline de Compilacao

```text
.pjx source
|
+-- parser.py -> parse(source) -> PjxFile
|   |
|   +-- imports (@from, @import)
|   +-- @props, @slot, @state, @bind, @let
|   +-- @component blocks (multi-component)
|   `-- body markup (HTML, component calls, control flow)
|
+-- compiler.py -> compile_pjx(ast) -> str
|   |
|   +-- compila imports
|   +-- compila props/slots/state
|   +-- transforma <Show>, <For>, <Switch>
|   +-- transforma component calls
|   `-- gera jinja_source final
|
`-- runtime.py
    |
    +-- Environment.from_string(jinja_source)
    `-- template.render(...)
```

## Parser e Compiler

O parser aceita a sintaxe `@directive`:

```text
source file
|
+-- top-level:
|   +-- @from module import Name1, Name2
|   +-- @import "path/to/Layout.pjx"
|   +-- @bind from module import ClassName
|   +-- @props { name: type = default, ... }
|   +-- @slot name?
|   +-- @state { field: value, ... }
|   +-- @let name = expr
|   `-- body markup
|
+-- multi-component mode:
    +-- @component Name {
    |     @props { ... }
    |     @slot name?
    |     body markup
    |   }
    `-- @component Name2 { ... }
```

O compiler trata o markup customizado:

* `<Show when="...">` / `<Else>`
* `<For each="..." as="item">` / `<Empty>`
* `<Switch value="...">` / `<Case>` / `<Default>`
* componentes TitleCase importados explicitamente
* named slots via `<:name>...</:name>`
* elementos HTML normais com attrs e diretivas

## Catalog

`Catalog` e o centro do runtime.

Responsabilidades:

* manter template mounts
* resolver aliases como `@/...` e `@admin/...`
* registrar assets base
* registrar diretivas
* expor `render`, `render_string`, `list_components`
* aplicar diretivas core e customizadas nos attrs

## Assets

O framework tem dois tipos de assets:

* assets do app, normalmente em `/static/...`
* assets do proprio PJX, servidos em `/_pjx/...`

## Partials e HTMX

Quando uma route ou action declara `target=...` e a request e HTMX, o runtime
faz render completo e depois extrai o fragmento pelo `id` alvo.

```text
HTMX POST
|
+-- route target="counter-value"
|
+-- render_root(..., partial=True, target="counter-value")
|
`-- extract_fragment_by_id(html, "counter-value")
```

## CLI

O CLI usa `tooling.py` como nucleo puro e `cli.py` apenas como interface.

```text
pjx cli
|
+-- Typer parsing
+-- Rich output
`-- tooling.py
    |
    +-- load_project
    +-- check_project
    `-- format_project
```

## Estado Atual

Pontos fortes:

* FastAPI como base real da API publica
* `Pjx.init_app(app)` registra diretamente no app do usuario
* `render()` como Depends, `Page`/`Template` como return types
* `@pjx.context_processor` para injecao de contexto
* sintaxe `@directive` canonica com extensao `.pjx`
* parser estrutural do arquivo
* runtime simples e previsivel
* CLI util e automatizavel

Pontos ainda abertos:

* markup parser ainda merece evolucao para lexer/token stream
* `signal` e `action` sao mais semantica de compilacao do que runtime nativo
* renderer backend ainda esta acoplado ao Jinja2
* extracao de fragmento por `id` ainda pode evoluir
