"""Scoped CSS — hash-based selector prefixing for PJX components."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Hash generation
# ---------------------------------------------------------------------------


def generate_scope_hash(path: Path) -> str:
    """Generate a deterministic 7-char hash for a component path.

    Args:
        path: Component file path (used as the hash input).

    Returns:
        A 7-character hex string derived from SHA-256.
    """
    digest = hashlib.sha256(str(path).encode()).hexdigest()
    return digest[:7]


# ---------------------------------------------------------------------------
# CSS scoping
# ---------------------------------------------------------------------------

# Matches a CSS selector (simplistic: everything before `{`)
_RULE_RE = re.compile(
    r"""
    (?P<atrule>@[^{]+)\{       # @media / @keyframes etc.
    |
    (?P<selectors>[^{}@]+)\{    # normal selectors
    """,
    re.VERBOSE,
)

_SELECTOR_SPLIT_RE = re.compile(r"\s*,\s*")


def scope_css(css_source: str, scope_hash: str) -> str:
    """Prefix all CSS selectors with a scoping attribute selector.

    Args:
        css_source: Raw CSS text.
        scope_hash: The 7-char hash to use for scoping.

    Returns:
        CSS with all selectors prefixed by ``[data-pjx-{hash}]``.
    """
    attr = f"[data-pjx-{scope_hash}]"
    return _scope_block(css_source, attr)


def _scope_block(css: str, attr: str, *, skip_scope: bool = False) -> str:
    """Recursively scope CSS, handling nested at-rules."""
    result: list[str] = []
    pos = 0

    while pos < len(css):
        m = _RULE_RE.search(css, pos)
        if m is None:
            result.append(css[pos:])
            break

        # Text before the match (whitespace, etc.)
        result.append(css[pos : m.start()])

        if m.group("atrule"):
            # At-rule: find its block and recurse
            atrule = m.group("atrule")
            block_start = m.end()
            block_end = _find_closing_brace(css, block_start)
            inner = css[block_start:block_end]
            # Don't scope selectors inside @keyframes — they use
            # keywords (from/to/percentages), not real selectors.
            is_keyframes = atrule.strip().startswith("@keyframes")
            scoped_inner = _scope_block(inner, attr, skip_scope=is_keyframes)
            result.append(f"{atrule}{{{scoped_inner}}}")
            pos = block_end + 1
        else:
            # Normal rule: scope selectors, copy block verbatim
            selectors_raw = m.group("selectors").strip()
            block_start = m.end()
            block_end = _find_closing_brace(css, block_start)
            block = css[block_start:block_end]

            if skip_scope:
                result.append(f"{selectors_raw} {{{block}}}")
            else:
                scoped_selectors = ", ".join(
                    _scope_selector(sel.strip(), attr)
                    for sel in _SELECTOR_SPLIT_RE.split(selectors_raw)
                )
                result.append(f"{scoped_selectors} {{{block}}}")
            pos = block_end + 1

    return "".join(result)


_COMBINATORS_RE = re.compile(r"(?<=[^\s>+~])([>+~])(?=[^\s>+~])")


def _scope_selector(selector: str, attr: str) -> str:
    """Append the scoping attribute to every simple selector in a compound selector.

    For example: ``.card .title`` → ``.card[data-pjx-abc] .title[data-pjx-abc]``

    This ensures the scope matches the element itself (Vue-style), not just
    descendants.
    """
    # Normalize combinators without spaces: `.a>.b` → `.a > .b`
    selector = _COMBINATORS_RE.sub(r" \1 ", selector)
    parts = selector.split()
    scoped = " ".join(
        f"{part}{attr}" if part not in {">", "+", "~"} else part
        for part in parts
        if part
    )
    return scoped


def _find_closing_brace(css: str, start: int) -> int:
    """Find the matching closing ``}`` starting from *inside* the block."""
    depth = 1
    pos = start
    while pos < len(css):
        if css[pos] == "{":
            depth += 1
        elif css[pos] == "}":
            depth -= 1
            if depth == 0:
                return pos
        pos += 1
    return len(css)
