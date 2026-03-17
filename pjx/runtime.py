"""Runtime: Jinja2 environment, template compilation cache, and render helpers.

The runtime is the bridge between `.pjx` files and Jinja2.  It:

* Parses and compiles `.pjx` files into Jinja2 template strings (once, cached
  by file mtime).
* Sets up the Jinja2 ``Environment`` with the PJX globals:
  ``__pjx_render_component``, ``__pjx_event_url``.
* Injects ``__pjx_id`` (a fresh UUID) at each render so each rendered
  component instance gets a unique identifier.
* Handles partial (fragment) rendering for HTMX responses.
* Validates required props and evaluates default expressions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Optional, Union, cast, get_args, get_origin

from jinja2 import Environment, StrictUndefined, pass_context
from markupsafe import Markup

from .ast import ImportDirective, PjxFile
from .compiler import compile_pjx
from .exceptions import PropValidationError
from .parser import parse

# Lazy import to avoid circular dependency
_bundle_resolver = None


# ── Type-checking helpers ──────────────────────────────────────────────────────

SAFE_TYPE_GLOBALS: dict[str, Any] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "Literal": Literal,
    "Optional": Optional,
    "None": None,
}


# ── Component metadata (light replacement for old CompiledComponent) ──────────


@dataclass(slots=True)
class _PropSpec:
    name: str
    type_expr: str | None
    default_expr: str | None


@dataclass(slots=True)
class ComponentMeta:
    """Metadata extracted from a compiled .pjx AST.

    Kept intentionally thin — only what ``Catalog.get_signature()`` and
    prop validation need.  The heavy lifting (template compilation, caching)
    is handled by the ``Runtime``.
    """

    component_name: str
    prop_specs: tuple[_PropSpec, ...]
    slot_specs: dict[str, Any]  # slot_name → True  (for compatibility)
    assets: tuple[Any, ...]  # always empty in this implementation
    path: str
    component_imports: dict[str, str]  # component_name → template_path
    is_multi_component: bool = False
    components_meta: dict[str, "ComponentMeta"] = field(default_factory=dict)


@dataclass(slots=True)
class ComponentInstance:
    component: ComponentMeta
    template: Any  # jinja2.Template
    source_mtime_ns: int


# ── Runtime ───────────────────────────────────────────────────────────────────


class Runtime:
    def __init__(self, catalog: Any) -> None:
        self.catalog = catalog
        self.environment = Environment(
            autoescape=True,
            trim_blocks=False,
            lstrip_blocks=False,
            undefined=StrictUndefined,
        )
        globals_map = cast(dict[str, Any], self.environment.globals)
        globals_map["__pjx_render_component"] = self._render_component
        globals_map["__pjx_event_url"] = _event_url
        globals_map["pjx_assets"] = self._pjx_assets
        self._template_cache: dict[str, ComponentInstance] = {}
        self._expr_cache: dict[str, Any] = {}
        self._bundle_resolver: Any = None

    def _pjx_assets(self) -> Markup:
        tags: list[str] = []
        for asset in self.catalog.base_assets:
            if asset.kind == "css":
                tags.append(f'<link rel="stylesheet" href="{asset.path}" />')
            elif asset.kind == "js":
                tags.append(f'<script src="{asset.path}"></script>')
            elif asset.kind == "js-defer":
                tags.append(f'<script src="{asset.path}" defer></script>')
        return Markup("\n    ".join(tags))

    # ── Template loading ───────────────────────────────────────────────────

    def get_component_instance(self, template_path: str) -> ComponentInstance:
        source_path = self.catalog.resolve_path(template_path)
        cache_key = str(source_path)
        source_mtime_ns = source_path.stat().st_mtime_ns
        cached = self._template_cache.get(cache_key)
        if cached is not None and (
            not self.catalog.auto_reload or cached.source_mtime_ns == source_mtime_ns
        ):
            return cached

        source = source_path.read_text(encoding="utf-8")
        ast = parse(source, filename=str(source_path))

        # Bundle mode: inline all imported component macros for page templates
        if (
            getattr(self.catalog, "bundle", False)
            and not ast.is_multi_component
            and ast.imports
        ):
            jinja_source = self._compile_bundled(ast, str(source_path))
        else:
            jinja_source = compile_pjx(ast, filename=str(source_path))

        template = self.environment.from_string(jinja_source)
        meta = _extract_meta(ast, str(source_path))
        instance = ComponentInstance(
            component=meta,
            template=template,
            source_mtime_ns=source_mtime_ns,
        )
        self._template_cache[cache_key] = instance
        return instance

    def _compile_bundled(self, ast: PjxFile, filename: str) -> str:
        """Compile a page template with all imported macros inlined."""
        from .compile import _ImportResolver, _compile_bundled

        if self._bundle_resolver is None:
            self._bundle_resolver = _ImportResolver(self.catalog)
        jinja_source, _ = _compile_bundled(ast, filename, self._bundle_resolver)
        return jinja_source

    def evaluate_expr(self, expr: str, context: dict[str, Any]) -> Any:
        compiled = self._expr_cache.get(expr)
        if compiled is None:
            compiled = self.environment.compile_expression(expr)
            self._expr_cache[expr] = compiled
        return compiled(**context)

    # ── Rendering ─────────────────────────────────────────────────────────

    def render_root(
        self,
        template_path: str,
        context: dict[str, Any],
        *,
        request: Any = None,
        partial: bool = False,
        target: str | None = None,
    ) -> str:
        instance = self.get_component_instance(template_path)
        ctx = dict(context)
        ctx.setdefault("request", request)
        ctx["__pjx_id"] = str(uuid.uuid4())
        self._inject_props(instance, ctx)
        html_output = instance.template.render(**ctx)
        if partial and target:
            return extract_fragment_by_id(html_output, target)
        return html_output

    def _inject_props(self, instance: ComponentInstance, ctx: dict[str, Any]) -> None:
        for spec in instance.component.prop_specs:
            if spec.name in ctx:
                if spec.type_expr and not _matches_type(spec.type_expr, ctx[spec.name]):
                    raise PropValidationError(
                        f"{instance.component.component_name}.{spec.name}: "
                        f"expected {spec.type_expr}, got {type(ctx[spec.name]).__name__}"
                    )
            elif spec.default_expr is not None:
                ctx[spec.name] = self.evaluate_expr(spec.default_expr, ctx)
            else:
                raise PropValidationError(
                    f"{instance.component.component_name}: "
                    f"missing required prop {spec.name!r}"
                )

    @pass_context
    def _render_component(
        self,
        jinja_ctx: Any,
        template_path: str,
        props: dict[str, Any],
        slots: dict[str, Any],
        component_name: str = "",
    ) -> Markup:
        """Jinja2 global ``__pjx_render_component`` — renders an imported component.

        ``component_name`` is set by ``@from mod import Name`` calls so the
        correct macro is invoked from a multi-component file.
        """
        instance = self.get_component_instance(template_path)
        ctx: dict[str, Any] = dict(jinja_ctx.get_all())
        ctx.update(props)
        ctx["__pjx_id"] = str(uuid.uuid4())
        for slot_name, slot_content in slots.items():
            ctx[f"__slot_{slot_name}"] = slot_content

        if instance.component.is_multi_component:
            # Multi-component file: call the named macro from the template module
            macro_name = component_name or instance.component.component_name
            macro = getattr(instance.template.module, macro_name, None)
            if macro is None:
                raise ValueError(
                    f"No macro '{macro_name}' found in {template_path!r}. "
                    "Check that the component name matches the file stem."
                )
            # Only pass slot variables (macros handle own prop defaults)
            kwargs: dict[str, Any] = dict(props)
            kwargs.update({f"__slot_{sn}": sv for sn, sv in slots.items()})
            return Markup(str(macro(**kwargs)))
        else:
            self._inject_props(instance, ctx)
            return Markup(instance.template.render(**ctx))


# ── Jinja2 global helpers ──────────────────────────────────────────────────────


def _event_url(event: str, **params: Any) -> str:
    """Generate a URL for a server-side component event.

    This default implementation produces ``/__pjx_event/{event}``.
    Override via context processor or replace the Jinja2 global entirely.
    """
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"/__pjx_event/{event}?{qs}"
    return f"/__pjx_event/{event}"


# ── Metadata extraction ────────────────────────────────────────────────────────


def _extract_meta(ast: PjxFile, path: str) -> ComponentMeta:
    stem = Path(path).stem
    name = stem[0].upper() + stem[1:] if stem else "Component"

    imports: dict[str, str] = {}
    for imp in ast.imports:
        if isinstance(imp, ImportDirective):
            imp_stem = PurePosixPath(imp.path).stem
            cname = imp_stem[0].upper() + imp_stem[1:] if imp_stem else imp_stem
            imports[cname] = imp.path

    # In multi-component mode extract all components; first is the default
    if ast.is_multi_component and ast.components:
        comp0 = ast.components[0]
        name = comp0.name
        prop_specs: tuple[_PropSpec, ...] = ()
        if comp0.props:
            prop_specs = tuple(
                _PropSpec(
                    name=p.name, type_expr=p.type_expr, default_expr=p.default_expr
                )
                for p in comp0.props.props
            )
        slot_specs: dict[str, Any] = {s.name: True for s in comp0.slots}

        components_meta: dict[str, ComponentMeta] = {}
        for comp in ast.components:
            c_prop_specs: tuple[_PropSpec, ...] = ()
            if comp.props:
                c_prop_specs = tuple(
                    _PropSpec(
                        name=p.name, type_expr=p.type_expr, default_expr=p.default_expr
                    )
                    for p in comp.props.props
                )
            c_slot_specs: dict[str, Any] = {s.name: True for s in comp.slots}
            components_meta[comp.name] = ComponentMeta(
                component_name=comp.name,
                prop_specs=c_prop_specs,
                slot_specs=c_slot_specs,
                assets=(),
                path=path,
                component_imports=imports,
                is_multi_component=True,
            )
    else:
        prop_specs = ()
        if ast.props:
            prop_specs = tuple(
                _PropSpec(
                    name=p.name, type_expr=p.type_expr, default_expr=p.default_expr
                )
                for p in ast.props.props
            )
        slot_specs = {s.name: True for s in ast.slots}
        components_meta = {}

    return ComponentMeta(
        component_name=name,
        prop_specs=prop_specs,
        slot_specs=slot_specs,
        assets=(),
        path=path,
        component_imports=imports,
        is_multi_component=ast.is_multi_component,
        components_meta=components_meta,
    )


# ── Fragment extraction ────────────────────────────────────────────────────────


def extract_fragment_by_id(html_source: str, target_id: str) -> str:
    marker = f'id="{target_id}"'
    start = html_source.find(marker)
    if start == -1:
        marker = f"id='{target_id}'"
        start = html_source.find(marker)
    if start == -1:
        raise ValueError(f"Could not find fragment with id {target_id!r}")

    open_start = html_source.rfind("<", 0, start)
    if open_start == -1:
        raise ValueError(f"Invalid HTML around fragment {target_id!r}")
    open_end = html_source.find(">", start)
    if open_end == -1:
        raise ValueError(f"Unclosed tag for fragment {target_id!r}")
    tag_name = _tag_name_from_open_tag(html_source[open_start : open_end + 1])
    cursor = open_end + 1
    depth = 1
    _BOUNDARY = frozenset({">", " ", "/", "\t", "\n"})

    while cursor < len(html_source):
        # Find next opening tag with boundary check
        next_open = -1
        search_from = cursor
        while True:
            pos = html_source.find(f"<{tag_name}", search_from)
            if pos == -1:
                break
            char_after = html_source[pos + 1 + len(tag_name) : pos + 2 + len(tag_name)]
            if char_after == "" or char_after in _BOUNDARY:
                next_open = pos
                break
            search_from = pos + 1

        # Find next closing tag with boundary check
        next_close = -1
        search_from = cursor
        close_token = f"</{tag_name}"
        while True:
            pos = html_source.find(close_token, search_from)
            if pos == -1:
                break
            char_after = html_source[
                pos + len(close_token) : pos + len(close_token) + 1
            ]
            if char_after == "" or char_after in _BOUNDARY:
                next_close = pos
                break
            search_from = pos + 1

        if next_close == -1:
            raise ValueError(f"Unclosed fragment tag {tag_name!r}")
        if next_open != -1 and next_open < next_close:
            depth += 1
            cursor = next_open + 1
            continue
        depth -= 1
        cursor = next_close + len(tag_name) + 3
        if depth == 0:
            return html_source[open_start:cursor]
    raise ValueError(f"Could not extract fragment {target_id!r}")


def _tag_name_from_open_tag(tag: str) -> str:
    body = tag[1:].split(None, 1)[0]
    return body.rstrip(">")


# ── Type validation ────────────────────────────────────────────────────────────


def _matches_type(type_expr: str, value: Any) -> bool:
    try:
        annotation = eval(type_expr, {"__builtins__": {}}, SAFE_TYPE_GLOBALS)  # noqa: S307
    except Exception:
        return True
    return _matches_annotation(annotation, value)


def _matches_annotation(annotation: Any, value: Any) -> bool:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is None:
        if annotation is Any:
            return True
        if annotation is None:
            return value is None
        return isinstance(value, annotation)
    if origin is Literal:
        return value in args
    if origin is list:
        return isinstance(value, list)
    if origin is dict:
        return isinstance(value, dict)
    if origin in (Union, getattr(__import__("types"), "UnionType", object())):
        return any(_matches_annotation(arg, value) for arg in args)
    return True
