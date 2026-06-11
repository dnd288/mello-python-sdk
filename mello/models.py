from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


def parse_datetime(val: Optional[str]) -> Optional[datetime]:
    """Helper to parse ISO-8601 datetime strings, handles 'Z' suffix for Python versions < 3.11."""
    if not val:
        return None
    if val.endswith("Z"):
        val = val[:-1] + "+00:00"
    try:
        # Some dates might have space instead of T or other variations, fromisoformat handles space/T
        return datetime.fromisoformat(val)
    except ValueError:
        return None


@dataclass
class User:
    id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        return cls(
            id=data.get("id", ""),
            email=data.get("email", ""),
            name=data.get("name", ""),
            avatar_url=data.get("avatar_url"),
            created_at=parse_datetime(data.get("created_at")),
        )


@dataclass
class Workspace:
    id: str
    name: str
    owner_id: str
    role: str
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workspace":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            owner_id=data.get("owner_id", ""),
            role=data.get("role", ""),
            image_url=data.get("image_url"),
            created_at=parse_datetime(data.get("created_at")),
        )


@dataclass
class WorkspaceMember:
    workspace_id: str
    user_id: str
    email: str
    name: str
    role: str
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceMember":
        return cls(
            workspace_id=data.get("workspace_id", ""),
            user_id=data.get("user_id", ""),
            email=data.get("email", ""),
            name=data.get("name", ""),
            role=data.get("role", ""),
            avatar_url=data.get("avatar_url"),
            created_at=parse_datetime(data.get("created_at")),
        )


@dataclass
class Label:
    id: str
    board_id: str
    name: str
    color: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Label":
        return cls(
            id=data.get("id", ""),
            board_id=data.get("board_id", ""),
            name=data.get("name", ""),
            color=data.get("color", ""),
        )


@dataclass
class ChecklistItem:
    id: str
    checklist_id: str
    title: str
    is_checked: bool
    position: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChecklistItem":
        return cls(
            id=data.get("id", ""),
            checklist_id=data.get("checklist_id", ""),
            title=data.get("title", ""),
            is_checked=data.get("is_checked", False),
            position=data.get("position", 0),
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
        )


@dataclass
class Checklist:
    id: str
    ticket_id: str
    title: str
    position: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: List[ChecklistItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checklist":
        items_data = data.get("items") or []
        return cls(
            id=data.get("id", ""),
            ticket_id=data.get("ticket_id", ""),
            title=data.get("title", ""),
            position=data.get("position", 0),
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
            items=[ChecklistItem.from_dict(i) for i in items_data],
        )


@dataclass
class Attachment:
    id: str
    ticket_id: str
    user_id: str
    bucket: str
    object_key: str
    filename: str
    content_type: str
    byte_size: int
    etag: str
    created_at: Optional[datetime] = None
    author: Optional[User] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Attachment":
        author_data = data.get("author")
        return cls(
            id=data.get("id", ""),
            ticket_id=data.get("ticket_id", ""),
            user_id=data.get("user_id", ""),
            bucket=data.get("bucket", ""),
            object_key=data.get("object_key", ""),
            filename=data.get("filename", ""),
            content_type=data.get("content_type", ""),
            byte_size=data.get("byte_size", 0),
            etag=data.get("etag", ""),
            created_at=parse_datetime(data.get("created_at")),
            author=User.from_dict(author_data) if author_data else None,
        )


@dataclass
class TicketMember:
    ticket_id: str
    user_id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TicketMember":
        return cls(
            ticket_id=data.get("ticket_id", ""),
            user_id=data.get("user_id", ""),
            email=data.get("email", ""),
            name=data.get("name", ""),
            avatar_url=data.get("avatar_url"),
            created_at=parse_datetime(data.get("created_at")),
        )


@dataclass
class Ticket:
    id: str
    ticket_number: int
    ticket_code: str
    column_id: str
    title: str
    description: str
    description_html: str
    position: int
    board_code: str = ""
    assignee_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    labels: List[Label] = field(default_factory=list)
    members: List[TicketMember] = field(default_factory=list)
    comment_count: int = 0
    attachment_count: int = 0
    checklist_item_count: int = 0
    checklist_checked_count: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ticket":
        labels_data = data.get("labels") or []
        members_data = data.get("members") or []
        return cls(
            id=data.get("id", ""),
            ticket_number=data.get("ticket_number", 0),
            ticket_code=data.get("ticket_code", ""),
            column_id=data.get("column_id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            description_html=data.get("description_html", ""),
            position=data.get("position", 0),
            board_code=data.get("board_code", ""),
            assignee_id=data.get("assignee_id"),
            start_date=parse_datetime(data.get("start_date")),
            end_date=parse_datetime(data.get("end_date")),
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
            labels=[Label.from_dict(lbl) for lbl in labels_data],
            members=[TicketMember.from_dict(m) for m in members_data],
            comment_count=data.get("comment_count", 0),
            attachment_count=data.get("attachment_count", 0),
            checklist_item_count=data.get("checklist_item_count", 0),
            checklist_checked_count=data.get("checklist_checked_count", 0),
        )


@dataclass
class Column:
    id: str
    board_id: str
    name: str
    position: int
    ticket_count: int = 0
    color: Optional[str] = None
    created_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    tickets: List[Ticket] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Column":
        tickets_data = data.get("tickets") or []
        return cls(
            id=data.get("id", ""),
            board_id=data.get("board_id", ""),
            name=data.get("name", ""),
            position=data.get("position", 0),
            ticket_count=data.get("ticket_count", 0),
            color=data.get("color"),
            created_at=parse_datetime(data.get("created_at")),
            archived_at=parse_datetime(data.get("archived_at")),
            tickets=[Ticket.from_dict(t) for t in tickets_data],
        )


@dataclass
class Board:
    id: str
    workspace_id: str
    code: str
    name: str
    background_color: Optional[str] = None
    cover_image_url: Optional[str] = None
    created_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    columns: List[Column] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Board":
        columns_data = data.get("columns") or []
        return cls(
            id=data.get("id", ""),
            workspace_id=data.get("workspace_id", ""),
            code=data.get("code", ""),
            name=data.get("name", ""),
            background_color=data.get("background_color"),
            cover_image_url=data.get("cover_image_url"),
            created_at=parse_datetime(data.get("created_at")),
            closed_at=parse_datetime(data.get("closed_at")),
            columns=[Column.from_dict(c) for c in columns_data],
        )


@dataclass
class Comment:
    id: str
    ticket_id: str
    user_id: str
    body: str
    body_html: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    author: Optional[User] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Comment":
        author_data = data.get("author")
        return cls(
            id=data.get("id", ""),
            ticket_id=data.get("ticket_id", ""),
            user_id=data.get("user_id", ""),
            body=data.get("body", ""),
            body_html=data.get("body_html", ""),
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
            author=User.from_dict(author_data) if author_data else None,
        )


@dataclass
class HistoryEntry:
    id: str
    ticket_id: str
    workspace_id: str
    action: str
    user_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    author: Optional[User] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryEntry":
        author_data = data.get("author")
        return cls(
            id=data.get("id", ""),
            ticket_id=data.get("ticket_id", ""),
            workspace_id=data.get("workspace_id", ""),
            action=data.get("action", ""),
            user_id=data.get("user_id"),
            payload=data.get("payload") or {},
            created_at=parse_datetime(data.get("created_at")),
            author=User.from_dict(author_data) if author_data else None,
        )


@dataclass
class TicketDetail(Ticket):
    board_id: str = ""
    workspace_id: str = ""
    column_name: str = ""
    comments: List[Comment] = field(default_factory=list)
    activities: List[HistoryEntry] = field(default_factory=list)
    checklists: List[Checklist] = field(default_factory=list)
    attachments: List[Attachment] = field(default_factory=list)
    custom_fields: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TicketDetail":
        # Extract base ticket data
        base_ticket = Ticket.from_dict(data)
        comments_data = data.get("comments") or []
        activities_data = data.get("activities") or []
        checklists_data = data.get("checklists") or []
        attachments_data = data.get("attachments") or []
        custom_fields_data = data.get("custom_fields") or []

        return cls(
            id=base_ticket.id,
            ticket_number=base_ticket.ticket_number,
            ticket_code=base_ticket.ticket_code,
            column_id=base_ticket.column_id,
            title=base_ticket.title,
            description=base_ticket.description,
            description_html=base_ticket.description_html,
            position=base_ticket.position,
            board_code=base_ticket.board_code or data.get("board_code", ""),
            assignee_id=base_ticket.assignee_id,
            start_date=base_ticket.start_date,
            end_date=base_ticket.end_date,
            created_at=base_ticket.created_at,
            updated_at=base_ticket.updated_at,
            labels=base_ticket.labels,
            members=base_ticket.members,
            comment_count=base_ticket.comment_count,
            attachment_count=base_ticket.attachment_count,
            checklist_item_count=base_ticket.checklist_item_count,
            checklist_checked_count=base_ticket.checklist_checked_count,
            board_id=data.get("board_id", ""),
            workspace_id=data.get("workspace_id", ""),
            column_name=data.get("column_name", ""),
            comments=[Comment.from_dict(c) for c in comments_data],
            activities=[HistoryEntry.from_dict(h) for h in activities_data],
            checklists=[Checklist.from_dict(c) for c in checklists_data],
            attachments=[Attachment.from_dict(a) for a in attachments_data],
            custom_fields=custom_fields_data,
        )


@dataclass
class SearchResult:
    id: str
    ticket_number: int
    ticket_code: str
    board_code: str
    column_id: str
    board_id: str
    workspace_id: str
    board_name: str
    column_name: str
    title: str
    description: str
    rank: float
    assignee_id: Optional[str] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResult":
        return cls(
            id=data.get("id", ""),
            ticket_number=data.get("ticket_number", 0),
            ticket_code=data.get("ticket_code", ""),
            board_code=data.get("board_code", ""),
            column_id=data.get("column_id", ""),
            board_id=data.get("board_id", ""),
            workspace_id=data.get("workspace_id", ""),
            board_name=data.get("board_name", ""),
            column_name=data.get("column_name", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            rank=data.get("rank", 0.0),
            assignee_id=data.get("assignee_id"),
            updated_at=parse_datetime(data.get("updated_at")),
        )


@dataclass
class MoveTicketResult:
    ticket: Ticket
    workspace_id: str
    from_column: str
    to_column: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MoveTicketResult":
        return cls(
            ticket=Ticket.from_dict(data.get("ticket") or {}),
            workspace_id=data.get("workspace_id", ""),
            from_column=data.get("from_column", ""),
            to_column=data.get("to_column", ""),
        )
