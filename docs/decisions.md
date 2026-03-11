# Decisions

Este arquivo registra as principais decisoes de design assumidas no estado
atual do PJX.

## 1. FastAPI e dependencia principal

Decisao:

* FastAPI faz parte do core do pacote

Motivo:

* a API publica do PJX gira em torno de `FastAPI`, `Request`, `Response`,
  `StaticFiles` e mount de sub-app
* tratar FastAPI como extra deixava a historia do framework artificial

Tradeoff:

* o pacote fica menos agnostico a framework no curto prazo

## 2. PJX como sub-app montado

Decisao:

* o app principal continua sendo FastAPI
* o PJX materializa um sub-app com `pjx.app(...)`

Motivo:

* deixa a responsabilidade do app host no FastAPI
* reduz o acoplamento da API publica
* simplifica mount de static, pages e actions

## 3. PJXRouter no lugar de API declarativa genérica

Decisao:

* usar `PJXRouter` como coletor de `page`, `action` e `directive`

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
* reaproveita um modelo mental ja usado em alias de templates

API atual:

```python
templates=[
    "templates",
    {"prefix": "admin", "path": "admin_templates"},
]
```

## 6. Parser estrutural antes de runtime novo

Decisao:

* sair do modo puramente regex-first na estrutura do arquivo antes de atacar runtime reativo nativo

Motivo:

* parser e AST sao a base para tooling, validacao, erros e evolucao de sintaxe
* sem isso, cada feature nova custa caro demais

## 7. HTMX + Alpine como enhancement

Decisao:

* HTMX e Alpine sao suporte de primeira classe
* runtime reativo proprio completo ainda nao e prioridade

Motivo:

* isso entrega interatividade agora
* mantem o projeto server-first
* evita inventar um runtime pesado cedo demais

## 8. Tailwind separado de browser integrations

Decisao:

* Tailwind e integracao de build
* HTMX e Alpine sao integrations de runtime

Motivo:

* Tailwind depende de scanner, config e build/watch
* nao faz sentido tratá-lo como simples script injetado

## 9. CLI primeiro como tooling do projeto

Decisao:

* `pjx check` e `pjx format` fazem parte do framework

Motivo:

* linguagem nova sem tooling novo vira custo, nao vantagem
* check e format aceleram evolucao da sintaxe

## 10. Typer + Rich para CLI

Decisao:

* usar `Typer` para parsing e `Rich` para output

Motivo:

* API mais clara
* bom suporte a testes
* base melhor para crescer com mais comandos

## 11. Numeros estaveis nas validacoes

Decisao:

* o `check` usa codigos estaveis como `[101] parse_error`

Motivo:

* deixa a saida mais escaneavel
* melhora a automacao
* permite documentacao consistente dos erros

## 12. Renderer continua Jinja2 por enquanto

Decisao:

* manter Jinja2 como backend de render atual

Motivo:

* o foco imediato e fechar linguagem, compiler, runtime e tooling
* trocar backend cedo demais aumentaria a superficie de risco

Consequencia:

* ainda existe acoplamento a Jinja2 no runtime
* `minijinja` continua como proxima fase, nao como base atual
