from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from jinja2 import TemplateError
from pydantic import BaseModel, ValidationError

from pjx.errors import PJXRenderError

_ALLOWED_HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})

_STATE_FORM_ERROR = "_pjx_form_validation_error"


def _format_sse_data(html: str, event_id: str | None = None, event_type: str | None = None) -> str:
    parts: list[str] = []
    if event_id is not None:
        parts.append(f"id: {event_id}\n")
    if event_type is not None:
        parts.append(f"event: {event_type}\n")
    lines = html.splitlines() or [""]
    for line in lines:
        parts.append(f"data: {line}\n")
    parts.append("\n")
    return "".join(parts)


def _coerce_form_data(form_data: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in form_data.multi_items():
        if key not in payload:
            payload[key] = value
        elif isinstance(payload[key], list):
            payload[key].append(value)
        else:
            payload[key] = [payload[key], value]
    return payload


async def _resolve_handler(func: Callable, request: Request, **kwargs: Any) -> Any:
    if asyncio.iscoroutinefunction(func):
        return await func(request, **kwargs)
    return func(request, **kwargs)


def FormData(model: type[BaseModel]) -> Any:
    """FastAPI Depends() that validates form data with a Pydantic model.

    On validation error, stores the error in request.state and returns None.
    The @ui.action decorator checks this and renders the error template.

    Usage:
        async def create_user(request, data: CreateUserForm = FormData(CreateUserForm)):
            ...
    """

    async def _dependency(request: Request) -> BaseModel | None:
        form_data = await request.form()
        payload = _coerce_form_data(form_data)
        try:
            return model.model_validate(payload)
        except ValidationError as e:
            setattr(request.state, _STATE_FORM_ERROR, e)
            return None

    return Depends(_dependency)


def _validate_method(method: str) -> str:
    method_lower = method.lower()
    if method_lower not in _ALLOWED_HTTP_METHODS:
        raise ValueError(f"HTTP method not allowed: {method!r}")
    return method_lower


class PJXRouter(APIRouter):
    def __init__(self, templates: Jinja2Templates, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._templates: Jinja2Templates = templates

    def _build_context(self, request: Request, props: Any) -> dict[str, Any]:
        return {
            "request": request,
            "props": props,
            "params": dict(request.path_params),
        }

    def _render(self, response_template: str, context: dict[str, Any] | None = None) -> str:
        template = self._templates.env.get_template(response_template)
        return template.render(context or {})

    def _render_or_raise(self, response_template: str, context: dict[str, Any]) -> str:
        try:
            return self._render(response_template, context)
        except TemplateError as exc:
            raise PJXRenderError(
                template=response_template,
                phase="render",
                cause=exc,
            ) from exc

    def render(self, response_template: str, context: dict[str, Any] | None = None) -> str:
        """Render a template. Use for error pages or anywhere outside decorators."""
        return self._render(response_template, context)

    def page(self, path: str, response_template: str, **route_kwargs: Any) -> Callable:
        route_kwargs.setdefault("response_class", HTMLResponse)
        route_kwargs.setdefault("response_model", None)

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(request: Request, **kwargs: Any) -> HTMLResponse:
                props = await _resolve_handler(func, request, **kwargs)
                if not isinstance(props, BaseModel):
                    raise TypeError(f"Handler must return a BaseModel, got {type(props)}")
                context = self._build_context(request, props)
                html = self._render_or_raise(response_template, context)
                return HTMLResponse(html)

            wrapper.__annotations__ = {"return": HTMLResponse}
            self.get(path, **route_kwargs)(wrapper)
            return wrapper

        return decorator

    def fragment(
        self,
        path: str,
        response_template: str,
        *,
        method: str = "GET",
        **route_kwargs: Any,
    ) -> Callable:
        route_kwargs.setdefault("response_class", HTMLResponse)
        route_kwargs.setdefault("response_model", None)

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(request: Request, **kwargs: Any) -> HTMLResponse:
                props = await _resolve_handler(func, request, **kwargs)
                if not isinstance(props, BaseModel):
                    raise TypeError(f"Handler must return a BaseModel, got {type(props)}")
                context = self._build_context(request, props)
                html = self._render_or_raise(response_template, context)
                headers: dict[str, str] = {}
                if hasattr(props, "__htmx_headers__"):
                    headers.update(props.__htmx_headers__)
                return HTMLResponse(html, headers=headers)

            wrapper.__annotations__ = {"return": HTMLResponse}
            route_method = getattr(self, _validate_method(method))
            route_method(path, **route_kwargs)(wrapper)
            return wrapper

        return decorator

    def action(
        self,
        path: str,
        *,
        success_template: str,
        error_template: str,
        method: str = "POST",
        **route_kwargs: Any,
    ) -> Callable:
        route_kwargs.setdefault("response_class", HTMLResponse)
        route_kwargs.setdefault("response_model", None)

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(request: Request, **kwargs: Any) -> HTMLResponse:
                validation_error = getattr(request.state, _STATE_FORM_ERROR, None)
                if validation_error is not None:
                    context = {
                        "request": request,
                        "errors": validation_error.errors(),
                        "params": dict(request.path_params),
                    }
                    html = self._render(error_template, context)
                    return HTMLResponse(html, status_code=422)

                props = await _resolve_handler(func, request, **kwargs)

                status_code = 200
                render_data = props
                if isinstance(props, ActionResult):
                    status_code = props.status
                    render_data = props.data

                context = self._build_context(request, render_data)
                html = self._render_or_raise(success_template, context)
                return HTMLResponse(html, status_code=status_code)

            wrapper.__annotations__ = {"return": HTMLResponse}
            route_method = getattr(self, _validate_method(method))
            route_method(path, **route_kwargs)(wrapper)
            return wrapper

        return decorator

    def stream(self, path: str, response_template: str, **route_kwargs: Any) -> Callable:
        route_kwargs.setdefault("response_class", StreamingResponse)
        route_kwargs.setdefault("response_model", None)

        def decorator(func: Callable) -> Callable:
            import inspect

            @wraps(func)
            async def wrapper(request: Request, **kwargs: Any) -> StreamingResponse:
                async def event_generator():
                    try:
                        async for item in func(request, **kwargs):
                            if isinstance(item, SSEEvent):
                                props = item.props
                                event_id = item.id
                                event_type = item.event
                            else:
                                props = item
                                event_id = None
                                event_type = None
                            context = self._build_context(request, props)
                            html = self._render(response_template, context)
                            yield _format_sse_data(html, event_id=event_id, event_type=event_type)
                    except asyncio.CancelledError:
                        return

                return StreamingResponse(
                    event_generator(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
                )

            # Override signature so FastAPI doesn't treat this as an async generator
            sig = inspect.signature(func)
            wrapper.__signature__ = sig.replace(return_annotation=StreamingResponse)  # ty: ignore[unresolved-attribute]
            del wrapper.__wrapped__
            self.get(path, **route_kwargs)(wrapper)
            return wrapper

        return decorator


@dataclass(frozen=True, slots=True)
class ActionResult:
    data: Any
    status: int = 200


@dataclass(frozen=True, slots=True)
class SSEEvent:
    props: Any
    id: str | None = None
    event: str | None = None
