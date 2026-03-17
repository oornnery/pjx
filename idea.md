# pjx — Especificação v1

## Objetivo

Criar uma camada de templates moderna sobre Jinja2, inspirada em TSX/JX/Solid, mas com foco em:

* SSR-first
* progressive enhancement
* integração natural com HTMX e Alpine
* sintaxe curta e previsível
* baixo custo de compilação
* fácil adoção por quem já usa Jinja

---

## Princípios de Design

1. O arquivo deve parecer principalmente HTML/template, não um arquivo de configuração.
2. A linguagem deve ter poucas primitivas e pouco ruído.
3. Tudo que puder ser biblioteca/helper não deve virar sintaxe do compilador.
4. O modelo de estado do cliente e do servidor deve ser claramente separado.
5. A forma simples deve ser o padrão; a forma avançada deve ser opcional.

---

## Heurística de Design

Antes de adicionar qualquer recurso novo, validar:

1. isso reduz boilerplate real ou só adiciona cerimônia?
2. isso precisa ser sintaxe da linguagem ou pode ser componente/helper?
3. isso mantém o arquivo parecido com template/HTML?
4. isso compila bem para Jinja sem mágica excessiva?

---

## Linguagem

### Modos de Arquivo

#### Modo simples

Quando o arquivo possui **um único componente principal**, o corpo do arquivo já representa esse componente. Não precisa de `@component`.

```pjx
@props {
  title: str
  subtitle: str = ""
}

<div class="card">
  <h2>{{ title }}</h2>
  <Show when="{{ subtitle }}">
    <p>{{ subtitle }}</p>
  </Show>
</div>
```

#### Modo avançado

Quando o arquivo possui **múltiplos componentes locais**, usar blocos nomeados com `@component Nome { ... }`. Componentes locais podem ser usados como `<Nome />` dentro do mesmo arquivo.

```pjx
@component Card {
  @props {
    title: str
  }

  <div class="card">
    <h2>{{ title }}</h2>
    <slot />
  </div>
}

@component Page {
  @props {
    name: str
  }

  <Card title="Olá">
    <p>{{ name }}</p>
  </Card>
}
```

**Regra:**

* 1 componente por arquivo → sem `@component`
* 2+ componentes locais → `@component Nome { ... }`

---

### Diretivas Top-Level

#### `@props`

Declara props tipadas do componente atual.

```pjx
@props {
  name: str
  email: str
  avatar: str = "/default.png"
  role: "admin" | "user" | "guest" = "user"
  tags: list[str] = []
}
```

Vantagens: documentação do componente, validação, autocomplete/editor tooling, ergonomia próxima de TSX sem depender de JS.

#### `@slot`

Declara slots esperados pelo componente.

```pjx
@slot default
@slot header?
@slot footer?
```

O `?` indica slot opcional.

#### `@state`

Declara estado local client-side para Alpine. Compila para `x-data`.

```pjx
@state {
  open: false
  selected: null
}
```

#### `@bind`

Liga o template a uma classe Python.

```pjx
@bind from components.data_table import DataTable
```

#### `@component`

Declara um componente local nomeado dentro do mesmo arquivo. Dentro do bloco são permitidos: `@props`, `@slot`, `@state`, `@let`, markup/template, uso de outros componentes e estruturas `<Show>`, `<For>`, `<Switch>`.

```pjx
@component UserCard {
  @props {
    name: str
  }

  <div>{{ name }}</div>
}
```

#### `@let`

Declara variável local no escopo do componente. Compila para `{% set %}` do Jinja. Útil para evitar repetição de expressões e para nomear valores intermediários.

```pjx
@let total = items | length
@let label = "Mostrando {{ total }} resultado(s)"
@let is_empty = total == 0
```

Dentro de `@component`, `@let` pode aparecer junto com `@props` e `@state`:

```pjx
@component Summary {
  @props {
    items: list
  }

  @let total = items | length
  @let has_items = total > 0

  <div>
    <Show when="{{ has_items }}">
      <p>{{ total }} item(s)</p>
      <:fallback>
        <EmptyState title="Nenhum item" />
      </:fallback>
    </Show>
  </div>
}
```

**Escopo:** visível apenas dentro do bloco onde foi declarado (arquivo ou `@component`).

#### `@from`

Importa símbolos Python, componentes ou helpers.

```pjx
@from components.cards import Card
```

#### `@import`

Importa outro template/componente por caminho lógico.

```pjx
@import "components/Card.pjx"
```

---

### Estruturas de Controle

#### `<Show>`

Renderização condicional. Compila para `if/else` do Jinja.

```pjx
<Show when="{{ user }}">
  <p>Olá {{ user.name }}</p>

  <:fallback>
    <p>Faça login</p>
  </:fallback>
</Show>
```

**Props:** `when: str`
**Slots:** `default`, `fallback?`

#### `<For>`

Iteração sobre listas. Compila para `for/else` do Jinja.

```pjx
<For each="{{ users }}" as="user" index="i">
  <p>{{ i + 1 }}. {{ user.name }}</p>

  <:empty>
    <p>Nenhum usuário</p>
  </:empty>
</For>
```

**Props:** `each: str`, `as: str`, `index: str?`
**Slots:** `default`, `empty?`

#### `<Switch>` / `<Match>`

Ramificação múltipla. Compila para cadeia `if/elif/else`.

```pjx
<Switch on="{{ role }}">
  <Match value="admin"><AdminPanel /></Match>
  <Match value="user"><UserPanel /></Match>

  <:fallback>
    <GuestPanel />
  </:fallback>
</Switch>
```

**Props de `<Switch>`:** `on: str`
**Props de `<Match>`:** `value: str`
**Slots:** `default` (contendo `<Match>`), `fallback?`

---

### Sistema de Slots

#### Slots nomeados

Declaração no componente:

```pjx
@slot default
@slot header?
@slot footer?
```

Uso ao invocar o componente:

```pjx
<Card>
  <:header>
    <h2>Título</h2>
  </:header>

  <p>Conteúdo</p>

  <:footer>
    <Button>Salvar</Button>
  </:footer>
</Card>
```

#### Scoped slots

Declaração no template do componente:

```pjx
<div class="autocomplete">
  <For each="{{ filtered_items }}" as="item" index="i">
    <slot name="item" :item="item" :index="i">
      <span>{{ item }}</span>
    </slot>
  </For>
</div>
```

Uso:

```pjx
<Autocomplete items="{{ users }}">
  <:item let:item let:index>
    <div class="user-option">
      <span>{{ index + 1 }}. {{ item.name }}</span>
    </div>
  </:item>
</Autocomplete>
```

---

### Estado: Cliente vs Servidor

A separação é obrigatória para a linguagem continuar simples.

**Regra forte:**

* `.pjx @state` = Alpine / estado local de UI no cliente
* `python state()` = estado server-side

Não usar o mesmo conceito com semântica híbrida.

`@state` no `.pjx` compila para `x-data` do Alpine:

```pjx
@state {
  open: false
}

<div :data="{{ @state }}">
  <button @click.alpine="open = !open">Abrir</button>
  <div x-show="open" x-transition>
    <slot />
  </div>
</div>
```

Compila conceitualmente para:

```html
<div x-data="{ open: false }">
  <button @click="open = !open">Abrir</button>
  <div x-show="open" x-transition>
    ...
  </div>
</div>
```

`state()` na classe Python representa estado server-side (ver seção Python).

---

### Resolução de Nomes

Quando o compilador encontra uma tag em maiúsculo:

1. componente local declarado com `@component`
2. símbolo importado via `@from` ou `@import`
3. erro de compilação se não encontrado

Tags HTML nativas continuam sendo tratadas normalmente.

---

### Helpers de Template

Variáveis e funções especiais disponíveis automaticamente no escopo de qualquer template pjx. São injetadas pelo compilador/runtime — não precisam ser importadas.

#### `@id`

Identificador único gerado para cada instância do componente em runtime. Útil para vincular elementos HTMX ao componente correto sem conflito entre múltiplas instâncias na mesma página.

```pjx
<div id="table-{{ @id }}">
  <button @target="#table-{{ @id }}">Recarregar</button>
</div>
```

#### `@has_slot(name)`

Retorna `true` se o slot com o nome dado foi fornecido pelo chamador. Usado para renderização condicional de regiões opcionais.

```pjx
@slot actions?

<div class="card">
  <slot />

  <Show when="{{ @has_slot('actions') }}">
    <div class="card__actions">
      <slot name="actions" />
    </div>
  </Show>
</div>
```

**Assinatura:** `@has_slot(name: str) -> bool`

#### `@event_url(event, **params)`

Gera a URL para disparar um evento de um `Component` via HTMX. A URL inclui o identificador da instância e os parâmetros fornecidos.

```pjx
<input
  @input.htmx="get:{{ @event_url('search') }}"
  @trigger="input changed delay:300ms"
/>

<Pagination
  url="{{ @event_url('page', page='{page}') }}"
/>
```

**Assinatura:** `@event_url(event: str, **params) -> str`

O template `{page}` nos parâmetros é substituído pelo valor correto em cada link gerado pelo componente de paginação.

#### `@state`

Quando usado como valor de atributo (`:data="{{ @state }}"`), serializa o bloco `@state` declarado no componente como JSON para inicializar o `x-data` do Alpine.

```pjx
@state {
  open: false
  count: 0
}

<div :data="{{ @state }}">
  <!-- compila para: x-data='{"open": false, "count": 0}' -->
</div>
```

---

## Integrações

### HTMX

Sintaxe de diretivas:

```pjx
<button
  @click.htmx="delete:/todos/{{ todo.id }}"
  @swap="outerHTML"
  @target="#todo-{{ todo.id }}"
  @confirm="Tem certeza?"
>
  Remover
</button>
```

Mapeamento completo:

* `@click.htmx="get:/url"` → `hx-get="/url" hx-trigger="click"`
* `@click.htmx="post:/url"` → `hx-post="/url" hx-trigger="click"`
* `@click.htmx="delete:/url"` → `hx-delete="/url" hx-trigger="click"`
* `@submit.htmx="post:/url"` → `hx-post="/url" hx-trigger="submit"`
* `@swap="outerHTML"` → `hx-swap="outerHTML"`
* `@target="#id"` → `hx-target="#id"`
* `@confirm="msg"` → `hx-confirm="msg"`
* `@indicator="#id"` → `hx-indicator="#id"`
* `@trigger="input changed delay:300ms"` → `hx-trigger="input changed delay:300ms"`
* `@push_url="true"` → `hx-push-url="true"`
* `@select="#fragment"` → `hx-select="#fragment"`
* `@vals='{"key": "value"}'` → `hx-vals='{"key": "value"}'`

### Alpine.js

A linguagem mantém Alpine quase nativo, com o mínimo de açúcar sintático. O ideal é ficar próximo do Alpine puro.

```pjx
@state {
  open: false
  selected: null
}

<div :data="{{ @state }}">
  <button @click.alpine="open = !open">Abrir</button>
  <div x-show="open" x-transition>
    <slot />
  </div>
</div>
```

---

## Python: Componentes com Classe

Componentes com lógica mais séria devem usar uma classe Python ligada com `@bind`.

A combinação recomendada é:

* `.pjx` para estrutura e template
* `.py` para estado server-side, computed, eventos, fetch, lógica de negócio

```python
from pjx import Component, prop, state, computed, event

class DataTable(Component):
    template = "components/DataTable.pjx"

    endpoint: str = prop()
    page_size: int = prop(default=20)
    searchable: bool = prop(default=True)

    current_page: int = state(default=1)
    sort_by: str = state(default="id")
    sort_dir: str = state(default="asc")
    search_query: str = state(default="")

    @computed
    def offset(self) -> int:
        return (self.current_page - 1) * self.page_size

    @event("search")
    async def handle_search(self, q: str):
        self.search_query = q
        self.current_page = 1
        return self.render()

    @event("page")
    async def handle_page(self, page: int):
        self.current_page = page
        return self.render()
```

No template `.pjx`:

```pjx
@bind from components.data_table import DataTable
```

### Relação entre `@bind`, `@props` e `props_model`

Quando um template usa `@bind`, ele é ligado a uma classe `Component`. A relação entre `@props` no template e `prop()` / `props_model` na classe segue esta regra:

**Regra:**

* `prop()` na classe define as props do componente do ponto de vista Python — validação, tipagem, valor default.
* `@props` no template define as props do ponto de vista do template — documentação, uso no markup, tooling de editor.
* Quando ambos coexistem (caso mais explícito), devem ser consistentes. O compilador pode emitir aviso se houver divergência de nomes.
* Quando a classe define `props_model: type[BaseModel]`, o `@props` no template pode ser omitido — o compilador deriva os nomes e tipos do modelo Pydantic. Isso é o modo mais conciso.

```python
class UserCard(Component):
    template = "components/UserCard.pjx"
    props_model = UserProps  # @props pode ser omitido no template
```

```pjx
# sem @props — derivado de UserProps automaticamente
@bind from components.user_card import UserCard

<div>{{ name }} — {{ email }}</div>
```

Ou, de forma explícita (útil para documentação e tooling):

```pjx
@bind from components.user_card import UserCard

@props {
  name: str
  email: str
  role: "admin" | "user" | "guest" = "user"
}

<div>{{ name }} — {{ email }}</div>
```

**`self.render()`** retorna uma `HTMLResponse` com o HTML renderizado do template, pronto para ser devolvido por um endpoint FastAPI.

---

## Componentes Built-in

### Async e Tempo Real

#### `Await`

Representa uma região cujo conteúdo será carregado de forma assíncrona via HTMX. Padroniza loading, erro, placeholder e lazy rendering de fragmentos server-side.

```pjx
<Await src="/api/users" trigger="load" target="this" swap="innerHTML">
  <:loading>
    <Spinner />
  </:loading>

  <:error>
    <Alert type="danger">Erro ao carregar.</Alert>
  </:error>
</Await>
```

**Props:**

* `src: str`
* `method: str = "get"`
* `trigger: str = "load"`
* `swap: str = "innerHTML"`
* `target: str = "this"`
* `indicator: str | None = None`
* `select: str | None = None`
* `push_url: bool | str = false`
* `vals: dict | None = None`

**Slots:** `loading?`, `error?`, `default?`

**Compilação conceitual:**

```html
<div hx-get="/api/users" hx-trigger="load" hx-target="this" hx-swap="innerHTML">
  <div class="await-loading">
    <!-- Spinner -->
  </div>
</div>
```

#### `Portal`

Renderiza conteúdo em outro ponto do DOM usando out-of-band swap do HTMX. Útil para notificações, toasts, modais e regiões globais da página.

```pjx
<Portal target="#notifications" swap="beforeend">
  <div class="toast">Operação realizada com sucesso.</div>
</Portal>
```

**Props:**

* `target: str`
* `swap: str = "beforeend"`

**Slots:** `default`

**Compilação conceitual:**

```html
<div hx-swap-oob="beforeend:#notifications">
  <div class="toast">Operação realizada com sucesso.</div>
</div>
```

#### `SSE`

Encapsula a conexão com um endpoint de Server-Sent Events. Define a região que estabelece a conexão e organiza os eventos filhos.

```pjx
<SSE connect="/events/notifications" id="notification-stream">
  <SSEEvent name="new-notification" swap="beforeend" target="#notifications" />
  <SSEEvent name="update-count" swap="innerHTML" target="#notif-count" />
</SSE>
```

**Props:**

* `connect: str`
* `id: str | None = None`
* `retry: int | None = None`
* `close_on_error: bool = false`

**Slots:** `default` (contendo `SSEEvent` e, opcionalmente, placeholders)

**Compilação conceitual:**

```html
<div hx-ext="sse" sse-connect="/events/notifications" id="notification-stream">
  ...
</div>
```

#### `SSEEvent`

Define como um evento SSE específico deve atualizar o DOM. Normalmente usado apenas dentro de `SSE`.

```pjx
<SSEEvent name="new-notification" swap="beforeend" target="#notifications" />
```

ou com slot de transição:

```pjx
<SSEEvent name="refresh-table" swap="outerHTML" target="#data-table">
  <:loading>
    <Spinner />
  </:loading>
</SSEEvent>
```

**Props:**

* `name: str`
* `swap: str = "innerHTML"`
* `target: str = "this"`
* `select: str | None = None`

**Slots:** `default?`, `loading?`

**Compilação conceitual:**

```html
<div sse-swap="new-notification" hx-swap="beforeend" hx-target="#notifications"></div>
```

#### `HtmxForm`

Padroniza formulários com envio via HTMX. Abstrai método HTTP, target, swap, indicador de loading e slots de erro/loading.

```pjx
<HtmxForm
  action="/users"
  method="post"
  swap="outerHTML"
  target="#user-list"
  indicator="#spinner"
>
  <Input name="name" label="Nome" required />
  <Input name="email" type="email" label="Email" required />

  <:loading>
    <Spinner id="spinner" />
  </:loading>

  <:error>
    <Alert type="danger">Erro ao salvar.</Alert>
  </:error>
</HtmxForm>
```

**Props:**

* `action: str`
* `method: str = "post"`
* `target: str = "this"`
* `swap: str = "outerHTML"`
* `indicator: str | None = None`
* `confirm: str | None = None`
* `push_url: bool | str = false`
* `vals: dict | None = None`
* `headers: dict | None = None`

**Slots:** `default`, `loading?`, `error?`, `actions?`

**Compilação conceitual:**

```html
<form hx-post="/users" hx-target="#user-list" hx-swap="outerHTML" hx-indicator="#spinner">
  ...
</form>
```

#### `LiveRegion`

Representa uma região que se atualiza ao vivo, normalmente com SSE, polling HTMX ou outra estratégia incremental. Abstração de mais alto nível que `SSE`.

```pjx
<LiveRegion
  src="/sse/stock-prices"
  event="price-update"
  swap="innerHTML"
  target="#stock-prices"
>
  <:loading>
    <Skeleton />
  </:loading>

  <div id="stock-prices"></div>
</LiveRegion>
```

**Props:**

* `src: str`
* `event: str`
* `swap: str = "innerHTML"`
* `target: str = "this"`
* `mode: str = "sse"` — valores possíveis: `sse`, `poll`
* `interval: str | None = None`

**Slots:** `default`, `loading?`, `error?`

---

### Layout

#### `Container`

Para largura máxima e padding horizontal consistente.

```pjx
<Container size="lg">
  <slot />
</Container>
```

**Props:** `size: "sm" | "md" | "lg" | "xl" | "full"`, `fluid: bool = false`, `class: str = ""`

**Slots:** `default`

#### `Stack`

Pilha vertical com espaçamento consistente. Mais genérico que `Column`.

```pjx
<Stack gap="md">
  <Card />
  <Card />
  <Card />
</Stack>
```

**Props:** `gap: str = "md"`, `align: str = "stretch"`, `divider: bool = false`, `class: str = ""`

**Slots:** `default`

#### `Inline`

Layout horizontal com wrap natural. Ideal para chips, ações, filtros, tags.

```pjx
<Inline gap="sm" wrap>
  <Badge />
  <Badge />
  <Badge />
</Inline>
```

**Props:** `gap: str = "sm"`, `wrap: bool = false`, `align: str = "center"`, `class: str = ""`

**Slots:** `default`

#### `Row`

Contêiner com layout horizontal explícito.

```pjx
<Row gap="md" align="center" justify="between">
  <div>Esquerda</div>
  <div>Direita</div>
</Row>
```

**Props:** `gap: str = "md"`, `align: str = "stretch"`, `justify: str = "start"`, `wrap: bool = false`, `class: str = ""`

**Slots:** `default`

#### `Column`

Contêiner com layout vertical.

```pjx
<Column gap="sm" align="start">
  <div>Item 1</div>
  <div>Item 2</div>
</Column>
```

**Props:** `gap: str = "md"`, `align: str = "stretch"`, `justify: str = "start"`, `class: str = ""`

**Slots:** `default`

#### `Grid`

Layout em grade com API declarativa. Ideal para dashboards, galerias, listas de cards.

```pjx
<Grid columns="3" gap="lg">
  <Card>1</Card>
  <Card>2</Card>
  <Card>3</Card>
</Grid>
```

**Props:** `columns: int | str = 1`, `gap: str = "md"`, `responsive: bool = true`, `min_item_width: str | None = None`, `class: str = ""`

**Slots:** `default`

#### `Center`

Para centralização horizontal/vertical. Ideal para empty states, loading states, telas de auth.

```pjx
<Center minHeight="200px">
  <Spinner />
</Center>
```

**Props:** `minHeight: str | None = None`, `class: str = ""`

**Slots:** `default`

#### `Spacer`

Para empurrar elementos dentro de `Row` ou `Inline`.

```pjx
<Row>
  <span>Esquerda</span>
  <Spacer />
  <Button>Salvar</Button>
</Row>
```

#### `Divider`

Separador visual simples, com label opcional.

```pjx
<Divider />
```

ou

```pjx
<Divider label="Ou" />
```

**Props:** `label: str | None = None`, `class: str = ""`

#### `Section`

Para dividir seções sem repetir classe e espaçamento.

```pjx
<Section title="Perfil" description="Informações principais">
  <Form />
</Section>
```

**Props:** `title: str | None = None`, `description: str | None = None`, `class: str = ""`

**Slots:** `default`

#### `Page`

Para padronizar estrutura de página. Pode renderizar cabeçalho, título, descrição e ações.

```pjx
<Page title="Usuários" description="Gerencie os usuários">
  <slot />
</Page>
```

**Props:** `title: str | None = None`, `description: str | None = None`, `class: str = ""`

**Slots:** `default`

#### `Card`

Componente base de UI, essencial na prática.

**Slots:** `default`, `header?`, `footer?`

#### `SidebarLayout`

Layout clássico com sidebar + conteúdo.

```pjx
<SidebarLayout>
  <:sidebar>
    <Nav />
  </:sidebar>

  <slot />
</SidebarLayout>
```

**Slots:** `sidebar`, `default`

#### `AspectRatio`

Para imagens, vídeos e cards com mídia.

```pjx
<AspectRatio ratio="16/9">
  <img src="{{ image }}" />
</AspectRatio>
```

**Props:** `ratio: str`, `class: str = ""`

**Slots:** `default`

#### `Wrap`

Contêiner com wrap automático de itens.

```pjx
<Wrap gap="sm">
  <Tag />
  <Tag />
</Wrap>
```

**Props:** `gap: str = "sm"`, `class: str = ""`

**Slots:** `default`

---

### Formulários

#### `Field`

Estrutura de campo composável: separa estrutura de campo do input real, oferece mais flexibilidade que um `Input` fechado.

```pjx
<Field label="Email" error="{{ errors.email }}" help="Use seu email principal">
  <input type="email" name="email" />
</Field>
```

**Props:** `label: str | None = None`, `error: str | None = None`, `help: str | None = None`, `class: str = ""`

**Slots:** `default`

#### `Label`

Útil quando se quer compor campos manualmente.

```pjx
<Label for="email">Email</Label>
```

**Props:** `for: str | None = None`, `class: str = ""`

**Slots:** `default`

#### `Input`

Padroniza campos de formulário com label, help text e erro. Facilita integração com `HtmxForm`.

```pjx
<Input
  name="email"
  type="email"
  label="Email"
  placeholder="voce@exemplo.com"
  required
/>
```

ou com erro:

```pjx
<Input
  name="email"
  type="email"
  label="Email"
  error="Email inválido"
/>
```

**Props:**

* `name: str`
* `type: str = "text"`
* `label: str | None = None`
* `value: str | None = None`
* `placeholder: str | None = None`
* `required: bool = false`
* `disabled: bool = false`
* `readonly: bool = false`
* `error: str | None = None`
* `help: str | None = None`
* `id: str | None = None`
* `class: str = ""`

#### `TextArea`

```pjx
<TextArea
  name="message"
  label="Mensagem"
  rows="4"
/>
```

**Props:** `name: str`, `label: str | None = None`, `rows: int = 3`, `placeholder: str | None = None`, `required: bool = false`, `disabled: bool = false`, `error: str | None = None`, `help: str | None = None`, `class: str = ""`

#### `Select`

```pjx
<Select
  name="role"
  label="Perfil"
  options="{{ roles }}"
  value="{{ current_role }}"
/>
```

**Props:** `name: str`, `label: str | None = None`, `options: list`, `value: str | None = None`, `required: bool = false`, `disabled: bool = false`, `error: str | None = None`, `class: str = ""`

#### `Checkbox`

```pjx
<Checkbox name="active" label="Ativo" checked />
```

**Props:** `name: str`, `label: str | None = None`, `checked: bool = false`, `disabled: bool = false`, `class: str = ""`

#### `RadioGroup`

```pjx
<RadioGroup
  name="plan"
  value="{{ plan }}"
  options="{{ plans }}"
/>
```

**Props:** `name: str`, `value: str | None = None`, `options: list`, `disabled: bool = false`, `class: str = ""`

#### `Toggle`

Para valores booleanos.

```pjx
<Toggle name="notifications" label="Receber notificações" />
```

**Props:** `name: str`, `label: str | None = None`, `checked: bool = false`, `disabled: bool = false`, `class: str = ""`

#### `Button`

Um dos componentes mais usados.

```pjx
<Button type="submit" variant="primary">Salvar</Button>
```

**Props:** `type: str = "button"`, `variant: str = "primary"`, `size: str = "md"`, `disabled: bool = false`, `loading: bool = false`, `href: str | None = None`, `target: str | None = None`, `icon: str | None = None`, `class: str = ""`

**Slots:** `default`

---

### Feedback e Status

#### `Alert`

Mensagens de feedback para usuário. Pode ser usado com `Portal`, `Await` e `HtmxForm`.

```pjx
<Alert type="success">Usuário salvo com sucesso.</Alert>
```

ou

```pjx
<Alert type="danger" title="Erro">
  Não foi possível concluir a operação.
</Alert>
```

**Props:** `type: str = "info"` — valores: `info`, `success`, `warning`, `danger`; `title: str | None = None`, `dismissible: bool = false`, `icon: bool = false`, `class: str = ""`

**Slots:** `default`

#### `Spinner`

Indicador visual de carregamento. Ideal para uso com `Await`, `HtmxForm` e `LiveRegion`.

```pjx
<Spinner />
```

ou

```pjx
<Spinner size="sm" label="Carregando..." />
```

**Props:** `size: str = "md"`, `label: str | None = None`, `id: str | None = None`, `class: str = ""`

#### `Skeleton`

Placeholder de loading mais sofisticado.

```pjx
<Skeleton lines="3" />
```

ou

```pjx
<SkeletonCard />
```

**Props de `Skeleton`:** `lines: int = 3`, `class: str = ""`

#### `EmptyState`

Ideal para listas, tabelas e uso com `For` e `Await`.

```pjx
<EmptyState
  title="Nenhum usuário encontrado"
  description="Tente ajustar os filtros."
/>
```

**Props:** `title: str`, `description: str | None = None`, `class: str = ""`

**Slots:** `default?`

#### `Badge`

Para status, tags e labels curtas.

```pjx
<Badge variant="success">Ativo</Badge>
```

**Props:** `variant: str = "default"`, `class: str = ""`

**Slots:** `default`

#### `Tag`

Semântico para listas e filtros.

**Props:** `class: str = ""`

**Slots:** `default`

#### `Toast`

Notificação temporária, ideal com `Portal`.

```pjx
<Portal target="#toasts">
  <Toast type="success">Salvo com sucesso</Toast>
</Portal>
```

**Props:** `type: str = "info"`, `class: str = ""`

**Slots:** `default`

---

### Dados e Navegação

#### `Pagination`

Paginação visual e interativa. Pode ser usada com links normais SSR ou com HTMX para trocar apenas uma região.

```pjx
<Pagination
  current="{{ current_page }}"
  total="{{ total_pages }}"
  url="{{ @event_url('page', page='{page}') }}"
  target="#data-table"
  swap="outerHTML"
/>
```

**Props:**

* `current: int`
* `total: int`
* `url: str`
* `target: str | None = None`
* `swap: str = "outerHTML"`
* `window: int = 2`
* `show_first_last: bool = true`
* `show_prev_next: bool = true`

#### `Avatar`

Com suporte a fallback com iniciais.

```pjx
<Avatar src="{{ user.avatar }}" alt="{{ user.name }}" />
```

**Props:** `src: str`, `alt: str = ""`, `size: str = "md"`, `class: str = ""`

#### `Breadcrumb`

**Slots:** `default`

#### `Icon`

Integração com sistema de ícones (opcional, dependendo do design system).

```pjx
<Icon name="search" />
```

**Props:** `name: str`, `size: str = "md"`, `class: str = ""`

---

### Interativos

#### `Modal`

```pjx
<Modal open="{{ open }}">
  <:header>Título</:header>
  <p>Conteúdo</p>
</Modal>
```

**Props:** `open: bool = false`, `class: str = ""`

**Slots:** `header?`, `default`, `footer?`

#### `Drawer`

Painel lateral deslizante.

**Props:** `open: bool = false`, `side: str = "right"`, `class: str = ""`

**Slots:** `header?`, `default`, `footer?`

#### `Tabs`

**Props:** `active: str | None = None`, `class: str = ""`

**Slots:** `default`

#### `Accordion`

Ótimo especialmente com Alpine.

```pjx
<Accordion>
  <AccordionItem title="Detalhes">
    ...
  </AccordionItem>
</Accordion>
```

**Props de `AccordionItem`:** `title: str`, `open: bool = false`

**Slots de `AccordionItem`:** `default`

#### `DropdownMenu`

**Props:** `class: str = ""`

**Slots:** `trigger`, `default`

#### `Table` / `TableHead` / `TableRow` / `TableCell`

Componentes estruturais de tabela.

#### `DataTable`

Tabela completa com estado server-side via classe Python.

#### `Tooltip`

**Props:** `content: str`, `placement: str = "top"`, `class: str = ""`

**Slots:** `default`

---

## Exemplos de Referência

### Arquivo simples

```pjx
@props {
  name: str
  email: str
  avatar: str = "/default.png"
}

@slot actions?

<div class="user-card">
  <img src="{{ avatar }}" alt="{{ name }}" />
  <h3>{{ name }}</h3>
  <p>{{ email }}</p>

  <Show when="{{ @has_slot('actions') }}">
    <slot name="actions" />
  </Show>
</div>
```

### Múltiplos componentes no mesmo arquivo

```pjx
@component Avatar {
  @props {
    src: str
    alt: str = ""
  }

  <img class="avatar" src="{{ src }}" alt="{{ alt }}" />
}

@component UserCard {
  @props {
    name: str
    email: str
    avatar: str
  }

  @slot actions?

  <div class="user-card">
    <Avatar src="{{ avatar }}" alt="{{ name }}" />
    <h3>{{ name }}</h3>
    <p>{{ email }}</p>

    <Show when="{{ @has_slot('actions') }}">
      <slot name="actions" />
    </Show>
  </div>
}
```

### Bind com classe Python

```python
# components/data_table.py
from pjx import Component, prop, state, computed, event

class DataTable(Component):
    template = "components/DataTable.pjx"

    endpoint: str = prop()
    page_size: int = prop(default=20)
    searchable: bool = prop(default=True)

    current_page: int = state(default=1)
    sort_by: str = state(default="id")
    sort_dir: str = state(default="asc")
    search_query: str = state(default="")

    @computed
    def offset(self) -> int:
        return (self.current_page - 1) * self.page_size

    @event("search")
    async def handle_search(self, q: str):
        self.search_query = q
        self.current_page = 1
        return self.render()

    @event("page")
    async def handle_page(self, page: int):
        self.current_page = page
        return self.render()
```

```pjx
@bind from components.data_table import DataTable

@props {
  columns: list[dict]
  data: list[dict]
}

<div id="data-table-{{ @id }}">
  <Show when="{{ searchable }}">
    <input
      type="search"
      name="q"
      placeholder="Buscar..."
      @input.htmx="get:{{ @event_url('search') }}"
      @trigger="input changed delay:300ms"
      @target="#data-table-{{ @id }}"
      @swap="outerHTML"
    />
  </Show>

  <table>
    <thead>
      <tr>
        <For each="{{ columns }}" as="col">
          <th>{{ col.label }}</th>
        </For>
      </tr>
    </thead>
    <tbody>
      <For each="{{ data }}" as="row">
        <tr>
          <For each="{{ columns }}" as="col">
            <td>{{ row[col.key] }}</td>
          </For>
        </tr>
      </For>
    </tbody>
  </table>
</div>
```

---

## Integração com FastAPI

### Filosofia

A integração com FastAPI deve seguir a mesma metodologia do próprio FastAPI: simples de usar no caso básico, poderosa quando necessário. O desenvolvedor que já conhece FastAPI deve se sentir em casa — mesmos padrões de `Annotated`, `Depends`, `APIRouter` e Pydantic.

### Setup da aplicação

A inicialização do pjx é feita uma vez, normalmente junto com o `FastAPI()`. Neste momento são configurados o diretório de templates, os componentes built-in e o engine Jinja2.

```python
from fastapi import FastAPI
from pjx import Pjx

pjx = Pjx(
    templates_dir="templates",       # diretório raiz dos arquivos .pjx
    components_dir="components",     # diretório dos componentes reutilizáveis
    auto_reload=True,                # recompila em dev quando o arquivo muda
    cache=True,                      # cacheia templates compilados em produção
)

app = FastAPI()
pjx.init_app(app)                   # registra middleware e configurações internas
```

Os templates compilados são cacheados em memória na primeira requisição (ou no startup, se `eager_compile=True`). Em desenvolvimento, `auto_reload=True` monitora mudanças nos arquivos `.pjx` e invalida o cache.

### Router

As rotas pjx devem ser registráveis como qualquer `APIRouter` do FastAPI.

```python
from fastapi import FastAPI
from pjx.fastapi import PjxRouter

router = PjxRouter(prefix="/users", tags=["users"])

app = FastAPI()
app.include_router(router)
```

### Tipos de retorno: `Page`, `Template` e `self.render()`

Existem dois tipos de resposta HTML:

* **`Page`** — resposta de página completa (inclui layout base, se configurado). Retorna `HTMLResponse` com status 200.
* **`Template`** — resposta de fragmento, sem layout. Usado para respostas HTMX que substituem apenas parte do DOM. Retorna `HTMLResponse` com status 200.
* **`self.render()`** — disponível dentro de classes `Component`. Renderiza o template do componente como fragmento e retorna `HTMLResponse`. Usado nos handlers `@event`.

Ambos `Page` e `Template` são chamáveis: recebem as variáveis de contexto como kwargs e retornam a resposta.

### Renderização por injeção (`Annotated` + `Depends`)

O padrão de renderização usa `Annotated` e `Depends` para injetar o renderizador como dependência de rota, exatamente como FastAPI injeta qualquer outra dependência.

```python
from typing import Annotated
from fastapi import Depends
from pjx.fastapi import render, Page, Template

# Renderiza uma página completa (com layout)
@router.get("/")
async def list_users(
    page: Annotated[Page, Depends(render("pages/users/index.pjx"))],
    users: Annotated[list[User], Depends(get_users)],
):
    return page(users=users)

# Renderiza um fragmento (resposta HTMX — sem layout)
@router.get("/{id}/card")
async def user_card(
    fragment: Annotated[Template, Depends(render("components/UserCard.pjx"))],
    user: Annotated[User, Depends(get_user)],
):
    return fragment(user=user)
```

### Fragmentos HTMX vs Páginas Completas

O HTMX espera que certas rotas retornem apenas um fragmento HTML — sem `<html>`, sem `<head>`, sem layout. O pjx distingue isso pelo tipo de renderizador injetado:

* `render("template.pjx")` → `Template` (fragmento, sem layout)
* `render("template.pjx", layout="layouts/base.pjx")` → `Page` (página completa)

Uma mesma rota pode retornar fragmento ou página dependendo do header `HX-Request`:

```python
from fastapi import Request
from pjx.fastapi import render, Page, Template, is_htmx

@router.get("/users")
async def list_users(
    request: Request,
    users: Annotated[list[User], Depends(get_users)],
    page: Annotated[Page, Depends(render("pages/users/index.pjx", layout="layouts/base.pjx"))],
    fragment: Annotated[Template, Depends(render("pages/users/index.pjx"))],
):
    ctx = {"users": users}
    return fragment(**ctx) if is_htmx(request) else page(**ctx)
```

### Pydantic para props e eventos

Props de componentes e payloads de eventos são validados com Pydantic. O mesmo modelo serve para receber dados de formulários HTMX e para tipar props de templates.

```python
from pydantic import BaseModel, EmailStr
from pjx import Component, prop, event

class UserProps(BaseModel):
    name: str
    email: EmailStr
    role: Literal["admin", "user", "guest"] = "user"

class UserCard(Component):
    template = "components/UserCard.pjx"

    # props validadas via Pydantic
    props_model = UserProps

    @event("save")
    async def handle_save(self, data: UserProps) -> Response:
        # data já vem validado pelo Pydantic
        await save_user(data)
        return self.render()
```

No template, a declaração `@props` espelha o modelo Pydantic:

```pjx
@bind from components.user_card import UserCard

@props {
  name: str
  email: str
  role: "admin" | "user" | "guest" = "user"
}

<div class="user-card">
  <h3>{{ name }}</h3>
  <p>{{ email }}</p>
</div>
```

### SSE via FastAPI

Endpoints SSE são declarados como rotas normais do FastAPI, retornando `EventSourceResponse`.

```python
from pjx.fastapi import sse_route, SSEContext

@router.get("/events/notifications")
async def notifications_stream(
    ctx: Annotated[SSEContext, Depends(sse_route())],
    user: Annotated[User, Depends(get_current_user)],
):
    async for event in notification_bus.subscribe(user.id):
        await ctx.send(event="new-notification", data=event.model_dump())
```

No template:

```pjx
<SSE connect="/events/notifications">
  <SSEEvent name="new-notification" swap="beforeend" target="#notifications" />
</SSE>
```

### Contexto Global

Variáveis que devem estar disponíveis em todos os templates (como `request`, `current_user`, `flash_messages`, configurações de tema) são injetadas via **context processors** — dependências globais registradas no `Pjx`.

```python
from fastapi import Request
from pjx import Pjx

pjx = Pjx(templates_dir="templates")

@pjx.context_processor
async def global_context(request: Request) -> dict:
    return {
        "request": request,
        "app_name": "Minha App",
    }

@pjx.context_processor
async def auth_context(
    user: Annotated[User | None, Depends(get_optional_user)],
) -> dict:
    return {"current_user": user}
```

Os context processors são executados antes de cada renderização e o resultado é mergeado com o contexto da rota. As dependências FastAPI dentro de context processors funcionam normalmente.

### Dependências reutilizáveis

O padrão `Depends` do FastAPI funciona normalmente para injetar dados no contexto do template.

```python
def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    ...

def get_user_context(user: Annotated[User, Depends(get_current_user)]) -> dict:
    return {"user": user, "is_admin": user.role == "admin"}

@router.get("/dashboard")
async def dashboard(
    page: Annotated[Page, Depends(render("pages/dashboard.pjx"))],
    ctx: Annotated[dict, Depends(get_user_context)],
):
    return page(**ctx)
```

### Performance e otimização

* Templates compilados uma vez e cacheados em memória — sem recompilação por request.
* O compilador produz Jinja2 puro, que é executado pelo engine Jinja2 nativo (sem overhead de interpretação em runtime).
* Props validadas por Pydantic com `model_validate` — validação rápida e com erro claro.
* Fragmentos HTMX renderizam apenas o subtree necessário, sem re-renderizar a página inteira.
* SSE usa `async for` nativo do Python, sem polling ou threads extras.
* Sem runtime JavaScript próprio — Alpine e HTMX são bibliotecas externas, o pjx só gera os atributos certos.

### Código Pythônico

* API declarativa: o mínimo de cerimônia para o caso comum.
* Tipos em todo lugar: props, eventos e payloads são tipados com Pydantic ou anotações Python.
* Sem magia implícita: o que entra no template é explicitamente passado, igual a como FastAPI expõe dependências.
* Erros cedo: props inválidas, slots ausentes e nomes não resolvidos são erros de compilação, não de runtime.
* Composição sobre herança: componentes se compõem via slots, não via herança de classes.

---

## Resumo da Gramática

### Núcleo da linguagem

* `@props`
* `@slot`
* `@state`
* `@bind`
* `@component`
* `@let`
* `@from`
* `@import`

### Estruturas

* `<Show>`
* `<For>`
* `<Switch>` / `<Match>`

### Blocos especiais

* `<:fallback>`
* `<:empty>`
* `<:header>`
* `<:footer>`
* `<:item>`
* `<:loading>`
* `<:error>`
* `<:sidebar>`
* `<:actions>`

### Regra central

A linguagem deve parecer principalmente HTML + Jinja, com poucas extensões elegantes e previsíveis. Tudo que for declarado em `@props`, `@slot` e `@state` pertence ao escopo do componente atual e fica disponível no template definido dentro dele.

### O que não colocar na v1

Para manter a linguagem simples e funcional, evitar:

* sintaxe demais para abstrações que podem ser biblioteca
* runtime cliente pesado
* semântica ambígua de estado
