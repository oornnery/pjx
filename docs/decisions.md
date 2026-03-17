# Decisions

Este arquivo registra as principais decisoes de design assumidas no estado
atual do PJX.

## 1. FastAPI e dependencia principal

Decisao:

* FastAPI faz parte do core do pacote

Motivo:

* a API publica do PJX gira em torno de `FastAPI`, `Request`, `Response`,
  `StaticFiles` e rotas registradas via `init_app`
* tratar FastAPI como extra deixava a historia do framework artificial

## 2. PJX registra no app via init_app

Decisao:

* `Pjx.init_app(app)` registra rotas e assets diretamente no FastAPI do usuario
* sem sub-app separado

Motivo:

* simplifica middleware, CORS e static mounts
* rotas PJX aparecem no mesmo OpenAPI schema
* `app.state.pjx` e `app.state.pjx_catalog` ficam acessiveis

## 3. PjxRouter no lugar de API declarativa generica

Decisao:

* usar `PjxRouter` como coletor de `page` e `action`

Motivo:

* o nome combina com `APIRouter`
* comunica melhor o papel publico do objeto

## 4. Templates em `templates/`

Decisao:

* consolidar `components`, `layouts` e `pages` dentro de uma raiz `templates/`

Motivo:

* simplifica descoberta
* combina com a expectativa de projetos FastAPI/Jinja
* melhora a historia de mounts adicionais

## 5. Prefixo de templates via `@prefix/...`

Decisao:

* mounts extras sao acessados como `@admin/...`

Motivo:

* a raiz principal continua limpa
* evita colisao entre paths relativos de mounts diferentes

## 6. Sintaxe `@directive` canonica

Decisao:

* toda diretiva PJX usa `@` como prefixo: `@props`, `@from`, `@component`, etc.
* extensao canonica e `.pjx`

Motivo:

* distingue claramente PJX de Jinja nativo
* evita ambiguidade com `{% %}` que e passthrough para Jinja

## 7. HTMX + Alpine como enhancement

Decisao:

* HTMX e Alpine sao suporte de primeira classe
* runtime reativo proprio completo ainda nao e prioridade

Motivo:

* entrega interatividade agora
* mantem o projeto server-first

## 8. render() como Depends

Decisao:

* `render(template, layout=None)` retorna `Page` ou `Template` via FastAPI Depends
* `Page.__call__(**context)` e `Template.__call__(**context)` retornam `HTMLResponse`

Motivo:

* aproveita o sistema de DI do FastAPI
* permite usar em rotas sem PjxRouter
* context processors sao executados automaticamente

## 9. CLI primeiro como tooling do projeto

Decisao:

* `pjx check` e `pjx format` fazem parte do framework

Motivo:

* linguagem nova sem tooling novo vira custo, nao vantagem
* check e format aceleram evolucao da sintaxe

## 10. Typer + Rich para CLI

Decisao:

* usar `Typer` para parsing e `Rich` para output

## 11. Numeros estaveis nas validacoes

Decisao:

* o `check` usa codigos estaveis como `[101] parse_error`

## 12. MiniJinja como backend alternativo

Decisao:

* `MiniJinjaRuntime` e um drop-in para `Runtime` usando `minijinja` (Rust)
* selecionado via `Pjx(renderer="minijinja")`
* requer extra: `pjx[minijinja]`

Motivo:

* MiniJinja oferece render significativamente mais rapido que Jinja2 em
  templates simples (medido com `pjx bench`)
* a API e identica: `render_root`, `_render_component`, cache por mtime
* a coexistencia de backends permite comparar e migrar gradualmente

Consequencia:

* `catalog.py` expoe `_create_runtime(renderer, catalog)` como factory
* `fastapi.py` aceita `renderer=` e `bundle=` no construtor de `Pjx`
* o default continua sendo Jinja2

## 13. Bundle mode para templates auto-contidos

Decisao:

* `compile_pjx(bundle=True)` emite chamadas diretas de macro em vez de
  `__pjx_render_component`
* `_ImportResolver` resolve imports recursivamente e gera macro preamble
* `pjx compile --bundle` produz `.jinja` auto-contidos sem callbacks Python

Motivo:

* elimina o overhead de callbacks Python por componente no MiniJinja
* permite auditoria do output compilado
* habilita deploy estatico de templates pre-compilados

Consequencia:

* bundle mode e opt-in (`bundle=False` por default)
* imports dinamicos ou condicionais nao sao suportados no bundle resolver
