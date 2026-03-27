"""Integration tests for HTMX endpoints in the example app.

Tests the real endpoints against the real app with TestClient,
protecting the interactive surface (counter, todos, search, messages)
from regressions.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """Sync HTTP client for the example app."""
    from app.main import app

    return TestClient(app, follow_redirects=False)


@pytest.fixture(autouse=True)
def _reset_app_state():
    """Snapshot and restore mutable in-memory state between tests."""
    from app import services

    original_todos = [dict(t) for t in services.todos_db]
    original_counter = dict(services.server_counter)
    original_messages = list(services.messages_db)
    yield
    services.todos_db[:] = original_todos
    services.server_counter.update(original_counter)
    services.server_counter["count"] = original_counter["count"]
    services.messages_db[:] = original_messages


def _get_csrf(client: TestClient) -> str:
    """Fetch a CSRF token by visiting a page."""
    resp = client.get("/login")
    return resp.cookies.get("_csrf", "")


def _post(client: TestClient, url: str, csrf: str, **kwargs) -> "Response":  # noqa: F821
    """POST with CSRF token."""
    return client.post(
        url,
        headers={"X-CSRFToken": csrf},
        cookies={"_csrf": csrf},
        **kwargs,
    )


def _put(client: TestClient, url: str, csrf: str, **kwargs) -> "Response":  # noqa: F821
    """PUT with CSRF token."""
    return client.put(
        url,
        headers={"X-CSRFToken": csrf},
        cookies={"_csrf": csrf},
        **kwargs,
    )


def _delete(client: TestClient, url: str, csrf: str, **kwargs) -> "Response":  # noqa: F821
    """DELETE with CSRF token."""
    return client.delete(
        url,
        headers={"X-CSRFToken": csrf},
        cookies={"_csrf": csrf},
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Counter endpoints
# ---------------------------------------------------------------------------


class TestCounterEndpoints:
    def test_increment_returns_updated_count(self, client: TestClient) -> None:
        csrf = _get_csrf(client)
        resp = _post(client, "/htmx/counter/increment", csrf)
        assert resp.status_code == 200
        assert "counter__value" in resp.text
        assert ">1<" in resp.text

    def test_decrement_below_zero(self, client: TestClient) -> None:
        csrf = _get_csrf(client)
        resp = _post(client, "/htmx/counter/decrement", csrf)
        assert resp.status_code == 200
        assert ">-1<" in resp.text

    def test_reset_returns_zero(self, client: TestClient) -> None:
        csrf = _get_csrf(client)
        _post(client, "/htmx/counter/increment", csrf)
        _post(client, "/htmx/counter/increment", csrf)
        resp = _post(client, "/htmx/counter/reset", csrf)
        assert resp.status_code == 200
        assert ">0<" in resp.text

    def test_increment_without_csrf_returns_403(self, client: TestClient) -> None:
        resp = client.post("/htmx/counter/increment")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Todo endpoints
# ---------------------------------------------------------------------------


class TestTodoEndpoints:
    def test_add_todo_appears_in_response(self, client: TestClient) -> None:
        csrf = _get_csrf(client)
        resp = _post(client, "/htmx/todos/add", csrf, data={"text": "New task"})
        assert resp.status_code == 200
        assert "New task" in resp.text

    def test_add_empty_todo_no_change(self, client: TestClient) -> None:
        csrf = _get_csrf(client)
        resp = _post(client, "/htmx/todos/add", csrf, data={"text": ""})
        assert resp.status_code == 200
        # Original 3 todos still present, no empty one added
        assert "Learn PJX" in resp.text
        assert "Build components" in resp.text
        assert "Ship it" in resp.text

    def test_toggle_changes_done_class(self, client: TestClient) -> None:
        csrf = _get_csrf(client)
        # Todo 0 is "Learn PJX" (done=True) — toggling makes it not done
        resp = _post(client, "/htmx/todos/0/toggle", csrf)
        assert resp.status_code == 200
        # After toggle, "Learn PJX" should NOT have todo--done class
        # Find the todo-0 div and check it doesn't have todo--done
        text = resp.text
        assert "Learn PJX" in text
        # The todo-0 div should now be without done class
        idx = text.find('id="todo-0"')
        assert idx != -1
        # Get the containing div tag
        div_start = text.rfind("<div", 0, idx)
        div_snippet = text[div_start : idx + 20]
        assert "todo--done" not in div_snippet

    def test_delete_removes_from_list(self, client: TestClient) -> None:
        csrf = _get_csrf(client)
        resp = _delete(client, "/htmx/todos/0", csrf)
        assert resp.status_code == 200
        assert "Learn PJX" not in resp.text

    def test_edit_updates_text(self, client: TestClient) -> None:
        csrf = _get_csrf(client)
        resp = _put(client, "/htmx/todos/1", csrf, data={"text": "Updated"})
        assert resp.status_code == 200
        assert "Updated" in resp.text
        assert "Build components" not in resp.text

    def test_filter_done_shows_only_completed(self, client: TestClient) -> None:
        resp = client.get("/htmx/todos/filter?status=done")
        assert resp.status_code == 200
        assert "Learn PJX" in resp.text
        assert "Build components" not in resp.text
        assert "Ship it" not in resp.text

    def test_filter_pending_shows_only_incomplete(self, client: TestClient) -> None:
        resp = client.get("/htmx/todos/filter?status=pending")
        assert resp.status_code == 200
        assert "Learn PJX" not in resp.text
        assert "Build components" in resp.text
        assert "Ship it" in resp.text

    def test_filter_all_shows_everything(self, client: TestClient) -> None:
        resp = client.get("/htmx/todos/filter?status=all")
        assert resp.status_code == 200
        assert "Learn PJX" in resp.text
        assert "Build components" in resp.text
        assert "Ship it" in resp.text

    def test_todo_stats_displayed(self, client: TestClient) -> None:
        resp = client.get("/htmx/todos/filter?status=all")
        assert "todo-stats" in resp.text
        assert "1/3 completed" in resp.text


# ---------------------------------------------------------------------------
# Search endpoints
# ---------------------------------------------------------------------------


class TestSearchEndpoints:
    def test_search_returns_matching_user(self, client: TestClient) -> None:
        resp = client.get("/htmx/search?query=alice")
        assert resp.status_code == 200
        assert "Alice" in resp.text
        assert "alice@example.com" in resp.text

    def test_search_empty_shows_prompt(self, client: TestClient) -> None:
        resp = client.get("/htmx/search?query=")
        assert resp.status_code == 200
        assert "Type to search" in resp.text

    def test_search_no_match_shows_empty_message(self, client: TestClient) -> None:
        resp = client.get("/htmx/search?query=zzz")
        assert resp.status_code == 200
        assert "No results" in resp.text

    def test_search_case_insensitive(self, client: TestClient) -> None:
        resp = client.get("/htmx/search?query=BOB")
        assert resp.status_code == 200
        assert "Bob" in resp.text


# ---------------------------------------------------------------------------
# Message endpoints
# ---------------------------------------------------------------------------


class TestMessageEndpoints:
    def test_message_valid_user_returns_success_toast(self, client: TestClient) -> None:
        csrf = _get_csrf(client)
        resp = _post(client, "/htmx/message/1", csrf)
        assert resp.status_code == 200
        assert "Message sent to Alice" in resp.text
        assert "toast--success" in resp.text

    def test_message_invalid_user_returns_error_toast(self, client: TestClient) -> None:
        csrf = _get_csrf(client)
        resp = _post(client, "/htmx/message/999", csrf)
        assert resp.status_code == 200
        assert "User not found" in resp.text
        assert "toast--error" in resp.text
