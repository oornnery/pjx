# PJX — Documento-Base

## 1. Resumo

PJX e um framework de UI server-side para Python com componentes, templates, slots, diretivas e reatividade parcial.

Ele busca combinar:

* ergonomia de frameworks modernos
* HTML como saida principal
* renderizacao server-first
* integracao forte com FastAPI, HTMX e Alpine
* arquitetura preparada para backends em Python e Rust

Mental model:

```text
Vue/Solid DX
+ HTML server-rendered
+ Jinja heritage
+ HTMX/Alpine incremental
+ FastAPI no backend
+ MiniJinja/Rust para performance
```

O problema que o PJX resolve e o espaco entre:

* templates simples, mas pouco componiveis
* engines rapidas, mas sem ergonomia de framework
* stacks client-heavy que exigem SPA, bundler e hydration

O objetivo do PJX e ser:

* component-first
* declarativo
* server-first
* incremental no cliente
* rapido por design

Nao objetivos iniciais:

* substituir React/Vue em SPAs complexas
* criar VDOM no cliente
* competir com bundlers JS
* colocar todas as features modernas no core inicial

Publico-alvo:

* devs Python que querem UI moderna sem SPA
* projetos FastAPI, Starlette ou Quart
* dashboards, backoffices, SaaS internos, blogs e apps CRUD server-driven

Proposta de valor:

* componentes reutilizaveis e tipados
* slots nomeados e scoped slots
* fluxo declarativo legivel
* diretivas em elementos
* renderizacao rapida
* bons erros em dev
* caminho real para partial reactivity

---

## 2. Principios de Design

* HTML-first: o template deve parecer HTML melhorado, nao uma DSL alienigena.
* Server-first: o servidor continua sendo a fonte da verdade.
* Progressive enhancement: recursos reativos entram por camadas.
* Declarativo > imperativo: componentes, slots e diretivas vencem boilerplate.
* Fast by design: toda feature precisa justificar custo de parse, transform e render.
* Escape hatch real: HTML puro, Jinja puro, Alpine puro e Python puro continuam validos.
* Excelente DX: erros bons, tipagem util, `check`, `inspect` e sintaxe previsivel.
* Gramática explicita: recursos centrais entram como blocos ou nos da AST, nao como comentarios magicos.

Filtro de simplicidade:

* se mais de uma sintaxe resolver o mesmo problema, o PJX precisa declarar uma forma preferida
* o que for suportado mas nao preferido deve ter papel claro
* sintaxe nova so entra quando melhora AST, leitura e mensagens de erro ao mesmo tempo
* se algo puder nascer como extensao ou fase posterior, nao deve complicar o P0

---

## 3. Arquitetura

Pipeline geral:

```text
arquivo .jinja (temporariamente nos exemplos; extensao-alvo: .pjx)
   ↓
lexer / parser PJX
   ↓
AST PJX
   ↓
transform passes
- props
- imports
- slots
- built-ins de fluxo
- diretivas
- context
- async
- signals
   ↓
IR intermediaria
   ↓
backend adapter
- Jinja2 (compat/dev)
- MiniJinja (perf/prod)
   ↓
HTML final
```

Camadas:

* Frontend da linguagem: parse, AST, validacao e erros.
* Compilador: transforms, built-ins, diretivas, props e IR.
* Runtime: render, contexto, cache, async, signals e actions.
* Integracao web: FastAPI helpers, HTMX helpers, static assets, partial rendering e dev mode.

Decisao central:

* a linguagem PJX precisa ser independente do backend
* parser e transforms nao podem depender diretamente de Jinja2
* a IR e o contrato entre linguagem e renderer

---

## 4. Design da Linguagem

### 4.1 Regras Centrais

Gramática canônica do PJX v0.1:

* declaracao de componente por bloco: `{% component Nome %} ... {% endcomponent %}`
* consumo de componente por tag em `PascalCase`: `<Card />` e `<Card>...</Card>`
* props por `{% props ... %}`
* expressoes por `{{ ... }}`
* conteudo default por `{{ content }}`
* slots nomeados por `{% slot nome %}` e acesso por `slot.nome`
* fluxo preferencial por `<If>`, `<For>` e `<Switch>`
* suporte equivalente por `{% if %}`, `{% for %}` e `{% set %}`
* diretivas `jx-*` restritas a comportamento e atributos de elemento
* imports e metadados locais por `{% import ... %}` no topo do arquivo sempre que possivel
* modificadores no final da declaracao principal, ex.: `{% component UserList async %}`

Decisoes de sintaxe:

* nao usar `{% end %}` generico
* usar fechamentos explicitos:
  * `{% endcomponent %}`
  * `{% endslot %}`
  * `{% endcomputed %}`
* `async` e `default` entram como modificadores
* `def` nao e a abstracao principal do framework

### 4.2 Componentes

Sintaxe base:

```jinja
{% import css "/static/css/button.css" %}

{% component Button %}
  {% props
    variant: Literal["default", "secondary", "outline", "ghost"] = "default",
    size: Literal["sm", "md", "lg", "icon"] = "md",
    type: str = "button",
    disabled: bool = false
  %}

  <button
    type="{{ type }}"
    class="btn btn-{{ variant }} btn-{{ size }}"
    {% if disabled %}disabled{% endif %}
  >
    {{ content }}
  </button>
{% endcomponent %}
```

Consumo:

```jinja
<Button variant="ghost">Salvar</Button>

<Card title="Dashboard" user="{{ current_user }}">
  {% slot header %}
    <h2>Resumo</h2>
  {% endslot %}

  <p>Conteudo principal</p>

  {% slot footer %}
    <Button variant="ghost">Fechar</Button>
  {% endslot %}
</Card>
```

Regras:

* componente e declarado como bloco e consumido como tag
* a declaracao de componente deve virar um no proprio da AST
* todos os imports devem ficar no topo do arquivo sempre que possivel
* attrs extras entram no P0 como bag reservada `attrs`
* o core inicial nao precisa de spread sintatico nem merge magico de attrs

### 4.3 Metadados por Componente

Direcao:

```jinja
{% import css "/static/components/alert.css" %}
{% import js "/static/components/alert.js" %}

{% component Alert %}
  {% props message: str %}

  <div class="alert">{{ message }}</div>
{% endcomponent %}
```

Requisitos:

* registrar CSS e JS por componente
* manter todos os imports agrupados no topo do arquivo como boa pratica
* deduplicar assets no render final
* suportar `inline`, `external` e `bundle manifest`
* entrar no parser como no proprio da AST

### 4.4 Slots

Named slots:

```jinja
{% component Card %}
  {% slot header %}{% endslot %}
  {% slot footer %}{% endslot %}

  <div class="card">
    <div class="card-header">{{ slot.header }}</div>
    <div class="card-body">{{ content }}</div>
    <div class="card-footer">{{ slot.footer }}</div>
  </div>
{% endcomponent %}
```

Scoped slots:

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

Requisitos:

* `content` como slot default
* slots nomeados
* scoped slots com parametros
* assinatura do slot declarada no proprio `slot`
* erro claro para slot inexistente ou assinatura invalida

### 4.5 Built-ins de Fluxo

Sintaxe preferencial:

```jinja
<If when="user">
  <p>{{ user.name }}</p>

  <Else>
    <p>Carregando...</p>
  </Else>
</If>

<For each="items" as="item" index="i">
  <li>{{ i + 1 }}. {{ item }}</li>

  <Empty>
    <li>Sem itens</li>
  </Empty>
</For>

<Switch value="status">
  <Case when="'draft'">Rascunho</Case>
  <Case when="'published'">Publicado</Case>
  <Default>Desconhecido</Default>
</Switch>
```

Forma estrutural equivalente:

```jinja
{% if user %}
  <p>{{ user.name }}</p>
{% else %}
  <p>Carregando...</p>
{% endif %}

{% for item in items %}
  <li>{{ loop.index }}. {{ item }}</li>
{% endfor %}
```

Hierarquia oficial:

1. docs e exemplos priorizam `<If>`, `<For>` e `<Switch>`
2. `{% if %}` e `{% for %}` existem como escape hatch e compatibilidade

Regras:

* `<Else>` so pode existir dentro de `<If>`
* `<Empty>` so pode existir dentro de `<For>`
* `<Case>` e `<Default>` so podem existir dentro de `<Switch>`
* todas as formas precisam compilar para a mesma IR estrutural base
* `<List>` e `<Match>` ficam fora do core para evitar duplicacao

### 4.6 Diretivas `jx-*`

Core inicial:

* `jx-bind:*`
* `jx-class`
* `jx-show`
* `jx-text`
* `jx-html`
* `jx-on:*`

Exemplo:

```html
<img jx-bind:src="user.avatar" jx-bind:alt="user.name">

<li jx-class='{"active": selected_id == user.id}'>{{ user.name }}</li>

<div jx-show="open"></div>

<button jx-on:click="toggle_menu">Menu</button>
```

Requisitos:

* operar no nivel de AST/elemento
* reutilizar a mesma gramática de expressao de `{{ ... }}` quando possivel
* permitir diretivas customizadas
* ter ordem de transform previsivel
* gerar erro claro para diretiva desconhecida

Ordem sugerida:

1. parse do elemento
2. aplicar diretivas core de atributo/comportamento
3. aplicar diretivas customizadas

Diretivas customizadas:

```python
from pjx import Catalog, directive

@directive("tooltip")
def tooltip_directive(element, value, ctx):
    return ...
```

A API de diretiva deve permitir:

* receber no estruturado, nao string crua apenas
* modificar atributos
* envolver o elemento
* gerar multiplos nos
* registrar no catalogo

### 4.7 Typed Props

Forma canônica:

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

Forma alternativa por alias:

```jinja
{% set ButtonProps = {
  "variant": Literal["default", "secondary", "outline", "ghost"],
  "size": Literal["sm", "md", "lg", "icon"],
  "type": str,
  "disabled": bool
} %}

{% component Button %}
  {% props ButtonProps %}
  ...
{% endcomponent %}
```

Regra recomendada:

* inline continua sendo a forma principal
* `{% props Nome %}` aceita alias estatico definido antes por `set`
* esse alias deve ser resolvido em compile-time, nao como variavel comum de runtime
* defaults ficam mais claros na forma inline

Suporte de tipos:

* P0: `str`, `int`, `float`, `bool`, `Literal`, `Optional`
* P1: `list[T]`, `dict[K, V]`, unions simples e enums Python

### 4.8 Variaveis, Computed, Contexto, Fragments e Modificadores

Variaveis locais:

```jinja
{% set my_variable = "valor" %}
{% set my_dict = {"key1": "value1", "key2": "value2"} %}
{% set my_list = ["item1", "item2", "item3"] %}
```

Tambem suportar:

```jinja
{% set description %}
  Texto grande aqui
{% endset %}
```

Valores computados:

```jinja
{% component Button %}
  {% props variant: str = "default", size: str = "md" %}

  {% computed classes %}
    {{ "btn-" ~ variant ~ " btn-" ~ size }}
  {% endcomputed %}

  <button class="{{ classes }}">{{ content }}</button>
{% endcomponent %}
```

Contexto:

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
  {% inject theme %}
  <button class="{{ 'dark' if theme == 'dark' else 'light' }}">{{ content }}</button>
{% endcomponent %}
```

Fragments:

* multi-root deve ser suportado nativamente
* `fragment` explicito nao precisa ser obrigatorio no P0 se multi-root implicito resolver

Async e default:

```jinja
{% component UserList async %}
  ...
{% endcomponent %}
```

```jinja
{% component Page default %}
  ...
{% endcomponent %}
```

Direcao:

* preferir `component async`
* preferir convencao por arquivo para componente default
* permitir modificador `default` so se export system realmente precisar

### 4.9 Async Components e Suspense

Exemplo:

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

Requisitos:

* render async real
* fetchers registrados
* suspense
* deduplicacao de requests por render
* cache por escopo opcional

Decisao:

* entra depois do core sincrono ficar solido

---

## 5. Signals e Partial Reactivity

Objetivo:

* permitir atualizacao parcial sem re-render total da pagina
* manter SSR como padrao
* evitar hydration pesada

Modelo mental:

```text
signal muda
   ↓
dependencias afetadas
   ↓
partial render
   ↓
patch HTML
   ↓
cliente atualiza
```

Primitivos propostos:

* `signal(value)`
* `computed(fn)`
* `action(fn)`
* `jx-signal="name"`
* `jx-on:*="action_name"`

Exemplo:

```jinja
<button jx-on:click="inc">+</button>
<span jx-signal="count">{{ count }}</span>
```

Aqui:

* `count` e o signal observado
* `inc` e uma action registrada no contexto do componente

Infra minima necessaria:

* ids estaveis por fragmento reativo
* registro de actions por componente ou por render
* dependency graph simples entre signal e fragmentos
* partial render por fragmento
* bridge minima no cliente para aplicar o patch HTML retornado

Transporte:

* P1/P2 inicial: HTTP incremental via HTMX
* P3: WebSocket para push server-driven

Requisitos:

* granularidade por fragmento
* dependency graph observavel
* SSR continua como padrao
* sem runtime cliente grande

Risco:

* e a parte mais dificil do roadmap
* precisa orientar a arquitetura cedo, mas nao deve travar o core de templates

---

## 6. Backend, Performance e Tooling

### 6.1 Backend

PJX deve nascer com backend pluggable:

* Jinja2 para compatibilidade e simplicidade
* MiniJinja para performance em producao

Decisao:

* linguagem e AST independentes do renderer
* backend e adaptador, nao centro da linguagem

### 6.2 Otimizacoes Esperadas

* parse cache
* AST cache
* precompile no startup
* bytecode/template cache
* asset dedupe
* dependency graph cache
* invalidation por `mtime` ou hash em dev

### 6.3 CLI

Comandos essenciais:

* `pjx init`
* `pjx dev`
* `pjx check`
* `pjx format`
* `pjx build`
* `pjx precompile`
* `pjx inspect`

`pjx check` deve validar:

* sintaxe
* imports
* props invalidas
* tipos invalidos
* slots inexistentes
* diretivas desconhecidas
* actions inexistentes
* referencias invalidas de signal
* assets duplicados ou ausentes

`pjx inspect` deve mostrar:

* AST
* IR
* arvore de componentes
* assets usados
* contexto `provide/inject`
* signals e actions por componente
* output transformado

### 6.4 Modo Dev e Prod

Dev:

* mensagens ricas de erro
* source maps de template
* reload inteligente
* validacao agressiva
* inspect de AST e IR

Prod:

* caches agressivos
* backend rapido
* assets deduplicados
* precompile
* `auto_reload` desligado
* metricas de render

### 6.5 Mensagens de Erro

PJX precisa tratar erro como feature.

Mensagens desejadas:

* prop invalida: componente, prop, tipo esperado e valor recebido
* alias de `props` invalido: nome, origem e aviso de schema estatico
* slot inexistente: slot declarado e slot usado
* diretiva desconhecida: sugestao de nome proximo
* `inject` ausente: cadeia de componentes inspecionada
* erro em `{% for %}`: expressao, iteravel e escopo
* fechamento invalido de bloco: bloco aberto e fechamento esperado
* uso invalido de `computed`, `signal` ou `action`

Formato ideal:

* arquivo
* linha e coluna
* trecho destacado
* sugestao objetiva

---

## 7. Compatibilidade e Adocao

Compatibilidade gradual:

* HTML puro continua valido
* Jinja puro continua valido
* componentes PJX convivem com templates existentes
* migracao pode ser incremental

Estrategia de adocao:

1. projeto comeca com componentes simples
2. adota named slots
3. adiciona typed props
4. passa a usar built-ins de fluxo e diretivas
5. migra para MiniJinja em producao se fizer sentido
6. ativa signals e partial rendering depois do core estabilizar

---

## 8. Escopo e Roadmap

### 8.1 MVP Recomendado

P0 — Fundacional:

* parser real
* AST propria
* componentes em bloco
* `props`
* attrs simples
* `content` default
* named slots
* typed props simples
* erros bons
* cache basico
* integracao FastAPI
* backend inicial funcional
* fechamentos explicitos de bloco

P0.5 — DX forte:

* `pjx check`
* `pjx inspect`
* metadados CSS/JS
* built-ins basicos de fluxo: `<If>`, `<Else>`, `<For>`, `<Empty>`
* fragments
* docs e exemplos
* formatter basico

P1 — Linguagem moderna:

* scoped slots
* `<Switch>`, `<Case>`, `<Default>`
* `jx-bind`, `jx-class`, `jx-show`, `jx-text`, `jx-html`, `jx-on`
* diretivas customizadas
* `provide/inject`
* `computed`

P2 — Recursos avancados:

* async components
* suspense
* signals base
* `action` registry
* partial updates via HTTP/HTMX
* scoped CSS

P3 — Diferencial forte:

* WebSocket transport
* dependency graph incremental mais sofisticado
* partial reactivity mais granular
* renderer/IR mais otimizado
* backend MiniJinja maduro

### 8.2 Fora do Core Inicial

Para evitar escopo inflado, estes itens nao devem bloquear o lancamento inicial:

* suspense completo
* scoped CSS complexo
* WebSocket nativo
* runtime JS proprio para reatividade
* renderer Rust 100% custom
* sistema generico de funcoes/template-defs estilo Python
* alternativas estruturais duplicadas para fluxo, como `<List>` e `<Match>`

### 8.3 Riscos Principais

* escopo grande demais
  * mitigacao: separar P0, P1, P2 e P3 com disciplina
* parser fragil
  * mitigacao: AST real, nao regex-only
* acoplamento ao backend
  * mitigacao: linguagem separada do renderer
* tipagem excessiva cedo demais
  * mitigacao: comecar com subset pequeno
* signals complexos demais
  * mitigacao: introduzir signals sobre fragment ids, actions e patch incremental simples
* gramática crescer cedo demais
  * mitigacao: priorizar poucas keywords fortes e expandir so quando houver ganho real

### 8.4 Decisoes Estrategicas

* PJX nao deve nascer como "JX mais rapido"; ele deve nascer como framework moderno de templates e componentes.
* AST propria e obrigatoria.
* Backend agnostico desde o inicio.
* Core pequeno e excelente vence core enorme e instavel.
* Signals precisam orientar a arquitetura, mas nao podem atrasar o fundamento do framework.
* Sintaxe central baseada em blocos explicitos e built-ins declarativos.
* `def` nao e abstracao principal de componente.
* Modificadores vencem explosao de keywords.

---

## 9. Exemplo de DX Alvo

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

Esse e o tipo de experiencia que o PJX deve buscar:

* declaracao em bloco
* consumo em tag
* fluxo declarativo como sintaxe principal
* Jinja como forma equivalente
* diretivas `jx-*` para comportamento de elemento

---

## 10. Proximos Documentos

A partir deste documento-base, os proximos documentos mais uteis sao:

1. especificacao da sintaxe PJX
2. arquitetura interna do compilador
3. PRD do CLI
4. especificacao do sistema de slots
5. especificacao de typed props e validacao
6. especificacao dos built-ins de fluxo e diretivas `jx-*`
7. arquitetura de signals, actions e partial rendering
8. arquitetura de backend Jinja2/MiniJinja
9. gramática de blocos e palavras reservadas do PJX v0.1

---

## 11. Tese Central

Se Jinja e uma template engine e JX e um passo em direcao a componentes, o PJX deve ser:

**um framework server-side moderno de UI para Python, com sintaxe declarativa, componentes fortes, renderizacao rapida e espaco real para reatividade incremental.**
