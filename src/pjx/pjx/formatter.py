from __future__ import annotations

import re
from pathlib import Path

FRONTMATTER_DELIM = "---"

SECTION_ORDER = ["imports", "props", "vars", "computed", "slots"]

IMPORT_RE = re.compile(r"^from\s+\S+\s+import\s+.+$")
PROP_RE = re.compile(r"^\w+\s*:\s*.+$")
SLOT_RE = re.compile(r"^slot\s+\w+$")
VAR_SCALAR_RE = re.compile(r'^\w+\s*:\s*".+"$')
VAR_MAP_KEY_RE = re.compile(r"^\w+\s*:\s*$")
VAR_MAP_ENTRY_RE = re.compile(r'^\s+\w[\w-]*\s*:\s*".+"$')
COMPUTED_RE = re.compile(r"^\w+\s*:\s*.+$")


def format_template(source: str) -> str:
    if not source.startswith(FRONTMATTER_DELIM + "\n") and not source.startswith(
        FRONTMATTER_DELIM + "\r\n"
    ):
        return source

    first_end = source.index("\n") + 1
    second_pos = source.find("\n" + FRONTMATTER_DELIM + "\n", first_end)
    if second_pos == -1:
        second_pos = source.find("\n" + FRONTMATTER_DELIM + "\r\n", first_end)
    if second_pos == -1:
        return source

    fm_content = source[first_end : second_pos + 1]
    body_start = source.index("\n", second_pos + 1) + 1
    body = source[body_start:]

    sections = _parse_sections(fm_content)
    formatted_fm = _format_sections(sections)

    return FRONTMATTER_DELIM + "\n" + formatted_fm + FRONTMATTER_DELIM + "\n" + body


def _parse_sections(content: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {
        "imports": [],
        "props": [],
        "vars": [],
        "computed": [],
        "slots": [],
    }

    current = "imports"
    lines = content.split("\n")

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if IMPORT_RE.match(line):
            sections["imports"].append(line)
            current = "imports"
            continue

        if line == "props:":
            current = "props"
            continue

        if line == "vars:":
            current = "vars"
            continue

        if line == "computed:":
            current = "computed"
            continue

        if SLOT_RE.match(line):
            sections["slots"].append(line)
            current = "slots"
            continue

        if current == "props":
            sections["props"].append(line)
        elif current == "vars":
            sections["vars"].append(raw_line.rstrip())
        elif current == "computed":
            sections["computed"].append(line)

    return sections


def _format_sections(sections: dict[str, list[str]]) -> str:
    parts: list[str] = []

    for section in SECTION_ORDER:
        lines = sections.get(section, [])
        if not lines:
            continue

        if parts:
            parts.append("")

        if section == "imports":
            parts.extend(lines)
        elif section == "props":
            parts.append("props:")
            for line in lines:
                parts.append(f"  {line}")
        elif section == "vars":
            parts.append("vars:")
            for line in lines:
                if line.startswith("  ") or line.startswith("    "):
                    parts.append(line)
                else:
                    parts.append(f"  {line}")
        elif section == "computed":
            parts.append("computed:")
            for line in lines:
                parts.append(f"  {line}")
        elif section == "slots":
            parts.extend(lines)

    if parts:
        parts.append("")

    return "\n".join(parts)


def format_file(path: Path) -> bool:
    source = path.read_text()
    formatted = format_template(source)
    if formatted != source:
        path.write_text(formatted)
        return True
    return False


def check_format(path: Path) -> bool:
    source = path.read_text()
    formatted = format_template(source)
    return formatted == source
