# PJX Examples

Estes arquivos mostram o caminho atual da API publica do PJX.
Sao executaveis e servem como exemplo de DX alvo.

Estrutura:

* `templates/layouts`: layouts compartilhados (`.pjx`)
* `templates/pages`: paginas `.pjx` com sintaxe PJX
* `api/routers`: modulos que declaram rotas sobre PjxRouter
* `main.py`: cria `Pjx(...)` e `FastAPI(...)`, registra com `pjx.init_app(app)`
* `data.py`: dados fake para os exemplos

Convencoes mostradas aqui:

* todos os imports ficam no topo do arquivo com `@from` e `@import`
* componentes sao importados de modulos PJX: `@from pjx.ui import Button`
* extensao canonica e `.pjx`
* built-ins de fluxo (`<Show>`, `<For>`, `<Switch>`) sao o caminho preferido
* HTMX faz o transporte incremental
* Alpine cuida do estado local pequeno
* assets de browser sao servidos pelo pacote em `/_pjx/js/...`
* CSS do framework via `css="pjx"` no construtor

Exemplo de template:

```text
@from pjx.ui import Button, Badge
@from pjx.layout import Card
@import "layouts/Layout.pjx"

@props { title: str = "Home" }

<Layout title="{{ title }}">
  <Card title="Example">
    <Button label="Click" />
    <Badge variant="ready" text="live" />
  </Card>
</Layout>
```

Arquivos principais:

* `templates/layouts/Layout.pjx`: layout compartilhado com `@slot default` e `@slot head?`
* `templates/pages/showcase.pjx`: pagina com props, `<For>`, componentes, slots nomeados
* `templates/pages/apps.pjx`: todo app e counter com HTMX
* `templates/pages/kitchen.pjx`: todos os componentes do framework
* `templates/pages/counter.pjx`: counter HTMX com `@bind`
* `main.py`: cria Pjx com `templates_dir`, `browser`, `css` e registra routers
* `api/routers/pages.py`: exporta `pages = PjxRouter()`
* `api/routers/actions.py`: exporta `actions = PjxRouter()`

Tooling:

* `uv run pjx check exemples.main:pjx`: valida templates e rotas HTML do exemplo
* `uv run pjx format exemples.main:pjx --check`: mostra quais templates sairiam formatados
