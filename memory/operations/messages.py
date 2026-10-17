"""Message persistence — low-level row writes and reads."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from memory.db import new_id
from memory.models import Message
from memory.operations.constants import STATE_HISTORY_WINDOW


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


def recent_messages(db: Session, user_id: str, *, limit: int = STATE_HISTORY_WINDOW) -> list[Message]:
    rows = db.scalars(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    ).all()
    return list(reversed(rows))
