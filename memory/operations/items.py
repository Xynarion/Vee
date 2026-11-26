"""Item reads for interaction state (writes land in M5)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from constants import ACTIVE_STATUSES
from memory.models import Item, ItemHistory


def list_recorded_items(
    db: Session,
    user_id: str,
    *,
    limit: int,
    before: Optional[Tuple[datetime, str]] = None,
) -> list[Item]:
    """One page of this user's items, newest first. `before` is the last (created_at, id) seen."""
    query = select(Item).where(Item.user_id == user_id)
    if before is not None:
        created_at, item_id = before
        query = query.where(
            or_(
                Item.created_at < created_at,
                and_(Item.created_at == created_at, Item.id < item_id),
            )
        )
    rows = db.scalars(
        query.order_by(Item.created_at.desc(), Item.id.desc()).limit(limit)
    ).all()
    return list(rows)


def count_recorded_items(db: Session, user_id: str) -> int:
    return db.scalar(select(func.count()).select_from(Item).where(Item.user_id == user_id)) or 0


def find_owned_item(db: Session, user_id: str, item_id: str) -> Optional[Item]:
    """The item when this user owns it; None for a missing or foreign id."""
    return db.scalar(select(Item).where(Item.id == item_id, Item.user_id == user_id))


def list_item_history(db: Session, item_id: str) -> list[ItemHistory]:
    """History rows for one item, oldest first."""
    rows = db.scalars(
        select(ItemHistory)
        .where(ItemHistory.item_id == item_id)
        .order_by(ItemHistory.created_at, ItemHistory.id)
    ).all()
    return list(rows)


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
