from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import wraps
from inspect import Parameter, Signature, isawaitable, signature
from pathlib import Path
from typing import Any, TypeAlias, TypedDict, cast

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from starlette.staticfiles import StaticFiles
from starlette.routing import Mount

from .catalog import Catalog, TemplateMount
from .models import AssetImport


@dataclass(slots=True, frozen=True)
class RenderResult:
    context: Mapping[str, Any] = field(default_factory=dict)
    template: str | None = None
    target: str | None = None
    status_code: int = 200
    headers: Mapping[str, str] = field(default_factory=dict)
    push_url: str | None = None


@dataclass(slots=True, frozen=True)
class _PendingRoute:
    path: str
    template: str
    methods: tuple[str, ...]
    target: str | None
    name: str | None
    include_in_schema: bool
    endpoint: Callable[..., Any]


@dataclass(slots=True, frozen=True)
class _PendingDirective:
    name: str
    fn: Callable[..., Any]


def is_htmx_request(request: Request | None) -> bool:
    return request is not None and request.headers.get("HX-Request") == "true"


PACKAGE_ROOT = Path(__file__).resolve().parent
PACKAGE_STATIC_ROOT = PACKAGE_ROOT / "static"
DEFAULT_FRAMEWORK_STATIC_URL = "/_pjx"


class TemplateMountMapping(TypedDict, total=False):
    path: str | Path
    prefix: str


TemplateMountInput: TypeAlias = str | Path | TemplateMount | TemplateMountMapping


class PJXRouter:
    def __init__(self, *, prefix: str = "") -> None:
        self.prefix = _normalize_prefix(prefix)
        self._pending_routes: list[_PendingRoute] = []
        self._pending_directives: list[_PendingDirective] = []

    @property
    def routes(self) -> tuple[_PendingRoute, ...]:
        return tuple(self._pending_routes)

    @property
    def directives(self) -> tuple[_PendingDirective, ...]:
        return tuple(self._pending_directives)

    def page(
        self,
        path: str,
        *,
        template: str,
        target: str | None = None,
        methods: Sequence[str] = ("GET",),
        name: str | None = None,
        include_in_schema: bool = True,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._queue_route(
            path=path,
            template=template,
            target=target,
            methods=methods,
            name=name,
            include_in_schema=include_in_schema,
        )

    def action(
        self,
        path: str,
        *,
        template: str,
        target: str,
        methods: Sequence[str] = ("POST",),
        name: str | None = None,
        include_in_schema: bool = False,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._queue_route(
            path=path,
            template=template,
            target=target,
            methods=methods,
            name=name,
            include_in_schema=include_in_schema,
        )

    def register_directive(self, name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        self._pending_directives.append(_PendingDirective(name=name, fn=fn))
        return fn

    def directive(self, name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            return self.register_directive(name, fn)

        return decorator

    def include(self, *routers: PJXRouter) -> PJXRouter:
        for router in routers:
            self._pending_routes.extend(router.routes)
            self._pending_directives.extend(router.directives)
        return self

    def include_router(self, *routers: PJXRouter) -> PJXRouter:
        return self.include(*routers)

    def _queue_route(
        self,
        *,
        path: str,
        template: str,
        target: str | None,
        methods: Sequence[str],
        name: str | None,
        include_in_schema: bool,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        route_path = _join_prefix(self.prefix, path)

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._pending_routes.append(
                _PendingRoute(
                    path=route_path,
                    template=template,
                    methods=tuple(methods),
                    target=target,
                    name=name,
                    include_in_schema=include_in_schema,
                    endpoint=fn,
                )
            )
            return fn

        return decorator


class PJX:
    def __init__(
        self,
        *,
        root: str | Path,
        templates: TemplateMountInput | Sequence[TemplateMountInput] = "templates",
        routers: Sequence[PJXRouter] | None = None,
        browser: Sequence[str] | None = None,
        css: str | None = None,
        renderer: str = "jinja2",
        aliases: Mapping[str, str] | None = None,
        auto_reload: bool = True,
        static_url: str = "/static",
        static_dir: str | Path = "static",
        framework_static_url: str = DEFAULT_FRAMEWORK_STATIC_URL,
    ) -> None:
        self.root = Path(root)
        template_mounts = _resolve_template_mounts(self.root, templates)
        self.templates_root = template_mounts[0].path
        resolved_aliases = {"@": str(self.templates_root)}
        if aliases:
            resolved_aliases.update(aliases)
        self.browser = tuple(browser or ())
        self.css = css
        self.renderer = renderer
        self.static_url = static_url.rstrip("/") or "/static"
        self.framework_static_url = framework_static_url.rstrip("/") or DEFAULT_FRAMEWORK_STATIC_URL
        self.static_dir = self.root / static_dir if not Path(static_dir).is_absolute() else Path(static_dir)
        self.catalog = Catalog(
            root=str(self.templates_root),
            aliases=dict(resolved_aliases),
            auto_reload=auto_reload,
        )
        if template_mounts[0].prefix is not None:
            self.catalog.add_template_root(
                template_mounts[0].path,
                prefix=template_mounts[0].prefix,
            )
        for template_mount in template_mounts[1:]:
            self.catalog.add_template_root(
                template_mount.path,
                prefix=template_mount.prefix,
            )
        self._app: FastAPI | None = None
        self._pending_routes: list[_PendingRoute] = []
        self._included_routers: set[int] = set()
        self._configure_integrations()
        if routers:
            self.include(*routers)

    def app(self, *args: Any, **kwargs: Any) -> FastAPI:
        if self._app is not None:
            return self._app

        app = FastAPI(*args, **kwargs)
        app.state.pjx = self
        app.state.pjx_catalog = self.catalog
        self._mount_static(app)
        self._mount_framework_static(app)
        self._register_pending_routes(app)
        self._app = app
        return app

    def fastapi(self, *args: Any, **kwargs: Any) -> FastAPI:
        return self.app(*args, **kwargs)

    def page(
        self,
        path: str,
        *,
        template: str,
        target: str | None = None,
        methods: Sequence[str] = ("GET",),
        name: str | None = None,
        include_in_schema: bool = True,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._queue_route(
            path=path,
            template=template,
            target=target,
            methods=methods,
            name=name,
            include_in_schema=include_in_schema,
        )

    def action(
        self,
        path: str,
        *,
        template: str,
        target: str,
        methods: Sequence[str] = ("POST",),
        name: str | None = None,
        include_in_schema: bool = False,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._queue_route(
            path=path,
            template=template,
            target=target,
            methods=methods,
            name=name,
            include_in_schema=include_in_schema,
        )

    def register_directive(self, name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        self.catalog.register_directive(name, fn)
        return fn

    def directive(self, name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self.catalog.register_directive(name, fn)
            return fn

        return decorator

    def include(self, *routers: PJXRouter) -> PJX:
        for router in routers:
            router_id = id(router)
            if router_id in self._included_routers:
                continue
            self._included_routers.add(router_id)

            for pending_directive in router.directives:
                self.catalog.register_directive(pending_directive.name, pending_directive.fn)

            for route in router.routes:
                self._pending_routes.append(route)
                if self._app is not None:
                    _register_route(self._app, self.catalog, route)

        return self

    def include_router(self, *routers: PJXRouter) -> PJX:
        return self.include(*routers)

    def add_templates(self, *templates: TemplateMountInput) -> PJX:
        if not templates:
            return self
        for template_mount in _resolve_template_mounts(self.root, templates):
            self.catalog.add_template_root(
                template_mount.path,
                prefix=template_mount.prefix,
            )
        return self

    def tailwind_content_globs(self) -> tuple[str, ...]:
        template_globs = {str(mount.path / "**/*.jinja") for mount in self.catalog.template_mounts}
        return (
            str(self.root / "**/*.pjx"),
            *sorted(template_globs),
            str(self.root / "**/*.py"),
        )

    def integrations(self) -> dict[str, Any]:
        return {
            "renderer": self.renderer,
            "browser": list(self.browser),
            "css": self.css,
            "templates": [str(path) for path in self.catalog.template_roots],
            "template_mounts": [
                {
                    "path": str(mount.path),
                    "prefix": mount.prefix,
                    "alias": mount.alias,
                }
                for mount in self.catalog.template_mounts
            ],
            "static_url": self.static_url,
            "framework_static_url": self.framework_static_url,
        }

    def _configure_integrations(self) -> None:
        for asset in self._framework_assets():
            self.catalog.add_asset(kind=asset.kind, path=asset.path)

    def _framework_assets(self) -> tuple[AssetImport, ...]:
        assets: list[AssetImport] = []
        browser_set = set(self.browser)
        if "htmx" in browser_set:
            assets.append(AssetImport(kind="js", path=f"{self.framework_static_url}/js/htmx.min.js"))
        if "alpine" in browser_set:
            assets.append(AssetImport(kind="js", path=f"{self.framework_static_url}/js/alpine.min.js"))
        if browser_set:
            assets.append(AssetImport(kind="js", path=f"{self.framework_static_url}/js/pjx-browser.js"))
        return tuple(assets)

    def _queue_route(
        self,
        *,
        path: str,
        template: str,
        target: str | None,
        methods: Sequence[str],
        name: str | None,
        include_in_schema: bool,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            route = _PendingRoute(
                path=path,
                template=template,
                methods=tuple(methods),
                target=target,
                name=name,
                include_in_schema=include_in_schema,
                endpoint=fn,
            )
            self._pending_routes.append(route)
            if self._app is not None:
                _register_route(self._app, self.catalog, route)
            return fn

        return decorator

    def _register_pending_routes(self, app: FastAPI) -> None:
        for route in self._pending_routes:
            _register_route(app, self.catalog, route)

    def _mount_static(self, app: FastAPI) -> None:
        if self.static_dir.exists() and not _has_mount(app, self.static_url):
            app.mount(self.static_url, StaticFiles(directory=self.static_dir), name="static")

    def _mount_framework_static(self, app: FastAPI) -> None:
        if PACKAGE_STATIC_ROOT.exists() and not _has_mount(app, self.framework_static_url):
            app.mount(
                self.framework_static_url,
                StaticFiles(directory=PACKAGE_STATIC_ROOT),
                name="pjx-static",
            )


def _register_route(app: FastAPI, catalog: Catalog, route: _PendingRoute) -> None:
    endpoint = _make_html_endpoint(
        catalog,
        route.endpoint,
        route.template,
        route.target,
    )
    app.api_route(
        route.path,
        methods=list(route.methods),
        response_class=HTMLResponse,
        name=route.name,
        include_in_schema=route.include_in_schema,
    )(endpoint)


def _make_html_endpoint(
    catalog: Catalog,
    fn: Callable[..., Any],
    default_template: str,
    default_target: str | None,
) -> Callable[..., Any]:
    original_signature = signature(fn)
    route_signature = _ensure_request_signature(original_signature)
    accepts_request = "request" in original_signature.parameters

    @wraps(fn)
    async def endpoint(*args: Any, **kwargs: Any) -> Response:
        request = _extract_request(args, kwargs)
        call_kwargs = dict(kwargs)
        if not accepts_request:
            call_kwargs.pop("request", None)
        result = fn(*args, **call_kwargs)
        if isawaitable(result):
            result = await result
        if isinstance(result, Response):
            return result

        render_result = _coerce_render_result(
            result,
            default_template=default_template,
            default_target=default_target,
        )
        partial = bool(render_result.target) and is_htmx_request(request)
        template_name = render_result.template
        if template_name is None:
            raise RuntimeError("PJX route resolution produced no template name.")
        html = catalog.render_string(
            template=template_name,
            context=dict(render_result.context),
            request=request,
            partial=partial,
            target=render_result.target if partial else None,
        )
        response = HTMLResponse(content=html, status_code=render_result.status_code)
        for header_name, header_value in render_result.headers.items():
            response.headers[header_name] = header_value
        if render_result.push_url:
            response.headers["HX-Push-Url"] = render_result.push_url
        return response

    cast(Any, endpoint).__signature__ = route_signature
    return endpoint


def _coerce_render_result(
    result: Any,
    *,
    default_template: str,
    default_target: str | None,
) -> RenderResult:
    if result is None:
        return RenderResult(template=default_template, target=default_target)
    if isinstance(result, RenderResult):
        return RenderResult(
            context=result.context,
            template=result.template or default_template,
            target=result.target or default_target,
            status_code=result.status_code,
            headers=result.headers,
            push_url=result.push_url,
        )
    if isinstance(result, Mapping):
        return RenderResult(
            context=result,
            template=default_template,
            target=default_target,
        )
    raise TypeError(
        "PJX HTML handlers must return a mapping, RenderResult, Response, or None."
    )


def _ensure_request_signature(sig: Signature) -> Signature:
    if "request" in sig.parameters:
        return sig
    request_param = Parameter(
        "request",
        kind=Parameter.KEYWORD_ONLY,
        annotation=Request,
    )
    params = list(sig.parameters.values())
    insert_at = len(params)
    for index, parameter in enumerate(params):
        if parameter.kind == Parameter.VAR_KEYWORD:
            insert_at = index
            break
    params.insert(insert_at, request_param)
    return sig.replace(parameters=params)


def _extract_request(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Request | None:
    request = kwargs.get("request")
    if isinstance(request, Request):
        return request
    for value in args:
        if isinstance(value, Request):
            return value
    return None


def _has_mount(app: FastAPI, path: str) -> bool:
    return any(isinstance(route, Mount) and route.path == path for route in app.router.routes)


def _normalize_prefix(prefix: str) -> str:
    if not prefix or prefix == "/":
        return ""
    return "/" + prefix.strip("/")


def _join_prefix(prefix: str, path: str) -> str:
    normalized_path = "/" + path.lstrip("/")
    if not prefix:
        return normalized_path
    return f"{prefix}{normalized_path}"


def _resolve_template_mounts(
    root: Path,
    templates: TemplateMountInput | Sequence[TemplateMountInput],
) -> list[TemplateMount]:
    candidates = _coerce_template_mount_inputs(templates)

    resolved: list[TemplateMount] = []
    for candidate in candidates:
        mount = _resolve_template_mount(root, candidate)
        if mount not in resolved:
            resolved.append(mount)

    if not resolved:
        raise ValueError("PJX requires at least one template root.")

    return resolved


def _resolve_template_mount(root: Path, candidate: TemplateMountInput) -> TemplateMount:
    if isinstance(candidate, TemplateMount):
        template_root = candidate.path
        if not template_root.is_absolute():
            template_root = root / template_root
        return TemplateMount(path=template_root, prefix=_normalize_template_mount_prefix(candidate.prefix))

    if isinstance(candidate, Mapping):
        mapping = cast(TemplateMountMapping, candidate)
        raw_path = mapping.get("path")
        if raw_path is None:
            raise ValueError("Template mount mappings require a 'path' key.")
        raw_prefix = mapping.get("prefix")
        template_root = Path(raw_path)
        if not template_root.is_absolute():
            template_root = root / template_root
        return TemplateMount(path=template_root, prefix=_normalize_template_mount_prefix(raw_prefix))

    template_root = Path(candidate)
    if not template_root.is_absolute():
        template_root = root / template_root
    return TemplateMount(path=template_root)


def _normalize_template_mount_prefix(prefix: str | None) -> str | None:
    if prefix is None:
        return None
    normalized = prefix.strip()
    if not normalized or normalized == "@":
        return None
    normalized = normalized.lstrip("@").strip("/")
    return normalized or None


def _coerce_template_mount_inputs(
    templates: TemplateMountInput | Sequence[TemplateMountInput],
) -> list[TemplateMountInput]:
    if isinstance(templates, (str, Path, TemplateMount)):
        return [templates]
    if isinstance(templates, Mapping):
        return [cast(TemplateMountMapping, templates)]
    return list(templates)


PJXDeclarative = PJXRouter
