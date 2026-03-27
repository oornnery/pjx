# PJX DSL — Especificação Completa

> DSL Python para componentes `.jinja` reativos, inspirada no SolidJS, Svelte e Vue.
> Compila para Jinja2 + HTMX + Alpine.js + SSE.

---

## 1. Estrutura de um Componente `.jinja`

Todo componente é um arquivo `.jinja` com um frontmatter declarativo delimitado
por `---` no topo e HTML reativo no corpo.

```html
---
import Button from "./Button.jinja"
import Badge from "../shared/Badge.jinja"
import { CardHeader, CardBody } from "./Card.jinja"

props {
  id:       int,
  text:     str,
  done:     bool      = false,
  priority: str       = "medium"  ["high", "medium", "low"],
  tags:     list[str] = [],
}

slot actions
slot footer = <span>Default footer</span>

let css_class = "todo-" + props.priority
const MAX_LENGTH = 140

state count = 0
state editing = false
state hover = false

computed remaining = MAX_LENGTH - len(props.text)
computed is_valid = remaining >= 0
---

<li id="todo-{{ props.id }}" class="{{ css_class }}" reactive>
    <!-- corpo do componente -->
</li>
```

---

## 2. Imports

### Importar componentes

```python
# ── Importar componente (nome = nome do arquivo) ──────────────
import Button from "./Button.jinja"
import Modal from "../shared/Modal.jinja"

# ── Alias ─────────────────────────────────────────────────────
import Button from "./Button.jinja" as PrimaryButton

# ── Importar múltiplos de um diretório ────────────────────────
import { Card, Badge, Avatar } from "./components/"

# ── Importar sub-componentes de um arquivo multi-export ───────
import { CardHeader, CardBody, CardFooter } from "./Card.jinja"

# ── Wildcard (todos do diretório) ─────────────────────────────
import * from "./ui/"
```

### Importar tipos Python/Pydantic

Tipos primitivos (`str`, `int`, `bool`, `float`, `list`, `dict`, `Callable`,
`Any`, `None`) são auto-importados. Tipos Pydantic e constraints precisam de
import explícito com syntax Python:

```python
from typing import Literal, Annotated
from pydantic import EmailStr, HttpUrl
from annotated_types import Gt, Lt, Ge, Le, MinLen, MaxLen
```

### Extends (herança de layout)

```python
extends "layouts/Base.jinja"
```

Indica que a página herda de um layout. O corpo da página é injetado no
`<Slot:content />` do layout. Veja seção 18 (Layouts).

### Compilação

| Escrito                               | Efeito interno                                        |
| ------------------------------------- | ----------------------------------------------------- |
| `import Button from "./Button.jinja"` | Registra `Button` no preprocessor, carrega o template |
| `import Button from "..." as Btn`     | Registra como `Btn`                                   |
| `import { A, B } from "./dir/"`       | Carrega `dir/A.jinja` e `dir/B.jinja`                 |
| `from pydantic import EmailStr`       | Disponibiliza `EmailStr` como tipo em props           |
| `extends "layouts/Base.jinja"`        | Wrapa a página no layout (template inheritance)       |

---

## 3. Props

Declaração tipada usando tipos Pydantic nativos.

```python
props {
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

**Tipos Pydantic suportados:**

| Tipo DSL                      | Pydantic         |
| ----------------------------- | ---------------- |
| `str`, `int`, `bool`, `float` | Tipos nativos    |
| `str \| None`                 | Union / Optional |
| `list[str]`, `dict[str, Any]` | Genéricos        |
| `Literal["a", "b"]`           | Enum inline      |
| `EmailStr`, `HttpUrl`         | Tipos Pydantic   |
| `Annotated[int, Gt(0)]`       | Constraints      |
| `Callable`                    | Callbacks        |

**Acesso no template:**

```html
<span>{{ props.name }}</span>
<span>{{ props.role }}</span>
```

**Compilação interna:**

```python
# Gera automaticamente um BaseModel:
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

---

## 4. Variáveis

```python
# ── let — variável server-side (disponível no template) ───────
let greeting = "Hello, " + props.name
let item_count = len(props.items)
let css_class = "card card--" + props.variant

# ── const — constante imutável ────────────────────────────────
const MAX_ITEMS = 50
const API_URL = "/api/v1"

# ── state — variável reativa CLIENT-SIDE (Alpine.js) ──────────
state count = 0
state open = false
state search = ""
state selected = []
state form = { name: "", email: "" }

# ── computed — derivada reativa (recalcula quando deps mudam) ─
computed total = len(props.items)
computed done_count = len([i for i in props.items if i.done])
computed progress = (done_count / total * 100) if total > 0 else 0
computed is_empty = total == 0
```

**Compilação:**

| Escrito                 | Server (Jinja2)          | Client (Alpine.js)         |
| ----------------------- | ------------------------ | -------------------------- |
| `let x = 1`             | `{% set x = 1 %}`        | —                          |
| `const X = 1`           | `{% set X = 1 %}`        | —                          |
| `state count = 0`       | `{{ count }}` para SSR   | `x-data` inclui `count: 0` |
| `computed total = expr` | `{% set total = expr %}` | —                          |

---

## 5. Slots

```python
# ── Declarar slot no frontmatter ──────────────────────────────
slot header                                    # slot sem fallback
slot footer = <span>© 2025 PJX</span>         # com fallback
slot actions                                   # slot vazio se não fornecido
```

**Renderizar slot no template:**

```html
<!-- Self-closing: renderiza ou vazio -->
<Slot:header />

<!-- Com fallback inline -->
<Slot:header>
    <h2>Título padrão</h2>
</Slot:header>

<!-- Slot com condicional -->
<Show when="has_slot('header')">
    <header><Slot:header /></header>
</Show>
```

**Passar slot ao usar componente:**

```html
<Card title="Hello">
    <!-- children = slot default -->
    <p>Corpo do card</p>

    <!-- slot nomeado -->
    <slot:header>
        <h1>Custom Header</h1>
    </slot:header>

    <slot:footer>
        <button on:click="close()">Fechar</button>
    </slot:footer>
</Card>
```

**Compilação:**

| Escrito                          | Resultado                                                        |
| -------------------------------- | ---------------------------------------------------------------- |
| `<Slot:header />`                | `{{ _slot_header \| default('') }}`                              |
| `<Slot:header>fb</Slot:header>`  | `{% if _slot_header %}{{ _slot_header }}{% else %}fb{% endif %}` |
| `<slot:name>content</slot:name>` | Passa `content` como slot nomeado ao componente pai              |

---

## 6. Control Flow — Tags HTML

### `<Show>` — Condicional

```html
<!-- Simples -->
<Show when="user.is_admin">
    <button>Delete</button>
</Show>

<!-- Com fallback -->
<Show when="items" fallback="<p>Nenhum item.</p>">
    <ul>...</ul>
</Show>

<!-- Negação -->
<Show when="not loading">
    <div>Conteúdo carregado</div>
</Show>

<!-- Expressão complexa -->
<Show when="user.age >= 18 and user.verified">
    <span>Acesso liberado</span>
</Show>
```

| Escrito                                    | Compilado                               |
| ------------------------------------------ | --------------------------------------- |
| `<Show when="x">...body...</Show>`         | `{% if x %}...body...{% endif %}`       |
| `<Show when="x" fallback="fb">body</Show>` | `{% if x %}body{% else %}fb{% endif %}` |

---

### `<For>` — Iteração

```html
<!-- Básico -->
<For each="users" as="user">
    <li>{{ user.name }}</li>
</For>

<!-- Com index (usa loop.index0 do Jinja2) -->
<For each="items" as="item">
    <li>{{ loop.index }}. {{ item }}</li>
</For>

<!-- Com fallback vazio -->
<For each="results" as="result">
    <div>{{ result.title }}</div>
<Empty>
    <p>Nenhum resultado encontrado.</p>
</Empty>
</For>

<!-- Nested -->
<For each="categories" as="cat">
    <h3>{{ cat.name }}</h3>
    <For each="cat.products" as="product">
        <span>{{ product.name }}</span>
    </For>
</For>

<!-- Com filtro inline -->
<For each="users | selectattr('active')" as="user">
    <li>{{ user.name }}</li>
</For>
```

| Escrito                 | Compilado          |
| ----------------------- | ------------------ |
| `<For each="x" as="i">` | `{% for i in x %}` |
| `<Empty>`               | `{% else %}`       |
| `</For>`                | `{% endfor %}`     |

**Variáveis de loop disponíveis (herdadas do Jinja2):**

| Variável              | Descrição                |
| --------------------- | ------------------------ |
| `loop.index`          | Iteração atual (1-based) |
| `loop.index0`         | Iteração atual (0-based) |
| `loop.first`          | `true` se primeiro item  |
| `loop.last`           | `true` se último item    |
| `loop.length`         | Total de itens           |
| `loop.cycle('a','b')` | Alterna entre valores    |

---

### `<Switch>` / `<Case>` / `<Default>` — Multi-branch

```html
<Switch on="status">
    <Case value="active">
        <Badge text="Ativo" variant="success" />
    </Case>
    <Case value="pending">
        <Badge text="Pendente" variant="warning" />
    </Case>
    <Case value="blocked">
        <Badge text="Bloqueado" variant="danger" />
    </Case>
    <Default>
        <Badge text="Desconhecido" variant="muted" />
    </Default>
</Switch>

<!-- Switch com números -->
<Switch on="props.level">
    <Case value="1"><h1>{{ title }}</h1></Case>
    <Case value="2"><h2>{{ title }}</h2></Case>
    <Case value="3"><h3>{{ title }}</h3></Case>
    <Default><p>{{ title }}</p></Default>
</Switch>
```

| Escrito                  | Compilado               |
| ------------------------ | ----------------------- |
| `<Switch on="x">`        | `{% set _sw = x %}`     |
| `<Case value="v">` (1º)  | `{% if _sw == "v" %}`   |
| `<Case value="v">` (2º+) | `{% elif _sw == "v" %}` |
| `<Default>`              | `{% else %}`            |
| `</Switch>`              | `{% endif %}`           |

---

### `<Portal>` — Out-of-Band Swap (HTMX OOB)

```html
<!-- Teleporta conteúdo para outro lugar do DOM via HTMX OOB -->
<Portal target="notifications">
    <div class="toast toast-success">Item salvo!</div>
</Portal>

<!-- Substituir sidebar -->
<Portal target="sidebar" swap="outerHTML">
    <nav>Menu atualizado</nav>
</Portal>
```

| Escrito                                 | Compilado                               |
| --------------------------------------- | --------------------------------------- |
| `<Portal target="id">`                  | `<div id="id" hx-swap-oob="true">`      |
| `<Portal target="id" swap="outerHTML">` | `<div id="id" hx-swap-oob="outerHTML">` |
| `</Portal>`                             | `</div>`                                |

---

### `<Component>` — Renderização de Componente

```html
<!-- Self-closing (sem children) -->
<Badge text="Novo" variant="success" />

<!-- Com children -->
<Card title="Welcome" variant="primary">
    <p>Conteúdo do card.</p>
</Card>

<!-- Com slots nomeados -->
<Modal title="Confirmar">
    <p>Tem certeza?</p>

    <slot:footer>
        <button on:click="cancel()">Cancelar</button>
        <button on:click="confirm()">Confirmar</button>
    </slot:footer>
</Modal>

<!-- Componente dinâmico -->
<Component is="{{ widget_type }}" data="{{ widget_data }}" />

<!-- Prop spreading — espalha dict como props -->
<Button ...btn_props />
<Button ...btn_props label="Override" />

<!-- Componente recursivo (tree) -->
<TreeNode node="{{ child }}" />
```

---

### `<ErrorBoundary>` — Tratamento de Erros

```html
<ErrorBoundary fallback="<p>Algo deu errado.</p>">
    <UserProfile user="{{ user }}" />
</ErrorBoundary>

<!-- Com componente de erro customizado -->
<ErrorBoundary>
    <RiskyComponent />
    <slot:error>
        <div class="error-box">
            <h3>Erro ao carregar</h3>
            <button action:get="/retry" target="closest div" swap="outerHTML">
                Tentar novamente
            </button>
        </div>
    </slot:error>
</ErrorBoundary>
```

| Escrito                                             | Compilado                                                   |
| --------------------------------------------------- | ----------------------------------------------------------- |
| `<ErrorBoundary fallback="fb">body</ErrorBoundary>` | `try/except` wrapper que renderiza fallback em caso de erro |

---

### `<Await>` — Carregamento Assíncrono

```html
<!-- Placeholder enquanto carrega via HTMX -->
<Await src="/api/users" trigger="load">
    <slot:loading>
        <div class="skeleton">Carregando...</div>
    </slot:loading>

    <slot:error>
        <p>Erro ao carregar dados.</p>
    </slot:error>
</Await>
```

| Escrito                             | Compilado                                                                |
| ----------------------------------- | ------------------------------------------------------------------------ |
| `<Await src="/url" trigger="load">` | `<div hx-get="/url" hx-trigger="load" hx-swap="innerHTML">` com skeleton |

---

### `<Transition>` — Animações

```html
<Transition enter="fade-in 300ms" leave="fade-out 200ms">
    <Show when="visible">
        <div class="modal">Conteúdo</div>
    </Show>
</Transition>

<!-- Transition de lista -->
<TransitionGroup tag="ul" enter="slide-in" leave="slide-out" move="shuffle">
    <For each="items" as="item">
        <li key="{{ item.id }}">{{ item.name }}</li>
    </For>
</TransitionGroup>
```

| Escrito                            | Compilado                                                   |
| ---------------------------------- | ----------------------------------------------------------- |
| `<Transition enter="x" leave="y">` | Wrapper com `x-transition:enter="x" x-transition:leave="y"` |

---

### `<Fragment>` — Wrapper sem elemento DOM

```html
<!-- Renderiza filhos sem criar um elemento wrapper -->
<Fragment>
    <li>Item 1</li>
    <li>Item 2</li>
    <li>Item 3</li>
</Fragment>
```

---

### `<Teleport>` — Renderizar em outro local do DOM (client-side)

```html
<!-- Diferente do Portal (OOB server): Teleport é client-side via Alpine -->
<Teleport to="#modal-root">
    <div class="modal">Conteúdo teleportado</div>
</Teleport>
```

---

## 7. Atributos Reativos (Alpine.js)

### `reactive` — Inicializa x-data

```html
<!-- Bare: gera x-data com todos os state declarados -->
<div reactive>

<!-- Explicit: x-data customizado -->
<div reactive="{ count: 0, open: false }">

<!-- Com escopo de store -->
<div reactive:store="todos">
```

| Escrito                 | Compilado                       |
| ----------------------- | ------------------------------- |
| `reactive`              | `x-data="{{ alpine_data }}"`    |
| `reactive="{ x: 0 }"`   | `x-data="{ x: 0 }"`             |
| `reactive:store="name"` | `x-data="Alpine.store('name')"` |

---

### `bind:` — Data Binding

```html
<span bind:text="count">0</span>              <!-- x-text -->
<div bind:html="richContent"></div>             <!-- x-html -->
<div bind:show="isVisible"></div>               <!-- x-show -->
<input bind:model="name" />                     <!-- x-model -->
<input bind:model.lazy="email" />               <!-- x-model.lazy -->
<input bind:model.number="age" />               <!-- x-model.number -->
<input bind:model.debounce.500ms="search" />    <!-- x-model.debounce.500ms -->
<div bind:class="{ 'active': isActive }"></div> <!-- :class -->
<div bind:style="{ color: textColor }"></div>   <!-- :style -->
<img bind:src="imageUrl" />                     <!-- :src -->
<a bind:href="link"></a>                        <!-- :href -->
<button bind:disabled="!isValid"></button>      <!-- :disabled -->
<div bind:id="'item-' + id"></div>              <!-- :id -->

<!-- Cloak (evita flash de conteúdo não-renderizado) -->
<div bind:cloak></div>                          <!-- x-cloak -->

<!-- Ref (referência ao elemento) -->
<input bind:ref="searchInput" />                <!-- x-ref -->

<!-- Transition -->
<div bind:transition></div>                     <!-- x-transition -->
<div bind:transition.opacity></div>             <!-- x-transition.opacity -->
<div bind:transition.duration.500ms></div>      <!-- x-transition.duration.500ms -->

<!-- Init (executa ao inicializar) -->
<div bind:init="fetchData()"></div>             <!-- x-init -->
```

| Escrito                         | Compilado                    |
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

---

## 8. Eventos

### `on:` — Event Handlers (Alpine.js client-side)

```html
<!-- Básico -->
<button on:click="count++">+</button>
<button on:click="handleClick()">Click</button>

<!-- Modifiers -->
<form on:submit.prevent="save()">
<a on:click.prevent.stop="navigate()">
<div on:click.outside="open = false">
<input on:keydown.enter="submit()">
<input on:keydown.escape="cancel()">
<div on:scroll.window="handleScroll()">

<!-- Timing modifiers -->
<button on:click.throttle.500ms="save()">
<input on:input.debounce.300ms="search()">
<button on:click.once="init()">

<!-- Self (apenas se o target for o próprio elemento) -->
<div on:click.self="close()">
```

| Escrito                       | Compilado                   |
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

## 9. HTMX — Server Interaction

### `action:` — Verbos HTTP

```html
<button action:get="/api/items">Carregar</button>
<form action:post="/api/items">Criar</form>
<button action:put="/api/items/1">Atualizar</button>
<button action:patch="/api/items/1/toggle">Toggle</button>
<button action:delete="/api/items/1">Deletar</button>
```

| Escrito                | Compilado          |
| ---------------------- | ------------------ |
| `action:get="/url"`    | `hx-get="/url"`    |
| `action:post="/url"`   | `hx-post="/url"`   |
| `action:put="/url"`    | `hx-put="/url"`    |
| `action:patch="/url"`  | `hx-patch="/url"`  |
| `action:delete="/url"` | `hx-delete="/url"` |

---

### Swap / Target / Trigger

```html
<div swap="innerHTML">            <!-- default -->
<div swap="outerHTML">             <!-- substitui o elemento inteiro -->
<div swap="beforebegin">           <!-- insere antes do elemento -->
<div swap="afterbegin">            <!-- insere no início (primeiro filho) -->
<div swap="beforeend">             <!-- insere no final (último filho) -->
<div swap="afterend">              <!-- insere depois do elemento -->
<div swap="delete">                <!-- remove o elemento -->
<div swap="none">                  <!-- sem swap (fire-and-forget) -->

<!-- Com modifiers -->
<div swap="innerHTML transition:true">
<div swap="innerHTML settle:300ms">
<div swap="innerHTML scroll:top">
<div swap="innerHTML show:top">
<div swap="innerHTML focus-scroll:true">

<!-- Target -->
<button target="#result">          <!-- onde colocar a resposta -->
<button target="closest li">      <!-- CSS selector relativo -->
<button target="next .panel">
<button target="previous .item">
<button target="find .content">   <!-- dentro do elemento -->

<!-- Trigger -->
<div trigger="load">               <!-- dispara ao carregar -->
<div trigger="revealed">           <!-- dispara quando visível (viewport) -->
<div trigger="intersect">          <!-- IntersectionObserver -->
<div trigger="every 5s">           <!-- polling -->
<input trigger="input changed delay:300ms">
<form trigger="submit">
<div trigger="click[ctrlKey]">     <!-- com filtro JS -->

<!-- Select (qual parte da resposta usar) -->
<div select=".content">            <!-- pega só .content da resposta -->
<div select-oob="#sidebar">        <!-- OOB swap adicional -->

<!-- Into (shorthand para target + swap) -->
<button into="#result">             <!-- hx-target="#result" hx-swap="innerHTML" -->
<button into="#result:outerHTML">   <!-- hx-target="#result" hx-swap="outerHTML" -->
```

| Escrito                          | Compilado                              |
| -------------------------------- | -------------------------------------- |
| `swap="x"`                       | `hx-swap="x"`                          |
| `target="x"`                     | `hx-target="x"`                        |
| `trigger="x"`                    | `hx-trigger="x"`                       |
| `select="x"`                     | `hx-select="x"`                        |
| `select-oob="x"`                 | `hx-select-oob="x"`                    |
| `confirm="x"`                    | `hx-confirm="x"`                       |
| `indicator="x"`                  | `hx-indicator="x"`                     |
| `push-url`                       | `hx-push-url="true"`                   |
| `push-url="/path"`               | `hx-push-url="/path"`                  |
| `replace-url`                    | `hx-replace-url="true"`                |
| `vals='{"k":"v"}'`               | `hx-vals='{"k":"v"}'`                  |
| `headers='{"X-Custom":"v"}'`     | `hx-headers='{"X-Custom":"v"}'`        |
| `encoding="multipart/form-data"` | `hx-encoding="multipart/form-data"`    |
| `preserve`                       | `hx-preserve="true"`                   |
| `sync="closest form:abort"`      | `hx-sync="closest form:abort"`         |
| `disabled-elt="this"`            | `hx-disabled-elt="this"`               |
| `into="#sel"`                    | `hx-target="#sel" hx-swap="innerHTML"` |
| `into="#sel:outerHTML"`          | `hx-target="#sel" hx-swap="outerHTML"` |

---

### Trigger Modifiers Compostos

```html
<!-- once — dispara apenas uma vez -->
<div trigger="load once">
<button trigger="click once">

<!-- delay -->
<input trigger="input changed delay:500ms">

<!-- throttle -->
<button trigger="click throttle:1s">

<!-- queue -->
<button trigger="click queue:first">
<button trigger="click queue:last">
<button trigger="click queue:all">

<!-- from (escutar evento de outro elemento) -->
<div trigger="click from:#other-button">

<!-- Combinar triggers -->
<div trigger="load, click, keyup[key=='Enter'] from:body">
```

| Escrito            | Compilado                                 |
| ------------------ | ----------------------------------------- |
| `once`             | adiciona `once` ao `hx-trigger`           |
| `debounce="500ms"` | adiciona `delay:500ms` ao `hx-trigger`    |
| `throttle="500ms"` | adiciona `throttle:500ms` ao `hx-trigger` |

---

### `boost` — Boost (Progressive Enhancement)

```html
<!-- Transforma links/forms em AJAX automaticamente -->
<nav boost>
    <a href="/about">About</a>    <!-- vira hx-get="/about" -->
    <a href="/contact">Contact</a>
</nav>

<form boost action="/submit" method="post">
    <!-- vira hx-post="/submit" -->
</form>
```

| Escrito | Compilado         |
| ------- | ----------------- |
| `boost` | `hx-boost="true"` |

---

## 10. SSE — Server-Sent Events

Requires `sse-starlette` dependency. Layouts must load the HTMX SSE extension
(`htmx-ext-sse@2`) via a `<script>` tag.

```html
<!-- Conectar a um endpoint SSE -->
<div live="/events/dashboard">
    <!-- Receber eventos específicos -->
    <span channel="user-count">0</span>
    <div channel="notifications" swap="beforeend"></div>
    <div channel="stats-update" swap="outerHTML"></div>
</div>

<!-- Fechar conexão em condição -->
<div live="/events/chat" close="closeChat">
```

| Escrito                    | Compilado                         |
| -------------------------- | --------------------------------- |
| `live="/url"`              | `hx-ext="sse" sse-connect="/url"` |
| `channel="event"`          | `sse-swap="event"`                |
| `channel="event" swap="x"` | `sse-swap="event" hx-swap="x"`    |
| `close="event"`            | `sse-close="event"`               |

---

## 11. WebSocket

```html
<!-- Conectar via WebSocket -->
<div socket="/ws/chat">
    <div channel="message" swap="beforeend"></div>
    <form send="message">
        <input name="text" />
    </form>
</div>
```

| Escrito         | Compilado                       |
| --------------- | ------------------------------- |
| `socket="/url"` | `hx-ext="ws" ws-connect="/url"` |
| `send="event"`  | `ws-send="event"`               |

---

## 12. Loading States

```html
<!-- Indicator global -->
<button action:post="/api/save"
        indicator="#spinner">
    Salvar
</button>
<span id="spinner" class="htmx-indicator">⏳</span>

<!-- Indicator inline com DSL -->
<button action:post="/api/save" loading>
    <span loading:hide>Salvar</span>
    <span loading:show>Salvando...</span>
</button>

<!-- Classes durante request -->
<button action:post="/api/save"
        loading:class="opacity-50 cursor-wait"
        loading:disabled>
    Salvar
</button>

<!-- Desabilitar durante request -->
<button action:post="/api/save"
        disabled-elt="this">
    Salvar
</button>

<!-- Skeleton loading -->
<div action:get="/api/data"
     trigger="load"
     loading:aria-busy="true">
    <div class="skeleton"></div>
</div>
```

| Escrito                    | Compilado                          |
| -------------------------- | ---------------------------------- |
| `loading`                  | Adiciona classe `htmx-indicator`   |
| `loading:show`             | Elemento visível durante request   |
| `loading:hide`             | Elemento escondido durante request |
| `loading:class="x"`        | Adiciona classes durante request   |
| `loading:disabled`         | `disabled` durante request         |
| `loading:aria-busy="true"` | `aria-busy` durante request        |
| `disabled-elt="this"`      | `hx-disabled-elt="this"`           |

---

## 13. Forms

```html
<!-- Form reativo com validação client-side -->
<form action:post="/api/users"
      swap="outerHTML"
      reactive="{ valid: false }">

    <input name="name"
           bind:model="name"
           required
           minlength="3"
           on:input="valid = $el.form.checkValidity()" />

    <input name="email"
           bind:model="email"
           type="email"
           required />

    <button type="submit"
            bind:disabled="!valid"
            loading:class="opacity-50"
            disabled-elt="this">
        <span loading:hide>Criar usuário</span>
        <span loading:show>Criando...</span>
    </button>
</form>

<!-- Upload de arquivo -->
<form action:post="/api/upload"
      encoding="multipart/form-data"
      swap="none">
    <input type="file" name="file" />
    <button type="submit">Upload</button>
</form>
```

---

## 14. CSS Scoping

```html
---
import Button from "./Button.jinja"
props { type: str = "info" }
---

<!-- Estilos com escopo automático (atributo data-pjx-HASH no componente) -->
<style scoped>
  .alert { padding: 1rem; border-radius: 8px; }
  .alert-success { background: #d1fae5; color: #065f46; }
  .alert-error { background: #fee2e2; color: #991b1b; }
</style>

<div class="alert alert-{{ props.type }}">
    {{ children }}
</div>
```

---

## 15. Asset Includes — JS, CSS e Arquivos Estáticos

Componentes podem declarar dependências de arquivos externos (scripts, folhas
de estilo, fontes) usando tags `<script>` e `<link>` no body. O PJX coleta
todas as dependências e as deduplica no HTML final.

### Include de CSS externo

```html
<link rel="stylesheet" href="/static/css/datepicker.css" />
```

### Include de JS externo

```html
<script src="/static/vendor/chart.js" defer></script>
```

### Estrutura de diretórios para assets

```text
project-root/
├── templates/
│   ├── pages/           # Páginas (extends layouts)
│   ├── components/      # Componentes reutilizáveis
│   ├── layouts/         # Layouts base
│   └── ui/              # Biblioteca de UI
├── static/
│   ├── vendor/          # JS/CSS de terceiros (Alpine, HTMX, etc.)
│   │   ├── alpine.min.js
│   │   └── htmx.min.js
│   ├── css/             # CSS compilado (Tailwind, bundles PJX)
│   │   └── pjx-components.css
│   ├── js/              # JS do projeto
│   └── images/          # Imagens e outros assets
├── pjx.toml             # Configuração do projeto
└── app.py               # Aplicação FastAPI
```

### Layout base com includes

O layout base (`templates/layouts/Base.jinja`) é responsável por incluir os
assets globais (Alpine.js, HTMX, CSS base). Páginas extendem esse layout:

```html
<!-- templates/layouts/Base.jinja -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{{ seo.title|default(title)|default("PJX App") }}</title>
  <link rel="icon" href="{{ favicon|default('/static/images/favicon.svg') }}" type="image/svg+xml" />

  {# SEO meta tags #}
  {% if seo.description %}<meta name="description" content="{{ seo.description }}" />{% endif %}
  {% if seo.og_title or seo.title %}<meta property="og:title" content="{{ seo.og_title|default(seo.title) }}" />{% endif %}
  {% if seo.og_description or seo.description %}<meta property="og:description" content="{{ seo.og_description|default(seo.description) }}" />{% endif %}

  {# Stylesheets #}
  <link rel="stylesheet" href="/static/css/base.css" />
  {% for css in head_css|default([]) %}
    <link rel="stylesheet" href="{{ css }}" />
  {% endfor %}

  {# Scripts #}
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
  <script src="https://unpkg.com/htmx.org@2/dist/htmx.min.js"></script>
  {% for js in head_scripts|default([]) %}
    <script src="{{ js }}"></script>
  {% endfor %}
</head>
<body>
  {{ body|default("") }}
  {% for js in body_scripts|default([]) %}
    <script src="{{ js }}"></script>
  {% endfor %}
  <script src="/static/js/app.js"></script>
</body>
</html>
```

### Componente com assets próprios

Componentes podem incluir scripts e estilos inline ou externos. O `<script>`
no body é passado direto para o HTML (não é processado pelo frontmatter):

```html
---
props {
  data: list = [],
  type: str = "bar",
}
---

<style scoped>
.chart-container { width: 100%; height: 300px; }
</style>

<div class="chart-container">
  <canvas id="chart-{{ props.type }}"></canvas>
</div>

<script src="/static/js/chart-init.js" defer></script>
```

### `pjx build` e bundling de CSS

O comando `pjx build` compila todos os componentes e gera um bundle CSS
unificado em `static/css/pjx-components.css` contendo todos os estilos
scoped. Esse arquivo pode ser incluído no layout base.

### Configuração de diretórios (`pjx.toml`)

```toml
engine = "hybrid"
debug = true

template_dirs = ["templates"]
static_dir = "static"
```

---

## 16. Tabela Completa de Compilação

### Control Flow

| DSL                                                                    | Jinja2                                          |
| ---------------------------------------------------------------------- | ----------------------------------------------- |
| `<Show when="x">body</Show>`                                           | `{% if x %}body{% endif %}`                     |
| `<Show when="x" fallback="fb">body</Show>`                             | `{% if x %}body{% else %}fb{% endif %}`         |
| `<For each="xs" as="x">body</For>`                                     | `{% for x in xs %}body{% endfor %}`             |
| `<For each="xs" as="x">body<Empty>fb</Empty></For>`                    | `{% for x in xs %}body{% else %}fb{% endfor %}` |
| `<Switch on="v"><Case value="a">A</Case><Default>?</Default></Switch>` | `{% if v=="a" %}A{% else %}?{% endif %}`        |
| `<ErrorBoundary fallback="fb">body</ErrorBoundary>`                    | `try/except` wrapper                            |
| `<Fragment>body</Fragment>`                                            | `body` (sem wrapper)                            |
| `<Portal target="id">body</Portal>`                                    | `<div id="id" hx-swap-oob="true">body</div>`    |
| `<Component is="name" />`                                              | Renderização dinâmica por nome                  |
| `<Await src="/url">`                                                   | `<div hx-get="/url" hx-trigger="load">`         |

### Variáveis

| DSL                 | Efeito                                 |
| ------------------- | -------------------------------------- |
| `let x = val`       | `{% set x = val %}` (server)           |
| `const X = val`     | `{% set X = val %}` (imutável, server) |
| `state x = val`     | Alpine `x-data` inclui `x: val`        |
| `computed x = expr` | `{% set x = expr %}` + reativo         |

### Alpine (client)

| DSL                             | HTML                         |
| ------------------------------- | ---------------------------- |
| `reactive`                      | `x-data="{{ alpine_data }}"` |
| `reactive="{ x: 0 }"`           | `x-data="{ x: 0 }"`          |
| `bind:text="x"`                 | `x-text="x"`                 |
| `bind:html="x"`                 | `x-html="x"`                 |
| `bind:show="x"`                 | `x-show="x"`                 |
| `bind:model="x"`                | `x-model="x"`                |
| `bind:model.lazy="x"`           | `x-model.lazy="x"`           |
| `bind:model.number="x"`         | `x-model.number="x"`         |
| `bind:model.debounce.500ms="x"` | `x-model.debounce.500ms="x"` |
| `bind:{attr}="x"`               | `:{attr}="x"`                |
| `bind:cloak`                    | `x-cloak`                    |
| `bind:ref="x"`                  | `x-ref="x"`                  |
| `bind:transition`               | `x-transition`               |
| `bind:init="x"`                 | `x-init="x"`                 |
| `on:event="x"`                  | `@event="x"`                 |
| `on:event.modifier="x"`         | `@event.modifier="x"`        |

### HTMX (server)

| DSL                    | HTML                    |
| ---------------------- | ----------------------- |
| `action:get="/url"`    | `hx-get="/url"`         |
| `action:post="/url"`   | `hx-post="/url"`        |
| `action:put="/url"`    | `hx-put="/url"`         |
| `action:patch="/url"`  | `hx-patch="/url"`       |
| `action:delete="/url"` | `hx-delete="/url"`      |
| `swap="x"`             | `hx-swap="x"`           |
| `target="x"`           | `hx-target="x"`         |
| `trigger="x"`          | `hx-trigger="x"`        |
| `select="x"`           | `hx-select="x"`         |
| `select-oob="x"`       | `hx-select-oob="x"`     |
| `confirm="x"`          | `hx-confirm="x"`        |
| `indicator="x"`        | `hx-indicator="x"`      |
| `push-url`             | `hx-push-url="true"`    |
| `replace-url`          | `hx-replace-url="true"` |
| `vals='json'`          | `hx-vals='json'`        |
| `headers='json'`       | `hx-headers='json'`     |
| `encoding="x"`         | `hx-encoding="x"`       |
| `preserve`             | `hx-preserve="true"`    |
| `sync="x"`             | `hx-sync="x"`           |
| `disabled-elt="x"`     | `hx-disabled-elt="x"`   |
| `boost`                | `hx-boost="true"`       |

### SSE / WebSocket

| DSL               | HTML                              |
| ----------------- | --------------------------------- |
| `live="/url"`     | `hx-ext="sse" sse-connect="/url"` |
| `channel="event"` | `sse-swap="event"`                |
| `close="event"`   | `sse-close="event"`               |
| `socket="/url"`   | `hx-ext="ws" ws-connect="/url"`   |
| `send="event"`    | `ws-send="event"`                 |

---

## 17. Exemplo Completo — Dashboard

```html
---
import { Card, Badge, Avatar } from "./ui/"
import DataTable from "./DataTable.jinja"
import Chart from "./Chart.jinja"
import Modal from "./Modal.jinja"

props {
  user:    dict,
  stats:   list[dict],
  orders:  list[dict],
  team:    list[dict],
}

slot header
slot sidebar

let total_revenue = sum(o.amount for o in props.orders)
let active_orders = [o for o in props.orders if o.status == "active"]

state selected_order = null
state show_modal = false
state filter = "all"
state search = ""

computed filtered_orders = active_orders if filter == "active" else props.orders
---

<style scoped>
  .dashboard { display: grid; grid-template-columns: 1fr 300px; gap: 1.5rem; }
  .stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
</style>

<div class="dashboard" reactive>

    <!-- Header slot -->
    <Slot:header>
        <header>
            <h1>Dashboard</h1>
            <p>Bem-vindo, {{ props.user.name }}</p>
        </header>
    </Slot:header>

    <!-- Stats com SSE live -->
    <section class="stat-grid" live="/events/stats" channel="stats-update">
        <For each="props.stats" as="stat">
            <Card variant="stat">
                <span class="stat-value">{{ stat.value }}</span>
                <span class="stat-label">{{ stat.label }}</span>
                <Switch on="stat.trend">
                    <Case value="up">
                        <Badge text="↑ {{ stat.delta }}%" variant="success" />
                    </Case>
                    <Case value="down">
                        <Badge text="↓ {{ stat.delta }}%" variant="danger" />
                    </Case>
                    <Default></Default>
                </Switch>
            </Card>
        </For>
    </section>

    <!-- Main content -->
    <main>
        <!-- Search & Filter -->
        <div class="toolbar">
            <input type="search"
                   placeholder="Buscar pedidos..."
                   bind:model.debounce.300ms="search"
                   action:get="/api/orders"
                   trigger="input changed delay:300ms"
                   target="#orders-table"
                   swap="innerHTML" />

            <div class="filter-group">
                <For each="['all', 'active', 'completed', 'cancelled']" as="f">
                    <button bind:class="filter === '{{ f }}' && 'active'"
                            on:click="filter = '{{ f }}'"
                            action:get="/api/orders?filter={{ f }}"
                            target="#orders-table"
                            swap="innerHTML">
                        {{ f | capitalize }}
                    </button>
                </For>
            </div>
        </div>

        <!-- Orders Table -->
        <DataTable id="orders-table"
                   rows="{{ filtered_orders }}"
                   searchable="true"
                   paginated="true">
            <slot:empty>
                <p class="empty">Nenhum pedido encontrado.</p>
            </slot:empty>
        </DataTable>

        <!-- Chart -->
        <Show when="props.orders">
            <Chart type="line"
                   data="{{ props.orders }}"
                   x="date"
                   y="amount"
                   title="Receita" />
        </Show>
    </main>

    <!-- Sidebar -->
    <aside>
        <Slot:sidebar>
            <h3>Equipe Online</h3>
            <For each="props.team" as="member">
                <div class="team-member"
                     on:click="selected_order = null"
                     action:get="/api/users/{{ member.id }}"
                     target="#user-detail"
                     swap="innerHTML">
                    <Avatar src="{{ member.avatar }}" size="32" />
                    <span>{{ member.name }}</span>
                    <Switch on="member.status">
                        <Case value="online">
                            <Badge text="●" variant="success" />
                        </Case>
                        <Case value="away">
                            <Badge text="●" variant="warning" />
                        </Case>
                        <Default>
                            <Badge text="●" variant="muted" />
                        </Default>
                    </Switch>
                </div>
            <Empty>
                <p>Ninguém online.</p>
            </Empty>
            </For>
            <div id="user-detail"></div>
        </Slot:sidebar>
    </aside>

    <!-- Modal -->
    <Show when="show_modal">
        <Modal title="Detalhes do Pedido">
            <div id="order-detail"
                 live="/events/order"
                 channel="order-update">
                Selecione um pedido.
            </div>
            <slot:footer>
                <button on:click="show_modal = false">Fechar</button>
                <button action:post="/api/orders/approve"
                        swap="none"
                        loading:disabled
                        loading:class="opacity-50">
                    <span loading:hide>Aprovar</span>
                    <span loading:show>Aprovando...</span>
                </button>
            </slot:footer>
        </Modal>
    </Show>
</div>
```

---

## 18. Comparação com Frameworks

| Conceito    | PJX                     | SolidJS            | Svelte              | Vue                |
| ----------- | ----------------------- | ------------------ | ------------------- | ------------------ |
| Condicional | `<Show when="x">`       | `<Show when={x}>`  | `{#if x}`           | `v-if="x"`         |
| Loop        | `<For each="x" as="i">` | `<For each={x}>`   | `{#each x as i}`    | `v-for="i in x"`   |
| Switch      | `<Switch on="x">`       | `<Switch>/<Match>` | —                   | —                  |
| Slot        | `<Slot:name />`         | `props.children`   | `<slot name="">`    | `<slot name="">`   |
| Slot pass   | `<slot:name>`           | —                  | `<svelte:fragment>` | `<template #name>` |
| Reatividade | `state x = 0`           | `createSignal()`   | `let x = 0`         | `ref(0)`           |
| Computed    | `computed x = expr`     | `createMemo()`     | `$: x = expr`       | `computed()`       |
| Binding     | `bind:model="x"`        | —                  | `bind:value={x}`    | `v-model="x"`      |
| Evento      | `on:click="fn()"`       | `onClick={fn}`     | `on:click={fn}`     | `@click="fn()"`    |
| HTTP        | `action:post="/url"`    | `fetch()`          | `fetch()`           | `axios`            |
| SSE         | `live="/url"`           | custom             | custom              | custom             |
| CSS scoped  | `<style scoped>`        | CSS modules        | `<style>` (auto)    | `<style scoped>`   |

---

## 19. Layouts e Herança

PJX suporta dois mecanismos de layout:

1. **Runtime layout** via `PJX(layout=...)` — wrapa `{{ body }}` no template
2. **Template inheritance** via `extends` — herança estática no frontmatter

### Runtime Layout (`PJX(layout=...)`)

Definido na instância PJX, o layout runtime wrapa automaticamente todas as
páginas. O conteúdo renderizado é injetado na variável `{{ body }}`:

```python
from pjx import PJX, PJXConfig, SEO

pjx = PJX(
    app,
    config=PJXConfig(toml_path="pjx.toml"),
    layout="layouts/Base.jinja",
    seo=SEO(title="My App", description="Default description."),
)
```

O layout recebe todas as variáveis do contexto da página, mais:

| Variável         | Tipo     | Descrição                              |
| ---------------- | -------- | -------------------------------------- |
| `body`           | `Markup` | HTML renderizado da página             |
| `seo`            | `SEO`    | SEO merged (global + per-page)         |
| `head_css`       | `list`   | CSS extras para `<head>`               |
| `head_scripts`   | `list`   | JS extras para `<head>`                |
| `body_scripts`   | `list`   | JS extras antes de `</body>`           |
| `favicon`        | `str`    | Caminho do favicon                     |

Para desabilitar o layout em uma página específica:

```python
@pjx.page("/api-docs", layout=None)
async def api_docs():
    return {"raw": True}
```

### Template Inheritance (`extends`)

Layouts definem a estrutura base da página (html, head, body, nav, footer).
Páginas herdam de layouts via `extends`.

### Layout base

```html
---
props {
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

### Página que herda do layout

```html
---
extends "layouts/Base.jinja"
from pydantic import EmailStr

props {
  user: dict,
  items: list[dict],
}
---

<slot:head>
    <meta property="og:title" content="Home — {{ props.user.name }}" />
    <link rel="canonical" href="/" />
</slot:head>

<h1>Bem-vindo, {{ props.user.name }}</h1>
<For each="props.items" as="item">
    <p>{{ item.title }}</p>
</For>
```

O corpo da página (fora de `<slot:*>`) é automaticamente injetado no
`<Slot:content />` do layout.

---

## 20. Prop Spreading

Espalhar um dict como props de um componente.

```html
---
let btn_props = {
  variant: "primary",
  size: "lg",
  disabled: false,
}
---

<!-- Espalha todas as props -->
<Button ...btn_props />

<!-- Espalha + override -->
<Button ...btn_props label="Salvar" disabled="true" />
```

Props explícitos têm prioridade sobre o spread. O spread é resolvido em
compile-time se o valor é estático, ou em runtime se é dinâmico.

| Escrito                         | Compilado                                                  |
| ------------------------------- | ---------------------------------------------------------- |
| `<Button ...props />`           | Merge `props` com attrs explícitos, passa via `{% with %}` |
| `<Button ...props label="x" />` | `label="x"` sobrescreve `props.label`                      |

---

## 21. Global State (Alpine Stores)

### Declarar store

```html
---
store todos = {
  items: [],
  filter: "all",
  add(text) { this.items.push({ text, done: false }) },
  toggle(index) { this.items[index].done = !this.items[index].done },
}
---
```

### Usar store em componentes

```html
<div reactive:store="todos">
    <input bind:model="$store.todos.filter" />
    <For each="$store.todos.items" as="item">
        <li>{{ item.text }}</li>
    </For>
</div>
```

| Escrito                       | Compilado                                          |
| ----------------------------- | -------------------------------------------------- |
| `store name = { ... }`        | `Alpine.store('name', { ... })` no script de init  |
| `reactive:store="name"`       | `x-data="Alpine.store('name')"`                    |
| `$store.name.prop`            | Acesso direto ao Alpine store                      |

Stores são inicializados via `<script>` gerado no layout base, alimentados
com dados do servidor.

---

## 22. Funções Built-in nos Templates

Funções disponíveis em expressões dentro do template body:

| Função                  | Descrição                                      |
| ----------------------- | ---------------------------------------------- |
| `has_slot('name')`      | `true` se o slot `name` foi fornecido pelo pai |
| `len(x)`                | Comprimento de lista/string                    |
| `range(n)`              | Gera sequência 0..n-1                          |
| `enumerate(x)`          | Pares (index, item)                            |
| `url_for('route_name')` | Gera URL reversa para rota FastAPI             |
| `static('path')`        | Gera URL para arquivo estático                 |

```html
<Show when="has_slot('header')">
    <header><Slot:header /></header>
</Show>

<img src="{{ static('images/logo.png') }}" />
<a href="{{ url_for('user_profile', user_id=user.id) }}">Perfil</a>
```

---

## 23. Páginas de Erro

### Páginas customizadas

```html
---
extends "layouts/Base.jinja"

props {
  path: str,
}
---

<div class="error-page">
    <h1>404</h1>
    <p>Página <code>{{ props.path }}</code> não encontrada.</p>
    <a href="/">Voltar ao início</a>
</div>
```

### Registro via FastAPI

```python
@pjx.error(404, "errors/404.jinja")
async def not_found(request: Request):
    return {"path": request.url.path}

@pjx.error(500, "errors/500.jinja")
async def server_error(request: Request):
    return {}
```

---

## 24. Componentes Recursivos

Componentes podem importar a si mesmos para renderizar estruturas em árvore.

```html
---
import TreeNode from "./TreeNode.jinja"

props {
  node: dict,
  depth: int = 0,
  max_depth: int = 10,
}
---

<div class="tree-node" style="margin-left: {{ props.depth * 16 }}px">
    <span>{{ props.node.label }}</span>
    <Show when="props.node.children and props.depth < props.max_depth">
        <For each="props.node.children" as="child">
            <TreeNode
                node="{{ child }}"
                depth="{{ props.depth + 1 }}"
                max_depth="{{ props.max_depth }}" />
        </For>
    </Show>
</div>
```

O compilador detecta imports circulares e limita profundidade via
`max_depth` (padrão: 10). Ultrapassar o limite gera `CompileError`.

---

## 25. File-Based Routing

PJX suporta roteamento baseado no sistema de arquivos, inspirado em Next.js e
SvelteKit. O método `pjx.auto_routes()` escaneia o diretório `pages/` e gera
rotas FastAPI automaticamente.

### Ativação

```python
pjx = PJX(app, config=PJXConfig(toml_path="pjx.toml"))
pjx.auto_routes()
```

### Convenções de arquivo

| Padrão de arquivo              | Rota gerada                  | Descrição                         |
| ------------------------------ | ---------------------------- | --------------------------------- |
| `pages/index.jinja`            | `/`                          | Página raiz                       |
| `pages/about.jinja`            | `/about`                     | Rota estática                     |
| `pages/blog/index.jinja`       | `/blog`                      | Index de diretório                |
| `pages/blog/[slug].jinja`      | `/blog/{slug}`               | Parâmetro dinâmico                |
| `pages/docs/[...slug].jinja`   | `/docs/{slug:path}`          | Catch-all (segmentos variáveis)   |
| `pages/(auth)/login.jinja`     | `/login`                     | Route group (sem prefixo na URL)  |
| `pages/layout.jinja`           | —                            | Layout compartilhado              |
| `pages/loading.jinja`          | —                            | Skeleton de carregamento          |
| `pages/error.jinja`            | —                            | Página de erro do diretório       |

### Arquivos especiais

- **`layout.jinja`** — Wrapa automaticamente todas as páginas e sub-diretórios
  do mesmo nível. Layouts aninhados: `pages/layout.jinja` wrapa
  `pages/blog/layout.jinja` que wrapa `pages/blog/[slug].jinja`.
- **`loading.jinja`** — Skeleton exibido via HTMX `hx-indicator` enquanto a
  página carrega.
- **`error.jinja`** — Renderizado quando um handler retorna erro. Recebe
  `status_code` e `message` no contexto.
- **Route groups `(name)/`** — Diretórios entre parênteses agrupam páginas sem
  afetar a URL. Útil para aplicar layouts/middleware a um subset de rotas.

### Colocated Handlers

Handlers Python podem ser colocados ao lado dos templates usando
`RouteHandler` e `APIRoute`:

```python
from pjx.routing import RouteHandler, APIRoute

handler = RouteHandler()

@handler.get
async def get():
    return {"items": await fetch_items()}

@handler.post
async def post(form: Annotated[ItemForm, FormData()]):
    await create_item(form)
    return {"items": await fetch_items()}

# Endpoint JSON servido sob /api/
api = APIRoute()

@api.get
async def list_items():
    return {"items": await fetch_items()}
```

---

## 26. Middleware

### Declaração no frontmatter

Componentes e páginas podem declarar middleware:

```html
---
middleware "auth", "rate_limit"
---
```

Aceita uma ou mais strings separadas por vírgula. Cada string referencia um
middleware registrado no runtime PJX.

### Registro no runtime

```python
@pjx.middleware("auth")
async def auth_middleware(request: Request, call_next):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401)
    response = await call_next(request)
    return response

@pjx.middleware("rate_limit")
async def rate_limit_middleware(request: Request, call_next):
    response = await call_next(request)
    return response
```

Middleware declarado no frontmatter é aplicado na ordem de declaração.
Middleware de layout é aplicado antes do middleware da página.

---

## 27. Layout Components (Built-ins)

PJX inclui componentes de layout built-in inspirados em Chakra UI. São
compilados diretamente pelo compilador (sem necessidade de import).

| Componente      | Descrição                                      | Props principais                      |
| --------------- | ---------------------------------------------- | ------------------------------------- |
| `<Center>`      | Centraliza conteúdo horizontal e verticalmente | `w`, `h`                              |
| `<HStack>`      | Stack horizontal com gap                       | `gap`, `align`, `justify`, `wrap`     |
| `<VStack>`      | Stack vertical com gap                         | `gap`, `align`, `justify`             |
| `<Grid>`        | Grid CSS responsivo                            | `cols`, `gap`, `min`, `max`           |
| `<Spacer>`      | Espaço flexível entre itens                    | —                                     |
| `<Container>`   | Largura máxima centralizada                    | `max`, `px`                           |
| `<Divider>`     | Linha divisória                                | `orientation`, `color`                |
| `<Wrap>`        | Flex wrap com gap                              | `gap`, `align`, `justify`             |
| `<AspectRatio>` | Mantém proporção do conteúdo                   | `ratio`                               |
| `<Hide>`        | Oculta conteúdo por breakpoint                 | `below`, `above`                      |

### Exemplo

```html
<Container max="1200px">
  <VStack gap="1rem">
    <HStack gap="0.5rem" justify="space-between">
      <h1>Dashboard</h1>
      <Spacer />
      <Button label="Settings" />
    </HStack>
    <Divider />
    <Grid cols="3" gap="1rem" min="300px">
      <Card title="Users" />
      <Card title="Revenue" />
      <Card title="Orders" />
    </Grid>
    <Hide below="md">
      <AspectRatio ratio="16/9">
        <img src="/chart.png" />
      </AspectRatio>
    </Hide>
  </VStack>
</Container>
```

### Compilação

| DSL                          | HTML compilado                                                            |
| ---------------------------- | ------------------------------------------------------------------------- |
| `<Center>`                   | `<div style="display:flex;align-items:center;justify-content:center">`    |
| `<HStack gap="1rem">`        | `<div style="display:flex;flex-direction:row;gap:1rem">`                  |
| `<VStack gap="1rem">`        | `<div style="display:flex;flex-direction:column;gap:1rem">`               |
| `<Grid cols="3" gap="1rem">` | `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem">` |
| `<Spacer />`                 | `<div style="flex:1">`                                                    |
| `<Container max="1200px">`   | `<div style="max-width:1200px;margin:0 auto">`                            |
| `<Hide below="md">`          | `<div class="pjx-hide-below-md">`                                         |
| `<AspectRatio ratio="16/9">` | `<div style="aspect-ratio:16/9">`                                         |

---

## 28. Frontmatter — Regras de Parsing

O frontmatter é delimitado por `---` na **primeira linha** e fechado pelo
próximo `---` em uma linha isolada. Regras:

- `---` deve estar **sozinho na linha** (sem espaços antes/depois)
- Strings dentro do frontmatter podem conter `---` sem ambiguidade:
  `let x = "foo --- bar"` é válido
- Comentários: `#` até o fim da linha (ignorados pelo lexer)
- Linhas em branco são ignoradas
- Multi-line: props blocks (`{ ... }`) podem ocupar várias linhas
- O `---` de fechamento marca o início do body HTML + `<style scoped>`

```text
---                       ← abertura (linha 1 do arquivo)
import ...
from pydantic import ...
extends "..."
props [Name =] { ... }
slot ...
let/const/state/computed
store ...
css "path/to/style.css"
js "path/to/script.js"
middleware "name", ...
---                       ← fechamento (próximo --- isolado)
<style scoped>...</style> ← opcional
<div>...</div>            ← body HTML
```

### Assets no Frontmatter

Componentes podem declarar dependências de CSS e JS:

```html
---
css "components/card.css"
js "components/card.js"
---
```

Assets são coletados recursivamente (incluindo imports), deduplicados por
`(kind, path)`, e disponibilizados no template via `{{ pjx_assets.render() }}`.
CSS é renderizado como `<link>`, JS como `<script type="module">`.
