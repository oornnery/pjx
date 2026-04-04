from __future__ import annotations

import re

from pjx.core.pipeline import ProcessorContext, ProcessorResult
from pjx.errors import PJXError, SourceLocation
from pjx.models import ImportDecl, PropDecl, SlotDecl, TemplateMetadata

FRONTMATTER_DELIM = "---"
IMPORT_RE = re.compile(r"^from\s+(\S+)\s+import\s+(.+)$")
PROP_RE = re.compile(r"^(\w+)\s*:\s*(.+?)(?:\s*=\s*(.+))?$")
SLOT_RE = re.compile(r"^slot\s+(\w+)$")


class FrontmatterProcessor:
    def process(self, source: str, ctx: ProcessorContext) -> ProcessorResult:
        if not source.startswith(FRONTMATTER_DELIM + "\n") and not source.startswith(
            FRONTMATTER_DELIM + "\r\n"
        ):
            return ProcessorResult(source=source)

        first_delim_end = source.index("\n") + 1
        second_delim_pos = source.find("\n" + FRONTMATTER_DELIM + "\n", first_delim_end)
        if second_delim_pos == -1:
            second_delim_pos = source.find(
                "\n" + FRONTMATTER_DELIM + "\r\n", first_delim_end
            )
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

    def _parse_frontmatter(
        self, content: str, filename: str | None
    ) -> TemplateMetadata:
        imports: list[ImportDecl] = []
        props: list[PropDecl] = []
        slots: list[SlotDecl] = []

        in_props = False
        lines = content.split("\n")

        for line_num, raw_line in enumerate(lines, start=2):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            import_match = IMPORT_RE.match(line)
            if import_match:
                in_props = False
                source_module = import_match.group(1)
                names = [n.strip() for n in import_match.group(2).split(",")]
                imports.append(ImportDecl(source=source_module, names=names))
                continue

            if line == "props:":
                in_props = True
                continue

            slot_match = SLOT_RE.match(line)
            if slot_match:
                in_props = False
                slots.append(SlotDecl(name=slot_match.group(1)))
                continue

            if in_props:
                prop_match = PROP_RE.match(line)
                if prop_match:
                    name = prop_match.group(1)
                    type_ann = prop_match.group(2).strip()
                    default = prop_match.group(3)
                    if default is not None:
                        default = default.strip()
                    props.append(
                        PropDecl(name=name, type_annotation=type_ann, default=default)
                    )
                    continue

            raise PJXError(
                f"Frontmatter invalido: '{line}'",
                SourceLocation(filename, line_num, 1),
                code="PJX002",
            )

        return TemplateMetadata(imports=imports, props=props, slots=slots)
