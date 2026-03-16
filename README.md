# PJX

PJX e um miniframework server-first para Python que usa uma linguagem de
componentes compilada para Jinja2, integra com FastAPI e trabalha bem com HTMX
e Alpine.

Hoje o projeto ja entrega:

* componentes `.pjx` com imports explicitos e sintaxe `@directive`
* `Pjx` e `PjxRouter` para integrar UI ao FastAPI
* `pjx.init_app(app)` para registrar rotas e assets no app existente
* `render()` como Depends, `Page` e `Template` como return types
* template roots com prefixo, como `@admin/...`
* assets automaticos do framework
* `pjx check` e `pjx format`
* app de exemplo com pages, actions e primitives de UI

Se voce quer entender a arquitetura interna, veja:

* [docs/README.md](docs/README.md)
* [docs/architecture.md](docs/architecture.md)
* [docs/template-language.md](docs/template-language.md)
* [docs/cli.md](docs/cli.md)
* [docs/decisions.md](docs/decisions.md)

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
from fastapi import FastAPI
from pjx import Pjx, PjxRouter

ui = PjxRouter()

pjx = Pjx(
    templates_dir="templates",
    browser=["htmx", "alpine"],
    css="pjx",
)
pjx.include_router(ui)

@ui.page("/", template="pages/Home.pjx")
def home() -> dict[str, object]:
    return {"title": "Home"}

app = FastAPI(title="My App")
pjx.init_app(app)
```

## Mental Model

O app principal continua sendo FastAPI. O PJX registra rotas e assets
diretamente no app do usuario via `init_app`.

```text
FastAPI app
|
+-- JSON/API routes
+-- PJX routes (pages, actions)
+-- /static (app static)
`-- /_pjx (framework static)
```

## Estrutura Recomendada

```text
my_app/
|-- main.py
|-- static/
|   `-- css/
`-- templates/
    |-- components/
    |-- layouts/
    `-- pages/
```

Exemplo real do repositorio:

* [exemples/main.py](exemples/main.py)
* [exemples/templates](exemples/templates)
* [exemples/api/routers/pages.py](exemples/api/routers/pages.py)
* [exemples/api/routers/actions.py](exemples/api/routers/actions.py)

## Templates

O root padrao e `templates/`.

```python
pjx = Pjx(templates_dir="templates")
```

A extensao canonica e `.pjx`. Sintaxe de diretivas usa `@`:

```text
@from pjx.ui import Button, Badge
@import "layouts/Layout.pjx"

@props { title: str = "Home" }

<Layout title="{{ title }}">
  <Button label="Click me" />
</Layout>
```

## Routers HTML

`PjxRouter` segue a ideia de `APIRouter`: ele coleta pages e actions
antes de serem incluidos no `Pjx`.

```python
ui = PjxRouter(prefix="/admin")

@ui.page("/dashboard", template="pages/admin_dashboard.pjx")
def dashboard() -> dict[str, object]:
    return {"title": "Admin"}

@ui.action(
    "/users/search",
    template="pages/admin_dashboard.pjx",
    target="users-table",
)
def search_users() -> dict[str, object]:
    return {"query": "ana"}
```

E entao:

```python
pjx = Pjx(templates_dir="templates")
pjx.include_router(ui)
```

## render() como Depends

`render()` e uma factory de `Depends` que retorna `Page` ou `Template`:

```python
from pjx import render

@app.get("/")
async def home(page: Page = render("pages/home.pjx", layout="layouts/Layout.pjx")):
    return await page(title="Home")
```

## Context Processors

```python
@pjx.context_processor
async def add_user(request):
    return {"user": get_current_user(request)}
```

## HTMX e Alpine

Ative browser integrations no `Pjx`:

```python
pjx = Pjx(
    templates_dir="templates",
    browser=["htmx", "alpine"],
)
```

Os assets do framework sao servidos automaticamente em `/_pjx/js/...`.

## CSS do Framework

Use `css="pjx"` para incluir o CSS built-in do framework:

```python
pjx = Pjx(templates_dir="templates", css="pjx")
```

## CLI

O projeto expoe um CLI com `Typer + Rich`:

```bash
uv run pjx check exemples.main:pjx
uv run pjx check exemples.main:pjx --format json
uv run pjx check . --strict

uv run pjx format exemples.main:pjx --check
uv run pjx format path/to/Button.pjx
```

`pjx check` valida:

* parse estrutural
* compilacao
* imports ausentes
* alias de import duplicado
* ciclos de import
* templates sombreados
* templates referenciados por pages e actions

A saida textual usa codigos numericos estaveis no formato `[NNN] code`.

## Extras

FastAPI faz parte do core do pacote. Hoje os extras publicos continuam:

```bash
uv add "pjx[minijinja]"
```

`htmx` e `alpine` nao sao extras Python; sao integrations servidas pelo
proprio PJX.

## Estado Atual

O projeto esta numa fase funcional, mas ainda em consolidacao de linguagem,
runtime e tooling. O roadmap de evolucao esta em [TODO.md](TODO.md).
