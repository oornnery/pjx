counter_state = {
    "count": 3,
}

studio_state = {
    "count": 6,
    "prompt": "Lancar uma homepage premium para analytics server-first.",
}


def get_dashboard_context():
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


def get_status_context():
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


def get_counter_context():
    return {
        "initial_count": counter_state["count"],
    }


def increment_counter():
    counter_state["count"] += 1
    return {"count": counter_state["count"]}


def decrement_counter():
    counter_state["count"] -= 1
    return {"count": counter_state["count"]}


def list_notifications():
    return get_dashboard_context()["notifications"]


def get_studio_context():
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


def increment_studio_count():
    studio_state["count"] = min(studio_state["count"] + 1, 12)
    return get_studio_context()


def decrement_studio_count():
    studio_state["count"] = max(studio_state["count"] - 1, 1)
    return get_studio_context()


def update_studio_prompt(prompt: str):
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


def _studio_lines(prompt: str, count: int):
    return [
        f"Prompt atual: {prompt}",
        f"Escala de exploracao: {count}/12",
        "Render feito no servidor e entregue pronto para o navegador.",
    ]


def _studio_highlights(prompt: str, count: int):
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


def _studio_variants(prompt: str, count: int):
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
