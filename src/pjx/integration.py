"""PJX FastAPI integration — decorators and helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Callable, get_args, get_origin

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from pydantic import BaseModel

from pjx.compiler import Compiler
from pjx.config import PJXConfig
from pjx.engine import EngineProtocol, HybridEngine, create_engine
from pjx.parser import parse_file
from pjx.props import generate_props_model, validate_props
from pjx.registry import ComponentRegistry

_INCLUDE_RE = re.compile(r'\{%[-\s]*include\s+"([^"]+)"')


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
    ) -> None:
        self.app = app
        self.config = config or PJXConfig()
        self.layout = layout
        self.default_seo = seo or SEO()
        self.registry = ComponentRegistry([Path(d) for d in self.config.template_dirs])
        self.engine: EngineProtocol = create_engine(self.config.engine)
        self.compiler = Compiler(registry=self.registry)
        self._props_models: dict[str, type[BaseModel]] = {}
        self._template_mtimes: dict[str, float] = {}  # path → mtime cache
        self._cached_css: dict[str, str | None] = {}
        self._cached_assets: dict[str, tuple] = {}
        self._compiled_sources: dict[str, str] = {}  # for inline rendering

        # Auto-mount static files directory
        static_dir = self.config.static_dir
        if static_dir.exists():
            from fastapi.staticfiles import StaticFiles

            app.mount("/static", StaticFiles(directory=static_dir), name="static")

        # Pre-compile layout if set
        if self.layout:
            self._compile_template(self.layout)

    def page(
        self,
        path: str,
        template: str | None = None,
        *,
        title: str | None = None,
        seo: SEO | None = None,
        layout: str | None = ...,  # type: ignore[assignment]
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
        page_layout = self.layout if layout is ... else layout
        page_methods = methods or ["GET"]

        # Build per-page SEO from decorator args
        if seo and title:
            seo = SEO(**{**seo.__dict__, "title": title})
        elif title:
            seo = SEO(title=title)
        page_seo = seo

        def decorator(func: Callable) -> Callable:
            tpl = template or f"{func.__name__}.jinja"

            async def wrapper(request: Request) -> HTMLResponse:
                context = await _call_handler(func, request)
                if not isinstance(context, dict):
                    context = {}
                context["request"] = request
                # Decorator-level SEO as base, handler can still override
                if page_seo and "seo" not in context:
                    context["seo"] = page_seo
                html = self.render(tpl, context, layout=page_layout)
                return HTMLResponse(html)

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            self.app.add_api_route(path, wrapper, methods=page_methods, **route_kwargs)
            return wrapper

        return decorator

    def component(self, template: str) -> Callable:
        """Decorator to register a component partial route."""

        def decorator(func: Callable) -> Callable:
            async def wrapper(request: Request) -> HTMLResponse:
                context = await _call_handler(func, request)
                if not isinstance(context, dict):
                    context = {}
                context["request"] = request
                html = self.render(template, context)
                return HTMLResponse(html)

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper

        return decorator

    def render(
        self,
        template: str,
        context: dict[str, Any],
        layout: str | None = None,
    ) -> str:
        """Compile and render a template, optionally wrapping in a layout.

        Args:
            template: Template path relative to template_dirs.
            context: Template context variables.
            layout: Optional layout template to wrap the rendered content.
        """
        from pjx.assets import AssetCollector

        css_parts: list[str] = []
        asset_collector = AssetCollector()

        # Compile and register the page template
        self._compile_template(template, css_parts, asset_collector)

        # Validate props if enabled and model is cached
        if self.config.validate_props and template in self._props_models:
            validate_props(self._props_models[template], context)

        # Build render context
        render_ctx = dict(context)
        render_ctx["props"] = _SimpleNamespace(context)
        render_ctx["seo"] = self._merge_seo(render_ctx.get("seo"))
        render_ctx["pjx_assets"] = asset_collector

        # Render the page content
        # Hybrid strategy: leaf partials (no layout, no includes) auto-use
        # render_string (MiniJinja); templates with includes use render (Jinja2)
        # because inlining collapses variable scopes across components.
        compiled_src = self._compiled_sources.get(template, "")
        has_includes = _INCLUDE_RE.search(compiled_src) is not None
        use_inline = (
            self.config.render_mode == "inline"
            or (
                layout is None
                and isinstance(self.engine, HybridEngine)
                and not has_includes
            )
        ) and template in self._compiled_sources
        if use_inline:
            flat_source = Compiler.inline_includes(compiled_src, self._compiled_sources)
            body = self.engine.render_string(flat_source, render_ctx)
        else:
            body = self.engine.render(template, render_ctx)

        # Inject scoped CSS as inline <style>
        if css_parts:
            style_tag = f"<style>\n{'\n'.join(css_parts)}\n</style>\n"
            body = style_tag + body

        # Wrap in layout if provided
        if layout:
            from markupsafe import Markup

            render_ctx["body"] = Markup(body)
            return self.engine.render(layout, render_ctx)

        return body

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

    def _compile_template(
        self,
        template: str,
        css_parts: list[str] | None = None,
        asset_collector: Any | None = None,
        _seen: set[str] | None = None,
    ) -> None:
        """Compile a template and all its imports, registering them in the engine.

        Uses mtime-based caching: skips recompilation if the file hasn't changed.
        The ``_seen`` set prevents diamond-dependency recompilation.
        """
        if _seen is None:
            _seen = set()
        if template in _seen:
            return
        _seen.add(template)

        template_path = self._find_template(template)

        # Mtime cache: skip if file hasn't changed since last compile
        try:
            current_mtime = template_path.stat().st_mtime
        except OSError:
            current_mtime = 0.0
        cached_mtime = self._template_mtimes.get(template)
        if cached_mtime == current_mtime and template in self._compiled_sources:
            # Still collect CSS/assets from cached compilation
            if css_parts is not None or asset_collector is not None:
                self._collect_cached_assets(template, css_parts, asset_collector)
            self._compile_imports_cached(
                template_path, css_parts, asset_collector, _seen
            )
            return

        component = parse_file(template_path)

        # Pre-register imports in the registry so the compiler can look up
        # child PropsDecl for attrs passthrough during compilation.
        self._register_imports_in_registry(component)

        compiled = self.compiler.compile(component)

        # Cache props model for runtime validation
        if component.props and template not in self._props_models:
            self._props_models[template] = generate_props_model(component.props)

        if css_parts is not None and compiled.css:
            css_parts.append(compiled.css.source)

        # Collect declared assets
        if asset_collector is not None:
            for asset in compiled.assets:
                asset_collector.add(asset)

        self._compiled_sources[template] = compiled.jinja_source
        self._template_mtimes[template] = current_mtime
        self._cached_css[template] = compiled.css.source if compiled.css else None
        self._cached_assets[template] = compiled.assets
        self.engine.add_template(template, compiled.jinja_source)
        self._register_jinja_includes(compiled.jinja_source)
        self._compile_imports(component, css_parts, asset_collector, _seen)

    def _collect_cached_assets(
        self,
        template: str,
        css_parts: list[str] | None,
        asset_collector: Any | None,
    ) -> None:
        """Re-collect CSS/assets from a previously compiled template."""
        if (
            css_parts is not None
            and template in self._cached_css
            and self._cached_css[template]
        ):
            css_parts.append(self._cached_css[template])
        if asset_collector is not None and template in self._cached_assets:
            for asset in self._cached_assets[template]:
                asset_collector.add(asset)

    def _compile_imports_cached(
        self,
        template_path: Path,
        css_parts: list[str] | None,
        asset_collector: Any | None,
        _seen: set[str],
    ) -> None:
        """Re-walk imports of a cached template to collect assets from children."""
        component = parse_file(template_path)
        for imp in component.imports:
            source = imp.source
            try:
                self._compile_template(source, css_parts, asset_collector, _seen)
            except FileNotFoundError:
                rel = str(template_path.parent / source)
                self._compile_template(rel, css_parts, asset_collector, _seen)

    def _register_imports_in_registry(self, component: Any) -> None:
        """Parse and register imported components so the compiler can look up child props."""
        for imp in component.imports:
            for name in imp.names:
                if self.registry.get(name) is not None:
                    continue
                try:
                    imp_path = self._find_template(imp.source)
                except FileNotFoundError:
                    imp_path = component.path.parent / imp.source
                    if not imp_path.exists():
                        continue
                imp_component = parse_file(imp_path)
                self.registry.register(name, imp_component)
                self._register_imports_in_registry(imp_component)

    def _compile_imports(
        self,
        component: Any,
        css_parts: list[str] | None,
        asset_collector: Any | None = None,
        _seen: set[str] | None = None,
    ) -> None:
        """Recursively compile and register imported components.

        Uses ``_seen`` to skip diamond dependencies (A→B→D, A→C→D).
        """
        if _seen is None:
            _seen = set()
        for imp in component.imports:
            source = imp.source
            if source in _seen:
                # Already compiled in this cycle — just collect cached assets
                self._collect_cached_assets(source, css_parts, asset_collector)
                continue
            _seen.add(source)
            try:
                imp_path = self._find_template(source)
            except FileNotFoundError:
                imp_path = component.path.parent / source
                if not imp_path.exists():
                    continue
            # Mtime check for imports too
            try:
                current_mtime = imp_path.stat().st_mtime
            except OSError:
                current_mtime = 0.0
            cached_mtime = self._template_mtimes.get(source)
            if cached_mtime == current_mtime and source in self._compiled_sources:
                self._collect_cached_assets(source, css_parts, asset_collector)
                imp_component = parse_file(imp_path)
                self._compile_imports(imp_component, css_parts, asset_collector, _seen)
                continue
            imp_component = parse_file(imp_path)
            imp_compiled = self.compiler.compile(imp_component)
            self._compiled_sources[source] = imp_compiled.jinja_source
            self._template_mtimes[source] = current_mtime
            self._cached_css[source] = (
                imp_compiled.css.source if imp_compiled.css else None
            )
            self._cached_assets[source] = imp_compiled.assets
            self.engine.add_template(source, imp_compiled.jinja_source)
            if css_parts is not None and imp_compiled.css:
                css_parts.append(imp_compiled.css.source)
            if asset_collector is not None:
                for asset in imp_compiled.assets:
                    asset_collector.add(asset)
            self._compile_imports(imp_component, css_parts, asset_collector, _seen)

    def _register_jinja_includes(self, source: str) -> None:
        """Find raw ``{% include "..." %}`` in compiled Jinja and register them."""
        for match in _INCLUDE_RE.finditer(source):
            inc_name = match.group(1)
            if self.engine.has_template(inc_name):
                continue
            try:
                self._compile_template(inc_name)
            except FileNotFoundError:
                pass

    def _find_template(self, template: str) -> Path:
        """Find a template file in the configured template directories."""
        for tpl_dir in self.config.template_dirs:
            candidate = Path(tpl_dir) / template
            if candidate.exists():
                return candidate
        msg = f"template not found: {template!r}"
        raise FileNotFoundError(msg)


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

    Example::

        from typing import Annotated
        from pydantic import BaseModel
        from pjx import FormData

        class SearchForm(BaseModel):
            query: str = ""

        @pjx.page("/search", methods=["GET", "POST"])
        async def search(form: Annotated[SearchForm, FormData()]):
            return {"results": do_search(form.query)}
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
    """Extract a Pydantic BaseModel from an annotation.

    Supports both ``Annotated[Model, FormData()]`` and bare ``Model``.
    """
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
