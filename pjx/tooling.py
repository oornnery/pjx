from __future__ import annotations

import importlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .ast import FromImport, ImportDirective, PjxFile, PropDef
from .catalog import Catalog
from .compiler import compile_pjx
from .parser import parse


TITLE_CASE_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
VALIDATION_NUMBERS = {
    "parse_error": 101,
    "compile_error": 102,
    "missing_import_alias": 103,
    "duplicate_import_alias": 104,
    "missing_import": 105,
    "self_import": 106,
    "missing_asset": 107,
    "component_name_mismatch": 108,
    "component_name_style": 109,
    "duplicate_component_name": 110,
    "shadowed_template": 111,
    "import_cycle": 112,
    "missing_route_template": 113,
}


@dataclass(slots=True, frozen=True)
class ValidationIssue:
    number: int
    severity: str
    code: str
    message: str
    path: str
    related_path: str | None = None


@dataclass(slots=True)
class TemplateCheckResult:
    path: str
    component_names: list[str] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


@dataclass(slots=True)
class RouteCheckResult:
    path: str
    methods: tuple[str, ...]
    template: str
    issues: list[ValidationIssue] = field(default_factory=list)


@dataclass(slots=True)
class CheckReport:
    root: str
    template_roots: tuple[str, ...]
    files_checked: int
    routes_checked: int
    errors: int
    warnings: int
    validation_map: dict[str, int]
    templates: list[TemplateCheckResult]
    routes: list[RouteCheckResult]

    def as_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "template_roots": list(self.template_roots),
            "files_checked": self.files_checked,
            "routes_checked": self.routes_checked,
            "errors": self.errors,
            "warnings": self.warnings,
            "validation_map": dict(self.validation_map),
            "templates": [
                {
                    "path": t.path,
                    "component_names": t.component_names,
                    "issues": [asdict(i) for i in t.issues],
                }
                for t in self.templates
            ],
            "routes": [
                {
                    "path": r.path,
                    "methods": list(r.methods),
                    "template": r.template,
                    "issues": [asdict(i) for i in r.issues],
                }
                for r in self.routes
            ],
        }


@dataclass(slots=True, frozen=True)
class FormatResult:
    path: str
    changed: bool


@dataclass(slots=True)
class LoadedProject:
    root: Path
    catalog: Catalog
    pjx: Any | None = None
    files: tuple[Path, ...] | None = None


def load_project(target: str | None) -> LoadedProject:
    if not target:
        return _load_from_path(Path.cwd())
    if ":" in target and not Path(target).exists():
        return _load_from_import(target)
    return _load_from_path(Path(target))


def check_project(target: str | None) -> CheckReport:
    project = load_project(target)
    files = _collect_template_files(project)
    template_results: list[TemplateCheckResult] = []
    compiled_by_path: dict[str, tuple[list[str], list[str]]] = {}
    relative_roots = _build_import_path_index(project.catalog)

    for file_path in files:
        result = _check_template_file(project, file_path)
        template_results.append(result)
        if result.error_count > 0:
            continue
        try:
            ast = parse(file_path.read_text(), str(file_path))
            compile_pjx(ast, str(file_path))
            imports = _extract_import_paths(ast)
            compiled_by_path[result.path] = (result.component_names, imports)
        except Exception:
            pass

    _apply_duplicate_component_name_checks(template_results)
    _apply_shadowed_template_checks(template_results, relative_roots)
    _apply_cycle_checks(template_results, compiled_by_path)

    route_results = _check_routes(project)

    validation_map: dict[str, int] = {}
    errors = 0
    warnings = 0
    for issue in _iter_issues(template_results, route_results):
        label = _validation_label(issue.number, issue.code)
        validation_map[label] = validation_map.get(label, 0) + 1
        if issue.severity == "error":
            errors += 1
        elif issue.severity == "warning":
            warnings += 1

    return CheckReport(
        root=str(project.root),
        template_roots=tuple(str(p) for p in project.catalog.template_roots),
        files_checked=len(files),
        routes_checked=len(route_results),
        errors=errors,
        warnings=warnings,
        validation_map=dict(
            sorted(validation_map.items(), key=lambda kv: _validation_sort_key(kv[0]))
        ),
        templates=template_results,
        routes=route_results,
    )


def format_project(target: str | None, *, check: bool = False) -> list[FormatResult]:
    project = load_project(target)
    files = _collect_template_files(project)
    results: list[FormatResult] = []
    for file_path in files:
        source = file_path.read_text()
        formatted = format_template_source(source, file_path)
        changed = formatted != source
        if changed and not check:
            file_path.write_text(formatted)
        results.append(
            FormatResult(
                path=_display_path(file_path, project.catalog), changed=changed
            )
        )
    return results


def format_template_source(source: str, path: Path) -> str:
    ast = parse(source, str(path))
    blocks: list[str] = []

    for imp in ast.imports:
        blocks.append(_format_import(imp))

    if ast.is_multi_component:
        for comp in ast.components:
            blocks.append(_format_component_def(comp))
    else:
        blocks.append(_format_page_file(ast))

    return "\n\n".join(blocks).rstrip() + "\n"


def render_check_report(report: CheckReport, *, output_format: str = "text") -> str:
    if output_format == "json":
        return json.dumps(report.as_dict(), indent=2, sort_keys=True)

    lines = [
        "PJX Check",
        f"Root: {report.root}",
        f"Template roots: {', '.join(report.template_roots)}",
        f"Files checked: {report.files_checked}",
        f"Routes checked: {report.routes_checked}",
        f"Errors: {report.errors}",
        f"Warnings: {report.warnings}",
    ]

    if report.validation_map:
        lines.append("")
        lines.append("Validation map:")
        for label, count in report.validation_map.items():
            lines.append(f"  {label}: {count}")

    with_issues = [t for t in report.templates if t.issues]
    if with_issues:
        lines.append("")
        lines.append("Template issues:")
        for item in with_issues:
            lines.append(f"  {item.path}")
            for issue in item.issues:
                related = f" [{issue.related_path}]" if issue.related_path else ""
                label = _validation_label(issue.number, issue.code)
                lines.append(
                    f"    {issue.severity.upper()} {label}{related}: {issue.message}"
                )

    route_issues = [r for r in report.routes if r.issues]
    if route_issues:
        lines.append("")
        lines.append("Route issues:")
        for item in route_issues:
            lines.append(f"  {'/'.join(item.methods)} {item.path} -> {item.template}")
            for issue in item.issues:
                related = f" [{issue.related_path}]" if issue.related_path else ""
                label = _validation_label(issue.number, issue.code)
                lines.append(
                    f"    {issue.severity.upper()} {label}{related}: {issue.message}"
                )

    return "\n".join(lines)


def render_format_report(results: list[FormatResult], *, check: bool = False) -> str:
    changed = [r.path for r in results if r.changed]
    unchanged = len(results) - len(changed)

    if not results:
        return "PJX Format\nNo templates found."

    lines = [
        "PJX Format",
        f"Templates scanned: {len(results)}",
        f"Changed: {len(changed)}",
        f"Unchanged: {unchanged}",
    ]

    if changed:
        lines.append("")
        lines.append("Templates:")
        for path in changed:
            prefix = "would format" if check else "formatted"
            lines.append(f"  {prefix}: {path}")

    return "\n".join(lines)


def _issue(
    *,
    severity: str,
    code: str,
    message: str,
    path: str,
    related_path: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        number=VALIDATION_NUMBERS.get(code, 999),
        severity=severity,
        code=code,
        message=message,
        path=path,
        related_path=related_path,
    )


def _validation_label(number: int, code: str) -> str:
    return f"[{number:03d}] {code}"


def _validation_sort_key(label: str) -> int:
    match = re.match(r"^\[(\d+)\]", label)
    return int(match.group(1)) if match else 999


def _load_from_import(target: str) -> LoadedProject:
    module_name, _, attr_name = target.partition(":")
    if not module_name or not attr_name:
        raise ValueError(f"Invalid import target: {target!r}")

    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    module = importlib.import_module(module_name)
    obj = getattr(module, attr_name)

    from .fastapi import Pjx

    if isinstance(obj, Pjx):
        return LoadedProject(
            root=obj.templates_dir.parent,
            catalog=obj.catalog,
            pjx=obj,
        )
    if isinstance(obj, Catalog):
        return LoadedProject(root=obj.root, catalog=obj)
    if isinstance(obj, Path):
        return _load_from_path(obj)
    if isinstance(obj, str):
        return _load_from_path(Path(obj))

    raise TypeError(f"Unsupported PJX CLI target: {target!r}")


def _load_from_path(path: Path) -> LoadedProject:
    resolved = path.resolve()
    if resolved.is_file():
        template_root = _discover_template_root(resolved.parent)
        catalog = Catalog(
            root=str(template_root),
            aliases={"@": str(template_root)},
            auto_reload=False,
        )
        return LoadedProject(
            root=template_root.parent
            if template_root.name == "templates"
            else template_root,
            catalog=catalog,
            files=(resolved,),
        )

    project_root = resolved
    template_root = _discover_template_root(project_root)
    catalog = Catalog(
        root=str(template_root),
        aliases={"@": str(template_root)},
        auto_reload=False,
    )
    return LoadedProject(root=project_root, catalog=catalog)


def _discover_template_root(path: Path) -> Path:
    current = path.resolve()
    for candidate in (current, *current.parents):
        template_root = candidate / "templates"
        if template_root.is_dir():
            return template_root
    return current


def _collect_template_files(project: LoadedProject) -> list[Path]:
    if project.files is not None:
        return list(project.files)
    files: dict[str, Path] = {}
    for template_root in project.catalog.template_roots:
        for path in template_root.rglob("*.pjx"):
            if path.is_file():
                files.setdefault(str(path.resolve()), path)
    return sorted(files.values())


def _extract_import_paths(ast: PjxFile) -> list[str]:
    paths: list[str] = []
    for imp in ast.imports:
        if isinstance(imp, ImportDirective):
            paths.append(imp.path)
        elif isinstance(imp, FromImport):
            paths.append(imp.module)
    return paths


def _check_template_file(
    project: LoadedProject, file_path: Path
) -> TemplateCheckResult:
    result = TemplateCheckResult(path=_display_path(file_path, project.catalog))
    source = file_path.read_text()

    try:
        ast = parse(source, str(file_path))
    except Exception as exc:
        result.issues.append(
            _issue(
                severity="error", code="parse_error", message=str(exc), path=result.path
            )
        )
        return result

    if ast.is_multi_component:
        for comp in ast.components:
            result.component_names.append(comp.name)
            if not TITLE_CASE_RE.fullmatch(comp.name):
                result.issues.append(
                    _issue(
                        severity="warning",
                        code="component_name_style",
                        message=f"component name {comp.name!r} should be TitleCase",
                        path=result.path,
                    )
                )
    else:
        stem = file_path.stem
        if ast.body:
            result.component_names.append(stem)

    for imp in ast.imports:
        if isinstance(imp, ImportDirective):
            resolved = project.catalog.resolve_path(imp.path)
            if not resolved.exists():
                result.issues.append(
                    _issue(
                        severity="error",
                        code="missing_import",
                        message=f"imported template {imp.path!r} does not exist",
                        path=result.path,
                        related_path=imp.path,
                    )
                )
            elif resolved.resolve() == file_path.resolve():
                result.issues.append(
                    _issue(
                        severity="warning",
                        code="self_import",
                        message=f"template imports itself via {imp.path!r}",
                        path=result.path,
                    )
                )

    try:
        compile_pjx(ast, str(file_path))
    except Exception as exc:
        result.issues.append(
            _issue(
                severity="error",
                code="compile_error",
                message=str(exc),
                path=result.path,
            )
        )

    return result


def _apply_duplicate_component_name_checks(results: list[TemplateCheckResult]) -> None:
    index: dict[str, list[TemplateCheckResult]] = {}
    for result in results:
        for name in result.component_names:
            index.setdefault(name, []).append(result)
    for name, items in index.items():
        if len(items) < 2:
            continue
        for item in items:
            related = [o.path for o in items if o.path != item.path]
            item.issues.append(
                _issue(
                    severity="warning",
                    code="duplicate_component_name",
                    message=f"component name {name!r} is used by multiple templates",
                    path=item.path,
                    related_path=", ".join(related),
                )
            )


def _build_import_path_index(catalog: Catalog) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for mount in catalog.template_mounts:
        for path in mount.path.rglob("*.pjx"):
            if not path.is_file():
                continue
            relative = str(path.relative_to(mount.path))
            if mount.prefix is None:
                import_path = relative
            else:
                import_path = f"@{mount.prefix}/{relative}"
            index.setdefault(import_path, []).append(str(mount.path))
    return index


def _apply_shadowed_template_checks(
    results: list[TemplateCheckResult],
    relative_roots: dict[str, list[str]],
) -> None:
    for result in results:
        roots = relative_roots.get(result.path)
        if roots and len(roots) >= 2:
            result.issues.append(
                _issue(
                    severity="warning",
                    code="shadowed_template",
                    message=f"template path {result.path!r} exists in multiple template roots",
                    path=result.path,
                    related_path=", ".join(roots),
                )
            )


def _apply_cycle_checks(
    results: list[TemplateCheckResult],
    compiled_by_path: dict[str, tuple[list[str], list[str]]],
) -> None:
    adjacency = {
        path: [child for child in children if child in compiled_by_path]
        for path, (_, children) in compiled_by_path.items()
    }
    result_index = {item.path: item for item in results}
    visiting: set[str] = set()
    visited: set[str] = set()

    def walk(path: str, stack: list[str]) -> None:
        if path in visited:
            return
        if path in visiting:
            cycle = stack[stack.index(path) :] + [path]
            for item in cycle[:-1]:
                if item in result_index:
                    result_index[item].issues.append(
                        _issue(
                            severity="error",
                            code="import_cycle",
                            message=f"import cycle detected: {' -> '.join(cycle)}",
                            path=item,
                        )
                    )
            return
        visiting.add(path)
        stack.append(path)
        for child in adjacency.get(path, []):
            walk(child, stack)
        stack.pop()
        visiting.remove(path)
        visited.add(path)

    for path in adjacency:
        walk(path, [])


def _check_routes(project: LoadedProject) -> list[RouteCheckResult]:
    if project.pjx is None:
        return []
    route_results: list[RouteCheckResult] = []
    for route in getattr(project.pjx, "_pending_routes", []):
        item = RouteCheckResult(
            path=route.path,
            methods=route.methods,
            template=route.template,
        )
        resolved = project.catalog.resolve_path(route.template)
        if not resolved.exists():
            item.issues.append(
                _issue(
                    severity="error",
                    code="missing_route_template",
                    message=f"route template {route.template!r} does not exist",
                    path=route.path,
                    related_path=route.template,
                )
            )
        route_results.append(item)
    return route_results


def _iter_issues(
    templates: list[TemplateCheckResult],
    routes: list[RouteCheckResult],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for item in templates:
        issues.extend(item.issues)
    for item in routes:
        issues.extend(item.issues)
    return issues


def _display_path(path: Path, catalog: Catalog) -> str:
    return catalog.import_path_for_file(path)


def _matches_component_stem(stem: str, component_name: str) -> bool:
    ns = stem.replace("_", "").lower()
    nc = component_name.lower()
    if ns == nc:
        return True
    for suffix in ("page", "layout", "component"):
        if nc.endswith(suffix) and ns == nc.removesuffix(suffix):
            return True
    return False


def _format_import(imp: ImportDirective | FromImport) -> str:
    if isinstance(imp, FromImport):
        names = ", ".join(imp.names)
        return f"@from {imp.module} import {names}"
    return f'@import "{imp.path}"'


def _format_component_def(comp: Any) -> str:
    lines: list[str] = []
    header = f"@component {comp.name} {{"
    lines.append(header)

    if comp.props:
        props_str = ", ".join(_format_prop_def(p) for p in comp.props.props)
        lines.append(f"  @props {{ {props_str} }}")

    for slot in comp.slots:
        opt = "?" if slot.optional else ""
        lines.append(f"  @slot {slot.name}{opt}")

    if comp.state:
        fields = ", ".join(f"{f.name}: {f.value}" for f in comp.state.fields)
        lines.append(f"  @state {{ {fields} }}")

    if comp.bind:
        lines.append(f"  @bind from {comp.bind.module} import {comp.bind.class_name}")

    for let in comp.lets:
        lines.append(f"  @let {let.name} = {let.expr}")

    body = _format_body_nodes(comp.children)
    if body.strip():
        lines.append(body)

    lines.append("}")
    return "\n".join(lines)


def _format_page_file(ast: PjxFile) -> str:
    lines: list[str] = []

    if ast.bind:
        lines.append(f"@bind from {ast.bind.module} import {ast.bind.class_name}")

    if ast.props:
        props_str = ", ".join(_format_prop_def(p) for p in ast.props.props)
        lines.append(f"@props {{ {props_str} }}")

    for slot in ast.slots:
        opt = "?" if slot.optional else ""
        lines.append(f"@slot {slot.name}{opt}")

    if ast.state:
        fields = ", ".join(f"{f.name}: {f.value}" for f in ast.state.fields)
        lines.append(f"@state {{ {fields} }}")

    for let in ast.lets:
        lines.append(f"@let {let.name} = {let.expr}")

    body = _format_body_nodes(ast.body)
    if body.strip():
        if lines:
            lines.append("")
        lines.append(body)

    return "\n".join(lines)


def _format_prop_def(prop: PropDef) -> str:
    parts = [prop.name]
    if prop.type_expr:
        parts.append(f": {prop.type_expr}")
    if prop.default_expr is not None:
        parts.append(f" = {prop.default_expr}")
    return "".join(parts)


def _format_body_nodes(nodes: tuple[Any, ...]) -> str:
    from .ast import TextNode, ExprNode

    chunks: list[str] = []
    for node in nodes:
        if isinstance(node, TextNode):
            chunks.append(node.content)
        elif isinstance(node, ExprNode):
            chunks.append(node.content)
        else:
            chunks.append(str(node))
    return "".join(chunks)


def main(argv: list[str] | None = None) -> int:
    from .cli import main as cli_main

    return cli_main(argv)
