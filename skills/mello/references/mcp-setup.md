# Optional Mello MCP Setup

Use MCP only when the user explicitly requests MCP or when an existing Mello MCP
server is already attached. For normal Mello operations, prefer `mello-cli`.

## Install

```bash
uv add "mello-sdk[mcp]"
# or
pip install "mello-sdk[mcp]"
```

Set a token in the server environment:

```bash
export MELLO_API_KEY="mello_pat_..."
export MELLO_BASE_URL="https://mello.mezon.vn/api/v1"  # optional
export MELLO_TIMEOUT="30"                              # optional seconds
```

## Run

Use stdio for a local MCP client:

```bash
mello-mcp-server
# or: python -m mello.mcp_server
```

For HTTP transport:

```bash
MCP_TRANSPORT=streamable-http MCP_HOST=127.0.0.1 MCP_PORT=8000 mello-mcp-server
```

The streamable HTTP endpoint is `http://127.0.0.1:8000/mcp`.

## Claude Code stdio Configuration

Use the command and environment appropriate for the user's package manager. Do
not place the token in a checked-in project config.

```json
{
  "mcpServers": {
    "mello": {
      "command": "mello-mcp-server",
      "env": {
        "MELLO_API_KEY": "${MELLO_API_KEY}"
      }
    }
  }
}
```

## MCP Update Behavior

MCP update tools accept an `updates` object. Omit a key to leave it unchanged;
set a key to JSON `null` to clear it. Ticket updates use `pic_user_id` and
`supervisor_id`, not `assignee_id`.

Attachments use Base64 string payloads through MCP. The CLI instead uploads and
downloads file paths directly and is the safer default for agent workflows.
