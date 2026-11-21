"""Item reads for interaction state (writes land in M5)."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from constants import ACTIVE_STATUSES
from memory.models import Item


def load_testimony_items(db: Session, user_id: str, item_ids: Sequence[str]) -> list[Item]:
    """Items this user owns among the testimony ids. Order is applied by the reply."""
    if not item_ids:
        return []
    rows = db.scalars(
        select(Item).where(Item.user_id == user_id, Item.id.in_(tuple(item_ids)))
    ).all()
    return list(rows)


def list_current_items(db: Session, user_id: str) -> list[Item]:
    """Active progress items for a user (todo / in_progress), newest first."""
    rows = db.scalars(
        select(Item)
        .where(Item.user_id == user_id, Item.status.in_(tuple(ACTIVE_STATUSES)))
        .order_by(Item.updated_at.desc())
    ).all()
    return list(rows)


def list_progress_items(db: Session, user_id: str) -> list[Item]:
    """All Progress Memory items for a user, oldest first, with history loaded."""
    rows = db.scalars(
        select(Item)
        .where(Item.user_id == user_id)
        .options(selectinload(Item.history))
        .order_by(Item.created_at.asc())
    ).all()
    return list(rows)
