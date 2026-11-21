"""add_item and update_item are Vee's writes into Progress Memory."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
from dotenv import load_dotenv
from pydantic import ValidationError
from sqlalchemy import select

load_dotenv()

from constants import ITEM_ID_RE
from memory.db import db_session
from memory.models import Item, ItemHistory
from memory.operations.ingress import ingress_turn
from memory.types import Turn
from tools.add_item import AddItemArgs, AddItemCall
from tools.add_item import run as run_add_item
from tools.execute import execute_plan
from tools.search_items import SearchItemsArgs, SearchItemsCall
from tools.update_item import UpdateItemArgs, UpdateItemCall
from tools.update_item import run as run_update_item

pytestmark = pytest.mark.skipif(
    not (os.getenv("DATABASE_URL") or "").strip(),
    reason="DATABASE_URL is required for Progress Memory write tests",
)

START = datetime(2026, 11, 6, 19, 0, tzinfo=timezone.utc)
END = datetime(2026, 11, 6, 20, 0, tzinfo=timezone.utc)
DUE = datetime(2026, 11, 7, 23, 59, 59, tzinfo=timezone.utc)

ITEM_FIELDS = (
    "id",
    "user_id",
    "type",
    "title",
    "description",
    "parent_id",
    "start_at",
    "end_at",
    "due_at",
    "status",
    "work_mode",
    "flags",
    "carried_since",
    "created_at",
    "updated_at",
)
UNSET = {
    "parent_id": None,
    "start_at": None,
    "end_at": None,
    "due_at": None,
    "status": "todo",
    "work_mode": None,
    "description": None,
    "flags": [],
    "carried_since": None,
}


def founder(prefix: str = "m5") -> Turn:
    return ingress_turn(
        platform="telegram",
        platform_user_id=f"{prefix}_{uuid.uuid4().hex[:12]}",
        role="user",
        text="record this",
    )


def add_call(**payload) -> AddItemCall:
    return AddItemCall(name="add_item", args=AddItemArgs.model_validate(payload))


def update_call(payload: dict) -> UpdateItemCall:
    return UpdateItemCall(name="update_item", args=UpdateItemArgs.model_validate(payload))


def write_add(turn: Turn, **payload) -> str:
    with db_session() as db:
        item_id, _changes = run_add_item(
            db,
            AddItemArgs.model_validate(payload),
            user_id=turn.user_id,
            message_id=turn.message_id,
        )
    return item_id


def write_update(turn: Turn, payload: dict) -> str:
    args = UpdateItemArgs.model_validate(payload)
    with db_session() as db:
        item_id, _changes = run_update_item(
            db, args, user_id=turn.user_id, message_id=turn.message_id
        )
    return item_id


def load(item_id: str) -> tuple[dict, list[dict]]:
    with db_session() as db:
        item = db.get(Item, item_id)
        assert item is not None
        columns = {name: getattr(item, name) for name in ITEM_FIELDS}
        rows = db.scalars(
            select(ItemHistory)
            .where(ItemHistory.item_id == item_id)
            .order_by(ItemHistory.created_at, ItemHistory.id)
        ).all()
        history = [
            {
                "id": row.id,
                "item_id": row.item_id,
                "message_id": row.message_id,
                "kind": str(row.kind),
                "source": str(row.source),
                "changes": row.changes,
            }
            for row in rows
        ]
    return columns, history


def count_items(user_id: str) -> int:
    with db_session() as db:
        return len(db.scalars(select(Item.id).where(Item.user_id == user_id)).all())


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def same(actual, expected) -> bool:
    if isinstance(expected, datetime):
        return isinstance(actual, datetime) and as_utc(actual) == as_utc(expected)
    return actual == expected


def format_value(value) -> str:
    if isinstance(value, datetime):
        return as_utc(value).strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, str) and value.endswith("+00:00") and "T" in value:
        return value.replace("T", " ").removesuffix("+00:00")
    if value is None:
        return "null"
    if isinstance(value, dict):
        return ", ".join(f"{key}={format_value(item)}" for key, item in value.items())
    return str(value)


def show_heading(heading: str) -> None:
    rule = "─" * len(heading)
    print(f"\n\033[1m{heading}\033[0m\n{rule}")


def show(heading: str, *lines: str) -> None:
    show_heading(heading)
    for line in lines:
        print(f"  {line}")


def history_with(history: list[dict], changes: dict) -> dict:
    matches = [row for row in history if row["changes"] == changes]
    assert len(matches) == 1, history
    return matches[0]


def assert_history(row: dict, *, item_id: str, message_id: str, kind: str, changes: dict) -> None:
    assert row["id"].startswith("hst_")
    assert len(row["id"]) == 20
    assert row["item_id"] == item_id
    assert row["message_id"] == message_id
    assert row["kind"] == kind
    assert row["source"] == "assistant_inference"
    assert row["changes"] == changes


def assert_defaults(item: dict, turn: Turn, sent: set[str]) -> None:
    assert ITEM_ID_RE.match(item["id"])
    assert item["user_id"] == turn.user_id
    assert item["created_at"] is not None
    assert item["updated_at"] is not None
    for name, default in UNSET.items():
        if name in sent:
            continue
        assert item[name] == default, name


def test_add_task_writes_only_sent_columns_and_history() -> None:
    turn = founder()
    item_id = write_add(turn, title="Hit the gym", type="task")
    item, history = load(item_id)
    show(
        "add task — title and type only",
        f"item     {item_id}",
        f"title    {item['title']}",
        f"type     {item['type']}",
        f"status   {item['status']}",
        f"history  {history[0]['kind']}  {format_value(history[0]['changes'])}",
    )

    assert item["title"] == "Hit the gym"
    assert item["type"] == "task"
    assert_defaults(item, turn, {"status"})
    assert len(history) == 1
    assert_history(
        history[0],
        item_id=item_id,
        message_id=turn.message_id,
        kind="created",
        changes={"title": "Hit the gym", "type": "task", "status": "todo"},
    )


def test_add_event_without_start_stores_null_start() -> None:
    turn = founder()
    item_id = write_add(turn, title="Family meeting", type="event")
    item, history = load(item_id)
    show(
        "add event — no start_at",
        f"item      {item_id}",
        f"type      {item['type']}",
        f"start_at  {format_value(item['start_at'])}",
        f"history   {history[0]['kind']}  {format_value(history[0]['changes'])}",
    )

    assert item["type"] == "event"
    assert item["start_at"] is None
    assert_defaults(item, turn, set())
    assert history[0]["changes"]["type"] == "event"
    assert "start_at" not in history[0]["changes"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("start_at", START),
        ("end_at", END),
        ("due_at", DUE),
        ("status", "in_progress"),
        ("work_mode", "building"),
    ],
)
def test_add_sets_one_optional_column(field: str, value) -> None:
    turn = founder()
    item_id = write_add(turn, title="One column", type="task", **{field: value})
    item, history = load(item_id)
    show(
        f"add task — only {field}",
        f"item     {item_id}",
        f"{field:<10} {format_value(item[field])}",
        f"history  {history[0]['kind']}  {format_value(history[0]['changes'])}",
    )

    assert same(item[field], value)
    assert_defaults(item, turn, {field, "status"} if field != "status" else {"status"})
    expected = {"title": "One column", "type": "task", "status": item["status"]}
    if field != "status":
        expected[field] = value.isoformat() if isinstance(value, datetime) else value
    assert history[0]["changes"] == expected
    assert history[0]["message_id"] == turn.message_id
    assert history[0]["kind"] == "created"


def test_add_parent_must_belong_to_the_same_user() -> None:
    owner = founder("parent")
    other = founder("other")
    parent_id = write_add(owner, title="Landing page", type="task")

    child_id = write_add(owner, title="Hero copy", type="task", parent_id=parent_id)
    child, history = load(child_id)
    assert child["parent_id"] == parent_id
    assert history[0]["changes"]["parent_id"] == parent_id
    assert_defaults(child, owner, {"parent_id", "status"})

    before = count_items(other.user_id)
    with pytest.raises(Exception, match="parent"):
        write_add(other, title="Not mine", type="task", parent_id=parent_id)
    show(
        "add child under the owner's parent",
        f"child     {child_id}",
        f"parent    {parent_id}",
        "other user rejected — their items stay unchanged",
    )
    assert count_items(other.user_id) == before
    assert load(parent_id)[0]["title"] == "Landing page"


def test_update_changes_one_column_and_leaves_the_rest() -> None:
    turn = founder()
    parent_id = write_add(turn, title="Parent", type="task")
    item_id = write_add(
        turn,
        title="Original",
        type="task",
        parent_id=parent_id,
        start_at=START,
        end_at=END,
        due_at=DUE,
        status="todo",
        work_mode="personal",
    )
    before, _history = load(item_id)
    new_parent = write_add(turn, title="Other parent", type="task")
    cases = [
        ("title", "Renamed", "updated"),
        ("type", "event", "updated"),
        ("parent_id", new_parent, "updated"),
        ("start_at", datetime(2026, 11, 8, 15, 0, tzinfo=timezone.utc), "updated"),
        ("end_at", datetime(2026, 11, 8, 16, 0, tzinfo=timezone.utc), "updated"),
        ("due_at", datetime(2026, 11, 9, 23, 59, 59, tzinfo=timezone.utc), "updated"),
        ("status", "completed", "completed"),
        ("work_mode", "marketing", "updated"),
    ]
    show_heading(f"update one column at a time — {item_id}")
    for field, value, kind in cases:
        current, _history = load(item_id)
        write_update(turn, {"id": item_id, field: value})
        item, history = load(item_id)
        print(f"  {field:<10} {format_value(item[field]):<22} kind {kind}")
        assert same(item[field], value)
        for name in ITEM_FIELDS:
            if name in {field, "updated_at"}:
                continue
            assert item[name] == current[name], name
        stored = value.isoformat() if isinstance(value, datetime) else value
        assert_history(
            history_with(history, {field: stored}),
            item_id=item_id,
            message_id=turn.message_id,
            kind=kind,
            changes={field: stored},
        )
    assert load(item_id)[0]["user_id"] == before["user_id"]
    assert load(item_id)[0]["description"] is None
    assert load(item_id)[0]["flags"] == []
    assert load(item_id)[0]["carried_since"] is None
    assert load(item_id)[0]["created_at"] == before["created_at"]


@pytest.mark.parametrize("status", ["cancelled", "dropped", "blocked"])
def test_update_status_chooses_history_kind(status: str) -> None:
    turn = founder()
    item_id = write_add(turn, title="Gym", type="task")
    write_update(turn, {"id": item_id, "status": status})
    item, history = load(item_id)
    assert item["status"] == status
    assert item["title"] == "Gym"
    kind = status if status in {"cancelled", "dropped"} else "updated"
    row = history_with(history, {"status": status})
    show(
        f"update status → {status}",
        f"item     {item_id}",
        f"status   {item['status']}",
        f"history  {row['kind']}",
    )
    assert row["kind"] == kind
    assert row["message_id"] == turn.message_id


@pytest.mark.parametrize("field", ["parent_id", "start_at", "end_at", "due_at", "work_mode"])
def test_update_null_clears_and_omit_keeps(field: str) -> None:
    turn = founder()
    parent_id = write_add(turn, title="Parent", type="task")
    item_id = write_add(
        turn,
        title="Scheduled",
        type="event",
        parent_id=parent_id,
        start_at=START,
        end_at=END,
        due_at=DUE,
        work_mode="research",
    )
    write_update(turn, {"id": item_id, field: None})
    cleared, history = load(item_id)
    assert cleared[field] is None
    cleared_row = history_with(history, {field: None})
    assert cleared_row["kind"] == "updated"
    assert cleared_row["message_id"] == turn.message_id

    write_update(turn, {"id": item_id, "title": "Still scheduled"})
    kept, history = load(item_id)
    assert kept["title"] == "Still scheduled"
    assert kept[field] is None
    assert history_with(history, {"title": "Still scheduled"})["kind"] == "updated"
    restored = {
        "parent_id": parent_id,
        "start_at": START,
        "end_at": END,
        "due_at": DUE,
        "work_mode": "research",
    }[field]
    write_update(turn, {"id": item_id, field: restored})
    filled, _history = load(item_id)
    assert same(filled[field], restored)

    snapshot, _history = load(item_id)
    write_update(turn, {"id": item_id, "title": "Untouched deadline"})
    after, history = load(item_id)
    assert same(after[field], snapshot[field])
    untouched = history_with(history, {"title": "Untouched deadline"})
    assert field not in untouched["changes"]
    show(
        f"clear {field}, then leave it out",
        f"after null      {format_value(cleared[field])}",
        f"title only      {field} stays {format_value(kept[field])}",
        f"restored        {format_value(filled[field])}",
        f"omitted again   {field} stays {format_value(after[field])}",
    )


@pytest.mark.parametrize("field", ["title", "type", "status"])
def test_null_required_field_is_rejected_before_a_write(field: str) -> None:
    turn = founder()
    item_id = write_add(turn, title="Stay", type="task", status="todo")
    before, before_history = load(item_id)
    with pytest.raises(ValidationError):
        UpdateItemArgs.model_validate({"id": item_id, field: None})
    after, after_history = load(item_id)
    show(f"reject null {field}", "rejected before a write — row unchanged")
    assert after == before
    assert after_history == before_history


def test_empty_title_is_rejected() -> None:
    show("reject blank title", "add_item never runs")
    with pytest.raises(ValidationError):
        AddItemArgs.model_validate({"title": "   ", "type": "task"})


def test_unknown_id_other_user_and_self_parent_do_not_write() -> None:
    owner = founder("owner")
    stranger = founder("stranger")
    item_id = write_add(owner, title="Mine", type="task", due_at=DUE)
    before, before_history = load(item_id)

    missing = update_call({"id": "itm_" + "ab" * 8, "title": "Nope"})
    failed = execute_plan(
        [missing], user_id=owner.user_id, message_id=owner.message_id
    )
    assert failed[0].ok is False
    assert load(item_id) == (before, before_history)

    stolen = execute_plan(
        [update_call({"id": item_id, "title": "Stolen"})],
        user_id=stranger.user_id,
        message_id=stranger.message_id,
    )
    assert stolen[0].ok is False
    assert load(item_id)[0]["title"] == "Mine"
    assert count_items(stranger.user_id) == 0

    with pytest.raises(Exception, match="own parent"):
        write_update(owner, {"id": item_id, "parent_id": item_id})
    assert load(item_id)[0]["parent_id"] is None
    show(
        "reject unknown id, another user, and self-parent",
        f"unknown id    {failed[0].error}",
        f"other user    {stolen[0].error}",
        "self parent   rejected — parent stays null",
    )


def test_failed_plan_rolls_back_earlier_calls() -> None:
    turn = founder()
    calls = [
        add_call(title="Should roll back", type="task"),
        update_call({"id": "itm_" + "cd" * 8, "status": "completed"}),
    ]
    results = execute_plan(calls, user_id=turn.user_id, message_id=turn.message_id)
    assert [row.ok for row in results] == [False, False]
    show(
        "plan rolls back — add, then a missing item",
        *[f"{row.name:<12} {row.error}" for row in results],
    )
    assert results[0].error == "rolled back"
    assert "not found" in (results[1].error or "")
    assert count_items(turn.user_id) == 0


def test_empty_plan_writes_nothing() -> None:
    turn = founder()
    assert execute_plan([], user_id=turn.user_id, message_id=turn.message_id) == []
    assert count_items(turn.user_id) == 0
    show("empty plan", "wrote nothing")


def test_search_items_is_not_executed_and_rolls_back() -> None:
    turn = founder()
    results = execute_plan(
        [
            add_call(title="Do not keep", type="task"),
            SearchItemsCall(name="search_items", args=SearchItemsArgs()),
        ],
        user_id=turn.user_id,
        message_id=turn.message_id,
    )
    show(
        "plan rolls back — add, then search_items",
        *[f"{row.name:<12} {row.error}" for row in results],
    )
    assert results[0].error == "rolled back"
    assert "search_items" in (results[1].error or "")
    assert count_items(turn.user_id) == 0
