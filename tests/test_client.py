from datetime import datetime, timezone
from typing import Any, Dict, List
import pytest
import responses

from mello import (
    MelloClient,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    ValidationErrorException,
    RateLimitedException,
    MelloAPIException,
)


@pytest.fixture
def client() -> MelloClient:
    return MelloClient(token="test_token_123")


@responses.activate
def test_get_current_user(client: MelloClient) -> None:
    user_payload = {
        "id": "e3b0c442-98fc-1c14-9afb-f4c8996fb924",
        "email": "user@example.com",
        "name": "Jane Doe",
        "avatar_url": "https://example.com/avatar.png",
        "created_at": "2026-06-08T12:00:00Z",
    }
    responses.add(
        responses.GET,
        "https://mello.mezon.vn/api/v1/me",
        json=user_payload,
        status=200,
    )

    user = client.get_current_user()
    assert user.id == "e3b0c442-98fc-1c14-9afb-f4c8996fb924"
    assert user.email == "user@example.com"
    assert user.name == "Jane Doe"
    assert user.avatar_url == "https://example.com/avatar.png"
    assert user.created_at == datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)


@responses.activate
def test_list_workspaces(client: MelloClient) -> None:
    workspaces_payload = [
        {
            "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
            "name": "Engineering Workspace",
            "owner_id": "e3b0c442-98fc-1c14-9afb-f4c8996fb924",
            "role": "admin",
            "image_url": None,
            "created_at": "2026-06-01T00:00:00Z",
        }
    ]
    responses.add(
        responses.GET,
        "https://mello.mezon.vn/api/v1/workspaces",
        json=workspaces_payload,
        status=200,
    )

    workspaces = client.list_workspaces()
    assert len(workspaces) == 1
    assert workspaces[0].name == "Engineering Workspace"
    assert workspaces[0].image_url is None
    assert workspaces[0].created_at == datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)


@responses.activate
def test_list_workspace_members(client: MelloClient) -> None:
    workspace_id = "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
    members_payload = [
        {
            "workspace_id": workspace_id,
            "user_id": "e3b0c442-98fc-1c14-9afb-f4c8996fb924",
            "email": "user@example.com",
            "name": "Jane Doe",
            "avatar_url": None,
            "role": "admin",
            "created_at": "2026-06-01T00:00:00Z",
        }
    ]
    responses.add(
        responses.GET,
        f"https://mello.mezon.vn/api/v1/workspaces/{workspace_id}/members",
        json=members_payload,
        status=200,
    )

    members = client.list_workspace_members(workspace_id)
    assert len(members) == 1
    assert members[0].name == "Jane Doe"
    assert members[0].role == "admin"


@responses.activate
def test_list_workspace_boards(client: MelloClient) -> None:
    workspace_id = "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
    boards_payload: List[Dict[str, Any]] = [
        {
            "id": "11111111-2222-3333-4444-555555555555",
            "workspace_id": workspace_id,
            "code": "PROJ",
            "name": "Project Board",
            "background_color": "#ffffff",
            "cover_image_url": None,
            "created_at": "2026-06-02T10:00:00Z",
            "closed_at": None,
            "columns": [],
        }
    ]
    responses.add(
        responses.GET,
        f"https://mello.mezon.vn/api/v1/workspaces/{workspace_id}/boards",
        json=boards_payload,
        status=200,
    )

    boards = client.list_workspace_boards(workspace_id)
    assert len(boards) == 1
    assert boards[0].code == "PROJ"
    assert boards[0].name == "Project Board"
    assert boards[0].columns == []


@responses.activate
def test_create_board(client: MelloClient) -> None:
    workspace_id = "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
    board_payload = {
        "id": "11111111-2222-3333-4444-555555555555",
        "workspace_id": workspace_id,
        "code": "NEW",
        "name": "New Board",
        "background_color": None,
        "cover_image_url": None,
        "created_at": "2026-06-08T12:00:00Z",
        "closed_at": None,
    }
    responses.add(
        responses.POST,
        f"https://mello.mezon.vn/api/v1/workspaces/{workspace_id}/boards",
        match=[
            responses.matchers.json_params_matcher({"name": "New Board", "code": "NEW"})
        ],
        json=board_payload,
        status=201,
    )

    board = client.create_board(workspace_id, name="New Board", code="NEW")
    assert board.name == "New Board"
    assert board.code == "NEW"


@responses.activate
def test_get_board(client: MelloClient) -> None:
    board_id = "11111111-2222-3333-4444-555555555555"
    board_payload = {
        "id": board_id,
        "workspace_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
        "code": "PROJ",
        "name": "Project Board",
        "background_color": "#ffffff",
        "cover_image_url": None,
        "created_at": "2026-06-02T10:00:00Z",
        "closed_at": None,
        "columns": [
            {
                "id": "c1c1c1c1-c2c2-c3c3-c4c4-c5c5c5c5c5c5",
                "board_id": board_id,
                "name": "To Do",
                "position": 1,
                "ticket_count": 1,
                "color": "#ff0000",
                "tickets": [
                    {
                        "id": "t1t1t1t1-t2t2-t3t3-t4t4-t5t5t5t5t5t5",
                        "ticket_number": 101,
                        "ticket_code": "PROJ-101",
                        "column_id": "c1c1c1c1-c2c2-c3c3-c4c4-c5c5c5c5c5c5",
                        "title": "Task 1",
                        "description": "Task description",
                        "description_html": "<p>Task description</p>",
                        "position": 1,
                        "assignee_id": None,
                        "created_at": "2026-06-02T11:00:00Z",
                        "updated_at": "2026-06-02T12:00:00Z",
                        "labels": [],
                        "members": [],
                        "comment_count": 0,
                        "attachment_count": 0,
                        "checklist_item_count": 0,
                        "checklist_checked_count": 0,
                    }
                ],
            }
        ],
    }
    responses.add(
        responses.GET,
        f"https://mello.mezon.vn/api/v1/boards/{board_id}",
        json=board_payload,
        status=200,
    )

    board = client.get_board(board_id)
    assert board.name == "Project Board"
    assert len(board.columns) == 1
    assert board.columns[0].name == "To Do"
    assert len(board.columns[0].tickets) == 1
    assert board.columns[0].tickets[0].title == "Task 1"


@responses.activate
def test_update_board(client: MelloClient) -> None:
    board_id = "11111111-2222-3333-4444-555555555555"
    board_payload = {
        "id": board_id,
        "workspace_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
        "code": "PROJ",
        "name": "Updated Board Name",
        "background_color": "#000000",
        "cover_image_url": "https://example.com/cover.png",
        "created_at": "2026-06-02T10:00:00Z",
        "closed_at": None,
    }
    responses.add(
        responses.PATCH,
        f"https://mello.mezon.vn/api/v1/boards/{board_id}",
        match=[
            responses.matchers.json_params_matcher(
                {
                    "name": "Updated Board Name",
                    "background_color": "#000000",
                    "cover_image_url": "https://example.com/cover.png",
                }
            )
        ],
        json=board_payload,
        status=200,
    )

    board = client.update_board(
        board_id,
        name="Updated Board Name",
        background_color="#000000",
        cover_image_url="https://example.com/cover.png",
    )
    assert board.name == "Updated Board Name"
    assert board.background_color == "#000000"
    assert board.cover_image_url == "https://example.com/cover.png"


@responses.activate
def test_delete_board(client: MelloClient) -> None:
    board_id = "11111111-2222-3333-4444-555555555555"
    responses.add(
        responses.DELETE,
        f"https://mello.mezon.vn/api/v1/boards/{board_id}",
        status=204,
    )

    client.delete_board(board_id)


@responses.activate
def test_list_columns(client: MelloClient) -> None:
    board_id = "11111111-2222-3333-4444-555555555555"
    columns_payload = [
        {
            "id": "c1c1c1c1-c2c2-c3c3-c4c4-c5c5c5c5c5c5",
            "board_id": board_id,
            "name": "To Do",
            "position": 1,
            "ticket_count": 0,
            "color": None,
            "tickets": [],
        }
    ]
    responses.add(
        responses.GET,
        f"https://mello.mezon.vn/api/v1/boards/{board_id}/columns",
        json=columns_payload,
        status=200,
    )

    columns = client.list_columns(board_id)
    assert len(columns) == 1
    assert columns[0].name == "To Do"


@responses.activate
def test_list_labels(client: MelloClient) -> None:
    board_id = "11111111-2222-3333-4444-555555555555"
    labels_payload = [
        {
            "id": "1abe11ab-e11b-e11b-e11b-e11be11be11b",
            "board_id": board_id,
            "name": "Auth",
            "color": "#c8f1df",
        }
    ]
    responses.add(
        responses.GET,
        f"https://mello.mezon.vn/api/boards/{board_id}/labels",
        json=labels_payload,
        status=200,
    )

    labels = client.list_labels(board_id)
    assert len(labels) == 1
    assert labels[0].name == "Auth"
    assert labels[0].color == "#c8f1df"
    assert labels[0].board_id == board_id

@responses.activate
def test_create_label(client: MelloClient) -> None:
    board_id = "11111111-2222-3333-4444-555555555555"
    label_payload = {
        "id": "1abe11ab-e11b-e11b-e11b-e11be11be11b",
        "board_id": board_id,
        "name": "Auth",
        "color": "#c8f1df",
    }
    responses.add(
        responses.POST,
        f"https://mello.mezon.vn/api/boards/{board_id}/labels",
        match=[
            responses.matchers.json_params_matcher(
                {"name": "Auth", "color": "#c8f1df"}
            )
        ],
        json=label_payload,
        status=201,
    )

    label = client.create_label(board_id, name="Auth", color="#c8f1df")
    assert label.name == "Auth"
    assert label.color == "#c8f1df"

@responses.activate
def test_update_label(client: MelloClient) -> None:
    label_id = "1abe11ab-e11b-e11b-e11b-e11be11be11b"
    label_payload = {
        "id": label_id,
        "board_id": "11111111-2222-3333-4444-555555555555",
        "name": "Auth 1",
        "color": "#ffa500",
    }
    responses.add(
        responses.PATCH,
        f"https://mello.mezon.vn/api/labels/{label_id}",
        match=[
            responses.matchers.json_params_matcher(
                {"name": "Auth 1", "color": "#ffa500"}
            )
        ],
        json=label_payload,
        status=200,
    )

    label = client.update_label(label_id, name="Auth 1", color="#ffa500")
    assert label.name == "Auth 1"
    assert label.color == "#ffa500"

@responses.activate
def test_create_column(client: MelloClient) -> None:
    board_id = "11111111-2222-3333-4444-555555555555"
    column_payload = {
        "id": "c1c1c1c1-c2c2-c3c3-c4c4-c5c5c5c5c5c5",
        "board_id": board_id,
        "name": "In Progress",
        "position": 2,
        "ticket_count": 0,
    }
    responses.add(
        responses.POST,
        f"https://mello.mezon.vn/api/v1/boards/{board_id}/columns",
        match=[
            responses.matchers.json_params_matcher(
                {"name": "In Progress", "position": 2}
            )
        ],
        json=column_payload,
        status=201,
    )

    column = client.create_column(board_id, name="In Progress", position=2)
    assert column.name == "In Progress"
    assert column.position == 2


@responses.activate
def test_reorder_columns(client: MelloClient) -> None:
    board_id = "11111111-2222-3333-4444-555555555555"
    column_ids = [
        "c2c2c2c2-c2c2-c2c2-c2c2-c2c2c2c2c2c2",
        "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1",
    ]
    responses.add(
        responses.PATCH,
        f"https://mello.mezon.vn/api/v1/boards/{board_id}/columns/reorder",
        match=[responses.matchers.json_params_matcher({"column_ids": column_ids})],
        status=204,
    )

    client.reorder_columns(board_id, column_ids)


@responses.activate
def test_update_column(client: MelloClient) -> None:
    column_id = "c1c1c1c1-c2c2-c3c3-c4c4-c5c5c5c5c5c5"
    column_payload = {
        "id": column_id,
        "board_id": "11111111-2222-3333-4444-555555555555",
        "name": "Done",
        "position": 3,
        "color": "#00ff00",
    }
    responses.add(
        responses.PATCH,
        f"https://mello.mezon.vn/api/v1/columns/{column_id}",
        match=[
            responses.matchers.json_params_matcher(
                {"name": "Done", "position": 3, "color": "#00ff00"}
            )
        ],
        json=column_payload,
        status=200,
    )

    column = client.update_column(column_id, name="Done", position=3, color="#00ff00")
    assert column.name == "Done"
    assert column.color == "#00ff00"


@responses.activate
def test_create_ticket(client: MelloClient) -> None:
    column_id = "c1c1c1c1-c2c2-c3c3-c4c4-c5c5c5c5c5c5"
    ticket_payload = {
        "id": "t1t1t1t1-t2t2-t3t3-t4t4-t5t5t5t5t5t5",
        "ticket_number": 102,
        "ticket_code": "PROJ-102",
        "column_id": column_id,
        "title": "New Bug",
        "description": "Bug description",
        "position": 1,
    }
    responses.add(
        responses.POST,
        f"https://mello.mezon.vn/api/v1/columns/{column_id}/tickets",
        match=[
            responses.matchers.json_params_matcher(
                {
                    "title": "New Bug",
                    "description": "Bug description",
                    "position": 1,
                }
            )
        ],
        json=ticket_payload,
        status=201,
    )

    ticket = client.create_ticket(
        column_id, title="New Bug", description="Bug description", position=1
    )
    assert ticket.title == "New Bug"
    assert ticket.ticket_code == "PROJ-102"


@responses.activate
def test_get_ticket(client: MelloClient) -> None:
    ticket_id = "t1t1t1t1-t2t2-t3t3-t4t4-t5t5t5t5t5t5"
    ticket_payload = {
        "id": ticket_id,
        "ticket_number": 101,
        "ticket_code": "PROJ-101",
        "board_code": "PROJ",
        "column_id": "c1c1c1c1-c2c2-c3c3-c4c4-c5c5c5c5c5c5",
        "title": "Task 1",
        "description": "Task description",
        "description_html": "<p>Task description</p>",
        "position": 1,
        "assignee_id": None,
        "created_at": "2026-06-02T11:00:00Z",
        "updated_at": "2026-06-02T12:00:00Z",
        "labels": [{"id": "l1", "board_id": "b1", "name": "bug", "color": "red"}],
        "members": [],
        "comment_count": 1,
        "attachment_count": 0,
        "checklist_item_count": 0,
        "checklist_checked_count": 0,
        "board_id": "11111111-2222-3333-4444-555555555555",
        "workspace_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
        "column_name": "To Do",
        "comments": [
            {
                "id": "comm1",
                "ticket_id": ticket_id,
                "user_id": "u1",
                "body": "A comment",
                "body_html": "<p>A comment</p>",
                "created_at": "2026-06-02T11:30:00Z",
            }
        ],
        "activities": [],
        "checklists": [
            {
                "id": "chk1",
                "ticket_id": ticket_id,
                "title": "Setup",
                "position": 0,
                "created_at": "2026-06-02T11:15:00Z",
                "updated_at": "2026-06-02T11:20:00Z",
                "items": [
                    {
                        "id": "chki1",
                        "checklist_id": "chk1",
                        "title": "Write tests",
                        "is_checked": True,
                        "position": 0,
                        "created_at": "2026-06-02T11:16:00Z",
                        "updated_at": "2026-06-02T11:18:00Z",
                    }
                ],
            }
        ],
        "attachments": [],
        "custom_fields": [],
    }
    responses.add(
        responses.GET,
        f"https://mello.mezon.vn/api/v1/tickets/{ticket_id}",
        json=ticket_payload,
        status=200,
    )

    ticket = client.get_ticket(ticket_id)
    assert ticket.title == "Task 1"
    assert ticket.column_name == "To Do"
    assert ticket.board_code == "PROJ"
    assert len(ticket.labels) == 1
    assert ticket.labels[0].name == "bug"
    assert len(ticket.comments) == 1
    assert ticket.comments[0].body == "A comment"
    assert len(ticket.checklists) == 1
    assert ticket.checklists[0].title == "Setup"
    assert len(ticket.checklists[0].items) == 1
    assert ticket.checklists[0].items[0].title == "Write tests"
    assert ticket.checklists[0].items[0].is_checked is True
    assert ticket.attachments == []
    assert ticket.custom_fields == []


@responses.activate
def test_update_ticket(client: MelloClient) -> None:
    ticket_id = "t1t1t1t1-t2t2-t3t3-t4t4-t5t5t5t5t5t5"
    ticket_payload = {
        "id": ticket_id,
        "ticket_number": 101,
        "ticket_code": "PROJ-101",
        "column_id": "c1c1c1c1-c2c2-c3c3-c4c4-c5c5c5c5c5c5",
        "title": "Updated Title",
        "description": "Updated Desc",
        "description_html": "<p>Updated Desc</p>",
        "position": 1,
        "pic_user_id": "e3b0c442-98fc-1c14-9afb-f4c8996fb924",
        "supervisor_id": None,
    }
    responses.add(
        responses.PATCH,
        f"https://mello.mezon.vn/api/v1/tickets/{ticket_id}",
        match=[
            responses.matchers.json_params_matcher(
                {
                    "title": "Updated Title",
                    "description": "Updated Desc",
                    "pic_user_id": "e3b0c442-98fc-1c14-9afb-f4c8996fb924",
                    "start_date": "2026-06-08T00:00:00+00:00",
                }
            )
        ],
        json=ticket_payload,
        status=200,
    )

    ticket = client.update_ticket(
        ticket_id,
        title="Updated Title",
        description="Updated Desc",
        pic_user_id="e3b0c442-98fc-1c14-9afb-f4c8996fb924",
        start_date=datetime(2026, 6, 8, 0, 0, 0, tzinfo=timezone.utc),
    )
    assert ticket.title == "Updated Title"
    assert ticket.pic_user_id == "e3b0c442-98fc-1c14-9afb-f4c8996fb924"


@responses.activate
def test_update_ticket_clear_fields(client: MelloClient) -> None:
    ticket_id = "t1t1t1t1-t2t2-t3t3-t4t4-t5t5t5t5t5t5"
    ticket_payload = {
        "id": ticket_id,
        "ticket_number": 101,
        "ticket_code": "PROJ-101",
        "column_id": "c1c1c1c1-c2c2-c3c3-c4c4-c5c5c5c5c5c5",
        "title": "Task 1",
        "description": "Task description",
        "position": 1,
        "pic_user_id": None,
        "supervisor_id": None,
    }
    responses.add(
        responses.PATCH,
        f"https://mello.mezon.vn/api/v1/tickets/{ticket_id}",
        match=[
            responses.matchers.json_params_matcher(
                {
                    "pic_user_id": None,
                    "supervisor_id": None,
                    "start_date": None,
                    "end_date": None,
                }
            )
        ],
        json=ticket_payload,
        status=200,
    )

    ticket = client.update_ticket(
        ticket_id,
        pic_user_id=None,
        supervisor_id=None,
        start_date=None,
        end_date=None,
    )
    assert ticket.pic_user_id is None


@responses.activate
def test_move_ticket(client: MelloClient) -> None:
    ticket_id = "t1t1t1t1-t2t2-t3t3-t4t4-t5t5t5t5t5t5"
    column_id = "c2c2c2c2-c2c2-c2c2-c2c2-c2c2c2c2c2c2"
    move_payload = {
        "ticket": {
            "id": ticket_id,
            "ticket_number": 101,
            "ticket_code": "PROJ-101",
            "column_id": column_id,
            "title": "Task 1",
            "description": "Task description",
            "description_html": "<p>Task description</p>",
            "position": 5,
        },
        "workspace_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
        "from_column": "c1c1c1c1-c2c2-c3c3-c4c4-c5c5c5c5c5c5",
        "to_column": column_id,
    }
    responses.add(
        responses.PATCH,
        f"https://mello.mezon.vn/api/v1/tickets/{ticket_id}/move",
        match=[
            responses.matchers.json_params_matcher(
                {"column_id": column_id, "position": 5}
            )
        ],
        json=move_payload,
        status=200,
    )

    result = client.move_ticket(ticket_id, column_id=column_id, position=5)
    assert result.workspace_id == "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
    assert result.from_column == "c1c1c1c1-c2c2-c3c3-c4c4-c5c5c5c5c5c5"
    assert result.to_column == column_id
    assert result.ticket.column_id == column_id
    assert result.ticket.position == 5


@responses.activate
def test_list_comments(client: MelloClient) -> None:
    ticket_id = "t1t1t1t1-t2t2-t3t3-t4t4-t5t5t5t5t5t5"
    comments_payload = [
        {
            "id": "comm1",
            "ticket_id": ticket_id,
            "user_id": "u1",
            "body": "First comment",
            "body_html": "<p>First comment</p>",
            "created_at": "2026-06-08T12:00:00Z",
            "updated_at": "2026-06-08T12:00:00Z",
            "author": {
                "id": "u1",
                "email": "user1@example.com",
                "name": "User One",
                "avatar_url": None,
                "created_at": "2026-06-01T00:00:00Z",
            },
        }
    ]
    responses.add(
        responses.GET,
        f"https://mello.mezon.vn/api/v1/tickets/{ticket_id}/comments",
        json=comments_payload,
        status=200,
    )

    comments = client.list_comments(ticket_id)
    assert len(comments) == 1
    assert comments[0].body == "First comment"
    assert comments[0].author is not None
    assert comments[0].author.name == "User One"


@responses.activate
def test_create_comment(client: MelloClient) -> None:
    ticket_id = "t1t1t1t1-t2t2-t3t3-t4t4-t5t5t5t5t5t5"
    comment_payload = {
        "id": "comm2",
        "ticket_id": ticket_id,
        "user_id": "u1",
        "body": "New comment",
        "body_html": "<p>New comment</p>",
    }
    responses.add(
        responses.POST,
        f"https://mello.mezon.vn/api/v1/tickets/{ticket_id}/comments",
        match=[
            responses.matchers.json_params_matcher(
                {"body": "New comment", "body_html": "<p>New comment</p>"}
            )
        ],
        json=comment_payload,
        status=201,
    )

    comment = client.create_comment(
        ticket_id, body="New comment", body_html="<p>New comment</p>"
    )
    assert comment.body == "New comment"
    assert comment.body_html == "<p>New comment</p>"


@responses.activate
def test_list_history(client: MelloClient) -> None:
    ticket_id = "t1t1t1t1-t2t2-t3t3-t4t4-t5t5t5t5t5t5"
    history_payload = [
        {
            "id": "h1",
            "ticket_id": ticket_id,
            "workspace_id": "w1",
            "user_id": "u1",
            "action": "ticket_created",
            "payload": {},
            "created_at": "2026-06-08T12:00:00Z",
        }
    ]
    responses.add(
        responses.GET,
        f"https://mello.mezon.vn/api/v1/tickets/{ticket_id}/history",
        json=history_payload,
        status=200,
    )

    history = client.list_history(ticket_id)
    assert len(history) == 1
    assert history[0].action == "ticket_created"


@responses.activate
def test_search_tickets(client: MelloClient) -> None:
    workspace_id = "w1"
    search_payload = [
        {
            "id": "t1",
            "ticket_number": 101,
            "ticket_code": "PROJ-101",
            "board_code": "PROJ",
            "column_id": "c1",
            "board_id": "b1",
            "workspace_id": workspace_id,
            "board_name": "Project Board",
            "column_name": "To Do",
            "title": "Fix bug",
            "description": "Description",
            "rank": 0.95,
            "assignee_id": None,
            "updated_at": "2026-06-08T12:00:00Z",
        }
    ]
    responses.add(
        responses.GET,
        "https://mello.mezon.vn/api/v1/search?workspace_id=w1&q=Fix+bug",
        json=search_payload,
        status=200,
    )

    results = client.search_tickets(workspace_id, q="Fix bug")
    assert len(results) == 1
    assert results[0].title == "Fix bug"
    assert results[0].rank == 0.95


@responses.activate
@pytest.mark.parametrize(
    "status,exception_class",
    [
        (401, UnauthorizedException),
        (403, ForbiddenException),
        (404, NotFoundException),
        (422, ValidationErrorException),
        (429, RateLimitedException),
        (500, MelloAPIException),
    ],
)
def test_error_handling(
    client: MelloClient, status: int, exception_class: type
) -> None:
    responses.add(
        responses.GET,
        "https://mello.mezon.vn/api/v1/me",
        json={"error": "some_error", "message": "error description"},
        status=status,
    )

    with pytest.raises(exception_class) as excinfo:
        client.get_current_user()

    assert isinstance(excinfo.value, MelloAPIException)
    assert excinfo.value.status_code == status
    assert excinfo.value.error_code == "some_error"


@responses.activate
def test_list_board_tickets_null_response(client: MelloClient) -> None:
    board_id = "11111111-2222-3333-4444-555555555555"
    responses.add(
        responses.GET,
        f"https://mello.mezon.vn/api/v1/boards/{board_id}/tickets",
        json=None,
        status=200,
    )

    tickets = client.list_board_tickets(board_id)
    assert tickets == []


@responses.activate
def test_create_checklist(client: MelloClient) -> None:
    ticket_id = "ticket-123"
    responses.add(
        responses.POST,
        f"https://mello.mezon.vn/api/v1/tickets/{ticket_id}/checklists",
        match=[responses.matchers.json_params_matcher({"title": "Setup"})],
        json={
            "id": "chk-1",
            "ticket_id": ticket_id,
            "title": "Setup",
            "position": 0,
        },
        status=201,
    )

    checklist = client.create_checklist(ticket_id, "Setup")
    assert checklist.id == "chk-1"
    assert checklist.title == "Setup"


@responses.activate
def test_create_checklist_item(client: MelloClient) -> None:
    checklist_id = "chk-1"
    responses.add(
        responses.POST,
        f"https://mello.mezon.vn/api/v1/checklists/{checklist_id}/items",
        match=[responses.matchers.json_params_matcher({"title": "Write tests"})],
        json={
            "id": "chki-1",
            "checklist_id": checklist_id,
            "title": "Write tests",
            "is_checked": False,
            "position": 0,
        },
        status=201,
    )

    item = client.create_checklist_item(checklist_id, "Write tests")
    assert item.id == "chki-1"
    assert item.title == "Write tests"
    assert item.is_checked is False


@responses.activate
def test_update_checklist_item(client: MelloClient) -> None:
    item_id = "chki-1"
    responses.add(
        responses.PATCH,
        f"https://mello.mezon.vn/api/v1/checklist-items/{item_id}",
        match=[responses.matchers.json_params_matcher({"is_checked": True})],
        json={
            "id": item_id,
            "checklist_id": "chk-1",
            "title": "Write tests",
            "is_checked": True,
            "position": 0,
        },
        status=200,
    )

    item = client.update_checklist_item(item_id, is_checked=True)
    assert item.is_checked is True


@responses.activate
def test_create_attachment(client: MelloClient) -> None:
    ticket_id = "ticket-123"
    responses.add(
        responses.POST,
        f"https://mello.mezon.vn/api/tickets/{ticket_id}/attachments",
        json={
            "id": "att-1",
            "ticket_id": ticket_id,
            "user_id": "user-1",
            "bucket": "ecosystems",
            "object_key": "some/path/test.png",
            "filename": "test.png",
            "content_type": "image/png",
            "byte_size": 12,
            "etag": "abc",
        },
        status=201,
    )

    att = client.create_attachment(ticket_id, "test.png", b"fakecontent", "image/png")
    assert att.id == "att-1"
    assert att.filename == "test.png"


@responses.activate
def test_download_attachment(client: MelloClient) -> None:
    attachment_id = "att-1"
    responses.add(
        responses.GET,
        f"https://mello.mezon.vn/api/attachments/{attachment_id}/download",
        body=b"filebytesdata",
        status=200,
    )

    content = client.download_attachment(attachment_id)
    assert content == b"filebytesdata"


@responses.activate
def test_webhook_endpoints(client: MelloClient) -> None:
    # list_webhooks
    responses.add(
        responses.GET,
        "https://mello.mezon.vn/api/v1/webhooks",
        json=[
            {
                "id": "wh-1",
                "user_id": "u-1",
                "workspace_id": "ws-1",
                "model_type": "board",
                "model_id": "b-1",
                "callback_url": "https://example.com/hook",
                "events": ["ticket.created"],
                "active": True,
                "consecutive_failures": 0,
            }
        ],
        status=200,
    )
    webhooks = client.list_webhooks()
    assert len(webhooks) == 1
    assert webhooks[0].id == "wh-1"
    assert webhooks[0].events == ["ticket.created"]

    # create_webhook
    responses.add(
        responses.POST,
        "https://mello.mezon.vn/api/v1/webhooks",
        match=[
            responses.matchers.json_params_matcher(
                {
                    "workspace_id": "ws-1",
                    "model_type": "board",
                    "model_id": "b-1",
                    "callback_url": "https://example.com/hook",
                    "event": ["ticket.created"],
                }
            )
        ],
        json={
            "id": "wh-1",
            "user_id": "u-1",
            "workspace_id": "ws-1",
            "model_type": "board",
            "model_id": "b-1",
            "callback_url": "https://example.com/hook",
            "events": ["ticket.created"],
            "active": True,
            "consecutive_failures": 0,
            "signing_secret": "secret123",
        },
        status=201,
    )
    wh = client.create_webhook(
        "ws-1", "board", "b-1", "https://example.com/hook", event=["ticket.created"]
    )
    assert wh.id == "wh-1"
    assert wh.signing_secret == "secret123"

    # update_webhook
    responses.add(
        responses.PATCH,
        "https://mello.mezon.vn/api/v1/webhooks/wh-1",
        match=[responses.matchers.json_params_matcher({"active": False})],
        json={
            "id": "wh-1",
            "user_id": "u-1",
            "workspace_id": "ws-1",
            "model_type": "board",
            "model_id": "b-1",
            "callback_url": "https://example.com/hook",
            "events": ["ticket.created"],
            "active": False,
            "consecutive_failures": 0,
        },
        status=200,
    )
    wh_updated = client.update_webhook("wh-1", active=False)
    assert wh_updated.active is False

    # delete_webhook
    responses.add(
        responses.DELETE,
        "https://mello.mezon.vn/api/v1/webhooks/wh-1",
        status=204,
    )
    client.delete_webhook("wh-1")

    # list_webhook_deliveries
    responses.add(
        responses.GET,
        "https://mello.mezon.vn/api/v1/webhooks/wh-1/deliveries",
        json=[
            {
                "id": "del-1",
                "webhook_id": "wh-1",
                "event_id": "ev-1",
                "event_type": "ticket.created",
                "status": "succeeded",
                "attempts": 1,
            }
        ],
        status=200,
    )
    deliveries = client.list_webhook_deliveries("wh-1")
    assert len(deliveries) == 1
    assert deliveries[0].id == "del-1"

    # redeliver_webhook_event
    responses.add(
        responses.POST,
        "https://mello.mezon.vn/api/v1/webhooks/wh-1/deliveries/del-1/redeliver",
        status=202,
    )
    client.redeliver_webhook_event("wh-1", "del-1")


@responses.activate
def test_github_endpoints(client: MelloClient) -> None:
    workspace_id = "ws-1"
    board_id = "b-1"
    ticket_id = "t-1"

    # list_github_installations
    responses.add(
        responses.GET,
        f"https://mello.mezon.vn/api/v1/workspaces/{workspace_id}/github/installations",
        json=[
            {
                "id": "ghi-1",
                "workspace_id": workspace_id,
                "owner_user_id": "u-1",
                "installation_id": 12345,
                "account_login": "org",
                "account_type": "Organization",
                "state": "active",
            }
        ],
        status=200,
    )
    insts = client.list_github_installations(workspace_id)
    assert len(insts) == 1
    assert insts[0].installation_id == 12345

    # list_github_repositories
    responses.add(
        responses.GET,
        f"https://mello.mezon.vn/api/v1/workspaces/{workspace_id}/github/repositories",
        json=[
            {
                "installation_id": 12345,
                "github_repo_id": 999,
                "owner": "org",
                "name": "repo",
                "full_name": "org/repo",
                "private": True,
                "html_url": "https://github.com/org/repo",
                "default_branch": "main",
            }
        ],
        status=200,
    )
    repos = client.list_github_repositories(workspace_id)
    assert len(repos) == 1
    assert repos[0].full_name == "org/repo"

    # list_github_board_repositories
    responses.add(
        responses.GET,
        f"https://mello.mezon.vn/api/v1/workspaces/{workspace_id}/boards/{board_id}/github/repositories",
        json=[],
        status=200,
    )
    board_repos = client.list_github_board_repositories(workspace_id, board_id)
    assert board_repos == []

    # replace_github_board_repositories
    responses.add(
        responses.PUT,
        f"https://mello.mezon.vn/api/v1/workspaces/{workspace_id}/boards/{board_id}/github/repositories",
        match=[
            responses.matchers.json_params_matcher(
                {"repositories": [{"installation_id": 12345, "github_repo_id": 999}]}
            )
        ],
        json=[
            {
                "installation_id": 12345,
                "github_repo_id": 999,
                "owner": "org",
                "name": "repo",
                "full_name": "org/repo",
                "private": True,
                "html_url": "https://github.com/org/repo",
                "default_branch": "main",
            }
        ],
        status=200,
    )
    rep_repos = client.replace_github_board_repositories(
        workspace_id, board_id, [{"installation_id": 12345, "github_repo_id": 999}]
    )
    assert len(rep_repos) == 1

    # start_github_connect
    responses.add(
        responses.POST,
        f"https://mello.mezon.vn/api/v1/workspaces/{workspace_id}/github/connect/start",
        json={"setup_url": "https://github.com/apps/mello/installations/new", "state": "xyz"},
        status=200,
    )
    conn = client.start_github_connect(workspace_id)
    assert conn["setup_url"] == "https://github.com/apps/mello/installations/new"

    # delete_github_installation
    responses.add(
        responses.DELETE,
        f"https://mello.mezon.vn/api/v1/workspaces/{workspace_id}/github/installations/ghi-1",
        status=204,
    )
    client.delete_github_installation(workspace_id, "ghi-1")

    # search_github_objects
    responses.add(
        responses.GET,
        f"https://mello.mezon.vn/api/v1/tickets/{ticket_id}/github/search?q=fix&type=issue",
        json=[
            {
                "installation_id": 12345,
                "github_repo_id": 999,
                "repository_full_name": "org/repo",
                "object": {
                    "kind": "issue",
                    "number": 1,
                    "title": "Fix bug",
                    "state": "open",
                    "status": "active",
                    "html_url": "https://github.com/org/repo/issues/1",
                },
            }
        ],
        status=200,
    )
    search_res = client.search_github_objects(ticket_id, q="fix", type="issue")
    assert len(search_res) == 1
    assert search_res[0].object.title == "Fix bug"

    # create_github_link
    responses.add(
        responses.POST,
        f"https://mello.mezon.vn/api/v1/tickets/{ticket_id}/github/links",
        match=[
            responses.matchers.json_params_matcher(
                {
                    "installation_id": 12345,
                    "github_repo_id": 999,
                    "kind": "issue",
                    "number": 1,
                }
            )
        ],
        json={
            "id": "link-1",
            "ticket_id": ticket_id,
            "workspace_id": workspace_id,
            "board_id": board_id,
            "github_repo_id": 999,
            "repository_full_name": "org/repo",
            "repository_owner": "org",
            "repository_name": "repo",
            "repository_html_url": "https://github.com/org/repo",
            "kind": "issue",
            "external_key": "org/repo#1",
            "number": 1,
            "title": "Fix bug",
            "state": "open",
            "status": "active",
            "html_url": "https://github.com/org/repo/issues/1",
        },
        status=201,
    )
    link = client.create_github_link(
        ticket_id, installation_id=12345, github_repo_id=999, kind="issue", number=1
    )
    assert link.id == "link-1"

    # delete_github_link
    responses.add(
        responses.DELETE,
        f"https://mello.mezon.vn/api/v1/tickets/{ticket_id}/github/links/link-1",
        status=204,
    )
    client.delete_github_link(ticket_id, "link-1")
