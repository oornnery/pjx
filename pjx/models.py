from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from markupsafe import Markup, escape


DirectiveFn = Callable[["Element", Any, "DirectiveContext"], "Element | list[Element] | None"]


@dataclass(slots=True)
class AssetImport:
    kind: str
    path: str


@dataclass(slots=True)
class PropSpec:
    name: str
    type_expr: str | None = None
    default_expr: str | None = None


@dataclass(slots=True)
class SlotSpec:
    name: str
    params: tuple[str, ...] = ()


@dataclass(slots=True)
class CompiledComponent:
    path: str
    component_name: str
    source_path: Path
    assets: tuple[AssetImport, ...]
    component_imports: dict[str, str]
    prop_specs: tuple[PropSpec, ...]
    slot_specs: dict[str, SlotSpec]
    inject_names: tuple[str, ...]
    provide_names: tuple[str, ...]
    action_names: tuple[str, ...]
    modifiers: frozenset[str]
    jinja_source: str


@dataclass(slots=True)
class DirectiveContext:
    tag_name: str
    render_state: "RenderState"
    component: CompiledComponent | None = None


@dataclass(slots=True)
class Element:
    name: str
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RenderState:
    catalog: Any
    request: Any = None
    partial: bool = False
    target: str | None = None
    assets: list[AssetImport] = field(default_factory=list)
    asset_keys: set[tuple[str, str]] = field(default_factory=set)
    fragment_counter: int = 0

    def register_assets(self, assets: tuple[AssetImport, ...]) -> None:
        for asset in assets:
            key = (asset.kind, asset.path)
            if key in self.asset_keys:
                continue
            self.asset_keys.add(key)
            self.assets.append(asset)

    def next_fragment_name(self, prefix: str) -> str:
        self.fragment_counter += 1
        return f"__pjx_{prefix}_{self.fragment_counter}"


class AttrBag:
    def __init__(self, attrs: dict[str, Any]):
        self.attrs = attrs

    def __bool__(self) -> bool:
        return bool(self.attrs)

    def __html__(self) -> Markup:
        if not self.attrs:
            return Markup("")
        parts: list[str] = []
        for key, value in self.attrs.items():
            if value is True:
                parts.append(f" {escape(key)}")
                continue
            if value in (False, None):
                continue
            parts.append(f' {escape(key)}="{escape(value)}"')
        return Markup("".join(parts))

    def __str__(self) -> str:
        return str(self.__html__())


class SlotAccessor:
    def __init__(self, slot_specs: dict[str, SlotSpec], provided_slots: dict[str, Any]):
        self._slot_specs = slot_specs
        self._provided_slots = provided_slots

    def __getattr__(self, name: str) -> Any:
        provided = self._provided_slots.get(name)
        spec = self._slot_specs.get(name)
        if provided is None:
            if spec is None or not spec.params:
                return Markup("")

            def empty_slot(*args: Any, **kwargs: Any) -> Markup:
                return Markup("")

            return empty_slot
        if spec is None or not spec.params:
            return Markup(provided() if callable(provided) else provided)

        def wrapper(*args: Any, **kwargs: Any) -> Markup:
            if callable(provided):
                return Markup(provided(*args, **kwargs))
            return Markup(provided)

        return wrapper
