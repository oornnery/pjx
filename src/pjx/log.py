"""PJX logging — Rich-powered log configuration."""

from __future__ import annotations

import logging

from rich.logging import RichHandler


def setup_logging(debug: bool = False) -> None:
    """Configure the ``pjx`` logger with Rich output.

    Args:
        debug: If True, set level to DEBUG; otherwise INFO.
    """
    level = logging.DEBUG if debug else logging.INFO
    handler = RichHandler(
        rich_tracebacks=True,
        show_path=debug,
        markup=True,
    )
    logger = logging.getLogger("pjx")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)


logger = logging.getLogger("pjx")
