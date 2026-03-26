"""PJX component registry — resolve imports, cache components."""

from __future__ import annotations

import logging
from pathlib import Path

from pjx.ast_nodes import Component, ImportDecl
from pjx.compiler import Compiler
from pjx.errors import ImportResolutionError
from pjx.parser import parse_file

logger = logging.getLogger("pjx")


class ComponentRegistry:
    """Registry that resolves, caches, and compiles PJX components.

    Args:
        root_dirs: Directories to search for components.
    """

    def __init__(self, root_dirs: list[Path] | None = None) -> None:
        self._root_dirs = root_dirs or [Path("templates")]
        self._by_name: dict[str, Component] = {}
        self._by_path: dict[Path, Component] = {}
        self._resolving: set[Path] = set()  # circular import detection
        self._mtimes: dict[Path, float] = {}

    def get(self, name: str) -> Component | None:
        """Get a cached component by name."""
        return self._by_name.get(name)

    def register(self, name: str, component: Component) -> None:
        """Register a component under a name."""
        self._by_name[name] = component
        self._by_path[component.path] = component
        self._mtimes[component.path] = component.path.stat().st_mtime_ns

    def resolve(self, import_decl: ImportDecl, from_path: Path) -> list[Component]:
        """Resolve an import declaration to one or more components.

        Args:
            import_decl: The import declaration to resolve.
            from_path: Path of the importing file (for relative resolution).

        Returns:
            List of resolved components.

        Raises:
            ImportResolutionError: If the import cannot be resolved.
        """
        source = import_decl.source
        base_dir = from_path.parent

        # Resolve path
        if source.startswith("./") or source.startswith("../"):
            resolved_path = (base_dir / source).resolve()
        else:
            resolved_path = self._find_in_roots(source)

        if resolved_path is None:
            raise ImportResolutionError(
                f"cannot resolve import {source!r}", path=from_path
            )

        # Wildcard: import all .jinja files from directory
        if import_decl.wildcard:
            if not resolved_path.is_dir():
                raise ImportResolutionError(
                    f"wildcard import requires a directory: {source!r}",
                    path=from_path,
                )
            components = []
            for jinja_file in sorted(resolved_path.glob("*.jinja")):
                comp = self._load(jinja_file)
                name = jinja_file.stem
                self._by_name[name] = comp
                components.append(comp)
            return components

        # Single file
        if resolved_path.is_file():
            comp = self._load(resolved_path)
            for name in import_decl.names:
                actual_name = import_decl.alias if import_decl.alias else name
                self._by_name[actual_name] = comp
            return [comp]

        # Directory with named imports
        if resolved_path.is_dir():
            components = []
            for name in import_decl.names:
                file_path = resolved_path / f"{name}.jinja"
                if not file_path.exists():
                    raise ImportResolutionError(
                        f"component {name!r} not found in {source!r}",
                        path=from_path,
                    )
                comp = self._load(file_path)
                self._by_name[name] = comp
                components.append(comp)
            return components

        raise ImportResolutionError(f"path not found: {resolved_path}", path=from_path)

    def _find_in_roots(self, source: str) -> Path | None:
        """Search root directories for a source path."""
        for root in self._root_dirs:
            candidate = root / source
            if candidate.exists():
                return candidate.resolve()
        return None

    def _load(self, path: Path) -> Component:
        """Load and cache a component, detecting circular imports."""
        resolved = path.resolve()

        # Check cache (with mtime invalidation)
        if resolved in self._by_path:
            current_mtime = resolved.stat().st_mtime_ns
            if self._mtimes.get(resolved) == current_mtime:
                return self._by_path[resolved]

        # Circular import detection
        if resolved in self._resolving:
            raise ImportResolutionError(
                f"circular import detected: {resolved}", path=resolved
            )

        self._resolving.add(resolved)
        try:
            component = parse_file(resolved)
            self._by_path[resolved] = component
            self._mtimes[resolved] = resolved.stat().st_mtime_ns
            return component
        finally:
            self._resolving.discard(resolved)

    def compile_all(self, entry: Path) -> dict[str, str]:
        """Compile an entry component and all its dependencies.

        Args:
            entry: Path to the entry component file.

        Returns:
            Dict mapping component names to compiled Jinja2 source.
        """
        compiler = Compiler(registry=self)
        root = self._load(entry)
        self._by_name[entry.stem] = root

        # Resolve all imports recursively
        self._resolve_imports(root)

        # Compile all registered components
        results: dict[str, str] = {}
        for name, component in self._by_name.items():
            compiled = compiler.compile(component)
            results[name] = compiled.jinja_source

        return results

    def _resolve_imports(
        self, component: Component, _seen: set[Path] | None = None
    ) -> None:
        """Recursively resolve all imports for a component."""
        if _seen is None:
            _seen = set()

        resolved_path = component.path.resolve()
        if resolved_path in _seen:
            raise ImportResolutionError(
                f"circular import detected: {resolved_path}", path=resolved_path
            )
        _seen.add(resolved_path)

        for imp in component.imports:
            resolved = self.resolve(imp, component.path)
            for dep in resolved:
                self._resolve_imports(dep, _seen)
