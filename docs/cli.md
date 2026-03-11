# CLI

## Objetivo

O CLI do PJX existe para duas tarefas:

* validar templates e rotas HTML
* formatar templates no estilo canonico do projeto

Implementacao atual:

* interface: [pjx/cli.py](/home/oornnery/proj/pjx/pjx/cli.py)
* nucleo: [pjx/tooling.py](/home/oornnery/proj/pjx/pjx/tooling.py)

## Stack

```text
Typer
|
`-- parsing de comandos e exit codes

Rich
|
`-- output de terminal

tooling.py
|
+-- load_project
+-- check_project
`-- format_project
```

## Comandos

### check

```bash
uv run pjx check exemples.main:pjx
uv run pjx check exemples.main:pjx --format json
uv run pjx check . --strict
```

Aceita:

* import target, como `exemples.main:pjx`
* pasta de projeto
* arquivo `.jinja`

### format

```bash
uv run pjx format exemples.main:pjx --check
uv run pjx format exemples.main:pjx
uv run pjx format path/to/Button.jinja
```

## Exit Codes

```text
0 -> sucesso
1 -> encontrou erro; ou warnings com --strict; ou arquivos mudariam com format --check
2 -> erro de uso da CLI
```

## Validacoes do check

Hoje o `pjx check` cobre:

* parse estrutural
* compile step
* alias de import ausente
* alias de import duplicado
* imports inexistentes
* self-import
* assets locais ausentes
* nome de componente divergente do arquivo
* nome de componente fora de TitleCase
* nome de componente duplicado
* template sombreado entre mounts
* ciclo de import
* template inexistente em route `page` ou `action`

## Codigos Numericos

A saida textual usa codigos numericos estaveis:

```text
[101] parse_error
[102] compile_error
[105] missing_import
```

Exemplo:

```text
Template issues:
  components/ui/Broken.jinja
    ERROR [105] missing_import [components/ui/Missing.jinja]: imported component "components/ui/Missing.jinja" does not exist
```

Objetivo:

* facilitar leitura rapida
* facilitar busca
* manter automacao simples

## JSON Output

```bash
uv run pjx check exemples.main:pjx --format json
```

O JSON inclui:

* root
* template_roots
* files_checked
* routes_checked
* errors
* warnings
* validation_map
* templates
* routes

Cada issue traz:

* `number`
* `severity`
* `code`
* `message`
* `path`
* `related_path`

## Formatter

O formatter atual e estrutural, nao um pretty-printer completo de HTML.

Ele:

* reorganiza preambulo
* estabiliza blocos de props
* normaliza quebras de linha do componente

Ele nao:

* reescreve agressivamente o body HTML
* corrige semantica invalida
* decide layout visual por voce

## Limites Atuais

* o `check` valida bastante coisa, mas ainda nao cobre todos os contratos semanticos possiveis do runtime
* o formatter ainda nao trabalha com spans/token stream
* a saida do `check` hoje e simples por design; ainda da para enriquecer com tabelas e agrupamentos do Rich
