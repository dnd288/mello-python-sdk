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

### Local stdio
```bash
mello-mcp-server
# or: python -m mello.mcp_server
```

### Remote SSE / HTTP (for remote clients / multiple machines)
```bash
mello-mcp-server --transport sse --host 0.0.0.0 --port 8000
# or with streamable-http:
# mello-mcp-server --transport streamable-http --host 0.0.0.0 --port 8000
```

When running remotely, clients can supply their own Mello token via:
1. `Authorization: Bearer <token>` or `X-Mello-Api-Key: <token>` HTTP header
2. `?api_key=<token>` query param
3. Assistant calling `set_api_key(api_key="<token>")`
4. Individual tool calls specifying `api_key="<token>"`

## Remote MCP Client Configuration (SSE)

For Claude Desktop, Cursor, or remote agents connecting over network:

```json
{
  "mcpServers": {
    "mello": {
      "url": "http://<server-host>:8000/sse",
      "headers": {
        "Authorization": "Bearer mello_pat_..."
      }
    }
  }
}
```

## Local Claude Code / Desktop stdio Configuration

Use the command and environment appropriate for the user's package manager:

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
