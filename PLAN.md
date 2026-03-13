# JinjaX — Spec Oficial v1

## 1. Visão do projeto

JinjaX é uma linguagem de templates com sintaxe inspirada em frameworks modernos de componentes, compilada para Jinja2.

A proposta da v1 é simples:

* **Jinja2 continua sendo o motor de renderização**
* **a linguagem pública deixa de ser Jinja puro** e passa a ser uma camada compilada orientada a componentes
* **FastAPI é a integração oficial inicial**
* **HTMX é first-class para interatividade server-driven**
* **Pydantic é first-class para props e validação de forms**
* o projeto suporta **compile-on-load** e **build step**, com equivalência garantida pelo mesmo compilador interno

A v1 não tenta resolver reatividade completa, DOM diff, runtime client-side próprio, hydration complexa ou LiveView-like runtime.

O foco da v1 é:

* componentes
* props tipadas
* variants
* vars
* slots
* layouts
* loops e condicionais
* SSR limpo
* integração moderna com FastAPI + HTMX + Pydantic

---

## 2. Objetivo da v1

A v1 existe para entregar uma linguagem pequena, robusta, previsível e compilável.

Ela deve permitir que um autor de template construa interfaces server-rendered modernas sem precisar escrever Jinja manualmente para os casos principais de componentização.

### O que a v1 deve entregar

* definir componentes reutilizáveis
* validar props com tipagem clara
* criar design systems com variants
* compor layouts e slots
* renderizar páginas e fragmentos HTMX
* validar formulários com Pydantic
* inspecionar o output compilado em produção
* ter um compilador confiável com erros legíveis

### O que a v1 não deve tentar resolver

* runtime reativo próprio
* signals com semântica completa
* DOM diff server-side
* hydration parcial
* JSX/import hook
* client router
* framework fullstack reativo
* sistema avançado de estado compartilhado

---

## 3. Princípios de design

### 3.1. Jinja continua sendo backend, não a API principal

O usuário final escreve JinjaX, não Jinja bruto, para os casos comuns.

### 3.2. A linguagem deve ser pequena

Tudo que entrar na v1 deve ter semântica clara, ser fácil de compilar e fácil de explicar.

### 3.3. Parser real, não regex

O compilador deve usar tokenizer, parser e AST próprios.

### 3.4. Output inspecionável

Todo template compilado deve poder ser lido, auditado e debugado.

### 3.5. Dev e prod com o mesmo compilador

Compile-on-load e build step devem compartilhar a mesma lógica de compilação.

### 3.6. Escape hatch explícito

Sempre deve existir uma forma oficial de bypass para Jinja puro.

### 3.7. Interatividade server-driven primeiro

A solução oficial de interação da v1 é HTMX.

### 3.8. Tipagem real para entradas

Props e forms devem ter contrato claro, preferencialmente via Pydantic.

### 3.9. Core agnóstico de design system

Basecoat pode ser primeira referência de exemplos, mas o core não deve depender dele.

---

## 4. Escopo oficial

## 4.1. Incluído na v1

* linguagem fonte compilada para Jinja2
* componentes
* props tipadas
* defaults e required
* variants
* vars tipadas
* slot default
* named slots simples
* layouts via componentes
* For
* Show
* lambdas simples no estilo arrow function
* imports explícitos de módulos e scripts Python
* chamadas de funções Python com contrato declarado
* helpers básicos de transformação de string
* integração FastAPI
* HTMX first-class
* validação de forms com Pydantic
* compile-on-load
* build step
* manifest de build
* diretório raw para Jinja puro
* mensagens de erro com arquivo, linha e coluna

## 4.2. Fora da v1

* Signal
* runtime reativo próprio
* DOM diff server-side
* SSE como peça central
* LiveView-like runtime
* hydration automática
* roteamento client-side
* stores globais
* async component execution model complexo
* context API
* suspense
* switch/match
* scoped slots
* slot props
* import system complexo com resolução dinâmica ampla
* plugins públicos instáveis

---

## 5. Extensão de arquivo e convenções

### Decisão oficial

A linguagem fonte **não deve usar `.jinja` como extensão principal**.

Motivo:

* `.jinja` sugere Jinja puro
* JinjaX é uma linguagem compilada, não Jinja bruto
* separar extensão reduz ambiguidade mental e técnica

### Recomendação oficial

Usar uma extensão própria para arquivos fonte, com uma destas opções:

* `.jx`
* `.jinjax`
* `.sjx`

### Recomendação preferida

**`.jx`** para arquivos fonte compilados.

### Uso sugerido

* `templates/components/*.jx`
* `templates/layouts/*.jx`
* `templates/pages/*.jx`
* `templates/raw/*.jinja`
* `build/jinja/**/*.jinja`

### Convenções obrigatórias

* diretórios `components`, `layouts` e `pages` passam pelo compilador
* diretório `raw` nunca passa pelo compilador
* componentes usam **PascalCase**
* nome do arquivo deve bater com o nome do componente, quando houver um componente principal no arquivo
* nomes de componentes públicos devem ser únicos na v1
* internamente o registry deve ser preparado para namespace futuro

---

## 6. Estrutura oficial do projeto

```text
src/jinjax/
├─ compiler/
│  ├─ tokenizer.py
│  ├─ parser.py
│  ├─ ast.py
│  ├─ compiler.py
│  ├─ errors.py
│  └─ source_map.py
│
├─ runtime/
│  ├─ loader.py
│  ├─ registry.py
│  ├─ cache.py
│  ├─ manifest.py
│  ├─ render.py
│  ├─ validation.py
│  └─ errors.py
│
├─ integrations/
│  └─ fastapi.py
│
├─ forms/
│  └─ helpers.py
│
├─ cli/
│  ├─ build.py
│  ├─ check.py
│  └─ dev.py
│
└─ __init__.py

templates/
├─ components/
├─ layouts/
├─ pages/
└─ raw/

build/
└─ jinja/
```

---

## 7. Arquitetura geral

```text
JinjaX source (.jx)
        ↓
Tokenizer
        ↓
Parser
        ↓
AST
        ↓
Compiler
        ↓
Jinja output (.jinja)
        ↓
Jinja2 Environment
        ↓
HTML
```

### Camadas

#### Linguagem

Define sintaxe, regras, semântica e erros de autoria.

#### Compilador

Converte AST para Jinja compilado.

#### Runtime

Resolve componentes, valida props, carrega templates e integra com Jinja2.

#### Integração web

FastAPI + HTMX + forms + fragment rendering.

---

## 8. API pública proposta

```python
Compiler.compile(source: str, *, path: str) -> CompiledTemplate
build_templates(src_dir: str, out_dir: str) -> BuildManifest
CompilerLoader(source_dirs: list[str], *, compiled_dir: str | None = None, mode: Literal["load", "compiled", "auto"] = "auto")
JinjaXEnvironment(...)
JinjaXTemplates(...)
render_template(name: str, context: dict[str, Any]) -> str
validate_form(request, Model) -> FormValidationResult[Model]
resolve_component_props(component_name: str, props: dict[str, Any]) -> dict[str, Any]
```

### Observações

* `Compiler.compile` é API central do compilador
* `build_templates` gera Jinja compilado e manifest
* `CompilerLoader` controla os modos de carregamento
* `JinjaXEnvironment` encapsula loader, registry, cache e helpers
* `JinjaXTemplates` fornece integração FastAPI estilo `Jinja2Templates`
* `resolve_component_props` deve validar e normalizar props antes do render

---

## 9. Linguagem oficial da v1

## 9.1. Regras gerais

* tags minúsculas são HTML
* tags em PascalCase são componentes
* `{expr}` em texto vira `{{ expr }}`
* `attr={expr}` vira atributo dinâmico
* `attr="literal"` continua literal
* attrs como `hx-*`, `x-*`, `@click`, `:class` passam intactos
* `children` é nome reservado para slot default
* nomes reservados da linguagem na v1:

  * `Component`
  * `For`
  * `Show`
  * `Slot`

---

## 9.2. Expressões

A v1 deve tratar expressões como **expressões simples compatíveis com Jinja/Python-like**, sem tentar implementar um parser Python completo.

### Permitido

* acesso por atributo: `{user.name}`
* indexação: `{items[0]}`
* chamadas simples já válidas no contexto do Jinja, quando permitido pelo compilador
* transformações simples de string: `{name.upper()}`, `{slug.lower()}`, `{tags.split(",")}`
* lambdas pequenas, restritas e compiláveis para usos declarativos
* operadores simples: `{foo or "bar"}`
* acesso a dicts de variants/vars

### Extensões planejadas

* lambdas devem funcionar como um primeiro passo para uma semântica parecida com arrow function de TSX
* o suporte inicial pode ser menor que o de Python e TSX, desde que seja explícito e previsível
* chamadas encadeadas em strings devem ser limitadas a um conjunto seguro e documentado de operações
* funções importadas devem poder retornar contrato tipado ou dado bruto validável

### Não objetivo da v1

* implementar gramática Python completa
* adicionar mini-linguagem própria de expressões
* avaliar expressões no compilador

O compilador deve preservar a expressão como conteúdo opaco quando possível e só transformá-la para o alvo Jinja.

---

## 9.3. Definição de componente

### Sintaxe oficial

```html
<Component Button>

props:
  label: str
  variant: str = "primary"
  size: str = "md"

variants:
  variant:
    primary: "btn-primary"
    secondary: "btn-secondary"
  size:
    sm: "btn-sm"
    md: "btn-md"
    lg: "btn-lg"

vars:
  base = "btn"

<button class="{base} {variants.variant[variant]} {variants.size[size]}">
  {label}
</button>

</Component>
```

### Semântica oficial

* `<Component Button>` define um componente compilável
* `props:` define o contrato de entrada
* `variants:` define mapeamentos declarativos para classes e variações
* `vars:` define variáveis internas locais ao componente
* o corpo HTML define o template renderizado

### Compilação conceitual

* componente vira macro/função Jinja equivalente
* props viram modelo Pydantic + interface de chamada da macro
* variants viram estruturas de dados internas do template compilado
* vars viram `set` ou equivalente no output Jinja

---

## 9.4. Props

### Regras

* props são a interface pública do componente
* suportam required e default
* suportam tipos Pydantic
* devem aceitar tipos primitivos comuns como `str`, `int`, `float`, `bool`, `dict`, `list`
* devem ser validadas antes do render
* devem gerar erro claro quando inválidas

### Fonte da verdade

**O modelo/schema Pydantic gerado é a verdade do contrato de props.**

A assinatura da macro Jinja é apenas um detalhe do output compilado, não o contrato principal do sistema.

### Boas práticas

* usar nomes claros e estáveis
* evitar props mágicas implícitas
* manter defaults previsíveis
* não misturar props de UI, estado e infra sem necessidade
* reservar nomes internos do runtime

### Reservados

* `children`
* nomes internos de slots gerados pelo compilador
* nomes internos de metadata do runtime

---

## 9.5. Variants

### Objetivo

Permitir design system declarativo sem acoplamento a um CSS framework específico.

### Formatos suportados

#### Mapeamento flat

```html
variants:
  primary: "btn-primary"
  secondary: "btn-secondary"
```

#### Mapeamento por eixo

```html
variants:
  variant:
    primary: "btn-primary"
    secondary: "btn-secondary"
  size:
    sm: "btn-sm"
    md: "btn-md"
```

### Regras

* variants são dados declarativos, não lógica arbitrária
* devem ser acessíveis no template como estrutura previsível
* erros de chave inválida devem ser claros
* o core não conhece Basecoat; só conhece mapeamentos

### Boas práticas

* usar eixos explícitos: `variant`, `size`, `tone`, `state`
* evitar variants enormes em um único componente
* extrair componentes ao invés de criar matrizes excessivas de variação

---

## 9.6. Vars

### Objetivo

Declarar valores internos locais ao template do componente.

### Regras

* `vars:` define variáveis internas somente daquele componente
* `vars:` podem declarar tipo explícito, por exemplo `title: str = "foo"`
* não substitui props
* não é storage reativo
* não é mecanismo de estado compartilhado

### Boas práticas

* usar para classes base, aliases internos e pequenas composições
* não concentrar lógica de negócio em `vars:`

### Tipagem inicial recomendada

* suportar na base `str`, `int`, `float`, `bool`, `dict`, `list`
* permitir evolução posterior para tipos compostos e validação mais rica
* manter a semântica de `vars:` próxima de `props:` sempre que isso reduzir ambiguidade

---

## 9.6.1. Imports e scripts Python

### Objetivo

Permitir que templates e componentes usem imports explícitos para acessar funções utilitárias e scripts Python com contrato estável.

### Casos alvo

* importar função que consulta API externa e retorna dados para render
* importar função de limpeza ou transformação de dados
* importar script Python reaproveitável como fonte de dado validável

### Regras iniciais

* imports devem ser explícitos e locais ao arquivo
* o runtime deve diferenciar valor bruto de retorno com contrato declarado
* a chamada deve se comportar como função pura do ponto de vista do template
* efeitos colaterais devem ser desencorajados e documentados como escape hatch
* o resultado deve poder ser validado antes de entrar no render final

### Não objetivo inicial

* transformar template em orquestrador arbitrário de scripts
* executar import dinâmico irrestrito
* abrir modelo de plugin público antes do core estabilizar

---

## 9.7. Uso de componente

### Self-closing

```html
<Button label="Save" variant="primary" />
```

### Com slot default

```html
<Card title="Hello">Body</Card>
```

### Semântica

* props são resolvidas e validadas antes do render do componente
* slot default alimenta `children`
* o autor do template não deve precisar escrever Jinja manual

---

## 9.8. Slots

### Decisão oficial

A v1 suporta:

* slot default
* named slots simples

### Fora da v1

* scoped slots
* slot props
* slot forwarding avançado
* composição profunda de slot semantics

### Sintaxe unificada recomendada

No uso:

```html
<Card title="Hello">
  <Slot name="header">Header</Slot>
  Body
</Card>
```

Na definição:

```html
<Slot name="header">Fallback</Slot>
```

### Motivo da unificação

Usar `Slot` tanto no uso quanto na definição torna a linguagem mais consistente do que misturar `template slot="..."` com `<Slot ...>`.

### Regras

* `children` é o slot default
* named slots aceitam fallback
* slot desconhecido deve gerar erro legível
* named slots da v1 devem ser simples e explícitos

---

## 9.9. For

### Sintaxe

```html
<For each={users}>...</For>
```

### Alias padrão

* alias implícito: `it`

### Alias explícito

```html
<For each={users} as="user">...</For>
```

### Regras

* `For` compila para loop Jinja equivalente
* o escopo do alias deve ser claro e local
* não incluir recursos avançados de collection transform na v1

---

## 9.10. Show

### Sintaxe

```html
<Show when={logged_in}>...</Show>
```

### Regras

* `Show` compila para `if` Jinja equivalente
* não incluir `else-if` sintático, `Switch`, `Match` ou formas avançadas na v1

---

## 9.11. Layouts

### Decisão oficial

Layouts são **componentes normais** no diretório `layouts/`.

Não existe, na v1, um sistema paralelo de herança além do modelo de composição por componentes.

### Motivo

* reduz complexidade
* mantém um único modelo mental
* evita coexistência confusa entre herança Jinja e composição de componentes

---

## 10. Registry e resolução de componentes

### Regra da v1

Componentes públicos têm nome único global no projeto.

### Regra interna recomendada

O runtime deve ser implementado já prevendo namespace por caminho para futura evolução.

### Estratégia

* scan dos diretórios compiláveis no boot ou build
* criação de registry central
* manifest contendo nome público, arquivo fonte, saída compilada e metadata
* falha imediata em caso de componente duplicado

### Futuro

Permitir nomes qualificados por namespace, mantendo compatibilidade com nomes globais simples quando possível.

---

## 11. Compilação

## 11.1. Compile-on-load

### Objetivo

Desenvolvimento local com feedback rápido.

### Regras

* compila em memória ao carregar template fonte
* usa cache por hash e/ou mtime
* deve invalidar corretamente quando arquivo mudar
* deve produzir o mesmo resultado lógico do build step

### Deve existir

* mensagens de erro amigáveis
* modo debug opcional mostrando output compilado
* rastreamento para arquivo fonte original

---

## 11.2. Build step

### Objetivo

Produção, inspeção e previsibilidade operacional.

### Regras

* compila fontes para `build/jinja/`
* gera `manifest.json`
* output gerado não é editado manualmente
* deve permitir auditoria do Jinja final

### Manifest deve incluir

* nome do componente/template
* path fonte
* path compilado
* hash
* schema de props
* metadata de slots
* metadata de variants

---

## 11.3. Equivalência

Compile-on-load e build step devem usar exatamente o mesmo compilador e produzir o mesmo output lógico.

Essa equivalência é requisito de arquitetura, não detalhe opcional.

---

## 12. Runtime e validação

## 12.1. Fonte da verdade de props

Props devem ser resolvidas e validadas antes da chamada efetiva do template compilado.

### Fluxo sugerido

```text
props recebidas
    ↓
resolver defaults
    ↓
validar com Pydantic
    ↓
normalizar dados
    ↓
chamar template compilado
```

## 12.2. Exceções específicas

O runtime deve expor exceções específicas e estáveis, por exemplo:

* `TemplateCompileError`
* `ComponentResolutionError`
* `PropsValidationError`
* `SlotValidationError`
* `TemplateRuntimeError`

### Boas práticas

* nunca expor stacktrace cru como UX padrão
* mensagens devem ser orientadas ao autor do template
* erros devem apontar arquivo, linha, coluna e contexto quando possível

---

## 13. Integração FastAPI

### Decisão oficial

FastAPI é a única integração oficial da v1.

### Deve existir

* criação de environment com `CompilerLoader`
* `TemplateResponse` para páginas
* render de fragmentos para HTMX
* helpers de forms
* integração previsível com request/context

### Não incluir na v1

* integração oficial com Flask
* integração oficial com Django
* múltiplos adaptadores web no core inicial

### Boas práticas

* manter integração pequena e idiomática
* evitar API mágica demais
* espelhar o conforto de `Jinja2Templates` sem copiar limitações desnecessárias

---

## 14. HTMX

### Decisão oficial

HTMX é o modelo oficial de interatividade server-driven da v1.

### Regras

* o compilador não cria DSL própria de eventos na v1
* attrs HTMX passam intactos
* templates podem renderizar páginas e fragmentos
* exemplos oficiais devem cobrir fluxo parcial e atualização incremental por HTML

### Exemplos oficiais devem incluir

* render inicial de página
* fragmento recarregado via HTMX
* submit de form
* replace/update de trecho
* componente reutilizado em página e fragmento

### Alpine

Alpine é escape hatch opcional para UI local, não parte central da proposta.

---

## 15. Pydantic

### Decisão oficial

Pydantic é first-class para props e forms.

### Props

* `props:` geram schema/modelo
* required e defaults vêm da definição
* tipos devem seguir semântica previsível
* mensagens de erro devem ser claras

### Forms

* `validate_form(request, Model)` deve existir
* deve suportar tipos comuns de Pydantic como `EmailStr`
* deve retornar estrutura clara com dados válidos e erros

### Boas práticas

* separar model de form de model de persistência quando necessário
* não misturar validação de transporte com regra de negócio pesada

---

## 16. Basecoat e design system

### Decisão oficial

O core não depende de Basecoat.

### O que entra na v1

* sistema de `variants` agnóstico
* starter kit e exemplos podem usar Basecoat
* componentes de referência podem mapear bem para Basecoat

### O que é desejável

* starter kit com Button, Card, Input, Alert, Badge, Layout
* convenções de variants alinhadas a design systems reais
* documentação mostrando composição de classes Basecoat com `variants` + `vars`

---

## 17. DX e ferramentas

### CLI mínima recomendada

* `jinjax build`
* `jinjax check`
* `jinjax dev`

### `build`

* compila templates
* gera manifest
* opcionalmente falha com warnings severos

### `check`

* valida sintaxe
* valida registry
* detecta componentes duplicados
* detecta erros de slots/props conhecidos

### `dev`

* inicia modo de desenvolvimento com compile-on-load
* pode expor debug de template compilado

### Futuro desejável

* integração com ruff-like developer flow
* comando de inspeção do AST
* comando para imprimir Jinja compilado de um arquivo específico

---

## 18. Boas práticas de implementação

### 18.1. Linguagem

* manter a gramática pequena
* evitar múltiplas formas de escrever a mesma coisa
* documentar claramente o que é sintaxe da linguagem e o que é pass-through

### 18.2. Compilador

* não misturar parsing com codegen
* manter AST explícita e tipada
* preservar source mapping
* garantir idempotência lógica do build

### 18.3. Runtime

* registry central único
* cache previsível
* validação antes do render
* erros específicos por categoria

### 18.4. Integração web

* preferir composição simples a abstrações mágicas
* tratar HTMX como HTML normal, não como subframework
* manter o request/context explícito

### 18.5. Componentes

* props pequenas e claras
* variants organizadas por eixo
* slots usados com moderação
* extrair componentes antes de criar monstros genéricos demais

### 18.6. Layouts

* usar layouts como componentes normais
* evitar herança paralela de template
* privilegiar composição

### 18.7. Forms

* usar Pydantic para contrato de entrada
* retornar erros estruturados
* manter o template livre de lógica de validação complexa

---

## 19. Anti-patterns a evitar

* usar regex como parser principal
* usar `.jinja` para linguagem compilada e gerar confusão com Jinja puro
* colocar lógica de negócio pesada dentro de `vars:`
* permitir sintaxe demais logo na v1
* adicionar runtime reativo cedo demais
* criar sistema paralelo de herança além de componentes
* acoplar core ao Basecoat
* esconder erros reais atrás de mensagens vagas
* validar props só depois de render parcialmente começar
* criar muitos nomes mágicos e implícitos

---

## 20. Roadmap de implementação

## Fase 1 — núcleo compilável

* tokenizer
* parser
* AST
* interpolação `{expr}`
* HTML normal
* reconhecimento de tags PascalCase
* `Component`
* uso self-closing
* slot default
* `vars:` com tipagem básica
* helpers de string como `split()`, `upper()` e `lower()`
* loader básico

## Fase 2 — contratos e controle de fluxo

* `props:`
* schema/modelo Pydantic gerado
* validação de props
* tipos básicos para `props` e `vars` como `str`, `int`, `float`, `dict` e correlatos
* `For`
* `Show`
* erros estruturados

## Fase 3 — composição e build

* `variants:`
* layouts
* imports explícitos de funções e scripts Python
* contratos de retorno para funções chamadas do template
* lambdas simples em semântica próxima de arrow functions
* build step
* manifest
* raw bypass
* registry completo

## Fase 4 — integração de aplicação

* FastAPI integration final
* HTMX examples oficiais
* forms com `validate_form`
* named slots simples
* CLI `check` e `dev`

---

## 21. Testes obrigatórios

### Golden tests do compilador

* `Component`
* `props`
* `variants`
* `vars`
* `vars` tipadas
* `For`
* `Show`
* slot default
* named slots
* layouts
* helpers de string
* lambdas simples
* imports explícitos

### Testes de equivalência

* compile-on-load e build step devem gerar o mesmo output lógico

### Testes de props

* required
* default
* validação com tipos Pydantic
* tipos primitivos como `str`, `int`, `float`, `dict`
* erro claro de prop inválida

### Testes de runtime/import

* import de função Python local
* execução de script utilitário com retorno validado
* falha clara quando contrato retornado não bate

### Testes de forms

* validação com `EmailStr`
* retorno de valores e erros

### Testes FastAPI

* render de página
* render de fragmento HTMX
* template com componente + props + slot

### Testes de compatibilidade

* templates em `raw/` não passam pelo compilador
* attrs HTMX passam intactos
* attrs Alpine passam intactos

### Testes de erro

* sintaxe inválida
* componente não resolvido
* slot nomeado desconhecido
* componente duplicado no manifest

---

## 22. Critérios de aceitação da v1

Um projeto FastAPI deve conseguir:

* definir componentes em arquivos fonte JinjaX
* usar props tipadas
* usar variants e vars
* compor layouts e slots
* renderizar páginas e fragmentos HTMX
* validar forms com Pydantic
* usar modo loader e modo build com equivalência
* manter templates raw em Jinja puro quando necessário

O autor do template não deve precisar escrever Jinja manualmente para os casos principais de componentização.

---

## 23. MVP vs pós-MVP

## 23.1. MVP realista

O MVP deve incluir apenas:

* extensão própria de arquivo fonte
* parser + AST
* Component
* props simples
* vars
* variants
* slot default
* For
* Show
* build + compile-on-load
* FastAPI integration básica
* HTMX pass-through
* forms simples com Pydantic
* raw bypass

## 23.2. Pós-MVP imediato

* named slots simples
* melhor inspeção de output compilado
* CLI mais rica
* manifest mais completo
* melhor debug com source mapping
* starter kit Basecoat
* namespaces internos preparados para futura exposição pública

---

## 24. Pós-v1 / Futuro desejável

Aqui entram ideias boas que foram retiradas corretamente da v1, mas que fazem sentido como evolução futura.

## 24.1. Reatividade server-driven avançada

* `Signal` ou primitive semelhante
* fragment invalidation
* rerender parcial orientado por componente
* DOM diff server-side
* engine LiveView-like opcional
* transporte por SSE/WebSocket

## 24.2. Estado e contexto

* context API
* stores por request
* estado local de componente com semântica server-first
* sincronização controlada entre UI e servidor

## 24.3. Slots avançados

* scoped slots
* slot props
* slot forwarding
* composição avançada de layouts e containers

## 24.4. Linguagem e ergonomia

* imports explícitos opcionais
* namespaces públicos de componentes
* sugar syntax adicional bem justificada
* switch/match
* `else` sintático para `Show`
* diretivas auxiliares pequenas e previsíveis

## 24.5. Tooling

* LSP/editor support
* syntax highlighting oficial
* formatter
* inspector de AST
* sourcemaps mais ricos
* template playground
* snapshot debugger

## 24.6. Integrações futuras

* Flask adapter
* Django adapter
* Starlette low-level adapter
* integração com sistemas de asset pipeline

## 24.7. Client-side opcional

* hydration parcial opcional
* runtime mínimo para progressive enhancement
* pequenos islands interativos
* integração opcional com Alpine/Stimulus/mini runtime próprio

## 24.8. Recursos inspirados em outros projetos e frameworks

Recursos que existem hoje em ecossistemas modernos e podem inspirar o futuro:

* pattern de islands architecture
* server components
* partial prerendering
* template static analysis
* compile-time optimization
* class variance helpers inspirados em CVA
* component manifests ricos para tooling
* fine-grained invalidation inspirada em frameworks reativos
* fragment rendering estratégico parecido com HTMX/Hotwire/Phoenix LiveView
* forms tipados com contratos compilados

---

## 25. Decisões finais fechadas

### Fechado para a v1

* Jinja2 é o motor de render
* JinjaX é a linguagem pública
* FastAPI é a única integração oficial
* HTMX é first-class
* Pydantic é first-class
* compile-on-load e build step coexistem
* parser real com AST
* layouts são componentes
* Basecoat fica fora do core
* runtime reativo fica fora da v1
* extensão fonte deve ser própria, não `.jinja`

### Mantido em aberto para o futuro

* nome final da extensão própria
* namespaces públicos de componentes
* recursos reativos avançados
* client runtime opcional
* integrações além de FastAPI

---

## 26. Recomendação final de posicionamento

A melhor forma de posicionar JinjaX é:

**uma linguagem moderna de componentes server-rendered para Python, compilada para Jinja2, com FastAPI + HTMX + Pydantic como stack oficial da v1.**

Isso diferencia o projeto de:

* engines de template clássicas puras
* clones de JSX incompletos
* frameworks reativos ambiciosos demais

E coloca JinjaX num espaço realista e útil:

* moderno na autoria
* previsível na compilação
* forte no SSR
* prático para app real
* pequeno o suficiente para ser implementado com qualidade

---

## 27. Resumo executivo

Se a v1 seguir esta spec, JinjaX terá:

* uma linguagem pequena e clara
* uma arquitetura sustentável
* bom equilíbrio entre performance e DX
* utilidade real em FastAPI
* ótima sinergia com HTMX
* tipagem e validação via Pydantic
* espaço saudável para evoluir depois sem comprometer a base

O principal acerto estratégico é este:

**não tentar vencer React, Solid, LiveView e Jinja ao mesmo tempo.**

A v1 deve vencer um problema menor e muito valioso:

**fazer componentização moderna sobre Jinja2 de forma confiável, tipada e agradável de usar.**
