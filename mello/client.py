from datetime import datetime, timezone
import hashlib
import hmac
from typing import Any, Dict, List, Optional, Union
import requests

from mello.exceptions import raise_for_status
from mello.models import (
    User,
    Workspace,
    WorkspaceMember,
    Board,
    Column,
    Ticket,
    TicketDetail,
    Comment,
    HistoryEntry,
    SearchResult,
    MoveTicketResult,
    Checklist,
    ChecklistItem,
    Attachment,
    Webhook,
    Delivery,
    GithubInstallation,
    GithubRepository,
    GithubSearchObjectResult,
    GithubLink,
    Label,
    parse_datetime,
)


def verify_webhook_signature(
    payload: Union[str, bytes],
    signature_header: str,
    timestamp_header: str,
    secret: str,
    tolerance_seconds: Optional[int] = 300,
) -> bool:
    """
    Verify the HMAC-SHA256 signature of a Mello webhook delivery.

    Args:
        payload: The raw request body as bytes or str.
        signature_header: Value of the X-Mello-Signature header (format 'sha256=<hex>').
        timestamp_header: Value of the X-Mello-Timestamp header (RFC3339 timestamp).
        secret: The webhook signing secret.
        tolerance_seconds: Maximum allowed age of timestamp in seconds for replay protection.
                           Pass None to disable timestamp check. Default is 300 (5 minutes).

    Returns:
        bool: True if signature and timestamp are valid, False otherwise.
    """
    if not signature_header or not timestamp_header or not secret:
        return False

    if not signature_header.startswith("sha256="):
        return False

    expected_sig_hex = signature_header.removeprefix("sha256=")

    if tolerance_seconds is not None:
        ts = parse_datetime(timestamp_header)
        if ts is None:
            return False
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if abs((now - ts).total_seconds()) > tolerance_seconds:
            return False

    raw_body = payload if isinstance(payload, bytes) else payload.encode("utf-8")
    signed_data = f"{timestamp_header}.".encode("utf-8") + raw_body

    mac = hmac.new(secret.encode("utf-8"), signed_data, hashlib.sha256)
    computed_hex = mac.hexdigest()

    return hmac.compare_digest(computed_hex, expected_sig_hex)


class UnsetType:
    def __repr__(self) -> str:
        return "UNSET"


UNSET: Any = UnsetType()


class MelloClient:
    """
    Client for interacting with the Mello Public REST API.
    """

    def __init__(
        self,
        token: str,
        base_url: str = "https://mello.mezon.vn/api/v1",
        timeout: float = 30.0,
    ):
        """
        Initialize the Mello API client.

        Args:
            token: Personal API bearer token.
            base_url: Base URL of the Mello API.
            timeout: Default timeout for requests in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        use_v1: bool = True,
        stream: bool = False,
    ) -> Any:
        base = self.base_url
        if not use_v1 and base.endswith("/v1"):
            base = base[:-3]
        url = f"{base}{path}"

        headers = {}
        if files:
            headers = {"Content-Type": None}

        response = self.session.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            files=files,
            headers=headers if files else None,
            timeout=self.timeout,
            stream=stream,
        )

        if stream:
            if response.status_code >= 400:
                try:
                    response_json = response.json() if response.text else None
                except ValueError:
                    response_json = None
                raise_for_status(response.status_code, response_json)
            return response.content

        try:
            response_json = response.json() if response.text else None
        except ValueError:
            response_json = None

        raise_for_status(response.status_code, response_json)

        if response.status_code == 204:
            return None

        return response_json

    def _format_datetime(self, val: Optional[datetime]) -> Optional[str]:
        if val is None:
            return None
        return val.isoformat()

    # --- Me Tag ---

    def get_current_user(self) -> User:
        """
        Get the API token owner.

        Returns:
            User: The authenticated user profile.
        """
        data = self._request("GET", "/me")
        return User.from_dict(data)

    # --- Workspaces Tag ---

    def list_workspaces(self) -> List[Workspace]:
        """
        List token-accessible workspaces.

        Returns:
            List[Workspace]: List of accessible workspaces.
        """
        data = self._request("GET", "/workspaces")
        return [Workspace.from_dict(w) for w in (data or [])]

    def list_workspace_members(self, workspace_id: str) -> List[WorkspaceMember]:
        """
        List workspace members.

        Args:
            workspace_id: The ID of the workspace.

        Returns:
            List[WorkspaceMember]: Members of the workspace.
        """
        data = self._request("GET", f"/workspaces/{workspace_id}/members")
        return [WorkspaceMember.from_dict(m) for m in (data or [])]

    # --- Boards Tag ---

    def list_workspace_boards(self, workspace_id: str) -> List[Board]:
        """
        List boards in a workspace.

        Args:
            workspace_id: The ID of the workspace.

        Returns:
            List[Board]: Boards in the workspace.
        """
        data = self._request("GET", f"/workspaces/{workspace_id}/boards")
        return [Board.from_dict(b) for b in (data or [])]

    def create_board(
        self, workspace_id: str, name: str, code: Optional[str] = None
    ) -> Board:
        """
        Create a board.

        Args:
            workspace_id: The ID of the workspace.
            name: The board name.
            code: Optional board code. Generated from name when omitted.

        Returns:
            Board: The created board.
        """
        payload: Dict[str, Any] = {"name": name}
        if code is not None:
            payload["code"] = code

        data = self._request(
            "POST", f"/workspaces/{workspace_id}/boards", json_data=payload
        )
        return Board.from_dict(data)

    def get_board(self, board_id: str) -> Board:
        """
        Get a board with columns and tickets.

        Args:
            board_id: The ID of the board.

        Returns:
            Board: The board details.
        """
        data = self._request("GET", f"/boards/{board_id}")
        return Board.from_dict(data)

    def update_board(
        self,
        board_id: str,
        name: Union[str, UnsetType] = UNSET,
        background_color: Union[Optional[str], UnsetType] = UNSET,
        cover_image_url: Union[Optional[str], UnsetType] = UNSET,
    ) -> Board:
        """
        Update board metadata.

        Args:
            board_id: The ID of the board.
            name: Optional board name update.
            background_color: Optional background color update.
            cover_image_url: Optional cover image URL update.

        Returns:
            Board: The updated board.
        """
        payload: Dict[str, Any] = {}
        if not isinstance(name, UnsetType):
            payload["name"] = name
        if not isinstance(background_color, UnsetType):
            payload["background_color"] = background_color
        if not isinstance(cover_image_url, UnsetType):
            payload["cover_image_url"] = cover_image_url

        data = self._request("PATCH", f"/boards/{board_id}", json_data=payload)
        return Board.from_dict(data)

    def delete_board(self, board_id: str) -> None:
        """
        Delete a board.

        Args:
            board_id: The ID of the board.
        """
        self._request("DELETE", f"/boards/{board_id}")

    # --- Columns Tag ---

    def list_columns(self, board_id: str) -> List[Column]:
        """
        List board columns.

        Args:
            board_id: The ID of the board.

        Returns:
            List[Column]: List of columns.
        """
        data = self._request("GET", f"/boards/{board_id}/columns")
        return [Column.from_dict(c) for c in (data or [])]

    def create_column(
        self, board_id: str, name: str, position: Optional[int] = None
    ) -> Column:
        """
        Create a column.

        Args:
            board_id: The ID of the board.
            name: Name of the column.
            position: Optional position of the column.

        Returns:
            Column: The created column.
        """
        payload: Dict[str, Any] = {"name": name}
        if position is not None:
            payload["position"] = position

        data = self._request("POST", f"/boards/{board_id}/columns", json_data=payload)
        return Column.from_dict(data)

    def reorder_columns(self, board_id: str, column_ids: List[str]) -> None:
        """
        Reorder board columns.

        Args:
            board_id: The ID of the board.
            column_ids: Ordered list of column UUID strings.
        """
        payload = {"column_ids": column_ids}
        self._request("PATCH", f"/boards/{board_id}/columns/reorder", json_data=payload)

    def update_column(
        self,
        column_id: str,
        name: Union[str, UnsetType] = UNSET,
        position: Union[int, UnsetType] = UNSET,
        color: Union[Optional[str], UnsetType] = UNSET,
    ) -> Column:
        """
        Update a column.

        Args:
            column_id: The ID of the column.
            name: Optional new column name.
            position: Optional new position.
            color: Optional column color hex value or string.

        Returns:
            Column: The updated column.
        """
        payload: Dict[str, Any] = {}
        if not isinstance(name, UnsetType):
            payload["name"] = name
        if not isinstance(position, UnsetType):
            payload["position"] = position
        if not isinstance(color, UnsetType):
            payload["color"] = color

        data = self._request("PATCH", f"/columns/{column_id}", json_data=payload)
        return Column.from_dict(data)

    # --- Labels Tag ---

    def list_labels(self, board_id: str) -> List[Label]:
        """
        List labels on a board.

        Args:
            board_id: The ID of the board.

        Returns:
            List[Label]: List of labels.
        """
        data = self._request("GET", f"/boards/{board_id}/labels")
        return [Label.from_dict(lbl) for lbl in (data or [])]

    def create_label(
        self, board_id: str, name: str, color: Optional[str] = None
    ) -> Label:
        """
        Create a label on a board.

        Args:
            board_id: The ID of the board.
            name: Name of the label.
            color: Optional label color hex value (#rrggbb).

        Returns:
            Label: The created label.
        """
        payload: Dict[str, Any] = {"name": name}
        if color is not None:
            payload["color"] = color

        data = self._request("POST", f"/boards/{board_id}/labels", json_data=payload)
        return Label.from_dict(data)

    def update_label(
        self,
        label_id: str,
        name: Union[str, UnsetType] = UNSET,
        color: Union[str, UnsetType] = UNSET,
    ) -> Label:
        """
        Update a label.

        Args:
            label_id: The ID of the label.
            name: Optional new label name.
            color: Optional new label color hex value (#rrggbb).

        Returns:
            Label: The updated label.
        """
        payload: Dict[str, Any] = {}
        if not isinstance(name, UnsetType):
            payload["name"] = name
        if not isinstance(color, UnsetType):
            payload["color"] = color

        data = self._request("PATCH", f"/labels/{label_id}", json_data=payload)
        return Label.from_dict(data)

    def delete_label(self, label_id: str) -> None:
        """
        Delete a label.

        Args:
            label_id: The ID of the label.
        """
        self._request("DELETE", f"/labels/{label_id}")

    # --- Tickets Tag ---

    def list_board_tickets(self, board_id: str) -> List[Ticket]:
        """
        List tickets on a board.

        Args:
            board_id: The ID of the board.

        Returns:
            List[Ticket]: Tickets in the board.
        """
        data = self._request("GET", f"/boards/{board_id}/tickets")
        return [Ticket.from_dict(t) for t in (data or [])]

    def create_ticket(
        self,
        column_id: str,
        title: str,
        description: Optional[str] = None,
        position: Optional[int] = None,
        description_markdown: Optional[str] = None,
        description_html: Optional[str] = None,
    ) -> Ticket:
        """
        Create a ticket in a column.

        Args:
            column_id: The ID of the column.
            title: Title of the ticket.
            description: Optional plain text ticket description.
            position: Optional ticket position.
            description_markdown: Optional markdown description (rendered server-side).
            description_html: Optional HTML description.

        Returns:
            Ticket: The created ticket.
        """
        payload: Dict[str, Any] = {"title": title}
        if description is not None:
            payload["description"] = description
        if position is not None:
            payload["position"] = position
        if description_markdown is not None:
            payload["description_markdown"] = description_markdown
        if description_html is not None:
            payload["description_html"] = description_html

        data = self._request("POST", f"/columns/{column_id}/tickets", json_data=payload)
        return Ticket.from_dict(data)

    def get_ticket(self, ticket_id: str) -> TicketDetail:
        """
        Get a ticket.

        Args:
            ticket_id: The ID of the ticket.

        Returns:
            TicketDetail: Detailed ticket information.
        """
        data = self._request("GET", f"/tickets/{ticket_id}")
        return TicketDetail.from_dict(data)

    def update_ticket(
        self,
        ticket_id: str,
        title: Union[str, UnsetType] = UNSET,
        description: Union[str, UnsetType] = UNSET,
        description_html: Union[str, UnsetType] = UNSET,
        description_markdown: Union[Optional[str], UnsetType] = UNSET,
        pic_user_id: Union[Optional[str], UnsetType] = UNSET,
        supervisor_id: Union[Optional[str], UnsetType] = UNSET,
        start_date: Union[Optional[datetime], UnsetType] = UNSET,
        end_date: Union[Optional[datetime], UnsetType] = UNSET,
    ) -> Ticket:
        """
        Update a ticket.

        Args:
            ticket_id: The ID of the ticket.
            title: Optional updated title.
            description: Optional updated description text.
            description_html: Optional updated HTML description.
            description_markdown: Optional updated markdown description.
            pic_user_id: Optional user UUID string to set as PIC, or None.
            supervisor_id: Optional user UUID string to set as supervisor, or None.
            start_date: Optional start date datetime.
            end_date: Optional end date datetime.

        Returns:
            Ticket: The updated ticket.
        """
        payload: Dict[str, Any] = {}
        if not isinstance(title, UnsetType):
            payload["title"] = title
        if not isinstance(description, UnsetType):
            payload["description"] = description
        if not isinstance(description_html, UnsetType):
            payload["description_html"] = description_html
        if not isinstance(description_markdown, UnsetType):
            payload["description_markdown"] = description_markdown
        if not isinstance(pic_user_id, UnsetType):
            payload["pic_user_id"] = pic_user_id
        if not isinstance(supervisor_id, UnsetType):
            payload["supervisor_id"] = supervisor_id
        if not isinstance(start_date, UnsetType):
            payload["start_date"] = self._format_datetime(start_date)
        if not isinstance(end_date, UnsetType):
            payload["end_date"] = self._format_datetime(end_date)

        data = self._request("PATCH", f"/tickets/{ticket_id}", json_data=payload)
        return Ticket.from_dict(data)

    def move_ticket(
        self,
        ticket_id: str,
        column_id: str,
        position: Optional[int] = None,
    ) -> MoveTicketResult:
        """
        Move a ticket atomically to another column.

        Args:
            ticket_id: The ID of the ticket.
            column_id: Target column ID.
            position: Unused (retained for backward compatibility).

        Returns:
            MoveTicketResult: Result of the ticket movement.
        """
        payload = {"column_id": column_id}
        data = self._request("PATCH", f"/tickets/{ticket_id}/move", json_data=payload)
        return MoveTicketResult.from_dict(data)

    def delete_ticket(self, ticket_id: str) -> None:
        """
        Delete a ticket.

        Args:
            ticket_id: The ID of the ticket.
        """
        self._request("DELETE", f"/tickets/{ticket_id}")

    def attach_label_to_ticket(self, ticket_id: str, label_id: str) -> None:
        """
        Attach a label to a ticket.

        Args:
            ticket_id: The ID of the ticket.
            label_id: The ID of the label.
        """
        self._request("POST", f"/tickets/{ticket_id}/labels/{label_id}")

    def detach_label_from_ticket(self, ticket_id: str, label_id: str) -> None:
        """
        Detach a label from a ticket.

        Args:
            ticket_id: The ID of the ticket.
            label_id: The ID of the label.
        """
        self._request("DELETE", f"/tickets/{ticket_id}/labels/{label_id}")

    # --- Comments Tag ---

    def list_comments(self, ticket_id: str) -> List[Comment]:
        """
        List ticket comments.

        Args:
            ticket_id: The ID of the ticket.

        Returns:
            List[Comment]: List of ticket comments.
        """
        data = self._request("GET", f"/tickets/{ticket_id}/comments")
        return [Comment.from_dict(c) for c in (data or [])]

    def create_comment(
        self,
        ticket_id: str,
        body: str,
        body_html: Optional[str] = None,
        body_markdown: Optional[str] = None,
    ) -> Comment:
        """
        Add a ticket comment.

        Args:
            ticket_id: The ID of the ticket.
            body: The comment text.
            body_html: Optional HTML version of comment.
            body_markdown: Optional markdown version of comment (rendered server-side).

        Returns:
            Comment: The created comment.
        """
        payload: Dict[str, Any] = {"body": body}
        if body_html is not None:
            payload["body_html"] = body_html
        if body_markdown is not None:
            payload["body_markdown"] = body_markdown

        data = self._request(
            "POST", f"/tickets/{ticket_id}/comments", json_data=payload
        )
        return Comment.from_dict(data)

    # --- History Tag ---

    def list_history(self, ticket_id: str) -> List[HistoryEntry]:
        """
        List ticket history.

        Args:
            ticket_id: The ID of the ticket.

        Returns:
            List[HistoryEntry]: The history list of the ticket.
        """
        data = self._request("GET", f"/tickets/{ticket_id}/history")
        return [HistoryEntry.from_dict(h) for h in (data or [])]

    # --- Search Tag ---

    def search_tickets(self, workspace_id: str, q: str) -> List[SearchResult]:
        """
        Search tickets in a workspace.

        Args:
            workspace_id: The ID of the workspace.
            q: Search query string.

        Returns:
            List[SearchResult]: Search results list.
        """
        params = {
            "workspace_id": workspace_id,
            "q": q,
        }
        data = self._request("GET", "/search", params=params)
        return [SearchResult.from_dict(s) for s in (data or [])]

    # --- Checklists Tag ---

    def create_checklist(
        self, ticket_id: str, title: str, position: Optional[int] = None
    ) -> Checklist:
        """
        Create a checklist for a ticket.
        """
        payload: Dict[str, Any] = {"title": title}
        if position is not None:
            payload["position"] = position
        data = self._request(
            "POST", f"/tickets/{ticket_id}/checklists", json_data=payload
        )
        return Checklist.from_dict(data)

    def update_checklist(
        self,
        checklist_id: str,
        title: Union[str, UnsetType] = UNSET,
        position: Union[int, UnsetType] = UNSET,
    ) -> Checklist:
        """
        Update a checklist.
        """
        payload: Dict[str, Any] = {}
        if not isinstance(title, UnsetType):
            payload["title"] = title
        if not isinstance(position, UnsetType):
            payload["position"] = position

        data = self._request("PATCH", f"/checklists/{checklist_id}", json_data=payload)
        return Checklist.from_dict(data)

    def delete_checklist(self, checklist_id: str) -> None:
        """
        Delete a checklist and its items.
        """
        self._request("DELETE", f"/checklists/{checklist_id}")

    def create_checklist_item(
        self, checklist_id: str, title: str, position: Optional[int] = None
    ) -> ChecklistItem:
        """
        Create an item inside a checklist.
        """
        payload: Dict[str, Any] = {"title": title}
        if position is not None:
            payload["position"] = position
        data = self._request(
            "POST", f"/checklists/{checklist_id}/items", json_data=payload
        )
        return ChecklistItem.from_dict(data)

    def update_checklist_item(
        self,
        checklist_item_id: str,
        title: Union[str, UnsetType] = UNSET,
        is_checked: Union[bool, UnsetType] = UNSET,
        position: Union[int, UnsetType] = UNSET,
    ) -> ChecklistItem:
        """
        Update a checklist item's properties (title, is_checked, position).
        """
        payload: Dict[str, Any] = {}
        if not isinstance(title, UnsetType):
            payload["title"] = title
        if not isinstance(is_checked, UnsetType):
            payload["is_checked"] = is_checked
        if not isinstance(position, UnsetType):
            payload["position"] = position

        data = self._request(
            "PATCH", f"/checklist-items/{checklist_item_id}", json_data=payload
        )
        return ChecklistItem.from_dict(data)

    def delete_checklist_item(self, checklist_item_id: str) -> None:
        """
        Delete a checklist item.
        """
        self._request("DELETE", f"/checklist-items/{checklist_item_id}")

    # --- Webhooks Tag ---

    def list_webhooks(self) -> List[Webhook]:
        """
        List webhooks.
        """
        data = self._request("GET", "/webhooks")
        return [Webhook.from_dict(w) for w in (data or [])]

    def create_webhook(
        self,
        workspace_id: str,
        model_type: str,
        model_id: str,
        callback_url: str,
        event: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> Webhook:
        """
        Create a webhook.
        """
        payload: Dict[str, Any] = {
            "workspace_id": workspace_id,
            "model_type": model_type,
            "model_id": model_id,
            "callback_url": callback_url,
        }
        if event is not None:
            payload["event"] = event
        if description is not None:
            payload["description"] = description

        data = self._request("POST", "/webhooks", json_data=payload)
        return Webhook.from_dict(data)

    def update_webhook(
        self,
        webhook_id: str,
        active: Union[bool, UnsetType] = UNSET,
        events: Union[List[str], UnsetType] = UNSET,
        description: Union[Optional[str], UnsetType] = UNSET,
        callback_url: Union[str, UnsetType] = UNSET,
    ) -> Webhook:
        """
        Update a webhook.
        """
        payload: Dict[str, Any] = {}
        if not isinstance(active, UnsetType):
            payload["active"] = active
        if not isinstance(events, UnsetType):
            payload["events"] = events
        if not isinstance(description, UnsetType):
            payload["description"] = description
        if not isinstance(callback_url, UnsetType):
            payload["callback_url"] = callback_url

        data = self._request("PATCH", f"/webhooks/{webhook_id}", json_data=payload)
        return Webhook.from_dict(data)

    def delete_webhook(self, webhook_id: str) -> None:
        """
        Delete a webhook.
        """
        self._request("DELETE", f"/webhooks/{webhook_id}")

    def list_webhook_deliveries(self, webhook_id: str) -> List[Delivery]:
        """
        List webhook deliveries.
        """
        data = self._request("GET", f"/webhooks/{webhook_id}/deliveries")
        return [Delivery.from_dict(d) for d in (data or [])]

    def redeliver_webhook_event(self, webhook_id: str, delivery_id: str) -> None:
        """
        Redeliver a webhook event delivery.
        """
        self._request(
            "POST", f"/webhooks/{webhook_id}/deliveries/{delivery_id}/redeliver"
        )

    # --- GitHub Tag ---

    def list_github_installations(self, workspace_id: str) -> List[GithubInstallation]:
        """
        List GitHub installations in a workspace.
        """
        data = self._request("GET", f"/workspaces/{workspace_id}/github/installations")
        return [GithubInstallation.from_dict(gi) for gi in (data or [])]

    def list_github_repositories(self, workspace_id: str) -> List[GithubRepository]:
        """
        List GitHub repositories in a workspace.
        """
        data = self._request("GET", f"/workspaces/{workspace_id}/github/repositories")
        return [GithubRepository.from_dict(gr) for gr in (data or [])]

    def list_github_board_repositories(
        self, workspace_id: str, board_id: str
    ) -> List[GithubRepository]:
        """
        List GitHub repositories connected to a board.
        """
        data = self._request(
            "GET", f"/workspaces/{workspace_id}/boards/{board_id}/github/repositories"
        )
        return [GithubRepository.from_dict(gr) for gr in (data or [])]

    def replace_github_board_repositories(
        self, workspace_id: str, board_id: str, repositories: List[Dict[str, int]]
    ) -> List[GithubRepository]:
        """
        Replace GitHub repositories connected to a board.
        """
        payload = {"repositories": repositories}
        data = self._request(
            "PUT",
            f"/workspaces/{workspace_id}/boards/{board_id}/github/repositories",
            json_data=payload,
        )
        return [GithubRepository.from_dict(gr) for gr in (data or [])]

    def start_github_connect(
        self,
        workspace_id: str,
        replace: Optional[bool] = None,
        board_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Start GitHub App installation flow.
        """
        payload: Dict[str, Any] = {}
        if replace is not None:
            payload["replace"] = replace
        if board_id is not None:
            payload["board_id"] = board_id

        data = self._request(
            "POST",
            f"/workspaces/{workspace_id}/github/connect/start",
            json_data=payload if payload else None,
        )
        return data or {}

    def delete_github_installation(
        self, workspace_id: str, installation_id: str
    ) -> None:
        """
        Delete a GitHub installation from a workspace.
        """
        self._request(
            "DELETE",
            f"/workspaces/{workspace_id}/github/installations/{installation_id}",
        )

    def search_github_objects(
        self,
        ticket_id: str,
        q: Optional[str] = None,
        type: Optional[str] = None,
        page: Optional[int] = None,
    ) -> List[GithubSearchObjectResult]:
        """
        Search GitHub objects for a ticket.
        """
        params: Dict[str, Any] = {}
        if q is not None:
            params["q"] = q
        if type is not None:
            params["type"] = type
        if page is not None:
            params["page"] = page

        data = self._request(
            "GET",
            f"/tickets/{ticket_id}/github/search",
            params=params if params else None,
        )
        return [GithubSearchObjectResult.from_dict(res) for res in (data or [])]

    def create_github_link(
        self,
        ticket_id: str,
        installation_id: int,
        github_repo_id: int,
        kind: str,
        number: Optional[int] = None,
        branch_name: Optional[str] = None,
    ) -> GithubLink:
        """
        Link a GitHub object to a ticket.
        """
        payload: Dict[str, Any] = {
            "installation_id": installation_id,
            "github_repo_id": github_repo_id,
            "kind": kind,
        }
        if number is not None:
            payload["number"] = number
        if branch_name is not None:
            payload["branch_name"] = branch_name

        data = self._request(
            "POST", f"/tickets/{ticket_id}/github/links", json_data=payload
        )
        return GithubLink.from_dict(data)

    def delete_github_link(self, ticket_id: str, link_id: str) -> None:
        """
        Unlink a GitHub object from a ticket.
        """
        self._request("DELETE", f"/tickets/{ticket_id}/github/links/{link_id}")

    # --- Attachments Tag ---

    def create_attachment(
        self,
        ticket_id: str,
        filename: str,
        file_content: bytes,
        content_type: Optional[str] = None,
    ) -> Attachment:
        """
        Upload an attachment to a ticket.
        """
        files = {"file": (filename, file_content, content_type)}
        data = self._request("POST", f"/tickets/{ticket_id}/attachments", files=files)
        return Attachment.from_dict(data)

    def download_attachment(self, attachment_id: str) -> bytes:
        """
        Download attachment raw content bytes.
        """
        return self._request(
            "GET", f"/attachments/{attachment_id}/download", stream=True
        )
