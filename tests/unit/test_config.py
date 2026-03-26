"""Tests for pjx.config — PJXConfig loading."""

from pathlib import Path

from pjx.config import PJXConfig


class TestPJXConfig:
    def test_defaults(self) -> None:
        config = PJXConfig()
        assert config.engine == "hybrid"
        assert config.debug is False
        assert config.host == "127.0.0.1"
        assert config.port == 8000
        assert config.alpine is True
        assert config.htmx is True
        assert config.tailwind is False

    def test_template_dirs_default(self) -> None:
        config = PJXConfig()
        assert config.template_dirs == [Path("templates")]

    def test_static_dir_default(self) -> None:
        config = PJXConfig()
        assert config.static_dir == Path("static")

    def test_env_override(self, monkeypatch: object) -> None:
        import os

        os.environ["PJX_DEBUG"] = "true"
        os.environ["PJX_PORT"] = "3000"
        try:
            config = PJXConfig()
            assert config.debug is True
            assert config.port == 3000
        finally:
            os.environ.pop("PJX_DEBUG", None)
            os.environ.pop("PJX_PORT", None)

    def test_engine_choices(self) -> None:
        for engine in ("hybrid", "jinja2", "minijinja", "auto"):
            config = PJXConfig(engine=engine)
            assert config.engine == engine
