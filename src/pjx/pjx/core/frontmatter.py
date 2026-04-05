from __future__ import annotations

import re

from pjx.core.types import ProcessorContext, ProcessorResult
from pjx.errors import PJXError, SourceLocation
from pjx.models import (
    ComputedDecl,
    ImportDecl,
    PropDecl,
    SlotDecl,
    TemplateMetadata,
    VarDecl,
)

FRONTMATTER_DELIM = "---"
IMPORT_RE = re.compile(r"^from\s+(\S+)\s+import\s+(.+)$")
PROP_RE = re.compile(r"^(\w+)\s*:\s*(.+?)(?:\s*=\s*(.+))?$")
SLOT_RE = re.compile(r"^slot\s+(\w+)$")
VAR_SCALAR_RE = re.compile(r'^(\w+)\s*:\s*"([^"]*)"$')
VAR_MAP_KEY_RE = re.compile(r"^(\w+)\s*:\s*$")
VAR_MAP_ENTRY_RE = re.compile(r'^(\w[\w-]*)\s*:\s*"([^"]*)"$')
COMPUTED_RE = re.compile(r"^(\w+)\s*:\s*(.+)$")


class FrontmatterProcessor:
    def process(self, source: str, ctx: ProcessorContext) -> ProcessorResult:
        if not source.startswith(FRONTMATTER_DELIM + "\n") and not source.startswith(
            FRONTMATTER_DELIM + "\r\n"
        ):
            return ProcessorResult(source=source)

        first_delim_end = source.index("\n") + 1
        second_delim_pos = source.find("\n" + FRONTMATTER_DELIM + "\n", first_delim_end)
        if second_delim_pos == -1:
            second_delim_pos = source.find("\n" + FRONTMATTER_DELIM + "\r\n", first_delim_end)
        if second_delim_pos == -1:
            if source.rstrip().endswith(FRONTMATTER_DELIM):
                second_delim_pos = source.rstrip().rfind(FRONTMATTER_DELIM) - 1
            else:
                raise PJXError(
                    "Frontmatter nao fechado: falta segundo '---'",
                    SourceLocation(ctx.filename, 1, 1),
                    code="PJX001",
                )

        frontmatter_content = source[first_delim_end : second_delim_pos + 1]
        body_start = source.index("\n", second_delim_pos + 1) + 1
        body = source[body_start:]

        metadata = self._parse_frontmatter(frontmatter_content, ctx.filename)
        return ProcessorResult(source=body, metadata=metadata)

    def _parse_frontmatter(self, content: str, filename: str | None) -> TemplateMetadata:
        imports: list[ImportDecl] = []
        props: list[PropDecl] = []
        slots: list[SlotDecl] = []
        vars_: list[VarDecl] = []
        computed: list[ComputedDecl] = []

        section: str | None = None  # "props", "vars", "computed", or None
        # For vars: map parsing
        current_map_name: str | None = None
        current_map_entries: dict[str, str] = {}

        lines = content.split("\n")

        for line_num, raw_line in enumerate(lines, start=2):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            # Imports
            import_match = IMPORT_RE.match(line)
            if import_match:
                self._flush_map(vars_, current_map_name, current_map_entries)
                current_map_name = None
                current_map_entries = {}
                section = None
                source_module = import_match.group(1)
                names = tuple(n.strip() for n in import_match.group(2).split(","))
                imports.append(ImportDecl(source=source_module, names=names))
                continue

            # Section headers
            if line == "props:":
                self._flush_map(vars_, current_map_name, current_map_entries)
                current_map_name = None
                current_map_entries = {}
                section = "props"
                continue

            if line == "vars:":
                self._flush_map(vars_, current_map_name, current_map_entries)
                current_map_name = None
                current_map_entries = {}
                section = "vars"
                continue

            if line == "computed:":
                self._flush_map(vars_, current_map_name, current_map_entries)
                current_map_name = None
                current_map_entries = {}
                section = "computed"
                continue

            # Slots
            slot_match = SLOT_RE.match(line)
            if slot_match:
                self._flush_map(vars_, current_map_name, current_map_entries)
                current_map_name = None
                current_map_entries = {}
                section = None
                slots.append(SlotDecl(name=slot_match.group(1)))
                continue

            # Props section
            if section == "props":
                prop_match = PROP_RE.match(line)
                if prop_match:
                    name = prop_match.group(1)
                    type_ann = prop_match.group(2).strip()
                    default = prop_match.group(3)
                    if default is not None:
                        default = default.strip()
                    props.append(PropDecl(name=name, type_annotation=type_ann, default=default))
                    continue

            # Vars section
            if section == "vars":
                # Check if this is a map entry (indented line inside a map var)
                if current_map_name is not None and raw_line.startswith("    "):
                    entry_match = VAR_MAP_ENTRY_RE.match(line)
                    if entry_match:
                        current_map_entries[entry_match.group(1)] = entry_match.group(2)
                        continue

                # Flush any pending map
                self._flush_map(vars_, current_map_name, current_map_entries)
                current_map_name = None
                current_map_entries = {}

                # Scalar var: name: "value"
                scalar_match = VAR_SCALAR_RE.match(line)
                if scalar_match:
                    vars_.append(VarDecl(name=scalar_match.group(1), value=scalar_match.group(2)))
                    continue

                # Map var header: name:
                map_match = VAR_MAP_KEY_RE.match(line)
                if map_match:
                    current_map_name = map_match.group(1)
                    current_map_entries = {}
                    continue

            # Computed section
            if section == "computed":
                computed_match = COMPUTED_RE.match(line)
                if computed_match:
                    computed.append(
                        ComputedDecl(
                            name=computed_match.group(1),
                            expression=computed_match.group(2).strip(),
                        )
                    )
                    continue

            raise PJXError(
                f"Frontmatter invalido: '{line}'",
                SourceLocation(filename, line_num, 1),
                code="PJX002",
            )

        # Flush any remaining map
        self._flush_map(vars_, current_map_name, current_map_entries)

        return TemplateMetadata(
            imports=imports,
            props=props,
            slots=slots,
            vars=vars_,
            computed=computed,
        )

    def _flush_map(
        self,
        vars_: list[VarDecl],
        name: str | None,
        entries: dict[str, str],
    ) -> None:
        if name is not None and entries:
            vars_.append(VarDecl(name=name, value=dict(entries)))
