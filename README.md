# PJX

PJX e um miniframework server-first para Python que usa uma linguagem de
componentes inspirada em Jinja, integra com FastAPI e trabalha bem com HTMX e
Alpine.

Hoje o projeto ja entrega:

* componentes `.jinja` com imports explicitos
* `PJX` e `PJXRouter` para integrar UI ao FastAPI
* template roots com prefixo, como `@admin/...`
* assets automáticos do framework
* `pjx check` e `pjx format`
* app de exemplo com pages, actions, directives e primitives de UI

Se voce quer entender a arquitetura interna, veja:

* [docs/README.md](/home/oornnery/proj/pjx/docs/README.md)
* [docs/architecture.md](/home/oornnery/proj/pjx/docs/architecture.md)
* [docs/template-language.md](/home/oornnery/proj/pjx/docs/template-language.md)
* [docs/cli.md](/home/oornnery/proj/pjx/docs/cli.md)
* [docs/decisions.md](/home/oornnery/proj/pjx/docs/decisions.md)

## Instalacao

```bash
uv sync
```

Para rodar o exemplo:

```bash
uv run uvicorn exemples.main:app --reload
```

O app fica em `http://127.0.0.1:8000`.

## Uso Rapido

```python
from pathlib import Path

from fastapi import FastAPI

from pjx import PJX, PJXRouter


ui = PJXRouter()

pjx = PJX(
    root=Path(__file__).parent,
    templates="templates",
    routers=[ui],
    browser=["htmx", "alpine"],
    css="tailwind",
)


@ui.page("/", template="pages/HomePage.jinja")
def home() -> dict[str, object]:
    return {"title": "Home"}


app = FastAPI(title="My App")
app.mount("/", pjx.app(title="My App UI"))
```

## Mental Model

O app principal continua sendo FastAPI. O PJX entra como um sub-app dedicado a
templates, assets do framework e rotas HTML.

```text
FastAPI app
|
+-- JSON/API routes
|
+-- mount("/", pjx.app(...))
    |
    +-- pages
    +-- actions
    +-- framework static (/_pjx)
    +-- app static (/static)
```

## Estrutura Recomendada

```text
my_app/
|-- main.py
|-- static/
|   |-- css/
|   `-- js/
`-- templates/
    |-- components/
    |-- layouts/
    `-- pages/
```

Exemplo real do repositorio:

* [exemples/main.py](/home/oornnery/proj/pjx/exemples/main.py)
* [exemples/templates](/home/oornnery/proj/pjx/exemples/templates)
* [exemples/api/routers/pages.py](/home/oornnery/proj/pjx/exemples/api/routers/pages.py)
* [exemples/api/routers/actions.py](/home/oornnery/proj/pjx/exemples/api/routers/actions.py)

## Templates

O root padrao e `templates/`.

```python
pjx = PJX(root=BASE_DIR, templates="templates")
```

Voce tambem pode registrar multiplos mounts:

```python
pjx = PJX(
    root=BASE_DIR,
    templates=[
        "templates",
        {"prefix": "admin", "path": "admin_templates"},
    ],
)
```

Nesse caso:

* o mount principal continua usando caminhos como `pages/dashboard.jinja`
* o mount prefixado usa `@admin/pages/dashboard.jinja`

Tambem funciona depois da criacao:

```python
pjx.add_templates(
    "templates/shared",
    {"prefix": "admin", "path": "admin_templates"},
)
```

## Routers HTML

`PJXRouter` segue a ideia de `APIRouter`: ele coleta pages, actions e
directives antes de serem incluidos no `PJX`.

```python
ui = PJXRouter(prefix="/admin")


@ui.page("/dashboard", template="pages/admin_dashboard.jinja")
def dashboard() -> dict[str, object]:
    return {"title": "Admin"}


@ui.action(
    "/users/search",
    template="pages/admin_dashboard.jinja",
    target="users-table",
)
def search_users() -> dict[str, object]:
    return {"query": "ana"}
```

E entao:

```python
pjx = PJX(root=BASE_DIR, templates="templates")
pjx.include_router(ui)
```

Ou diretamente no construtor:

```python
pjx = PJX(root=BASE_DIR, templates="templates", routers=[ui])
```

## Diretivas

Diretivas customizadas sao registradas no router:

```python
@ui.directive("tooltip")
def tooltip(element, value, ctx):
    element.attrs["data-tooltip"] = value
    return element
```

O `Catalog` aplica primeiro as diretivas core (`jx-bind:*`, `jx-class`,
`jx-show`, `jx-on:*`) e depois as customizadas.

## HTMX e Alpine

Ative browser integrations no `PJX`:

```python
pjx = PJX(
    root=BASE_DIR,
    templates="templates",
    browser=["htmx", "alpine"],
)
```

Os assets do framework sao servidos automaticamente em `/_pjx/js/...`.

Nos templates:

```jinja
{{ assets.render() }}
```

Ou:

```jinja
{{ assets.render_css() }}
{{ assets.render_js() }}
```

## Tailwind

Tailwind continua tratado como integracao de build.

```python
globs = pjx.tailwind_content_globs()
```

Isso expõe os globs base para `.pjx`, `.jinja` e `.py`, incluindo mounts extras
de templates.

## CLI

O projeto expõe um CLI com `Typer + Rich`:

```bash
uv run pjx check exemples.main:pjx
uv run pjx check exemples.main:pjx --format json
uv run pjx check . --strict

uv run pjx format exemples.main:pjx --check
uv run pjx format path/to/Button.jinja
```

`pjx check` valida o maximo que o framework consegue inferir hoje:

* parse estrutural
* compilacao
* imports ausentes
* assets locais ausentes
* alias de import duplicado
* ciclos de import
* templates sombreados
* templates referenciados por pages e actions

A saida textual usa codigos numericos estaveis no formato `[NNN] code`.

## Extras

FastAPI faz parte do core do pacote. Hoje os extras publicos continuam:

```bash
uv add "pjx[tailwind,minijinja]"
```

`htmx` e `alpine` nao sao extras Python; sao integrations servidas pelo proprio
PJX.

## Estado Atual

O projeto esta numa fase funcional, mas ainda em consolidacao de linguagem,
runtime e tooling. O roadmap de evolucao esta em
[TODO.md](/home/oornnery/proj/pjx/TODO.md).
