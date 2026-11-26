"""Resolve platform identity → User + UserChannel."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from memory.db import new_id
from memory.models import User, UserChannel
from settings import DEFAULT_TIMEZONE


def find_user_id(db: Session, *, platform: str, platform_user_id: str) -> Optional[str]:
    """User id behind a platform identity, or None. Never creates rows."""
    return db.scalar(
        select(UserChannel.user_id).where(
            UserChannel.platform == platform,
            UserChannel.platform_user_id == platform_user_id,
        )
    )


def get_or_create_user(
    db: Session,
    *,
    platform: str,
    platform_user_id: str,
) -> tuple[User, UserChannel]:
    """Map (platform, platform_user_id) to User; create both rows on first contact."""
    channel = db.scalar(
        select(UserChannel).where(
            UserChannel.platform == platform,
            UserChannel.platform_user_id == platform_user_id,
        )
    )
    if channel is not None:
        user = db.get(User, channel.user_id)
        if user is None:
            raise RuntimeError(f"user missing for channel {channel.id}")
        return user, channel

    user = User(id=new_id("usr"), timezone=DEFAULT_TIMEZONE)
    channel = UserChannel(
        id=new_id("chn"),
        user_id=user.id,
        platform=platform,
        platform_user_id=platform_user_id,
        is_primary=True,
    )
    db.add(user)
    db.add(channel)
    db.flush()
    return user, channel
