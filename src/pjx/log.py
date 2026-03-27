"""PJX logging — Rich (dev) and JSON (production) log configuration."""

from __future__ import annotations

import logging

from pythonjsonlogger.json import JsonFormatter
from rich.logging import RichHandler


def setup_logging(
    debug: bool = False,
    json_output: bool = False,
    level: str | None = None,
) -> None:
    """Configure the ``pjx`` logger.

    Args:
        debug: If True, set level to DEBUG; otherwise INFO (unless overridden).
        json_output: If True, use JSON formatter for production log aggregation.
            Otherwise use Rich for human-readable dev output.
        level: Explicit log level string (e.g. ``"WARNING"``). Overrides the
            ``debug`` flag when provided.
    """
    if level is not None:
        log_level = getattr(logging, level.upper(), logging.INFO)
    else:
        log_level = logging.DEBUG if debug else logging.INFO

    logger = logging.getLogger("pjx")
    logger.handlers.clear()

    if json_output:
        handler = logging.StreamHandler()
        handler.setFormatter(
            JsonFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(module)s %(message)s",
                rename_fields={
                    "asctime": "timestamp",
                    "levelname": "level",
                },
            )
        )
    else:
        handler = RichHandler(
            rich_tracebacks=True,
            show_path=debug,
            markup=True,
        )

    logger.addHandler(handler)
    logger.setLevel(log_level)


logger = logging.getLogger("pjx")
