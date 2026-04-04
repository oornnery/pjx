from __future__ import annotations

import re

from pjx.core.pipeline import ProcessorContext, ProcessorResult

# Match {expr} in attribute values, but NOT {{ expr }} (Jinja) or {% %} (Jinja tags)
# This regex finds attr="...{expr}..." or attr={expr} patterns
ATTR_EXPR_RE = re.compile(
    r"""
    ([\w:.\-@]+)            # attribute name
    \s*=\s*                  # equals sign
    \{                       # opening brace
    (?!\{)                   # NOT followed by another { (would be Jinja {{ }})
    ([^}]+)                  # expression content
    \}                       # closing brace
    (?!\})                   # NOT followed by another } (would be Jinja {{ }})
    """,
    re.VERBOSE,
)


class ExpressionProcessor:
    def process(self, source: str, ctx: ProcessorContext) -> ProcessorResult:
        result = ATTR_EXPR_RE.sub(self._replace_expr, source)
        return ProcessorResult(source=result)

    def _replace_expr(self, match: re.Match) -> str:
        attr_name = match.group(1)
        expr = match.group(2).strip()
        return f'{attr_name}="{{{{ {expr} }}}}"'
