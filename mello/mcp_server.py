import argparse
import base64
from datetime import datetime
import inspect
import os
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type

from mello.client import MelloClient, UNSET
from mello.serialize import serialize as _serialize

try:
    from mcp.server.fastmcp import Context, FastMCP
except ImportError:
    try:
        from mcp.server.mcpserver import Context, FastMCP  # type: ignore
    except ImportError:
        Context = Any  # type: ignore
        FastMCP = Any  # type: ignore

ClientFactory = Callable[..., Any]

# In-memory client cache: (token, base_url, timeout) -> MelloClient
_client_cache: Dict[Tuple[str, str, float], MelloClient] = {}
# Session ID -> token mapping for SSE connections
_session_api_keys: Dict[str, str] = {}


def _client_from_env() -> MelloClient:
    token = os.environ.get("MELLO_API_KEY")
    if not token:
        raise RuntimeError("MELLO_API_KEY is required to run the Mello MCP server")

    base_url = os.environ.get("MELLO_BASE_URL", "https://mello.mezon.vn/api/v1")
    timeout = float(os.environ.get("MELLO_TIMEOUT", "30.0"))
    return MelloClient(token=token, base_url=base_url, timeout=timeout)


def _get_cached_client(token: str, base_url: str, timeout: float) -> MelloClient:
    cache_key = (token, base_url, timeout)
    if cache_key not in _client_cache:
        _client_cache[cache_key] = MelloClient(
            token=token, base_url=base_url, timeout=timeout
        )
    return _client_cache[cache_key]


def _extract_token_from_request(request: Any) -> Optional[str]:
    """Extract token from Starlette Request (headers or query parameters)."""
    if request is None:
        return None

    headers = getattr(request, "headers", None)
    if headers and hasattr(headers, "get"):
        auth_header = headers.get("authorization", "")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1].strip()
            if not parts[0].lower().startswith("bearer"):
                return auth_header.strip()

        x_key = headers.get("x-mello-api-key")
        if x_key:
            return str(x_key).strip()

    query_params = getattr(request, "query_params", None)
    if query_params and hasattr(query_params, "get"):
        q_key = query_params.get("api_key")
        if q_key:
            return str(q_key).strip()

    return None


def resolve_token(
    api_key: Optional[str] = None,
    ctx: Optional[Any] = None,
) -> Optional[str]:
    """
    Resolve Mello API key with priority:
    1. Explicit tool argument (api_key)
    2. ctx.session attribute (_mello_api_key)
    3. ctx.request_context.request headers/query parameters
    4. Session ID map (_session_api_keys)
    5. Environment variable MELLO_API_KEY
    """
    if api_key and str(api_key).strip():
        return str(api_key).strip()

    if ctx is not None:
        session = getattr(ctx, "session", None)
        if session is not None and hasattr(session, "_mello_api_key"):
            s_key = getattr(session, "_mello_api_key")
            if s_key and str(s_key).strip():
                return str(s_key).strip()

        req_ctx = getattr(ctx, "request_context", None)
        req = getattr(req_ctx, "request", None)
        if req is not None:
            token = _extract_token_from_request(req)
            if token:
                return token

            q_params = getattr(req, "query_params", None)
            if q_params and hasattr(q_params, "get"):
                sid = q_params.get("session_id")
                if sid and sid in _session_api_keys:
                    return _session_api_keys[sid]

    env_key = os.environ.get("MELLO_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    return None


class MelloSseAuthMiddleware:
    """
    ASGI middleware for SSE transport:
    - Captures API key from GET /sse headers or query parameters and associates it with the session_id
    - Captures API key from POST /messages headers or query parameters
    """

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") == "http":
            try:
                from starlette.requests import Request

                request = Request(scope)
                token = _extract_token_from_request(request)
                session_id = request.query_params.get("session_id")

                if session_id and token:
                    _session_api_keys[session_id] = token

                if scope.get("path", "").endswith("/sse") and token:

                    async def intercepting_send(message: Dict[str, Any]) -> None:
                        if message.get("type") == "http.response.body":
                            body = message.get("body", b"").decode(
                                "utf-8", errors="ignore"
                            )
                            match = re.search(r"session_id=([^&\s\r\n]+)", body)
                            if match:
                                _session_api_keys[match.group(1)] = token
                        await send(message)

                    await self.app(scope, receive, intercepting_send)
                    return
            except Exception:
                pass

        await self.app(scope, receive, send)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


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
            "description_markdown",
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
    if server_cls is None:
        server_cls = FastMCP

    server = server_cls("Mello")

    def get_client(
        api_key: Optional[str] = None, ctx: Optional[Context] = None
    ) -> Any:
        token = resolve_token(api_key=api_key, ctx=ctx)

        if client_factory is not None:
            try:
                sig = inspect.signature(client_factory)
                if len(sig.parameters) > 0:
                    return client_factory(token=token)
            except (ValueError, TypeError):
                pass
            return client_factory()

        if not token:
            raise RuntimeError(
                "Mello API key is required. Please provide it via Authorization header, "
                "X-Mello-Api-Key header, ?api_key query parameter, set_api_key tool, "
                "or MELLO_API_KEY environment variable."
            )

        # If an explicit api_key was passed and ctx is available, remember it for the session
        if api_key and str(api_key).strip() and ctx is not None:
            session = getattr(ctx, "session", None)
            if session is not None and not getattr(session, "_mello_api_key", None):
                setattr(session, "_mello_api_key", str(api_key).strip())

        base_url = os.environ.get("MELLO_BASE_URL", "https://mello.mezon.vn/api/v1")
        timeout = float(os.environ.get("MELLO_TIMEOUT", "30.0"))
        return _get_cached_client(token, base_url, timeout)

    @server.tool()
    def set_api_key(api_key: str, ctx: Optional[Context] = None) -> Dict[str, Any]:
        """
        Set or update the Mello API key (Personal Access Token) for the current session.
        All subsequent tool calls in this session will automatically use this key.
        """
        clean_key = api_key.strip()
        if not clean_key:
            raise ValueError("api_key cannot be empty")

        if ctx is not None:
            session = getattr(ctx, "session", None)
            if session is not None:
                setattr(session, "_mello_api_key", clean_key)

            req_ctx = getattr(ctx, "request_context", None)
            req = getattr(req_ctx, "request", None)
            if req is not None:
                q_params = getattr(req, "query_params", None)
                if q_params and hasattr(q_params, "get"):
                    sid = q_params.get("session_id")
                    if sid:
                        _session_api_keys[sid] = clean_key

        prefix = (
            clean_key[:14] + "..." if len(clean_key) > 14 else clean_key
        )
        return {
            "status": "authenticated",
            "message": "API key successfully set for the current session",
            "token_prefix": prefix,
        }

    @server.tool()
    def get_current_user(
        api_key: Optional[str] = None, ctx: Optional[Context] = None
    ) -> Any:
        """Get the authenticated Mello user."""
        return _serialize(get_client(api_key=api_key, ctx=ctx).get_current_user())

    @server.tool()
    def list_workspaces(
        api_key: Optional[str] = None, ctx: Optional[Context] = None
    ) -> Any:
        """List token-accessible Mello workspaces."""
        return _serialize(get_client(api_key=api_key, ctx=ctx).list_workspaces())

    @server.tool()
    def list_workspace_members(
        workspace_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """List members in a Mello workspace."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).list_workspace_members(workspace_id)
        )

    @server.tool()
    def list_workspace_boards(
        workspace_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """List boards in a Mello workspace."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).list_workspace_boards(workspace_id)
        )

    @server.tool()
    def create_board(
        workspace_id: str,
        name: str,
        code: Optional[str] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Create a board in a Mello workspace."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).create_board(workspace_id, name, code)
        )

    @server.tool()
    def get_board(
        board_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Get a Mello board with columns and tickets."""
        return _serialize(get_client(api_key=api_key, ctx=ctx).get_board(board_id))

    @server.tool()
    def update_board(
        board_id: str,
        updates: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Update board fields: name, background_color, cover_image_url."""
        kwargs = _present_update_kwargs(
            updates, ["name", "background_color", "cover_image_url"]
        )
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).update_board(board_id, **kwargs)
        )

    @server.tool()
    def delete_board(
        board_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> None:
        """Delete a Mello board."""
        get_client(api_key=api_key, ctx=ctx).delete_board(board_id)
        return None

    @server.tool()
    def list_columns(
        board_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """List columns on a Mello board."""
        return _serialize(get_client(api_key=api_key, ctx=ctx).list_columns(board_id))

    @server.tool()
    def create_column(
        board_id: str,
        name: str,
        position: Optional[int] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Create a column on a Mello board."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).create_column(
                board_id, name, position
            )
        )

    @server.tool()
    def reorder_columns(
        board_id: str,
        column_ids: List[str],
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> None:
        """Reorder columns on a Mello board."""
        get_client(api_key=api_key, ctx=ctx).reorder_columns(board_id, column_ids)
        return None

    @server.tool()
    def update_column(
        column_id: str,
        updates: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Update column fields: name, position, color."""
        kwargs = _present_update_kwargs(updates, ["name", "position", "color"])
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).update_column(column_id, **kwargs)
        )

    @server.tool()
    def list_labels(
        board_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """List labels on a Mello board."""
        return _serialize(get_client(api_key=api_key, ctx=ctx).list_labels(board_id))

    @server.tool()
    def create_label(
        board_id: str,
        name: str,
        color: Optional[str] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Create a label on a Mello board."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).create_label(board_id, name, color)
        )

    @server.tool()
    def update_label(
        label_id: str,
        updates: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Update label fields: name, color."""
        kwargs = _present_update_kwargs(updates, ["name", "color"])
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).update_label(label_id, **kwargs)
        )

    @server.tool()
    def delete_label(
        label_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> None:
        """Delete a label."""
        get_client(api_key=api_key, ctx=ctx).delete_label(label_id)
        return None

    @server.tool()
    def list_board_tickets(
        board_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """List tickets on a Mello board."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).list_board_tickets(board_id)
        )

    @server.tool()
    def create_ticket(
        column_id: str,
        title: str,
        description: Optional[str] = None,
        position: Optional[int] = None,
        description_markdown: Optional[str] = None,
        description_html: Optional[str] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Create a ticket in a Mello column."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).create_ticket(
                column_id,
                title,
                description,
                position,
                description_markdown=description_markdown,
                description_html=description_html,
            )
        )

    @server.tool()
    def get_ticket(
        ticket_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Get a Mello ticket."""
        return _serialize(get_client(api_key=api_key, ctx=ctx).get_ticket(ticket_id))

    @server.tool()
    def update_ticket(
        ticket_id: str,
        updates: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """
        Update ticket fields, including nullable pic_user_id, supervisor_id,
        date fields, and description_markdown.
        """
        kwargs = _ticket_update_kwargs(updates)
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).update_ticket(ticket_id, **kwargs)
        )

    @server.tool()
    def move_ticket(
        ticket_id: str,
        column_id: str,
        position: Optional[int] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Move a Mello ticket to another column."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).move_ticket(ticket_id, column_id)
        )

    @server.tool()
    def attach_label_to_ticket(
        ticket_id: str,
        label_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> None:
        """Attach a label to a Mello ticket."""
        get_client(api_key=api_key, ctx=ctx).attach_label_to_ticket(
            ticket_id, label_id
        )
        return None

    @server.tool()
    def detach_label_from_ticket(
        ticket_id: str,
        label_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> None:
        """Detach a label from a Mello ticket."""
        get_client(api_key=api_key, ctx=ctx).detach_label_from_ticket(
            ticket_id, label_id
        )
        return None

    @server.tool()
    def list_comments(
        ticket_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """List comments on a Mello ticket."""
        return _serialize(get_client(api_key=api_key, ctx=ctx).list_comments(ticket_id))

    @server.tool()
    def create_comment(
        ticket_id: str,
        body: Optional[str] = None,
        body_html: Optional[str] = None,
        body_markdown: Optional[str] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Create a comment on a Mello ticket."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).create_comment(
                ticket_id, body=body, body_html=body_html, body_markdown=body_markdown
            )
        )

    @server.tool()
    def list_history(
        ticket_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """List history entries for a Mello ticket."""
        return _serialize(get_client(api_key=api_key, ctx=ctx).list_history(ticket_id))

    @server.tool()
    def search_tickets(
        workspace_id: str,
        q: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Search tickets in a Mello workspace."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).search_tickets(workspace_id, q)
        )

    @server.tool()
    def create_checklist(
        ticket_id: str,
        title: str,
        position: Optional[int] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Create a checklist for a ticket."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).create_checklist(
                ticket_id, title, position
            )
        )

    @server.tool()
    def update_checklist(
        checklist_id: str,
        updates: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Update checklist fields: title, position."""
        kwargs = _present_update_kwargs(updates, ["title", "position"])
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).update_checklist(
                checklist_id, **kwargs
            )
        )

    @server.tool()
    def delete_checklist(
        checklist_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> None:
        """Delete a checklist and its items."""
        get_client(api_key=api_key, ctx=ctx).delete_checklist(checklist_id)
        return None

    @server.tool()
    def create_checklist_item(
        checklist_id: str,
        title: str,
        position: Optional[int] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Create an item inside a checklist."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).create_checklist_item(
                checklist_id, title, position
            )
        )

    @server.tool()
    def update_checklist_item(
        checklist_item_id: str,
        updates: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Update checklist item fields: title, is_checked, position."""
        kwargs = _present_update_kwargs(updates, ["title", "is_checked", "position"])
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).update_checklist_item(
                checklist_item_id, **kwargs
            )
        )

    @server.tool()
    def delete_checklist_item(
        checklist_item_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> None:
        """Delete a checklist item."""
        get_client(api_key=api_key, ctx=ctx).delete_checklist_item(checklist_item_id)
        return None

    @server.tool()
    def list_webhooks(
        workspace_id: Optional[str] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """List webhooks in workspace or globally."""
        return _serialize(get_client(api_key=api_key, ctx=ctx).list_webhooks())

    @server.tool()
    def create_webhook(
        workspace_id: str,
        model_type: str,
        model_id: str,
        callback_url: str,
        event: Optional[List[str]] = None,
        description: Optional[str] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Create a webhook."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).create_webhook(
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
        webhook_id: str,
        updates: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Update webhook fields: active, events, description, callback_url."""
        kwargs = _present_update_kwargs(
            updates, ["active", "events", "description", "callback_url"]
        )
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).update_webhook(webhook_id, **kwargs)
        )

    @server.tool()
    def delete_webhook(
        webhook_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> None:
        """Delete a webhook."""
        get_client(api_key=api_key, ctx=ctx).delete_webhook(webhook_id)
        return None

    @server.tool()
    def list_webhook_deliveries(
        webhook_id: str,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """List webhook delivery attempts."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).list_webhook_deliveries(
                webhook_id, limit=limit, cursor=cursor
            )
        )

    @server.tool()
    def redeliver_webhook_event(
        webhook_id: str,
        delivery_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> None:
        """Redeliver a webhook event delivery."""
        get_client(api_key=api_key, ctx=ctx).redeliver_webhook_event(
            webhook_id, delivery_id
        )
        return None

    @server.tool()
    def list_github_installations(
        workspace_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """List GitHub installations in a workspace."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).list_github_installations(
                workspace_id
            )
        )

    @server.tool()
    def list_github_repositories(
        workspace_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """List GitHub repositories in a workspace."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).list_github_repositories(workspace_id)
        )

    @server.tool()
    def list_github_board_repositories(
        workspace_id: str,
        board_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """List GitHub repositories connected to a board."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).list_github_board_repositories(
                workspace_id, board_id
            )
        )

    @server.tool()
    def replace_github_board_repositories(
        workspace_id: str,
        board_id: str,
        repositories: List[Dict[str, int]],
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Replace GitHub repositories connected to a board."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).replace_github_board_repositories(
                workspace_id, board_id, repositories
            )
        )

    @server.tool()
    def start_github_connect(
        workspace_id: str,
        replace: Optional[bool] = None,
        board_id: Optional[str] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Start GitHub App installation flow."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).start_github_connect(
                workspace_id, replace=replace, board_id=board_id
            )
        )

    @server.tool()
    def delete_github_installation(
        workspace_id: str,
        installation_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> None:
        """Delete a GitHub installation from a workspace."""
        get_client(api_key=api_key, ctx=ctx).delete_github_installation(
            workspace_id, installation_id
        )
        return None

    @server.tool()
    def search_github_objects(
        ticket_id: str,
        q: Optional[str] = None,
        type: Optional[str] = None,
        page: Optional[int] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Search GitHub objects for a ticket."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).search_github_objects(
                ticket_id, q=q, type=type, page=page
            )
        )

    @server.tool()
    def create_github_link(
        ticket_id: str,
        installation_id: int,
        github_repo_id: int,
        kind: str,
        number: Optional[int] = None,
        branch_name: Optional[str] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Link a GitHub object to a ticket."""
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).create_github_link(
                ticket_id,
                installation_id,
                github_repo_id,
                kind,
                number=number,
                branch_name=branch_name,
            )
        )

    @server.tool()
    def delete_github_link(
        ticket_id: str,
        link_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> None:
        """Unlink a GitHub object from a ticket."""
        get_client(api_key=api_key, ctx=ctx).delete_github_link(ticket_id, link_id)
        return None

    @server.tool()
    def create_attachment(
        ticket_id: str,
        filename: str,
        file_content_base64: str,
        content_type: Optional[str] = None,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        """Upload an attachment to a ticket (requires Base64 encoded file content)."""
        file_content = base64.b64decode(file_content_base64)
        return _serialize(
            get_client(api_key=api_key, ctx=ctx).create_attachment(
                ticket_id, filename, file_content, content_type
            )
        )

    @server.tool()
    def download_attachment(
        attachment_id: str,
        api_key: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> str:
        """Download attachment content as a Base64 encoded string."""
        content = get_client(api_key=api_key, ctx=ctx).download_attachment(
            attachment_id
        )
        return base64.b64encode(content).decode("utf-8")

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Mello MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport protocol (stdio, sse, streamable-http)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "0.0.0.0"),
        help="Host to bind for HTTP/SSE (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "8000")),
        help="Port to bind for HTTP/SSE (default: 8000)",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("MCP_LOG_LEVEL", "info"),
        help="Log level (default: info)",
    )
    args, _ = parser.parse_known_args()

    server = create_mcp_server()

    if args.transport == "sse":
        import uvicorn
        import anyio

        starlette_app = server.sse_app()
        starlette_app.add_middleware(MelloSseAuthMiddleware)
        config = uvicorn.Config(
            starlette_app,
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower(),
        )
        uvicorn_server = uvicorn.Server(config)
        anyio.run(uvicorn_server.serve)
    elif args.transport == "streamable-http":
        server.settings.host = args.host
        server.settings.port = args.port
        server.run(transport="streamable-http")
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
