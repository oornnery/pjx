"""PJX — server-first component framework for Python.

Public API
----------
Core layer (works standalone, no FastAPI required):

    from pjx import parse, compile_pjx, Runtime

FastAPI integration layer:

    from pjx import Pjx, PjxRouter, render, Page, Template, is_htmx
"""

from __future__ import annotations

# ── Core ──────────────────────────────────────────────────────────────────────

from .ast import PjxFile
from .compiler import compile_pjx
from .exceptions import (
    CompileError,
    ComponentError,
    ParseError,
    PjxError,
    PropValidationError,
    ResolutionError,
)
from .models import Component, computed, event, prop, state
from .parser import parse
from .runtime import Runtime

# ── FastAPI integration (requires fastapi) ────────────────────────────────────

try:
    from .catalog import Catalog, TemplateMount
    from .fastapi import (
        Page,
        Pjx,
        PjxRouter,
        RenderResult,
        Template,
        is_htmx,
        is_htmx_request,
        render,
    )

    PJX = Pjx
    PJXRouter = PjxRouter
    PJXDeclarative = PjxRouter

    __all__ = [
        "PjxFile",
        "compile_pjx",
        "parse",
        "Runtime",
        "Component",
        "computed",
        "event",
        "prop",
        "state",
        "PjxError",
        "ParseError",
        "CompileError",
        "ComponentError",
        "ResolutionError",
        "PropValidationError",
        "Catalog",
        "TemplateMount",
        "Pjx",
        "PjxRouter",
        "PJX",
        "PJXRouter",
        "PJXDeclarative",
        "RenderResult",
        "Page",
        "Template",
        "render",
        "is_htmx",
        "is_htmx_request",
    ]
except ImportError:
    __all__ = [
        "PjxFile",
        "compile_pjx",
        "parse",
        "Runtime",
        "Component",
        "computed",
        "event",
        "prop",
        "state",
        "PjxError",
        "ParseError",
        "CompileError",
        "ComponentError",
        "ResolutionError",
        "PropValidationError",
    ]
