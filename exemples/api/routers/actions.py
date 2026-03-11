from __future__ import annotations

from typing import Annotated, Any

from fastapi import Form

from exemples.data import (
    decrement_counter,
    decrement_studio_count,
    increment_counter,
    increment_studio_count,
    submit_forms_demo,
    update_studio_prompt,
)
from pjx import PJXRouter


actions = PJXRouter()


@actions.action("/actions/counter/inc", template="pages/signals_counter.jinja", target="counter-value")
def increment_counter_action() -> dict[str, Any]:
    state = increment_counter()
    return {"initial_count": state["count"]}


@actions.action("/actions/counter/dec", template="pages/signals_counter.jinja", target="counter-value")
def decrement_counter_action() -> dict[str, Any]:
    state = decrement_counter()
    return {"initial_count": state["count"]}


@actions.action("/actions/studio/inc", template="pages/studio.jinja", target="studio-shell")
def studio_count_up() -> dict[str, Any]:
    return increment_studio_count()


@actions.action("/actions/studio/dec", template="pages/studio.jinja", target="studio-shell")
def studio_count_down() -> dict[str, Any]:
    return decrement_studio_count()


@actions.action("/actions/studio/prompt", template="pages/studio.jinja", target="studio-shell")
def studio_prompt_submit(prompt: Annotated[str, Form()]) -> dict[str, Any]:
    return update_studio_prompt(prompt)


@actions.action("/actions/forms/submit", template="pages/forms_playground.jinja", target="forms-shell")
def forms_submit_action(
    name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    message: Annotated[str, Form()],
) -> dict[str, object]:
    return submit_forms_demo(name, email, message)


__all__ = ["actions"]
