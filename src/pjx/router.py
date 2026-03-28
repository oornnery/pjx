"""File-based router — scans pages directory and builds route table.

Inspired by Next.js conventions:
- ``pages/index.jinja`` → ``/``
- ``pages/about.jinja`` → ``/about``
- ``pages/blog/[slug].jinja`` → ``/blog/{slug}``
- ``pages/blog/[...slug].jinja`` → ``/blog/{slug:path}``
- ``pages/(auth)/login.jinja`` → ``/login`` (route group)
- ``pages/api/users.py`` → ``/api/users`` (API route)
"""

from __future__ import annotations

import importlib.util
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

if TYPE_CHECKING:
    from pjx.integration import PJX

logger = logging.getLogger("pjx")

# Special files that are NOT routes
_SPECIAL_FILES = frozenset(
    {"layout.jinja", "loading.jinja", "error.jinja", "not-found.jinja"}
)

# Parallel route prefix (e.g. @stats, @activity)
_PARALLEL_RE = re.compile(r"^@(\w+)$")

# Pattern for dynamic segments: [param] or [...param]
_DYNAMIC_RE = re.compile(r"^\[(?:\.\.\.)?(\w+)\]$")
_CATCH_ALL_RE = re.compile(r"^\[\.\.\.(\w+)\]$")
_GROUP_RE = re.compile(r"^\(([^)]+)\)$")


@dataclass(frozen=True, slots=True)
class RouteEntry:
    """A single discovered route from the filesystem."""

    url_pattern: str
    template: str
    handler_path: Path | None = None
    layout_chain: tuple[str, ...] = ()
    loading: str | None = None
    error: str | None = None
    not_found: str | None = None
    parallel_slots: dict[str, str] | None = None
    methods: tuple[str, ...] = ("GET",)
    middleware: tuple[str, ...] = ()
    is_api: bool = False


class FileRouter:
    """Scans a pages directory and builds a route table.

    Args:
        pages_dir: Root directory to scan for page templates.
        template_dirs: Template search directories (for relative path computation).
    """

    def __init__(self, pages_dir: Path, template_dirs: list[Path]) -> None:
        self._pages_dir = pages_dir.resolve()
        self._template_dirs = [d.resolve() for d in template_dirs]
        self._routes: list[RouteEntry] = []

    def scan(self) -> list[RouteEntry]:
        """Walk pages_dir, build and return sorted route table."""
        self._routes = []

        if not self._pages_dir.exists():
            logger.warning("pages_dir does not exist: %s", self._pages_dir)
            return []

        # Collect .jinja page templates
        for path in sorted(self._pages_dir.rglob("*.jinja")):
            if path.name in _SPECIAL_FILES:
                continue
            if path.name.startswith("_"):
                continue
            # Skip files inside @parallel route directories
            if any(
                part.startswith("@") for part in path.relative_to(self._pages_dir).parts
            ):
                continue
            entry = self._build_route(path, is_api=False)
            if entry:
                self._routes.append(entry)

        # Collect .py API routes
        for path in sorted(self._pages_dir.rglob("*.py")):
            if path.name.startswith("_"):
                continue
            entry = self._build_route(path, is_api=True)
            if entry:
                self._routes.append(entry)

        self._routes = _sort_routes(self._routes)
        return list(self._routes)

    def register(self, pjx: PJX) -> None:
        """Register all discovered routes on the PJX/FastAPI app."""
        for entry in self._routes:
            if entry.is_api:
                self._register_api_route(pjx, entry)
            else:
                self._register_page_route(pjx, entry)

    def _build_route(self, path: Path, *, is_api: bool) -> RouteEntry | None:
        """Build a RouteEntry from a file path."""
        rel = path.resolve().relative_to(self._pages_dir)
        url = _path_to_url(rel, is_api=is_api)

        # Compute template path relative to template_dirs
        template = ""
        if not is_api:
            template = self._relative_template(path)

        # Find colocated handler (.py with same stem)
        handler_path: Path | None = None
        if is_api:
            handler_path = path
        else:
            py_file = path.with_suffix(".py")
            if py_file.exists():
                handler_path = py_file

        # Resolve layout chain, loading, error, not-found
        layout_chain = self._find_layout_chain(path.parent)
        loading = self._find_special(path.parent, "loading.jinja")
        error = self._find_special(path.parent, "error.jinja")
        not_found = self._find_special(path.parent, "not-found.jinja")

        # Detect parallel route slots (@folder/page.jinja)
        parallel_slots = self._find_parallel_slots(path.parent)

        # Determine methods from handler
        methods: tuple[str, ...] = ("GET",)
        if handler_path and not is_api:
            handler_obj = _load_handler_object(handler_path)
            if handler_obj is not None and hasattr(handler_obj, "methods"):
                methods = tuple(handler_obj.methods)

        return RouteEntry(
            url_pattern=url,
            template=template,
            handler_path=handler_path,
            layout_chain=layout_chain,
            loading=loading,
            error=error,
            not_found=not_found,
            parallel_slots=parallel_slots if parallel_slots else None,
            methods=methods,
            is_api=is_api,
        )

    def _relative_template(self, path: Path) -> str:
        """Compute template path relative to template_dirs."""
        resolved = path.resolve()
        for tpl_dir in self._template_dirs:
            try:
                return str(resolved.relative_to(tpl_dir))
            except ValueError:
                continue
        # Fallback: relative to pages_dir parent
        return str(resolved.relative_to(self._pages_dir.parent))

    def _find_layout_chain(self, directory: Path) -> tuple[str, ...]:
        """Walk from directory up to pages_dir, collecting layout.jinja files."""
        layouts: list[str] = []
        current = directory.resolve()
        pages = self._pages_dir

        while True:
            layout = current / "layout.jinja"
            if layout.exists():
                layouts.append(self._relative_template(layout))
            if current == pages:
                break
            parent = current.parent
            if parent == current:
                break
            current = parent

        # Root first, innermost last
        layouts.reverse()
        return tuple(layouts)

    def _find_special(self, directory: Path, filename: str) -> str | None:
        """Find nearest special file (loading.jinja, error.jinja) walking up."""
        current = directory.resolve()
        pages = self._pages_dir

        while True:
            candidate = current / filename
            if candidate.exists():
                return self._relative_template(candidate)
            if current == pages:
                break
            parent = current.parent
            if parent == current:
                break
            current = parent

        return None

    def _find_parallel_slots(self, directory: Path) -> dict[str, str]:
        """Find @folder parallel route slots in a directory.

        Parallel routes use ``@name/page.jinja`` convention. Each
        ``@folder`` renders independently into a named slot.

        Returns:
            Dict mapping slot name to template path.
        """
        slots: dict[str, str] = {}
        resolved = directory.resolve()
        if not resolved.is_dir():
            return slots
        for child in resolved.iterdir():
            if child.is_dir():
                m = _PARALLEL_RE.match(child.name)
                if m:
                    slot_name = m.group(1)
                    page = child / "page.jinja"
                    if page.exists():
                        slots[slot_name] = self._relative_template(page)
        return slots

    def _register_page_route(self, pjx: PJX, entry: RouteEntry) -> None:
        """Register a page route on the PJX app."""
        # Determine layout — use innermost layout from chain
        layout = entry.layout_chain[-1] if entry.layout_chain else pjx.layout

        # Load handler if colocated
        handler_fn = (
            _load_handler_fn(entry.handler_path) if entry.handler_path else None
        )

        template = entry.template
        methods = list(entry.methods)

        # Discover middleware from template frontmatter
        tpl_middleware: list[str] = list(entry.middleware)
        if not tpl_middleware:
            try:
                from pjx.parser import parse_file as _parse

                tpl_path = pjx.pipeline.find_template(template)
                component = _parse(tpl_path)
                for mw_decl in component.middleware:
                    tpl_middleware.extend(mw_decl.names)
            except FileNotFoundError:
                pass

        async def page_wrapper(request: Request, **path_params: Any) -> HTMLResponse:
            # Enforce middleware from template frontmatter
            for mw_name in tpl_middleware:
                mw_func = pjx._middleware_registry.get(mw_name)
                if mw_func is not None:
                    await mw_func(request)

            context: dict[str, Any] = dict(path_params)
            context["request"] = request
            if handler_fn is not None:
                import inspect

                if inspect.iscoroutinefunction(handler_fn):
                    result = await handler_fn(request=request, **path_params)
                else:
                    result = handler_fn(request=request, **path_params)
                if isinstance(result, dict):
                    context.update(result)
            html = pjx.render(template, context, layout=layout)
            return HTMLResponse(html)

        page_wrapper.__name__ = Path(entry.template).stem
        pjx.app.add_api_route(entry.url_pattern, page_wrapper, methods=methods)
        logger.info("route  %s → %s", entry.url_pattern, entry.template)

        # Register server action routes from colocated handler
        handler_obj = (
            _load_handler_object(entry.handler_path) if entry.handler_path else None
        )
        if handler_obj is not None and hasattr(handler_obj, "_actions"):
            _register_action_routes(pjx, handler_obj._actions)

    def _register_api_route(self, pjx: PJX, entry: RouteEntry) -> None:
        """Register an API route from a .py file."""
        if entry.handler_path is None:
            return

        route_obj = _load_route_object(entry.handler_path)
        if route_obj is None:
            return

        for method, fn in route_obj._handlers.items():

            async def api_wrapper(
                request: Request,
                _fn: Callable = fn,
                **path_params: Any,
            ) -> JSONResponse:
                import inspect

                if inspect.iscoroutinefunction(_fn):
                    result = await _fn(request=request, **path_params)
                else:
                    result = _fn(request=request, **path_params)
                return JSONResponse(result)

            api_wrapper.__name__ = f"{Path(entry.handler_path).stem}_{method.lower()}"
            pjx.app.add_api_route(entry.url_pattern, api_wrapper, methods=[method])
            logger.info(
                "api    %s %s → %s", method, entry.url_pattern, entry.handler_path
            )


# ---------------------------------------------------------------------------
# URL conversion
# ---------------------------------------------------------------------------


def _path_to_url(rel: Path, *, is_api: bool) -> str:
    """Convert a relative file path to a URL pattern.

    Examples:
        index.jinja → /
        about.jinja → /about
        blog/index.jinja → /blog
        blog/[slug].jinja → /blog/{slug}
        blog/[...slug].jinja → /blog/{slug:path}
        (auth)/login.jinja → /login
        api/users.py → /api/users
    """
    parts: list[str] = []
    # Process directory parts
    for part in rel.parts[:-1]:
        segment = _convert_segment(part)
        if segment is not None:
            parts.append(segment)

    # Process filename (strip extension)
    stem = rel.stem
    if stem != "index":
        segment = _convert_segment(stem)
        if segment is not None:
            parts.append(segment)

    url = "/" + "/".join(parts)
    return url


def _convert_segment(segment: str) -> str | None:
    """Convert a single path segment to URL segment.

    Returns None for route groups (stripped from URL).
    """
    # Route group: (name) → stripped
    if _GROUP_RE.match(segment):
        return None

    # Catch-all: [...param] → {param:path}
    m = _CATCH_ALL_RE.match(segment)
    if m:
        return f"{{{m.group(1)}:path}}"

    # Dynamic: [param] → {param}
    m = _DYNAMIC_RE.match(segment)
    if m:
        return f"{{{m.group(1)}}}"

    # Static segment
    return segment


# ---------------------------------------------------------------------------
# Route sorting
# ---------------------------------------------------------------------------


def _route_sort_key(entry: RouteEntry) -> tuple[int, int, str]:
    """Sort key: static before dynamic, specific before catch-all."""
    url = entry.url_pattern
    # Count dynamic segments
    dynamic_count = url.count("{")
    # Catch-all gets highest priority number (sorted last)
    has_catch_all = 1 if ":path}" in url else 0
    return (has_catch_all, dynamic_count, url)


def _sort_routes(routes: list[RouteEntry]) -> list[RouteEntry]:
    """Sort routes: static first, then dynamic, catch-all last."""
    return sorted(routes, key=_route_sort_key)


# ---------------------------------------------------------------------------
# Handler loading
# ---------------------------------------------------------------------------


def _load_module(path: Path) -> Any:
    """Dynamically import a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _load_handler_object(path: Path) -> Any:
    """Load the `handler` object from a colocated .py file."""
    try:
        module = _load_module(path)
        return getattr(module, "handler", None)
    except Exception:
        logger.warning("failed to load handler: %s", path, exc_info=True)
        return None


def _load_handler_fn(path: Path) -> Callable | None:
    """Load the handler function from a colocated .py file.

    Looks for ``handler.get``, ``handler.post``, or a bare ``handler`` callable.
    """
    obj = _load_handler_object(path)
    if obj is None:
        return None
    # RouteHandler with _handlers dict
    if hasattr(obj, "_handlers"):
        # Return the first available handler function
        for fn in obj._handlers.values():
            return fn
    # Bare callable
    if callable(obj):
        return obj
    return None


def _load_route_object(path: Path) -> Any:
    """Load the `route` object from an API .py file."""
    try:
        module = _load_module(path)
        return getattr(module, "route", None)
    except Exception:
        logger.warning("failed to load API route: %s", path, exc_info=True)
        return None


def _register_action_routes(pjx: PJX, actions: dict[str, Callable]) -> None:
    """Register server action handlers as POST routes.

    Each action ``name`` is mounted at ``/_pjx/actions/{name}`` as a POST
    endpoint.  The handler receives the ``Request`` and returns an
    ``HTMLResponse`` (for HTMX swap) or a ``JSONResponse``.
    """
    import inspect

    for action_name, fn in actions.items():
        action_path = f"/_pjx/actions/{action_name}"

        async def action_wrapper(
            request: Request,
            _fn: Callable = fn,
        ) -> HTMLResponse:
            if inspect.iscoroutinefunction(_fn):
                result = await _fn(request=request)
            else:
                result = _fn(request=request)
            if isinstance(result, str):
                return HTMLResponse(result)
            if isinstance(result, dict):
                return JSONResponse(result)  # ty: ignore[invalid-return-type]
            return HTMLResponse(str(result))

        action_wrapper.__name__ = f"action_{action_name}"
        pjx.app.add_api_route(
            action_path, action_wrapper, methods=["POST"], response_model=None
        )
        logger.info("action %s → %s", action_path, action_name)
