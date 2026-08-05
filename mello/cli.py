"""JSON-first command-line interface for the Mello Public API."""

import argparse
import base64
import json
import os
import sys
import traceback
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Callable, Dict, List, NoReturn, Optional, Sequence

import requests

from mello.client import MelloClient
from mello.exceptions import (
    ForbiddenException,
    MelloAPIException,
    NotFoundException,
    RateLimitedException,
    UnauthorizedException,
    ValidationErrorException,
)
from mello.serialize import serialize

ClientFactory = Callable[..., MelloClient]

UPDATE_FIELDS = {
    "board": {"name", "background_color", "cover_image_url"},
    "column": {"name", "position", "color"},
    "ticket": {
        "title",
        "description",
        "description_html",
        "pic_user_id",
        "supervisor_id",
        "start_date",
        "end_date",
    },
    "checklist": {"title", "position"},
    "label": {"name", "color"},
    "checklist_item": {"title", "is_checked", "position"},
    "webhook": {"active", "events", "description", "callback_url"},
}
DATE_UPDATE_FIELDS = {"start_date", "end_date"}
INT_UPDATE_FIELDS = {"position"}
BOOL_UPDATE_FIELDS = {"is_checked", "active"}


class CLIError(Exception):
    """A command-line usage, configuration, or confirmation error."""

    def __init__(self, message: str, error_type: str = "usage", exit_code: int = 2):
        self.message = message
        self.error_type = error_type
        self.exit_code = exit_code
        super().__init__(message)


class MelloArgumentParser(argparse.ArgumentParser):
    """Argument parser that preserves JSON error output for automation."""

    def error(self, message: str) -> NoReturn:
        raise CLIError(message)


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON output (default)."
    )
    parser.add_argument("--text", action="store_true", help="Emit human-readable JSON.")
    parser.add_argument("--token", help="Mello API token. Overrides MELLO_API_KEY.")
    parser.add_argument("--base-url", help="Mello API base URL.")
    parser.add_argument("--timeout", type=float, help="Request timeout in seconds.")
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Confirm destructive action."
    )
    parser.add_argument(
        "--no-input", action="store_true", help="Never prompt for confirmation."
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress non-data output."
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print traceback for errors."
    )
    parser.add_argument("--version", action="version", version=_version_string())


def _version_string() -> str:
    try:
        return version("mello-sdk")
    except PackageNotFoundError:
        return "mello-sdk (development)"


def _subparser(parent: Any, name: str, help_text: str) -> argparse.ArgumentParser:
    return parent.add_parser(name, help=help_text)


def _required(parser: argparse.ArgumentParser, *names: str) -> None:
    for name in names:
        parser.add_argument(name, required=True)


def _updates(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="FIELD=VALUE",
        help="Set an update field; may be repeated. JSON values are accepted.",
    )
    parser.add_argument(
        "--clear",
        action="append",
        default=[],
        metavar="FIELD",
        help="Clear a nullable update field; may be repeated.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = MelloArgumentParser(
        prog="mello-cli", description="JSON-first CLI for the Mello Public API."
    )
    _add_common_options(parser)
    groups = parser.add_subparsers(dest="group", required=True)

    me = _subparser(groups, "me", "Authenticated user operations")
    me_sub = me.add_subparsers(dest="verb", required=True)
    _subparser(me_sub, "get", "Get the authenticated user").set_defaults(func=_cmd_me)

    whoami = _subparser(groups, "whoami", "Alias for 'me get'")
    whoami.set_defaults(func=_cmd_me)

    workspace = _subparser(groups, "workspace", "Workspace operations")
    ws_sub = workspace.add_subparsers(dest="verb", required=True)
    _subparser(ws_sub, "list", "List workspaces").set_defaults(func=_cmd_workspace_list)
    p = _subparser(ws_sub, "members", "List workspace members")
    _required(p, "--workspace-id")
    p.set_defaults(func=_cmd_workspace_members)

    board = _subparser(groups, "board", "Board operations")
    b_sub = board.add_subparsers(dest="verb", required=True)
    p = _subparser(b_sub, "list", "List workspace boards")
    _required(p, "--workspace-id")
    p.set_defaults(func=_cmd_board_list)
    p = _subparser(b_sub, "get", "Get a board")
    _required(p, "--board-id")
    p.set_defaults(func=_cmd_board_get)
    p = _subparser(b_sub, "create", "Create a board")
    _required(p, "--workspace-id", "--name")
    p.add_argument("--code")
    p.set_defaults(func=_cmd_board_create)
    p = _subparser(b_sub, "update", "Update a board")
    _required(p, "--board-id")
    _updates(p)
    p.set_defaults(func=_cmd_board_update)
    p = _subparser(b_sub, "delete", "Delete a board")
    _required(p, "--board-id")
    p.set_defaults(func=_cmd_board_delete, destructive=True)

    column = _subparser(groups, "column", "Column operations")
    c_sub = column.add_subparsers(dest="verb", required=True)
    p = _subparser(c_sub, "list", "List board columns")
    _required(p, "--board-id")
    p.set_defaults(func=_cmd_column_list)
    p = _subparser(c_sub, "create", "Create a column")
    _required(p, "--board-id", "--name")
    p.add_argument("--position", type=int)
    p.set_defaults(func=_cmd_column_create)
    p = _subparser(c_sub, "update", "Update a column")
    _required(p, "--column-id")
    _updates(p)
    p.set_defaults(func=_cmd_column_update)
    p = _subparser(c_sub, "reorder", "Reorder board columns")
    _required(p, "--board-id", "--column-ids")
    p.set_defaults(func=_cmd_column_reorder)

    label = _subparser(groups, "label", "Label operations")
    l_sub = label.add_subparsers(dest="verb", required=True)
    p = _subparser(l_sub, "list", "List board labels")
    _required(p, "--board-id")
    p.set_defaults(func=_cmd_label_list)
    p = _subparser(l_sub, "create", "Create a label")
    _required(p, "--board-id", "--name")
    p.add_argument("--color")
    p.set_defaults(func=_cmd_label_create)
    p = _subparser(l_sub, "update", "Update a label")
    _required(p, "--label-id")
    _updates(p)
    p.set_defaults(func=_cmd_label_update)
    ticket = _subparser(groups, "ticket", "Ticket operations")
    t_sub = ticket.add_subparsers(dest="verb", required=True)
    p = _subparser(t_sub, "list", "List board tickets")
    _required(p, "--board-id")
    p.set_defaults(func=_cmd_ticket_list)
    p = _subparser(t_sub, "get", "Get ticket detail")
    _required(p, "--ticket-id")
    p.set_defaults(func=_cmd_ticket_get)
    p = _subparser(t_sub, "create", "Create a ticket")
    _required(p, "--column-id", "--title")
    p.add_argument("--description")
    p.add_argument("--position", type=int)
    p.set_defaults(func=_cmd_ticket_create)
    p = _subparser(t_sub, "update", "Update a ticket")
    _required(p, "--ticket-id")
    _updates(p)
    p.set_defaults(func=_cmd_ticket_update)
    p = _subparser(t_sub, "move", "Move a ticket")
    _required(p, "--ticket-id", "--column-id", "--position")
    p.set_defaults(func=_cmd_ticket_move)
    p = _subparser(t_sub, "delete", "Delete a ticket")
    _required(p, "--ticket-id")
    p.set_defaults(func=_cmd_ticket_delete, destructive=True)
    p = _subparser(t_sub, "search", "Search workspace tickets")
    _required(p, "--workspace-id", "--query")
    p.set_defaults(func=_cmd_ticket_search)

    comment = _subparser(groups, "comment", "Comment operations")
    cm_sub = comment.add_subparsers(dest="verb", required=True)
    p = _subparser(cm_sub, "list", "List ticket comments")
    _required(p, "--ticket-id")
    p.set_defaults(func=_cmd_comment_list)
    p = _subparser(cm_sub, "create", "Create a comment")
    _required(p, "--ticket-id", "--body")
    p.add_argument("--body-html")
    p.set_defaults(func=_cmd_comment_create)

    history = _subparser(groups, "history", "Ticket history")
    h_sub = history.add_subparsers(dest="verb", required=True)
    p = _subparser(h_sub, "list", "List ticket history")
    _required(p, "--ticket-id")
    p.set_defaults(func=_cmd_history_list)

    checklist = _subparser(groups, "checklist", "Checklist operations")
    cl_sub = checklist.add_subparsers(dest="verb", required=True)
    p = _subparser(cl_sub, "create", "Create a checklist")
    _required(p, "--ticket-id", "--title")
    p.add_argument("--position", type=int)
    p.set_defaults(func=_cmd_checklist_create)
    p = _subparser(cl_sub, "update", "Update a checklist")
    _required(p, "--checklist-id")
    _updates(p)
    p.set_defaults(func=_cmd_checklist_update)
    p = _subparser(cl_sub, "delete", "Delete a checklist")
    _required(p, "--checklist-id")
    p.set_defaults(func=_cmd_checklist_delete, destructive=True)
    p = _subparser(cl_sub, "item-create", "Create a checklist item")
    _required(p, "--checklist-id", "--title")
    p.add_argument("--position", type=int)
    p.set_defaults(func=_cmd_checklist_item_create)
    p = _subparser(cl_sub, "item-update", "Update a checklist item")
    _required(p, "--checklist-item-id")
    _updates(p)
    p.set_defaults(func=_cmd_checklist_item_update)
    p = _subparser(cl_sub, "item-delete", "Delete a checklist item")
    _required(p, "--checklist-item-id")
    p.set_defaults(func=_cmd_checklist_item_delete, destructive=True)

    attachment = _subparser(groups, "attachment", "Attachment operations")
    a_sub = attachment.add_subparsers(dest="verb", required=True)
    p = _subparser(a_sub, "upload", "Upload an attachment")
    _required(p, "--ticket-id", "--file")
    p.add_argument("--content-type")
    p.set_defaults(func=_cmd_attachment_upload)
    p = _subparser(a_sub, "download", "Download an attachment")
    _required(p, "--attachment-id")
    p.add_argument("--output")
    p.set_defaults(func=_cmd_attachment_download)

    webhook = _subparser(groups, "webhook", "Webhook operations")
    w_sub = webhook.add_subparsers(dest="verb", required=True)
    _subparser(w_sub, "list", "List webhooks").set_defaults(func=_cmd_webhook_list)
    p = _subparser(w_sub, "create", "Create a webhook")
    _required(p, "--workspace-id", "--model-type", "--model-id", "--callback-url")
    p.add_argument("--event", action="append", default=[])
    p.add_argument("--description")
    p.set_defaults(func=_cmd_webhook_create, destructive=True)
    p = _subparser(w_sub, "update", "Update a webhook")
    _required(p, "--webhook-id")
    _updates(p)
    p.set_defaults(func=_cmd_webhook_update, destructive=True)
    p = _subparser(w_sub, "delete", "Delete a webhook")
    _required(p, "--webhook-id")
    p.set_defaults(func=_cmd_webhook_delete, destructive=True)
    p = _subparser(w_sub, "deliveries", "List webhook deliveries")
    _required(p, "--webhook-id")
    p.set_defaults(func=_cmd_webhook_deliveries)
    p = _subparser(w_sub, "redeliver", "Redeliver a webhook event")
    _required(p, "--webhook-id", "--delivery-id")
    p.set_defaults(func=_cmd_webhook_redeliver, destructive=True)

    github = _subparser(groups, "github", "GitHub integration operations")
    g_sub = github.add_subparsers(dest="verb", required=True)
    for name, func, help_text in [
        ("installations", _cmd_github_installations, "List GitHub installations"),
        ("repos", _cmd_github_repos, "List workspace repositories"),
    ]:
        p = _subparser(g_sub, name, help_text)
        _required(p, "--workspace-id")
        p.set_defaults(func=func)
    p = _subparser(g_sub, "board-repos", "List board repositories")
    _required(p, "--workspace-id", "--board-id")
    p.set_defaults(func=_cmd_github_board_repos)
    p = _subparser(g_sub, "replace-board-repos", "Replace board repositories")
    _required(p, "--workspace-id", "--board-id", "--repositories")
    p.set_defaults(func=_cmd_github_replace_board_repos, destructive=True)
    p = _subparser(g_sub, "connect-start", "Start GitHub App connection")
    _required(p, "--workspace-id")
    p.add_argument("--replace", action="store_true")
    p.add_argument("--board-id")
    p.set_defaults(func=_cmd_github_connect_start, destructive=True)
    p = _subparser(g_sub, "delete-installation", "Delete a GitHub installation")
    _required(p, "--workspace-id", "--installation-id")
    p.set_defaults(func=_cmd_github_delete_installation, destructive=True)
    p = _subparser(g_sub, "search", "Search GitHub objects for a ticket")
    _required(p, "--ticket-id")
    p.add_argument("--query")
    p.add_argument("--type", choices=["issue", "pull_request", "branch", "commit"])
    p.add_argument("--page", type=int)
    p.set_defaults(func=_cmd_github_search)
    p = _subparser(g_sub, "link", "Link a GitHub object to a ticket")
    _required(p, "--ticket-id", "--installation-id", "--github-repo-id", "--kind")
    p.add_argument("--number", type=int)
    p.add_argument("--branch-name")
    p.set_defaults(func=_cmd_github_link, destructive=True)
    p = _subparser(g_sub, "unlink", "Unlink a GitHub object from a ticket")
    _required(p, "--ticket-id", "--link-id")
    p.set_defaults(func=_cmd_github_unlink, destructive=True)

    return parser


def _parse_value(value: str, field: str) -> Any:
    if value.lower() in ("null", "none"):
        return None
    if field in DATE_UPDATE_FIELDS:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            raise CLIError("%s must be an ISO-8601 datetime or null" % field)
    if field in INT_UPDATE_FIELDS:
        try:
            return int(value)
        except ValueError:
            raise CLIError("%s must be an integer" % field)
    if field in BOOL_UPDATE_FIELDS:
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False
        raise CLIError("%s must be true or false" % field)
    try:
        parsed = json.loads(value)
    except ValueError:
        return value
    return parsed


def _parse_updates(args: argparse.Namespace, resource: str) -> Dict[str, Any]:
    allowed = UPDATE_FIELDS[resource]
    updates: Dict[str, Any] = {}
    for assignment in args.set:
        if "=" not in assignment:
            raise CLIError("--set must use FIELD=VALUE")
        field, value = assignment.split("=", 1)
        if field not in allowed:
            raise CLIError("Unsupported update field: %s" % field)
        updates[field] = _parse_value(value, field)
    for field in args.clear:
        if field not in allowed:
            raise CLIError("Unsupported update field: %s" % field)
        updates[field] = None
    if not updates:
        raise CLIError("Provide at least one --set or --clear update field")
    return updates


def _require_confirmation(args: argparse.Namespace, action: str) -> None:
    if args.yes:
        return
    non_interactive = (
        args.no_input
        or not sys.stdin.isatty()
        or os.environ.get("MELLO_CLI_NO_INPUT") == "1"
        or os.environ.get("CI")
    )
    if non_interactive:
        raise CLIError(
            "Confirmation required for %s; rerun with --yes after user confirmation."
            % action,
            "confirmation_required",
        )
    answer = input("Confirm %s? [y/N] " % action).strip().lower()
    if answer not in ("y", "yes"):
        raise CLIError("Cancelled %s." % action, "confirmation_required")


def _client_from_args(
    args: argparse.Namespace, factory: Optional[ClientFactory]
) -> MelloClient:
    token = args.token or os.environ.get("MELLO_API_KEY")
    if not token:
        raise CLIError("MELLO_API_KEY or --token is required", "config")
    base_url = args.base_url or os.environ.get(
        "MELLO_BASE_URL", "https://mello.mezon.vn/api/v1"
    )
    timeout = args.timeout
    if timeout is None:
        try:
            timeout = float(os.environ.get("MELLO_TIMEOUT", "30.0"))
        except ValueError:
            raise CLIError("MELLO_TIMEOUT must be a number", "config")
    factory = factory or MelloClient
    return factory(token=token, base_url=base_url, timeout=timeout)


def _success(data: Any, text: bool) -> None:
    payload: Dict[str, Any] = {"ok": True, "data": serialize(data)}
    if isinstance(data, (list, tuple)):
        payload["count"] = len(data)
    print(
        json.dumps(payload, ensure_ascii=False, indent=2 if text else None, default=str)
    )


def _error_payload(error_type: str, message: str, **details: Any) -> Dict[str, Any]:
    error: Dict[str, Any] = {"type": error_type, "message": message}
    error.update({key: value for key, value in details.items() if value is not None})
    return {"ok": False, "error": error}


def _emit_error(exc: Exception, text: bool, verbose: bool) -> int:
    if isinstance(exc, CLIError):
        payload = _error_payload(exc.error_type, exc.message)
        code = exc.exit_code
    elif isinstance(exc, UnauthorizedException):
        payload = _error_payload(
            "unauthorized",
            exc.message,
            code=exc.error_code,
            status_code=exc.status_code,
        )
        code = 3
    elif isinstance(exc, ForbiddenException):
        payload = _error_payload(
            "forbidden", exc.message, code=exc.error_code, status_code=exc.status_code
        )
        code = 3
    elif isinstance(exc, NotFoundException):
        payload = _error_payload(
            "not_found", exc.message, code=exc.error_code, status_code=exc.status_code
        )
        code = 4
    elif isinstance(exc, ValidationErrorException):
        payload = _error_payload(
            "validation_error",
            exc.message,
            code=exc.error_code,
            status_code=exc.status_code,
            fields=exc.fields,
        )
        code = 2
    elif isinstance(exc, RateLimitedException):
        payload = _error_payload(
            "rate_limited",
            exc.message,
            code=exc.error_code,
            status_code=exc.status_code,
        )
        code = 5
    elif isinstance(exc, MelloAPIException):
        payload = _error_payload(
            "api_error",
            exc.message,
            code=exc.error_code,
            status_code=exc.status_code,
            fields=exc.fields,
        )
        code = 1
    elif isinstance(exc, requests.RequestException):
        payload = _error_payload("network", str(exc))
        code = 1
    else:
        payload = _error_payload("internal_error", str(exc) or type(exc).__name__)
        code = 1
    print(
        json.dumps(payload, ensure_ascii=False, indent=2 if text else None),
        file=sys.stderr,
    )
    if verbose:
        traceback.print_exc(file=sys.stderr)
    return code


# Command handlers deliberately delegate all API logic to MelloClient.
def _cmd_me(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.get_current_user()


def _cmd_workspace_list(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.list_workspaces()


def _cmd_workspace_members(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.list_workspace_members(args.workspace_id)


def _cmd_board_list(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.list_workspace_boards(args.workspace_id)


def _cmd_board_get(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.get_board(args.board_id)


def _cmd_board_create(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.create_board(args.workspace_id, args.name, args.code)


def _cmd_board_update(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.update_board(args.board_id, **_parse_updates(args, "board"))


def _cmd_board_delete(client: MelloClient, args: argparse.Namespace) -> Any:
    _require_confirmation(args, "delete board %s" % args.board_id)
    return client.delete_board(args.board_id)


def _cmd_column_list(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.list_columns(args.board_id)


def _cmd_column_create(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.create_column(args.board_id, args.name, args.position)


def _cmd_column_update(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.update_column(args.column_id, **_parse_updates(args, "column"))


def _cmd_column_reorder(client: MelloClient, args: argparse.Namespace) -> Any:
    column_ids = [column_id for column_id in args.column_ids.split(",") if column_id]
    if not column_ids:
        raise CLIError("--column-ids must contain at least one ID")
    return client.reorder_columns(args.board_id, column_ids)


def _cmd_label_list(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.list_labels(args.board_id)


def _cmd_label_create(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.create_label(args.board_id, args.name, args.color)


def _cmd_label_update(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.update_label(args.label_id, **_parse_updates(args, "label"))


def _cmd_ticket_list(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.list_board_tickets(args.board_id)


def _cmd_ticket_get(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.get_ticket(args.ticket_id)


def _cmd_ticket_create(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.create_ticket(
        args.column_id, args.title, args.description, args.position
    )


def _cmd_ticket_update(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.update_ticket(args.ticket_id, **_parse_updates(args, "ticket"))


def _cmd_ticket_move(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.move_ticket(args.ticket_id, args.column_id, args.position)


def _cmd_ticket_delete(client: MelloClient, args: argparse.Namespace) -> Any:
    _require_confirmation(args, "delete ticket %s" % args.ticket_id)
    return client.delete_ticket(args.ticket_id)


def _cmd_ticket_search(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.search_tickets(args.workspace_id, args.query)


def _cmd_comment_list(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.list_comments(args.ticket_id)


def _cmd_comment_create(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.create_comment(args.ticket_id, args.body, args.body_html)


def _cmd_history_list(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.list_history(args.ticket_id)


def _cmd_checklist_create(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.create_checklist(args.ticket_id, args.title, args.position)


def _cmd_checklist_update(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.update_checklist(
        args.checklist_id, **_parse_updates(args, "checklist")
    )


def _cmd_checklist_delete(client: MelloClient, args: argparse.Namespace) -> Any:
    _require_confirmation(args, "delete checklist %s" % args.checklist_id)
    return client.delete_checklist(args.checklist_id)


def _cmd_checklist_item_create(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.create_checklist_item(args.checklist_id, args.title, args.position)


def _cmd_checklist_item_update(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.update_checklist_item(
        args.checklist_item_id, **_parse_updates(args, "checklist_item")
    )


def _cmd_checklist_item_delete(client: MelloClient, args: argparse.Namespace) -> Any:
    _require_confirmation(args, "delete checklist item %s" % args.checklist_item_id)
    return client.delete_checklist_item(args.checklist_item_id)


def _cmd_attachment_upload(client: MelloClient, args: argparse.Namespace) -> Any:
    try:
        with open(args.file, "rb") as file_handle:
            content = file_handle.read()
    except OSError as exc:
        raise CLIError("Unable to read attachment file: %s" % exc, "file")
    return client.create_attachment(
        args.ticket_id, os.path.basename(args.file), content, args.content_type
    )


def _cmd_attachment_download(client: MelloClient, args: argparse.Namespace) -> Any:
    content = client.download_attachment(args.attachment_id)
    if args.output:
        try:
            with open(args.output, "wb") as file_handle:
                file_handle.write(content)
        except OSError as exc:
            raise CLIError("Unable to write attachment file: %s" % exc, "file")
        return {
            "attachment_id": args.attachment_id,
            "path": args.output,
            "bytes": len(content),
        }
    return {
        "attachment_id": args.attachment_id,
        "content_base64": base64.b64encode(content).decode("ascii"),
    }


def _cmd_webhook_list(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.list_webhooks()


def _cmd_webhook_create(client: MelloClient, args: argparse.Namespace) -> Any:
    _require_confirmation(args, "create webhook for workspace %s" % args.workspace_id)
    return client.create_webhook(
        args.workspace_id,
        args.model_type,
        args.model_id,
        args.callback_url,
        event=args.event or None,
        description=args.description,
    )


def _cmd_webhook_update(client: MelloClient, args: argparse.Namespace) -> Any:
    _require_confirmation(args, "update webhook %s" % args.webhook_id)
    return client.update_webhook(args.webhook_id, **_parse_updates(args, "webhook"))


def _cmd_webhook_delete(client: MelloClient, args: argparse.Namespace) -> Any:
    _require_confirmation(args, "delete webhook %s" % args.webhook_id)
    return client.delete_webhook(args.webhook_id)


def _cmd_webhook_deliveries(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.list_webhook_deliveries(args.webhook_id)


def _cmd_webhook_redeliver(client: MelloClient, args: argparse.Namespace) -> Any:
    _require_confirmation(args, "redeliver webhook delivery %s" % args.delivery_id)
    return client.redeliver_webhook_event(args.webhook_id, args.delivery_id)


def _cmd_github_installations(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.list_github_installations(args.workspace_id)


def _cmd_github_repos(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.list_github_repositories(args.workspace_id)


def _cmd_github_board_repos(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.list_github_board_repositories(args.workspace_id, args.board_id)


def _parse_repositories(value: str) -> List[Dict[str, int]]:
    try:
        data = json.loads(value)
    except ValueError:
        raise CLIError("--repositories must be a JSON array")
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise CLIError("--repositories must be a JSON array of objects")
    for item in data:
        if set(item) != {"installation_id", "github_repo_id"}:
            raise CLIError(
                "Each repository must contain installation_id and github_repo_id"
            )
        if not isinstance(item["installation_id"], int) or not isinstance(
            item["github_repo_id"], int
        ):
            raise CLIError("Repository IDs must be integers")
    return data


def _cmd_github_replace_board_repos(
    client: MelloClient, args: argparse.Namespace
) -> Any:
    _require_confirmation(
        args, "replace GitHub repositories for board %s" % args.board_id
    )
    return client.replace_github_board_repositories(
        args.workspace_id, args.board_id, _parse_repositories(args.repositories)
    )


def _cmd_github_connect_start(client: MelloClient, args: argparse.Namespace) -> Any:
    _require_confirmation(
        args, "start GitHub connection for workspace %s" % args.workspace_id
    )
    return client.start_github_connect(args.workspace_id, args.replace, args.board_id)


def _cmd_github_delete_installation(
    client: MelloClient, args: argparse.Namespace
) -> Any:
    _require_confirmation(args, "delete GitHub installation %s" % args.installation_id)
    return client.delete_github_installation(args.workspace_id, args.installation_id)


def _cmd_github_search(client: MelloClient, args: argparse.Namespace) -> Any:
    return client.search_github_objects(
        args.ticket_id, args.query, args.type, args.page
    )


def _cmd_github_link(client: MelloClient, args: argparse.Namespace) -> Any:
    _require_confirmation(args, "link GitHub object to ticket %s" % args.ticket_id)
    return client.create_github_link(
        args.ticket_id,
        int(args.installation_id),
        int(args.github_repo_id),
        args.kind,
        args.number,
        args.branch_name,
    )


def _cmd_github_unlink(client: MelloClient, args: argparse.Namespace) -> Any:
    _require_confirmation(args, "unlink GitHub object %s" % args.link_id)
    return client.delete_github_link(args.ticket_id, args.link_id)


def main(
    argv: Optional[Sequence[str]] = None,
    client_factory: Optional[ClientFactory] = None,
) -> int:
    """Run the CLI and return its process-compatible exit code."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        client = _client_from_args(args, client_factory)
        result = args.func(client, args)
        _success(result, args.text)
        return 0
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 0
    except Exception as exc:
        text = bool(getattr(locals().get("args", None), "text", False))
        verbose = bool(getattr(locals().get("args", None), "verbose", False))
        return _emit_error(exc, text, verbose)


if __name__ == "__main__":
    sys.exit(main())
