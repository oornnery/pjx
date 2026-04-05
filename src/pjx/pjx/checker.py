from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import BaseLoader, FileSystemLoader

from pjx.core.pipeline import PreprocessorPipeline
from pjx.core.types import PreprocessResult
from pjx.errors import Diagnostic, DiagnosticLevel, SourceLocation
from pjx.models import TemplateMetadata

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


@dataclass
class CheckResult:
    template: str
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(d.level == DiagnosticLevel.ERROR for d in self.diagnostics)


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
        _check_undefined_vars(result, preprocess, metadata, filename)

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
    for m in VAR_REF_RE.finditer(preprocess.source):
        refs.add(m.group(1))
    for m in ATTR_EXPR_RE.finditer(preprocess.source):
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
    if path.is_file():
        base_dir = path.parent
        files = [path]
    else:
        base_dir = path
        files = sorted(path.rglob("*.jinja"))

    loader = FileSystemLoader(str(base_dir))
    pipeline = PreprocessorPipeline()
    results: list[CheckResult] = []

    for file in files:
        template_name = str(file.relative_to(base_dir))
        source = file.read_text()
        result = check_template(source, template_name, pipeline, loader)
        results.append(result)

    return results
