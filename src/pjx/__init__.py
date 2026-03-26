"""PJX — Python DSL for reactive Jinja components.

Public API::

    from pjx import PJX, parse, parse_file, Compiler
    from pjx.config import PJXConfig
"""

__version__ = "0.0.1"

from pjx.compiler import Compiler
from pjx.config import PJXConfig
from pjx.engine import HybridEngine, Jinja2Engine, MiniJinjaEngine, create_engine
from pjx.handler import APIRoute, RouteHandler
from pjx.integration import PJX, SEO, FormData
from pjx.parser import parse, parse_file
from pjx.router import FileRouter

__all__ = [
    "APIRoute",
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
