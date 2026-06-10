import os
from dataclasses import fields, is_dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, Type

from mello.client import MelloClient, UNSET


ClientFactory = Callable[[], Any]


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()

    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _serialize(getattr(value, field.name))
            for field in fields(value)
        }

    if isinstance(value, list):
        return [_serialize(item) for item in value]

    if isinstance(value, tuple):
        return [_serialize(item) for item in value]

    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}

    return value


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def _client_from_env() -> MelloClient:
    token = os.environ.get("MELLO_API_KEY")
    if not token:
        raise RuntimeError("MELLO_API_KEY is required to run the Mello MCP server")

    base_url = os.environ.get("MELLO_BASE_URL", "https://mello.mezon.vn/api/v1")
    timeout = float(os.environ.get("MELLO_TIMEOUT", "30.0"))
    return MelloClient(token=token, base_url=base_url, timeout=timeout)


def _validate_update_fields(
    updates: Dict[str, Any], allowed_fields: Iterable[str]
) -> None:
    allowed = set(allowed_fields)
    for field_name in updates:
        if field_name not in allowed:
            raise ValueError(f"Unsupported update field: {field_name}")


def _to_update_kwargs(
    updates: Dict[str, Any], allowed_fields: Iterable[str]
) -> Dict[str, Any]:
    _validate_update_fields(updates, allowed_fields)
    return {
        field_name: updates[field_name] if field_name in updates else UNSET
        for field_name in allowed_fields
    }


def _present_update_kwargs(
    updates: Optional[Dict[str, Any]], allowed_fields: Iterable[str]
) -> Dict[str, Any]:
    if updates is None:
        updates = {}
    _validate_update_fields(updates, allowed_fields)
    return dict(updates)


def _ticket_update_kwargs(updates: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    kwargs = _present_update_kwargs(
        updates,
        [
            "title",
            "description",
            "description_html",
            "assignee_id",
            "start_date",
            "end_date",
        ],
    )

    for field_name in ("start_date", "end_date"):
        if field_name in kwargs and isinstance(kwargs[field_name], str):
            kwargs[field_name] = _parse_datetime(kwargs[field_name])

    return kwargs


def create_mcp_server(
    client_factory: Optional[ClientFactory] = None,
    server_cls: Optional[Type[Any]] = None,
) -> Any:
    if client_factory is None:
        client_factory = _client_from_env

    if server_cls is None:
        from mcp.server.fastmcp import FastMCP

        server_cls = FastMCP

    server = server_cls("Mello")

    def client() -> Any:
        return client_factory()

    @server.tool()
    def get_current_user() -> Any:
        """Get the authenticated Mello user."""
        return _serialize(client().get_current_user())

    @server.tool()
    def list_workspaces() -> Any:
        """List token-accessible Mello workspaces."""
        return _serialize(client().list_workspaces())

    @server.tool()
    def list_workspace_members(workspace_id: str) -> Any:
        """List members in a Mello workspace."""
        return _serialize(client().list_workspace_members(workspace_id))

    @server.tool()
    def list_workspace_boards(workspace_id: str) -> Any:
        """List boards in a Mello workspace."""
        return _serialize(client().list_workspace_boards(workspace_id))

    @server.tool()
    def create_board(workspace_id: str, name: str, code: Optional[str] = None) -> Any:
        """Create a board in a Mello workspace."""
        return _serialize(client().create_board(workspace_id, name, code))

    @server.tool()
    def get_board(board_id: str) -> Any:
        """Get a Mello board with columns and tickets."""
        return _serialize(client().get_board(board_id))

    @server.tool()
    def update_board(board_id: str, updates: Optional[Dict[str, Any]] = None) -> Any:
        """Update board fields: name, background_color, cover_image_url."""
        kwargs = _present_update_kwargs(
            updates, ["name", "background_color", "cover_image_url"]
        )
        return _serialize(client().update_board(board_id, **kwargs))

    @server.tool()
    def delete_board(board_id: str) -> None:
        """Delete a Mello board."""
        client().delete_board(board_id)
        return None

    @server.tool()
    def list_columns(board_id: str) -> Any:
        """List columns on a Mello board."""
        return _serialize(client().list_columns(board_id))

    @server.tool()
    def create_column(board_id: str, name: str, position: Optional[int] = None) -> Any:
        """Create a column on a Mello board."""
        return _serialize(client().create_column(board_id, name, position))

    @server.tool()
    def reorder_columns(board_id: str, column_ids: List[str]) -> None:
        """Reorder columns on a Mello board."""
        client().reorder_columns(board_id, column_ids)
        return None

    @server.tool()
    def update_column(column_id: str, updates: Optional[Dict[str, Any]] = None) -> Any:
        """Update column fields: name, position, color."""
        kwargs = _present_update_kwargs(updates, ["name", "position", "color"])
        return _serialize(client().update_column(column_id, **kwargs))

    @server.tool()
    def list_board_tickets(board_id: str) -> Any:
        """List tickets on a Mello board."""
        return _serialize(client().list_board_tickets(board_id))

    @server.tool()
    def create_ticket(
        column_id: str,
        title: str,
        description: Optional[str] = None,
        position: Optional[int] = None,
    ) -> Any:
        """Create a ticket in a Mello column."""
        return _serialize(
            client().create_ticket(column_id, title, description, position)
        )

    @server.tool()
    def get_ticket(ticket_id: str) -> Any:
        """Get a Mello ticket."""
        return _serialize(client().get_ticket(ticket_id))

    @server.tool()
    def update_ticket(ticket_id: str, updates: Optional[Dict[str, Any]] = None) -> Any:
        """Update ticket fields, including nullable assignee and date fields."""
        kwargs = _ticket_update_kwargs(updates)
        return _serialize(client().update_ticket(ticket_id, **kwargs))

    @server.tool()
    def move_ticket(ticket_id: str, column_id: str, position: int) -> Any:
        """Move a Mello ticket to another column and position."""
        return _serialize(client().move_ticket(ticket_id, column_id, position))

    @server.tool()
    def list_comments(ticket_id: str) -> Any:
        """List comments on a Mello ticket."""
        return _serialize(client().list_comments(ticket_id))

    @server.tool()
    def create_comment(
        ticket_id: str, body: str, body_html: Optional[str] = None
    ) -> Any:
        """Create a comment on a Mello ticket."""
        return _serialize(client().create_comment(ticket_id, body, body_html))

    @server.tool()
    def list_history(ticket_id: str) -> Any:
        """List history entries for a Mello ticket."""
        return _serialize(client().list_history(ticket_id))

    @server.tool()
    def search_tickets(workspace_id: str, q: str) -> Any:
        """Search tickets in a Mello workspace."""
        return _serialize(client().search_tickets(workspace_id, q))

    return server


def main() -> None:
    create_mcp_server().run()


if __name__ == "__main__":
    main()
