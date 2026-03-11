# Architecture

## Objetivo

O PJX quer ser um miniframework server-first para FastAPI com:

* linguagem de componentes simples
* compile step proprio antes do Jinja
* runtime leve no servidor
* HTMX e Alpine como enhancement, nao como base obrigatoria
* tooling de validacao e formatacao

## Camadas

```text
User app
|
+-- FastAPI root app
|   |
|   +-- JSON/API routes
|   `-- mount("/", pjx.app(...))
|
`-- PJX
    |
    +-- PJXRouter collection
    +-- Catalog
    +-- Parser
    +-- Compiler
    +-- Runtime
    `-- CLI tooling
```

## Modulos Principais

```text
pjx/
|-- fastapi.py    -> API publica de integracao com FastAPI
|-- catalog.py    -> roots, mounts, aliases, directives, render facade
|-- parser.py     -> parser estrutural do arquivo .jinja
|-- ast.py        -> AST do preambulo e do componente
|-- compiler.py   -> AST/markup -> Jinja source compilado
|-- markup.py     -> parser de markup e arvores auxiliares
|-- runtime.py    -> cache, render, props, slots, assets, partials
|-- assets.py     -> render de CSS/JS e view de assets
|-- models.py     -> modelos compilados, attrs, slots, render state
|-- tooling.py    -> check/format/load_project
`-- cli.py        -> Typer + Rich
```

## Fluxo de Boot

```text
main.py
|
+-- cria PJX(root=..., templates=..., routers=...)
|   |
|   +-- resolve template mounts
|   +-- cria Catalog
|   +-- registra framework assets
|   `-- inclui PJXRouters
|
+-- cria FastAPI()
|
+-- include_router(api_router)
|
`-- mount("/", pjx.app(...))
    |
    +-- mount /static
    +-- mount /_pjx
    `-- registra pages/actions HTML pendentes
```

## Fluxo de Render

```text
HTTP request
|
+-- FastAPI route criada pelo PJX
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
        |   +-- compile_component_file(...)
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
.jinja source
|
+-- parser.py
|   |
|   +-- imports
|   +-- props aliases
|   +-- component signature
|   `-- component directives
|
+-- compiler.py
|   |
|   +-- compila directives
|   +-- compila imports/assets
|   +-- transforma markup customizado
|   `-- gera jinja_source final
|
`-- runtime.py
    |
    +-- Environment.from_string(jinja_source)
    `-- template.render(...)
```

## Parser e Compiler

Hoje o parser estrutural ja saiu do modo puramente regex-first para a estrutura
do arquivo:

```text
source file
|
+-- top-level:
|   +-- {% import ... %}
|   +-- {% set DemoProps = {...} %}
|   `-- {% component Name %} ... {% endcomponent %}
|
`-- component preamble:
    +-- {% props ... %}
    +-- {% inject ... %}
    +-- {% provide ... %}
    +-- {% computed ... %} ... {% endcomputed %}
    +-- {% slot ... %}{% endslot %}
    +-- {% signal ... %}
    `-- {% action ... %} ... {% endaction %}
```

O compiler trata o markup customizado:

* `<If>`
* `<For>`
* `<Switch>`
* componentes TitleCase importados explicitamente
* elementos HTML normais com attrs e diretivas

## Catalog

`Catalog` e o centro do runtime.

Responsabilidades:

* manter template mounts
* resolver aliases como `@/...` e `@admin/...`
* registrar assets base
* registrar diretivas
* expor `render`, `render_string`, `list_components`, `get_signature`
* aplicar diretivas core e customizadas nos attrs

Diagrama:

```text
Catalog
|
+-- template_mounts
+-- aliases
+-- directives
+-- base_assets
`-- runtime
```

## Template Mounts

O PJX trabalha com um mount principal e mounts extras opcionais.

```text
templates=[
  "templates",
  {"prefix": "admin", "path": "admin_templates"},
  {"prefix": "marketing", "path": "marketing_templates"},
]
```

Resolucao:

```text
pages/Home.jinja                -> templates/pages/Home.jinja
@admin/pages/Home.jinja         -> admin_templates/pages/Home.jinja
@marketing/pages/Home.jinja     -> marketing_templates/pages/Home.jinja
```

## Assets

O framework tem dois tipos de assets:

* assets do app, normalmente em `/static/...`
* assets do proprio PJX, servidos em `/_pjx/...`

Fluxo:

```text
component imports css/js
|
`-- compiler extrai AssetImport
    |
    `-- runtime coleta transitivamente
        |
        `-- assets.render() ou fallback automatico
```

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

Isso mantem um caminho unico de render e simplifica o contrato de pages/actions.

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
* mounts de templates com prefixo
* parser estrutural do arquivo
* runtime simples e previsivel
* CLI util e automatizavel

Pontos ainda abertos:

* markup parser ainda merece evolucao para lexer/token stream
* `signal` e `action` no template ainda sao mais semantica de compilacao do que runtime nativo completo
* renderer backend ainda esta acoplado ao Jinja2
* extração de fragmento por `id` ainda pode evoluir
