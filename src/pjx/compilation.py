"""Compilation pipeline — template discovery, compilation, and import resolution."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pjx.cache import TemplateCache
from pjx.compiler import Compiler
from pjx.config import PJXConfig
from pjx.engine import EngineProtocol
from pjx.parser import parse_file
from pjx.props import generate_props_model
from pjx.registry import ComponentRegistry

_INCLUDE_RE = re.compile(r'\{%[-\s]*include\s+"([^"]+)"')


class CompilationPipeline:
    """Compiles PJX templates and resolves their import trees.

    Handles mtime-based caching, recursive import compilation, and
    registration of compiled templates in the engine.

    Args:
        compiler: The PJX AST-to-Jinja compiler.
        registry: Component registry for resolving imports.
        engine: Template engine where compiled sources are registered.
        cache: Shared template cache instance.
        config: PJX configuration.
    """

    def __init__(
        self,
        compiler: Compiler,
        registry: ComponentRegistry,
        engine: EngineProtocol,
        cache: TemplateCache,
        config: PJXConfig,
    ) -> None:
        self.compiler = compiler
        self.registry = registry
        self.engine = engine
        self.cache = cache
        self.config = config

    def compile_template(
        self,
        template: str,
        css_parts: list[str] | None = None,
        asset_collector: Any | None = None,
        _seen: set[str] | None = None,
    ) -> None:
        """Compile a template and all its imports, registering them in the engine.

        Uses mtime-based caching: skips recompilation if the file hasn't changed.
        The ``_seen`` set prevents diamond-dependency recompilation.
        """
        if _seen is None:
            _seen = set()
        if template in _seen:
            return
        _seen.add(template)

        template_path = self.find_template(template)

        try:
            current_mtime = template_path.stat().st_mtime
        except OSError:
            current_mtime = 0.0

        if not self.cache.is_stale(template, current_mtime):
            if css_parts is not None or asset_collector is not None:
                self.cache.collect_cached_assets(template, css_parts, asset_collector)
            self._compile_imports_cached(
                template_path, css_parts, asset_collector, _seen
            )
            return

        component = parse_file(template_path)
        self._register_imports_in_registry(component)
        compiled = self.compiler.compile(component)

        if component.props:
            self.cache.store_props_model(
                template, generate_props_model(component.props)
            )

        if css_parts is not None and compiled.css:
            css_parts.append(compiled.css.source)

        if asset_collector is not None:
            for asset in compiled.assets:
                asset_collector.add(asset)

        self.cache.store(
            template,
            current_mtime,
            compiled.jinja_source,
            compiled.css.source if compiled.css else None,
            compiled.assets,
        )
        self.engine.add_template(template, compiled.jinja_source)
        self._register_jinja_includes(compiled.jinja_source)
        self._compile_imports(component, css_parts, asset_collector, _seen)

    def register_builtin_layouts(self) -> None:
        """Parse and register built-in layout components in the registry."""
        from pjx.layout import LAYOUT_COMPONENTS, LAYOUT_PREFIX

        for name in LAYOUT_COMPONENTS:
            if self.registry.get(name) is not None:
                continue
            path = self.find_template(f"{LAYOUT_PREFIX}/{name}.jinja")
            component = parse_file(path)
            self.registry.register(name, component)

    def find_template(self, template: str) -> Path:
        """Find a template file in the configured template directories.

        Validates that the resolved path stays within the template directory
        to prevent path traversal attacks.
        """
        from pjx.layout import UI_DIR

        for tpl_dir in [*self.config.template_dirs, UI_DIR.parent]:
            tpl_root = Path(tpl_dir).resolve()
            candidate = (Path(tpl_dir) / template).resolve()
            try:
                candidate.relative_to(tpl_root)
            except ValueError:
                continue
            if candidate.exists():
                return candidate
        msg = f"template not found: {template!r}"
        raise FileNotFoundError(msg)

    def _compile_imports_cached(
        self,
        template_path: Path,
        css_parts: list[str] | None,
        asset_collector: Any | None,
        _seen: set[str],
    ) -> None:
        """Re-walk imports of a cached template to collect assets from children."""
        component = parse_file(template_path)
        for imp in component.imports:
            source = imp.source
            try:
                self.compile_template(source, css_parts, asset_collector, _seen)
            except FileNotFoundError:
                rel = str(template_path.parent / source)
                self.compile_template(rel, css_parts, asset_collector, _seen)

    def _register_imports_in_registry(self, component: Any) -> None:
        """Parse and register imported components so the compiler can look up child props."""
        for imp in component.imports:
            for name in imp.names:
                if self.registry.get(name) is not None:
                    continue
                try:
                    imp_path = self.find_template(imp.source)
                except FileNotFoundError:
                    imp_path = component.path.parent / imp.source
                    if not imp_path.exists():
                        continue
                imp_component = parse_file(imp_path)
                self.registry.register(name, imp_component)
                self._register_imports_in_registry(imp_component)

    def _compile_imports(
        self,
        component: Any,
        css_parts: list[str] | None,
        asset_collector: Any | None = None,
        _seen: set[str] | None = None,
    ) -> None:
        """Recursively compile and register imported components."""
        if _seen is None:
            _seen = set()
        for imp in component.imports:
            source = imp.source
            if source in _seen:
                self.cache.collect_cached_assets(source, css_parts, asset_collector)
                continue
            _seen.add(source)
            try:
                imp_path = self.find_template(source)
            except FileNotFoundError:
                imp_path = component.path.parent / source
                if not imp_path.exists():
                    continue
            try:
                current_mtime = imp_path.stat().st_mtime
            except OSError:
                current_mtime = 0.0
            if not self.cache.is_stale(source, current_mtime):
                self.cache.collect_cached_assets(source, css_parts, asset_collector)
                imp_component = parse_file(imp_path)
                self._compile_imports(imp_component, css_parts, asset_collector, _seen)
                continue
            imp_component = parse_file(imp_path)
            imp_compiled = self.compiler.compile(imp_component)
            self.cache.store(
                source,
                current_mtime,
                imp_compiled.jinja_source,
                imp_compiled.css.source if imp_compiled.css else None,
                imp_compiled.assets,
            )
            self.engine.add_template(source, imp_compiled.jinja_source)
            if css_parts is not None and imp_compiled.css:
                css_parts.append(imp_compiled.css.source)
            if asset_collector is not None:
                for asset in imp_compiled.assets:
                    asset_collector.add(asset)
            self._compile_imports(imp_component, css_parts, asset_collector, _seen)

    def _register_jinja_includes(self, source: str) -> None:
        """Find raw ``{% include "..." %}`` in compiled Jinja and register them."""
        for match in _INCLUDE_RE.finditer(source):
            inc_name = match.group(1)
            if self.engine.has_template(inc_name):
                continue
            try:
                self.compile_template(inc_name)
            except FileNotFoundError:
                pass
