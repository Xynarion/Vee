"""Item reads for interaction state (writes land in M5)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from memory.models import Item
from constants import ACTIVE_STATUSES


def list_current_items(db: Session, user_id: str) -> list[Item]:
    """Active progress items for a user (todo / in_progress), newest first."""
    rows = db.scalars(
        select(Item)
        .where(Item.user_id == user_id, Item.status.in_(tuple(ACTIVE_STATUSES)))
        .order_by(Item.updated_at.desc())
    ).all()
    return list(rows)
