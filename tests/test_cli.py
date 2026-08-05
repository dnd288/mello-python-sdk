import json
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest

from mello.cli import main
from mello.exceptions import NotFoundException


class FakeClient:
    def __init__(self, **kwargs: Any) -> None:
        self.options = kwargs
        self.calls: List[Any] = []

    def _call(self, name: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append((name, args, kwargs))
        return {"method": name, "args": list(args), "kwargs": kwargs}

    def get_current_user(self) -> Dict[str, Any]:
        return self._call("get_current_user", created_at=datetime(2026, 8, 4))

    def list_workspaces(self) -> List[Dict[str, str]]:
        self.calls.append(("list_workspaces", (), {}))
        return [{"id": "workspace-1"}]

    def delete_ticket(self, ticket_id: str) -> None:
        self.calls.append(("delete_ticket", (ticket_id,), {}))

    def list_labels(self, board_id: str) -> List[Dict[str, str]]:
        self.calls.append(("list_labels", (board_id,), {}))
        return [{"id": "label-1", "board_id": board_id}]

    def create_label(
        self, board_id: str, name: str, color: Any = None
    ) -> Dict[str, Any]:
        self.calls.append(("create_label", (board_id, name, color), {}))
        return {
            "method": "create_label",
            "args": [board_id, name, color],
            "kwargs": {},
        }

    def update_label(self, label_id: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("update_label", (label_id,), kwargs))
        return {"method": "update_label", "args": [label_id], "kwargs": kwargs}

    def update_ticket(self, ticket_id: str, **kwargs: Any) -> Dict[str, Any]:
        return self._call("update_ticket", ticket_id, **kwargs)

    def create_attachment(
        self, ticket_id: str, filename: str, content: bytes, content_type: Any
    ) -> Dict[str, Any]:
        return self._call(
            "create_attachment", ticket_id, filename, content, content_type=content_type
        )

    def download_attachment(self, attachment_id: str) -> bytes:
        self.calls.append(("download_attachment", (attachment_id,), {}))
        return b"attachment-data"

    def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        if ticket_id == "missing":
            raise NotFoundException(404, "not_found", "Ticket not found")
        return self._call("get_ticket", ticket_id)


def make_factory(store: Dict[str, FakeClient]) -> Any:
    def factory(**kwargs: Any) -> FakeClient:
        client = FakeClient(**kwargs)
        store["client"] = client
        return client

    return factory


def output(capsys: pytest.CaptureFixture[str]) -> Dict[str, Any]:
    captured = capsys.readouterr()
    assert captured.err == ""
    return json.loads(captured.out)


def test_missing_api_key_emits_structured_config_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("MELLO_API_KEY", raising=False)

    assert main(["me", "get"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    error = json.loads(captured.err)
    assert error["ok"] is False
    assert error["error"]["type"] == "config"
    assert "MELLO_API_KEY" in error["error"]["message"]


def test_token_option_takes_precedence_over_environment(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MELLO_API_KEY", "environment-token")
    clients: Dict[str, FakeClient] = {}

    assert main(["--token", "flag-token", "me", "get"], make_factory(clients)) == 0

    payload = output(capsys)
    assert payload["ok"] is True
    assert payload["data"]["kwargs"]["created_at"] == "2026-08-04T00:00:00"
    assert clients["client"].options["token"] == "flag-token"


def test_list_command_emits_count(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MELLO_API_KEY", "token")

    assert main(["workspace", "list"], make_factory({})) == 0

    payload = output(capsys)
    assert payload == {"ok": True, "data": [{"id": "workspace-1"}], "count": 1}


def test_ticket_update_keeps_omitted_fields_and_clears_nullable_fields(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MELLO_API_KEY", "token")
    clients: Dict[str, FakeClient] = {}

    assert (
        main(
            [
                "ticket",
                "update",
                "--ticket-id",
                "ticket-1",
                "--set",
                "title=New title",
                "--clear",
                "pic_user_id",
                "--set",
                "start_date=2026-08-04T01:02:03Z",
            ],
            make_factory(clients),
        )
        == 0
    )

    payload = output(capsys)
    assert payload["data"]["method"] == "update_ticket"
    _method, args, kwargs = clients["client"].calls[-1]
    assert args == ("ticket-1",)
    assert kwargs == {
        "title": "New title",
        "pic_user_id": None,
        "start_date": datetime(2026, 8, 4, 1, 2, 3, tzinfo=timezone.utc),
    }


def test_unknown_update_field_returns_usage_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MELLO_API_KEY", "token")

    assert (
        main(
            [
                "ticket",
                "update",
                "--ticket-id",
                "ticket-1",
                "--set",
                "assignee_id=user-1",
            ],
            make_factory({}),
        )
        == 2
    )

    error = json.loads(capsys.readouterr().err)
    assert error["error"]["type"] == "usage"
    assert "assignee_id" in error["error"]["message"]


def test_noninteractive_delete_requires_yes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MELLO_API_KEY", "token")
    clients: Dict[str, FakeClient] = {}

    assert (
        main(["ticket", "delete", "--ticket-id", "ticket-1"], make_factory(clients))
        == 2
    )

    error = json.loads(capsys.readouterr().err)
    assert error["error"]["type"] == "confirmation_required"
    assert clients["client"].calls == []


def test_confirmed_delete_calls_client(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MELLO_API_KEY", "token")
    clients: Dict[str, FakeClient] = {}

    assert (
        main(
            ["--yes", "ticket", "delete", "--ticket-id", "ticket-1"],
            make_factory(clients),
        )
        == 0
    )

    assert output(capsys) == {"ok": True, "data": None}
    assert clients["client"].calls == [("delete_ticket", ("ticket-1",), {})]


def test_label_list_and_create(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MELLO_API_KEY", "token")
    clients: Dict[str, FakeClient] = {}

    assert (
        main(["label", "list", "--board-id", "board-1"], make_factory(clients)) == 0
    )
    payload = output(capsys)
    assert payload == {
        "ok": True,
        "data": [{"id": "label-1", "board_id": "board-1"}],
        "count": 1,
    }

    assert (
        main(
            [
                "label",
                "create",
                "--board-id",
                "board-1",
                "--name",
                "Auth",
                "--color",
                "#c8f1df",
            ],
            make_factory(clients),
        )
        == 0
    )
    payload = output(capsys)
    assert payload["ok"] is True
    assert payload["data"]["args"] == ["board-1", "Auth", "#c8f1df"]

def test_label_update(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MELLO_API_KEY", "token")
    clients: Dict[str, FakeClient] = {}

    assert (
        main(
            [
                "label",
                "update",
                "--label-id",
                "label-1",
                "--set",
                "name=Auth 1",
                "--set",
                "color=#ffa500",
            ],
            make_factory(clients),
        )
        == 0
    )
    payload = output(capsys)
    assert payload["data"]["kwargs"] == {"name": "Auth 1", "color": "#ffa500"}

def test_label_update_rejects_unknown_field(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MELLO_API_KEY", "token")

    assert (
        main(
            [
                "label",
                "update",
                "--label-id",
                "label-1",
                "--set",
                "position=1",
            ],
            make_factory({}),
        )
        == 2
    )

    error = json.loads(capsys.readouterr().err)
    assert error["error"]["type"] == "usage"
    assert "position" in error["error"]["message"]

def test_attachment_upload_and_download(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Any,
) -> None:
    monkeypatch.setenv("MELLO_API_KEY", "token")
    source = tmp_path / "report.txt"
    source.write_bytes(b"hello")
    clients: Dict[str, FakeClient] = {}

    assert (
        main(
            ["attachment", "upload", "--ticket-id", "ticket-1", "--file", str(source)],
            make_factory(clients),
        )
        == 0
    )
    output(capsys)
    _method, args, kwargs = clients["client"].calls[-1]
    assert args == ("ticket-1", "report.txt", b"hello")
    assert kwargs == {"content_type": None}

    destination = tmp_path / "download.txt"
    assert (
        main(
            [
                "attachment",
                "download",
                "--attachment-id",
                "att-1",
                "--output",
                str(destination),
            ],
            make_factory({}),
        )
        == 0
    )
    assert destination.read_bytes() == b"attachment-data"
    assert output(capsys)["data"]["bytes"] == len(b"attachment-data")


def test_not_found_exception_uses_stable_error_type(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MELLO_API_KEY", "token")

    assert main(["ticket", "get", "--ticket-id", "missing"], make_factory({})) == 4

    error = json.loads(capsys.readouterr().err)
    assert error["error"] == {
        "type": "not_found",
        "message": "Ticket not found",
        "code": "not_found",
        "status_code": 404,
    }
