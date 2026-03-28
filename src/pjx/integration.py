"""PJX FastAPI integration — decorators and helpers."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, get_args, get_origin

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from markupsafe import Markup

from pjx.cache import TemplateCache
from pjx.compilation import CompilationPipeline
from pjx.compiler import Compiler
from pjx.config import PJXConfig
from pjx.engine import HybridEngine, create_engine
from pjx.layout import UI_DIR
from pjx.props import validate_props
from pjx.registry import ComponentRegistry
from pjx.router import FileRouter
from pjx.setup import (
    setup_cache,
    setup_cors,
    setup_csrf,
    setup_health,
    setup_logging,
    setup_static,
)

_INCLUDE_RE = re.compile(r'\{%[-\s]*include\s+"([^"]+)"')
_UNSET: object = object()  # sentinel for "use PJX default layout"


class FormData:
    """Marker for ``Annotated`` form/query parameters.

    Usage::

        from pjx import FormData

        @pjx.page("/search", methods=["GET", "POST"])
        async def search(form: Annotated[SearchForm, FormData()]):
            return {"results": do_search(form.query)}
    """


@dataclass
class SEO:
    """SEO metadata for a page.

    Pass an instance in the handler's return dict under the ``seo`` key.
    The layout template receives all fields as ``seo.*`` variables.

    Example::

        @pjx.page("/about")
        async def about():
            return {
                "seo": SEO(
                    title="About Us",
                    description="Learn more about our team.",
                    og_image="/static/images/og-about.png",
                ),
            }
    """

    title: str = ""
    description: str = ""
    keywords: str = ""
    canonical: str = ""
    og_title: str = ""
    og_description: str = ""
    og_image: str = ""
    og_type: str = "website"
    og_url: str = ""
    twitter_card: str = "summary_large_image"
    twitter_title: str = ""
    twitter_description: str = ""
    twitter_image: str = ""
    robots: str = ""
    extra_meta: list[dict[str, str]] = field(default_factory=list)


class PJX:
    """PJX integration for FastAPI applications.

    Args:
        app: The FastAPI application instance.
        config: Optional PJX configuration. Uses defaults if not provided.
        layout: Optional layout template path (e.g. ``"layouts/Base.jinja"``).
            If set, all ``page()`` routes wrap their content in this layout.
            The layout receives ``body`` (rendered page HTML) and all context
            vars from the handler.
        seo: Default SEO metadata applied to all pages. Per-page SEO returned
            from handlers is merged on top (non-empty fields override defaults).
    """

    def __init__(
        self,
        app: FastAPI,
        config: PJXConfig | None = None,
        layout: str | None = None,
        seo: SEO | None = None,
        csrf: bool = False,
        csrf_secret: str | None = None,
        csrf_exempt_paths: set[str] | None = None,
        health: bool = False,
    ) -> None:
        self.app = app
        self.config = config or PJXConfig()
        self.layout = layout
        self.default_seo = seo or SEO()

        # Include built-in ui/ directory so layout components are resolvable
        tpl_dirs = [Path(d) for d in self.config.template_dirs] + [UI_DIR.parent]
        self.registry = ComponentRegistry(tpl_dirs)
        self.engine = create_engine(self.config.engine)
        self.compiler = Compiler(registry=self.registry)
        self.cache = TemplateCache()
        self.pipeline = CompilationPipeline(
            compiler=self.compiler,
            registry=self.registry,
            engine=self.engine,
            cache=self.cache,
            config=self.config,
        )

        self._csrf_middleware: Any | None = None
        self._middleware_registry: dict[str, Callable] = {}
        self._pattern_middleware: list[tuple[str, Callable]] = []
        self._registered_paths: set[str] = set()

        # Setup application infrastructure
        setup_static(app, self.config)

        if csrf:
            self._csrf_middleware = setup_csrf(app, csrf_secret, csrf_exempt_paths)

        setup_cors(app, self.config)
        setup_cache(app, self.config)

        if health:
            setup_health(app, self.config)

        setup_logging(self.config)

        # Pre-register built-in layout components and compile layout
        self.pipeline.register_builtin_layouts()
        if self.layout:
            self.pipeline.compile_template(self.layout)

    def page(
        self,
        path: str,
        template: str | None = None,
        *,
        title: str | None = None,
        seo: SEO | None = None,
        layout: str | None | object = _UNSET,
        methods: list[str] | None = None,
        **route_kwargs: Any,
    ) -> Callable:
        """Decorator to register a page route.

        Args:
            path: URL path for the route.
            template: Template path (relative to template_dirs).
                Auto-discovered from function name if omitted.
            title: Page title — shortcut for ``seo=SEO(title=...)``.
            seo: Per-page SEO overrides merged on top of the global default.
            layout: Layout template for this page. Uses the PJX default
                layout if not specified. Pass ``None`` to disable layout.
            methods: HTTP methods for this route. Defaults to ``["GET"]``.
                Add ``"POST"`` to handle form submissions.
            **route_kwargs: Additional kwargs for FastAPI route.
        """
        page_layout: str | None = self.layout if layout is _UNSET else layout  # ty: ignore[invalid-assignment]
        page_methods = methods or ["GET"]

        # Build per-page SEO from decorator args
        if seo and title:
            from dataclasses import replace

            seo = replace(seo, title=title)
        elif title:
            seo = SEO(title=title)
        page_seo = seo

        def decorator[F: Callable[..., Any]](func: F) -> F:
            func_name = getattr(func, "__name__", "unknown")
            tpl = template or f"{func_name}.jinja"

            # Discover middleware from template frontmatter
            tpl_middleware: list[str] = []
            try:
                tpl_path = self.pipeline.find_template(tpl)
                component = _parse_file(tpl_path)
                for mw_decl in component.middleware:
                    tpl_middleware.extend(mw_decl.names)
            except FileNotFoundError:
                pass

            async def wrapper(request: Request) -> HTMLResponse:
                # Run pattern-based middleware
                for mw_func in self._get_pattern_middleware(path):
                    result = await mw_func(request)
                    if result is not None:
                        return result  # ty: ignore[invalid-return-type]

                # Run middleware from template frontmatter
                for mw_name in tpl_middleware:
                    mw_func = self._middleware_registry.get(mw_name)
                    if mw_func is not None:
                        await mw_func(request)

                context = await _call_handler(func, request)
                if not isinstance(context, dict):
                    context = {}
                context["request"] = request
                # Decorator-level SEO as base, handler can still override
                if page_seo and "seo" not in context:
                    context["seo"] = page_seo
                html = self.render(tpl, context, layout=page_layout)
                return HTMLResponse(html)

            wrapper.__name__ = func_name
            wrapper.__doc__ = getattr(func, "__doc__", None)
            self.app.add_api_route(path, wrapper, methods=page_methods, **route_kwargs)
            return wrapper  # ty: ignore[invalid-return-type]

        return decorator

    def component(self, template: str) -> Callable[..., Any]:
        """Decorator to register a component partial route."""

        def decorator[F: Callable[..., Any]](func: F) -> F:
            async def wrapper(request: Request) -> HTMLResponse:
                context = await _call_handler(func, request)
                if not isinstance(context, dict):
                    context = {}
                context["request"] = request
                html = self.render(template, context)
                return HTMLResponse(html)

            wrapper.__name__ = getattr(func, "__name__", "unknown")
            wrapper.__doc__ = getattr(func, "__doc__", None)
            return wrapper  # ty: ignore[invalid-return-type]

        return decorator

    def auto_routes(self, pages_dir: Path | str | None = None) -> None:
        """Discover and register all file-based routes from a pages directory.

        Args:
            pages_dir: Directory to scan. Defaults to ``config.pages_dir``.
        """
        dir_ = Path(pages_dir) if pages_dir else self.config.pages_dir
        router = FileRouter(dir_, [Path(d) for d in self.config.template_dirs])
        router.scan()
        router.register(self)

    def action(self, name: str) -> Callable:
        """Decorator to register a server action handler.

        Server actions are auto-registered as POST routes at
        ``/_pjx/actions/{name}``. Reference them in templates via
        ``action:post="@name"``.

        Args:
            name: Action identifier.
        """
        from pjx.router import _register_action_routes

        def decorator(func: Callable) -> Callable:
            _register_action_routes(self, {name: func})
            return func

        return decorator

    def middleware(
        self, name: str | None = None, *, pattern: str | None = None
    ) -> Callable:
        """Decorator to register a middleware function.

        Can be used as a named middleware (referenced from frontmatter)
        or as a pattern-based middleware (applied to matching routes).

        Args:
            name: Middleware identifier used in frontmatter declarations.
            pattern: URL pattern to match (e.g. ``"/admin/*"``).
                Uses ``fnmatch`` syntax.
        """

        def decorator(func: Callable) -> Callable:
            if name:
                self._middleware_registry[name] = func
            if pattern:
                self._pattern_middleware.append((pattern, func))
            return func

        return decorator

    def _get_pattern_middleware(self, path: str) -> list[Callable]:
        """Get all pattern-based middleware matching a URL path."""
        import fnmatch

        return [
            fn for pat, fn in self._pattern_middleware if fnmatch.fnmatch(path, pat)
        ]

    def partial(self, template: str, **props: Any) -> Markup:
        """Render a component as an HTML fragment, ready to embed in a page.

        Returns ``Markup`` so Jinja2 won't double-escape the result.

        Args:
            template: Component template path relative to template_dirs.
            **props: Props passed to the component as keyword arguments.
        """
        return self.render(template, props)

    def render(
        self,
        template: str,
        context: dict[str, Any],
        layout: str | None = None,
    ) -> Markup:
        """Compile and render a template, optionally wrapping in a layout.

        Args:
            template: Template path relative to template_dirs.
            context: Template context variables.
            layout: Optional layout template to wrap the rendered content.
        """
        from pjx.assets import AssetCollector

        css_parts: list[str] = []
        asset_collector = AssetCollector()

        self.pipeline.compile_template(template, css_parts, asset_collector)

        # Validate props if enabled and model is cached
        props_model = self.cache.get_props_model(template)
        if self.config.validate_props and props_model is not None:
            validate_props(props_model, context)

        # Build render context
        render_ctx = dict(context)
        render_ctx["props"] = _SimpleNamespace(context)
        render_ctx["seo"] = self._merge_seo(render_ctx.get("seo"))
        render_ctx["pjx_assets"] = asset_collector

        # Inject CSRF token helper if middleware is active
        if self._csrf_middleware is not None and "request" in render_ctx:
            request = render_ctx["request"]
            mw = self._csrf_middleware
            render_ctx["csrf_token"] = lambda: mw.get_token(request)

        # Render the page content
        compiled_src = self.cache.get_source(template) or ""
        has_includes = _INCLUDE_RE.search(compiled_src) is not None
        use_inline = (
            self.config.render_mode == "inline"
            or (
                layout is None
                and isinstance(self.engine, HybridEngine)
                and not has_includes
            )
        ) and self.cache.has_source(template)
        try:
            if use_inline:
                flat_source = Compiler.inline_includes(
                    compiled_src, self.cache._compiled_sources
                )
                body = self.engine.render_string(flat_source, render_ctx)
            else:
                body = self.engine.render(template, render_ctx)
        except Exception as exc:
            from pjx.errors import RenderError

            msg = f"error rendering {template!r}: {exc}"
            raise RenderError(msg) from exc

        # Inject scoped CSS as inline <style>
        if css_parts:
            style_tag = f"<style>\n{'\n'.join(css_parts)}\n</style>\n"
            body = style_tag + body

        # Wrap in layout if provided
        if layout:
            render_ctx["body"] = Markup(body)
            try:
                return Markup(self.engine.render(layout, render_ctx))
            except Exception as exc:
                from pjx.errors import RenderError

                msg = f"error rendering layout {layout!r}: {exc}"
                raise RenderError(msg) from exc

        return Markup(body)

    def _merge_seo(self, page_seo: SEO | None) -> SEO:
        """Merge per-page SEO over global defaults. Non-empty page fields win."""
        if page_seo is None:
            return self.default_seo
        from dataclasses import fields as dc_fields

        merged = {}
        for f in dc_fields(SEO):
            page_val = getattr(page_seo, f.name)
            default_val = getattr(self.default_seo, f.name)
            merged[f.name] = page_val if page_val else default_val
        return SEO(**merged)


def _parse_file(path: Path) -> Any:
    """Thin wrapper to avoid circular imports at module level."""
    from pjx.parser import parse_file

    return parse_file(path)


class _SimpleNamespace:
    """Dict-backed namespace so templates can use ``props.X`` syntax."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.__dict__.update(data)

    def __repr__(self) -> str:
        return f"Namespace({self.__dict__})"


async def _call_handler(func: Callable, request: Request) -> Any:
    """Call a handler function, supporting both sync and async.

    Handlers may accept:
    - ``request``: the Starlette :class:`Request` object.
    - ``Annotated[MyModel, FormData()]``: Pydantic model parsed from form
      data (POST) or query params (GET).
    """
    import inspect
    from typing import get_type_hints

    sig = inspect.signature(func)
    try:
        hints = get_type_hints(func, include_extras=True)
    except Exception:
        hints = {}

    kwargs: dict[str, Any] = {}

    for name in sig.parameters:
        if name == "request":
            kwargs["request"] = request
            continue

        annotation = hints.get(name)
        if annotation is None:
            continue

        model_type = _extract_form_model(annotation)
        if model_type is not None:
            kwargs[name] = await _parse_form_or_query(request, model_type)

    if inspect.iscoroutinefunction(func):
        return await func(**kwargs)
    return func(**kwargs)


def _extract_form_model(annotation: Any) -> type[Any] | None:
    """Extract a Pydantic BaseModel from an annotation."""
    from pydantic import BaseModel

    # Annotated[SearchForm, FormData()]
    if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        if len(args) >= 2 and any(isinstance(a, FormData) for a in args[1:]):
            model = args[0]
            if isinstance(model, type) and issubclass(model, BaseModel):
                return model
        return None

    # Bare Model (backward compat)
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation

    return None


async def _parse_form_or_query(request: Request, model: type[Any]) -> Any:
    """Parse a Pydantic model from form data (POST) or query params (GET)."""
    if request.method == "POST":
        form_data = await request.form()
        return model(**dict(form_data))
    return model(**dict(request.query_params))
