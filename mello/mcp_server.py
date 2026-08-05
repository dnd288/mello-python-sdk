import os
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, Type

from mello.client import MelloClient, UNSET
from mello.serialize import serialize as _serialize

ClientFactory = Callable[[], Any]


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
            "pic_user_id",
            "supervisor_id",
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
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError:
            try:
                from mcp.server.mcpserver import FastMCP
            except ImportError:
                from mcp.server.mcpserver import MCPServer as FastMCP

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
    def list_labels(board_id: str) -> Any:
        """List labels on a Mello board."""
        return _serialize(client().list_labels(board_id))

    @server.tool()
    def create_label(board_id: str, name: str, color: Optional[str] = None) -> Any:
        """Create a label on a Mello board."""
        return _serialize(client().create_label(board_id, name, color))

    @server.tool()
    def update_label(label_id: str, updates: Optional[Dict[str, Any]] = None) -> Any:
        """Update label fields: name, color."""
        kwargs = _present_update_kwargs(updates, ["name", "color"])
        return _serialize(client().update_label(label_id, **kwargs))

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
        """Update ticket fields, including nullable pic_user_id, supervisor_id, and date fields."""
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

    @server.tool()
    def create_checklist(
        ticket_id: str, title: str, position: Optional[int] = None
    ) -> Any:
        """Create a checklist for a ticket."""
        return _serialize(client().create_checklist(ticket_id, title, position))

    @server.tool()
    def update_checklist(
        checklist_id: str, updates: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Update checklist fields: title, position."""
        kwargs = _present_update_kwargs(updates, ["title", "position"])
        return _serialize(client().update_checklist(checklist_id, **kwargs))

    @server.tool()
    def delete_checklist(checklist_id: str) -> None:
        """Delete a checklist and its items."""
        client().delete_checklist(checklist_id)
        return None

    @server.tool()
    def create_checklist_item(
        checklist_id: str, title: str, position: Optional[int] = None
    ) -> Any:
        """Create an item inside a checklist."""
        return _serialize(client().create_checklist_item(checklist_id, title, position))

    @server.tool()
    def update_checklist_item(
        checklist_item_id: str, updates: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Update checklist item fields: title, is_checked, position."""
        kwargs = _present_update_kwargs(updates, ["title", "is_checked", "position"])
        return _serialize(client().update_checklist_item(checklist_item_id, **kwargs))

    @server.tool()
    def delete_checklist_item(checklist_item_id: str) -> None:
        """Delete a checklist item."""
        client().delete_checklist_item(checklist_item_id)
        return None

    @server.tool()
    def list_webhooks() -> Any:
        """List webhooks."""
        return _serialize(client().list_webhooks())

    @server.tool()
    def create_webhook(
        workspace_id: str,
        model_type: str,
        model_id: str,
        callback_url: str,
        event: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> Any:
        """Create a webhook."""
        return _serialize(
            client().create_webhook(
                workspace_id,
                model_type,
                model_id,
                callback_url,
                event=event,
                description=description,
            )
        )

    @server.tool()
    def update_webhook(
        webhook_id: str, updates: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Update webhook fields: active, events, description, callback_url."""
        kwargs = _present_update_kwargs(
            updates, ["active", "events", "description", "callback_url"]
        )
        return _serialize(client().update_webhook(webhook_id, **kwargs))

    @server.tool()
    def delete_webhook(webhook_id: str) -> None:
        """Delete a webhook."""
        client().delete_webhook(webhook_id)
        return None

    @server.tool()
    def list_webhook_deliveries(webhook_id: str) -> Any:
        """List webhook delivery attempts."""
        return _serialize(client().list_webhook_deliveries(webhook_id))

    @server.tool()
    def redeliver_webhook_event(webhook_id: str, delivery_id: str) -> None:
        """Redeliver a webhook event delivery."""
        client().redeliver_webhook_event(webhook_id, delivery_id)
        return None

    @server.tool()
    def list_github_installations(workspace_id: str) -> Any:
        """List GitHub installations in a workspace."""
        return _serialize(client().list_github_installations(workspace_id))

    @server.tool()
    def list_github_repositories(workspace_id: str) -> Any:
        """List GitHub repositories in a workspace."""
        return _serialize(client().list_github_repositories(workspace_id))

    @server.tool()
    def list_github_board_repositories(workspace_id: str, board_id: str) -> Any:
        """List GitHub repositories connected to a board."""
        return _serialize(
            client().list_github_board_repositories(workspace_id, board_id)
        )

    @server.tool()
    def replace_github_board_repositories(
        workspace_id: str, board_id: str, repositories: List[Dict[str, int]]
    ) -> Any:
        """Replace GitHub repositories connected to a board."""
        return _serialize(
            client().replace_github_board_repositories(
                workspace_id, board_id, repositories
            )
        )

    @server.tool()
    def start_github_connect(
        workspace_id: str,
        replace: Optional[bool] = None,
        board_id: Optional[str] = None,
    ) -> Any:
        """Start GitHub App installation flow."""
        return _serialize(
            client().start_github_connect(
                workspace_id, replace=replace, board_id=board_id
            )
        )

    @server.tool()
    def delete_github_installation(workspace_id: str, installation_id: str) -> None:
        """Delete a GitHub installation from a workspace."""
        client().delete_github_installation(workspace_id, installation_id)
        return None

    @server.tool()
    def search_github_objects(
        ticket_id: str,
        q: Optional[str] = None,
        type: Optional[str] = None,
        page: Optional[int] = None,
    ) -> Any:
        """Search GitHub objects for a ticket."""
        return _serialize(
            client().search_github_objects(ticket_id, q=q, type=type, page=page)
        )

    @server.tool()
    def create_github_link(
        ticket_id: str,
        installation_id: int,
        github_repo_id: int,
        kind: str,
        number: Optional[int] = None,
        branch_name: Optional[str] = None,
    ) -> Any:
        """Link a GitHub object to a ticket."""
        return _serialize(
            client().create_github_link(
                ticket_id,
                installation_id,
                github_repo_id,
                kind,
                number=number,
                branch_name=branch_name,
            )
        )

    @server.tool()
    def delete_github_link(ticket_id: str, link_id: str) -> None:
        """Unlink a GitHub object from a ticket."""
        client().delete_github_link(ticket_id, link_id)
        return None

    @server.tool()
    def create_attachment(
        ticket_id: str,
        filename: str,
        file_content_base64: str,
        content_type: Optional[str] = None,
    ) -> Any:
        """Upload an attachment to a ticket (requires Base64 encoded file content)."""
        import base64

        file_content = base64.b64decode(file_content_base64)
        return _serialize(
            client().create_attachment(ticket_id, filename, file_content, content_type)
        )

    @server.tool()
    def download_attachment(attachment_id: str) -> str:
        """Download attachment content as a Base64 encoded string."""
        import base64

        content = client().download_attachment(attachment_id)
        return base64.b64encode(content).decode("utf-8")

    return server


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    server = create_mcp_server()

    if transport in ("streamable-http", "sse"):
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "8000"))
        # FastMCP reads bind settings from its settings object.
        server.settings.host = host
        server.settings.port = port
        server.run(transport=transport)
    else:
        server.run()


if __name__ == "__main__":
    main()
