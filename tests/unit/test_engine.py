"""Tests for pjx.engine — template engine wrappers."""

from pjx.engine import (
    EngineProtocol,
    HybridEngine,
    Jinja2Engine,
    MiniJinjaEngine,
    create_engine,
)


class TestJinja2Engine:
    def test_render_string(self) -> None:
        engine = Jinja2Engine()
        result = engine.render_string("Hello {{ name }}!", {"name": "World"})
        assert result == "Hello World!"

    def test_add_and_render(self) -> None:
        engine = Jinja2Engine()
        engine.add_template("greeting", "Hi {{ name }}")
        result = engine.render("greeting", {"name": "PJX"})
        assert result == "Hi PJX"

    def test_add_global(self) -> None:
        engine = Jinja2Engine()
        engine.add_global("app_name", "PJX")
        result = engine.render_string("{{ app_name }}", {})
        assert result == "PJX"

    def test_implements_protocol(self) -> None:
        assert isinstance(Jinja2Engine(), EngineProtocol)


class TestMiniJinjaEngine:
    def test_render_string(self) -> None:
        engine = MiniJinjaEngine()
        result = engine.render_string("Hello {{ name }}!", {"name": "World"})
        assert result == "Hello World!"

    def test_add_and_render(self) -> None:
        engine = MiniJinjaEngine()
        engine.add_template("greeting", "Hi {{ name }}")
        result = engine.render("greeting", {"name": "PJX"})
        assert result == "Hi PJX"

    def test_implements_protocol(self) -> None:
        assert isinstance(MiniJinjaEngine(), EngineProtocol)


class TestHybridEngine:
    def test_render_string(self) -> None:
        engine = HybridEngine()
        result = engine.render_string("Hello {{ name }}!", {"name": "World"})
        assert result == "Hello World!"

    def test_add_and_render(self) -> None:
        engine = HybridEngine()
        engine.add_template("greeting", "Hi {{ name }}")
        result = engine.render("greeting", {"name": "PJX"})
        assert result == "Hi PJX"

    def test_add_global(self) -> None:
        engine = HybridEngine()
        engine.add_global("app_name", "PJX")
        engine.add_template("test", "{{ app_name }}")
        result = engine.render("test", {})
        assert result == "PJX"

    def test_has_template(self) -> None:
        engine = HybridEngine()
        assert not engine.has_template("missing")
        engine.add_template("exists", "ok")
        assert engine.has_template("exists")

    def test_implements_protocol(self) -> None:
        assert isinstance(HybridEngine(), EngineProtocol)


class TestCreateEngine:
    def test_auto_returns_hybrid(self) -> None:
        engine = create_engine("auto")
        assert isinstance(engine, HybridEngine)

    def test_hybrid_explicit(self) -> None:
        engine = create_engine("hybrid")
        assert isinstance(engine, HybridEngine)

    def test_jinja2_explicit(self) -> None:
        engine = create_engine("jinja2")
        assert isinstance(engine, Jinja2Engine)

    def test_minijinja_explicit(self) -> None:
        engine = create_engine("minijinja")
        assert isinstance(engine, MiniJinjaEngine)
