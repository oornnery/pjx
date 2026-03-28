"""Tests for pjx.setup — application setup helpers."""

from unittest.mock import MagicMock, patch

from pjx.config import PJXConfig
from pjx.setup import setup_cors, setup_logging, setup_static


class TestSetupStatic:
    def test_mounts_static_when_dir_exists(self, tmp_path) -> None:
        static = tmp_path / "static"
        static.mkdir()
        config = PJXConfig(static_dir=static)
        app = MagicMock()
        setup_static(app, config)
        app.mount.assert_called_once()
        args = app.mount.call_args
        assert args[0][0] == "/static"

    def test_skips_when_dir_missing(self, tmp_path) -> None:
        config = PJXConfig(static_dir=tmp_path / "nonexistent")
        app = MagicMock()
        setup_static(app, config)
        app.mount.assert_not_called()


class TestSetupCors:
    def test_adds_middleware_when_origins_set(self) -> None:
        config = PJXConfig(cors_origins=["http://localhost:3000"])
        app = MagicMock()
        setup_cors(app, config)
        app.add_middleware.assert_called_once()

    def test_skips_when_no_origins(self) -> None:
        config = PJXConfig()
        app = MagicMock()
        setup_cors(app, config)
        app.add_middleware.assert_not_called()


class TestSetupLogging:
    @patch("pjx.log.setup_logging")
    def test_calls_setup_logging_with_config(self, mock_log_setup) -> None:
        config = PJXConfig(debug=True, log_json=True, log_level="DEBUG")
        setup_logging(config)
        mock_log_setup.assert_called_once_with(
            debug=True, json_output=True, level="DEBUG"
        )
