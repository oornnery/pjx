"""Tests for server action declarations — parser, compiler, handler, formatter."""

from textwrap import dedent

from pjx.compiler import Compiler
from pjx.handler import RouteHandler
from pjx.parser import parse


class TestActionParser:
    """Tests for parsing action declarations in frontmatter."""

    def test_action_no_params(self) -> None:
        source = dedent("""\
            ---
            action refresh()
            ---

            <div />
        """)
        component = parse(source)
        assert len(component.actions) == 1
        act = component.actions[0]
        assert act.name == "refresh"
        assert act.params == ()

    def test_action_single_param(self) -> None:
        source = dedent("""\
            ---
            action add_todo(text: str)
            ---

            <div />
        """)
        component = parse(source)
        assert len(component.actions) == 1
        act = component.actions[0]
        assert act.name == "add_todo"
        assert len(act.params) == 1
        assert act.params[0].name == "text"
        assert act.params[0].type_expr == "str"

    def test_action_multiple_params(self) -> None:
        source = dedent("""\
            ---
            action update_user(name: str, age: int = 0)
            ---

            <div />
        """)
        component = parse(source)
        assert len(component.actions) == 1
        act = component.actions[0]
        assert act.name == "update_user"
        assert len(act.params) == 2
        assert act.params[0].name == "name"
        assert act.params[0].type_expr == "str"
        assert act.params[1].name == "age"
        assert act.params[1].type_expr == "int"
        assert act.params[1].default == "0"

    def test_multiple_actions(self) -> None:
        source = dedent("""\
            ---
            action add_todo(text: str)
            action delete_todo(id: int)
            ---

            <div />
        """)
        component = parse(source)
        assert len(component.actions) == 2
        assert component.actions[0].name == "add_todo"
        assert component.actions[1].name == "delete_todo"

    def test_action_with_other_declarations(self) -> None:
        source = dedent("""\
            ---
            state count = 0
            action increment()
            middleware "auth"
            ---

            <div />
        """)
        component = parse(source)
        assert len(component.actions) == 1
        assert len(component.states) == 1
        assert len(component.middleware) == 1


class TestActionCompiler:
    """Tests for compiling @action_name references."""

    def test_action_ref_compiles_to_pjx_route(self) -> None:
        source = dedent("""\
            ---
            action add_todo(text: str)
            ---

            <form action:post="@add_todo">
              <input name="text" />
            </form>
        """)
        component = parse(source)
        compiler = Compiler()
        result = compiler.compile(component)
        assert 'hx-post="/_pjx/actions/add_todo"' in result.jinja_source

    def test_action_ref_preserves_non_ref_urls(self) -> None:
        source = dedent("""\
            ---
            ---

            <form action:post="/api/todos">
              <input name="text" />
            </form>
        """)
        component = parse(source)
        compiler = Compiler()
        result = compiler.compile(component)
        assert 'hx-post="/api/todos"' in result.jinja_source

    def test_action_ref_with_get_verb(self) -> None:
        source = dedent("""\
            ---
            action search(query: str)
            ---

            <div action:get="@search"></div>
        """)
        component = parse(source)
        compiler = Compiler()
        result = compiler.compile(component)
        assert 'hx-get="/_pjx/actions/search"' in result.jinja_source


class TestRouteHandlerActions:
    """Tests for RouteHandler.action() decorator."""

    def test_register_action(self) -> None:
        handler = RouteHandler()

        @handler.action("add_todo")
        async def add_todo(request):
            return "<li>New todo</li>"

        assert "add_todo" in handler._actions
        assert handler._actions["add_todo"] is add_todo

    def test_multiple_actions(self) -> None:
        handler = RouteHandler()

        @handler.action("add")
        async def add(request):
            pass

        @handler.action("delete")
        async def delete(request):
            pass

        assert len(handler._actions) == 2
        assert "add" in handler._actions
        assert "delete" in handler._actions


class TestActionFormatter:
    """Tests for formatter handling of action declarations."""

    def test_format_action_no_params(self) -> None:
        from pjx.formatter import format_source

        source = dedent("""\
            ---
            action refresh()
            ---

            <div />
        """)
        result = format_source(source)
        assert "action refresh()" in result

    def test_format_action_with_params(self) -> None:
        from pjx.formatter import format_source

        source = dedent("""\
            ---
            action add_todo(text: str, done: bool = false)
            ---

            <div />
        """)
        result = format_source(source)
        assert "action add_todo(text: str, done: bool = false)" in result

    def test_format_action_canonical_order(self) -> None:
        """Actions should appear after middleware in canonical order... actually before middleware."""
        from pjx.formatter import format_source

        source = dedent("""\
            ---
            middleware "auth"
            action refresh()
            state count = 0
            ---

            <div />
        """)
        result = format_source(source)
        lines = result.split("---\n")[1].strip().split("\n")
        # Order: state → action → middleware
        assert lines[0].startswith("state")
        assert lines[1].startswith("action")
        assert lines[2].startswith("middleware")
