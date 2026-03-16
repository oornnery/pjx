# Template Language

## Visao Geral

A linguagem do PJX usa extensao `.pjx` e sintaxe `@directive` para diretivas
do framework.

Estrutura canonica:

```text
@from pjx.ui import Button, Badge
@import "layouts/Layout.pjx"

@props { title: str = "Home", count: int = 0 }

<Layout title="{{ title }}">
  <Button label="{{ title }}" />
</Layout>
```

## Ordem do Arquivo

O formato esperado e:

```text
1. imports (@from, @import)
2. @bind (opcional)
3. @props
4. @slot declarations
5. @state (opcional)
6. @let (opcional)
7. body markup
```

Em modo multi-component:

```text
1. imports (@from, @import)
2. @component Name {
     @props { ... }
     @slot name?
     body
   }
3. @component Name2 { ... }
```

## Imports

Tipos suportados:

```text
@from pjx.ui import Button, Badge, Alert
@from pjx.layout import Card
@import "layouts/Layout.pjx"
```

Regras:

* `@from module import Name` importa componentes de um modulo PJX
* `@import "path"` importa um template inteiro
* componentes usados no markup precisam estar importados

## Props

Inline:

```text
@props { title: str, count: int = 0 }
```

Regras atuais:

* so pode existir um bloco `@props` por componente/pagina
* type hints basicos sao validados no runtime
* props ausentes sem default geram `PropValidationError`

## Slots

Declaracao:

```text
@slot default
@slot footer?
```

O `?` indica slot opcional. Preenchimento no chamador:

```text
<Card title="Example">
  Conteudo principal (slot default)
  <:footer>
    <Button label="Action" />
  </:footer>
</Card>
```

Teste de slot preenchido:

```text
<Show when="{{ @has_slot('footer') }}">
  <div class="card-footer">
    <slot name="footer" />
  </div>
</Show>
```

## State

```text
@state { count: 0, items: [] }
```

Serializado como JSON e passado para Alpine `x-data`.

## Bind

```text
@bind from exemples.state import Counter
```

Associa o template a uma classe Python que mantem estado no servidor.

## Let

```text
@let greeting = "Hello, " + name
```

Define uma variavel computada no preamble Jinja.

## Component Definition

Em modo multi-component:

```text
@component Button {
  @props { label: str = "", variant: str = "default" }
  @slot default
  <button class="btn btn-{{ variant }}">
    <Show when="{{ label }}">{{ label }}</Show>
    <slot />
  </button>
}
```

## Built-ins de Markup

### Show

```text
<Show when="{{ count > 0 }}">
  <p>Tem itens</p>
  <Else>
    <p>Vazio</p>
  </Else>
</Show>
```

### For

```text
<For each="{{ items }}" as="item">
  <li>{{ item.name }}</li>
  <Empty>
    <li>Sem itens</li>
  </Empty>
</For>
```

### Switch

```text
<Switch value="{{ status }}">
  <Case when="ready">Pronto</Case>
  <Case when="building">Processando</Case>
  <Default>Desconhecido</Default>
</Switch>
```

## Component Calls

Componentes importados com TitleCase podem ser usados como tags:

```text
<Button variant="primary" label="Salvar" />
<Badge variant="ready" text="live" />
```

O compiler transforma isso em chamadas para `__pjx_render_component(...)`.

## Named Slots

Slots nomeados usam a sintaxe `<:name>`:

```text
<Card title="Example">
  <:header>
    <strong>Custom header</strong>
  </:header>
  Body content
  <:footer>
    <Button label="Action" />
  </:footer>
</Card>
```

## Attrs e Diretivas Core

Attrs HTML normais passam direto. Alem disso, o Catalog trata diretivas core:

* `jx-bind:name`
* `jx-class`
* `jx-show`
* `jx-text`
* `jx-html`
* `jx-on:event`

HTMX e Alpine attrs no template:

```text
<button
  @click.htmx="post:/actions/counter/inc"
  @target="#counter-display"
  @swap="outerHTML"
>+</button>
```

## Expressoes

A forma principal para expressoes em attrs:

```text
prop="{{ expr }}"
```

Binding via `:prop`:

```text
<Badge :variant="status" text="live" />
```

## Formatacao Canonica

`pjx format` reorganiza:

* imports
* @props, @slot, @state, @let
* corpo do componente

Ele tenta preservar o corpo o maximo possivel sem inventar layout novo.
