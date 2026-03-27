"""PJX compiler — transforms a Component AST into Jinja2 + Alpine + HTMX output."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pjx.ast_nodes import (
    AwaitNode,
    CaseNode,
    CompiledComponent,
    Component,
    ComponentNode,
    ElementNode,
    ErrorBoundaryNode,
    ExprNode,
    ForNode,
    FragmentNode,
    Node,
    PortalNode,
    ScopedStyle,
    ShowNode,
    SlotPassNode,
    SlotRenderNode,
    SwitchNode,
    TeleportNode,
    TextNode,
    TransitionGroupNode,
    TransitionNode,
)
from pjx.css import generate_scope_hash, scope_css
from pjx.errors import CompileError
from pjx.layout import LAYOUT_COMPONENTS, LAYOUT_PREFIX, get_layout_props
from pjx.props import separate_attrs

if TYPE_CHECKING:
    from pjx.registry import ComponentRegistry


# ---------------------------------------------------------------------------
# Attribute mapping tables
# ---------------------------------------------------------------------------

# bind:X → Alpine x-directive mapping
_BIND_ALPINE: dict[str, str] = {
    "text": "x-text",
    "model": "x-model",
    "show": "x-show",
    "html": "x-html",
    "cloak": "x-cloak",
    "ref": "x-ref",
    "transition": "x-transition",
    "init": "x-init",
}

# Shorthand HTMX attrs: DSL name → hx-* name
_HTMX_ATTRS: frozenset[str] = frozenset(
    {
        "swap",
        "target",
        "trigger",
        "select",
        "select-oob",
        "confirm",
        "indicator",
        "push-url",
        "replace-url",
        "vals",
        "headers",
        "encoding",
        "preserve",
        "sync",
        "disabled-elt",
    }
)


def _compile_attr(name: str, value: str | bool) -> list[tuple[str, str | bool]]:
    """Transform a single DSL attribute into one or more output attributes."""
    # Boolean attribute
    if value is True:
        if name == "reactive":
            return []  # handled separately via x-data
        if name == "boost":
            return [("hx-boost", "true")]
        if name == "send":
            return [("ws-send", True)]
        return [(name, True)]

    sval = str(value)

    # bind:X
    if name.startswith("bind:"):
        suffix = name[5:]
        # Check for modifiers (e.g., bind:model.lazy)
        base = suffix.split(".")[0]
        if base in _BIND_ALPINE:
            mapped = _BIND_ALPINE[base]
            # Re-attach modifiers
            if "." in suffix:
                mods = suffix[len(base) :]
                mapped += mods
            return [(mapped, sval)]
        # Generic bind → Alpine shorthand :attr
        return [(f":{suffix}", sval)]

    # on:event[.mods]
    if name.startswith("on:"):
        event = name[3:]
        return [(f"@{event}", sval)]

    # action:verb → hx-verb
    if name.startswith("action:"):
        verb = name[7:]
        return [(f"hx-{verb}", sval)]

    # into= shorthand → hx-target + hx-swap
    if name == "into":
        if ":" in sval:
            target, swap = sval.rsplit(":", 1)
        else:
            target, swap = sval, "innerHTML"
        return [("hx-target", target), ("hx-swap", swap)]

    # HTMX shorthand attrs
    if name in _HTMX_ATTRS:
        return [(f"hx-{name}", sval)]

    # SSE
    if name == "live":
        return [("hx-ext", "sse"), ("sse-connect", sval)]
    if name == "channel":
        return [("sse-swap", sval)]
    if name == "close":
        return [("sse-close", sval)]

    # WebSocket
    if name == "socket":
        return [("hx-ext", "ws"), ("ws-connect", sval)]

    # loading:* → htmx indicator patterns
    if name.startswith("loading:"):
        indicator_type = name[8:]
        if indicator_type == "class":
            return [("class", f"htmx-indicator {sval}")]
        if indicator_type == "remove":
            return [("class", f"htmx-indicator-remove {sval}")]
        return [(f"loading-{indicator_type}", sval)]

    # Passthrough
    return [(name, value)]


# ---------------------------------------------------------------------------
# Compiler
# ---------------------------------------------------------------------------


class Compiler:
    """Compiles a PJX Component AST into Jinja2 + Alpine + HTMX output.

    Args:
        registry: Optional component registry for resolving includes.
            Can be ``None`` for standalone compilation.
    """

    def __init__(self, registry: ComponentRegistry | None = None) -> None:
        self._registry = registry

    def compile(self, component: Component) -> CompiledComponent:
        """Compile a Component AST into a CompiledComponent.

        Args:
            component: Parsed component AST.

        Returns:
            Compiled output with Jinja2 source, optional scoped CSS, and Alpine data.
        """
        parts: list[str] = []
        scope_hash = generate_scope_hash(component.path)

        # Extends
        if component.extends:
            parts.append(f'{{% extends "{component.extends.source}" %}}')
            parts.append("")

        # Preamble: {% set %} for let/const/computed
        preamble = self._compile_preamble(component)
        if preamble:
            parts.append(preamble)

        # Alpine stores
        for store in component.stores:
            parts.append(
                f'<script>document.addEventListener("alpine:init", () => '
                f"Alpine.store('{store.name}', {store.value}))</script>"
            )

        # Body
        body_html = self._compile_nodes(component.body, component, scope_hash)
        parts.append(body_html)

        jinja_source = "\n".join(parts).strip()

        # Scoped CSS
        scoped_style: ScopedStyle | None = None
        if component.style:
            scoped_css = scope_css(component.style, scope_hash)
            scoped_style = ScopedStyle(source=scoped_css, hash=scope_hash)

        # Alpine data
        alpine_data = self._build_alpine_data(component)

        return CompiledComponent(
            jinja_source=jinja_source,
            css=scoped_style,
            alpine_data=alpine_data,
            scope_hash=scope_hash,
            assets=component.assets,
        )

    def _compile_preamble(self, component: Component) -> str:
        """Generate ``{% set %}`` statements for variables, computed values, and props namespace."""
        lines: list[str] = []

        # Build props namespace so templates can use props.X syntax
        if component.props:
            field_names = [f.name for f in component.props.fields]
            # Set defaults for props fields, then build namespace
            for field in component.props.fields:
                if field.default is not None:
                    lines.append(
                        f"{{% set {field.name} = {field.name}|default({field.default}) %}}"
                    )
            ns_args = ", ".join(f"{n}={n}" for n in field_names)
            lines.append(f"{{% set props = namespace({ns_args}) %}}")

        # State defaults (server-side fallback for Jinja rendering)
        for state in component.states:
            lines.append(
                f"{{% set {state.name} = {state.name}|default({state.value}) %}}"
            )

        for var in component.variables:
            lines.append(f"{{% set {var.name} = {var.expr} %}}")
        for comp in component.computed:
            lines.append(f"{{% set {comp.name} = {comp.expr} %}}")
        return "\n".join(lines)

    def _build_alpine_data(self, component: Component) -> str | None:
        """Build the Alpine.js x-data JSON string from state declarations."""
        if not component.states:
            return None
        pairs = [f"{s.name}: {s.value}" for s in component.states]
        return "{ " + ", ".join(pairs) + " }"

    def _compile_nodes(
        self,
        nodes: tuple[Node, ...],
        component: Component,
        scope_hash: str,
    ) -> str:
        return "".join(self._compile_node(n, component, scope_hash) for n in nodes)

    def _compile_node(
        self,
        node: Node,
        component: Component,
        scope_hash: str,
    ) -> str:
        match node:
            case TextNode(content=content):
                return content

            case ExprNode(expr=expr):
                return f"{{{{ {expr} }}}}"

            case ElementNode():
                return self._compile_element(node, component, scope_hash)

            case ShowNode():
                return self._compile_show(node, component, scope_hash)

            case ForNode():
                return self._compile_for(node, component, scope_hash)

            case SwitchNode():
                return self._compile_switch(node, component, scope_hash)

            case PortalNode():
                return self._compile_portal(node, component, scope_hash)

            case ErrorBoundaryNode():
                return self._compile_error_boundary(node, component, scope_hash)

            case AwaitNode():
                return self._compile_await(node, component, scope_hash)

            case TransitionNode():
                return self._compile_transition(node, component, scope_hash)

            case TransitionGroupNode():
                return self._compile_transition_group(node, component, scope_hash)

            case FragmentNode():
                return self._compile_nodes(node.children, component, scope_hash)

            case TeleportNode():
                return self._compile_teleport(node, component, scope_hash)

            case SlotRenderNode():
                return self._compile_slot_render(node, component, scope_hash)

            case SlotPassNode():
                return self._compile_nodes(node.content, component, scope_hash)

            case ComponentNode():
                return self._compile_component(node, component, scope_hash)

            case CaseNode():
                return self._compile_nodes(node.body, component, scope_hash)

            case _:
                raise CompileError(
                    f"unknown node type: {type(node).__name__}", path=component.path
                )

    def _compile_element(
        self,
        node: ElementNode,
        component: Component,
        scope_hash: str,
    ) -> str:
        attrs = self._compile_attrs(node.attrs, component, scope_hash)
        if node.self_closing:
            return f"<{node.tag}{attrs} />"
        inner = self._compile_nodes(node.children, component, scope_hash)
        return f"<{node.tag}{attrs}>{inner}</{node.tag}>"

    def _compile_attrs(
        self,
        attrs: dict[str, str | bool],
        component: Component,
        scope_hash: str,
    ) -> str:
        """Transform DSL attributes to output HTML attributes."""
        out_attrs: list[tuple[str, str | bool]] = []
        has_reactive = "reactive" in attrs

        for name, value in attrs.items():
            if name == "reactive":
                # Add x-data with state
                alpine_data = self._build_alpine_data(component) or "{}"
                out_attrs.append(("x-data", alpine_data))
                # Add scope attribute
                out_attrs.append((f"data-pjx-{scope_hash}", True))
                continue
            out_attrs.extend(_compile_attr(name, value))

        if not has_reactive and component.style:
            # Add scope attribute for CSS scoping even without reactive
            out_attrs.append((f"data-pjx-{scope_hash}", True))

        return self._render_attrs(out_attrs)

    def _render_attrs(self, attrs: list[tuple[str, str | bool]]) -> str:
        if not attrs:
            return ""
        parts: list[str] = []
        for name, value in attrs:
            if value is True:
                parts.append(name)
            elif '"' in str(value):
                parts.append(f"{name}='{value}'")
            else:
                parts.append(f'{name}="{value}"')
        return " " + " ".join(parts)

    def _compile_show(
        self, node: ShowNode, component: Component, scope_hash: str
    ) -> str:
        body = self._compile_nodes(node.body, component, scope_hash)
        result = f"{{% if {node.when} %}}{body}"
        if node.fallback:
            fallback = self._compile_nodes(node.fallback, component, scope_hash)
            result += f"{{% else %}}{fallback}"
        result += "{% endif %}"
        return result

    def _compile_for(self, node: ForNode, component: Component, scope_hash: str) -> str:
        body = self._compile_nodes(node.body, component, scope_hash)
        result = f"{{% for {node.as_var} in {node.each} %}}{body}"
        if node.empty:
            empty = self._compile_nodes(node.empty, component, scope_hash)
            result += f"{{% else %}}{empty}"
        result += "{% endfor %}"
        return result

    def _compile_switch(
        self, node: SwitchNode, component: Component, scope_hash: str
    ) -> str:
        parts: list[str] = []
        for i, case in enumerate(node.cases):
            keyword = "if" if i == 0 else "elif"
            body = self._compile_nodes(case.body, component, scope_hash)
            parts.append(f"{{% {keyword} {node.on} == {case.value} %}}{body}")
        if node.default:
            default_body = self._compile_nodes(node.default, component, scope_hash)
            parts.append(f"{{% else %}}{default_body}")
        parts.append("{% endif %}")
        return "".join(parts)

    def _compile_portal(
        self, node: PortalNode, component: Component, scope_hash: str
    ) -> str:
        body = self._compile_nodes(node.body, component, scope_hash)
        return (
            f'<div hx-get="{node.target}" hx-swap="{node.swap}" '
            f'hx-trigger="load">{body}</div>'
        )

    def _compile_error_boundary(
        self, node: ErrorBoundaryNode, component: Component, scope_hash: str
    ) -> str:
        body = self._compile_nodes(node.body, component, scope_hash)
        return f"{{% try %}}{body}{{% except %}}{node.fallback}{{% endtry %}}"

    def _compile_await(
        self, node: AwaitNode, component: Component, scope_hash: str
    ) -> str:
        loading_html = ""
        if node.loading:
            loading_html = self._compile_nodes(node.loading, component, scope_hash)
        return (
            f'<div hx-get="{node.src}" hx-trigger="{node.trigger}" '
            f'hx-swap="innerHTML">{loading_html}</div>'
        )

    def _compile_transition(
        self, node: TransitionNode, component: Component, scope_hash: str
    ) -> str:
        body = self._compile_nodes(node.body, component, scope_hash)
        attrs_parts: list[str] = []
        if node.enter:
            attrs_parts.append(f'x-transition:enter="{node.enter}"')
        if node.leave:
            attrs_parts.append(f'x-transition:leave="{node.leave}"')
        attrs_str = " ".join(attrs_parts)
        return f"<div {attrs_str}>{body}</div>"

    def _compile_transition_group(
        self, node: TransitionGroupNode, component: Component, scope_hash: str
    ) -> str:
        body = self._compile_nodes(node.body, component, scope_hash)
        attrs_parts: list[str] = []
        if node.enter:
            attrs_parts.append(f'x-transition:enter="{node.enter}"')
        if node.leave:
            attrs_parts.append(f'x-transition:leave="{node.leave}"')
        if node.move:
            attrs_parts.append(f'x-transition:move="{node.move}"')
        attrs_str = " ".join(attrs_parts)
        tag = node.tag
        return f"<{tag} {attrs_str}>{body}</{tag}>"

    def _compile_teleport(
        self, node: TeleportNode, component: Component, scope_hash: str
    ) -> str:
        body = self._compile_nodes(node.body, component, scope_hash)
        return f"{{% block teleport_{node.to} %}}{body}{{% endblock %}}"

    def _compile_slot_render(
        self, node: SlotRenderNode, component: Component, scope_hash: str
    ) -> str:
        var_name = f"slot_{node.name}"
        if node.fallback:
            fallback_html = self._compile_nodes(node.fallback, component, scope_hash)
            return f"{{% if {var_name} is defined %}}{{{{ {var_name} }}}}{{% else %}}{fallback_html}{{% endif %}}"
        return f'{{{{ {var_name}|default("") }}}}'

    def _compile_component(
        self, node: ComponentNode, component: Component, scope_hash: str
    ) -> str:
        """Compile a component usage to ``{% set %}`` + ``{% include %}``."""
        lines: list[str] = []

        # Find template path from imports (needed for child lookup)
        # Built-in layout components resolve to ui/layouts/<Name>.jinja
        if node.name in LAYOUT_COMPONENTS:
            template_path = f"{LAYOUT_PREFIX}/{node.name}.jinja"
        else:
            template_path = f"{node.name}.jinja"
            for imp in component.imports:
                if node.name in imp.names:
                    template_path = imp.source
                    break

        # Reset props for built-in layout components to prevent scope leaking
        # through Jinja {% include %}. Unmentioned props must be cleared.
        if node.name in LAYOUT_COMPONENTS:
            passed = set(node.attrs.keys())
            for prop_name in get_layout_props(node.name):
                if prop_name not in passed:
                    lines.append(f'{{% set {prop_name} = "" %}}')

        # Separate declared props from extra passthrough attrs
        child_props_decl = None
        if self._registry is not None:
            child = self._registry.get(node.name)
            if child is not None:
                child_props_decl = child.props

        props_attrs, extra_attrs = separate_attrs(child_props_decl, node.attrs)

        # Set declared props
        for name, value in props_attrs.items():
            if value is True:
                lines.append(f"{{% set {name} = true %}}")
            elif "{{" in str(value):
                # Jinja expression — extract and pass raw
                expr = str(value).replace("{{", "").replace("}}", "").strip()
                lines.append(f"{{% set {name} = {expr} %}}")
            else:
                lines.append(f'{{% set {name} = "{value}" %}}')

        # Extra attrs → pre-rendered string via {% set attrs %}...{% endset %}
        # Jinja evaluates expressions inside the block at render time.
        if extra_attrs:
            attr_parts: list[str] = []
            for name, value in extra_attrs.items():
                for out_name, out_value in _compile_attr(name, value):
                    if out_value is True:
                        attr_parts.append(out_name)
                    elif "{{" in str(out_value):
                        # Jinja expression — keep raw so it evaluates at render
                        attr_parts.append(f'{out_name}="{out_value}"')
                    else:
                        attr_parts.append(f'{out_name}="{out_value}"')
            attrs_str = " ".join(attr_parts)
            lines.append(f"{{% set attrs %}}{attrs_str}{{% endset %}}")
        else:
            lines.append('{% set attrs = "" %}')

        # Spread
        if node.spread:
            lines.append(f"{{% set _spread = {node.spread} %}}")

        # Slots passed to child (from explicit node.slots dict)
        for slot_name, slot_nodes in node.slots.items():
            slot_content = self._compile_nodes(slot_nodes, component, scope_hash)
            lines.append(f"{{% set slot_{slot_name} %}}{slot_content}{{% endset %}}")

        # Extract SlotRenderNodes from children as named slot passes;
        # remaining children become slot_default
        if node.children:
            default_children: list[Node] = []
            for child in node.children:
                if isinstance(child, SlotRenderNode):
                    # <Slot:name> inside a component = pass content to that slot
                    if child.fallback:
                        slot_html = self._compile_nodes(
                            child.fallback, component, scope_hash
                        )
                        lines.append(
                            f"{{% set slot_{child.name} %}}{slot_html}{{% endset %}}"
                        )
                else:
                    default_children.append(child)
            # Non-slot children become slot_default
            if any(
                not isinstance(c, TextNode) or c.content.strip()
                for c in default_children
            ):
                children_html = self._compile_nodes(
                    tuple(default_children), component, scope_hash
                )
                lines.append(f"{{% set slot_default %}}{children_html}{{% endset %}}")

        lines.append(f'{{% include "{template_path}" %}}')
        return "".join(lines)

    # -- On-the-fly rendering helpers ----------------------------------------

    _INCLUDE_RE = re.compile(r'\{%[-\s]*include\s+"([^"]+)"\s*[-]?%}')

    @staticmethod
    def inline_includes(
        source: str,
        compiled_templates: dict[str, str],
        *,
        max_depth: int = 50,
    ) -> str:
        """Replace ``{% include "X" %}`` with the template source, recursively.

        Produces a single flat template string with no includes, suitable for
        ``engine.render_string()``.

        Args:
            source: Compiled Jinja2 source with include directives.
            compiled_templates: Map of template name → compiled Jinja2 source.
            max_depth: Maximum recursion depth (prevents infinite loops).

        Returns:
            Flattened template source.
        """
        if max_depth <= 0:
            return source

        def _replace(match: re.Match[str]) -> str:
            name = match.group(1)
            child_source = compiled_templates.get(name)
            if child_source is None:
                return match.group(0)  # keep original if not found
            # Recursively inline nested includes
            return Compiler.inline_includes(
                child_source, compiled_templates, max_depth=max_depth - 1
            )

        return Compiler._INCLUDE_RE.sub(_replace, source)
