from __future__ import annotations

from dataclasses import asdict, dataclass, field
import importlib
import json
from pathlib import Path
import re
import sys
from typing import Any

from .ast import (
    ActionDirectiveNode,
    ComputedDirectiveNode,
    ImportNode,
    InjectDirectiveNode,
    PropDeclNode,
    PropsAliasNode,
    PropsDirectiveNode,
    ProvideDirectiveNode,
    SignalDirectiveNode,
    SlotDirectiveNode,
)
from .catalog import Catalog
from .compiler import compile_component_file
from .fastapi import PJX
from .parser import parse_component_source


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
    component_name: str | None = None
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")


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
                    "path": item.path,
                    "component_name": item.component_name,
                    "issues": [asdict(issue) for issue in item.issues],
                }
                for item in self.templates
            ],
            "routes": [
                {
                    "path": item.path,
                    "methods": list(item.methods),
                    "template": item.template,
                    "issues": [asdict(issue) for issue in item.issues],
                }
                for item in self.routes
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
    pjx: PJX | None
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
    compiled_by_path: dict[str, tuple[str, list[str]]] = {}
    relative_roots = _build_import_path_index(project.catalog)

    for file_path in files:
        template_result = _check_template_file(project, file_path)
        template_results.append(template_result)

        if template_result.error_count > 0:
            continue

        compiled = compile_component_file(file_path.read_text(), file_path)
        imports = list(compiled.component_imports.values())
        compiled_by_path[template_result.path] = (compiled.component_name, imports)

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
        template_roots=tuple(str(path) for path in project.catalog.template_roots),
        files_checked=len(files),
        routes_checked=len(route_results),
        errors=errors,
        warnings=warnings,
        validation_map=dict(sorted(validation_map.items(), key=lambda item: _validation_sort_key(item[0]))),
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
        results.append(FormatResult(path=_display_path(file_path, project.catalog), changed=changed))

    return results


def format_template_source(source: str, path: Path) -> str:
    parsed = parse_component_source(source, path)

    blocks: list[str] = []
    if parsed.imports:
        blocks.extend(_format_import(item) for item in parsed.imports)
    if parsed.prop_aliases:
        blocks.extend(_format_props_alias(item) for item in parsed.prop_aliases)

    component_lines: list[str] = []
    component_header = " ".join(("component", parsed.component.name, *parsed.component.modifiers)).strip()
    component_lines.append(f"{{% {component_header} %}}")

    if parsed.component.directives:
        component_lines.append("")
        for index, directive in enumerate(parsed.component.directives):
            component_lines.extend(_format_directive(directive))
            if index != len(parsed.component.directives) - 1:
                component_lines.append("")

    body = _normalize_block_body(parsed.component.body)
    if body:
        component_lines.append("")
        component_lines.extend(body.splitlines())

    component_lines.append("{% endcomponent %}")
    blocks.append("\n".join(component_lines))

    return "\n\n".join(blocks).rstrip() + "\n"


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
    if match is None:
        return 999
    return int(match.group(1))


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

    template_with_issues = [item for item in report.templates if item.issues]
    if template_with_issues:
        lines.append("")
        lines.append("Template issues:")
        for item in template_with_issues:
            lines.append(f"  {item.path}")
            for issue in item.issues:
                related = f" [{issue.related_path}]" if issue.related_path else ""
                label = _validation_label(issue.number, issue.code)
                lines.append(f"    {issue.severity.upper()} {label}{related}: {issue.message}")

    route_with_issues = [item for item in report.routes if item.issues]
    if route_with_issues:
        lines.append("")
        lines.append("Route issues:")
        for item in route_with_issues:
            lines.append(f"  {'/'.join(item.methods)} {item.path} -> {item.template}")
            for issue in item.issues:
                related = f" [{issue.related_path}]" if issue.related_path else ""
                label = _validation_label(issue.number, issue.code)
                lines.append(f"    {issue.severity.upper()} {label}{related}: {issue.message}")

    return "\n".join(lines)


def render_format_report(results: list[FormatResult], *, check: bool = False) -> str:
    changed = [item.path for item in results if item.changed]
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


def _load_from_import(target: str) -> LoadedProject:
    module_name, _, attr_name = target.partition(":")
    if not module_name or not attr_name:
        raise ValueError(f"Invalid import target: {target!r}")

    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    module = importlib.import_module(module_name)
    obj = getattr(module, attr_name)

    if isinstance(obj, PJX):
        return LoadedProject(root=obj.root, catalog=obj.catalog, pjx=obj)
    if isinstance(obj, Catalog):
        return LoadedProject(root=obj.root, catalog=obj, pjx=None)
    if isinstance(obj, Path):
        return _load_from_path(obj)
    if isinstance(obj, str):
        return _load_from_path(Path(obj))

    raise TypeError(f"Unsupported PJX CLI target: {target!r}")


def _load_from_path(path: Path) -> LoadedProject:
    resolved = path.resolve()
    if resolved.is_file():
        template_root = _discover_template_root(resolved.parent)
        catalog = Catalog(root=str(template_root), aliases={"@": str(template_root)}, auto_reload=False)
        return LoadedProject(root=template_root.parent if template_root.name == "templates" else template_root, catalog=catalog, pjx=None, files=(resolved,))

    project_root = resolved
    template_root = _discover_template_root(project_root)
    catalog = Catalog(root=str(template_root), aliases={"@": str(template_root)}, auto_reload=False)
    return LoadedProject(root=project_root, catalog=catalog, pjx=None)


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
        for path in template_root.rglob("*.jinja"):
            if not path.is_file():
                continue
            files.setdefault(str(path.resolve()), path)
    return sorted(files.values())


def _check_template_file(project: LoadedProject, file_path: Path) -> TemplateCheckResult:
    result = TemplateCheckResult(path=_display_path(file_path, project.catalog))
    source = file_path.read_text()

    try:
        parsed = parse_component_source(source, file_path)
    except Exception as exc:
        result.issues.append(
            _issue(
                severity="error",
                code="parse_error",
                message=str(exc),
                path=result.path,
            )
        )
        return result

    result.component_name = parsed.component.name

    if not _matches_component_stem(file_path.stem, parsed.component.name):
        result.issues.append(
            _issue(
                severity="warning",
                code="component_name_mismatch",
                message=f"file stem {file_path.stem!r} does not match component {parsed.component.name!r}",
                path=result.path,
            )
        )

    if not TITLE_CASE_RE.fullmatch(parsed.component.name):
        result.issues.append(
            _issue(
                severity="warning",
                code="component_name_style",
                message=f"component name {parsed.component.name!r} should be TitleCase",
                path=result.path,
            )
        )

    aliases: dict[str, str] = {}
    for import_node in parsed.imports:
        if import_node.kind == "component":
            if import_node.alias is None:
                result.issues.append(
                    _issue(
                        severity="error",
                        code="missing_import_alias",
                        message=f"component import {import_node.path!r} requires an alias",
                        path=result.path,
                    )
                )
                continue

            previous = aliases.get(import_node.alias)
            if previous is not None:
                result.issues.append(
                    _issue(
                        severity="error",
                        code="duplicate_import_alias",
                        message=f"component import alias {import_node.alias!r} is declared more than once",
                        path=result.path,
                        related_path=previous,
                    )
                )
            else:
                aliases[import_node.alias] = import_node.path

            resolved_path = project.catalog.resolve_path(import_node.path)
            if not resolved_path.exists():
                result.issues.append(
                    _issue(
                        severity="error",
                        code="missing_import",
                        message=f"imported component {import_node.path!r} does not exist",
                        path=result.path,
                        related_path=import_node.path,
                    )
                )
            elif resolved_path.resolve() == file_path.resolve():
                result.issues.append(
                    _issue(
                        severity="warning",
                        code="self_import",
                        message=f"component imports itself via {import_node.path!r}",
                        path=result.path,
                    )
                )
        else:
            missing_asset = _resolve_asset_path(project, import_node)
            if missing_asset is not None and not missing_asset.exists():
                result.issues.append(
                    _issue(
                        severity="warning",
                        code="missing_asset",
                        message=f"asset {import_node.path!r} does not exist",
                        path=result.path,
                        related_path=str(missing_asset),
                    )
                )

    try:
        compile_component_file(source, file_path)
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


def _resolve_asset_path(project: LoadedProject, import_node: ImportNode) -> Path | None:
    asset_path = import_node.path
    if asset_path.startswith("/static/"):
        return project.root / asset_path.lstrip("/")

    candidate = Path(asset_path)
    if candidate.is_absolute():
        return candidate

    return None


def _apply_duplicate_component_name_checks(results: list[TemplateCheckResult]) -> None:
    index: dict[str, list[TemplateCheckResult]] = {}
    for result in results:
        if result.component_name is None:
            continue
        index.setdefault(result.component_name, []).append(result)

    for component_name, items in index.items():
        if len(items) < 2:
            continue
        for item in items:
            related = [other.path for other in items if other.path != item.path]
            item.issues.append(
                _issue(
                    severity="warning",
                    code="duplicate_component_name",
                    message=f"component name {component_name!r} is used by multiple templates",
                    path=item.path,
                    related_path=", ".join(related),
                )
            )


def _build_import_path_index(catalog: Catalog) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for mount in catalog.template_mounts:
        for path in mount.path.rglob("*.jinja"):
            if not path.is_file():
                continue
            relative_path = str(path.relative_to(mount.path))
            if mount.prefix is None:
                import_path = relative_path
            else:
                import_path = f"@{mount.prefix}/{relative_path}"
            index.setdefault(import_path, []).append(str(mount.path))
    return index


def _apply_shadowed_template_checks(
    results: list[TemplateCheckResult],
    relative_roots: dict[str, list[str]],
) -> None:
    if len(relative_roots) < 2:
        return

    for result in results:
        roots = relative_roots.get(result.path)
        if roots is None or len(roots) < 2:
            continue
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
    compiled_by_path: dict[str, tuple[str, list[str]]],
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
                result_index[item].issues.append(
                    _issue(
                        severity="error",
                        code="import_cycle",
                        message=f"component import cycle detected: {' -> '.join(cycle)}",
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
        resolved_path = project.catalog.resolve_path(route.template)
        if not resolved_path.exists():
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
    normalized_stem = stem.replace("_", "").lower()
    normalized_component = component_name.lower()
    if normalized_stem == normalized_component:
        return True
    for suffix in ("page", "layout", "component"):
        if normalized_component.endswith(suffix) and normalized_stem == normalized_component.removesuffix(suffix):
            return True
    return False


def _normalize_block_body(body: str) -> str:
    lines = body.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(line.rstrip() for line in lines)


def _format_import(import_node: ImportNode) -> str:
    if import_node.kind == "component":
        return f'{{% import "{import_node.path}" as {import_node.alias} %}}'
    return f'{{% import {import_node.kind} "{import_node.path}" %}}'


def _format_props_alias(alias: PropsAliasNode) -> str:
    lines = [f"{{% set {alias.name} = {{"]
    for index, prop in enumerate(alias.props):
        suffix = "," if index < len(alias.props) - 1 else ""
        lines.append(f'  "{prop.name}": {_format_prop_decl(prop)}{suffix}')
    lines.append("} %}")
    return "\n".join(lines)


def _format_directive(
    directive: (
        PropsDirectiveNode
        | InjectDirectiveNode
        | ProvideDirectiveNode
        | ComputedDirectiveNode
        | SlotDirectiveNode
        | SignalDirectiveNode
        | ActionDirectiveNode
    ),
) -> list[str]:
    if isinstance(directive, PropsDirectiveNode):
        if directive.alias_name:
            return [f"  {{% props {directive.alias_name} %}}"]
        if len(directive.props) <= 1:
            prop_decl = ", ".join(_format_prop_decl(item) for item in directive.props)
            return [f"  {{% props {prop_decl} %}}"]
        lines = ["  {% props"]
        for index, prop in enumerate(directive.props):
            suffix = "," if index < len(directive.props) - 1 else ""
            lines.append(f"    {_format_prop_decl(prop)}{suffix}")
        lines.append("  %}")
        return lines

    if isinstance(directive, InjectDirectiveNode):
        return [f"  {{% inject {' '.join(directive.names)} %}}"]

    if isinstance(directive, ProvideDirectiveNode):
        return [f"  {{% provide {' '.join(directive.names)} %}}"]

    if isinstance(directive, ComputedDirectiveNode):
        lines = [f"  {{% computed {directive.name} %}}"]
        body = _normalize_block_body(directive.body)
        if body:
            lines.extend(f"    {line}" if line else "" for line in body.splitlines())
        lines.append("  {% endcomputed %}")
        return lines

    if isinstance(directive, SlotDirectiveNode):
        signature = directive.name
        if directive.params:
            signature += f"({', '.join(directive.params)})"
        return [f"  {{% slot {signature} %}}{{% endslot %}}"]

    if isinstance(directive, SignalDirectiveNode):
        return [f"  {{% signal {directive.name} = signal({directive.expr}) %}}"]

    if isinstance(directive, ActionDirectiveNode):
        lines = [f"  {{% action {directive.name} %}}"]
        body = _normalize_block_body(directive.body)
        if body:
            lines.extend(f"    {line}" if line else "" for line in body.splitlines())
        lines.append("  {% endaction %}")
        return lines

    raise TypeError(f"Unsupported directive type: {type(directive)!r}")


def _format_prop_decl(prop: PropDeclNode) -> str:
    chunks = [prop.name]
    if prop.type_expr:
        chunks.append(f": {prop.type_expr}")
    if prop.default_expr is not None:
        chunks.append(f" = {prop.default_expr}")
    return "".join(chunks)


def main(argv: list[str] | None = None) -> int:
    from .cli import main as cli_main

    return cli_main(argv)
