# Template Language

## Visao Geral

A linguagem atual do PJX ainda usa extensao `.jinja`, mas ja tem uma camada de
parser e compiler propria.

Estrutura canônica:

```jinja
{% import css "/static/css/components/ui/button.css" %}
{% import "layouts/AppLayout.jinja" as AppLayout %}
{% import "components/ui/Button.jinja" as Button %}

{% component ExamplePage %}
  {% props title: str, count: int = 0 %}

  <AppLayout page_title="Example">
    <Button>{{ title }}</Button>
  </AppLayout>
{% endcomponent %}
```

## Ordem do Arquivo

O formato esperado hoje e:

```text
1. imports
2. props aliases opcionais com {% set ... = {...} %}
3. um unico {% component ... %} ... {% endcomponent %}
4. dentro do componente:
   - directives do preamble
   - corpo do markup
```

## Imports

Tipos suportados:

```jinja
{% import "components/ui/Button.jinja" as Button %}
{% import css "/static/css/components/ui/button.css" %}
{% import js "/static/js/example.js" %}
```

Regras:

* componentes precisam de alias
* componentes usados no markup precisam estar importados
* css e js viram assets do componente

## Template Mounts e Prefixos

Quando voce registra mounts extras:

```python
pjx = PJX(
    root=BASE_DIR,
    templates=[
        "templates",
        {"prefix": "admin", "path": "admin_templates"},
    ],
)
```

voce pode importar assim:

```jinja
{% import "@admin/components/ui/Button.jinja" as AdminButton %}
{% import "@admin/layouts/AdminLayout.jinja" as AdminLayout %}
```

Convencao:

* mount principal: sem prefixo, como `components/...`
* mount extra: `@prefix/...`

## Component

O componente e definido por um unico bloco:

```jinja
{% component Button %}
  ...
{% endcomponent %}
```

Hoje o parser aceita modificadores depois do nome:

```jinja
{% component Button async experimental %}
```

Mas eles ainda sao so metadado do componente compilado; nao existe semantica
publica forte para eles ainda.

## Props

Inline:

```jinja
{% props title: str, count: int = 0 %}
```

Multilinha:

```jinja
{% props
  title: str,
  count: int = 0,
  active: bool = False
%}
```

Alias de props:

```jinja
{% set ButtonProps = {
  "label": label: str,
  "variant": variant: str = "primary"
} %}

{% component Button %}
  {% props ButtonProps %}
  ...
{% endcomponent %}
```

Regras atuais:

* so pode existir um bloco `props` por componente
* type hints basicos sao validados no runtime
* props ausentes sem default geram erro

## Inject e Provide

```jinja
{% inject theme %}
{% provide theme %}
```

Uso esperado:

* layout ou componente ancestral seta um valor provido
* componentes filhos pedem `inject`

Hoje isso funciona como contexto de render do servidor, nao como estado
reativo no cliente.

## Computed

```jinja
{% computed label %}
{{ title }} - {{ count }}
{% endcomputed %}
```

Isso vira um `set` no preamble do Jinja compilado.

## Slots

Declaracao:

```jinja
{% slot header %}{% endslot %}
{% slot footer(actions) %}{% endslot %}
```

Preenchimento no chamador:

```jinja
<Card>
  <Fill slot="header">
    <h2>Header</h2>
  </Fill>

  Conteudo principal
</Card>
```

O corpo default entre as tags continua sendo `content`.

## Signal e Action

Sintaxe atual:

```jinja
{% signal count = signal(initial_count) %}

{% action increment %}
count = count + 1
{% endaction %}
```

Estado atual:

* `signal` hoje vira principalmente preambulo compilado
* `action` e reconhecido e registrado como metadado do componente
* o runtime nativo completo para signals/actions ainda nao esta fechado

Hoje o caminho funcional de interacao continua sendo:

* HTMX para round-trip incremental
* Alpine para estado local pequeno

## Built-ins de Markup

### If

```jinja
<If when={{ count > 0 }}>
  <p>Tem itens</p>
  <Else>
    <p>Vazio</p>
  </Else>
</If>
```

### For

```jinja
<For each={{ items }} as="item" index="index">
  <li>{{ index }} - {{ item }}</li>
  <Empty>
    <li>Sem itens</li>
  </Empty>
</For>
```

### Switch

```jinja
<Switch value={{ status }}>
  <Case when="ready">Pronto</Case>
  <Case when="building">Processando</Case>
  <Default>Desconhecido</Default>
</Switch>
```

## Component Calls

Componentes importados com alias TitleCase podem ser usados como tags:

```jinja
<Button variant="primary">Salvar</Button>
<StatusBadge status="ready" />
```

O compiler transforma isso em chamadas para `__pjx_render_component(...)`.

## Attrs e Diretivas Core

Attrs HTML normais passam direto. Alem disso, o Catalog trata algumas diretivas
core:

* `jx-bind:name`
* `jx-class`
* `jx-show`
* `jx-text`
* `jx-html`
* `jx-on:event`

Exemplo:

```jinja
<div
  jx-bind:data-id={{ user_id }}
  jx-class={{ {"is-active": active} }}
  jx-show={{ visible }}
/>
```

## Escolha Canonica de Expressao

Hoje a forma principal para expressoes em attrs do PJX continua:

```jinja
prop={{ expr }}
```

Isso vale para built-ins e componentes.

O projeto ainda nao promove `:prop="expr"` como sintaxe de primeira classe.

## Formatacao Canonica

`pjx format` reorganiza:

* imports
* alias de props
* directives do preamble
* espacos em branco do componente

Ele tenta preservar o corpo o maximo possivel sem inventar layout novo.
