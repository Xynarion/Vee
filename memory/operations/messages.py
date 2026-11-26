"""Message persistence — low-level row writes and reads."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from memory.db import new_id
from memory.models import Message
from settings import STATE_HISTORY_WINDOW


def create_message(
    db: Session,
    *,
    user_id: str,
    user_channel_id: str,
    role: str,
    text: str,
) -> Message:
    """Insert one message row. Caller supplies identity + role + text."""
    message = Message(
        id=new_id("msg"),
        user_id=user_id,
        user_channel_id=user_channel_id,
        role=role,
        text=text,
    )
    db.add(message)
    db.flush()
    return message


def load_messages(db: Session, user_id: str, message_ids: Sequence[str]) -> list[Message]:
    """This user's messages among the ids, oldest first."""
    if not message_ids:
        return []
    rows = db.scalars(
        select(Message)
        .where(Message.user_id == user_id, Message.id.in_(tuple(message_ids)))
        .order_by(Message.created_at, Message.id)
    ).all()
    return list(rows)


def list_recent_messages(
    db: Session,
    user_id: str,
    *,
    limit: int = STATE_HISTORY_WINDOW,
) -> list[Message]:
    """Return the latest messages for a user, oldest-first within the window."""
    rows = db.scalars(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    ).all()
    return list(reversed(rows))
