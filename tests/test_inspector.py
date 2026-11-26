"""Inspector V0 shows one founder's recorded items, their history, and source messages."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.testclient import TestClient

load_dotenv()

from api.inspector.routes import router
from memory.db import db_session
from memory.operations.ingress import ingress_turn
from memory.types import Turn
from tools.add_item import AddItemArgs
from tools.add_item import run as run_add_item
from tools.update_item import UpdateItemArgs
from tools.update_item import run as run_update_item

TOKEN = "inspector-test-token"
DUE = datetime(2026, 11, 7, 23, 59, 59, tzinfo=timezone.utc)

needs_db = pytest.mark.skipif(
    not (os.getenv("DATABASE_URL") or "").strip(),
    reason="DATABASE_URL is required for Inspector reads",
)


def open_founder(text: str = "record this") -> Turn:
    return ingress_turn(
        platform="telegram",
        platform_user_id=f"insp_{uuid.uuid4().hex[:12]}",
        role="user",
        text=text,
    )


def write_add(turn: Turn, **payload) -> str:
    with db_session() as db:
        item_id, _ = run_add_item(
            db, AddItemArgs.model_validate(payload), user_id=turn.user_id, message_id=turn.message_id
        )
    return item_id


def write_update(turn: Turn, payload: dict) -> None:
    with db_session() as db:
        run_update_item(
            db, UpdateItemArgs.model_validate(payload), user_id=turn.user_id, message_id=turn.message_id
        )


def show(heading: str, *lines: str) -> None:
    print(f"\n\033[1m{heading}\033[0m\n{'─' * len(heading)}")
    for line in lines:
        print(f"  {line}")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("INSPECTOR_TOKEN", TOKEN)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_page_is_served(client: TestClient) -> None:
    response = client.get("/inspector")
    show("page", f"status {response.status_code}", response.headers["content-type"])
    assert response.status_code == 200
    assert "My Company" in response.text


def test_items_need_the_token(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INSPECTOR_TELEGRAM_ID", "unused")
    missing = client.get("/inspector/api/items")
    wrong = client.get("/inspector/api/items", headers={"X-Inspector-Token": "nope"})
    monkeypatch.delenv("INSPECTOR_TOKEN")
    unset = client.get("/inspector/api/items", headers={"X-Inspector-Token": TOKEN})
    show(
        "token guard",
        f"no token      {missing.status_code}",
        f"wrong token   {wrong.status_code}",
        f"token unset   {unset.status_code}",
    )
    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert unset.status_code == 503


@needs_db
def test_unknown_founder_has_no_items(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INSPECTOR_TELEGRAM_ID", f"nobody_{uuid.uuid4().hex[:12]}")
    response = client.get("/inspector/api/items", headers={"X-Inspector-Token": TOKEN})
    show("unknown founder", f"items {response.json()['items']}")
    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None, "total": 0}


@needs_db
def test_list_shows_only_the_founders_items_newest_first(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    founder = open_founder()
    stranger = open_founder()
    first = write_add(founder, title="Chase Acme", type="task", due_at=DUE)
    second = write_add(founder, title="Family meeting", type="event")
    write_add(stranger, title="Not yours", type="task")
    monkeypatch.setenv("INSPECTOR_TELEGRAM_ID", founder.platform_user_id)

    items = client.get("/inspector/api/items", headers={"X-Inspector-Token": TOKEN}).json()["items"]
    show("recorded items", *[f"{row['type']:<6} {row['status']:<6} {row['title']}" for row in items])
    assert {row["id"] for row in items} == {first, second}
    assert "Not yours" not in {row["title"] for row in items}
    assert [row["created_at"] for row in items] == sorted(
        (row["created_at"] for row in items), reverse=True
    )


@needs_db
def test_list_pages_through_every_item_once(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    founder = open_founder()
    written = [write_add(founder, title=f"Task {n}", type="task") for n in range(5)]
    monkeypatch.setenv("INSPECTOR_TELEGRAM_ID", founder.platform_user_id)

    seen, pages, cursor = [], [], None
    while True:
        params = {"limit": 2, **({"cursor": cursor} if cursor else {})}
        body = client.get("/inspector/api/items", params=params, headers={"X-Inspector-Token": TOKEN}).json()
        pages.append([row["title"] for row in body["items"]])
        seen.extend(row["id"] for row in body["items"])
        assert body["total"] == 5
        cursor = body["next_cursor"]
        if cursor is None:
            break
    show("pages of 2", *[f"page {n + 1}  {titles}" for n, titles in enumerate(pages)])
    assert [len(page) for page in pages] == [2, 2, 1]
    assert sorted(seen) == sorted(written)


def test_a_bad_cursor_is_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INSPECTOR_TELEGRAM_ID", "unused")
    response = client.get(
        "/inspector/api/items", params={"cursor": "garbage"}, headers={"X-Inspector-Token": TOKEN}
    )
    show("bad cursor", f"status {response.status_code}")
    assert response.status_code == 400


@needs_db
def test_details_show_fields_history_and_source_messages(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    founder = open_founder("move the Acme chase to tomorrow")
    item_id = write_add(founder, title="Chase Acme", type="task")
    later = ingress_turn(
        platform="telegram",
        platform_user_id=founder.platform_user_id,
        role="user",
        text="the Acme chase is done",
    )
    write_update(later, {"id": item_id, "status": "completed", "due_at": DUE})
    monkeypatch.setenv("INSPECTOR_TELEGRAM_ID", founder.platform_user_id)

    body = client.get(f"/inspector/api/items/{item_id}", headers={"X-Inspector-Token": TOKEN}).json()
    show(
        "item details",
        f"title     {body['item']['title']}",
        f"status    {body['item']['status']}",
        *[f"history   {row['kind']:<10} {row['changes']}" for row in body["history"]],
        *[f"message   {row['text']}" for row in body["messages"]],
    )
    assert body["item"]["status"] == "completed"
    assert body["item"]["due_at"].startswith("2026-11-07")
    assert [row["kind"] for row in body["history"]] == ["created", "completed"]
    assert [row["text"] for row in body["messages"]] == [
        "move the Acme chase to tomorrow",
        "the Acme chase is done",
    ]


@needs_db
def test_another_users_item_is_not_found(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    founder = open_founder()
    stranger = open_founder()
    foreign = write_add(stranger, title="Not yours", type="task")
    monkeypatch.setenv("INSPECTOR_TELEGRAM_ID", founder.platform_user_id)

    response = client.get(f"/inspector/api/items/{foreign}", headers={"X-Inspector-Token": TOKEN})
    show("foreign item", f"status {response.status_code}", response.json()["detail"])
    assert response.status_code == 404
