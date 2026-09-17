# Mello Python SDK

Typed Python client for the [Mello Public REST API](https://mello.mezon.vn/api/v1).

The SDK wraps Mello workspaces, boards, columns, tickets, comments, history, and
search endpoints with dataclass models and typed exceptions.

## Installation

```bash
uv add mello-sdk
```

Install from source during development:

```bash
git clone <repository-url>
cd mello-python-sdk
uv sync --extra dev
```

If you are not using `uv`, install with `pip install mello-sdk`.

## Quick Start

```python
from mello import MelloClient

client = MelloClient(token="YOUR_PERSONAL_API_TOKEN")

user = client.get_current_user()
print(f"Logged in as {user.name} ({user.email})")

for workspace in client.list_workspaces():
    print(f"Workspace: {workspace.name}")

    for board in client.list_workspace_boards(workspace.id):
        print(f"  Board: {board.name} ({board.code})")
```

## CLI

`mello-cli` is a JSON-first command-line interface for scripts and AI agents. It
uses `MELLO_API_KEY` by default and emits exactly one JSON object on stdout.

```bash
export MELLO_API_KEY="mello_pat_..."

mello-cli me get
mello-cli workspace list
mello-cli ticket search --workspace-id "workspace-uuid" --query "login crash"
mello-cli ticket update --ticket-id "ticket-uuid" --set title="Fix login on iOS"
mello-cli ticket update --ticket-id "ticket-uuid" --clear pic_user_id
```

Omitted update fields stay unchanged. `--clear field` (or `--set field=null`)
clears nullable fields such as `pic_user_id`, `supervisor_id`, and dates.

Destructive and high-impact operations require explicit confirmation. After
confirming the target with the user, pass `--yes`:

```bash
mello-cli --yes ticket delete --ticket-id "ticket-uuid"
mello-cli --yes github replace-board-repos \
  --workspace-id "workspace-uuid" --board-id "board-uuid" \
  --repositories '[{"installation_id": 1, "github_repo_id": 2}]'
```

Use `--token`, `--base-url`, and `--timeout` to override `MELLO_API_KEY`,
`MELLO_BASE_URL`, and `MELLO_TIMEOUT`. Run `mello-cli --help` for the complete
resource command surface.

### Install the CLI globally

Install `mello-cli` (and `mello-mcp-server`) globally as an isolated tool with
[uv](https://docs.astral.sh/uv/):

```bash
# From PyPI
uv tool install mello-sdk

# Or directly from this repository (local development)
uv tool install --from . mello-sdk
```

The executables land in `~/.local/bin` (make sure it is on your `PATH`).

**Important:** when installed from a local source directory, the global tool
does **not** track your changes. After updating the CLI code in this repo,
reinstall to refresh the global executables:

```bash
uv tool install --from . mello-sdk --force
```

### Claude Code Skill

The repository ships a [Claude Code](https://claude.com/claude-code) skill at
[`skills/mello/`](skills/mello/) that teaches agents to operate Mello through
`mello-cli` (JSON output, safe confirmation rules, update semantics).

To use it, install the skill into your Claude Code configuration:

```bash
# Personal (available in every project)
cp -r skills/mello ~/.claude/skills/mello

# Or project-local (only inside a specific project)
cp -r skills/mello /path/to/your-project/.claude/skills/mello
```

Then make sure `mello-cli` is installed globally (see above) and
`MELLO_API_KEY` is set in your shell environment. Claude Code will trigger the
`mello` skill automatically for Mello-related requests.

## MCP Server

The package can also run as a Model Context Protocol server for AI assistants
that support MCP tools.

Install the MCP extra:

```bash
uv add "mello-sdk[mcp]"
```

For local development from this repository:

```bash
uv sync --extra mcp --extra dev
```

### Configuration & Authentication

The MCP server supports both single-user and multi-user/remote deployments. API keys are resolved in order:
1. **Explicit tool argument**: `api_key="..."` on any tool call.
2. **Session tool**: Calling `set_api_key(api_key="...")` once sets the token for the active session.
3. **HTTP Header / Query Param** (Remote SSE / HTTP mode):
   - Header: `Authorization: Bearer <token>` or `X-Mello-Api-Key: <token>`
   - Query Param: `?api_key=<token>`
4. **Environment Variable**: `MELLO_API_KEY` (fallback default).

```bash
# Optional fallback token for stdio or single-user deployments:
export MELLO_API_KEY="mello_pat_..."
export MELLO_BASE_URL="https://mello.mezon.vn/api/v1"  # optional
export MELLO_TIMEOUT="30"                              # optional seconds
```

### Running the Server

Run locally with stdio:

```bash
uv run mello-mcp-server
# or: uv run python -m mello.mcp_server
```

Run as a remote SSE service accessible to other machines on the network:

```bash
uv run mello-mcp-server --transport sse --host 0.0.0.0 --port 8000
# or with streamable-http:
# uv run mello-mcp-server --transport streamable-http --host 0.0.0.0 --port 8000
```

You can also configure via environment variables: `MCP_TRANSPORT=sse`, `MCP_HOST=0.0.0.0`, `MCP_PORT=8000`.

### Remote MCP Client Configuration

Other machines and MCP clients (Claude Desktop, Cursor, etc.) can connect over SSE.

#### 1. Header-based Authentication (Recommended)

In client configs that support HTTP headers (e.g. Claude Desktop, Cursor):

```json
{
  "mcpServers": {
    "mello": {
      "url": "http://<server-host>:8000/sse",
      "headers": {
        "Authorization": "Bearer mello_pat_your_personal_token"
      }
    }
  }
}
```

#### 2. Query Parameter

```json
{
  "mcpServers": {
    "mello": {
      "url": "http://<server-host>:8000/sse?api_key=mello_pat_your_personal_token"
    }
  }
}
```

#### 3. In-Chat Session Key

If your client does not configure custom headers, connect to `http://<server-host>:8000/sse` and instruct your assistant:
> "Use the `set_api_key` tool with my Mello token `mello_pat_...`"

All subsequent tool calls in that session will use your token.

### Docker

The repository ships a `Dockerfile` and `docker-compose.yml` for remote deployments.

Build and run with Docker:

```bash
docker build -t mello-mcp-server .
# Run without hardcoded key (clients provide their own key):
docker run --rm -p 8000:8000 -e MCP_TRANSPORT=sse mello-mcp-server

# Or with a shared fallback key:
docker run --rm -p 8000:8000 -e MCP_TRANSPORT=sse -e MELLO_API_KEY="mello_pat_..." mello-mcp-server
```

Or use Docker Compose:

```bash
docker compose up --build
```

## Usage

### Boards

```python
board = client.create_board(
    workspace_id="workspace-uuid",
    name="Q3 Planning",
    code="Q3PL",
)

board_detail = client.get_board(board.id)

client.update_board(
    board.id,
    name="Q3 Project Planning",
    background_color="#3b5998",
)

client.delete_board(board.id)
```

### Columns

```python
column = client.create_column(
    board_id="board-uuid",
    name="In Review",
    position=2,
)

client.update_column(column.id, name="Code Review", color="#ffcc00")

client.reorder_columns(
    board_id="board-uuid",
    column_ids=["column-uuid-1", "column-uuid-2", "column-uuid-3"],
)
```

### Tickets and Labels

```python
# Create ticket with Markdown rendered server-side
ticket = client.create_ticket(
    column_id="column-uuid",
    title="Fix login crash",
    description_markdown="## Steps to reproduce\n\n1. Open app\n2. Click login",
)

ticket_detail = client.get_ticket(ticket.id)
print(len(ticket_detail.comments))

# Labels
label = client.create_label(board_id="board-uuid", name="Bug", color="#ff0000")
client.attach_label_to_ticket(ticket.id, label.id)
client.detach_label_from_ticket(ticket.id, label.id)
client.delete_label(label.id)

client.update_ticket(
    ticket.id,
    title="Fix login crash on iOS",
    description_markdown="## Updated steps\n\n1. Open iOS app",
    pic_user_id="user-uuid",
)

# Nullable fields can be cleared explicitly with None.
client.update_ticket(
    ticket.id,
    pic_user_id=None,
    supervisor_id=None,
    start_date=None,
    end_date=None,
)

client.move_ticket(ticket.id, column_id="other-column-uuid", position=0)
```

### Comments, History, And Search

```python
# Create comment with Markdown support
comment = client.create_comment(
    ticket_id="ticket-uuid",
    body="Investigating this issue now.",
    body_markdown="Investigating this issue **now**.",
)

comments = client.list_comments(ticket_id="ticket-uuid")
history = client.list_history(ticket_id="ticket-uuid")
results = client.search_tickets(workspace_id="workspace-uuid", q="login crash")
```

### Webhook Signature Verification

```python
from mello import verify_webhook_signature

is_valid = verify_webhook_signature(
    payload=raw_request_body_bytes,
    signature_header=request.headers.get("X-Mello-Signature"),
    timestamp_header=request.headers.get("X-Mello-Timestamp"),
    secret="YOUR_WEBHOOK_SECRET",
    tolerance_seconds=300,
)
```

## Error Handling

The SDK raises typed exceptions derived from `MelloAPIException` for API errors:

```python
from mello import (
    MelloAPIException,
    MelloClient,
    ForbiddenException,
    NotFoundException,
    RateLimitedException,
    UnauthorizedException,
    ValidationErrorException,
)

client = MelloClient(token="YOUR_PERSONAL_API_TOKEN")

try:
    client.get_current_user()
except UnauthorizedException:
    print("Invalid or expired API token.")
except ForbiddenException:
    print("The token cannot access this resource.")
except NotFoundException:
    print("Resource not found.")
except ValidationErrorException as exc:
    print(f"Validation failed: {exc.fields}")
except RateLimitedException:
    print("Rate limit exceeded. Try again later.")
except MelloAPIException as exc:
    print(f"Mello API error {exc.status_code}: {exc.error_code}")
```

## Development

Install development dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run unit tests:

```bash
pytest
```

Run live integration tests. These tests create and delete data in your Mello
workspace, so use a dedicated test token when possible:

```bash
export MELLO_API_KEY="mello_pat_..."
pytest -m integration
```

Run quality checks:

```bash
black --check mello tests
flake8 mello tests
mypy mello tests
```

## Build And Publish

The package uses `pyproject.toml` with `setuptools`. Build artifacts locally:

```bash
python -m build
python -m twine check dist/*
```

Recommended release flow:

```bash
rm -rf dist/ build/ *.egg-info
python -m build
python -m twine check dist/*
python -m twine upload --repository testpypi dist/*
```

After validating installation from TestPyPI, publish to PyPI:

```bash
python -m twine upload dist/*
```

Use PyPI API tokens instead of passwords, and avoid committing `.env`,
`.pypirc`, `dist/`, or build artifacts.

## License

MIT. See [LICENSE](LICENSE).
