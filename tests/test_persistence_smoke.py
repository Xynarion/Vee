"""M1 persistence smoke — schema + ingress round-trip against Postgres."""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import inspect, text

from memory.db import db_session, get_engine
from memory.models import Item, ItemHistory, Message, User, UserChannel
from memory.operations.ingress import ingress_turn
from memory.operations.messages import recent_messages


pytestmark = pytest.mark.skipif(
    not (os.getenv("DATABASE_URL") or "").strip(),
    reason="DATABASE_URL is required for Postgres persistence smoke tests",
)


EXPECTED_TABLES = {
    "users",
    "user_channels",
    "messages",
    "items",
    "items_history",
    "alembic_version",
}


def test_schema_tables_exist() -> None:
    inspector = inspect(get_engine())
    tables = set(inspector.get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"missing tables after migrate: {sorted(missing)}"


def test_ingress_round_trip() -> None:
    chat_id = f"smoke_{uuid.uuid4().hex[:12]}"
    text = "Finished the landing page."

    turn = ingress_turn(
        platform="telegram",
        platform_user_id=chat_id,
        role="user",
        text=text,
    )

    assert turn.platform == "telegram"
    assert turn.platform_user_id == chat_id
    assert turn.role == "user"
    assert turn.text == text
    assert turn.user_id.startswith("usr_")
    assert turn.channel_id.startswith("chn_")
    assert turn.message_id.startswith("msg_")

    with db_session() as db:
        user = db.get(User, turn.user_id)
        channel = db.get(UserChannel, turn.channel_id)
        message = db.get(Message, turn.message_id)

        assert user is not None
        assert channel is not None
        assert message is not None
        assert channel.user_id == user.id
        assert channel.platform == "telegram"
        assert channel.platform_user_id == chat_id
        assert message.user_id == user.id
        assert message.user_channel_id == channel.id
        assert message.role == "user"
        assert message.text == text

        recent = recent_messages(db, user.id, limit=5)
        assert any(m.id == message.id for m in recent)


def test_item_and_history_write() -> None:
    """Items + history are writable (M1 schema; full maintain path is M5)."""
    chat_id = f"smoke_item_{uuid.uuid4().hex[:12]}"
    turn = ingress_turn(
        platform="telegram",
        platform_user_id=chat_id,
        role="user",
        text="Still need to pay the server invoice.",
    )

    with db_session() as db:
        item = Item(
            id=f"itm_{uuid.uuid4().hex[:16]}",
            user_id=turn.user_id,
            type="task",
            title="Pay server invoice",
            status="todo",
            flags=[],
        )
        history = ItemHistory(
            id=f"hst_{uuid.uuid4().hex[:16]}",
            item_id=item.id,
            message_id=turn.message_id,
            kind="created",
            source="user_message",
            changes=None,
        )
        db.add(item)
        db.flush()
        db.add(history)
        db.flush()

        loaded = db.get(Item, item.id)
        hist = db.get(ItemHistory, history.id)
        assert loaded is not None
        assert loaded.title == "Pay server invoice"
        assert hist is not None
        assert hist.kind == "created"
        assert hist.message_id == turn.message_id


def test_alembic_version_is_head() -> None:
    with get_engine().connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    assert row is not None
    assert row[0] == "20261017_0001"
