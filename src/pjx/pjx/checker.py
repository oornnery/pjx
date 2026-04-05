from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import BaseLoader, FileSystemLoader

from pjx.core.pipeline import PreprocessorPipeline
from pjx.core.types import PreprocessResult
from pjx.errors import Diagnostic, DiagnosticLevel, SourceLocation
from pjx.models import ImportDecl, TemplateMetadata

JINJA_BUILTINS = frozenset(
    {
        "range",
        "lipsum",
        "dict",
        "cycler",
        "joiner",
        "namespace",
        "loop",
        "true",
        "false",
        "none",
        "content",
        "request",
        "props",
        "params",
        "errors",
    }
)

VAR_REF_RE = re.compile(r"\{\{[\s]*(\w+)")
ATTR_EXPR_RE = re.compile(r"\{([^{}]+)\}")
IMPORT_LINE_RE = re.compile(r"^from\s+(\S+)\s+import\s+(.+)$")


@dataclass
class CheckResult:
    template: str
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(d.level == DiagnosticLevel.ERROR for d in self.diagnostics)


@dataclass(frozen=True, slots=True)
class FixResult:
    files_changed: int = 0
    fixes_applied: int = 0


def check_template(
    source: str,
    filename: str,
    pipeline: PreprocessorPipeline,
    loader: BaseLoader | None = None,
) -> CheckResult:
    result = CheckResult(template=filename)

    try:
        preprocess = pipeline.process(source, filename=filename)
    except Exception as e:
        result.diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                code="PJX900",
                message=str(e),
                loc=SourceLocation(filename, 1, 1),
            )
        )
        return result

    metadata = preprocess.metadata
    result.diagnostics.extend(preprocess.diagnostics)

    if metadata:
        _check_imports(result, metadata, filename, loader)
        _check_computed_cycles(result, metadata, filename)
        _check_undefined_vars(result, source, preprocess, metadata, filename)

    return result


def _check_imports(
    result: CheckResult,
    metadata: TemplateMetadata,
    filename: str,
    loader: BaseLoader | None,
) -> None:
    for imp in metadata.imports:
        for name in imp.names:
            resolved = metadata.resolve_import(name, filename)
            if resolved is None:
                result.diagnostics.append(
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        code="PJX301",
                        message=f"Cannot resolve import '{name}' from '{imp.source}'",
                        loc=SourceLocation(filename, 1, 1),
                    )
                )
                continue

            if loader and isinstance(loader, FileSystemLoader):
                found = False
                for search_path in loader.searchpath:
                    if (Path(search_path) / resolved).exists():
                        found = True
                        break
                if not found:
                    result.diagnostics.append(
                        Diagnostic(
                            level=DiagnosticLevel.WARNING,
                            code="PJX302",
                            message=f"Import '{name}' resolves to '{resolved}' but file not found",
                            loc=SourceLocation(filename, 1, 1),
                            hint=f"Expected at: {resolved}",
                        )
                    )


def _check_computed_cycles(
    result: CheckResult,
    metadata: TemplateMetadata,
    filename: str,
) -> None:
    computed_names = {c.name for c in metadata.computed}
    deps: dict[str, set[str]] = {}

    for comp in metadata.computed:
        refs = set(re.findall(r"\b(\w+)\b", comp.expression))
        deps[comp.name] = refs & computed_names

    visited: set[str] = set()
    path: list[str] = []

    def _visit(name: str) -> bool:
        if name in path:
            cycle = " -> ".join(path[path.index(name) :] + [name])
            result.diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    code="PJX303",
                    message=f"Circular dependency in computed: {cycle}",
                    loc=SourceLocation(filename, 1, 1),
                )
            )
            return True
        if name in visited:
            return False
        visited.add(name)
        path.append(name)
        for dep in deps.get(name, set()):
            if _visit(dep):
                return True
        path.pop()
        return False

    for name in computed_names:
        _visit(name)


def _check_undefined_vars(
    result: CheckResult,
    source: str,
    preprocess: PreprocessResult,
    metadata: TemplateMetadata,
    filename: str,
) -> None:
    defined = set(JINJA_BUILTINS)
    for p in metadata.props:
        defined.add(p.name)
    for v in metadata.vars:
        defined.add(v.name)
    for c in metadata.computed:
        defined.add(c.name)
    for imp in metadata.imports:
        defined.update(imp.names)
    for s in metadata.slots:
        defined.add(s.name)

    refs: set[str] = set()
    # VAR_REF_RE: {{ var }} in preprocessed output (PJX → Jinja2).
    # ATTR_EXPR_RE: {expr} in original source (HTML attrs before compilation).
    for m in VAR_REF_RE.finditer(preprocess.source):
        refs.add(m.group(1))
    for m in ATTR_EXPR_RE.finditer(source):
        for word in re.findall(r"\b(\w+)\b", m.group(1)):
            refs.add(word)

    # Filter out Jinja keywords, filters, and Python builtins
    jinja_keywords = frozenset(
        {
            "for",
            "endfor",
            "if",
            "endif",
            "elif",
            "else",
            "set",
            "endset",
            "with",
            "endwith",
            "include",
            "block",
            "endblock",
            "extends",
            "macro",
            "endmacro",
            "call",
            "endcall",
            "filter",
            "endfilter",
            "not",
            "and",
            "or",
            "in",
            "is",
            "true",
            "false",
            "none",
            "True",
            "False",
            "None",
            "length",
            "default",
            "safe",
            "int",
            "str",
            "list",
            "dict",
            "float",
            "bool",
        }
    )
    refs -= jinja_keywords

    undefined = refs - defined
    for name in sorted(undefined):
        if name.startswith("_") or name[0].isupper():
            continue
        result.diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.WARNING,
                code="PJX304",
                message=f"Possibly undefined variable: '{name}'",
                loc=SourceLocation(filename, 1, 1),
                hint="Define in props:, vars:, or computed:",
            )
        )


def check_directory(
    path: Path,
    verbose: bool = False,
) -> list[CheckResult]:
    base_dir, files = _discover_template_files(path)
    loader = FileSystemLoader(str(base_dir))
    pipeline = PreprocessorPipeline()
    results: list[CheckResult] = []

    for file in files:
        template_name = str(file.relative_to(base_dir))
        source = file.read_text()
        result = check_template(source, template_name, pipeline, loader)
        results.append(result)

    return results


def apply_check_fixes(path: Path) -> FixResult:
    base_dir, files = _discover_template_files(path)
    name_index = _build_name_index(files, base_dir)

    files_changed = 0
    fixes_applied = 0

    for file in files:
        template_name = str(file.relative_to(base_dir))
        source = file.read_text()
        fixed_source, file_fix_count = _autofix_template(
            source,
            template_name,
            base_dir,
            name_index,
        )
        if file_fix_count == 0:
            continue

        file.write_text(fixed_source)
        files_changed += 1
        fixes_applied += file_fix_count

    return FixResult(files_changed=files_changed, fixes_applied=fixes_applied)


def _discover_template_files(path: Path) -> tuple[Path, list[Path]]:
    if path.is_file():
        base_dir = path.parent
        files = [path]
    else:
        base_dir = path
        files = sorted(path.rglob("*.jinja"))
    return base_dir, files


def _build_name_index(files: list[Path], base_dir: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for file in files:
        rel_path = file.relative_to(base_dir)
        index.setdefault(file.stem, []).append(rel_path)
    return index


def _autofix_template(
    source: str,
    filename: str,
    base_dir: Path,
    name_index: dict[str, list[Path]],
) -> tuple[str, int]:
    frontmatter = _extract_frontmatter(source)
    if frontmatter is None:
        return source, 0

    frontmatter_lines, body, line_ending = frontmatter
    fixed_lines: list[str] = []
    fix_count = 0

    for line in frontmatter_lines:
        new_lines, line_fix_count = _autofix_import_line(line, filename, base_dir, name_index)
        fixed_lines.extend(new_lines)
        fix_count += line_fix_count

    if fix_count == 0:
        return source, 0

    frontmatter_content = line_ending.join(fixed_lines)
    fixed_source = f"---{line_ending}{frontmatter_content}{line_ending}---{line_ending}{body}"
    return fixed_source, fix_count


def _extract_frontmatter(source: str) -> tuple[list[str], str, str] | None:
    if source.startswith("---\r\n"):
        line_ending = "\r\n"
    elif source.startswith("---\n"):
        line_ending = "\n"
    else:
        return None

    marker = f"{line_ending}---{line_ending}"
    second_delim_pos = source.find(marker, 4)
    if second_delim_pos == -1:
        return None

    frontmatter_content = source[4:second_delim_pos]
    body = source[second_delim_pos + len(marker) :]
    return frontmatter_content.split(line_ending), body, line_ending


def _autofix_import_line(
    line: str,
    filename: str,
    base_dir: Path,
    name_index: dict[str, list[Path]],
) -> tuple[list[str], int]:
    stripped = line.strip()
    import_match = IMPORT_LINE_RE.match(stripped)
    if import_match is None:
        return [line], 0

    source_module = import_match.group(1)
    imported_names = [name.strip() for name in import_match.group(2).split(",") if name.strip()]
    grouped_names: list[tuple[str, list[str]]] = []
    fixes = 0

    for name in imported_names:
        target_module = source_module
        if not _import_exists(source_module, name, filename, base_dir):
            candidate_module = _find_unique_candidate_module(name, filename, name_index)
            if candidate_module is not None and candidate_module != source_module:
                target_module = candidate_module
                fixes += 1

        if grouped_names and grouped_names[-1][0] == target_module:
            grouped_names[-1][1].append(name)
        else:
            grouped_names.append((target_module, [name]))

    if fixes == 0:
        return [line], 0

    fixed_lines = [f"from {module} import {', '.join(names)}" for module, names in grouped_names]
    return fixed_lines, fixes


def _import_exists(source_module: str, name: str, filename: str, base_dir: Path) -> bool:
    metadata = TemplateMetadata(imports=[ImportDecl(source=source_module, names=(name,))])
    resolved = metadata.resolve_import(name, filename)
    if resolved is None:
        return False
    return (base_dir / resolved).exists()


def _find_unique_candidate_module(
    name: str,
    filename: str,
    name_index: dict[str, list[Path]],
) -> str | None:
    candidates = [path for path in name_index.get(name, []) if path.as_posix() != filename]
    if len(candidates) != 1:
        return None

    parent = candidates[0].parent
    if not parent.parts:
        return None
    return ".".join(parent.parts)
