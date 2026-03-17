"""Recursive descent parser for .pjx source files.

Produces a PjxFile AST from raw source text.

Design notes
------------
* No separate lexer — the parser operates directly on the source string via
  a position cursor.  This avoids the dead-code problem identified in the
  reviewed implementations.
* `@component` blocks are parsed with a proper brace-depth tracker, not a
  naive ``str.replace`` that fires on the first ``}`` it sees.
* Every ``{{ }}`` expression is treated as an opaque token and preserved
  verbatim; Jinja2 will evaluate it at render time.
* Line / col tracking is used exclusively for error messages.
"""

from __future__ import annotations

import re
from typing import Any

from .ast import (
    Attribute,
    BindDirective,
    ComponentCall,
    ComponentDef,
    ExprNode,
    ForNode,
    FromImport,
    HtmlElement,
    ImportDirective,
    LetDirective,
    MatchCase,
    NamedSlotContent,
    PjxFile,
    PropDef,
    PropsBlock,
    ShowNode,
    SlotDecl,
    SlotNode,
    StateBlock,
    StateField,
    SwitchNode,
    TextNode,
)
from .exceptions import ParseError

# ── Constants ─────────────────────────────────────────────────────────────────

_VOID_ELEMENTS = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)

_RE_IDENT = re.compile(r"[A-Za-z_]\w*")
_RE_DOTTED = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")
_RE_TAG_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*")
_RE_ATTR_NAME = re.compile(r"[@:A-Za-z_][\w.:-]*")
_RE_SLOT_CLOSE = re.compile(r"</:([\w-]+)>")
_RE_COMMENT = re.compile(r"\{#.*?#\}", re.DOTALL)


# ── Parser ────────────────────────────────────────────────────────────────────


class Parser:
    """Parse a .pjx source string into a ``PjxFile`` AST."""

    def __init__(self, source: str, filename: str = "<string>") -> None:
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1

    # ── Public entry ──────────────────────────────────────────────────────────

    def parse(self) -> PjxFile:
        self._skip_blanks()
        imports: list[FromImport | ImportDirective] = []
        bind: BindDirective | None = None
        props: PropsBlock | None = None
        slots: list[SlotDecl] = []
        state: StateBlock | None = None
        lets: list[LetDirective] = []
        components: list[ComponentDef] = []

        # Multi-component mode: all top-level content is @component blocks
        if self._has_component_blocks():
            while not self._at_end():
                self._skip_blanks()
                if self._at_end():
                    break
                if self._lookahead("@from"):
                    imports.append(self._parse_from())
                elif self._lookahead("@import"):
                    imports.append(self._parse_import())
                elif self._lookahead("@component"):
                    components.append(self._parse_component_def())
                else:
                    ch = self.source[self.pos]
                    raise ParseError(
                        f"Unexpected character {ch!r} in multi-component file",
                        file=self.filename,
                        line=self.line,
                    )
            return PjxFile(
                imports=tuple(imports),
                components=tuple(components),
            )

        # Simple mode: optional directives followed by template body
        while not self._at_end():
            self._skip_blanks()
            if self._at_end():
                break
            if self._lookahead("@from"):
                imports.append(self._parse_from())
            elif self._lookahead("@import"):
                imports.append(self._parse_import())
            elif self._lookahead("@bind"):
                bind = self._parse_bind()
            elif self._lookahead("@props"):
                props = self._parse_props_block()
            elif self._lookahead("@slot"):
                slots.append(self._parse_slot_decl())
            elif self._lookahead("@state"):
                state = self._parse_state_block()
            elif self._lookahead("@let"):
                lets.append(self._parse_let())
            else:
                break  # start of template body

        body = self._parse_body(stop_tags=set())
        return PjxFile(
            imports=tuple(imports),
            bind=bind,
            props=props,
            slots=tuple(slots),
            state=state,
            lets=tuple(lets),
            body=tuple(body),
        )

    # ── Heuristic: multi-component detection ──────────────────────────────────

    def _has_component_blocks(self) -> bool:
        """Return True if this file is in multi-component mode.

        A file is multi-component when the first substantive top-level line
        (after ``@import`` / ``@from`` and blank lines) is a ``@component``
        directive.  This avoids false positives from ``@component`` text
        that appears inside ``<pre><code>`` blocks in showcase templates.
        """
        for line in self.source.splitlines():
            stripped = line.strip()
            if not stripped:
                continue  # blank line
            if stripped.startswith("@import ") or stripped.startswith("@from "):
                continue  # allowed before @component blocks
            return stripped.startswith("@component ")
        return False

    # ── Directive parsers ─────────────────────────────────────────────────────

    def _parse_from(self) -> FromImport:
        line, col = self.line, self.col
        self._expect("@from")
        self._skip_ws()
        module = self._consume_re(_RE_DOTTED) or self._err(
            "Expected module path after @from"
        )
        self._skip_ws()
        self._expect("import")
        self._skip_ws()
        names: list[str] = []
        while True:
            name = self._consume_re(_RE_IDENT)
            if name:
                names.append(name)
            self._skip_ws()
            if self._peek() == ",":
                self._advance()
                self._skip_ws()
            else:
                break
        self._skip_line()
        return FromImport(module=module, names=tuple(names), line=line, col=col)

    def _parse_import(self) -> ImportDirective:
        line, col = self.line, self.col
        self._expect("@import")
        self._skip_ws()
        path = self._parse_string()
        self._skip_line()
        return ImportDirective(path=path, line=line, col=col)

    def _parse_bind(self) -> BindDirective:
        line, col = self.line, self.col
        self._expect("@bind")
        self._skip_ws()
        self._expect("from")
        self._skip_ws()
        module = self._consume_re(_RE_DOTTED) or self._err(
            "Expected module path after @bind from"
        )
        self._skip_ws()
        self._expect("import")
        self._skip_ws()
        class_name = self._consume_re(_RE_IDENT) or self._err("Expected class name")
        self._skip_line()
        return BindDirective(module=module, class_name=class_name, line=line, col=col)

    def _parse_props_block(self) -> PropsBlock:
        line, col = self.line, self.col
        self._expect("@props")
        self._skip_ws()
        self._expect("{")
        props: list[PropDef] = []
        while True:
            self._skip_blanks()
            # Skip optional trailing comma between props
            if self._peek() == ",":
                self._advance()
                self._skip_blanks()
            if self._lookahead("}"):
                self._advance()
                break
            if self._at_end():
                self._err("Unclosed @props block")
            props.append(self._parse_prop_def())
        return PropsBlock(props=tuple(props), line=line, col=col)

    def _parse_prop_def(self) -> PropDef:
        line, col = self.line, self.col
        name = self._consume_re(_RE_IDENT) or self._err("Expected prop name")
        self._skip_ws()
        self._expect(":")
        self._skip_ws()
        type_expr, default_expr = self._parse_type_and_default()
        return PropDef(
            name=name,
            type_expr=type_expr or None,
            default_expr=default_expr,
            line=line,
            col=col,
        )

    def _parse_type_and_default(self) -> tuple[str, str | None]:
        """Parse ``TypeExpr = default`` up to newline, ``,``, or ``}``."""
        type_parts: list[str] = []
        depth = 0
        in_quote: str | None = None

        while not self._at_end():
            ch = self._peek()
            if in_quote:
                type_parts.append(self._advance())
                if ch == in_quote:
                    in_quote = None
                continue
            if ch in ('"', "'"):
                in_quote = ch
                type_parts.append(self._advance())
                continue
            if ch in "([":
                depth += 1
                type_parts.append(self._advance())
            elif ch in ")]":
                depth -= 1
                type_parts.append(self._advance())
            elif ch == "=" and depth == 0:
                self._advance()
                self._skip_ws()
                default_val = self._parse_default_value()
                return "".join(type_parts).strip(), default_val
            elif ch in ("\n", ",") and depth == 0:
                # Consume newlines; leave commas for _parse_props_block to skip
                if ch == "\n":
                    self._advance()
                break
            elif ch == "}" and depth == 0:
                break
            else:
                type_parts.append(self._advance())

        return "".join(type_parts).strip(), None

    def _parse_default_value(self) -> str:
        """Consume a default value until newline, ``,``, or ``}`` at depth 0."""
        parts: list[str] = []
        depth = 0
        in_quote: str | None = None

        while not self._at_end():
            ch = self._peek()
            if in_quote:
                parts.append(self._advance())
                if ch == in_quote:
                    in_quote = None
                continue
            if ch in ('"', "'"):
                in_quote = ch
                parts.append(self._advance())
                continue
            if ch in "([{":
                depth += 1
                parts.append(self._advance())
            elif ch in ")]}":
                if depth == 0:
                    break
                depth -= 1
                parts.append(self._advance())
            elif ch in ("\n", ",") and depth == 0:
                # Consume newlines; leave commas for the parent to skip
                if ch == "\n":
                    self._advance()
                break
            else:
                parts.append(self._advance())

        return "".join(parts).strip()

    def _parse_slot_decl(self) -> SlotDecl:
        line, col = self.line, self.col
        self._expect("@slot")
        self._skip_ws()
        raw = self._consume_re(re.compile(r"[A-Za-z_][\w]*\??")) or self._err(
            "Expected slot name"
        )
        optional = raw.endswith("?")
        name = raw.rstrip("?")
        self._skip_line()
        return SlotDecl(name=name, optional=optional, line=line, col=col)

    def _parse_state_block(self) -> StateBlock:
        line, col = self.line, self.col
        self._expect("@state")
        self._skip_ws()
        self._expect("{")
        fields: list[StateField] = []
        while True:
            self._skip_blanks()
            # Skip optional trailing comma between fields
            if self._peek() == ",":
                self._advance()
                self._skip_blanks()
            if self._lookahead("}"):
                self._advance()
                break
            if self._at_end():
                self._err("Unclosed @state block")
            fields.append(self._parse_state_field())
        return StateBlock(fields=tuple(fields), line=line, col=col)

    def _parse_state_field(self) -> StateField:
        line, col = self.line, self.col
        name = self._consume_re(_RE_IDENT) or self._err("Expected state field name")
        self._skip_ws()
        self._expect(":")
        self._skip_ws()
        value = self._parse_default_value()
        return StateField(name=name, value=value or "null", line=line, col=col)

    def _parse_let(self) -> LetDirective:
        line, col = self.line, self.col
        self._expect("@let")
        self._skip_ws()
        name = self._consume_re(_RE_IDENT) or self._err(
            "Expected variable name after @let"
        )
        self._skip_ws()
        self._expect("=")
        self._skip_ws()
        expr = self._consume_until_newline()
        return LetDirective(name=name, expr=expr.strip(), line=line, col=col)

    # ── @component block ──────────────────────────────────────────────────────

    def _parse_component_def(self) -> ComponentDef:
        line, col = self.line, self.col
        self._expect("@component")
        self._skip_ws()
        name = self._consume_re(_RE_IDENT) or self._err("Expected component name")
        self._skip_ws()
        self._expect("{")

        bind: BindDirective | None = None
        props: PropsBlock | None = None
        slots: list[SlotDecl] = []
        state: StateBlock | None = None
        lets: list[LetDirective] = []

        # Parse inner directives until we hit the body or closing brace
        while not self._at_end():
            self._skip_blanks()
            if self._lookahead("}"):
                self._advance()
                return ComponentDef(
                    name=name,
                    bind=bind,
                    props=props,
                    slots=tuple(slots),
                    state=state,
                    lets=tuple(lets),
                    children=(),
                    line=line,
                    col=col,
                )
            if self._lookahead("@bind"):
                bind = self._parse_bind()
            elif self._lookahead("@props"):
                props = self._parse_props_block()
            elif self._lookahead("@slot"):
                slots.append(self._parse_slot_decl())
            elif self._lookahead("@state"):
                state = self._parse_state_block()
            elif self._lookahead("@let"):
                lets.append(self._parse_let())
            else:
                break  # start of body

        # Parse template body until the matching closing brace
        children = self._parse_body(stop_tags={"}"})
        self._skip_blanks()
        if self._lookahead("}"):
            self._advance()

        return ComponentDef(
            name=name,
            bind=bind,
            props=props,
            slots=tuple(slots),
            state=state,
            lets=tuple(lets),
            children=tuple(children),
            line=line,
            col=col,
        )

    # ── Template body ─────────────────────────────────────────────────────────

    def _parse_body(self, stop_tags: set[str]) -> list[Any]:
        """Parse template nodes until EOF, a close tag, or a stop marker."""
        nodes: list[Any] = []
        while not self._at_end():
            self._skip_jinja_comments()
            if self._at_end():
                break

            # Stop markers (used inside @component blocks)
            for marker in stop_tags:
                if self._lookahead(marker):
                    return nodes

            # Named slot close tag — parent handles it
            if self._lookahead("</"):
                break

            node = self._parse_node()
            if node is not None:
                nodes.append(node)

        return nodes

    def _parse_node(self) -> Any:
        self._skip_inline_comments()
        if self._at_end():
            return None

        # Jinja2 expression {{ ... }}
        if self._lookahead("{{"):
            return self._parse_expr()

        # Named slot content <:name>
        if self._lookahead("<:"):
            return self._parse_named_slot_content()

        # Close tag — signals end of parent's child scope
        if self._lookahead("</"):
            return None

        # HTML declaration <!DOCTYPE html> or comment <!-- --> — pass through
        if self._lookahead("<!"):
            return self._parse_html_raw()

        # HTML / component element
        if self._peek() == "<":
            return self._parse_element()

        # Plain text
        return self._parse_text()

    def _parse_expr(self) -> ExprNode:
        line, col = self.line, self.col
        start = self.pos
        self._expect("{{")
        # Consume until }}; handle nested {{ }} via depth counting
        depth = 1
        while not self._at_end() and depth > 0:
            if self._lookahead("{{"):
                depth += 1
                self._advance(2)
            elif self._lookahead("}}"):
                depth -= 1
                self._advance(2)
            else:
                self._advance()
        content = self.source[start : self.pos]
        return ExprNode(content=content, line=line, col=col)

    def _parse_html_raw(self) -> TextNode:
        """Consume ``<!DOCTYPE ...>`` declarations and ``<!-- -->`` comments as raw text."""
        line, col = self.line, self.col
        start = self.pos
        self._advance(2)  # <!
        if self._lookahead("--"):
            self._advance(2)  # --
            while not self._at_end():
                if self._lookahead("-->"):
                    self._advance(3)
                    break
                self._advance()
        else:
            while not self._at_end() and self._peek() != ">":
                self._advance()
            if not self._at_end():
                self._advance()  # >
        return TextNode(content=self.source[start : self.pos], line=line, col=col)

    def _parse_text(self) -> TextNode | None:
        line, col = self.line, self.col
        parts: list[str] = []
        while not self._at_end():
            ch = self._peek()
            if ch == "<":
                break
            if self._lookahead("{{"):
                break
            # Consume {# ... #} inline Jinja comments (no text output)
            if self._lookahead("{#"):
                m = _RE_COMMENT.match(self.source, self.pos)
                if m:
                    self._advance(len(m.group()))
                    continue
                break
            # Stop at brace-only stop markers (inside @component)
            if ch == "}" and col == 1:
                break
            parts.append(self._advance())

        text = "".join(parts)
        if not text:
            return None
        return TextNode(content=text, line=line, col=col)

    def _parse_element(self) -> Any:
        line, col = self.line, self.col
        self._expect("<")

        tag = self._consume_re(_RE_TAG_NAME)
        if not tag:
            self._err("Expected tag name after '<'")

        attrs = self._parse_attributes()
        self._skip_ws()

        self_closing = False
        if self._lookahead("/>"):
            self._advance(2)
            self_closing = True
        elif self._lookahead(">"):
            self._advance()
        else:
            self._err(f"Expected '>' or '/>' after <{tag}>")

        if tag.lower() in _VOID_ELEMENTS:
            self_closing = True

        # ── Control structures ────────────────────────────────────────────────
        if tag == "Show":
            return self._build_show(attrs, self_closing, line, col)
        if tag == "For":
            return self._build_for(attrs, self_closing, line, col)
        if tag == "Switch":
            return self._build_switch(attrs, self_closing, line, col)
        if tag == "slot":
            return self._build_slot(attrs, self_closing, line, col)

        # ── Component or HTML ─────────────────────────────────────────────────
        children: list[Any] = []
        named_slots: dict[str, tuple[Any, ...]] = {}

        if not self_closing:
            children, named_slots = self._parse_element_children(tag)
            self._skip_jinja_comments()
            self._expect(f"</{tag}>")

        if tag[0].isupper():
            return ComponentCall(
                name=tag,
                attrs=tuple(attrs),
                children=tuple(children),
                named_slots=named_slots,
                self_closing=self_closing,
                line=line,
                col=col,
            )
        return HtmlElement(
            tag=tag,
            attrs=tuple(attrs),
            children=tuple(children),
            self_closing=self_closing,
            line=line,
            col=col,
        )

    def _parse_element_children(
        self, parent_tag: str
    ) -> tuple[list[Any], dict[str, tuple[Any, ...]]]:
        """Return (default_children, named_slots_dict)."""
        children: list[Any] = []
        named_slots: dict[str, tuple[Any, ...]] = {}

        while not self._at_end():
            self._skip_inline_comments()
            if self._at_end():
                break
            if self._lookahead(f"</{parent_tag}>"):
                break
            # Named slot content <:name>
            if self._lookahead("<:"):
                slot_node = self._parse_named_slot_content()
                if isinstance(slot_node, NamedSlotContent):
                    named_slots[slot_node.name] = slot_node.children
                continue
            # Any other close tag means we've over-shot — stop
            if self._lookahead("</"):
                break
            node = self._parse_node()
            if node is None:
                break
            children.append(node)

        return children, named_slots

    def _parse_named_slot_content(self) -> NamedSlotContent:
        line, col = self.line, self.col
        self._expect("<:")
        name = self._consume_re(re.compile(r"[A-Za-z_][\w-]*")) or self._err(
            "Expected slot name after '<:'"
        )
        # Optional let: bindings
        let_bindings: list[str] = []
        self._skip_ws()
        while self._lookahead("let:"):
            self._expect("let:")
            binding = self._consume_re(_RE_IDENT)
            if binding:
                let_bindings.append(binding)
            self._skip_ws()
        self._skip_ws()
        self._expect(">")

        children = self._parse_body(stop_tags=set())
        self._skip_jinja_comments()
        self._expect(f"</:{name}>")

        return NamedSlotContent(
            name=name,
            let_bindings=tuple(let_bindings),
            children=tuple(children),
            line=line,
            col=col,
        )

    # ── Attribute parsing ─────────────────────────────────────────────────────

    def _parse_attributes(self) -> list[Attribute]:
        attrs: list[Attribute] = []
        while not self._at_end():
            self._skip_blanks()
            if self._peek() in (">", "/") or self._lookahead("/>"):
                break
            line, col = self.line, self.col
            name = self._consume_re(_RE_ATTR_NAME)
            if not name:
                break
            value: str | None = None
            self._skip_blanks()
            if self._peek() == "=":
                self._advance()
                self._skip_blanks()
                value = self._parse_attr_value()
            attrs.append(Attribute(name=name, value=value, line=line, col=col))
        return attrs

    def _parse_attr_value(self) -> str:
        if self._peek() == '"':
            return self._parse_dq_string()
        if self._peek() == "'":
            return self._parse_sq_string()
        if self._lookahead("{{"):
            return self._parse_expr().content
        # Unquoted
        parts: list[str] = []
        while not self._at_end() and self._peek() not in (" ", "\t", "\n", ">", "/"):
            parts.append(self._advance())
        return "".join(parts)

    def _parse_dq_string(self) -> str:
        self._expect('"')
        parts: list[str] = []
        while not self._at_end() and self._peek() != '"':
            if self._lookahead("{{"):
                expr = self._parse_expr()
                parts.append(expr.content)
            elif self._peek() == "\\":
                self._advance()
                if not self._at_end():
                    parts.append(self._advance())
            else:
                parts.append(self._advance())
        self._expect('"')
        return "".join(parts)

    def _parse_sq_string(self) -> str:
        self._expect("'")
        parts: list[str] = []
        while not self._at_end() and self._peek() != "'":
            parts.append(self._advance())
        self._expect("'")
        return "".join(parts)

    # ── Control structure builders ────────────────────────────────────────────

    def _get_attr(self, attrs: list[Attribute], name: str) -> str | None:
        for a in attrs:
            if a.name == name:
                return a.value
        return None

    def _strip_expr(self, val: str | None) -> str:
        """Strip ``{{ }}`` delimiters from an attribute value."""
        if val is None:
            return ""
        val = val.strip()
        if val.startswith("{{") and val.endswith("}}"):
            return val[2:-2].strip()
        return val.strip('"').strip("'")

    def _build_show(
        self, attrs: list[Attribute], self_closing: bool, line: int, col: int
    ) -> ShowNode:
        condition = self._strip_expr(self._get_attr(attrs, "when"))
        if not condition:
            self._err("<Show> requires a 'when' attribute", line=line)
        children: list[Any] = []
        fallback: list[Any] = []
        if not self_closing:
            raw_children, named = self._parse_element_children("Show")
            children = raw_children
            fallback = list(named.get("fallback", ()))
            self._skip_jinja_comments()
            self._expect("</Show>")
        return ShowNode(
            condition=condition,
            children=tuple(children),
            fallback=tuple(fallback),
            line=line,
            col=col,
        )

    def _build_for(
        self, attrs: list[Attribute], self_closing: bool, line: int, col: int
    ) -> ForNode:
        iterable = self._strip_expr(self._get_attr(attrs, "each"))
        if not iterable:
            self._err("<For> requires an 'each' attribute", line=line)
        variable = (self._get_attr(attrs, "as") or "item").strip("\"'")
        index_var_raw = self._get_attr(attrs, "index")
        index_var = index_var_raw.strip("\"'") if index_var_raw else None
        children: list[Any] = []
        empty: list[Any] = []
        if not self_closing:
            raw_children, named = self._parse_element_children("For")
            children = raw_children
            empty = list(named.get("empty", ()))
            self._skip_jinja_comments()
            self._expect("</For>")
        return ForNode(
            iterable=iterable,
            variable=variable,
            index_var=index_var,
            children=tuple(children),
            empty=tuple(empty),
            line=line,
            col=col,
        )

    def _build_switch(
        self, attrs: list[Attribute], self_closing: bool, line: int, col: int
    ) -> SwitchNode:
        expression = self._strip_expr(self._get_attr(attrs, "on"))
        if not expression:
            self._err("<Switch> requires an 'on' attribute", line=line)
        cases: list[MatchCase] = []
        fallback: list[Any] = []
        if not self_closing:
            while not self._at_end():
                self._skip_jinja_comments()
                if self._lookahead("</Switch>"):
                    break
                if self._lookahead("<:fallback>"):
                    slot = self._parse_named_slot_content()
                    # _parse_named_slot_content already consumed </fallback>
                    fallback = list(slot.children)
                    continue
                if self._lookahead("<Match"):
                    cases.append(self._parse_match_case())
                else:
                    node = self._parse_node()
                    if node is None:
                        break
            self._skip_jinja_comments()
            self._expect("</Switch>")
        return SwitchNode(
            expression=expression,
            cases=tuple(cases),
            fallback=tuple(fallback),
            line=line,
            col=col,
        )

    def _parse_match_case(self) -> MatchCase:
        line, col = self.line, self.col
        self._expect("<Match")
        attrs = self._parse_attributes()
        self._skip_ws()
        self_closing = False
        if self._lookahead("/>"):
            self._advance(2)
            self_closing = True
        else:
            self._expect(">")
        value = (self._get_attr(attrs, "value") or "").strip("\"'")
        children: list[Any] = []
        if not self_closing:
            children = self._parse_body(stop_tags=set())
            self._skip_jinja_comments()
            self._expect("</Match>")
        return MatchCase(value=value, children=tuple(children), line=line, col=col)

    def _build_slot(
        self, attrs: list[Attribute], self_closing: bool, line: int, col: int
    ) -> SlotNode:
        name = (self._get_attr(attrs, "name") or "default").strip("\"'")
        scope_bindings: dict[str, str] = {}
        for attr in attrs:
            if attr.name.startswith(":") and attr.name != ":data":
                key = attr.name[1:]
                scope_bindings[key] = self._strip_expr(attr.value) or key
        fallback: list[Any] = []
        if not self_closing:
            fallback = self._parse_body(stop_tags=set())
            self._skip_jinja_comments()
            self._expect("</slot>")
        return SlotNode(
            name=name,
            scope_bindings=scope_bindings,
            fallback=tuple(fallback),
            line=line,
            col=col,
        )

    # ── String helpers ────────────────────────────────────────────────────────

    def _parse_string(self) -> str:
        if self._peek() == '"':
            return self._parse_dq_string()
        if self._peek() == "'":
            return self._parse_sq_string()
        self._err("Expected a quoted string")

    # ── Cursor helpers ────────────────────────────────────────────────────────

    def _at_end(self) -> bool:
        return self.pos >= len(self.source)

    def _peek(self, n: int = 1) -> str:
        return self.source[self.pos : self.pos + n]

    def _lookahead(self, text: str) -> bool:
        return self.source[self.pos :].startswith(text)

    def _advance(self, n: int = 1) -> str:
        text = self.source[self.pos : self.pos + n]
        for ch in text:
            if ch == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
        self.pos += n
        return text

    def _expect(self, text: str) -> str:
        if not self.source[self.pos :].startswith(text):
            got = repr(self.source[self.pos : self.pos + len(text) + 8])
            raise ParseError(
                f"Expected {text!r}, got {got}",
                file=self.filename,
                line=self.line,
            )
        return self._advance(len(text))

    def _consume_re(self, pattern: re.Pattern[str]) -> str | None:
        m = pattern.match(self.source, self.pos)
        if m:
            self._advance(len(m.group()))
            return m.group()
        return None

    def _skip_ws(self) -> None:
        """Skip inline whitespace (spaces and tabs, not newlines)."""
        while not self._at_end() and self._peek() in (" ", "\t"):
            self._advance()

    def _skip_blanks(self) -> None:
        """Skip all whitespace including newlines."""
        while not self._at_end() and self._peek() in (" ", "\t", "\n", "\r"):
            self._advance()

    def _skip_line(self) -> None:
        """Skip to the end of the current line."""
        while not self._at_end() and self._peek() != "\n":
            self._advance()
        if not self._at_end():
            self._advance()  # consume the newline

    def _skip_jinja_comments(self) -> None:
        """Skip whitespace and {# ... #} Jinja comments (block-level use only).

        Suitable between top-level nodes and before/after close tags.
        Do NOT use inside inline element content — it eats meaningful whitespace.
        """
        while True:
            self._skip_blanks()
            m = _RE_COMMENT.match(self.source, self.pos)
            if m:
                self._advance(len(m.group()))
            else:
                break

    def _skip_inline_comments(self) -> None:
        """Skip {# ... #} Jinja comments WITHOUT consuming surrounding whitespace.

        Safe to use inside element children where inline whitespace is significant.
        """
        while True:
            m = _RE_COMMENT.match(self.source, self.pos)
            if m:
                self._advance(len(m.group()))
            else:
                break

    def _consume_until_newline(self) -> str:
        parts: list[str] = []
        while not self._at_end() and self._peek() != "\n":
            parts.append(self._advance())
        if not self._at_end():
            self._advance()  # consume newline
        return "".join(parts)

    def _err(self, msg: str, line: int | None = None) -> None:
        raise ParseError(msg, file=self.filename, line=line or self.line)


# ── Public API ────────────────────────────────────────────────────────────────


def parse(source: str, filename: str = "<string>") -> PjxFile:
    return Parser(source, filename).parse()
