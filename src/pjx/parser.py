"""PJX parser — transforms ``.jinja`` source into a :class:`Component` AST.

Pipeline::

    source text
      → _extract_blocks()  → frontmatter, style, body
      → lexer.tokenize()   → tokens
      → _parse_script()    → declarations
      → _parse_body()      → node tree
      → Component AST
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from pjx.ast_nodes import (
    AssetDecl,
    AwaitNode,
    CaseNode,
    Component,
    ComponentNode,
    ComputedDecl,
    ConstDecl,
    ElementNode,
    ErrorBoundaryNode,
    ExprNode,
    ExtendsDecl,
    ForNode,
    FragmentNode,
    FromImportDecl,
    ImportDecl,
    LetDecl,
    MiddlewareDecl,
    Node,
    PortalNode,
    PropField,
    PropsDecl,
    ShowNode,
    SlotDecl,
    SlotPassNode,
    SlotRenderNode,
    StateDecl,
    StoreDecl,
    SwitchNode,
    TeleportNode,
    TextNode,
    TransitionGroupNode,
    TransitionNode,
)
from pjx.errors import ParseError
from pjx.lexer import Token, TokenKind, tokenize

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse(source: str, path: Path | None = None) -> Component:
    """Parse a ``.jinja`` component source string into a Component AST.

    Args:
        source: Full file contents.
        path: Optional file path for error messages.

    Returns:
        Parsed :class:`Component` AST.
    """
    path = path or Path("<string>")
    frontmatter, style, body = _extract_blocks(source)

    # Parse frontmatter declarations
    extends = None
    from_imports: list[FromImportDecl] = []
    imports: list[ImportDecl] = []
    props: PropsDecl | None = None
    slots: list[SlotDecl] = []
    stores: list[StoreDecl] = []
    assets: list[AssetDecl] = []
    variables: list[LetDecl | ConstDecl] = []
    states: list[StateDecl] = []
    computed: list[ComputedDecl] = []
    middleware: list[MiddlewareDecl] = []

    if frontmatter is not None:
        tokens = tokenize(frontmatter)
        parser = _ScriptParser(tokens, path)
        while not parser.at_end():
            parser.skip_newlines()
            if parser.at_end():
                break
            decl = parser.parse_statement()
            if isinstance(decl, ExtendsDecl):
                extends = decl
            elif isinstance(decl, FromImportDecl):
                from_imports.append(decl)
            elif isinstance(decl, ImportDecl):
                imports.append(decl)
            elif isinstance(decl, PropsDecl):
                props = decl
            elif isinstance(decl, SlotDecl):
                slots.append(decl)
            elif isinstance(decl, StoreDecl):
                stores.append(decl)
            elif isinstance(decl, AssetDecl):
                assets.append(decl)
            elif isinstance(decl, (LetDecl, ConstDecl)):
                variables.append(decl)
            elif isinstance(decl, StateDecl):
                states.append(decl)
            elif isinstance(decl, ComputedDecl):
                computed.append(decl)
            elif isinstance(decl, MiddlewareDecl):
                middleware.append(decl)

    # Collect known component names for body parser
    known: set[str] = set()
    for imp in imports:
        known.update(imp.names)

    body_nodes = _parse_body(body, known) if body.strip() else ()

    return Component(
        path=path,
        extends=extends,
        from_imports=tuple(from_imports),
        imports=tuple(imports),
        props=props,
        slots=tuple(slots),
        stores=tuple(stores),
        assets=tuple(assets),
        middleware=tuple(middleware),
        variables=tuple(variables),
        states=tuple(states),
        computed=tuple(computed),
        body=body_nodes,
        style=style,
    )


def parse_file(path: Path) -> Component:
    """Read and parse a ``.jinja`` file."""
    return parse(path.read_text(encoding="utf-8"), path)


# ---------------------------------------------------------------------------
# Block extraction
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"\A\s*---\n(.*?)\n---\n?", re.DOTALL)
_STYLE_RE = re.compile(r"<style\s+scoped\s*>(.*?)</style>", re.DOTALL)


def _extract_blocks(source: str) -> tuple[str | None, str | None, str]:
    """Split source into (frontmatter, style, body).

    Returns:
        Tuple of (frontmatter_text | None, style_css | None, body_html).
    """
    frontmatter: str | None = None
    rest = source

    fm_match = _FRONTMATTER_RE.match(source)
    if fm_match:
        frontmatter = fm_match.group(1)
        rest = source[fm_match.end() :]

    style: str | None = None
    style_match = _STYLE_RE.search(rest)
    if style_match:
        style = style_match.group(1).strip()
        rest = rest[: style_match.start()] + rest[style_match.end() :]

    return frontmatter, style, rest.strip()


# ---------------------------------------------------------------------------
# Frontmatter (script) parser — recursive descent on token stream
# ---------------------------------------------------------------------------

# Declaration type alias
_Decl = (
    ExtendsDecl
    | FromImportDecl
    | ImportDecl
    | PropsDecl
    | SlotDecl
    | StoreDecl
    | AssetDecl
    | LetDecl
    | ConstDecl
    | StateDecl
    | ComputedDecl
    | MiddlewareDecl
)


class _ScriptParser:
    """LL(1) recursive-descent parser for PJX frontmatter tokens."""

    def __init__(self, tokens: list[Token], path: Path) -> None:
        self._tokens = tokens
        self._pos = 0
        self._path = path

    # -- helpers --

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _expect(self, kind: TokenKind) -> Token:
        tok = self._peek()
        if tok.kind != kind:
            raise ParseError(
                f"expected {kind.value!r}, got {tok.kind.value!r} ({tok.value!r})",
                path=self._path,
                line=tok.line,
                col=tok.col,
            )
        return self._advance()

    def at_end(self) -> bool:
        return self._peek().kind == TokenKind.EOF

    def skip_newlines(self) -> None:
        while self._peek().kind == TokenKind.NEWLINE:
            self._advance()

    # -- statements --

    def parse_statement(self) -> _Decl:
        tok = self._peek()
        match tok.kind:
            case TokenKind.EXTENDS:
                return self._parse_extends()
            case TokenKind.FROM:
                return self._parse_from_import()
            case TokenKind.IMPORT:
                return self._parse_import()
            case TokenKind.PROPS:
                return self._parse_props()
            case TokenKind.SLOT:
                return self._parse_slot()
            case TokenKind.STORE:
                return self._parse_store()
            case TokenKind.LET:
                return self._parse_let()
            case TokenKind.CONST:
                return self._parse_const()
            case TokenKind.STATE:
                return self._parse_state()
            case TokenKind.COMPUTED:
                return self._parse_computed()
            case TokenKind.CSS:
                return self._parse_asset("css")
            case TokenKind.JS:
                return self._parse_asset("js")
            case TokenKind.MIDDLEWARE:
                return self._parse_middleware()
            case _:
                raise ParseError(
                    f"unexpected token {tok.value!r}",
                    path=self._path,
                    line=tok.line,
                    col=tok.col,
                )

    def _parse_extends(self) -> ExtendsDecl:
        self._advance()  # consume 'extends'
        src = self._expect(TokenKind.STRING)
        return ExtendsDecl(source=src.value)

    def _parse_from_import(self) -> FromImportDecl:
        self._advance()  # consume 'from'
        module = self._parse_dotted_name()
        self._expect(TokenKind.IMPORT)
        names = [self._expect(TokenKind.IDENT).value]
        while self._peek().kind == TokenKind.COMMA:
            self._advance()
            names.append(self._expect(TokenKind.IDENT).value)
        return FromImportDecl(module=module, names=tuple(names))

    def _parse_dotted_name(self) -> str:
        parts = [self._expect(TokenKind.IDENT).value]
        while self._peek().kind == TokenKind.DOT:
            self._advance()
            parts.append(self._expect(TokenKind.IDENT).value)
        return ".".join(parts)

    def _parse_import(self) -> ImportDecl:
        self._advance()  # consume 'import'
        tok = self._peek()

        # Wildcard: import * from "..."
        if tok.kind == TokenKind.STAR:
            self._advance()
            self._expect(TokenKind.FROM)
            src = self._expect(TokenKind.STRING)
            return ImportDecl(names=(), source=src.value, wildcard=True)

        # Named: import { A, B } from "..."
        if tok.kind == TokenKind.LBRACE:
            self._advance()
            names = [self._expect(TokenKind.IDENT).value]
            while self._peek().kind == TokenKind.COMMA:
                self._advance()
                names.append(self._expect(TokenKind.IDENT).value)
            self._expect(TokenKind.RBRACE)
            self._expect(TokenKind.FROM)
            src = self._expect(TokenKind.STRING)
            return ImportDecl(names=tuple(names), source=src.value)

        # Default: import Name from "..." [as Alias]
        name = self._expect(TokenKind.IDENT)
        self._expect(TokenKind.FROM)
        src = self._expect(TokenKind.STRING)
        alias: str | None = None
        if self._peek().kind == TokenKind.AS:
            self._advance()
            alias = self._expect(TokenKind.IDENT).value
        return ImportDecl(names=(name.value,), source=src.value, alias=alias)

    def _parse_props(self) -> PropsDecl:
        self._advance()  # consume 'props'
        name = ""
        if self._peek().kind == TokenKind.IDENT:
            name = self._advance().value
            self._expect(TokenKind.EQUALS)
        self._expect(TokenKind.LBRACE)
        self.skip_newlines()
        fields: list[PropField] = []
        while self._peek().kind != TokenKind.RBRACE:
            fields.append(self._parse_prop_field())
            if self._peek().kind == TokenKind.COMMA:
                self._advance()
            self.skip_newlines()
        self._expect(TokenKind.RBRACE)
        return PropsDecl(name=name, fields=tuple(fields))

    def _parse_prop_field(self) -> PropField:
        name = self._expect(TokenKind.IDENT).value
        self._expect(TokenKind.COLON)
        type_expr = self._parse_type_expr()
        default: str | None = None
        if self._peek().kind == TokenKind.EQUALS:
            self._advance()
            default = self._parse_expr()
        return PropField(name=name, type_expr=type_expr, default=default)

    def _parse_type_expr(self) -> str:
        """Parse a type expression like ``str | None``, ``list[str]``, ``Literal["a"]``."""
        parts = [self._parse_single_type()]
        while self._peek().kind == TokenKind.PIPE:
            self._advance()
            parts.append(self._parse_single_type())
        return " | ".join(parts)

    def _parse_single_type(self) -> str:
        tok = self._expect(TokenKind.IDENT)
        result = tok.value
        if self._peek().kind == TokenKind.LBRACKET:
            self._advance()
            args = [self._parse_type_or_expr()]
            while self._peek().kind == TokenKind.COMMA:
                self._advance()
                args.append(self._parse_type_or_expr())
            self._expect(TokenKind.RBRACKET)
            result += f"[{', '.join(args)}]"
        return result

    def _parse_type_or_expr(self) -> str:
        """Parse either a type expression or a value expression inside brackets."""
        tok = self._peek()
        if tok.kind == TokenKind.STRING:
            self._advance()
            return f'"{tok.value}"'
        if tok.kind == TokenKind.NUMBER:
            self._advance()
            return tok.value
        if tok.kind == TokenKind.IDENT:
            return self._parse_single_type()
        # For more complex expressions, collect until comma/bracket
        return self._parse_expr()

    def _parse_expr(self) -> str:
        """Parse a value expression — collect tokens until statement boundary."""
        parts: list[str] = []
        depth = 0
        while True:
            tok = self._peek()
            if tok.kind in (TokenKind.EOF, TokenKind.NEWLINE):
                break
            if tok.kind == TokenKind.COMMA and depth == 0:
                break
            if tok.kind == TokenKind.RBRACE and depth == 0:
                break
            if tok.kind in (TokenKind.LBRACE, TokenKind.LBRACKET, TokenKind.LPAREN):
                depth += 1
            elif tok.kind in (TokenKind.RBRACE, TokenKind.RBRACKET, TokenKind.RPAREN):
                depth -= 1
                if depth < 0:
                    break
            self._advance()
            if tok.kind == TokenKind.STRING:
                parts.append(f'"{tok.value}"')
            else:
                parts.append(tok.value)
        return " ".join(parts)

    def _parse_slot(self) -> SlotDecl:
        self._advance()  # consume 'slot'
        name = self._expect(TokenKind.IDENT).value
        fallback: str | None = None
        if self._peek().kind == TokenKind.EQUALS:
            self._advance()
            fallback = self._parse_expr()
        return SlotDecl(name=name, fallback=fallback)

    def _parse_store(self) -> StoreDecl:
        self._advance()  # consume 'store'
        name = self._expect(TokenKind.IDENT).value
        self._expect(TokenKind.EQUALS)
        # Collect JS object literal
        value = self._parse_expr()
        return StoreDecl(name=name, value=value)

    def _parse_let(self) -> LetDecl:
        self._advance()
        name = self._expect(TokenKind.IDENT).value
        self._expect(TokenKind.EQUALS)
        return LetDecl(name=name, expr=self._parse_expr())

    def _parse_const(self) -> ConstDecl:
        self._advance()
        name = self._expect(TokenKind.IDENT).value
        self._expect(TokenKind.EQUALS)
        return ConstDecl(name=name, expr=self._parse_expr())

    def _parse_state(self) -> StateDecl:
        self._advance()
        name = self._expect(TokenKind.IDENT).value
        self._expect(TokenKind.EQUALS)
        return StateDecl(name=name, value=self._parse_expr())

    def _parse_computed(self) -> ComputedDecl:
        self._advance()
        name = self._expect(TokenKind.IDENT).value
        self._expect(TokenKind.EQUALS)
        return ComputedDecl(name=name, expr=self._parse_expr())

    def _parse_asset(self, kind: str) -> AssetDecl:
        self._advance()  # consume 'css' or 'js'
        path = self._expect(TokenKind.STRING).value
        return AssetDecl(kind=kind, path=path)

    def _parse_middleware(self) -> MiddlewareDecl:
        """Parse ``middleware "auth", "rate_limit"``."""
        self._advance()  # consume 'middleware'
        names: list[str] = [self._expect(TokenKind.STRING).value]
        while self._peek().kind == TokenKind.COMMA:
            self._advance()
            names.append(self._expect(TokenKind.STRING).value)
        return MiddlewareDecl(names=tuple(names))


# ---------------------------------------------------------------------------
# Body parser — HTML with PJX extensions
# ---------------------------------------------------------------------------

# Control flow tags that map to specific AST nodes
_CONTROL_TAGS = frozenset(
    {
        "Show",
        "For",
        "Switch",
        "Case",
        "Portal",
        "ErrorBoundary",
        "Await",
        "Transition",
        "TransitionGroup",
        "Fragment",
        "Teleport",
    }
)

# Self-closing HTML tags
_VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

_EXPR_RE = re.compile(r"\{\{(.+?)\}\}")

# Matches {% ... %} blocks (non-greedy).
_JINJA_BLOCK_RE = re.compile(r"\{%.*?%\}", re.DOTALL)


def _find_tag_end(html: str, start: int) -> int:
    """Find the closing ``>`` of an HTML tag, respecting quotes and ``{% %}`` blocks.

    Args:
        html: Full HTML source.
        start: Index of the opening ``<``.

    Returns:
        Index of the closing ``>`` or ``-1`` if not found.
    """
    i = start + 1
    in_single = False
    in_double = False
    in_jinja = False
    while i < len(html):
        if in_jinja:
            if html[i : i + 2] == "%}":
                in_jinja = False
                i += 2
                continue
        elif in_single:
            if html[i] == "'":
                in_single = False
        elif in_double:
            if html[i] == '"':
                in_double = False
        elif html[i : i + 2] == "{%":
            in_jinja = True
            i += 2
            continue
        elif html[i] == "'":
            in_single = True
        elif html[i] == '"':
            in_double = True
        elif html[i] == ">":
            return i
        i += 1
    return -1


def _has_unquoted_jinja_block(tag_text: str) -> bool:
    """Check if an HTML opening tag contains ``{% %}`` outside of attribute quotes."""
    in_single = False
    in_double = False
    i = 0
    while i < len(tag_text):
        c = tag_text[i]
        if in_single:
            if c == "'":
                in_single = False
        elif in_double:
            if c == '"':
                in_double = False
        elif c == "'":
            in_single = True
        elif c == '"':
            in_double = True
        elif tag_text[i : i + 2] == "{%":
            return True
        i += 1
    return False


def _rewrite_tag_with_jinja(tag_text: str) -> str:
    """Strip unquoted ``{% %}`` blocks from an HTML tag and emit them before it.

    This is intentionally lossy — conditional attributes lose their
    wrapping logic — but it prevents :class:`~html.parser.HTMLParser` from
    silently dropping the entire element tree.  Template authors should
    place ``{% %}`` blocks inside quoted attribute values or use PJX
    control-flow components instead.
    """
    m = re.match(r"<([a-zA-Z][a-zA-Z0-9]*)", tag_text)
    if not m:
        return tag_text
    tag_name = m.group(1)
    rest = tag_text[m.end() : -1]  # between tagname and closing >

    blocks: list[str] = []
    parts: list[str] = []
    i = 0
    frag_start = 0
    in_single = False
    in_double = False
    while i < len(rest):
        c = rest[i]
        if in_single:
            if c == "'":
                in_single = False
        elif in_double:
            if c == '"':
                in_double = False
        elif c == "'":
            in_single = True
        elif c == '"':
            in_double = True
        elif rest[i : i + 2] == "{%":
            if i > frag_start:
                parts.append(rest[frag_start:i])
            end = rest.find("%}", i + 2)
            if end >= 0:
                blocks.append(rest[i : end + 2])
                i = end + 2
                frag_start = i
                continue
        i += 1
    if frag_start < len(rest):
        parts.append(rest[frag_start:])

    clean_attrs = "".join(parts).strip()
    prefix = "".join(blocks)
    tag_out = f"<{tag_name} {clean_attrs}>" if clean_attrs else f"<{tag_name}>"
    return f"{prefix}{tag_out}"


def _extract_jinja_from_tags(html: str) -> str:
    """Move ``{% ... %}`` blocks out of HTML opening tags.

    Python's :class:`~html.parser.HTMLParser` cannot parse Jinja2 block
    syntax (``{% ... %}``) embedded inside an HTML opening tag (e.g.
    ``<body{% if X %} attr{% endif %}>``).  The block becomes part of the
    tag name and the parser silently drops the entire element tree.

    ``{% ... %}`` inside quoted attribute values is fine and left untouched.
    """
    i = 0
    out: list[str] = []
    while i < len(html):
        if html[i] == "<" and i + 1 < len(html) and html[i + 1 : i + 2].isalpha():
            tag_end = _find_tag_end(html, i)
            if tag_end >= 0:
                tag_text = html[i : tag_end + 1]
                if _has_unquoted_jinja_block(tag_text):
                    out.append(_rewrite_tag_with_jinja(tag_text))
                else:
                    out.append(tag_text)
                i = tag_end + 1
                continue
        out.append(html[i])
        i += 1
    return "".join(out)


def _parse_body(html: str, known_components: set[str]) -> tuple[Node, ...]:
    """Parse HTML body into AST nodes."""
    html = _extract_jinja_from_tags(html)
    parser = _BodyParser(known_components)
    parser.feed(html)
    return tuple(parser.root_nodes())


class _BodyParser(HTMLParser):
    """HTMLParser subclass that builds PJX AST nodes.

    Overrides tag handling to preserve the original case of tag names,
    since ``HTMLParser`` lowercases everything by default.
    """

    CDATA_CONTENT_ELEMENTS = ()  # ty: ignore[override-of-final-variable]

    def __init__(self, known_components: set[str]) -> None:
        from pjx.layout import LAYOUT_COMPONENTS

        super().__init__(convert_charrefs=False)
        self._known = known_components | _CONTROL_TAGS | LAYOUT_COMPONENTS
        self._stack: list[_OpenTag] = []
        self._root: list[Node] = []
        self._original_source: str = ""

    def feed(self, data: str) -> None:
        self._original_source = data
        super().feed(data)

    def get_starttag_text(self) -> str | None:  # noqa: N802
        return super().get_starttag_text()

    def _recover_tag_name(self, lowered_tag: str) -> str:
        """Recover the original-case tag name from the source.

        Uses a position cursor per tag to avoid O(n*m) re-scanning.
        Compiles each tag regex once and caches it.
        """
        if not hasattr(self, "_last_positions"):
            self._last_positions: dict[str, int] = {}
        if not hasattr(self, "_tag_re_cache"):
            self._tag_re_cache: dict[str, re.Pattern[str]] = {}

        if lowered_tag not in self._tag_re_cache:
            self._tag_re_cache[lowered_tag] = re.compile(
                rf"</?({re.escape(lowered_tag)})\b", re.IGNORECASE
            )
        tag_re = self._tag_re_cache[lowered_tag]
        start_from = self._last_positions.get(lowered_tag, 0)

        m = tag_re.search(self._original_source, pos=start_from)
        if m and m.group(1).lower() == lowered_tag:
            self._last_positions[lowered_tag] = m.start() + 1
            return m.group(1)
        return lowered_tag

    def root_nodes(self) -> list[Node]:
        return self._root

    def _current_children(self) -> list[Node]:
        if self._stack:
            return self._stack[-1].children
        return self._root

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = self._recover_tag_name(tag)
        attr_dict: dict[str, str | bool] = {}
        spread: str | None = None
        for name, value in attrs:
            if name.startswith("..."):
                spread = name[3:]
                continue
            attr_dict[name] = value if value is not None else True

        is_void = tag.lower() in _VOID_ELEMENTS

        if is_void:
            node = self._make_node(tag, attr_dict, (), spread)
            self._current_children().append(node)
        else:
            self._stack.append(_OpenTag(tag, attr_dict, spread=spread))

    def handle_endtag(self, tag: str) -> None:
        tag = self._recover_tag_name(tag)
        if not self._stack:
            return
        # Find matching open tag (case-insensitive match for HTML compat)
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i].tag.lower() == tag.lower():
                break
        else:
            return

        open_tag = self._stack.pop(i)
        children = tuple(open_tag.children)
        node = self._make_node(open_tag.tag, open_tag.attrs, children, open_tag.spread)
        self._current_children().append(node)

    def handle_data(self, data: str) -> None:
        nodes = self._parse_text_with_exprs(data)
        self._current_children().extend(nodes)

    def handle_entityref(self, name: str) -> None:
        self._current_children().append(TextNode(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self._current_children().append(TextNode(f"&#{name};"))

    def handle_comment(self, data: str) -> None:
        self._current_children().append(TextNode(f"<!--{data}-->"))

    def handle_decl(self, decl: str) -> None:
        self._current_children().append(TextNode(f"<!{decl}>"))

    def _parse_text_with_exprs(self, text: str) -> list[Node]:
        """Split text containing ``{{ expr }}`` into TextNode/ExprNode."""
        nodes: list[Node] = []
        last = 0
        for m in _EXPR_RE.finditer(text):
            if m.start() > last:
                nodes.append(TextNode(text[last : m.start()]))
            nodes.append(ExprNode(m.group(1).strip()))
            last = m.end()
        if last < len(text):
            nodes.append(TextNode(text[last:]))
        return nodes

    def _make_node(
        self,
        tag: str,
        attrs: dict[str, str | bool],
        children: tuple[Node, ...],
        spread: str | None = None,
    ) -> Node:
        """Create the appropriate AST node for a tag."""
        # Slot render: <Slot /> (default), <Slot:name /> or <Slot:name>fallback</Slot:name>
        if tag == "Slot":
            return SlotRenderNode(name="default", fallback=children or None)
        if tag.startswith("Slot:"):
            slot_name = tag[5:]
            return SlotRenderNode(name=slot_name, fallback=children or None)

        # Slot pass: <slot:name>content</slot:name>
        if tag.startswith("slot:"):
            slot_name = tag[5:]
            return SlotPassNode(name=slot_name, content=children)

        # Control flow tags
        if tag in _CONTROL_TAGS:
            return self._make_control_node(tag, attrs, children)

        # PascalCase = component (but not control flow tags)
        if tag[0:1].isupper() and tag in self._known and tag not in _CONTROL_TAGS:
            return self._make_component_node(tag, attrs, children, spread)

        # Regular HTML element
        return ElementNode(
            tag=tag,
            attrs=attrs,
            children=children,
            self_closing=not children and tag in _VOID_ELEMENTS,
        )

    def _make_control_node(
        self,
        tag: str,
        attrs: dict[str, str | bool],
        children: tuple[Node, ...],
    ) -> Node:
        match tag:
            case "Show":
                when = str(attrs.get("when", ""))
                fallback_nodes: tuple[Node, ...] | None = None
                body_nodes: list[Node] = []
                for child in children:
                    if isinstance(child, ElementNode) and child.tag == "Else":
                        fallback_nodes = child.children
                    else:
                        body_nodes.append(child)
                return ShowNode(
                    when=when,
                    body=tuple(body_nodes),
                    fallback=fallback_nodes,
                )

            case "For":
                each = str(attrs.get("each", ""))
                as_var = str(attrs.get("as", "item"))
                empty_nodes: tuple[Node, ...] | None = None
                body_list: list[Node] = []
                for child in children:
                    if isinstance(child, ElementNode) and child.tag == "Empty":
                        empty_nodes = child.children
                    else:
                        body_list.append(child)
                return ForNode(
                    each=each,
                    as_var=as_var,
                    body=tuple(body_list),
                    empty=empty_nodes,
                )

            case "Switch":
                on = str(attrs.get("on", ""))
                cases: list[CaseNode] = []
                default: tuple[Node, ...] | None = None
                for child in children:
                    if isinstance(child, CaseNode):
                        cases.append(child)
                    elif isinstance(child, ElementNode) and child.tag == "Default":
                        default = child.children
                return SwitchNode(on=on, cases=tuple(cases), default=default)

            case "Case":
                value = str(attrs.get("value", ""))
                return CaseNode(value=value, body=children)

            case "Portal":
                target = str(attrs.get("target", ""))
                swap = str(attrs.get("swap", "innerHTML"))
                return PortalNode(target=target, swap=swap, body=children)

            case "ErrorBoundary":
                fallback = str(attrs.get("fallback", ""))
                error_slot = attrs.get("error_slot")
                return ErrorBoundaryNode(
                    fallback=fallback,
                    body=children,
                    error_slot=str(error_slot) if error_slot else None,
                )

            case "Await":
                src = str(attrs.get("src", ""))
                trigger = str(attrs.get("trigger", "load"))
                loading_nodes: tuple[Node, ...] | None = None
                error_nodes: tuple[Node, ...] | None = None
                for child in children:
                    if isinstance(child, ElementNode) and child.tag == "Loading":
                        loading_nodes = child.children
                    elif isinstance(child, ElementNode) and child.tag == "Error":
                        error_nodes = child.children
                return AwaitNode(
                    src=src, trigger=trigger, loading=loading_nodes, error=error_nodes
                )

            case "Transition":
                enter = str(attrs.get("enter", ""))
                leave = str(attrs.get("leave", ""))
                return TransitionNode(enter=enter, leave=leave, body=children)

            case "TransitionGroup":
                return TransitionGroupNode(
                    tag=str(attrs.get("tag", "div")),
                    enter=str(attrs.get("enter", "")),
                    leave=str(attrs.get("leave", "")),
                    move=str(attrs.get("move", "")),
                    body=children,
                )

            case "Fragment":
                return FragmentNode(children=children)

            case "Teleport":
                to = str(attrs.get("to", ""))
                return TeleportNode(to=to, body=children)

            case _:
                return ElementNode(tag=tag, attrs=attrs, children=children)

    def _make_component_node(
        self,
        tag: str,
        attrs: dict[str, str | bool],
        children: tuple[Node, ...],
        spread: str | None,
    ) -> ComponentNode:
        """Build a ComponentNode, extracting slot passes from children."""
        slot_passes: dict[str, tuple[Node, ...]] = {}
        remaining: list[Node] = []
        for child in children:
            if isinstance(child, SlotPassNode):
                slot_passes[child.name] = child.content
            else:
                remaining.append(child)
        return ComponentNode(
            name=tag,
            attrs=attrs,
            children=tuple(remaining),
            slots=slot_passes,
            spread=spread,
        )


class _OpenTag:
    """Tracks an open tag on the parser stack."""

    __slots__ = ("tag", "attrs", "children", "spread")

    def __init__(
        self,
        tag: str,
        attrs: dict[str, str | bool],
        spread: str | None = None,
    ) -> None:
        self.tag = tag
        self.attrs = attrs
        self.children: list[Node] = []
        self.spread = spread
