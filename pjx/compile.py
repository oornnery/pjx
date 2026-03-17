"""Compile: batch-compile .pjx files to .jinja templates.

The ``compile_project`` function walks all template roots, parses each
``.pjx`` file, compiles it to Jinja2 source, and writes the result into
an output directory preserving the original folder structure.

In **bundle mode** (``--bundle``), imported component macros are resolved
recursively and inlined into each page template, producing self-contained
``.jinja`` files that need no Python callbacks at render time.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from .ast import FromImport, ImportDirective, PjxFile
from .compiler import compile_pjx
from .parser import parse


@dataclass(slots=True, frozen=True)
class CompileResult:
    source_path: str
    output_path: str
    success: bool
    bundled: bool = False
    deps_inlined: int = 0
    error: str | None = None


@dataclass(slots=True)
class CompileReport:
    output_dir: str
    files_compiled: int
    files_failed: int
    bundle: bool = False
    results: list[CompileResult] = field(default_factory=list)


def compile_project(
    project: Any,
    output_dir: Path,
    *,
    clean: bool = False,
    bundle: bool = False,
) -> CompileReport:
    """Compile all .pjx files in the project to .jinja output.

    Parameters
    ----------
    project:
        A ``LoadedProject`` from ``tooling.load_project()``.
    output_dir:
        Target directory for compiled ``.jinja`` files.
    clean:
        If True, remove output_dir before compiling.
    bundle:
        If True, inline imported component macros into page templates.
    """
    if clean and output_dir.exists():
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[CompileResult] = []
    files_compiled = 0
    files_failed = 0

    # Pre-build resolver for bundle mode
    resolver = _ImportResolver(project.catalog) if bundle else None

    # Collect all .pjx files from template roots
    seen: set[str] = set()
    for template_root in project.catalog.template_roots:
        for pjx_file in sorted(template_root.rglob("*.pjx")):
            if not pjx_file.is_file():
                continue
            resolved = str(pjx_file.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)

            relative = pjx_file.relative_to(template_root)
            jinja_path = output_dir / relative.with_suffix(".jinja")
            jinja_path.parent.mkdir(parents=True, exist_ok=True)

            source_display = str(relative)
            try:
                source = pjx_file.read_text(encoding="utf-8")
                ast = parse(source, filename=str(pjx_file))

                if bundle and not ast.is_multi_component:
                    # Bundle mode: inline all imported macros
                    jinja_source, deps_inlined = _compile_bundled(
                        ast, str(pjx_file), resolver
                    )
                    jinja_path.write_text(jinja_source, encoding="utf-8")
                    results.append(
                        CompileResult(
                            source_path=source_display,
                            output_path=str(jinja_path),
                            success=True,
                            bundled=True,
                            deps_inlined=deps_inlined,
                        )
                    )
                else:
                    jinja_source = compile_pjx(ast, filename=str(pjx_file))
                    jinja_path.write_text(jinja_source, encoding="utf-8")
                    results.append(
                        CompileResult(
                            source_path=source_display,
                            output_path=str(jinja_path),
                            success=True,
                        )
                    )
                files_compiled += 1
            except Exception as exc:
                results.append(
                    CompileResult(
                        source_path=source_display,
                        output_path=str(jinja_path),
                        success=False,
                        error=str(exc),
                    )
                )
                files_failed += 1

    return CompileReport(
        output_dir=str(output_dir),
        files_compiled=files_compiled,
        files_failed=files_failed,
        bundle=bundle,
        results=results,
    )


# ── Bundle: import resolution and macro inlining ─────────────────────────────


class _ImportResolver:
    """Resolves import paths to compiled macro sources, with caching."""

    def __init__(self, catalog: Any) -> None:
        self.catalog = catalog
        self._cache: dict[str, str] = {}  # resolved_path → macro_source

    def resolve_macros(
        self, ast: PjxFile, visited: set[str] | None = None
    ) -> tuple[str, int]:
        """Recursively resolve all imports and return (macro_sources, count)."""
        if visited is None:
            visited = set()

        macro_parts: list[str] = []
        count = 0

        for imp in ast.imports:
            import_paths = self._get_import_paths(imp)

            for import_path in import_paths:
                source_path = self.catalog.resolve_path(import_path)
                resolved_key = str(source_path.resolve())

                if resolved_key in visited:
                    continue
                visited.add(resolved_key)

                # Check cache
                if resolved_key in self._cache:
                    macro_parts.append(self._cache[resolved_key])
                    count += 1
                    continue

                if not source_path.exists():
                    continue

                source = source_path.read_text(encoding="utf-8")
                dep_ast = parse(source, filename=str(source_path))

                # Recursively resolve this dependency's imports first
                sub_macros, sub_count = self.resolve_macros(dep_ast, visited)

                # Compile this dependency's macros with bundle=True
                # so nested component calls use direct macro invocations
                if dep_ast.is_multi_component:
                    compiled = compile_pjx(
                        dep_ast, filename=str(source_path), bundle=True
                    )
                else:
                    compiled = _wrap_single_as_macro(dep_ast, source_path)

                # Cache the FULL output (sub-deps + this macro) so subsequent
                # pages that import this template get everything they need
                full = f"{sub_macros}\n{compiled}" if sub_macros else compiled
                self._cache[resolved_key] = full
                macro_parts.append(full)
                count += sub_count + 1

        return "\n".join(macro_parts), count

    def _get_import_paths(self, imp: Any) -> list[str]:
        """Extract template paths from an import directive."""
        if isinstance(imp, ImportDirective):
            return [imp.path]
        if isinstance(imp, FromImport):
            return [imp.module.replace(".", "/") + ".pjx"]
        return []


def _wrap_single_as_macro(
    ast: PjxFile, source_path: Path, resolver: _ImportResolver | None = None
) -> str:
    """Wrap a single-component .pjx file as a Jinja2 macro.

    If *resolver* is provided, the file's own imports are recursively resolved
    and their macro definitions prepended, so the result is fully self-contained.
    """
    stem = source_path.stem
    name = stem[0].upper() + stem[1:] if stem else "Component"

    # Resolve sub-imports first so they appear before this macro
    sub_macros = ""
    if resolver:
        sub_macros, _ = resolver.resolve_macros(ast)

    # Compile body with bundle=True so nested imports are also local calls
    body = compile_pjx(ast, filename=str(source_path), bundle=True)

    # Build macro signature from props and slots
    params: list[str] = []
    if ast.props:
        for p in ast.props.props:
            if p.default_expr is not None:
                params.append(f"{p.name}={p.default_expr}")
            else:
                params.append(p.name)
    params.append("__slot_default=''")
    for s in ast.slots:
        if s.name != "default":
            params.append(f"__slot_{s.name}=''")

    sig = ", ".join(params)
    macro = f"{{% macro {name}({sig}) %}}\n{body}\n{{% endmacro %}}\n"

    if sub_macros:
        return f"{sub_macros}\n{macro}"
    return macro


def _compile_bundled(
    ast: PjxFile,
    filename: str,
    resolver: _ImportResolver | None,
) -> tuple[str, int]:
    """Compile a page template with all imports bundled inline."""
    # 1. Resolve all imported macros recursively
    deps_inlined = 0
    macro_preamble = ""
    if resolver:
        macro_preamble, deps_inlined = resolver.resolve_macros(ast)

    # 2. Compile the page itself with bundle=True
    #    This makes the compiler emit direct macro calls instead of
    #    __pjx_render_component
    page_source = compile_pjx(ast, filename=filename, bundle=True)

    # 3. Concatenate: macros first, then page body
    if macro_preamble:
        bundled = f"{macro_preamble}\n{page_source}"
    else:
        bundled = page_source

    return bundled, deps_inlined


def render_compile_report(report: CompileReport) -> str:
    lines = [
        "PJX Compile",
        f"Output: {report.output_dir}",
        f"Bundle: {'yes' if report.bundle else 'no'}",
        f"Compiled: {report.files_compiled}",
        f"Failed: {report.files_failed}",
    ]

    failed = [r for r in report.results if not r.success]
    if failed:
        lines.append("")
        lines.append("Errors:")
        for r in failed:
            lines.append(f"  {r.source_path}: {r.error}")

    succeeded = [r for r in report.results if r.success]
    if succeeded:
        lines.append("")
        lines.append("Files:")
        for r in succeeded:
            suffix = ""
            if r.bundled:
                suffix = f" (bundled, {r.deps_inlined} deps inlined)"
            lines.append(f"  {r.source_path} -> {r.output_path}{suffix}")

    return "\n".join(lines)
