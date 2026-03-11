# PJX Examples

Estes arquivos mostram como esperamos que o PJX funcione com base no [idea.md](/home/debian/proj/pjx/idea.md).

Eles nao sao implementacao executavel ainda. Sao exemplos de sintaxe, organizacao de projeto e DX alvo.

Estrutura:

* `components/ui`: componentes reutilizaveis de interface
* `layouts`: layouts compartilhados
* `pages`: paginas `.jinja` com sintaxe PJX
* `directives`: diretivas customizadas
* `api/routers`: routers FastAPI
* `catalog.py`: configuracao do `Catalog`
* `main.py`: app FastAPI fim a fim
* `data.py`: dados fake para os exemplos

Convencoes mostradas aqui:

* todos os imports ficam no topo do arquivo, antes do primeiro `{% component %}`
* componentes sao importados por alias de caminho `@/...`
* paginas importam layouts e componentes explicitamente
* enquanto nao houver syntax highlight de `.pjx`, os exemplos usam extensao `.jinja`
* built-ins de fluxo sao o caminho preferido
* `{% if %}` e `{% for %}` continuam validos
* `jx-*` fica para comportamento de elemento

Exemplo de import:

```jinja
{% import css "/static/components/ui/button.css" %}
{% import "@/layouts/AppLayout.jinja" as AppLayout %}
{% import "@/components/ui/Button.jinja" as Button %}
{% import "@/components/ui/Card.jinja" as Card %}

{% component DashboardPage %}
  ...
{% endcomponent %}
```

Arquivos principais:

* `components/ui/Button.jinja`: alias de props, `computed`, assets e `inject`
* `components/ui/Card.jinja`: named slots e `content`
* `components/ui/ForEach.jinja`: scoped slots e loop reutilizavel
* `components/ui/StatusBadge.jinja`: componente simples de UI com `computed`
* `layouts/AppLayout.jinja`: layout compartilhado com `provide`
* `pages/dashboard.jinja`: pagina completa com imports, slots, `<If>`, `<For>` e `jx-*`
* `pages/status_overview.jinja`: imports, `<Switch>`, `ForEach` e fallback com Jinja
* `pages/signals_counter.jinja`: imports, `signal`, `action`, `jx-signal` e `jx-on:*`
* `catalog.py`: alias `@`, diretivas e helpers de render
* `api/routers/pages.py`: rotas HTML
* `api/routers/actions.py`: actions e partials
* `api/routers/api.py`: endpoints JSON
