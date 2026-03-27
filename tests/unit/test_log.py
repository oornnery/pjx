"""Tests for pjx.log — logging configuration."""

import json
import logging

from pjx.log import setup_logging


class TestSetupLogging:
    def test_default_info_level(self) -> None:
        setup_logging()
        logger = logging.getLogger("pjx")
        assert logger.level == logging.INFO

    def test_debug_mode(self) -> None:
        setup_logging(debug=True)
        logger = logging.getLogger("pjx")
        assert logger.level == logging.DEBUG

    def test_explicit_level_overrides_debug(self) -> None:
        setup_logging(debug=True, level="WARNING")
        logger = logging.getLogger("pjx")
        assert logger.level == logging.WARNING

    def test_rich_handler_by_default(self) -> None:
        setup_logging()
        logger = logging.getLogger("pjx")
        from rich.logging import RichHandler

        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], RichHandler)

    def test_json_handler(self) -> None:
        setup_logging(json_output=True)
        logger = logging.getLogger("pjx")
        assert len(logger.handlers) == 1
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        from pythonjsonlogger.json import JsonFormatter

        assert isinstance(handler.formatter, JsonFormatter)

    def test_json_output_format(self, capsys) -> None:
        """JSON logger should produce valid JSON output."""
        setup_logging(json_output=True)
        logger = logging.getLogger("pjx")
        logger.info("test message")
        captured = capsys.readouterr()
        # Parse the JSON output
        data = json.loads(captured.err.strip())
        assert data["message"] == "test message"
        assert "timestamp" in data
        assert data["level"] == "INFO"

    def test_handlers_cleared_on_reconfigure(self) -> None:
        """Calling setup_logging twice should not double handlers."""
        setup_logging()
        setup_logging()
        logger = logging.getLogger("pjx")
        assert len(logger.handlers) == 1
