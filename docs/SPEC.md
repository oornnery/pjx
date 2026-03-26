# PJX — Especificação Técnica

> DSL Python que compila componentes `.jinja` reativos para
> Jinja2 + HTMX + Alpine.js + SSE.

## 1. Visão Geral

PJX é um compilador e runtime que transforma uma sintaxe de componentes
inspirada em JSX/SolidJS/Svelte em templates Jinja2 padrão, enriquecidos com
HTMX (interação server-side) e Alpine.js (reatividade client-side).

### Stack

| Camada             | Tecnologia                                      |
| ------------------ | ----------------------------------------------- |
| Linguagem          | Python 3.14+                                    |
| Template engine    | Jinja2 (padrão), MiniJinja (opt-in)             |
| Server framework   | FastAPI + Uvicorn                               |
| Reatividade client | Alpine.js                                       |
| Interação server   | HTMX                                            |
| Realtime           | SSE / WebSocket (via HTMX extensions)           |
| CSS                | Scoped por componente + Tailwind CSS (opcional) |
| Validação          | Pydantic                                        |
| CLI                | Typer + Rich                                    |
| Frontend tooling   | npm (Alpine, HTMX, Tailwind → vendor/)          |

### Público-alvo

Desenvolvedores Python que querem construir UIs reativas server-rendered sem
escrever JavaScript, mantendo a produtividade de um framework de componentes
moderno.

---

## 2. Anatomia de um Componente

Todo componente é um arquivo `.jinja` com até três blocos:

```text
┌──────────────────────────────────┐
│ ---                              │  ← Frontmatter (DSL declarativa)
│   extends, from, import,         │
│   props, slot, store,            │
│   let, const, state, computed    │
│ ---                              │
├──────────────────────────────────┤
│ <style scoped>                   │  ← CSS com escopo automático (opcional)
│   .card { ... }                  │
│ </style>                         │
├──────────────────────────────────┤
│ <div reactive>                   │  ← HTML body com DSL de atributos
│   <Show when="x">...</Show>     │
│   <Button ...spread_props />    │
│ </div>                           │
└──────────────────────────────────┘
```

- O frontmatter (`---`) é **obrigatório** se o componente tem props, state
  ou imports. Pode ser omitido em componentes puramente estáticos.
- O bloco `<style scoped>` é **opcional**.
- O **body HTML** é obrigatório.

---

## 3. Gramática do Frontmatter

O frontmatter (`---`) aceita 10 tipos de declaração. Cada linha começa com
uma keyword, tornando a gramática LL(1).

### 3.1 EBNF

```ebnf
script        = { statement } ;
statement     = extends_stmt | import_stmt | from_import_stmt
              | props_stmt | slot_stmt | store_stmt
              | let_stmt | const_stmt | state_stmt | computed_stmt ;

extends_stmt  = "extends" STRING ;

import_stmt   = "import" ( default_import | named_import | wildcard_import ) ;
default_import = IDENT "from" STRING [ "as" IDENT ] ;
named_import  = "{" IDENT { "," IDENT } "}" "from" STRING ;
wildcard_import = "*" "from" STRING ;

from_import_stmt = "from" MODULE "import" IDENT { "," IDENT } ;

props_stmt    = "props" IDENT "=" "{" prop_field { "," prop_field } "}" ;
prop_field    = IDENT ":" type_expr [ "=" expr ] ;
type_expr     = pydantic_type [ "|" type_expr ] ;
pydantic_type = IDENT [ "[" type_expr { "," type_expr } "]" ]
              | "Literal" "[" expr { "," expr } "]"
              | "Annotated" "[" type_expr { "," expr } "]" ;

slot_stmt     = "slot" IDENT [ "=" html_fragment ] ;
store_stmt    = "store" IDENT "=" "{" js_object "}" ;

let_stmt      = "let" IDENT "=" expr ;
const_stmt    = "const" IDENT "=" expr ;
state_stmt    = "state" IDENT "=" expr ;
computed_stmt = "computed" IDENT "=" expr ;

(* Body: spread syntax em componentes *)
component_use = "<" IDENT { attr | spread } [ "/" ] ">" ;
spread        = "..." IDENT ;
```

### 3.2 Tipos suportados em props

A DSL aceita tipos Pydantic nativos diretamente:

| Tipo DSL                      | Pydantic model           |
| ----------------------------- | ------------------------ |
| `str`, `int`, `bool`, `float` | Tipos nativos            |
| `str \| None`                 | `str \| None` (Optional) |
| `list[str]`, `dict[str, Any]` | Genéricos                |
| `Literal["a", "b"]`           | Enum inline              |
| `EmailStr`, `HttpUrl`         | Tipos Pydantic           |
| `Annotated[int, Gt(0)]`       | Constraints              |
| `Callable`                    | `Callable \| None`       |

---

## 4. Imports

### Importar componentes

```python
# Default — nome = nome do arquivo
import Button from "./Button.jinja"

# Alias
import Button from "./Button.jinja" as PrimaryButton

# Named — múltiplos de um arquivo ou diretório
import { CardHeader, CardBody } from "./Card.jinja"
import { Card, Badge, Avatar } from "./components/"

# Wildcard — todos do diretório
import * from "./ui/"
```

### Importar tipos Python/Pydantic

Tipos primitivos (`str`, `int`, `bool`, `float`, `list`, `dict`, `Callable`,
`Any`, `None`) são auto-importados. Tipos Pydantic precisam de import
explícito:

```python
from typing import Literal, Annotated
from pydantic import EmailStr, HttpUrl
from annotated_types import Gt, Lt, Ge, Le, MinLen, MaxLen
```

### Extends (herança de layout)

```python
extends "layouts/Base.jinja"
```

Indica que a página herda de um layout. O corpo é injetado no
`<Slot:content />` do layout. Veja seção 25 (Layouts).

### Resolução de caminhos

| Padrão                    | Resolução                                      |
| ------------------------- | ---------------------------------------------- |
| `"./Button.jinja"`        | Relativo ao arquivo que importa                |
| `"../shared/Modal.jinja"` | Subida de diretório relativa                   |
| `"./components/"`         | Diretório: busca `{Name}.jinja` para cada nome |
| `"./ui/"` com wildcard    | Glob `*.jinja` no diretório                    |

### Compilação e composição

O compilador registra cada import no `ComponentRegistry`. Ao encontrar
`<Button />` no body, resolve para `{% include %}` com contexto via
`{% with %}`:

```jinja2
{# <Button label="Salvar" variant="primary" /> compila para: #}
{% with _props_label="Salvar", _props_variant="primary" %}
{% include "components/Button.jinja" %}
{% endwith %}

{# <Card title="Hello"><p>Body</p><slot:footer>F</slot:footer></Card> #}
{% with _props_title="Hello", _slot_default="<p>Body</p>", _slot_footer="F" %}
{% include "components/Card.jinja" %}
{% endwith %}

{# <Button ...btn_props label="Override" /> compila para: #}
{% with _spread=btn_props, _props_label="Override" %}
{% include "components/Button.jinja" %}
{% endwith %}
```

Props explícitos sempre sobrescrevem valores do spread.

---

## 5. Props

Declaração tipada usando tipos Pydantic nativos.

```python
props UserCardProps = {
  name:     str,                                        # required
  age:      int                        = 0,             # optional
  role:     Literal["admin", "mod", "user"] = "user",   # choices via Literal
  email:    EmailStr,                                    # tipo Pydantic
  bio:      str | None                 = None,           # nullable
  tags:     list[str]                  = [],             # list factory
  meta:     dict[str, Any]            = {},              # dict factory
  score:    Annotated[int, Gt(0), Lt(100)] = 50,         # constraints
  url:      HttpUrl | None             = None,           # URL validada
  on_click: Callable                   = None,           # callback
}
```

### Tipos suportados

| Tipo DSL                      | Pydantic         |
| ----------------------------- | ---------------- |
| `str`, `int`, `bool`, `float` | Tipos nativos    |
| `str \| None`                 | Union / Optional |
| `list[str]`, `dict[str, Any]` | Genéricos        |
| `Literal["a", "b"]`           | Enum inline      |
| `EmailStr`, `HttpUrl`         | Tipos Pydantic   |
| `Annotated[int, Gt(0)]`       | Constraints      |
| `Callable`                    | Callbacks        |

### Acesso no template

```html
<span>{{ props.name }}</span>
```

### Compilação interna

Cada `PropsDecl` gera um `pydantic.BaseModel` dinâmico via
`pydantic.create_model()`:

```python
class UserCardProps(BaseModel):
    name: str
    age: int = 0
    role: Literal["admin", "mod", "user"] = "user"
    email: EmailStr
    bio: str | None = None
    tags: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
    score: Annotated[int, Gt(0), Lt(100)] = 50
    url: HttpUrl | None = None
    on_click: Callable | None = None
```

A validação ocorre no momento do render: o contexto passado pela rota FastAPI
é validado contra o model antes de chegar ao template engine.

---

## 6. Variáveis

| Keyword    | Escopo             | Mutável  | Compilação           |
| ---------- | ------------------ | -------- | -------------------- |
| `let`      | Server (Jinja2)    | Sim      | `{% set x = expr %}` |
| `const`    | Server (Jinja2)    | Não      | `{% set X = expr %}` |
| `state`    | Client (Alpine.js) | Sim      | Incluído no `x-data` |
| `computed` | Server (Jinja2)    | Derivada | `{% set x = expr %}` |

### Exemplos

```python
let greeting = "Hello, " + props.name
const MAX_ITEMS = 50
state count = 0
state form = { name: "", email: "" }
computed total = len(props.items)
computed progress = (done_count / total * 100) if total > 0 else 0
```

### State e x-data

Todas as declarações `state` são coletadas e emitidas como o objeto
`x-data` do elemento marcado com `reactive`:

```html
<!-- DSL -->
<div reactive>

<!-- Compilado -->
<div x-data="{ count: 0, form: { name: '', email: '' } }">
```

---

## 7. Slots

### Declaração

```python
slot header                                  # sem fallback
slot footer = <span>© 2025 PJX</span>       # com fallback
```

### Renderização no template

```html
<!-- Self-closing -->
<Slot:header />

<!-- Com fallback inline -->
<Slot:header>
    <h2>Título padrão</h2>
</Slot:header>

<!-- Condicional -->
<Show when="has_slot('header')">
    <header><Slot:header /></header>
</Show>
```

### Passagem ao usar componente

```html
<Card title="Hello">
    <p>Corpo (slot default)</p>
    <slot:header><h1>Custom</h1></slot:header>
    <slot:footer><button>Fechar</button></slot:footer>
</Card>
```

### Compilação

| DSL                               | Jinja2                                                             |
| --------------------------------- | ------------------------------------------------------------------ |
| `<Slot:name />`                   | `{{ _slot_name \| default('') }}`                                  |
| `<Slot:name>fallback</Slot:name>` | `{% if _slot_name %}{{ _slot_name }}{% else %}fallback{% endif %}` |
| `<slot:name>content</slot:name>`  | Passa `content` como variável `_slot_name` via `{% with %}`        |

---

## 8. Control Flow Tags

### 8.1 `<Show>` — Condicional

```html
<Show when="user.is_admin">
    <button>Delete</button>
</Show>

<Show when="items" fallback="<p>Nenhum item.</p>">
    <ul>...</ul>
</Show>
```

| DSL                                        | Jinja2                                  |
| ------------------------------------------ | --------------------------------------- |
| `<Show when="x">body</Show>`               | `{% if x %}body{% endif %}`             |
| `<Show when="x" fallback="fb">body</Show>` | `{% if x %}body{% else %}fb{% endif %}` |

### 8.2 `<For>` — Iteração

```html
<For each="users" as="user">
    <li>{{ user.name }}</li>
<Empty>
    <p>Nenhum resultado.</p>
</Empty>
</For>
```

| DSL                               | Jinja2                             |
| --------------------------------- | ---------------------------------- |
| `<For each="x" as="i">body</For>` | `{% for i in x %}body{% endfor %}` |
| `<Empty>fallback</Empty>`         | `{% else %}fallback`               |

Variáveis de loop herdadas do Jinja2: `loop.index`, `loop.index0`,
`loop.first`, `loop.last`, `loop.length`, `loop.cycle()`.

### 8.3 `<Switch>` / `<Case>` / `<Default>`

```html
<Switch on="status">
    <Case value="active"><Badge variant="success" /></Case>
    <Case value="pending"><Badge variant="warning" /></Case>
    <Default><Badge variant="muted" /></Default>
</Switch>
```

| DSL                      | Jinja2                  |
| ------------------------ | ----------------------- |
| `<Switch on="x">`        | `{% set _sw = x %}`     |
| `<Case value="v">` (1º)  | `{% if _sw == "v" %}`   |
| `<Case value="v">` (2º+) | `{% elif _sw == "v" %}` |
| `<Default>`              | `{% else %}`            |
| `</Switch>`              | `{% endif %}`           |

### 8.4 `<Portal>` — Out-of-Band (HTMX OOB)

```html
<Portal target="notifications">
    <div class="toast">Item salvo!</div>
</Portal>
```

| DSL                                     | HTML                                    |
| --------------------------------------- | --------------------------------------- |
| `<Portal target="id">`                  | `<div id="id" hx-swap-oob="true">`      |
| `<Portal target="id" swap="outerHTML">` | `<div id="id" hx-swap-oob="outerHTML">` |

### 8.5 `<ErrorBoundary>`

```html
<ErrorBoundary fallback="<p>Algo deu errado.</p>">
    <UserProfile user="{{ user }}" />
</ErrorBoundary>
```

Compilação: wrapper `try/except` que renderiza fallback em caso de erro.

### 8.6 `<Await>` — Carregamento Assíncrono

```html
<Await src="/api/users" trigger="load">
    <slot:loading><div class="skeleton">Carregando...</div></slot:loading>
    <slot:error><p>Erro ao carregar.</p></slot:error>
</Await>
```

| DSL                                 | HTML                                                        |
| ----------------------------------- | ----------------------------------------------------------- |
| `<Await src="/url" trigger="load">` | `<div hx-get="/url" hx-trigger="load" hx-swap="innerHTML">` |

### 8.7 `<Transition>` / `<TransitionGroup>`

```html
<Transition enter="fade-in 300ms" leave="fade-out 200ms">
    <Show when="visible"><div>Conteúdo</div></Show>
</Transition>

<!-- Lista com transições -->
<TransitionGroup tag="ul" enter="slide-in" leave="slide-out" move="shuffle">
    <For each="items" as="item">
        <li key="{{ item.id }}">{{ item.name }}</li>
    </For>
</TransitionGroup>
```

| DSL                                             | HTML                                            |
| ----------------------------------------------- | ----------------------------------------------- |
| `<Transition enter="x" leave="y">`              | `x-transition:enter="x" x-transition:leave="y"` |
| `<TransitionGroup tag="ul" enter="x" move="y">` | `<ul>` com transition classes por item          |
| `key="{{ id }}"`                                | Identificador para diff de lista                |

### 8.8 `<Fragment>` — Sem wrapper DOM

```html
<Fragment>
    <li>Item 1</li>
    <li>Item 2</li>
</Fragment>
```

Compilação: renderiza apenas os filhos, sem elemento wrapper.

### 8.9 `<Teleport>` — Client-side (Alpine)

```html
<Teleport to="#modal-root">
    <div class="modal">Conteúdo</div>
</Teleport>
```

Diferente do Portal (server OOB): Teleport usa Alpine.js para mover
elementos no DOM client-side.

### 8.10 `<Component>` — Renderização Dinâmica

```html
<Component is="{{ widget_type }}" data="{{ widget_data }}" />
```

Resolve o componente por nome em runtime via registry.

---

## 9. Atributos Reativos (Alpine.js)

### 9.1 `reactive` — Inicializa x-data

| DSL                     | HTML                            |
| ----------------------- | ------------------------------- |
| `reactive`              | `x-data="{ ...states }"`        |
| `reactive="{ x: 0 }"`   | `x-data="{ x: 0 }"`             |
| `reactive:store="name"` | `x-data="Alpine.store('name')"` |

### 9.2 `bind:` — Data Binding

| DSL                             | HTML                         |
| ------------------------------- | ---------------------------- |
| `bind:text="x"`                 | `x-text="x"`                 |
| `bind:html="x"`                 | `x-html="x"`                 |
| `bind:show="x"`                 | `x-show="x"`                 |
| `bind:model="x"`                | `x-model="x"`                |
| `bind:model.lazy="x"`           | `x-model.lazy="x"`           |
| `bind:model.number="x"`         | `x-model.number="x"`         |
| `bind:model.debounce.500ms="x"` | `x-model.debounce.500ms="x"` |
| `bind:class="x"`                | `:class="x"`                 |
| `bind:style="x"`                | `:style="x"`                 |
| `bind:{attr}="x"`               | `:{attr}="x"`                |
| `bind:cloak`                    | `x-cloak`                    |
| `bind:ref="x"`                  | `x-ref="x"`                  |
| `bind:transition`               | `x-transition`               |
| `bind:init="x"`                 | `x-init="x"`                 |

### 9.3 `on:` — Event Handlers

| DSL                           | HTML                        |
| ----------------------------- | --------------------------- |
| `on:click="x"`                | `@click="x"`                |
| `on:click.prevent="x"`        | `@click.prevent="x"`        |
| `on:click.stop="x"`           | `@click.stop="x"`           |
| `on:click.outside="x"`        | `@click.outside="x"`        |
| `on:click.once="x"`           | `@click.once="x"`           |
| `on:click.throttle.500ms="x"` | `@click.throttle.500ms="x"` |
| `on:input.debounce.300ms="x"` | `@input.debounce.300ms="x"` |
| `on:keydown.enter="x"`        | `@keydown.enter="x"`        |
| `on:scroll.window="x"`        | `@scroll.window="x"`        |

---

## 10. HTMX — Interação Server

### 10.1 `action:` — Verbos HTTP

| DSL                    | HTML               |
| ---------------------- | ------------------ |
| `action:get="/url"`    | `hx-get="/url"`    |
| `action:post="/url"`   | `hx-post="/url"`   |
| `action:put="/url"`    | `hx-put="/url"`    |
| `action:patch="/url"`  | `hx-patch="/url"`  |
| `action:delete="/url"` | `hx-delete="/url"` |

### 10.2 Swap, Target, Trigger

| DSL                | HTML                    |
| ------------------ | ----------------------- |
| `swap="x"`         | `hx-swap="x"`           |
| `target="x"`       | `hx-target="x"`         |
| `trigger="x"`      | `hx-trigger="x"`        |
| `select="x"`       | `hx-select="x"`         |
| `select-oob="x"`   | `hx-select-oob="x"`     |
| `confirm="x"`      | `hx-confirm="x"`        |
| `indicator="x"`    | `hx-indicator="x"`      |
| `push-url`         | `hx-push-url="true"`    |
| `replace-url`      | `hx-replace-url="true"` |
| `vals='json'`      | `hx-vals='json'`        |
| `headers='json'`   | `hx-headers='json'`     |
| `encoding="x"`     | `hx-encoding="x"`       |
| `preserve`         | `hx-preserve="true"`    |
| `sync="x"`         | `hx-sync="x"`           |
| `disabled-elt="x"` | `hx-disabled-elt="x"`   |
| `boost`            | `hx-boost="true"`       |

### 10.3 Swap values

`innerHTML` (default), `outerHTML`, `beforebegin`, `afterbegin`,
`beforeend`, `afterend`, `delete`, `none`.

Modifiers: `transition:true`, `settle:300ms`, `scroll:top`, `show:top`,
`focus-scroll:true`.

### 10.4 Trigger modifiers

`once`, `delay:Nms`, `throttle:Ns`, `queue:first|last|all`,
`from:#selector`.

---

## 11. SSE — Server-Sent Events

```html
<div live="/events/dashboard">
    <span channel="user-count">0</span>
    <div channel="notifications" swap="beforeend"></div>
</div>
```

| DSL               | HTML                              |
| ----------------- | --------------------------------- |
| `live="/url"`     | `hx-ext="sse" sse-connect="/url"` |
| `channel="event"` | `sse-swap="event"`                |
| `close="event"`   | `sse-close="event"`               |

---

## 12. WebSocket

```html
<div socket="/ws/chat">
    <div channel="message" swap="beforeend"></div>
    <form send="message"><input name="text" /></form>
</div>
```

| DSL             | HTML                            |
| --------------- | ------------------------------- |
| `socket="/url"` | `hx-ext="ws" ws-connect="/url"` |
| `send="event"`  | `ws-send="event"`               |

---

## 13. Loading States

| DSL                        | Efeito                           |
| -------------------------- | -------------------------------- |
| `loading`                  | Classe `htmx-indicator`          |
| `loading:show`             | Visível durante request          |
| `loading:hide`             | Escondido durante request        |
| `loading:class="x"`        | Adiciona classes durante request |
| `loading:disabled`         | `disabled` durante request       |
| `loading:aria-busy="true"` | `aria-busy` durante request      |

---

## 14. Forms

```html
<form action:post="/api/users" swap="outerHTML" reactive="{ valid: false }">
    <input name="name" bind:model="name" required minlength="3"
           on:input="valid = $el.form.checkValidity()" />
    <button type="submit" bind:disabled="!valid"
            loading:class="opacity-50" disabled-elt="this">
        <span loading:hide>Criar</span>
        <span loading:show>Criando...</span>
    </button>
</form>
```

Upload com `encoding="multipart/form-data"`.

---

## 15. CSS Scoping

```html
<style scoped>
  .alert { padding: 1rem; }
  .alert-success { background: #d1fae5; }
</style>
```

### Compilação

1. Gerar hash determinístico do path do componente: `sha256(path)[:7]`
2. Prefixar cada seletor: `.alert` → `[data-pjx-a1b2c3] .alert`
3. Adicionar `data-pjx-a1b2c3` ao root element do componente
4. Coletar CSS de todos os componentes no build final

---

## 16. Template Engine

### Protocol

```python
class EngineProtocol(Protocol):
    def render(self, template_name: str, context: dict[str, Any]) -> str: ...
    def render_string(self, source: str, context: dict[str, Any]) -> str: ...
    def add_template(self, name: str, source: str) -> None: ...
    def add_global(self, name: str, value: Any) -> None: ...
```

### Engines

| Engine                 | Quando usar                                                  |
| ---------------------- | ------------------------------------------------------------ |
| **Jinja2** (padrão)    | Máxima compatibilidade, ecossistema maduro, 1.5x mais rápido |
| **MiniJinja** (opt-in) | Rust-based, melhor para free-threaded Python 3.14            |

Configurável via `pjx.toml`:

```toml
[pjx]
engine = "jinja2"  # "jinja2" | "minijinja" | "auto"
```

`auto` → Jinja2 (default, pode mudar no futuro).

### Limitações do MiniJinja

- Sem acesso a métodos Python (`x.items()`)
- Sem `varargs`/`kwargs` em macros
- Sem `%` string formatting
- Tuples viram lists

O compilador PJX gera Jinja2 syntax padrão compatível com ambos os engines.

---

## 17. Integração FastAPI

### Classe principal

```python
from pjx import PJX, PJXConfig, SEO

app = FastAPI()
pjx = PJX(
    app,
    config=PJXConfig(toml_path="pjx.toml"),
    layout="layouts/Base.jinja",
    seo=SEO(
        title="My App",
        description="Default SEO for all pages.",
        og_type="website",
    ),
)
```

Parâmetros de `PJX`:

| Param    | Tipo       | Descrição                                                  |
| -------- | ---------- | ---------------------------------------------------------- |
| `app`    | `FastAPI`  | Instância do FastAPI                                       |
| `config` | `PJXConfig`| Configuração carregada de `pjx.toml` (opcional)            |
| `layout` | `str`      | Template de layout padrão, wrapa todas as páginas          |
| `seo`    | `SEO`      | SEO global — páginas herdam, podem sobrescrever por campo  |

O `PJX` auto-monta `/static` a partir de `config.static_dir`.

### SEO

`SEO` é um dataclass com campos para `<title>`, `<meta>` tags, Open Graph e
Twitter Card. O SEO global definido em `PJX(seo=...)` é aplicado a todas as
páginas. Para sobrescrever por página, use `title=` no decorador ou retorne
`seo` no handler:

```python
# Via decorador (mais comum)
@pjx.page("/about", title="About — My App")

# Via handler (controle total)
@pjx.page("/about")
async def about():
    return {"seo": SEO(title="About", description="Custom description.")}
```

Campos não-vazios da página sobrescrevem o global; vazios usam o fallback.

### Decorators

```python
# Página com template, título e métodos
@pjx.page(
    "/search",
    template="pages/Search.jinja",
    title="Search — My App",
    methods=["GET", "POST"],
)
async def search(form: Annotated[SearchForm, FormData()]):
    results = do_search(form.query)
    return {"query": form.query, "results": results}

# Componente parcial (sem layout, retorna HTML fragment)
@pjx.component("components/ItemList.jinja")
async def item_list(request: Request):
    return {"items": await get_items()}
```

### FormData e Annotated

Handlers de página podem receber Pydantic models como parâmetros. Use
`Annotated[Model, FormData()]` para parsear form data (POST) ou query params
(GET) automaticamente:

```python
from typing import Annotated
from pydantic import BaseModel
from pjx import FormData

class SearchForm(BaseModel):
    query: str = ""

@pjx.page("/search", methods=["GET", "POST"])
async def search(form: Annotated[SearchForm, FormData()]):
    return {"results": do_search(form.query)}
```

Parâmetros sem `FormData` são injetados normalmente pelo FastAPI (`request`,
`Depends`, etc.).

### HTMX Partials

Endpoints que retornam HTML fragments para HTMX não precisam de layout.
Use rotas FastAPI normais com `HTMLResponse`:

```python
@app.post("/htmx/todos/add")
async def htmx_add_todo(request: Request) -> HTMLResponse:
    form = await request.form()
    todos_db.append({"text": form["text"], "done": False})
    return HTMLResponse(render_todo_list())
```

### Fluxo por request

1. FastAPI chama o handler → recebe `dict` de contexto
2. PJX merge SEO: decorator `title=` → handler `seo` → global default
3. Compila template e imports (com cache)
4. Engine renderiza Jinja2 compilado com contexto + `props` namespace
5. Wrapa no layout (se configurado) com `{{ body }}` como Markup
6. Retorna `HTMLResponse`

### SSE Decorator

```python
@pjx.sse("/events/stats")
async def stats_stream(stream: EventStream):
    while True:
        stats = await get_stats()
        await stream.send_html("stats-update", "partials/stats.jinja", stats)
        await asyncio.sleep(5)
```

---

## 18. CLI

Comandos disponíveis via `pjx` (Typer + Rich):

| Comando            | Descrição                                                    |
| ------------------ | ------------------------------------------------------------ |
| `pjx init`         | Scaffolda projeto: dirs, config, package.json                |
| `pjx dev`          | Dev server com hot reload (uvicorn --reload)                 |
| `pjx run`          | Production server                                            |
| `pjx build`        | Compila todos os `.jinja` + bundle CSS + npm build           |
| `pjx check`        | Verifica sintaxe de todos os `.jinja` (como ruff check)      |
| `pjx format`       | Auto-formata `.jinja` (normaliza whitespace, ordena imports) |
| `pjx add <pkg>`    | Instala pacote JS via npm + copia para vendor/               |
| `pjx remove <pkg>` | Remove pacote JS via npm                                     |

### Logging

Todos os comandos usam `logging` com `rich.logging.RichHandler`:

- `DEBUG` — detalhes de parse/compile (flag `--verbose`)
- `INFO` — progresso normal (arquivos processados, server iniciado)
- `WARNING` — deprecations, fallbacks
- `ERROR` — erros de parse/compile com localização (arquivo:linha:coluna)

---

## 19. Estrutura de Projeto (gerada por `pjx init`)

```text
project/
├── pjx.toml                  # Configuração PJX
├── package.json               # npm para deps JS
├── templates/
│   ├── pages/                 # Componentes de página completa
│   ├── components/            # Componentes reutilizáveis
│   ├── ui/                    # Primitivos UI (Button, Badge, etc.)
│   ├── layouts/               # Layouts base (header, footer, nav)
│   └── vendor/                # Templates de terceiros
├── static/
│   ├── vendor/                # JS/CSS compilado do npm (alpine, htmx)
│   ├── js/                    # JavaScript customizado
│   └── css/                   # CSS customizado + scoped compilado
└── src/
    └── app.py                 # FastAPI app com PJX
```

---

## 20. Configuração (`pjx.toml`)

O PJX usa um arquivo TOML **flat** (sem tabelas `[pjx]`) carregado via
`PJXConfig`:

```toml
engine = "jinja2"           # "jinja2" | "minijinja" | "auto"
debug = false

template_dirs = ["templates"]
static_dir = "static"
pages_dir = "templates/pages"
components_dir = "templates/components"
layouts_dir = "templates/layouts"
ui_dir = "templates/ui"
vendor_templates_dir = "templates/vendor"
vendor_static_dir = "static/vendor"

host = "127.0.0.1"
port = 8000

alpine = true               # Incluir Alpine.js por padrão
htmx = true                 # Incluir HTMX por padrão
tailwind = false             # Tailwind CSS opt-in
```

### Carregamento

```python
from pjx import PJXConfig

# Caminho explícito — paths resolvidos relativo ao diretório do .toml
config = PJXConfig(toml_path="examples/pjx.toml")

# CWD
config = PJXConfig()  # procura pjx.toml no diretório atual
```

Variáveis de ambiente com prefixo `PJX_` sobrescrevem valores do TOML
(via `pydantic-settings`). Prioridade: init kwargs > env vars > TOML.

Todos os caminhos relativos no TOML são resolvidos contra o diretório do
arquivo `pjx.toml`, não contra o CWD.

---

## 21. Pipeline de Compilação

```text
.jinja file
  │
  ├─ [1] parser._extract_blocks()
  │      Separa: frontmatter, <style scoped> body, HTML body
  │
  ├─ [2] lexer.tokenize(script)
  │      Gera stream de tokens (keyword-driven)
  │
  ├─ [3] parser._parse_script(tokens)
  │      Produz: extends, from_imports, imports, props, slots, store,
  │              let/const, state, computed
  │
  ├─ [4] parser._parse_body(html, known_components)
  │      html.parser.HTMLParser → árvore de Nodes
  │      Reconhece: <Show>, <For>, <Switch>, <Portal>, etc.
  │      Reconhece componentes registrados (PascalCase)
  │
  ├─ [5] Component AST (ast_nodes.Component)
  │
  ├─ [6] compiler.compile(component)
  │      ├─ Emite {% set %} para let/const/computed
  │      ├─ Coleta state → alpine_data dict
  │      ├─ Transforma nodes recursivamente:
  │      │   ShowNode → {% if %}
  │      │   ForNode → {% for %}
  │      │   SwitchNode → {% if/elif/else %}
  │      │   ElementNode → transforma attrs (bind:→x-, on:→@, action:→hx-)
  │      │   ComponentNode → {% with %}{% include %}{% endwith %}
  │      │   PortalNode → <div hx-swap-oob>
  │      │   AwaitNode → <div hx-get hx-trigger="load">
  │      └─ css.scope_css() se <style scoped> presente
  │
  ├─ [7] CompiledComponent
  │      .jinja_source  → template Jinja2 válido
  │      .css           → CSS com escopo
  │      .alpine_data   → dict para x-data
  │      .scope_hash    → identificador de escopo
  │
  └─ [8] engine.render(jinja_source, context) → HTML final
```

---

## 22. Arquitetura de Módulos

```text
src/pjx/
├── errors.py          # Hierarquia de exceções
├── ast_nodes.py       # Dataclasses do AST (IR)
├── lexer.py           # Tokenizer do frontmatter
├── parser.py          # .jinja → Component AST
├── compiler.py        # AST → Jinja2 + Alpine + HTMX
├── css.py             # Scoped CSS
├── config.py          # PydanticSettings
├── registry.py        # Component registry + imports
├── props.py           # Props → Pydantic models
├── slots.py           # Slot resolution
├── engine.py          # Template engine wrapper
├── integration.py     # FastAPI decorators
├── sse.py             # SSE helpers
├── assets.py          # Static files + vendor
├── log.py             # Rich logging
├── __init__.py        # Public API
├── __main__.py        # python -m pjx → CLI
└── cli/
    ├── __init__.py    # Typer app
    ├── init.py        # pjx init
    ├── dev.py         # pjx dev, run
    ├── build.py       # pjx build, check, format
    └── packages.py    # pjx add, remove
```

### Grafo de dependências

```text
errors (leaf)
ast_nodes (leaf)
css (leaf)
log (leaf)
config (leaf)
lexer → errors
parser → lexer, ast_nodes, errors
props → ast_nodes, errors
slots → ast_nodes
compiler → ast_nodes, registry, css, errors
registry → ast_nodes, parser, errors
engine → config
integration → registry, compiler, engine, props, config
sse → engine, integration
assets → config
cli/* → config, registry, compiler, engine, log
```

---

## 23. Layouts e Herança

Layouts definem a estrutura base da página. Páginas herdam via `extends`.

### Layout base (`layouts/Base.jinja`)

```html
---
props LayoutProps = {
  title: str = "PJX App",
  description: str = "",
}

slot head
slot content
slot footer
---

<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{{ props.title }}</title>
    <Show when="props.description">
        <meta name="description" content="{{ props.description }}" />
    </Show>
    <Slot:head />
    <link rel="stylesheet" href="/static/css/app.css" />
    <script defer src="/static/vendor/alpine.min.js"></script>
    <script defer src="/static/vendor/htmx.min.js"></script>
</head>
<body>
    <Slot:content />
    <Slot:footer>
        <footer><p>© 2025 PJX</p></footer>
    </Slot:footer>
</body>
</html>
```

### Página que herda

```html
---
extends "layouts/Base.jinja"
from pydantic import EmailStr

props HomeProps = {
  user: dict,
}
---

<slot:head>
    <meta property="og:title" content="Home — {{ props.user.name }}" />
</slot:head>

<h1>Bem-vindo, {{ props.user.name }}</h1>
```

O corpo da página (fora de `<slot:*>`) é injetado no `<Slot:content />`
do layout automaticamente.

### Compilação

```jinja2
{# extends "layouts/Base.jinja" compila para: #}
{% extends "layouts/Base.jinja" %}
{% block content %}
  <h1>Bem-vindo, {{ props.user.name }}</h1>
{% endblock %}
{% block head %}
  <meta property="og:title" content="Home — {{ props.user.name }}" />
{% endblock %}
```

---

## 24. Prop Spreading

Espalhar um dict como props de um componente:

```html
<Button ...btn_props />
<Button ...btn_props label="Override" />
```

Props explícitos sobrescrevem valores do spread. Compilação:

```jinja2
{% with _spread=btn_props, _props_label="Override" %}
{% include "components/Button.jinja" %}
{% endwith %}
```

---

## 25. Global State (Alpine Stores)

### Declaração no frontmatter

```python
store todos = {
  items: [],
  filter: "all",
  add(text) { this.items.push({ text, done: false }) },
}
```

### Uso em componentes

```html
<div reactive:store="todos">
    <input bind:model="$store.todos.filter" />
</div>
```

### Compilação

| Escrito                 | Compilado                                      |
| ----------------------- | ---------------------------------------------- |
| `store name = { ... }`  | `Alpine.store('name', { ... })` no script init |
| `reactive:store="name"` | `x-data="Alpine.store('name')"`                |

---

## 26. Funções Built-in nos Templates

| Função                  | Descrição                               |
| ----------------------- | --------------------------------------- |
| `has_slot('name')`      | `true` se o slot foi fornecido pelo pai |
| `len(x)`                | Comprimento de lista/string             |
| `range(n)`              | Sequência 0..n-1                        |
| `enumerate(x)`          | Pares (index, item)                     |
| `url_for('route_name')` | URL reversa para rota FastAPI           |
| `static('path')`        | URL para arquivo estático               |

### Implementação

Registradas como globals no template engine via `engine.add_global()`.
`has_slot('name')` verifica se `_slot_{name}` está definido no contexto.

---

## 27. Páginas de Erro

### Template de erro

```html
---
extends "layouts/Base.jinja"

props Error404Props = {
  path: str,
}
---

<h1>404</h1>
<p>Página <code>{{ props.path }}</code> não encontrada.</p>
```

### Registro via FastAPI

```python
@pjx.error(404, "errors/404.jinja")
async def not_found(request: Request):
    return {"path": request.url.path}
```

Internamente, registra um `exception_handler` no FastAPI que renderiza
o template com o contexto retornado.

---

## 28. Componentes Recursivos

Componentes podem importar a si mesmos para árvores:

```html
---
import TreeNode from "./TreeNode.jinja"

props TreeNodeProps = {
  node: dict,
  depth: int = 0,
  max_depth: int = 10,
}
---

<div style="margin-left: {{ props.depth * 16 }}px">
    <span>{{ props.node.label }}</span>
    <Show when="props.node.children and props.depth < props.max_depth">
        <For each="props.node.children" as="child">
            <TreeNode node="{{ child }}" depth="{{ props.depth + 1 }}" />
        </For>
    </Show>
</div>
```

O registry detecta self-imports e permite até `max_depth` níveis.
Ultrapassar gera `CompileError`.

---

## 29. Frontmatter — Regras de Parsing

- `---` deve estar **sozinho na linha** (sem espaços)
- Primeiro `---` abre, próximo `---` isolado fecha
- Strings no frontmatter podem conter `---`:
  `let x = "foo --- bar"` é válido
- Comentários: `#` até fim da linha
- Linhas em branco ignoradas
- Props blocks `{ ... }` podem ocupar várias linhas

Ordem recomendada das declarações:

```text
extends → from → import → props → slot → store → let/const → state → computed
```

---

## 30. Formato de Erros

Erros seguem o formato `arquivo:linha:coluna: Tipo: mensagem`:

```text
templates/Card.jinja:15:3: ParseError: Tag <Show> não fechada
templates/Home.jinja:3:1: ImportError: Componente "Missing.jinja" não encontrado
templates/Form.jinja:8:12: PropValidationError: Campo "email" esperava EmailStr
```

### `pjx check` output

```text
✗ templates/Card.jinja
  15:3  error  Tag <Show> não fechada
  42:5  error  Prop "status" requerido mas sem default

✗ templates/Home.jinja
  3:1   error  Componente "Missing.jinja" não encontrado

✓ templates/Layout.jinja
✓ templates/Button.jinja

Found 3 errors in 2 files (checked 4 files)
```

---

## 31. `pjx format` — Regras de Formatação

- **Frontmatter**: normaliza indentação (0 espaços), espaço ao redor de `=`
  e `:`, agrupa declarações por tipo (extends → imports → props → etc.)
- **Imports**: ordena alfabeticamente, agrupa `from` imports separados de
  `import` componentes
- **Props**: alinha `:` e `=` por coluna, um campo por linha
- **Body HTML**: normaliza indentação (2 espaços), self-closing com `/>`
- **Atributos**: um por linha se mais de 3 atributos
- **Style**: preserva CSS original (não reformata)

---

## 32. Non-Goals

- **Não é um framework frontend JS** — Alpine.js lida com reatividade client
- **Não compila para React/Vue/Solid** — o alvo é Jinja2 + HTMX
- **Não é um bundler JS completo** — npm + build simples para vendor/
- **Não suporta TypeScript** — a DSL é Python-typed
- **Não faz SSG** — foco em server-rendered dinâmico
- **Não substitui Jinja2** — compila *para* Jinja2

---

## 33. Referências

- [HTMX](https://htmx.org/docs/)
- [Alpine.js](https://alpinejs.dev/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [MiniJinja](https://github.com/mitsuhiko/minijinja)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic](https://docs.pydantic.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
