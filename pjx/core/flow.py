from __future__ import annotations

import re

from pjx.core.pipeline import ProcessorContext, ProcessorResult
from pjx.errors import PJXError, SourceLocation

FOR_EACH_RE = re.compile(r"each\s*=\s*\{([^}]+)\}")
FOR_AS_RE = re.compile(r'as\s*=\s*"([^"]+)"')
SHOW_WHEN_RE = re.compile(r"when\s*=\s*\{([^}]+)\}")
SWITCH_EXPR_RE = re.compile(r"expr\s*=\s*\{([^}]+)\}")
CASE_VALUE_RE = re.compile(r'value\s*=\s*"([^"]*)"')


class ControlFlowProcessor:
    def process(self, source: str, ctx: ProcessorContext) -> ProcessorResult:
        result = source
        result = self._process_for(result, ctx)
        result = self._process_show(result, ctx)
        result = self._process_switch(result, ctx)
        return ProcessorResult(source=result)

    def _process_for(self, source: str, ctx: ProcessorContext) -> str:
        result = source
        result = re.sub(
            r"<For\s+([^>]+?)(?:\s*/)?>",
            self._replace_for_open,
            result,
        )
        result = result.replace("</For>", "{% endfor %}")
        return result

    def _replace_for_open(self, match: re.Match) -> str:
        attrs = match.group(1)
        each_match = FOR_EACH_RE.search(attrs)
        as_match = FOR_AS_RE.search(attrs)
        if not each_match:
            raise PJXError(
                "Tag <For> requer atributo 'each'",
                SourceLocation(None, 0, 0),
                code="PJX101",
                hint='use <For each={items} as="item">',
            )
        if not as_match:
            raise PJXError(
                "Tag <For> requer atributo 'as'",
                SourceLocation(None, 0, 0),
                code="PJX102",
                hint='use <For each={items} as="item">',
            )
        iterable = each_match.group(1).strip()
        var_name = as_match.group(1).strip()
        return f"{{% for {var_name} in {iterable} %}}"

    def _process_show(self, source: str, ctx: ProcessorContext) -> str:
        result = source
        result = re.sub(
            r"<Show\s+([^>]*?)(?:\s*/)?>",
            self._replace_show_open,
            result,
        )
        result = re.sub(r"<Show\s*>", self._raise_show_no_when, result)
        result = result.replace("</Show>", "{% endif %}")
        result = re.sub(r"<Else\s*/?>", "{% else %}", result)
        result = result.replace("</Else>", "")
        return result

    def _raise_show_no_when(self, match: re.Match) -> str:
        raise PJXError(
            "Tag <Show> requer atributo 'when'",
            SourceLocation(None, 0, 0),
            code="PJX103",
            hint="use <Show when={condition}>",
        )

    def _replace_show_open(self, match: re.Match) -> str:
        attrs = match.group(1)
        when_match = SHOW_WHEN_RE.search(attrs)
        if not when_match:
            raise PJXError(
                "Tag <Show> requer atributo 'when'",
                SourceLocation(None, 0, 0),
                code="PJX103",
                hint="use <Show when={condition}>",
            )
        condition = when_match.group(1).strip()
        return f"{{% if {condition} %}}"

    def _process_switch(self, source: str, ctx: ProcessorContext) -> str:
        result = []
        lines = source.split("\n")
        switch_stack: list[str] = []
        case_count_stack: list[int] = []

        for line in lines:
            stripped = line.strip()

            switch_match = re.search(r"<Switch\s*([^>]*)>", stripped)
            if switch_match:
                attrs = switch_match.group(1).strip()
                expr_match = SWITCH_EXPR_RE.search(attrs) if attrs else None
                if not expr_match:
                    raise PJXError(
                        "Tag <Switch> requer atributo 'expr'",
                        SourceLocation(None, 0, 0),
                        code="PJX104",
                        hint="use <Switch expr={value}>",
                    )
                switch_stack.append(expr_match.group(1).strip())
                case_count_stack.append(0)
                continue

            if re.search(r"</Switch\s*>", stripped):
                if switch_stack:
                    switch_stack.pop()
                    case_count_stack.pop()
                indent = line[: len(line) - len(line.lstrip())]
                result.append(f"{indent}{{% endif %}}")
                continue

            case_match = re.search(r"<Case\s+([^>]+?)>", stripped)
            if case_match and switch_stack:
                attrs = case_match.group(1)
                value_match = CASE_VALUE_RE.search(attrs)
                if not value_match:
                    raise PJXError(
                        "Tag <Case> requer atributo 'value'",
                        SourceLocation(None, 0, 0),
                        code="PJX105",
                    )
                value = value_match.group(1)
                expr = switch_stack[-1]
                count = case_count_stack[-1]
                indent = line[: len(line) - len(line.lstrip())]
                keyword = "if" if count == 0 else "elif"
                result.append(f'{indent}{{% {keyword} {expr} == "{value}" %}}')
                case_count_stack[-1] = count + 1
                continue

            if re.search(r"</Case\s*>", stripped):
                continue

            if re.search(r"<Default\s*/?>", stripped):
                indent = line[: len(line) - len(line.lstrip())]
                result.append(f"{indent}{{% else %}}")
                continue

            if re.search(r"</Default\s*>", stripped):
                continue

            result.append(line)

        return "\n".join(result)
