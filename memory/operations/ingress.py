"""Ingress — resolve user and persist a conversation turn (user or assistant)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from memory.db import db_session
from memory.operations.messages import create_message
from memory.operations.users import get_or_create_user
from memory.types import Turn


def _ingress_turn(
    db: Session,
    *,
    platform: str,
    platform_user_id: str,
    role: str,
    text: str,
) -> Turn:
    user, channel = get_or_create_user(
        db,
        platform=platform,
        platform_user_id=platform_user_id,
    )
    message = create_message(
        db,
        user_id=user.id,
        user_channel_id=channel.id,
        role=role,
        text=text,
    )
    return Turn(
        user_id=user.id,
        channel_id=channel.id,
        message_id=message.id,
        platform=platform,
        platform_user_id=platform_user_id,
        role=role,
        text=text,
    )


def ingress_turn(
    *,
    platform: str,
    platform_user_id: str,
    role: str,
    text: str,
) -> Turn:
    """
    Resolve user, persist message, return Turn.

    Used by perceive (role=user) and later testify (role=assistant).
    Does not build state.
    """
    with db_session() as db:
        return _ingress_turn(
            db,
            platform=platform,
            platform_user_id=platform_user_id,
            role=role,
            text=text,
        )
