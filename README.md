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

Configure the server with environment variables:

```bash
export MELLO_API_KEY="mello_pat_..."
export MELLO_BASE_URL="https://mello.mezon.vn/api/v1"  # optional
export MELLO_TIMEOUT="30"                              # optional seconds
```

Run it with the console script:

```bash
uv run mello-mcp-server
```

Or run the module directly:

```bash
uv run python -m mello.mcp_server
```

The MCP server exposes the SDK's full read/write surface: workspaces, boards,
columns, tickets, comments, history, and search. Update tools accept an
`updates` object so omitted fields are left unchanged while explicit `null`
values are sent to Mello for nullable fields.

### Transport

`main()` selects the transport from the `MCP_TRANSPORT` environment variable.
The default is `stdio` for local assistant integrations. Set it to
`streamable-http` (or `sse`) to expose the server over HTTP. In HTTP mode the
bind address is controlled by `MCP_HOST` (default `0.0.0.0`) and `MCP_PORT`
(default `8000`).

```bash
MCP_TRANSPORT=streamable-http MCP_PORT=8000 uv run mello-mcp-server
```

### Docker

The repository ships a `Dockerfile` and `docker-compose.yml` that run the
server with the `streamable-http` transport on port `8000`.

Build and run with Docker:

```bash
docker build -t mello-mcp-server .
docker run --rm -p 8000:8000 -e MELLO_API_KEY="mello_pat_..." mello-mcp-server
```

Or use Docker Compose (reads `MELLO_API_KEY` from your environment or `.env`):

```bash
export MELLO_API_KEY="mello_pat_..."
docker compose up --build
```

The HTTP endpoint is served at `http://localhost:8000/mcp`. Point an MCP client
that supports the streamable-http transport at that URL.

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

### Tickets

```python
ticket = client.create_ticket(
    column_id="column-uuid",
    title="Fix login crash",
    description="Steps to reproduce...",
)

ticket_detail = client.get_ticket(ticket.id)
print(len(ticket_detail.comments))

client.update_ticket(
    ticket.id,
    title="Fix login crash on iOS",
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
comment = client.create_comment(
    ticket_id="ticket-uuid",
    body="Investigating this issue now.",
)

comments = client.list_comments(ticket_id="ticket-uuid")
history = client.list_history(ticket_id="ticket-uuid")
results = client.search_tickets(workspace_id="workspace-uuid", q="login crash")
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
