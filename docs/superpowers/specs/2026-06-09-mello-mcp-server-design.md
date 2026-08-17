# Mello MCP Server Design

## Goal

Add a Model Context Protocol server to this SDK so MCP clients can use Mello
workspaces, boards, columns, tickets, comments, history, and search through
typed tools.

## Scope

The first version exposes the full read/write surface already implemented by
`MelloClient`:

- user, workspace, board, column, ticket, comment, history, and search reads
- board, column, ticket, and comment creation/update actions
- destructive and ordering actions: delete board, reorder columns, move ticket

No new Mello REST endpoints are added. The MCP server delegates to the existing
SDK methods.

## Architecture

Add `mello/mcp_server.py` with a FastMCP app built from the official MCP Python
SDK. The app creates `MelloClient` instances from environment configuration:

- `MELLO_API_KEY` is required.
- `MELLO_BASE_URL` is optional and defaults to the SDK base URL.
- `MELLO_TIMEOUT` is optional and defaults to the SDK timeout.

The server is runnable with `python -m mello.mcp_server` and a console script
named `mello-mcp-server`.

## Tool Model

Each MCP tool maps one-to-one to an SDK method. Tool names match SDK method
names so usage stays predictable:

- `get_current_user`
- `list_workspaces`
- `list_workspace_members`
- `list_workspace_boards`
- `create_board`
- `get_board`
- `update_board`
- `delete_board`
- `list_columns`
- `create_column`
- `reorder_columns`
- `update_column`
- `list_board_tickets`
- `create_ticket`
- `get_ticket`
- `update_ticket`
- `move_ticket`
- `list_comments`
- `create_comment`
- `list_history`
- `search_tickets`

Tool results are JSON-serializable dictionaries, lists, or `None`. Dataclasses
are converted recursively and datetimes are serialized as ISO-8601 strings.

## Optional And Nullable Fields

Update tools need to distinguish omitted values from explicit `null`. The MCP
wrapper will use a private sentinel default for optional update parameters and
pass `UNSET` to `MelloClient` when a field is omitted. Explicit `None` is
preserved for nullable fields such as assignee and ticket dates.

Date parameters accepted by MCP tools are strings. They are parsed with
`datetime.fromisoformat`, including a trailing `Z`, before being passed to the
SDK.

## Error Handling

Missing `MELLO_API_KEY` raises a clear runtime configuration error when a tool
is called. API errors continue to use the SDK exception types; FastMCP will
surface them as tool errors to the MCP client.

## Packaging

Add an optional dependency extra:

```toml
[project.optional-dependencies]
mcp = ["mcp>=1.0.0"]
```

Add a console script:

```toml
[project.scripts]
mello-mcp-server = "mello.mcp_server:main"
```

Document local setup in the README.

## Testing

Add focused unit tests for:

- recursive serialization of dataclasses and datetimes
- environment-driven client creation
- selected read/write MCP tool wrappers calling the expected SDK methods
- omitted versus explicit nullable update values

Existing SDK tests remain unchanged.
