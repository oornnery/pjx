# PJX — Documento de Requisitos, Arquitetura e Roadmap Inicial

## 1. Visão

PJX é um framework de componentes e templates server-side inspirado no JX, mas redesenhado do zero com foco em:

* performance
* sintaxe moderna
* experiência de desenvolvimento próxima de Vue/Solid/React
* integração nativa com FastAPI, HTMX e Alpine
* arquitetura preparada para backend híbrido: Python + Rust

A proposta do PJX não é ser apenas um pré-processador de templates. A meta é virar um **framework de UI server-side declarativo**, com componentes, slots, diretivas, controle de fluxo, tipagem, contexto, async e reatividade parcial.

---

## 2. Problema que o PJX resolve

Hoje, no ecossistema Python, o desenvolvimento de frontend server-side normalmente cai em um destes extremos:

* templates simples demais, mas pouco componíveis
* engines rápidas, mas sem ergonomia de framework
* stacks modernas demais no cliente, exigindo SPA, bundler, hydration e toolchain JS

O PJX quer ocupar um espaço diferente:

* DX moderna de componentes
* renderização no servidor
* interatividade incremental
* baixo acoplamento com JavaScript complexo
* HTML como saída principal

Em resumo:

**PJX = ergonomia de frameworks modernos + arquitetura server-side simples + performance forte.**

---

## 3. Objetivos do produto

### Objetivos principais

1. Criar um sistema de componentes declarativo e elegante.
2. Melhorar legibilidade comparado a Jinja/JinjaX puros.
3. Suportar patterns modernos de UI sem exigir SPA.
4. Permitir backend otimizado com MiniJinja/Rust.
5. Manter boa integração com Python e frameworks web existentes.
6. Oferecer validação, tipagem e erros bons em tempo de desenvolvimento.
7. Evoluir de template engine para framework fullstack server-driven.

### Objetivos secundários

* boa integração com Tailwind
* suporte forte a HTMX
* possibilidade de reatividade parcial com signals
* base sólida para CLI, lint, check e precompile

### Não objetivos iniciais

* substituir React/Vue em SPAs complexas
* criar VDOM no cliente
* competir com bundlers JS
* implementar tudo de uma vez no core

---

## 4. Princípios de design

### 4.1 HTML-first

O template continua sendo HTML-centric. Tudo deve parecer HTML melhorado, não uma DSL alienígena.

### 4.2 Server-first

O servidor é a fonte da verdade. O cliente recebe HTML, atributos e comportamento incremental.

### 4.3 Progressive enhancement

Funciona bem com HTML puro. Recursos reativos e comportamentais entram por camadas.

### 4.4 Declarativo > imperativo

Sempre que possível, usar componentes, slots e diretivas em vez de boilerplate manual.

### 4.5 Fast by design

Toda feature deve ser pensada com custo de parse, compilação, cache e render em mente.

### 4.6 Escape hatch real

Quando necessário, o usuário pode descer para Jinja puro, HTML puro, Alpine puro ou Python puro.

### 4.7 Excelente DX

Erros bons, tipagem útil, CLI de check, autocomplete viável e sintaxe previsível.

### 4.8 Gramática explícita > metadata escondida

Recursos centrais da linguagem devem preferir **blocos reais** e nós próprios na AST, em vez de depender de comentários especiais como mecanismo principal.

---

## 5. Posicionamento do PJX

PJX deve ser entendido como:

* **template/component framework** para Python
* **UI server-side framework** com sintaxe moderna
* **camada declarativa** sobre renderização server-side

Mental model:

```text
Vue/Solid DX
+ Jinja syntax heritage
+ HTMX/Alpine interatividade incremental
+ FastAPI no backend
+ MiniJinja/Rust para performance
```

---

## 6. Público-alvo

### Primário

* devs Python que querem construir UI moderna sem SPA
* projetos FastAPI/Starlette/Quart
* dashboards, backoffices, SaaS internos, blogs, apps CRUD e produtos web server-driven

### Secundário

* quem hoje usa Jinja, JinjaX, HTMX ou Alpine
* quem quer DX parecida com Vue/React sem depender de Node no core do app

---

## 7. Proposta de valor

Com PJX, o usuário deve conseguir:

* criar componentes reutilizáveis e tipados
* usar named slots e scoped slots
* escrever controle de fluxo legível
* usar diretivas declarativas em atributos
* fazer binding e interação incremental sem muito boilerplate
* compilar e renderizar rápido
* obter bons erros em tempo de desenvolvimento

---

## 8. Visão de arquitetura

## 8.1 Pipeline geral

```text
.pjx/.jinja component
        ↓
Lexer / Parser PJX
        ↓
AST PJX
        ↓
Transforms
- props
- imports
- slots
- directives
- control flow components
- context/inject
- async resources
        ↓
IR intermediária
        ↓
Backend renderer
- Jinja2 backend (compat/dev)
- MiniJinja backend (perf/prod)
        ↓
HTML final
```

## 8.2 Camadas

### Camada 1 — Frontend da linguagem

Responsável por:

* parsear arquivos PJX
* construir AST
* validar sintaxe
* gerar mensagens de erro amigáveis

### Camada 2 — Compilador

Responsável por:

* expandir diretivas
* resolver componentes built-in
* transformar slots
* transformar typed props
* gerar IR estável

### Camada 3 — Runtime

Responsável por:

* renderizar templates
* resolver contexto
* aplicar cache
* executar async resources
* integrar actions/signals futuramente

### Camada 4 — Integração web

Responsável por:

* FastAPI helpers
* HTMX helpers
* dev server
* static assets
* partial rendering

---

## 9. Sintaxe e recursos principais

## 9.0 Direção de sintaxe da linguagem

PJX passa a adotar uma sintaxe **baseada em blocos explícitos** para declarações principais da linguagem, substituindo o uso de comentários especiais como mecanismo central de definição.

### Objetivo

* deixar a linguagem mais legível
* tornar parser/AST mais robustos
* melhorar lint, format, autocomplete e mensagens de erro
* aproximar a ergonomia de linguagens/template engines modernas

### Direção aprovada

* preferir blocos como `{% component %}`, `{% props %}`, `{% slot %}`, `{% computed %}`
* manter `{{ ... }}` para expressões
* manter `{% if %}`, `{% for %}`, `{% set %}` e demais estruturas familiares quando fizer sentido
* evitar comentários mágicos como mecanismo primário da linguagem

### Decisões de sintaxe

* **não usar `{% end %}` genérico**
* usar fechamentos explícitos como:

  * `{% endcomponent %}`
  * `{% endslot %}`
  * `{% endcomputed %}`
* `async` e `default` entram como **modificadores**, não como keywords totalmente separadas
* `def` deixa de ser o centro da modelagem de componentes; o núcleo passa a ser `component + props + slot + computed`

### Filtro de simplicidade para o core

* se mais de uma sintaxe resolver o mesmo problema, o PJX precisa declarar uma forma preferida e limitar o papel das demais
* construções familiares de Jinja continuam suportadas, mas a documentação prioriza a sintaxe declarativa própria do PJX
* sintaxe estrutural nova só entra quando melhora AST, mensagens de erro e leitura ao mesmo tempo
* recurso novo precisa ser explicável em uma frase curta na documentação
* se algo puder nascer como built-in de P1 ou extensão oficial, não deve complicar o P0

### Gramática canônica do PJX v0.1

* declaração de componente por bloco: `{% component Nome %} ... {% endcomponent %}`
* consumo de componente por tag em `PascalCase`: `<Card />` e `<Card>...</Card>`
* props declaradas por `{% props ... %}`
* props dinâmicas no uso seguem `{{ ... }}` em atributos; o core não adiciona `:` ou `@`
* conteúdo default via `{{ content }}`
* named slots via `{% slot nome %}` e acesso por `slot.nome`
* fluxo preferencial via `<If>`, `<For>` e `<Switch>`
* suporte equivalente via `{% if %}`, `{% for %}` e `{% set %}`
* metadados locais via `{% import css "..." %}` e `{% import js "..." %}`
* modificadores opcionais no final da declaração principal, ex.: `{% component UserList async %}`

### Motivações

* parser mais simples e previsível
* AST mais forte e menos ambígua
* melhor nesting de blocos
* leitura mais clara em componentes longos
* menor confusão entre conceito de função Python e declaração de componente/template

---

## 9.1 Componentes base

### Sintaxe preferencial

```jinja
{% component Button %}
  {% props
    variant: Literal["default", "secondary", "outline", "ghost"] = "default",
    size: Literal["sm", "md", "lg", "icon"] = "md",
    type: str = "button",
    disabled: bool = false
  %}

  {% import css "/static/css/button.css" %}

  <button
    type="{{ type }}"
    class="btn btn-{{ variant }} btn-{{ size }}"
    {% if disabled %}disabled{% endif %}
  >
    {{ content }}
  </button>
{% endcomponent %}
```

### Sintaxe de consumo

```jinja
<Card title="Dashboard" user="{{ current_user }}">
  {% slot header %}
    <h2>Resumo</h2>
  {% endslot %}

  <p>Conteúdo principal</p>

  {% slot footer %}
    <Button variant="ghost">Fechar</Button>
  {% endslot %}
</Card>
```

### Regra de uso

* componente é declarado como bloco e consumido como tag
* slot nomeado usa o mesmo `{% slot %}` tanto na declaração quanto no consumo
* `content` continua sendo o corpo livre da tag

### Requisitos

* suporte a props
* conteúdo default
* passthrough simples de attrs
* metadados de assets
* composição de componentes

### Decisão adicional

A declaração de componente deve ser um nó próprio da AST, e não derivada de comentário especial no topo do arquivo.

No P0, attrs extras devem entrar como uma bag reservada `attrs`, sem spread sintático ou merge mágico no core inicial.

---

## 9.2 Metadados por componente

Exemplo legado conceitual:

```jinja
{#def message #}
{# css "/static/components/alert.css" #}
{# js "/static/components/alert.js" #}

<div class="alert">{{ message }}</div>
```

### Direção atualizada

Metadados passam a preferir sintaxe de bloco/tag da linguagem:

```jinja
{% component Alert %}
  {% props message: str %}
  {% import css "/static/components/alert.css" %}
  {% import js "/static/components/alert.js" %}

  <div class="alert">{{ message }}</div>
{% endcomponent %}
```

### Requisitos

* registrar CSS e JS por componente
* deduplicar assets no render final
* permitir modos:

  * inline
  * external
  * bundle manifest
* integração futura com build pipelines

### Decisão proposta

Metadados entram no parser como nó próprio da AST, não como regex solta.

---

## 9.3 Named Slots

### Exemplo

```jinja
{% component Card %}
  {% slot header %}{% endslot %}
  {% slot footer %}{% endslot %}

  <div class="rounded-xl border bg-card shadow">
    <div class="p-6">{{ slot.header }}</div>
    <div class="p-6 pt-0">{{ content }}</div>
    <div class="flex items-center p-6 pt-0">{{ slot.footer }}</div>
  </div>
{% endcomponent %}
```

### Requisitos

* slot default (`content`)
* slots nomeados
* fallback opcional
* erro claro quando slot inexistente é usado
* verificação de slot obrigatório no futuro

### Casos de uso

* card
* modal
* dropdown
* layout
* table shells

---

## 9.4 Scoped Slots / Render Props

### Exemplo

```jinja

{% set ForEachProps = {
  "items": list
} %}

{% component ForEach %}
  {% props ForEachProps %}
  {% slot item(value, index) %}{% endslot %}

  {% for value in items %}
    {{ slot.item(value=value, index=loop.index0) }}
  {% endfor %}
{% endcomponent %}
```

### Requisitos

* slot que recebe parâmetros
* assinatura do slot declarada no próprio `slot`, sem duplicar isso em `props`
* binding nomeado
* suporte a listas, tabelas, grids e iteradores
* boa mensagem de erro quando a assinatura divergir

### Casos de uso

* `<For>`
* data tables
* menus
* autocomplete
* virtualized rendering no futuro

---

## 9.5 Built-ins declarativos de fluxo

PJX prioriza built-ins tag-based para fluxo. `{% if %}` e `{% for %}` continuam suportados como escape hatch e compatibilidade.

### Sintaxe preferencial

```jinja
<If when="user">
  <p>{{ user.name }}</p>

  <Else>
    <p>Carregando...</p>
  </Else>
</If>

<ul>
  <For each="items" as="item" index="i">
    <li>{{ i + 1 }}. {{ item }}</li>

    <Empty>
      <li>Sem itens</li>
    </Empty>
  </For>
</ul>

<Switch value="status">
  <Case when="'draft'">Rascunho</Case>
  <Case when="'published'">Publicado</Case>
  <Default>Desconhecido</Default>
</Switch>
```

### Sintaxe equivalente suportada

```jinja
{% if user %}
  <p>{{ user.name }}</p>
{% else %}
  <p>Carregando...</p>
{% endif %}

<ul>
  {% for item in items %}
    <li>{{ loop.index }}. {{ item }}</li>
  {% endfor %}
</ul>
```

### Hierarquia oficial de uso

1. preferir `<If>`, `<For>` e `<Switch>` nos exemplos, docs e happy path
2. usar `{% if %}` e `{% for %}` quando a lógica ficar mais livre ou mais densa

### Requisitos

* compilar para a mesma IR estrutural base
* `<Else>` existir apenas como filho de `<If>`
* `<Empty>` existir apenas como filho de `<For>`
* `<Case>` e `<Default>` existirem apenas como filhos de `<Switch>`
* não ter `<List>` nem `<Match>` no core

### Decisão proposta

`<If>`, `<For>` e `<Switch>` são a sintaxe preferida do PJX. Blocos Jinja permanecem como forma estrutural equivalente.

---

## 9.6 Diretivas de elemento `jx-*`

### Core inicial

* `jx-bind:*`
* `jx-class`
* `jx-show`
* `jx-text`
* `jx-html`
* `jx-on:*`

### Escopo inicial

As diretivas acima formam o core. O resto entra como diretiva customizada ou integração específica.

### Exemplo

```html
<img jx-bind:src="user.avatar" jx-bind:alt="user.name">

<li jx-class='{"active": selected_id == user.id}'>{{ user.name }}</li>

<div jx-show="open"></div>

<button jx-on:click="toggle_menu">Menu</button>
```

### Requisitos

* operar no nível de AST/elemento
* reutilizar a mesma gramática de expressão de `{{ ... }}` sempre que possível
* permitir diretivas customizadas
* ordem de transformação previsível
* erro claro para diretiva desconhecida

### Ordem de transformação sugerida

1. parse do elemento
2. aplicar diretivas core de atributo/comportamento
3. aplicar diretivas customizadas

---

## 9.7 Diretivas customizadas

### API proposta

```python
from pjx import Catalog, directive

@directive("tooltip")
def tooltip_directive(element, value, ctx):
    return ...
```

### Requisitos

* receber nó/elemento estruturado, não string crua apenas
* poder modificar atributos
* poder envolver o elemento
* poder gerar múltiplos nós
* registrar no catálogo

### Casos de uso

* tooltip
* modal wrapper
* analytics attrs
* integração Alpine/HTMX

---

## 9.8 Typed Props com validação

### Sintaxe atualizada

```jinja
{% component Button %}
  {% props
    variant: Literal["default", "secondary", "outline", "ghost"] = "default",
    size: Literal["sm", "md", "lg", "icon"] = "md",
    disabled: bool = false,
    type: str = "button"
  %}

  <button
    type="{{ type }}"
    class="{{ variant_classes[variant] }} {{ size_classes[size] }}"
    {% if disabled %}disabled{% endif %}
  >
    {{ content }}
  </button>
{% endcomponent %}
```

### Forma alternativa: alias de props

```jinja
{% set ButtonProps = {
  "variant": Literal["default", "secondary", "outline", "ghost"],
  "size": Literal["sm", "md", "lg", "icon"],
  "type": str,
  "disabled": bool
} %}

{% component Button %}
  {% props ButtonProps %}

  <button
    type="{{ type }}"
    class="{{ variant_classes[variant] }} {{ size_classes[size] }}"
    {% if disabled %}disabled{% endif %}
  >
    {{ content }}
  </button>
{% endcomponent %}
```

### Regra recomendada

* a forma inline continua sendo a forma canônica
* `{% props Nome %}` pode aceitar um alias definido antes via `set`
* esse alias deve ser resolvido em compile-time como schema estático, não como variável normal de runtime
* essa forma é melhor para reuso, não para virar a sintaxe principal do framework
* no P0, defaults continuam mais claros no bloco inline; alias de `props` deve começar simples

### Requisitos

* parser de tipos simples
* Literals / unions simples
* bool, int, float, str, list, dict
* erro em dev ao passar valor inválido
* integração com CLI `check`
* base futura para geração de schema/docs

### Decisão proposta

Começar com um subconjunto pequeno e estável.

#### P0

* str
* int
* float
* bool
* Literal
* Optional

#### P1

* list[T]
* dict[K, V]
* unions simples
* enums Python

---

## 9.9 Reactive Attributes

### Propostos

* `jx-bind:*`
* `jx-class`
* `jx-show`
* `jx-text`
* `jx-html`
* `jx-on:*`

### Backends possíveis

* Alpine-first
* HTMX-first
* bridge mínima de patch para signals

### Estratégia recomendada

No começo, mapear para Alpine/HTML attrs onde fizer sentido e usar patch incremental para signals sem depender de um runtime cliente grande.

---

## 9.10 Context / Provide-Inject

### Exemplo

```jinja
{% component Layout %}
  {% props theme: str = "light" %}
  {% provide theme %}

  <div class="app" data-theme="{{ theme }}">
    {{ content }}
  </div>
{% endcomponent %}
```

```jinja
{% component Button %}
  {% props variant: str = "default" %}
  {% inject theme %}

  {% set dark = theme == "dark" %}

  <button class="{{ 'bg-white text-black' if dark else 'bg-black text-white' }}">
    {{ content }}
  </button>
{% endcomponent %}
```

### Requisitos

* passagem implícita de dados pela árvore
* lookup lexical/hierárquico
* shadowing previsível
* fallback padrão opcional

### Casos de uso

* tema
* locale
* config de layout
* form context
* tabela/lista compartilhando config

### Risco

Pode complicar debugging. Precisa de tooling bom e inspect em dev.

---

## 9.11 Fragments

### Requisitos

* múltiplas raízes sem wrapper artificial
* funcionar em componentes comuns e layouts
* preservar ordem

### Sintaxe candidata

```jinja
{% component AppShell %}
  {% fragment %}
    <Header />
    <Main />
    <Footer />
  {% endfragment %}
{% endcomponent %}
```

ou multi-root implícito.

### Decisão proposta

Suportar multi-root de forma nativa no parser e renderer.

---

## 9.12 Async Components + Suspense

### Exemplo

```jinja
{% component UserList async %}
  {% fetch users from "users" %}

  <ul>
    {% for user in users %}
      <li>{{ user.name }}</li>
    {% endfor %}
  </ul>
{% endcomponent %}
```

### Requisitos

* render async real
* fetchers registrados
* suspense/fallback
* deduplicação de requests por render
* cache por escopo opcional

### Casos de uso

* listas remotas
* widgets de dashboard
* sidebars dinâmicas

### Decisão proposta

Entrar depois do core síncrono estar sólido.

---

## 9.13 Variáveis locais e estruturas literais

PJX mantém a sintaxe familiar de `set` para variáveis locais, dicionários e listas.

### Exemplos

```jinja
{% set my_variable = "valor" %}
{% set my_dict = {"key1": "value1", "key2": "value2"} %}
{% set my_list = ["item1", "item2", "item3"] %}
```

### Também suportar

```jinja
{% set description %}
  Texto grande aqui
  com múltiplas linhas
{% endset %}
```

### Decisão proposta

* manter `set` o mais compatível possível com o modelo mental de Jinja
* não reinventar variável local com keyword nova sem necessidade

---

## 9.14 Valores computados

Em vez de usar `def` como mecanismo central da linguagem, PJX passa a separar claramente:

* `props` para entradas do componente
* `provide/inject` para contexto compartilhado
* `set` para variáveis locais
* `signal` para valores reativos
* `action` para handlers de evento server-side
* `fragment` para múltiplas raízes
* `computed` para valores derivados

### Exemplo conceitual

```jinja
{% component Button %}
  {% props variant: str = "default", size: str = "md" %}

  {% computed classes %}
    {{ "btn-" ~ variant ~ " btn-" ~ size }}
  {% endcomputed %}

  <button class="{{ classes }}">{{ content }}</button>
{% endcomponent %}
```

### Motivação

* evita confusão com função Python real
* separa melhor responsabilidades
* deixa a linguagem mais declarativa

### Status recomendado

* `computed` pode entrar cedo no design da AST
* nenhuma abstração extra além de `computed` entra no core inicial

---

## 9.15 Async como modificador

PJX adota `async` como modificador da declaração principal, em vez de criar muitas keywords paralelas.

### Exemplo

```jinja
{% component UserList async %}
  ...
{% endcomponent %}
```

### Regra equivalente potencialmente aceitável

```jinja
{% async component UserList %}
  ...
{% endcomponent %}
```

### Decisão atual

Preferir:

```jinja
{% component UserList async %}
```

porque mantém consistência visual e simplifica a leitura da gramática.

---

## 9.16 Default como modificador ou convenção

PJX evita criar keyword isolada como `default_component`.

### Opções consideradas

1. modificador:

```jinja
{% component Page default %}
  ...
{% endcomponent %}
```

2. convenção por arquivo: se o arquivo tem um único componente top-level, ele é o default automaticamente.

### Direção recomendada

* preferir **convenção por arquivo** no início
* permitir modificador `default` se o runtime/export system realmente precisar disso

---

## 10. Reatividade server-side e signals

## 10.1 Objetivo

Permitir que partes da página sejam atualizadas de forma incremental sem re-render total.

## 10.2 Modelo mental

```text
signal muda
   ↓
dependências afetadas
   ↓
partial render
   ↓
patch HTML
   ↓
cliente atualiza
```

## 10.3 Primitivos propostos

* `signal(value)`
* `computed(fn)`
* `action(fn)`
* `jx-signal="name"`
* `jx-on:*="action_name"`

### Exemplo

```jinja
<button jx-on:click="inc">+</button>
<span jx-signal="count">{{ count }}</span>
```

Aqui, `count` representa o signal observado e `inc` uma action registrada no contexto do componente.

## 10.4 Infra mínima necessária

* ids estáveis por fragmento reativo
* registro de actions por componente ou por render
* dependency graph simples entre signal e fragmentos
* partial render por fragmento
* bridge mínima no cliente para aplicar o patch HTML retornado

## 10.5 Estratégia de transporte

### P1

HTMX request/response incremental por fragmento

### P2

WebSocket para push server-driven

## 10.6 Requisitos

* granularidade por fragmento
* dependency graph simples e observável
* SSR continua como padrão
* sem hidratação pesada
* sem runtime cliente grande

### Risco

É o recurso mais complexo do roadmap. Não deve entrar no core inicial.

---

## 11. Backend e performance

## 11.1 Estratégia de backend

PJX deve nascer com arquitetura de backend plugável:

* backend Python/Jinja2 para compatibilidade e simplicidade
* backend Rust/MiniJinja para performance

## 11.2 Decisão de arquitetura

A linguagem PJX e a AST devem ser **independentes do backend**. O compilador não pode depender diretamente de Jinja2.

Isso evita acoplamento e permite:

* backend dev
* backend prod
* testes por IR
* evolução futura para renderer nativo

## 11.3 Pipeline recomendado

```text
Parser PJX → AST PJX → Transform passes → IR → Backend adapter → Render
```

## 11.4 Otimizações esperadas

* parse cache
* AST cache
* precompile no startup
* bytecode/template cache
* asset dedupe
* dependency graph cache
* invalidation por mtime/hash em dev

---

## 12. CLI e tooling

## 12.1 Comandos essenciais

* `pjx init`
* `pjx dev`
* `pjx check`
* `pjx format`
* `pjx build`
* `pjx precompile`
* `pjx inspect`

## 12.2 `pjx check`

Deve validar:

* sintaxe
* imports
* props inválidas
* tipos inválidos
* slots inexistentes
* diretivas desconhecidas
* actions inexistentes
* referências inválidas de signal
* assets duplicados/ausentes

## 12.3 `pjx inspect`

Deve mostrar:

* AST
* IR
* árvore de componentes
* assets usados
* contexto/provide/inject
* signals/actions por componente
* output transformado

---

## 13. Fluxos principais

## 13.1 Fluxo de render normal

```text
request HTTP
   ↓
route FastAPI
   ↓
pjx.render("page")
   ↓
loader resolve componentes
   ↓
parser/AST/cache
   ↓
backend render
   ↓
HTML
   ↓
response
```

## 13.2 Fluxo com diretivas

```text
arquivo PJX
   ↓
parser encontra <li jx-class='{"active": selected_id == user.id}'>
   ↓
transform pass de diretivas
   ↓
AST reescrita
   ↓
backend renderiza atributos e nós resultantes
```

## 13.3 Fluxo com slots

```text
pai chama componente
   ↓
parser captura slot default + named slots
   ↓
compilador valida assinatura
   ↓
slot é ligado ao componente filho
   ↓
render final resolve conteúdo e escopos
```

## 13.4 Fluxo com signals (futuro)

```text
evento do usuário
   ↓
action server-side
   ↓
signal muda
   ↓
dependency graph encontra fragmentos afetados
   ↓
partial render
   ↓
bridge de patch via HTTP/WebSocket
   ↓
DOM parcial atualizado
```

---

## 14. Modo dev e modo prod

## 14.1 Dev

* mensagens ricas de erro
* source maps de template
* reload inteligente
* validação agressiva
* inspect AST/IR

## 14.2 Prod

* caches agressivos
* backend rápido
* assets deduplicados
* precompile
* auto_reload desativado
* métricas de render

---

## 15. Mensagens de erro desejadas

PJX precisa tratar erro como feature principal.

Exemplos:

* prop inválida: mostrar componente, prop, tipo esperado e valor recebido
* alias de `props` inválido: mostrar nome, origem e dizer que o schema precisa ser estático
* slot inexistente: mostrar slot declarado e slot usado
* diretiva desconhecida: sugerir nome próximo
* `inject` ausente: mostrar cadeia de componentes inspecionada
* erro em `{% for %}`: mostrar expressão, iterável e escopo
* fechamento inválido de bloco: mostrar bloco aberto e fechamento esperado, ex. `endcomponent`
* uso inválido de `computed`, `signal` ou `action` fora do local permitido

Formato ideal:

* arquivo
* linha/coluna
* trecho destacado
* sugestão objetiva

---

## 16. Compatibilidade e estratégia de adoção

## 16.1 Compatibilidade gradual

* permitir HTML puro
* permitir Jinja puro
* permitir componentes PJX
* permitir mistura progressiva

## 16.2 Estratégia de adoção

1. projeto começa com componentes simples
2. adota named slots
3. adiciona typed props
4. passa a usar diretivas e built-ins
5. opta por backend MiniJinja em produção
6. futuramente ativa signals/partials

---

## 17. MVP recomendado

### P0 — Fundacional

* parser real
* AST própria
* componentes básicos com sintaxe de bloco
* `props`
* attrs simples
* content default
* named slots
* typed props simples
* erros bons
* cache básico
* integração FastAPI
* backend inicial funcional
* fechamentos explícitos de bloco

### P0.5 — DX forte

* `pjx check`
* `pjx inspect`
* metadados CSS/JS
* built-ins básicos de fluxo (`<If>`, `<Else>`, `<For>`, `<Empty>`)
* fragments
* docs e exemplos
* formatter básico focado em blocos da linguagem

### P1 — Recursos modernos

* scoped slots
* built-ins declarativos (`<Switch>`, `<Case>`, `<Default>`)
* diretivas `jx-bind`, `jx-class`, `jx-show`, `jx-text`, `jx-html`, `jx-on`
* diretivas customizadas
* provide/inject
* `computed`

### P2 — Recursos avançados

* async components
* suspense
* signals base
* `action` registry
* partial updates via HTTP/HTMX
* scoped CSS

### P3 — Diferencial competitivo forte

* WebSocket transport
* dependency graph incremental mais otimizado
* partial reactivity mais granular
* renderer/IR mais otimizado
* backend MiniJinja maduro

---

## 18. O que deve ficar fora do core inicial

Para evitar escopo inflado, estes itens não devem bloquear o lançamento inicial:

* suspense completo
* scoped CSS complexo
* WebSocket nativo
* runtime JS próprio para reatividade
* renderer Rust 100% custom
* sistema de funções/template-defs genéricas estilo Python completo
* alternativas estruturais duplicadas para fluxo no core (`<List>`, `<Match>`, etc.)

---

## 19. Riscos principais

### 19.1 Escopo grande demais

Mitigação: separar P0/P1/P2/P3 com disciplina.

### 19.2 Parser frágil

Mitigação: AST de verdade, não regex-only.

### 19.3 Acoplamento ao backend

Mitigação: linguagem PJX independente do renderer.

### 19.4 Tipagem excessiva cedo demais

Mitigação: começar simples com subset pequeno.

### 19.5 Reatividade server-side ficar complexa demais

Mitigação: introduzir signals só depois do core de templates, mas já com fragment ids, actions e patch incremental bem definidos.

### 19.6 Gramática crescer demais cedo

Mitigação: priorizar poucas keywords fortes (`component`, `props`, `slot`, `computed`, `signal`, `provide`, `inject`, `fragment`) e adicionar novas só quando houver ganho real.

---

## 20. Decisões estratégicas recomendadas

### Decisão 1

**PJX não deve nascer como “JX mais rápido”.**
Deve nascer como **framework de templates/componentes moderno** com backend pluggable.

### Decisão 2

**AST própria é obrigatória.**
Regex pode até ajudar em protótipos, mas não pode ser a base do projeto.

### Decisão 3

**Backend agnóstico desde o começo.**
Nada de amarrar parser e transforms diretamente em Jinja2.

### Decisão 4

**Core pequeno e excelente vence core enorme e instável.**
Priorizar P0 + P1 bem feitos.

### Decisão 5

**Signals entram cedo o bastante para orientar a arquitetura, mas não antes do core ficar sólido.**
Eles são parte do diferencial do PJX, mas precisam nascer sobre fragmentos, actions e patch incremental simples.

### Decisão 6

**Sintaxe central baseada em blocos explícitos.**
Evitar comentários mágicos como mecanismo principal e preferir estruturas legíveis e próprias da gramática da linguagem.

### Decisão 7

**Não usar `def` como abstração principal de componente.**
Separar conceitos entre `component`, `props`, `signal` e `computed`.

### Decisão 8

**Preferir modificadores a explosão de keywords.**
Ex.: `component async`, `component default` quando necessário.

---

## 21. Identidade do projeto

### Definição curta

PJX é um framework de UI server-side para Python com componentes, diretivas e renderização rápida.

### Definição expandida

PJX combina a ergonomia de Vue/Solid/React com a simplicidade de HTML server-rendered e a performance de um backend moderno em Python + Rust.

### Tagline candidata

* Modern server-side UI for Python.
* Component-first templating for Python.
* Vue-like DX, server-first architecture.
* Fast server-driven UI for Python.

---

## 22. Exemplo de DX alvo

```jinja
{% component Card %}
  {% props title: str, user: Optional[dict], items: list %}
  {% slot header %}{% endslot %}
  {% slot footer %}{% endslot %}

  <div class="card">
    <div class="card-header">
      {{ slot.header or title }}
    </div>

    <div class="card-body">
      <If when="user">
        <h2>{{ user.name }}</h2>

        <Else>
          <p>Carregando...</p>
        </Else>
      </If>

      <ul>
        <For each="items" as="item" index="i">
          <li jx-class='{"active": i == 0}'>{{ i + 1 }}. {{ item }}</li>

          <Empty>
            <li>Nenhum item</li>
          </Empty>
        </For>
      </ul>

      {{ content }}
    </div>

    <div class="card-footer">
      {{ slot.footer }}
    </div>
  </div>
{% endcomponent %}
```

```jinja
<Card title="Equipe" user="{{ current_user }}" items="{{ users }}">
  {% slot header %}
    <h1>Equipe</h1>
  {% endslot %}

  <p>Total: {{ users|length }}</p>

  {% slot footer %}
    <Button variant="ghost">Fechar</Button>
  {% endslot %}
</Card>
```

Esse é o tipo de experiência que o PJX deve buscar: declaração em bloco, consumo em tag e built-ins de fluxo como sintaxe principal, mantendo Jinja e `jx-*` como suporte equivalente.

---

## 23. Roadmap resumido

### Fase 1

Core estável:

* parser
* AST
* componentes em bloco
* props
* slots
* typed props
* errors
* FastAPI

### Fase 2

Linguagem moderna:

* built-ins declarativos de fluxo (`<If>`, `<For>`, `<Switch>`)
* diretivas de elemento
* inject/provide
* fragments
* computed

### Fase 3

Capacidades avançadas:

* async/suspense
* signals base
* actions e patch incremental
* assets melhores
* extensões de diretiva
* backend MiniJinja sólido

### Fase 4

Diferencial forte:

* partial updates
* websocket
* dependency graph incremental mais sofisticado

---

## 24. Recomendação final

O caminho mais forte para o PJX é:

1. começar com um compilador sério e AST própria
2. separar linguagem de backend
3. lançar um core pequeno, bonito e confiável
4. construir a camada moderna em cima disso
5. usar performance como diferencial real, não como único argumento

Em outras palavras:

**primeiro framework bom, depois framework muito rápido.**

---

## 25. Próximos documentos derivados

A partir deste documento-base, faz sentido criar:

1. **Especificação da sintaxe PJX**
2. **Documento de arquitetura interna do compilador**
3. **PRD do CLI (`pjx check`, `pjx dev`, `pjx build`)**
4. **Especificação do sistema de slots**
5. **Especificação de typed props e validação**
6. **Especificação dos built-ins de fluxo e diretivas `jx-*`**
7. **Arquitetura de signals, actions e partial rendering**
8. **Arquitetura de backend Jinja2/MiniJinja**
9. **Gramática de blocos e palavras reservadas do PJX v0.1**

---

## 26. Tese central

Se Jinja é uma template engine e JX é um passo em direção a componentes, o PJX deve ser:

**um framework server-side moderno de UI para Python, com sintaxe declarativa, componentes fortes, renderização rápida e espaço real para reatividade incremental.**
