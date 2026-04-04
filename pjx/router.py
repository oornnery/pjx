from __future__ import annotations

import asyncio
from functools import wraps
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, ValidationError

from pjx.errors import PJXRenderError


def _format_sse_data(
    html: str, event_id: str | None = None, event_type: str | None = None
) -> str:
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
            request.state.form_validation_error = e
            return None

    return Depends(_dependency)


class PJXRouter(APIRouter):
    def __init__(self, templates: Any, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._templates = templates

    def _render(
        self, response_template: str, context: dict[str, Any] | None = None
    ) -> str:
        template = self._templates.env.get_template(response_template)
        return template.render(context or {})

    def render(
        self, response_template: str, context: dict[str, Any] | None = None
    ) -> str:
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
                    raise TypeError(
                        f"Handler must return a BaseModel, got {type(props)}"
                    )
                try:
                    context = {
                        "request": request,
                        "props": props,
                        "params": dict(request.path_params),
                    }
                    html = self._render(response_template, context)
                except Exception as exc:
                    raise PJXRenderError(
                        template=response_template,
                        phase="render",
                        cause=exc,
                    ) from exc
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
                    raise TypeError(
                        f"Handler must return a BaseModel, got {type(props)}"
                    )
                try:
                    context = {
                        "request": request,
                        "props": props,
                        "params": dict(request.path_params),
                    }
                    html = self._render(response_template, context)
                except Exception as exc:
                    raise PJXRenderError(
                        template=response_template,
                        phase="render",
                        cause=exc,
                    ) from exc
                headers: dict[str, str] = {}
                if hasattr(props, "__htmx_headers__"):
                    headers.update(props.__htmx_headers__)
                return HTMLResponse(html, headers=headers)

            wrapper.__annotations__ = {"return": HTMLResponse}
            route_method = getattr(self, method.lower())
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
                validation_error = getattr(request.state, "form_validation_error", None)
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

                try:
                    context = {
                        "request": request,
                        "props": render_data,
                        "params": dict(request.path_params),
                    }
                    html = self._render(success_template, context)
                except Exception as exc:
                    raise PJXRenderError(
                        template=success_template,
                        phase="render",
                        cause=exc,
                    ) from exc
                return HTMLResponse(html, status_code=status_code)

            wrapper.__annotations__ = {"return": HTMLResponse}
            route_method = getattr(self, method.lower())
            route_method(path, **route_kwargs)(wrapper)
            return wrapper

        return decorator

    def stream(
        self, path: str, response_template: str, **route_kwargs: Any
    ) -> Callable:
        def decorator(func: Callable) -> Callable:
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
                            context = {
                                "request": request,
                                "props": props,
                                "params": dict(request.path_params),
                            }
                            html = self._render(response_template, context)
                            yield _format_sse_data(
                                html, event_id=event_id, event_type=event_type
                            )
                    except asyncio.CancelledError:
                        return

                return StreamingResponse(
                    event_generator(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
                )

            self.get(path, **route_kwargs)(wrapper)
            return wrapper

        return decorator


class ActionResult:
    def __init__(self, data: Any, status: int = 200) -> None:
        self.data = data
        self.status = status


class SSEEvent:
    def __init__(
        self, props: Any, id: str | None = None, event: str | None = None
    ) -> None:
        self.props = props
        self.id = id
        self.event = event
