---
name: mello
description: This skill should be used when interacting with Mello workspaces, boards, columns, tickets, comments, checklists, attachments, webhooks, or GitHub links; using mello-sdk, mello-cli, or mello-mcp-server; or when a user asks to create, move, search, update, or delete a Mello ticket.
---

# Mello

Use `mello-cli` as the default Mello control plane. It produces one JSON response
on stdout and has stable nonzero exit codes and structured errors on stderr.
Prefer it to ad-hoc `curl`, a one-off Python SDK script, or MCP tools when
performing Mello work.

## Prerequisites

- `mello-cli` must be installed (`pip install mello-sdk` or `uv add mello-sdk`).
- Require `MELLO_API_KEY` in the command environment. Never invent, echo, log,
  or put API tokens in source control.
- Optional configuration: `MELLO_BASE_URL` and `MELLO_TIMEOUT`. Command-line
  `--token`, `--base-url`, and `--timeout` override environment values.

Check configuration safely with a read-only command:

```bash
mello-cli me get
```

A success response is `{"ok":true,"data":...}`. On error, inspect stderr's
`{"ok":false,"error":...}` response and report `error.message` and validation
fields without exposing credentials.

## Operating Workflow

1. Resolve ambiguity before mutating: use `workspace list`, `board list`,
   `ticket search`, `ticket list`, or `ticket get` to identify the exact ID.
2. Use resource commands described in [operations.md](references/operations.md).
3. Parse JSON stdout before deciding the next command. Do not infer an ID from a
   resource name if multiple results are possible.
4. Use exactly one control plane per mutation: `mello-cli` by default. Do not
   repeat a write through the SDK or MCP after it already succeeded.
5. Keep commands machine-readable: do not add unrelated shell output when
   consuming JSON response data.

## Safety Policy

Ask the user for explicit confirmation before any command marked **confirm** in
the operations reference. This includes deletion, replacing connected GitHub
repositories, creating/updating/redelivering webhooks, starting a GitHub
connection, and linking/unlinking GitHub objects.

After the user confirms the exact target and action, include `--yes`:

```bash
mello-cli --yes ticket delete --ticket-id "ticket-uuid"
```

Never attempt to answer an interactive prompt. Without `--yes`, noninteractive
execution returns `error.type: "confirmation_required"`; surface that to the
user and obtain confirmation instead. Read-only commands and ordinary,
unambiguously requested board/ticket/comment/checklist writes do not need an
extra confirmation.

## Update Semantics

For every `update` command:

- Omit a field to leave it unchanged.
- Use repeatable `--set FIELD=VALUE` for changes.
- Use `--clear FIELD` or `--set FIELD=null` to send an explicit null for a
  nullable field.
- Use current ticket fields `pic_user_id` and `supervisor_id`. Do **not** use
  retired `assignee_id`.

Examples:

```bash
mello-cli ticket update --ticket-id "ticket-uuid" --set title="Fix login on iOS"
mello-cli ticket update --ticket-id "ticket-uuid" --clear pic_user_id
mello-cli ticket update --ticket-id "ticket-uuid" --set start_date=2026-08-04T09:00:00Z
```

## Attachments

Use a path for uploads. For downloads, use `--output PATH` to write bytes to a
file. Without `--output`, the CLI returns Base64 in JSON instead of raw binary.

```bash
mello-cli attachment upload --ticket-id "ticket-uuid" --file ./report.pdf
mello-cli attachment download --attachment-id "attachment-uuid" --output ./report.pdf
```

## Source of Truth

When working from a clone of the SDK, validate less-common options against:

- `mello/cli.py` — CLI flags and command behavior
- `mello/client.py` — typed SDK method surface
- `docs/mello.v1.yaml` — public API contract
- `mello/mcp_server.py` — MCP setup/tool surface, only when the user explicitly
  asks to use MCP; see [mcp-setup.md](references/mcp-setup.md)
