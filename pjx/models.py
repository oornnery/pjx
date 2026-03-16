from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from markupsafe import Markup, escape


# ── Component base-class API ───────────────────────────────────────────────────

_MISSING: Any = object()


class _StateField:
    """Marker for a class-level reactive state field."""

    __slots__ = ("name", "default")

    def __init__(self, default: Any = None) -> None:
        self.name: str = ""
        self.default: Any = default


class _PropField:
    """Marker for a component template-prop field."""

    __slots__ = ("name", "default", "type_")

    def __init__(self, default: Any = _MISSING, *, type_: Any = None) -> None:
        self.name: str = ""
        self.default: Any = default
        self.type_: Any = type_


def state(default: Any = None) -> Any:
    """Declare a class-level server-side state field on a :class:`Component`."""
    return _StateField(default)


def prop(default: Any = _MISSING, *, type_: Any = None) -> Any:
    """Declare a component prop field on a :class:`Component`."""
    return _PropField(default, type_=type_)


#: Alias — use ``@computed`` as a property decorator on Component subclasses.
computed = property


def event(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a method as a named event handler."""

    def _decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn._pjx_event = name  # type: ignore[attr-defined]
        return fn

    return _decorator


class _ComponentMeta(type):
    """Metaclass that lifts ``state()`` / ``prop()`` fields off the class body
    and stores them in ``_pjx_state_fields`` / ``_pjx_prop_fields`` so that
    class-level attribute access (``MyComp.count``) is intercepted transparently.
    """

    def __new__(
        mcs,
        cls_name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
    ) -> "_ComponentMeta":
        state_fields: dict[str, _StateField] = {}
        prop_fields: dict[str, _PropField] = {}
        clean: dict[str, Any] = {}

        for key, val in namespace.items():
            if isinstance(val, _StateField):
                val.name = key
                state_fields[key] = val
            elif isinstance(val, _PropField):
                val.name = key
                prop_fields[key] = val
            else:
                clean[key] = val

        cls = super().__new__(mcs, cls_name, bases, clean)
        # Use type.__setattr__ to bypass our own __setattr__ below.
        type.__setattr__(cls, "_pjx_state_fields", state_fields)
        type.__setattr__(cls, "_pjx_prop_fields", prop_fields)
        type.__setattr__(
            cls,
            "_pjx_state_values",
            {k: v.default for k, v in state_fields.items()},
        )
        type.__setattr__(cls, "_pjx_lock", Lock())
        return cls

    def __getattr__(cls, name: str) -> Any:
        for klass in cls.__mro__:
            sf = klass.__dict__.get("_pjx_state_fields", {})
            if name in sf:
                sv = klass.__dict__.get("_pjx_state_values", {})
                return sv.get(name, sf[name].default)
        raise AttributeError(f"type object '{cls.__name__}' has no attribute '{name}'")

    def __setattr__(cls, name: str, value: Any) -> None:
        for klass in cls.__mro__:
            sf = klass.__dict__.get("_pjx_state_fields", {})
            if name in sf:
                # Mutate the dict directly — mappingproxy holds a reference.
                klass.__dict__["_pjx_state_values"][name] = value
                return
        type.__setattr__(cls, name, value)


class Component(metaclass=_ComponentMeta):
    """Base class for server-side PJX components with reactive state.

    Example::

        from pjx import Component, state

        class Counter(Component):
            count = state(0)

            @classmethod
            def increment(cls) -> None:
                with cls._pjx_lock:
                    cls.count += 1

        # In a route handler:
        Counter.increment()
        return Counter.context()   # → {"count": 1}
    """

    @classmethod
    def context(cls) -> dict[str, Any]:
        """Return all declared *state* and *prop* values as a template context dict."""
        ctx: dict[str, Any] = {}
        for klass in reversed(cls.__mro__):
            sf = klass.__dict__.get("_pjx_state_fields", {})
            sv = klass.__dict__.get("_pjx_state_values", {})
            for key in sf:
                ctx[key] = sv.get(key, sf[key].default)
            pf = klass.__dict__.get("_pjx_prop_fields", {})
            for key, pfield in pf.items():
                if pfield.default is not _MISSING:
                    ctx.setdefault(key, pfield.default)
        return ctx


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
class DirectiveContext:
    tag_name: str
    render_state: "RenderState"
    component: Any = None


@dataclass(slots=True)
class Element:
    name: str
    attrs: dict[str, Any] = field(default_factory=dict)
    text_content: str | None = None
    html_content: str | None = None


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
