from pathlib import Path

from pjx import Catalog
from pjx.web import Request

from exemples.directives.tooltip import tooltip_directive

BASE_DIR = Path(__file__).parent


# Illustrative API for how a PJX catalog could be configured in a real app.
catalog = Catalog(
    root=str(BASE_DIR),
    aliases={
        "@": str(BASE_DIR),
    },
)

catalog.register_directive("tooltip", tooltip_directive)


def render_page(request: Request, template: str, **context):
    return catalog.render(
        template=template,
        request=request,
        context=context,
    )


def render_fragment(request: Request, template: str, target: str, **context):
    return catalog.render(
        template=template,
        request=request,
        context=context,
        partial=True,
        target=target,
    )
