from __future__ import annotations

from typing import Any, TypedDict, cast


class CounterState(TypedDict):
    count: int


class StudioState(TypedDict):
    count: int
    prompt: str


class FormValues(TypedDict):
    name: str
    email: str
    message: str


counter_state: CounterState = {
    "count": 3,
}

studio_state: StudioState = {
    "count": 6,
    "prompt": "Lancar uma homepage premium para analytics server-first.",
}

form_demo_state: FormValues = {
    "name": "",
    "email": "",
    "message": "",
}

last_form_submission: FormValues | None = None


def get_dashboard_context() -> dict[str, object]:
    return {
        "user": {
            "name": "Ana",
            "role": "Staff Engineer",
            "status": "ready",
        },
        "stats": [
            {"label": "MRR", "value": "R$ 128k"},
            {"label": "Trials", "value": "42"},
            {"label": "Churn", "value": "1.8%"},
        ],
        "notifications": [
            {
                "title": "Deploy finalizado",
                "message": "A versao 0.2 foi publicada em producao.",
                "visible": True,
            },
            {
                "title": "Janela de manutencao",
                "message": "Backup agendado para 02:00 UTC.",
                "visible": False,
            },
        ],
    }


def get_status_context() -> dict[str, object]:
    return {
        "status": "building",
        "jobs": [
            {
                "name": "frontend-build",
                "status": "ready",
                "badge_html": "<strong class='ok'>ok</strong>",
            },
            {
                "name": "worker-tests",
                "status": "building",
                "badge_html": "<strong class='warn'>running</strong>",
            },
        ],
    }


def get_counter_context() -> dict[str, int]:
    return {
        "initial_count": counter_state["count"],
    }


def increment_counter() -> dict[str, int]:
    counter_state["count"] += 1
    return {"count": counter_state["count"]}


def decrement_counter() -> dict[str, int]:
    counter_state["count"] -= 1
    return {"count": counter_state["count"]}


def list_notifications() -> list[dict[str, object]]:
    return cast(list[dict[str, object]], get_dashboard_context()["notifications"])


def get_studio_context() -> dict[str, object]:
    count = studio_state["count"]
    prompt = studio_state["prompt"]
    status = _studio_status(count)
    energy = _studio_energy(count)

    return {
        "initial_count": count,
        "prompt": prompt,
        "status": status,
        "energy_label": energy,
        "preview": {
            "title": _studio_title(prompt),
            "summary": _studio_summary(prompt, count),
            "eyebrow": "Server rendered concept",
            "lines": _studio_lines(prompt, count),
        },
        "highlights": _studio_highlights(prompt, count),
        "variants": _studio_variants(prompt, count),
    }


def increment_studio_count() -> dict[str, object]:
    studio_state["count"] = min(studio_state["count"] + 1, 12)
    return get_studio_context()


def decrement_studio_count() -> dict[str, object]:
    studio_state["count"] = max(studio_state["count"] - 1, 1)
    return get_studio_context()


def update_studio_prompt(prompt: str) -> dict[str, object]:
    cleaned = (prompt or "").strip()
    if cleaned:
        studio_state["prompt"] = cleaned
    return get_studio_context()


def _studio_status(count: int) -> str:
    if count >= 9:
        return "ready"
    if count >= 5:
        return "building"
    return "draft"


def _studio_energy(count: int) -> str:
    if count >= 9:
        return "Alta"
    if count >= 5:
        return "Media"
    return "Calma"


def _studio_title(prompt: str) -> str:
    prompt = prompt.strip().rstrip(".")
    if len(prompt) <= 56:
        return prompt
    return prompt[:53] + "..."


def _studio_summary(prompt: str, count: int) -> str:
    return (
        "O servidor respondeu com uma proposta de interface mais intensa, "
        f"organizada para um ritmo de iteracao nivel {count}."
        if count >= 8
        else "O servidor respondeu com uma proposta equilibrada, focada em clareza e hierarquia."
        if count >= 5
        else "O servidor respondeu com uma proposta limpa, mais editorial e com menos ruído visual."
    )


def _studio_lines(prompt: str, count: int) -> list[str]:
    return [
        f"Prompt atual: {prompt}",
        f"Escala de exploracao: {count}/12",
        "Render feito no servidor e entregue pronto para o navegador.",
    ]


def _studio_highlights(prompt: str, count: int) -> list[dict[str, str]]:
    base = [
        {"label": "Prompt", "value": prompt},
        {"label": "Contador", "value": f"{count}/12"},
        {"label": "Estado", "value": _studio_status(count)},
    ]
    if count >= 8:
        base.append({"label": "Tom", "value": "Denso e dramatico"})
    elif count >= 5:
        base.append({"label": "Tom", "value": "Equilibrado e ritmico"})
    else:
        base.append({"label": "Tom", "value": "Editorial e contido"})
    return base


def _studio_variants(prompt: str, count: int) -> list[dict[str, str]]:
    return [
        {
            "name": "Hero de impacto",
            "status": "ready" if count >= 8 else "building",
            "description": "Titulo grande, fundo atmosferico e CTA frontal.",
        },
        {
            "name": "Control panel",
            "status": "building" if count >= 5 else "draft",
            "description": "Input, botoes e sinais expostos como estado do servidor.",
        },
        {
            "name": "Server preview",
            "status": "ready",
            "description": f"Resumo gerado a partir do prompt: {prompt}",
        },
    ]


def get_showcase_context() -> dict[str, object]:
    return {
        "page_intro": "Uma stack de UI server-first para Python que nao te obriga a montar infraestrutura toda vez.",
        "capabilities": [
            {
                "title": "FastAPI native",
                "icon": "server",
                "detail": "Rotas HTML com decorators, sem APIRouter manual para cada caso.",
            },
            {
                "title": "Components + slots",
                "icon": "blocks",
                "detail": "Composicao declarativa, named slots e scoped slots no mesmo fluxo.",
            },
            {
                "title": "HTMX + Alpine",
                "icon": "workflow",
                "detail": "Interacoes incrementais no browser, com servidor ainda no centro da verdade.",
            },
        ],
        "features": [
            {
                "title": "Linguagem propria, backend separado",
                "icon": "layout",
                "summary": "O parser estrutural do PJX ja esta separado do backend de render, preparando o caminho para Jinja2 hoje e MiniJinja depois.",
            },
            {
                "title": "Integracoes embutidas",
                "icon": "sparkles",
                "summary": "Assets de HTMX e Alpine entram como parte do framework, nao como setup repetido do app final.",
            },
            {
                "title": "Catalogo introspectivo",
                "icon": "database",
                "summary": "Listagem de componentes, assinatura de props e assets por template ficam expostos para tooling e docs.",
            },
        ],
        "demos": [
            {
                "title": "Dashboard",
                "path": "/dashboard",
                "summary": "SSR puro com composicao de componentes, props tipadas, slots nomeados e diretivas server-side.",
                "status": "ready",
                "category": "Composicao",
                "icon": "layout",
                "tags": ["Card", "StatusBadge", "slots", "jx-show"],
                "featured": True,
            },
            {
                "title": "Patterns",
                "path": "/patterns",
                "summary": "Pagina pensada para mostrar provide/inject, attrs passthrough, scoped slots e pequenos enhancements locais.",
                "status": "ready",
                "category": "Ergonomia",
                "icon": "blocks",
                "tags": ["inject", "attrs", "tooltip", "Alpine"],
                "featured": True,
            },
            {
                "title": "Status Overview",
                "path": "/status",
                "summary": "Fluxo declarativo com Switch, Case, Default e renderizacao de HTML seguro vindo do servidor.",
                "status": "ready",
                "category": "Fluxo",
                "icon": "activity",
                "tags": ["Switch", "ForEach", "jx-html"],
                "featured": False,
            },
            {
                "title": "Data Views",
                "path": "/data",
                "summary": "Tabela, listas e estados operacionais usando primitives server-first reaproveitaveis.",
                "status": "ready",
                "category": "Dados",
                "icon": "table",
                "tags": ["Table", "List", "StatusBadge", "slots"],
                "featured": True,
            },
            {
                "title": "Forms",
                "path": "/forms",
                "summary": "Field, Input, Textarea e validacao server-side com resposta incremental no mesmo fluxo.",
                "status": "ready",
                "category": "Validacao",
                "icon": "mail",
                "tags": ["Field", "Input", "Textarea", "HTMX"],
                "featured": True,
            },
            {
                "title": "Signals Counter",
                "path": "/signals",
                "summary": "Partial render com HTMX para mostrar como sinais podem ter UX incremental sem reload completo.",
                "status": "building",
                "category": "Interacao",
                "icon": "workflow",
                "tags": ["HTMX", "partials", "signals"],
                "featured": False,
            },
            {
                "title": "Studio",
                "path": "/studio",
                "summary": "Playground completo com actions server-side, HTMX, Alpine e feedback visual em torno do mesmo estado.",
                "status": "ready",
                "category": "Showpiece",
                "icon": "bolt",
                "tags": ["forms", "partials", "Alpine", "server actions"],
                "featured": True,
            },
            {
                "title": "Catalog",
                "path": "/catalog",
                "summary": "Introspeccao do catalog mostrando templates, slots, props e assets do proprio projeto.",
                "status": "ready",
                "category": "Tooling",
                "icon": "database",
                "tags": ["catalog", "signatures", "assets"],
                "featured": False,
            },
        ],
    }


def get_data_views_context() -> dict[str, object]:
    return {
        "summary": [
            {
                "label": "Regions",
                "value": "6",
                "note": "A mesma estrutura pode renderizar listas, tabelas e badges sem boilerplate extra.",
                "icon": "table",
            },
            {
                "label": "Active jobs",
                "value": "42",
                "note": "Status vem do servidor e segue consistente nos componentes de leitura.",
                "icon": "activity",
            },
            {
                "label": "Queue latency",
                "value": "118ms",
                "note": "Cards e tabelas compartilham a mesma base visual do demo inteiro.",
                "icon": "workflow",
            },
            {
                "label": "Catalog sync",
                "value": "ready",
                "note": "Dados operacionais e primitives vivem no mesmo catalogo de componentes.",
                "icon": "database",
            },
        ],
        "deployment_columns": [
            {"label": "Service"},
            {"label": "Region"},
            {"label": "Updated"},
            {"label": "Status"},
            {"label": "Actions"},
        ],
        "deployments": [
            {
                "service": "edge-gateway",
                "region": "gru / sao-paulo",
                "updated_at": "2 min ago",
                "status": "ready",
                "icon": "server",
            },
            {
                "service": "billing-api",
                "region": "iad / virginia",
                "updated_at": "11 min ago",
                "status": "building",
                "icon": "database",
            },
            {
                "service": "event-worker",
                "region": "mad / madrid",
                "updated_at": "23 min ago",
                "status": "draft",
                "icon": "workflow",
            },
        ],
        "activities": [
            {
                "title": "Schema drift resolved",
                "detail": "A migration foi consolidada e a tabela principal voltou a ficar estavel.",
                "time": "4m",
                "icon": "shield-check",
            },
            {
                "title": "Preview build queued",
                "detail": "O fluxo incremental disparou um novo snapshot do studio playground.",
                "time": "9m",
                "icon": "bolt",
            },
            {
                "title": "Catalog signature refreshed",
                "detail": "Props e slots do componente Table foram expostos para docs internas.",
                "time": "16m",
                "icon": "list",
            },
        ],
        "queues": [
            {
                "name": "emails:transactional",
                "detail": "Workers com retry exponencial e render server-side.",
                "size": "12 jobs",
                "status": "ready",
            },
            {
                "name": "deployments:preview",
                "detail": "Fila de pre-render para ambientes temporarios.",
                "size": "5 jobs",
                "status": "building",
            },
            {
                "name": "search:indexer",
                "detail": "Reprocessamento manual aguardando janelas menores.",
                "size": "2 jobs",
                "status": "draft",
            },
        ],
        "shortcuts": [
            {
                "label": "Warm caches",
                "description": "Preaquece templates e rotas HTML mais acessadas no startup.",
                "command": "uv run python -m exemples.warmup",
                "status": "ready",
                "icon": "sparkles",
            },
            {
                "label": "Render catalog",
                "description": "Lista assinaturas e assets do projeto atual.",
                "command": "uv run python -m exemples.dump_catalog",
                "status": "ready",
                "icon": "terminal",
            },
            {
                "label": "Profile page render",
                "description": "Mede custo de renderizacao e compilacao para a pagina atual.",
                "command": "uv run python -m exemples.profile_page --path /forms",
                "status": "building",
                "icon": "activity",
            },
        ],
    }


def get_patterns_context() -> dict[str, object]:
    return {
        "team": [
            {"name": "Ana", "role": "Design systems lead", "status": "ready"},
            {"name": "Caio", "role": "FastAPI + data flow", "status": "building"},
            {"name": "Bia", "role": "Interaction polish", "status": "draft"},
        ],
        "state_card": {
            "title": "Server directives compiladas",
            "summary": "Esse card mistura jx-class, jx-text, jx-html e jx-show sem inventar runtime pesado no cliente.",
            "status": "ready",
            "active": True,
            "note_visible": True,
            "note": "O HTML do badge veio pronto do contexto e entrou no template via jx-html.",
            "badge_html": "<strong>directive output</strong>",
        },
        "attrs_demo": {
            "title": "Attrs livres e previsiveis",
            "summary": "Componentes podem receber tooltip, data-* e atributos de Alpine/HTMX sem declarar tudo como prop.",
            "variant": "playground",
            "tooltip": "Esse tooltip veio de um custom directive do app demo.",
        },
        "interactive_demo": {
            "densities": [
                {"label": "Comfortable", "value": "comfortable"},
                {"label": "Compact", "value": "compact"},
                {"label": "Editorial", "value": "editorial"},
            ],
        },
        "tooltip_examples": [
            {
                "label": "Server action",
                "icon": "server",
                "description": "O trigger continua server-first; o tooltip so melhora a leitura contextual.",
            },
            {
                "label": "Partial refresh",
                "icon": "workflow",
                "description": "Bom para explicar o que um botao HTMX ou um chip de status realmente faz.",
            },
            {
                "label": "Design token",
                "icon": "palette",
                "description": "Ajuda a documentar variantes sem entupir o layout com texto persistente.",
            },
        ],
        "hover_examples": [
            {
                "title": "Gateway rollout",
                "eyebrow": "Hover card",
                "summary": "Painel leve para contexto denso sem abrir modal e sem quebrar o ritmo da pagina.",
                "icon": "bolt",
                "trigger": "Ver rollout",
                "points": [
                    "48 requests/s durante o warmup.",
                    "Backfill parcial em 3 regioes.",
                    "Health checks voltando em 118 ms.",
                ],
            },
            {
                "title": "Catalog insights",
                "eyebrow": "Tooling",
                "summary": "Bom para metadados, signatures e pequenos checklists de componentes.",
                "icon": "database",
                "trigger": "Ver catalogo",
                "points": [
                    "Slots nomeados expostos para docs internas.",
                    "Assets de CSS e JS indexados no catalog.",
                    "Props opcionais e obrigatorias ficam visiveis no tooling.",
                ],
            },
        ],
        "accordion_examples": [
            {
                "title": "Accordion nativo",
                "summary": "Disclosure simples, acessivel e sem runtime adicional.",
                "open": True,
                "points": [
                    "Usa <details> e <summary> como base.",
                    "Recebe attrs passthrough normalmente.",
                    "Continua server-first, sem precisar de um widget JS dedicado.",
                ],
            },
            {
                "title": "Select + toggles",
                "summary": "Primitives focadas em formularios e playgrounds locais.",
                "open": False,
                "points": [
                    "Select aceita options vindas do servidor.",
                    "Checkbox e Switch aceitam x-model sem boilerplate.",
                    "O preview local muda sem sair do fluxo do PJX.",
                ],
            },
        ],
        "snippets": [
            {
                "title": "Props declaradas no topo",
                "icon": "layout",
                "kind": "props",
                "description": "Props continuam explicitas e parseaveis, sem comentario magico.",
                "code": '{% props title: str, tone: str = "warm" %}',
            },
            {
                "title": "Slots scoped",
                "icon": "workflow",
                "kind": "slots",
                "description": "O componente expone um contrato e o consumidor decide a marcação final.",
                "code": '{% slot item(value, index) %}\\n  <li>{{ index + 1 }}. {{ value.name }}</li>\\n{% endslot %}',
            },
            {
                "title": "Attrs passthrough",
                "icon": "terminal",
                "kind": "attrs",
                "description": "HTMX, Alpine e data attributes passam sem boilerplate extra.",
                "code": '<ThemePanel tooltip="..." x-data="{ open: false }" data_variant="playground" />',
            },
        ],
    }


def get_forms_context(*, errors: dict[str, str] | None = None, submitted: bool = False) -> dict[str, object]:
    current_errors = errors or {}
    current_values = (
        dict(last_form_submission)
        if submitted and last_form_submission is not None
        else dict(form_demo_state)
    )

    return {
        "form": dict(form_demo_state),
        "errors": current_errors,
        "submitted": submitted,
        "submitted_payload": dict(last_form_submission) if last_form_submission is not None else None,
        "primitives": [
            {
                "name": "Field",
                "icon": "list",
                "summary": "Agrupa label, hint e error num contrato unico e previsivel.",
                "tokens": ["label", "hint", "error", "required"],
            },
            {
                "name": "Input",
                "icon": "mail",
                "summary": "Input HTML normal com classes, estados invalidos e attrs passthrough.",
                "tokens": ["type", "autocomplete", "data-*", "x-*"],
            },
            {
                "name": "Textarea",
                "icon": "terminal",
                "summary": "Campo multiline com o mesmo estilo e contrato do Input.",
                "tokens": ["rows", "invalid", "placeholder", "required"],
            },
            {
                "name": "List",
                "icon": "table",
                "summary": "Primitive para sequencias, empty states e conteudo via scoped slot.",
                "tokens": ["item slot", "empty slot", "divided", "compact"],
            },
            {
                "name": "Select",
                "icon": "workflow",
                "summary": "Select estilizado com placeholder, options vindas do servidor e attrs livres.",
                "tokens": ["options", "invalid", "disabled", "x-model"],
            },
            {
                "name": "Checkbox",
                "icon": "shield-check",
                "summary": "Controle booleano compacto, pronto para forms reais ou Alpine local.",
                "tokens": ["checked", "value", "disabled", "x-model"],
            },
            {
                "name": "Switch",
                "icon": "activity",
                "summary": "Toggle visual para estados de feature flag, config ou preferencia.",
                "tokens": ["checked", "disabled", "label", "x-model"],
            },
            {
                "name": "Accordion",
                "icon": "blocks",
                "summary": "Disclosure nativo para advanced settings, docs internas e paines progressivos.",
                "tokens": ["title", "summary", "open", "attrs"],
            },
        ],
        "interactive_demo": {
            "regions": [
                {"label": "GRU / Sao Paulo", "value": "gru"},
                {"label": "IAD / Virginia", "value": "iad"},
                {"label": "MAD / Madrid", "value": "mad"},
            ],
            "plans": [
                {"label": "Starter", "value": "starter"},
                {"label": "Team", "value": "team"},
                {"label": "Enterprise", "value": "enterprise"},
            ],
        },
        "validation_modal": {
            "description": "Resumo rapido do estado atual do payload, das regras do servidor e do que ainda falta antes do submit final.",
            "checklist": [
                "Nome precisa ter 3+ caracteres.",
                "Email precisa ter formato entregavel.",
                "Brief precisa trazer contexto suficiente para o payload final.",
            ],
            "tips": [
                "Use o modal para revisar o estado sem perder o contexto da pagina.",
                "Tooltip e hover states complementam a leitura sem exigir mais screens.",
            ],
        },
        "validation_rules": _form_validation_rules(current_values, current_errors, submitted),
        "form_status": _form_status(current_errors, submitted),
    }


def submit_forms_demo(name: str, email: str, message: str) -> dict[str, object]:
    global last_form_submission

    payload: FormValues = {
        "name": name.strip(),
        "email": email.strip().lower(),
        "message": " ".join(message.strip().split()),
    }
    form_demo_state.update(payload)
    errors = _validate_form_payload(payload)

    if errors:
        return get_forms_context(errors=errors)

    last_form_submission = {
        "name": payload["name"],
        "email": payload["email"],
        "message": payload["message"],
    }
    form_demo_state.update({"name": "", "email": "", "message": ""})
    return get_forms_context(submitted=True)


def get_catalog_context(catalog: object) -> dict[str, object]:
    catalog_api = cast(Any, catalog)
    templates = cast(list[str], catalog_api.list_components())
    entries: list[dict[str, object]] = []

    for template_path in templates:
        signature = cast(dict[str, object], catalog_api.get_signature(template_path))
        slots = cast(list[str], signature["slots"])
        css_assets = cast(list[str], signature["css"])
        js_assets = cast(list[str], signature["js"])
        required = cast(list[str], signature["required"])
        optional = cast(list[str], signature["optional"])

        entries.append(
            {
                "template": template_path,
                "component": signature["component"],
                "required": required,
                "optional": optional,
                "slots": slots,
                "css": css_assets,
                "js": js_assets,
                "status": "ready" if css_assets or js_assets or slots else "draft",
            }
        )

    return {
        "stats": {
            "total": len(entries),
            "with_slots": sum(1 for entry in entries if entry["slots"]),
            "with_assets": sum(1 for entry in entries if entry["css"] or entry["js"]),
        },
        "entries": entries,
    }


def _validate_form_payload(values: FormValues) -> dict[str, str]:
    errors: dict[str, str] = {}

    if len(values["name"]) < 3:
        errors["name"] = "Use pelo menos 3 caracteres no nome."

    email = values["email"]
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        errors["email"] = "Informe um email valido para continuarmos."

    if len(values["message"]) < 24:
        errors["message"] = "Explique um pouco mais o projeto para o payload ficar util."

    return errors


def _form_validation_rules(
    values: dict[str, str],
    errors: dict[str, str],
    submitted: bool,
) -> list[dict[str, str]]:
    return [
        _rule_entry(
            label="Name with 3+ chars",
            detail="Evita payloads vagos e melhora o contrato do submit.",
            value=values.get("name", ""),
            field="name",
            errors=errors,
            submitted=submitted,
        ),
        _rule_entry(
            label="Email with basic delivery shape",
            detail="Mantem o servidor no comando da aceitacao do payload.",
            value=values.get("email", ""),
            field="email",
            errors=errors,
            submitted=submitted,
        ),
        _rule_entry(
            label="Brief with enough context",
            detail="A resposta volta com mais sinal quando o pedido tem contexto minimo.",
            value=values.get("message", ""),
            field="message",
            errors=errors,
            submitted=submitted,
        ),
    ]


def _form_status(errors: dict[str, str], submitted: bool) -> dict[str, str]:
    if submitted:
        return {
            "status": "ready",
            "summary": "Payload aceito. O servidor limpou o formulario e preservou a ultima submissao valida.",
        }
    if errors:
        return {
            "status": "building",
            "summary": "Os erros vieram do servidor e voltaram alinhados por campo, sem reload completo.",
        }
    return {
        "status": "draft",
        "summary": "Preencha os campos e envie. O objetivo aqui e mostrar validacao incremental com primitives reutilizaveis.",
    }


def _rule_entry(
    *,
    label: str,
    detail: str,
    value: str,
    field: str,
    errors: dict[str, str],
    submitted: bool,
) -> dict[str, str]:
    has_value = bool(value)
    if field in errors and has_value:
        status = "building"
    elif field in errors:
        status = "draft"
    elif submitted:
        status = "ready"
    elif has_value:
        status = "building"
    else:
        status = "draft"

    icon = "shield-check" if status == "ready" else "circle-alert" if field in errors else "list"
    return {
        "label": label,
        "detail": detail,
        "status": status,
        "icon": icon,
    }
