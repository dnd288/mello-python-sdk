from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pytest

from mello.client import UNSET


class FakeFastMCP:
    def __init__(self, name: str):
        self.name = name
        self.tools: Dict[str, Callable[..., Any]] = {}
        self.ran = False

    def tool(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.tools[func.__name__] = func
            return func

        return decorator

    def run(self) -> None:
        self.ran = True


@dataclass
class NestedThing:
    at: datetime


@dataclass
class ExampleThing:
    name: str
    nested: NestedThing
    values: List[Any]


def test_serialize_recursively_converts_dataclasses_and_datetimes() -> None:
    from mello.mcp_server import _serialize

    data = ExampleThing(
        name="demo",
        nested=NestedThing(at=datetime(2026, 6, 9, 1, 2, 3, tzinfo=timezone.utc)),
        values=[NestedThing(at=datetime(2026, 6, 10, 4, 5, 6))],
    )

    assert _serialize(data) == {
        "name": "demo",
        "nested": {"at": "2026-06-09T01:02:03+00:00"},
        "values": [{"at": "2026-06-10T04:05:06"}],
    }


def test_parse_datetime_accepts_iso_strings_and_z_suffix() -> None:
    from mello.mcp_server import _parse_datetime

    assert _parse_datetime(None) is None
    assert _parse_datetime("2026-06-09T01:02:03Z") == datetime(
        2026, 6, 9, 1, 2, 3, tzinfo=timezone.utc
    )


def test_client_from_env_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from mello.mcp_server import _client_from_env

    monkeypatch.delenv("MELLO_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="MELLO_API_KEY"):
        _client_from_env()


def test_client_from_env_uses_optional_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mello.mcp_server import _client_from_env

    monkeypatch.setenv("MELLO_API_KEY", "token-123")
    monkeypatch.setenv("MELLO_BASE_URL", "https://example.test/api")
    monkeypatch.setenv("MELLO_TIMEOUT", "12.5")

    client = _client_from_env()

    assert client.base_url == "https://example.test/api"
    assert client.timeout == 12.5
    assert client.session.headers["Authorization"] == "Bearer token-123"


class FakeClient:
    def __init__(self) -> None:
        self.calls: List[Any] = []

    def get_current_user(self) -> Dict[str, Any]:
        self.calls.append(("get_current_user",))
        return {"id": "user-1", "created_at": datetime(2026, 6, 9)}

    def list_workspaces(self) -> List[Dict[str, str]]:
        self.calls.append(("list_workspaces",))
        return [{"id": "workspace-1"}]

    def list_workspace_members(self, workspace_id: str) -> List[Dict[str, str]]:
        self.calls.append(("list_workspace_members", workspace_id))
        return [{"workspace_id": workspace_id}]

    def list_workspace_boards(self, workspace_id: str) -> List[Dict[str, str]]:
        self.calls.append(("list_workspace_boards", workspace_id))
        return [{"workspace_id": workspace_id, "id": "board-1"}]

    def create_board(
        self, workspace_id: str, name: str, code: Optional[str] = None
    ) -> Dict[str, Any]:
        self.calls.append(("create_board", workspace_id, name, code))
        return {"workspace_id": workspace_id, "name": name, "code": code}

    def get_board(self, board_id: str) -> Dict[str, str]:
        self.calls.append(("get_board", board_id))
        return {"id": board_id}

    def update_board(self, board_id: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("update_board", board_id, kwargs))
        return {"id": board_id, **kwargs}

    def delete_board(self, board_id: str) -> None:
        self.calls.append(("delete_board", board_id))

    def list_columns(self, board_id: str) -> List[Dict[str, str]]:
        self.calls.append(("list_columns", board_id))
        return [{"board_id": board_id}]

    def create_column(
        self, board_id: str, name: str, position: Optional[int] = None
    ) -> Dict[str, Any]:
        self.calls.append(("create_column", board_id, name, position))
        return {"board_id": board_id, "name": name, "position": position}

    def reorder_columns(self, board_id: str, column_ids: List[str]) -> None:
        self.calls.append(("reorder_columns", board_id, column_ids))

    def update_column(self, column_id: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("update_column", column_id, kwargs))
        return {"id": column_id, **kwargs}

    def list_board_tickets(self, board_id: str) -> List[Dict[str, str]]:
        self.calls.append(("list_board_tickets", board_id))
        return [{"board_id": board_id}]

    def create_ticket(
        self,
        column_id: str,
        title: str,
        description: Optional[str] = None,
        position: Optional[int] = None,
    ) -> Dict[str, Any]:
        self.calls.append(("create_ticket", column_id, title, description, position))
        return {"column_id": column_id, "title": title}

    def get_ticket(self, ticket_id: str) -> Dict[str, str]:
        self.calls.append(("get_ticket", ticket_id))
        return {"id": ticket_id}

    def update_ticket(self, ticket_id: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("update_ticket", ticket_id, kwargs))
        return {"id": ticket_id, **kwargs}

    def move_ticket(
        self, ticket_id: str, column_id: str, position: int
    ) -> Dict[str, Any]:
        self.calls.append(("move_ticket", ticket_id, column_id, position))
        return {"ticket_id": ticket_id, "column_id": column_id, "position": position}

    def list_comments(self, ticket_id: str) -> List[Dict[str, str]]:
        self.calls.append(("list_comments", ticket_id))
        return [{"ticket_id": ticket_id}]

    def create_comment(
        self, ticket_id: str, body: str, body_html: Optional[str] = None
    ) -> Dict[str, Any]:
        self.calls.append(("create_comment", ticket_id, body, body_html))
        return {"ticket_id": ticket_id, "body": body, "body_html": body_html}

    def list_history(self, ticket_id: str) -> List[Dict[str, str]]:
        self.calls.append(("list_history", ticket_id))
        return [{"ticket_id": ticket_id}]

    def search_tickets(self, workspace_id: str, q: str) -> List[Dict[str, str]]:
        self.calls.append(("search_tickets", workspace_id, q))
        return [{"workspace_id": workspace_id, "q": q}]

    def create_checklist(self, ticket_id: str, title: str) -> Dict[str, Any]:
        self.calls.append(("create_checklist", ticket_id, title))
        return {"ticket_id": ticket_id, "title": title, "id": "chk-1"}

    def create_checklist_item(self, checklist_id: str, title: str) -> Dict[str, Any]:
        self.calls.append(("create_checklist_item", checklist_id, title))
        return {"checklist_id": checklist_id, "title": title, "id": "chki-1"}

    def update_checklist_item(
        self, checklist_item_id: str, is_checked: bool
    ) -> Dict[str, Any]:
        self.calls.append(("update_checklist_item", checklist_item_id, is_checked))
        return {"id": checklist_item_id, "is_checked": is_checked}

    def create_attachment(
        self,
        ticket_id: str,
        filename: str,
        file_content: bytes,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.calls.append(
            ("create_attachment", ticket_id, filename, file_content, content_type)
        )
        return {"ticket_id": ticket_id, "filename": filename, "id": "att-1"}

    def download_attachment(self, attachment_id: str) -> bytes:
        self.calls.append(("download_attachment", attachment_id))
        return b"fakebytescontent"


def build_fake_server() -> Any:
    from mello.mcp_server import create_mcp_server

    client = FakeClient()
    server = create_mcp_server(client_factory=lambda: client, server_cls=FakeFastMCP)
    return server, client


def test_create_mcp_server_registers_full_tool_surface() -> None:
    server, _client = build_fake_server()

    assert sorted(server.tools) == [
        "create_attachment",
        "create_board",
        "create_checklist",
        "create_checklist_item",
        "create_column",
        "create_comment",
        "create_ticket",
        "delete_board",
        "download_attachment",
        "get_board",
        "get_current_user",
        "get_ticket",
        "list_board_tickets",
        "list_columns",
        "list_comments",
        "list_history",
        "list_workspace_boards",
        "list_workspace_members",
        "list_workspaces",
        "move_ticket",
        "reorder_columns",
        "search_tickets",
        "update_board",
        "update_checklist_item",
        "update_column",
        "update_ticket",
    ]


def test_registered_tools_delegate_to_client_and_serialize_results() -> None:
    server, client = build_fake_server()

    assert server.tools["get_current_user"]() == {
        "id": "user-1",
        "created_at": "2026-06-09T00:00:00",
    }
    assert server.tools["create_ticket"](
        column_id="column-1", title="Ship MCP", description="Do it", position=2
    ) == {"column_id": "column-1", "title": "Ship MCP"}
    assert server.tools["delete_board"](board_id="board-1") is None
    assert client.calls[-1] == ("delete_board", "board-1")

    # Checklist tests
    assert server.tools["create_checklist"](ticket_id="ticket-1", title="Setup") == {
        "ticket_id": "ticket-1",
        "title": "Setup",
        "id": "chk-1",
    }
    assert client.calls[-1] == ("create_checklist", "ticket-1", "Setup")

    assert server.tools["create_checklist_item"](
        checklist_id="chk-1", title="Task 1"
    ) == {"checklist_id": "chk-1", "title": "Task 1", "id": "chki-1"}
    assert client.calls[-1] == ("create_checklist_item", "chk-1", "Task 1")

    assert server.tools["update_checklist_item"](
        checklist_item_id="chki-1", is_checked=True
    ) == {"id": "chki-1", "is_checked": True}
    assert client.calls[-1] == ("update_checklist_item", "chki-1", True)

    # Attachment tests
    import base64

    content_b64 = base64.b64encode(b"hello world").decode("utf-8")
    assert server.tools["create_attachment"](
        ticket_id="ticket-1",
        filename="test.txt",
        file_content_base64=content_b64,
        content_type="text/plain",
    ) == {"ticket_id": "ticket-1", "filename": "test.txt", "id": "att-1"}
    assert client.calls[-1] == (
        "create_attachment",
        "ticket-1",
        "test.txt",
        b"hello world",
        "text/plain",
    )

    assert server.tools["download_attachment"](
        attachment_id="att-1"
    ) == base64.b64encode(b"fakebytescontent").decode("utf-8")
    assert client.calls[-1] == ("download_attachment", "att-1")


def test_update_tools_preserve_omitted_and_explicit_null_values() -> None:
    server, client = build_fake_server()

    assert server.tools["update_ticket"](
        ticket_id="ticket-1",
        updates={"title": "New title", "assignee_id": None},
    ) == {"id": "ticket-1", "title": "New title", "assignee_id": None}

    method, ticket_id, kwargs = client.calls[-1]
    assert method == "update_ticket"
    assert ticket_id == "ticket-1"
    assert kwargs["title"] == "New title"
    assert kwargs["assignee_id"] is None
    assert "description" not in kwargs

    server.tools["update_board"](board_id="board-1", updates={})
    _method, _board_id, empty_kwargs = client.calls[-1]
    assert empty_kwargs == {}


def test_update_ticket_parses_date_update_strings() -> None:
    server, client = build_fake_server()

    server.tools["update_ticket"](
        ticket_id="ticket-1",
        updates={"start_date": "2026-06-09T01:02:03Z", "end_date": None},
    )

    _method, _ticket_id, kwargs = client.calls[-1]
    assert kwargs["start_date"] == datetime(2026, 6, 9, 1, 2, 3, tzinfo=timezone.utc)
    assert kwargs["end_date"] is None


def test_unknown_update_fields_are_rejected() -> None:
    server, _client = build_fake_server()

    with pytest.raises(ValueError, match="Unsupported update field"):
        server.tools["update_ticket"]("ticket-1", {"not_a_field": "nope"})


def test_to_update_kwargs_maps_missing_fields_to_unset() -> None:
    from mello.mcp_server import _to_update_kwargs

    kwargs = _to_update_kwargs({"name": "Next"}, ["name", "color"])

    assert kwargs["name"] == "Next"
    assert kwargs["color"] is UNSET


def test_pyproject_declares_mcp_extra_and_console_script() -> None:
    pyproject = Path("pyproject.toml").read_text()

    assert "mcp = [" in pyproject
    assert '"mcp>=' in pyproject
    assert "[project.scripts]" in pyproject
    assert 'mello-mcp-server = "mello.mcp_server:main"' in pyproject
