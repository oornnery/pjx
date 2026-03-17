"""MiniJinja runtime backend — drop-in alternative to the Jinja2-based Runtime.

Uses the ``minijinja`` Rust-based template engine for significantly faster
rendering while maintaining full compatibility with compiled PJX output.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Optional, Union, get_args, get_origin

from markupsafe import Markup

from .ast import ImportDirective, PjxFile
from .compiler import compile_pjx
from .exceptions import PropValidationError
from .parser import parse
from .runtime import (
    ComponentInstance,
    ComponentMeta,
    _PropSpec,
    _extract_meta,
    _event_url,
    _matches_type,
    extract_fragment_by_id,
    SAFE_TYPE_GLOBALS,
)

try:
    import minijinja
except ImportError as exc:
    raise ImportError(
        "minijinja is required for the MiniJinja backend. "
        "Install it with: pip install pjx[minijinja]"
    ) from exc


class MiniJinjaRuntime:
    """Runtime backed by minijinja (Rust) instead of Jinja2."""

    def __init__(self, catalog: Any) -> None:
        self.catalog = catalog
        self.env = minijinja.Environment()
        self.env.auto_escape_callback = lambda _: True
        self.env.keep_trailing_newline = True

        # Register globals as functions
        self.env.add_function("__pjx_event_url", _event_url)
        self.env.add_function("pjx_assets", self._pjx_assets)

        self._template_cache: dict[str, ComponentInstance] = {}
        self._compiled_sources: dict[str, str] = {}
        self._render_component_ctx: dict | None = None
        self._bundle_resolver: Any = None

    def _pjx_assets(self) -> str:
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

        # Bundle mode: inline all imported component macros
        if (
            getattr(self.catalog, "bundle", False)
            and not ast.is_multi_component
            and ast.imports
        ):
            jinja_source = self._compile_bundled(ast, str(source_path))
        else:
            jinja_source = compile_pjx(ast, filename=str(source_path))

        meta = _extract_meta(ast, str(source_path))

        # Register template in minijinja env
        self.env.add_template(cache_key, jinja_source)
        self._compiled_sources[cache_key] = jinja_source

        instance = ComponentInstance(
            component=meta,
            template=cache_key,  # store the key, not a template object
            source_mtime_ns=source_mtime_ns,
        )
        self._template_cache[cache_key] = instance
        return instance

    def _compile_bundled(self, ast: Any, filename: str) -> str:
        """Compile a page template with all imported macros inlined."""
        from .compile import _ImportResolver, _compile_bundled

        if self._bundle_resolver is None:
            self._bundle_resolver = _ImportResolver(self.catalog)
        jinja_source, _ = _compile_bundled(ast, filename, self._bundle_resolver)
        return jinja_source

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

        # Set up __pjx_render_component as a function in the context
        def render_component(template_path: str, props: dict, slots: dict, component_name: str = "") -> str:
            return str(self._render_component(template_path, props, slots, component_name, parent_ctx=ctx))

        ctx["__pjx_render_component"] = render_component

        template_key = instance.template
        html_output = self.env.render_template(template_key, **ctx)
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
                # Evaluate default using minijinja
                try:
                    result = self.env.eval_expr(spec.default_expr, **ctx)
                    ctx[spec.name] = result
                except Exception:
                    # Fallback: use Python eval for simple expressions
                    ctx[spec.name] = eval(spec.default_expr, {"__builtins__": {}}, SAFE_TYPE_GLOBALS)  # noqa: S307
            else:
                raise PropValidationError(
                    f"{instance.component.component_name}: "
                    f"missing required prop {spec.name!r}"
                )

    def _render_component(
        self,
        template_path: str,
        props: dict[str, Any],
        slots: dict[str, Any],
        component_name: str = "",
        parent_ctx: dict[str, Any] | None = None,
    ) -> Markup:
        instance = self.get_component_instance(template_path)
        ctx: dict[str, Any] = dict(parent_ctx or {})
        ctx.update(props)
        ctx["__pjx_id"] = str(uuid.uuid4())
        for slot_name, slot_content in slots.items():
            ctx[f"__slot_{slot_name}"] = slot_content

        # Recursive render_component for nested components
        def render_component(tp: str, p: dict, s: dict, cn: str = "") -> str:
            return str(self._render_component(tp, p, s, cn, parent_ctx=ctx))

        ctx["__pjx_render_component"] = render_component

        if instance.component.is_multi_component:
            macro_name = component_name or instance.component.component_name
            # For multi-component files, we render the full template and
            # call the macro via Jinja2 expression wrapping
            macro_source = self._compiled_sources.get(instance.template, "")
            call_args = ", ".join(
                f"{k}={_jinja_repr(v)}" for k, v in props.items()
            )
            for sn, sv in slots.items():
                call_args += f", __slot_{sn}={_jinja_repr(sv)}"
            call_template = f"{macro_source}\n{{{{ {macro_name}({call_args}) }}}}"
            temp_key = f"__call_{id(call_template)}"
            self.env.add_template(temp_key, call_template)
            try:
                result = self.env.render_template(temp_key, **ctx)
            finally:
                self.env.remove_template(temp_key)
            return Markup(result.strip())
        else:
            self._inject_props(instance, ctx)
            template_key = instance.template
            return Markup(self.env.render_template(template_key, **ctx))


def _jinja_repr(value: Any) -> str:
    """Convert a Python value to a Jinja2 literal for macro calls."""
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return "none"
    # Fallback — pass as string
    escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"
