from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from markupsafe import Markup, escape


DirectiveFn = Callable[
    ["Element", Any, "DirectiveContext"], "Element | list[Element] | None"
]


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
    assets_rendered: bool = False
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
        self.attrs = dict(attrs)

    def __bool__(self) -> bool:
        return bool(self.attrs)

    def render(self, **defaults: Any) -> Markup:
        merged = dict(self.attrs)
        for key, value in defaults.items():
            clean_key = _normalize_attr_name(key)
            if clean_key is None:
                continue
            if clean_key == "class":
                merged[clean_key] = _merge_classes(value, merged.get(clean_key))
                continue
            merged.setdefault(clean_key, value)
        return _render_attrs(merged)

    def set(self, **kwargs: Any) -> "AttrBag":
        for key, value in kwargs.items():
            clean_key = _normalize_attr_name(key)
            if clean_key is None:
                continue
            if clean_key == "class":
                self.attrs[clean_key] = _merge_classes(self.attrs.get(clean_key), value)
                continue
            if value in (False, None):
                self.attrs.pop(clean_key, None)
                continue
            self.attrs[clean_key] = value
        return self

    def setdefault(self, **kwargs: Any) -> "AttrBag":
        for key, value in kwargs.items():
            clean_key = _normalize_attr_name(key)
            if clean_key is None or clean_key in self.attrs:
                continue
            self.attrs[clean_key] = value
        return self

    def get(self, name: str, default: Any = None) -> Any:
        clean_name = _normalize_attr_name(name)
        if clean_name is None:
            return default
        return self.attrs.get(clean_name, default)

    def add_class(self, *values: Any) -> "AttrBag":
        self.attrs["class"] = _merge_classes(self.attrs.get("class"), *values)
        return self

    def prepend_class(self, *values: Any) -> "AttrBag":
        self.attrs["class"] = _merge_classes(*values, self.attrs.get("class"))
        return self

    def remove_class(self, *names: str) -> "AttrBag":
        blocked = {item for name in names for item in str(name).split() if item}
        if not blocked:
            return self
        remaining = [
            token
            for token in _class_tokens(self.attrs.get("class"))
            if token not in blocked
        ]
        if remaining:
            self.attrs["class"] = " ".join(remaining)
        else:
            self.attrs.pop("class", None)
        return self

    @property
    def classes(self) -> str:
        return " ".join(_class_tokens(self.attrs.get("class")))

    @property
    def as_dict(self) -> dict[str, Any]:
        return dict(sorted(self.attrs.items()))

    def __html__(self) -> Markup:
        return self.render()

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


def _normalize_attr_name(name: str) -> str | None:
    if name.startswith("_"):
        return None
    return name.replace("_", "-")


def _render_attrs(attrs: dict[str, Any]) -> Markup:
    if not attrs:
        return Markup("")
    parts: list[str] = []
    for key, value in attrs.items():
        if value is True:
            parts.append(f" {escape(key)}")
            continue
        if value in (False, None):
            continue
        parts.append(f' {escape(key)}="{escape(value)}"')
    return Markup("".join(parts))


def _class_tokens(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, dict):
        return [name for name, enabled in value.items() if enabled]
    if isinstance(value, (list, tuple, set)):
        tokens: list[str] = []
        for item in value:
            tokens.extend(_class_tokens(item))
        return tokens
    return [token for token in str(value).split() if token]


def _merge_classes(*values: Any) -> str:
    tokens: list[str] = []
    for value in values:
        for token in _class_tokens(value):
            if token not in tokens:
                tokens.append(token)
    return " ".join(tokens)
