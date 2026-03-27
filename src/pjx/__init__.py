"""PJX — Python DSL for reactive Jinja components.

Compiles a declarative component syntax (props, state, slots, imports,
control flow) down to Jinja2 + HTMX + Alpine.js.

Public API::

    from pjx import PJX, PJXConfig, SEO, parse, Compiler
"""

__version__ = "0.0.1"

from pjx.compiler import Compiler
from pjx.config import PJXConfig
from pjx.engine import HybridEngine, Jinja2Engine, MiniJinjaEngine, create_engine
from pjx.handler import APIRoute, RouteHandler
from pjx.integration import PJX, SEO, FormData
from pjx.middleware import CSRFMiddleware
from pjx.parser import parse, parse_file
from pjx.router import FileRouter

__all__ = [
    "APIRoute",
    "CSRFMiddleware",
    "Compiler",
    "FileRouter",
    "FormData",
    "HybridEngine",
    "Jinja2Engine",
    "MiniJinjaEngine",
    "PJX",
    "PJXConfig",
    "RouteHandler",
    "SEO",
    "create_engine",
    "parse",
    "parse_file",
]
