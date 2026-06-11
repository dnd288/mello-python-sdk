from datetime import datetime
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
)


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
    ) -> Ticket:
        """
        Create a ticket in a column.

        Args:
            column_id: The ID of the column.
            title: Title of the ticket.
            description: Optional ticket description.
            position: Optional ticket position.

        Returns:
            Ticket: The created ticket.
        """
        payload: Dict[str, Any] = {"title": title}
        if description is not None:
            payload["description"] = description
        if position is not None:
            payload["position"] = position

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
        assignee_id: Union[Optional[str], UnsetType] = UNSET,
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
            assignee_id: Optional user UUID string to assign, or None to unassign
                (or empty string/sentinel depending on backend API).
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
        if not isinstance(assignee_id, UnsetType):
            payload["assignee_id"] = assignee_id
        if not isinstance(start_date, UnsetType):
            payload["start_date"] = self._format_datetime(start_date)
        if not isinstance(end_date, UnsetType):
            payload["end_date"] = self._format_datetime(end_date)

        data = self._request("PATCH", f"/tickets/{ticket_id}", json_data=payload)
        return Ticket.from_dict(data)

    def move_ticket(
        self, ticket_id: str, column_id: str, position: int
    ) -> MoveTicketResult:
        """
        Move a ticket atomically.

        Args:
            ticket_id: The ID of the ticket.
            column_id: Target column ID.
            position: Position in the target column.

        Returns:
            MoveTicketResult: Result of the ticket movement.
        """
        payload = {
            "column_id": column_id,
            "position": position,
        }
        data = self._request("PATCH", f"/tickets/{ticket_id}/move", json_data=payload)
        return MoveTicketResult.from_dict(data)

    def delete_ticket(self, ticket_id: str) -> None:
        """
        Delete a ticket.

        Args:
            ticket_id: The ID of the ticket.
        """
        self._request("DELETE", f"/tickets/{ticket_id}")

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
        self, ticket_id: str, body: str, body_html: Optional[str] = None
    ) -> Comment:
        """
        Add a ticket comment.

        Args:
            ticket_id: The ID of the ticket.
            body: The comment text.
            body_html: Optional HTML version of comment.

        Returns:
            Comment: The created comment.
        """
        payload: Dict[str, Any] = {"body": body}
        if body_html is not None:
            payload["body_html"] = body_html

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

    def create_checklist(self, ticket_id: str, title: str) -> Checklist:
        """
        Create a checklist for a ticket.
        """
        payload = {"title": title}
        data = self._request(
            "POST", f"/tickets/{ticket_id}/checklists", json_data=payload, use_v1=False
        )
        return Checklist.from_dict(data)

    def create_checklist_item(self, checklist_id: str, title: str) -> ChecklistItem:
        """
        Create an item inside a checklist.
        """
        payload = {"title": title}
        data = self._request(
            "POST", f"/checklists/{checklist_id}/items", json_data=payload, use_v1=False
        )
        return ChecklistItem.from_dict(data)

    def update_checklist_item(
        self, checklist_item_id: str, is_checked: bool
    ) -> ChecklistItem:
        """
        Update a checklist item's state (checked/unchecked).
        """
        payload = {"is_checked": is_checked}
        data = self._request(
            "PATCH",
            f"/checklist-items/{checklist_item_id}",
            json_data=payload,
            use_v1=False,
        )
        return ChecklistItem.from_dict(data)

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
        data = self._request(
            "POST", f"/tickets/{ticket_id}/attachments", files=files, use_v1=False
        )
        return Attachment.from_dict(data)

    def download_attachment(self, attachment_id: str) -> bytes:
        """
        Download attachment raw content bytes.
        """
        return self._request(
            "GET", f"/attachments/{attachment_id}/download", use_v1=False, stream=True
        )
