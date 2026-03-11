# PJX Examples

Estes arquivos mostram o caminho atual da API publica do PJX com base no
[idea.md](/home/oornnery/proj/pjx/idea.md).

Eles sao executaveis e servem como exemplo de DX alvo.

Estrutura:

* `templates/components/ui`: componentes reutilizaveis de interface
* `templates/layouts`: layouts compartilhados
* `templates/pages`: paginas `.jinja` com sintaxe PJX
* `directives`: diretivas customizadas
* `api/routers`: modulos que declaram rotas sobre coletores declarativos
* `main.py`: cria o `PJX(...)` com `templates="templates"` e `routers=[...]`, o `FastAPI(...)` principal e monta o sub-app PJX
* `data.py`: dados fake para os exemplos

Convencoes mostradas aqui:

* todos os imports ficam no topo do arquivo, antes do primeiro `{% component %}`
* componentes sao importados por alias de caminho `@/...`
* paginas importam layouts e componentes explicitamente
* enquanto nao houver syntax highlight de `.pjx`, os exemplos usam extensao `.jinja`
* built-ins de fluxo sao o caminho preferido
* `{% if %}` e `{% for %}` continuam validos
* HTMX faz o transporte incremental
* Alpine cuida do estado local pequeno
* os assets de browser sao servidos pelo proprio pacote em `/_pjx/js/...`
* `jx-*` continua reservado para recursos nativos do PJX

Exemplo de import:

```jinja
{% import css "/static/css/components/ui/button.css" %}
{% import "layouts/AppLayout.jinja" as AppLayout %}
{% import "components/ui/Button.jinja" as Button %}
{% import "components/ui/Card.jinja" as Card %}

{% component DashboardPage %}
  ...
{% endcomponent %}
```

Arquivos principais:

* `templates/components/ui/Button.jinja`: alias de props, `computed` e passthrough de attrs
* `templates/components/ui/Card.jinja`: named slots, `content` e attrs no root
* `templates/components/ui/ForEach.jinja`: scoped slots e loop reutilizavel
* `templates/components/ui/StatusBadge.jinja`: componente simples de UI com `computed`
* `templates/layouts/AppLayout.jinja`: layout compartilhado usando `{{ assets.render() }}`
* `templates/pages/dashboard.jinja`: pagina completa com imports, slots, `<If>`, `<For>` e diretiva customizada
* `templates/pages/status_overview.jinja`: imports, `<Switch>`, `ForEach` e fallback com Jinja
* `templates/pages/signals_counter.jinja`: counter incremental via HTMX com fragment target
* `templates/pages/studio.jinja`: HTMX para partial render + Alpine para estado local do input
* `main.py`: passa `pages`, `actions` e `tooltips` direto para `PJX(..., templates=\"templates\", routers=[...])`, liga HTMX/Alpine e monta o sub-app PJX
* `api/routers/pages.py`: exporta `pages = PJXRouter()`
* `api/routers/actions.py`: exporta `actions = PJXRouter()`
* `directives/tooltip.py`: exporta `tooltips = PJXRouter()`
* `api/routers/api.py`: exporta `router = APIRouter(...)`

Tooling:

* `uv run pjx check exemples.main:pjx`: valida templates e rotas HTML do exemplo
* `uv run pjx format exemples.main:pjx --check`: mostra quais templates sairiam no formato canonico
* se voce quiser montar outra arvore de templates, o `PJX(...)` aceita `templates=[\"templates\", {\"prefix\": \"admin\", \"path\": \"admin_templates\"}]` e isso expoe imports como `@admin/...`
