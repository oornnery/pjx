# TODO

Este arquivo registra o que falta para o PJX sair de prototipo funcional para
miniframework maduro.

## Norte do Projeto

Objetivo:

* linguagem propria para componentes server-first
* FastAPI como base real do app host
* compile pipeline clara: linguagem -> parser/AST -> compiler/IR -> renderer
* HTMX e Alpine como enhancement
* DX simples, com pouco boilerplate

## Fase 0: consolidar o que ja existe

Meta:

* deixar a base atual previsivel, documentada e usavel

Checklist:

* [x] `PJX` integrado como sub-app FastAPI
* [x] `PJXRouter`
* [x] `templates/` como raiz
* [x] mounts com prefixo `@prefix/...`
* [x] parser estrutural do arquivo
* [x] `pjx check`
* [x] `pjx format`
* [x] docs iniciais de arquitetura e uso

## Fase 1: endurecer o core

Meta:

* melhorar contratos internos e reduzir fragilidade do runtime

### Catalog

* [ ] `add_package(...)`
* [ ] `collect_assets(output_dir)`
* [ ] filtros, tests e globals mais explicitos
* [ ] introspecao de mounts e aliases mais rica

### Runtime

* [ ] melhorar extração de partials para algo menos fragil que busca por `id`
* [ ] cache mais observavel e com estatisticas
* [ ] separar melhor render de assets e render de markup
* [ ] interface explicita de renderer backend

### Attrs e directives

* [ ] enriquecer `AttrBag` com `set`, `setdefault`, `add_class`, `remove_class`
* [ ] mapear melhor o contrato das diretivas customizadas
* [ ] documentar o que e core directive vs custom directive

## Fase 2: parser e compiler mais fortes

Meta:

* sair do modo “estrutura forte, markup medio” para uma base bem mais confiavel

### Parser

* [ ] introduzir lexer/token stream
* [ ] spans e mensagens de erro melhores
* [ ] parser do markup menos baseado em transformacao de string
* [ ] formatter com base em token stream

### Compiler

* [ ] introduzir uma IR intermediaria explicita
* [ ] separar melhor built-ins (`If`, `For`, `Switch`) do resto do transform
* [ ] surface clara para extensao futura do compiler

## Fase 3: linguagem

Meta:

* fechar uma spec P0 da linguagem e depois evoluir com cuidado

### Sintaxe

* [ ] congelar a forma canonica de expressoes em attrs
* [ ] decidir oficialmente se `prop={{ expr }}` continua sendo a unica forma P0
* [ ] avaliar `:prop="expr"` apenas como sugar opcional P1
* [ ] formalizar modificadores de componente ou remover se continuarem sem semantica

### Blocos e built-ins

* [ ] revisar `signal` e `action` para semantica clara
* [ ] avaliar `Fill`/slots nomeados com sintaxe mais explicita
* [ ] revisar se `computed` deve continuar como bloco ou ganhar forma inline

### Imports e mounts

* [ ] relative imports reais como `./Sibling.jinja`
* [ ] estrategia de conflito entre mounts com nomes iguais
* [ ] `pjx check` com validacoes especificas para alias de mount

## Fase 4: runtime interativo nativo

Meta:

* ir alem de HTMX/Alpine quando a base ja estiver madura

### Signals/actions

* [ ] registry real de actions
* [ ] dependency graph de signals
* [ ] estrategia de update parcial por fragmento
* [ ] contrato claro entre runtime server e browser bridge

### Browser bridge

* [ ] decidir se existe bridge propria alem de `pjx-browser.js`
* [ ] eventos do tipo `jx-on:*` com semantica oficial
* [ ] progressive enhancement consistente

## Fase 5: renderer backend

Meta:

* desacoplar linguagem do backend de render

### Interface

* [ ] `RendererBackend`/`Protocol`
* [ ] adapter Jinja2
* [ ] adapter experimental MiniJinja

### Performance

* [ ] benchmark oficial do framework
* [ ] profile de cold render vs hot render
* [ ] precompile opcional no startup
* [ ] investigar cache persistente/bytecode cache

## Fase 6: CLI e tooling

Meta:

* transformar o CLI em parte central da experiencia

### Check

* [ ] mais regras semanticas
* [ ] tabela Rich opcional para resumo
* [ ] pagina de documentacao dos codigos `[NNN]`
* [ ] modo machine-readable mais forte

### Format

* [ ] formatter baseado em tokens
* [ ] preservar melhor comments e spacing intencional
* [ ] `--diff`

### Novos comandos

* [ ] `pjx inspect`
* [ ] `pjx list-components`
* [ ] `pjx doctor`
* [ ] `pjx bench`
* [ ] `pjx new`

## Fase 7: framework experience

Meta:

* reduzir ainda mais o boilerplate do projeto host

* [ ] helper de projeto novo
* [ ] scaffold de `templates/components/layouts/pages`
* [ ] presets de browser integrations
* [ ] suporte melhor a apps montados em prefixo, tipo `/ui`
* [ ] storybook-like local preview ou gallery interna

## Fase 8: primitives e demo app

Meta:

* usar o demo como prova real do framework

* [ ] Tabs
* [ ] Dialog/Sheet
* [ ] Combobox
* [ ] Table mais rica com sorting/filtering server-first
* [ ] primitives de navigation
* [ ] exemplos de auth, dashboard e admin com mounts prefixados

## Fase 9: docs

Meta:

* fazer a documentacao acompanhar o framework

* [ ] documentar todos os codigos do `check`
* [ ] cookbook com exemplos pequenos
* [ ] docs de extensao de directives
* [ ] docs de assets e Tailwind
* [ ] docs de performance e troubleshooting

## Regras de Prioridade

Sempre priorizar nesta ordem:

1. clareza de linguagem
2. previsibilidade do runtime
3. tooling e validacao
4. performance
5. runtime reativo proprio

Se alguma feature nova piorar muito os itens 1-3, ela deve esperar.
