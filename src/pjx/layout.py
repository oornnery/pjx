"""Built-in layout components — auto-discovered from ``ui/layouts/*.jinja``.

No ``import`` needed in user templates — always available.
"""

from __future__ import annotations

from pathlib import Path

#: Root directory containing built-in component subdirectories.
UI_DIR: Path = Path(__file__).parent / "ui"

#: Prefix for layout component template paths (e.g. ``ui/layouts/Center.jinja``).
LAYOUT_PREFIX: str = "ui/layouts"

_LAYOUTS_DIR: Path = UI_DIR / "layouts"

#: Component names auto-discovered from ``ui/layouts/*.jinja``.
LAYOUT_COMPONENTS: frozenset[str] = frozenset(
    p.stem for p in _LAYOUTS_DIR.glob("*.jinja")
) if _LAYOUTS_DIR.is_dir() else frozenset()

#: Cache for parsed props — populated lazily by ``get_layout_props()``.
_props_cache: dict[str, tuple[str, ...]] = {}


def get_layout_props(name: str) -> tuple[str, ...]:
    """Return declared prop names for a built-in layout component.

    Parses the ``.jinja`` template on first access, caches the result.
    """
    if name in _props_cache:
        return _props_cache[name]
    path = _LAYOUTS_DIR / f"{name}.jinja"
    if not path.exists():
        _props_cache[name] = ()
        return ()
    from pjx.parser import parse_file

    component = parse_file(path)
    props = tuple(f.name for f in component.props.fields) if component.props else ()
    _props_cache[name] = props
    return props
