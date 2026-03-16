"""Compiler: transforms PjxFile AST to Jinja2 source.

Design notes
------------
* Simple-mode files compile to a flat Jinja2 template with an optional
  preamble (state, prop defaults, let bindings) followed by the body.
* Multi-component files (containing @component blocks) compile to a set of
  Jinja2 macros — one per @component.
* Named slots are captured via ``{% set __slot_name %}...{% endset %}``
  and passed as keyword arguments to local macros or as a dict to the
  ``__pjx_render_component()`` Jinja2 global for imported templates.
* HTMX shorthand attributes (``@event.htmx``, ``@swap``, etc.) are
  lowered to ``hx-*`` attributes at compile time.
* Alpine bindings (``@event.alpine``) and dynamic bindings (``:attr``)
  are preserved as-is with ``{{ }}`` expression wrapping where needed.
* ``{{ @id }}``, ``{{ @state }}``, ``{{ @has_slot('x') }}``, and
  ``{{ @event_url(...) }}`` helpers are substituted to Jinja2 globals.
"""

from __future__ import annotations

import json
import re
from pathlib import PurePosixPath
from typing import Any

from .ast import (
    Attribute,
    ComponentCall,
    ComponentDef,
    ExprNode,
    ForNode,
    FromImport,
    HtmlElement,
    ImportDirective,
    LetDirective,
    NamedSlotContent,
    PjxFile,
    PropsBlock,
    ShowNode,
    SlotNode,
    StateBlock,
    SwitchNode,
    TextNode,
)
from .exceptions import CompileError


# ── @-helper regex ─────────────────────────────────────────────────────────────

_RE_HELPER = re.compile(
    r"\{\{\s*@(id|state|has_slot\([^)]*\)|event_url\([^)]*\))\s*\}\}"
)
# Bare form — for use inside Jinja2 control expressions ({% if @has_slot('x') %})
_RE_HELPER_BARE = re.compile(r"@(id|state|has_slot\([^)]*\)|event_url\([^)]*\))")

# ── Attribute classification regexes ──────────────────────────────────────────

_RE_HTMX_EVENT = re.compile(r"^@([\w-]+)\.htmx$")
_RE_HTMX_MOD = re.compile(
    r"^@(swap|target|confirm|indicator|push-url|push_url|select|vals|trigger)$"
)
_RE_ALPINE_EVENT = re.compile(r"^@([\w:.-]+)\.alpine$")


# ── Public API ─────────────────────────────────────────────────────────────────


def compile_pjx(ast: PjxFile, filename: str = "<string>") -> str:
    """Compile a *PjxFile* AST to a Jinja2 template string."""
    return Compiler(ast, filename).emit()


# ── Compiler ──────────────────────────────────────────────────────────────────


class Compiler:
    def __init__(self, ast: PjxFile, filename: str = "<string>") -> None:
        self.ast = ast
        self.filename = filename
        self._local_components: set[str] = set()
        # name → (template_path, component_name_override | None)
        self._imported_components: dict[str, tuple[str, str | None]] = {}

        for imp in ast.imports:
            if isinstance(imp, ImportDirective):
                stem = PurePosixPath(imp.path).stem
                name = stem[0].upper() + stem[1:] if stem else stem
                self._imported_components[name] = (imp.path, None)
            elif isinstance(imp, FromImport):
                # @from a.b.c import Comp1, Comp2 → "a/b/c.pjx"
                tpl_path = imp.module.replace(".", "/") + ".pjx"
                for comp_name in imp.names:
                    self._imported_components[comp_name] = (tpl_path, comp_name)

        if ast.is_multi_component:
            self._local_components = {c.name for c in ast.components}

    # ── Top-level emit ────────────────────────────────────────────────────────

    def emit(self) -> str:
        if self.ast.is_multi_component:
            return "".join(self._emit_component_def(c) for c in self.ast.components)

        preamble = self._emit_preamble(
            state=self.ast.state,
            props=self.ast.props,
            lets=self.ast.lets,
        )
        body = self._emit_nodes(self.ast.body)
        return preamble + body

    # ── Preamble ──────────────────────────────────────────────────────────────

    def _emit_preamble(
        self,
        *,
        state: StateBlock | None,
        props: PropsBlock | None,
        lets: tuple[LetDirective, ...],
    ) -> str:
        out: list[str] = []

        if state:
            pairs = ", ".join(f"{json.dumps(f.name)}: {f.value}" for f in state.fields)
            out.append(f"{{% set __pjx_state = {{{pairs}}} %}}\n")

        if props:
            for p in props.props:
                if p.default_expr is not None:
                    out.append(
                        f"{{% if {p.name} is not defined %}}"
                        f"{{% set {p.name} = {p.default_expr} %}}"
                        f"{{% endif %}}\n"
                    )

        for let in lets:
            out.append(f"{{% set {let.name} = {let.expr} %}}\n")

        return "".join(out)

    # ── @component → Jinja2 macro ─────────────────────────────────────────────

    def _emit_component_def(self, comp: ComponentDef) -> str:
        params: list[str] = []

        if comp.props:
            for p in comp.props.props:
                if p.default_expr is not None:
                    params.append(f"{p.name}={p.default_expr}")
                else:
                    params.append(p.name)

        # Default slot is always available; named slots are declared explicitly.
        # Skip "default" in the loop since we always add it explicitly above.
        params.append("__slot_default=''")
        for s in comp.slots:
            if s.name != "default":
                params.append(f"__slot_{s.name}=''")

        sig = ", ".join(params)
        preamble = self._emit_preamble(state=comp.state, props=None, lets=comp.lets)
        body = self._emit_nodes(comp.children)

        return (
            f"{{% macro {comp.name}({sig}) %}}\n{preamble}{body}\n{{% endmacro %}}\n\n"
        )

    # ── Node dispatch ─────────────────────────────────────────────────────────

    def _emit_nodes(self, nodes: tuple[Any, ...] | list[Any]) -> str:
        return "".join(self._emit_node(n) for n in nodes)

    def _emit_node(self, node: Any) -> str:
        if isinstance(node, TextNode):
            return node.content
        if isinstance(node, ExprNode):
            return self._subst(node.content)
        if isinstance(node, HtmlElement):
            return self._emit_html(node)
        if isinstance(node, ComponentCall):
            return self._emit_call(node)
        if isinstance(node, SlotNode):
            return self._emit_slot(node)
        if isinstance(node, ShowNode):
            return self._emit_show(node)
        if isinstance(node, ForNode):
            return self._emit_for(node)
        if isinstance(node, SwitchNode):
            return self._emit_switch(node)
        if isinstance(node, NamedSlotContent):
            return ""  # consumed by _emit_call; never reached at top level
        raise CompileError(
            f"Unexpected AST node type: {type(node).__name__}", file=self.filename
        )

    # ── HTML element ──────────────────────────────────────────────────────────

    def _emit_html(self, node: HtmlElement) -> str:
        attrs = self._emit_attrs(node.attrs)
        if node.self_closing:
            return f"<{node.tag}{attrs} />"
        body = self._emit_nodes(node.children)
        return f"<{node.tag}{attrs}>{body}</{node.tag}>"

    def _emit_attrs(self, attrs: tuple[Attribute, ...]) -> str:
        out: list[str] = []
        htmx_trigger: str | None = None
        htmx_pending: list[str] = []

        for a in attrs:
            n, v = a.name, a.value

            # @event.htmx="method:/url" → hx-{method}="/url" + hx-trigger="{event}"
            m = _RE_HTMX_EVENT.match(n)
            if m:
                if v:
                    method, _, url = v.partition(":")
                    htmx_pending.append(f' hx-{method.lower()}="{self._subst(url)}"')
                    htmx_trigger = m.group(1)
                continue  # always skip, even if no value

            # @swap, @target, @confirm, etc.
            m = _RE_HTMX_MOD.match(n)
            if m:
                key = m.group(1).replace("_", "-")
                htmx_pending.append(f' hx-{key}="{self._subst(v or "")}"')
                continue

            # @event.alpine="..." → @event="..."
            m = _RE_ALPINE_EVENT.match(n)
            if m:
                out.append(f' @{m.group(1)}="{self._subst(v or "")}"')
                continue

            # :attr="expr" → attr="{{ expr }}"
            if n.startswith(":") and len(n) > 1:
                out.append(f' {n[1:]}="{self._to_jinja_expr(v)}"')
                continue

            # Boolean attribute
            if v is None:
                out.append(f" {n}")
                continue

            # Regular attribute (static string, possibly with {{ }} interpolation)
            out.append(f' {n}="{self._subst(v)}"')

        if htmx_trigger:
            out.append(f' hx-trigger="{htmx_trigger}"')
        out.extend(htmx_pending)
        return "".join(out)

    def _to_jinja_expr(self, raw: str | None) -> str:
        """Wrap a binding value as a Jinja2 interpolation if not already one."""
        if not raw:
            return ""
        raw = raw.strip()
        if raw.startswith("{{") and raw.endswith("}}"):
            return self._subst(raw)
        return "{{ " + self._subst(raw) + " }}"

    # ── Component call ────────────────────────────────────────────────────────

    def _emit_call(self, node: ComponentCall) -> str:
        out: list[str] = []
        slot_vars: list[tuple[str, str]] = []  # (slot_name, jinja_var)

        # Capture default slot content
        if node.children:
            out.append("{% set __slot_default %}")
            out.append(self._emit_nodes(node.children))
            out.append("{% endset %}")
            slot_vars.append(("default", "__slot_default"))

        # Capture named slot content
        for sname, schildren in node.named_slots.items():
            var = f"__slot_{sname}"
            out.append(f"{{% set {var} %}}")
            out.append(self._emit_nodes(schildren))
            out.append("{% endset %}")
            slot_vars.append((sname, var))

        if node.name in self._local_components:
            args = [self._attr_as_arg(a) for a in node.attrs]
            args += [f"__slot_{sn}={sv}" for sn, sv in slot_vars]
            out.append(f"{{{{ {node.name}({', '.join(args)}) }}}}")
        else:
            entry = self._imported_components.get(node.name)
            if entry is None:
                raise CompileError(
                    f"Unknown component <{node.name}>; add @import or define @component {node.name}",
                    file=self.filename,
                    line=node.line,
                )
            tpl, comp_override = entry
            props_expr = (
                "{"
                + ", ".join(
                    f"{json.dumps(a.name.lstrip(':'))}: {self._attr_val_as_expr(a.value)}"
                    for a in node.attrs
                )
                + "}"
            )
            slots_expr = (
                "{" + ", ".join(f"{json.dumps(sn)}: {sv}" for sn, sv in slot_vars) + "}"
            )
            if comp_override:
                out.append(
                    f"{{{{ __pjx_render_component({tpl!r}, {props_expr}, {slots_expr}, {comp_override!r}) }}}}"
                )
            else:
                out.append(
                    f"{{{{ __pjx_render_component({tpl!r}, {props_expr}, {slots_expr}) }}}}"
                )

        return "".join(out)

    def _attr_as_arg(self, attr: Attribute) -> str:
        name = attr.name.lstrip(":")
        return f"{name}={self._attr_val_as_expr(attr.value)}"

    _INTERP_RE = re.compile(r"\{\{(.+?)\}\}")

    def _attr_val_as_expr(self, raw: str | None) -> str:
        """Return a bare Jinja2 expression string for a prop value in a macro call."""
        if raw is None:
            return "True"
        raw = self._subst(raw)
        if raw.startswith("{{") and raw.endswith("}}") and raw.count("{{") == 1:
            return raw[2:-2].strip()
        if "{{" in raw:
            parts: list[str] = []
            last = 0
            for m in self._INTERP_RE.finditer(raw):
                before = raw[last : m.start()]
                if before:
                    parts.append(json.dumps(before))
                parts.append(f"({m.group(1).strip()})")
                last = m.end()
            after = raw[last:]
            if after:
                parts.append(json.dumps(after))
            return " ~ ".join(parts) if parts else json.dumps(raw)
        return json.dumps(raw)

    # ── Slot output ───────────────────────────────────────────────────────────

    def _emit_slot(self, node: SlotNode) -> str:
        v = f"__slot_{node.name}"
        if node.fallback:
            return (
                f"{{% if {v} %}}"
                f"{{{{ {v} | safe }}}}"
                "{% else %}" + self._emit_nodes(node.fallback) + "{% endif %}"
            )
        return f"{{{{ {v} | safe }}}}"

    # ── Control structures ────────────────────────────────────────────────────

    def _emit_show(self, node: ShowNode) -> str:
        cond = self._subst_cond(node.condition)
        out = [f"{{% if {cond} %}}", self._emit_nodes(node.children)]
        if node.fallback:
            out += ["{% else %}", self._emit_nodes(node.fallback)]
        out.append("{% endif %}")
        return "".join(out)

    def _emit_for(self, node: ForNode) -> str:
        iterable = self._subst_cond(node.iterable)
        out = [f"{{% for {node.variable} in {iterable} %}}"]
        if node.index_var:
            out.append(f"{{% set {node.index_var} = loop.index0 %}}")
        out.append(self._emit_nodes(node.children))
        if node.empty:
            out += ["{% else %}", self._emit_nodes(node.empty)]
        out.append("{% endfor %}")
        return "".join(out)

    def _emit_switch(self, node: SwitchNode) -> str:
        if not node.cases and not node.fallback:
            return ""
        expr = self._subst_cond(node.expression)
        out: list[str] = []
        for i, case in enumerate(node.cases):
            kw = "if" if i == 0 else "elif"
            val = self._case_val(case.value)
            out.append(f"{{% {kw} {expr} == {val} %}}")
            out.append(self._emit_nodes(case.children))
        if node.fallback:
            out += ["{% else %}", self._emit_nodes(node.fallback)]
        out.append("{% endif %}")
        return "".join(out)

    def _case_val(self, v: str) -> str:
        """Return a Jinja2 literal for a <Match value="..."> attribute."""
        v = v.strip()
        # Explicit Jinja2 expression — unwrap
        if v.startswith("{{") and v.endswith("}}"):
            return v[2:-2].strip()
        # Numeric literal
        if re.match(r"^-?\d+(\.\d+)?$", v):
            return v
        # Everything else is a string literal
        return json.dumps(v)

    # ── @-helper substitution ─────────────────────────────────────────────────

    def _subst(self, s: str) -> str:
        """Replace ``{{ @helper }}`` patterns with their Jinja2 equivalents."""
        return _RE_HELPER.sub(_replace_helper, s)

    def _subst_cond(self, s: str) -> str:
        """Replace bare ``@helper`` patterns in control-flow expressions."""
        return _RE_HELPER_BARE.sub(_replace_helper_bare, s)


# ── Module-level helpers ───────────────────────────────────────────────────────


def _replace_helper(m: re.Match) -> str:  # type: ignore[type-arg]
    """Replaces ``{{ @helper }}`` — for use in text/attribute contexts."""
    expr = m.group(1)
    if expr == "id":
        return "{{ __pjx_id }}"
    if expr == "state":
        return "{{ __pjx_state | tojson }}"
    hs = re.match(r"has_slot\(['\"]?([\w-]+)['\"]?\)", expr)
    if hs:
        return f"{{{{ __slot_{hs.group(1)} }}}}"
    eu = re.match(r"event_url\((.+)\)", expr)
    if eu:
        return f"{{{{ __pjx_event_url({eu.group(1)}) }}}}"
    return m.group(0)


def _replace_helper_bare(m: re.Match) -> str:  # type: ignore[type-arg]
    """Replaces bare ``@helper`` — for use inside {% if %} / {% for %} expressions."""
    expr = m.group(1)
    if expr == "id":
        return "__pjx_id"
    if expr == "state":
        return "__pjx_state"
    hs = re.match(r"has_slot\(['\"]?([\w-]+)['\"]?\)", expr)
    if hs:
        return f"__slot_{hs.group(1)}"
    eu = re.match(r"event_url\((.+)\)", expr)
    if eu:
        return f"__pjx_event_url({eu.group(1)})"
    return m.group(0)
