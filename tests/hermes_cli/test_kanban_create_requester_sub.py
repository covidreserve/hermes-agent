"""`hermes kanban create` run from a gateway session subscribes that session's requester."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from hermes_cli import kanban as kc
from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_connect as kbc
from hermes_cli import kanban_db_notify as kbn


@pytest.fixture
def kanban_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    for k in ("HERMES_SESSION_KEY", "HERMES_KANBAN_TASK", "HERMES_SESSION_THREAD_ID"):
        monkeypatch.delenv(k, raising=False)
    kb.init_db()
    return home


def _create_and_subs():
    root = argparse.ArgumentParser(prog="hermes")
    kc.build_parser(root.add_subparsers())
    assert kc._cmd_create(root.parse_args(["kanban", "create", "t"])) == 0
    with kbc.connect_closing() as conn:
        tid = conn.execute("select id from tasks order by created_at desc limit 1").fetchone()[0]
        return kbn.list_notify_subs(conn, tid)


def test_gateway_session_create_subscribes_requester(kanban_home, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_PLATFORM", "slack")
    monkeypatch.setenv("HERMES_SESSION_CHAT_ID", "D123")
    monkeypatch.setenv("HERMES_SESSION_USER_ID", "U456")
    subs = _create_and_subs()
    assert [(s["platform"], s["chat_id"], s["user_id"]) for s in subs] == [("slack", "D123", "U456")]


def test_plain_cli_create_has_no_subscription(kanban_home, monkeypatch):
    monkeypatch.delenv("HERMES_SESSION_PLATFORM", raising=False)
    monkeypatch.delenv("HERMES_SESSION_CHAT_ID", raising=False)
    assert _create_and_subs() == []
