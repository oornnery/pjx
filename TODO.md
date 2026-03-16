# TODO

Este arquivo registra o que falta para o PJX sair de prototipo funcional para
miniframework maduro.

## Norte do Projeto

Objetivo:

* linguagem propria para componentes server-first com sintaxe `@directive`
* FastAPI como base real do app host
* compile pipeline clara: `.pjx` -> parser/AST -> compiler -> Jinja2
* HTMX e Alpine como enhancement
* DX simples, com pouco boilerplate

## Fase 0: consolidar o que ja existe (feito)

* [x] `Pjx` integrado via `init_app(app)`
* [x] `PjxRouter`
* [x] `templates/` como raiz
* [x] mounts com prefixo `@prefix/...`
* [x] parser estrutural com sintaxe `@directive`
* [x] `pjx check` e `pjx format`
* [x] docs iniciais de arquitetura e uso
* [x] `render()` como Depends, `Page`/`Template` como return types
* [x] `@pjx.context_processor`
* [x] extensao `.pjx` canonica
* [x] `PropValidationError` com exceptions customizadas
* [x] boundary check em `extract_fragment_by_id`
* [x] multi-component `_extract_meta`
* [x] `:prop` binding em component calls
* [x] `jx-text`/`jx-html` directives
* [x] app de exemplo limpo com props canonicos

## Fase 1: endurecer o core

Meta:

* melhorar contratos internos e reduzir fragilidade do runtime

### Catalog

* [ ] `add_package(...)`
* [ ] `collect_assets(output_dir)`
* [ ] filtros, tests e globals mais explicitos
* [ ] introspecao de mounts e aliases mais rica

### Runtime

* [ ] melhorar extracao de partials para algo menos fragil que busca por `id`
* [ ] cache mais observavel e com estatisticas
* [ ] separar melhor render de assets e render de markup
* [ ] interface explicita de renderer backend

### Attrs e directives

* [ ] enriquecer `AttrBag` com `set`, `setdefault`, `add_class`, `remove_class`
* [ ] mapear melhor o contrato das diretivas customizadas
* [ ] scoped slot `let:` bindings (parser ja captura, falta emit no compiler)

## Fase 2: parser e compiler mais fortes

Meta:

* sair do modo "estrutura forte, markup medio" para uma base bem mais confiavel

### Parser

* [ ] introduzir lexer/token stream
* [ ] spans e mensagens de erro melhores
* [ ] formatter baseado em token stream

### Compiler

* [ ] introduzir uma IR intermediaria explicita
* [ ] separar melhor built-ins (`Show`, `For`, `Switch`) do resto do transform
* [ ] surface clara para extensao futura do compiler

## Fase 3: linguagem

Meta:

* fechar uma spec P0 da linguagem e depois evoluir com cuidado

### Sintaxe

* [ ] congelar a forma canonica de expressoes em attrs
* [ ] avaliar `:prop="expr"` como sugar oficial
* [ ] formalizar modificadores de componente ou remover

### Blocos e built-ins

* [ ] revisar `signal` e `action` para semantica clara
* [ ] revisar se `computed` deve continuar como bloco ou ganhar forma inline

### Imports e mounts

* [ ] relative imports reais como `./Sibling.pjx`
* [ ] estrategia de conflito entre mounts com nomes iguais

## Fase 4: runtime interativo nativo

Meta:

* ir alem de HTMX/Alpine quando a base ja estiver madura

### Signals/actions

* [ ] registry real de actions
* [ ] dependency graph de signals
* [ ] estrategia de update parcial por fragmento

### Browser bridge

* [ ] decidir se existe bridge propria
* [ ] eventos `jx-on:*` com semantica oficial
* [ ] progressive enhancement consistente

## Fase 5: renderer backend

Meta:

* desacoplar linguagem do backend de render

### Interface

* [ ] `RendererBackend` protocol
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
* [ ] tabela Rich para resumo
* [ ] pagina de documentacao dos codigos `[NNN]`

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

Checklist:

* [ ] helper de projeto novo
* [ ] scaffold de `templates/components/layouts/pages`
* [ ] presets de browser integrations
* [ ] storybook-like local preview

## Fase 8: primitives e demo app

Meta:

* usar o demo como prova real do framework

Checklist:

* [x] Tabs, Dialog, Combobox, Table, Pagination, Tooltip, Popover
* [x] Accordion, Breadcrumb, Dropdown, Avatar, Skeleton, Toggle, Slider
* [ ] primitives de navigation mais ricos
* [ ] exemplos de auth, dashboard e admin com mounts prefixados

## Regras de Prioridade

Sempre priorizar nesta ordem:

1. clareza de linguagem
2. previsibilidade do runtime
3. tooling e validacao
4. performance
5. runtime reativo proprio

Se alguma feature nova piorar muito os itens 1-3, ela deve esperar.
