import os
from datetime import datetime, timezone
import pytest
from mello import MelloClient

# Load .env file manually to populate os.environ
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

API_KEY = os.getenv("MELLO_API_KEY")
pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not API_KEY, reason="MELLO_API_KEY is not set in environment or .env"
)
def test_mello_client_integration() -> None:
    assert API_KEY is not None
    # Initialize the real client
    client = MelloClient(token=API_KEY)

    # 1. Get current user
    user = client.get_current_user()
    assert user.id is not None
    assert user.email != ""
    assert user.name != ""

    # 2. List workspaces
    workspaces = client.list_workspaces()
    assert len(workspaces) > 0
    workspace = workspaces[0]
    assert workspace.id != ""

    # 3. List workspace members
    members = client.list_workspace_members(workspace.id)
    assert len(members) > 0
    assert any(m.user_id == user.id for m in members)

    # 4. Create a board
    test_board_name = f"Integration Test Board - {int(datetime.now().timestamp())}"
    board = client.create_board(workspace.id, name=test_board_name)
    assert board.id != ""
    assert board.name == test_board_name

    try:
        # 5. List boards and ensure our new board is in the list
        boards = client.list_workspace_boards(workspace.id)
        assert any(b.id == board.id for b in boards)

        # 6. Get Board detail
        board_detail = client.get_board(board.id)
        assert board_detail.id == board.id
        assert isinstance(board_detail.columns, list)

        # 7. Create a Column
        column = client.create_column(board.id, name="To Do", position=0)
        assert column.id != ""
        assert column.name == "To Do"

        # 8. List columns
        columns = client.list_columns(board.id)
        assert len(columns) > 0
        assert any(c.id == column.id for c in columns)

        # 9. Create a Ticket
        ticket = client.create_ticket(
            column.id,
            title="Integrate Mello SDK",
            description="Verify ticket operations against live API",
            position=0,
        )
        assert ticket.id != ""
        assert ticket.title == "Integrate Mello SDK"
        assert ticket.column_id == column.id

        # 10. List board tickets
        tickets = client.list_board_tickets(board.id)
        assert len(tickets) > 0
        assert any(t.id == ticket.id for t in tickets)

        # 11. Update ticket description and clear/set start_date
        now = datetime.now(timezone.utc)
        updated_ticket = client.update_ticket(
            ticket.id,
            description="Updated description",
            start_date=now,
        )
        assert updated_ticket.description == "Updated description"

        # Verify we can clear assignee/dates (set to None)
        cleared_ticket = client.update_ticket(
            ticket.id,
            assignee_id=None,
            start_date=None,
            end_date=None,
        )
        assert cleared_ticket.assignee_id is None

        # 12. Create a comment
        comment = client.create_comment(
            ticket.id,
            body="SDK integration test is running successfully.",
            body_html="<p>SDK integration test is running successfully.</p>",
        )
        assert comment.id != ""
        assert comment.body == "SDK integration test is running successfully."

        # 13. List comments
        comments = client.list_comments(ticket.id)
        assert len(comments) > 0
        assert any(c.id == comment.id for c in comments)

        # 14. List History
        history = client.list_history(ticket.id)
        assert len(history) > 0

        # 15. Search tickets
        search_results = client.search_tickets(workspace.id, q="SDK")
        assert isinstance(search_results, list)

    finally:
        # Cleanup: delete the board
        client.delete_board(board.id)

        # Verify deletion
        boards_after_cleanup = client.list_workspace_boards(workspace.id)
        assert not any(b.id == board.id for b in boards_after_cleanup)
