"""PJX — Python DSL for reactive Jinja components.

Compiles a declarative component syntax (props, state, slots, imports,
control flow) down to Jinja2 + HTMX + Alpine.js.

Public API::

    from pjx import PJX, PJXConfig, SEO, parse, Compiler
"""

__version__ = "0.2.0"

from pjx.caching import cache, memo
from pjx.compiler import Compiler
from pjx.seo import dict_to_seo, generate_robots, generate_sitemap, metadata
from pjx.config import PJXConfig
from pjx.engine import HybridEngine, Jinja2Engine, MiniJinjaEngine, create_engine
from pjx.errors import RenderError
from pjx.handler import APIRoute, RouteHandler
from pjx.integration import PJX, SEO, FormData
from pjx.middleware import CSRFMiddleware
from pjx.parser import parse, parse_file
from pjx.router import FileRouter

__all__ = [
    "APIRoute",
    "CSRFMiddleware",
    "Compiler",
    "cache",
    "FileRouter",
    "FormData",
    "HybridEngine",
    "Jinja2Engine",
    "MiniJinjaEngine",
    "PJX",
    "PJXConfig",
    "RenderError",
    "RouteHandler",
    "SEO",
    "create_engine",
    "dict_to_seo",
    "generate_robots",
    "generate_sitemap",
    "memo",
    "metadata",
    "parse",
    "parse_file",
]
