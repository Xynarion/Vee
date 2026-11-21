"""Shared write helpers. The model never sends history or a message id."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from memory.db import new_id
from memory.models import Item, ItemHistory


class ToolWriteError(Exception):
    """This call cannot be written. The plan rolls back."""


def serialize_changes(changes: dict) -> dict:
    """JSON-safe copy of the fields the code applied."""
    stored: dict[str, Any] = {}
    for key, value in changes.items():
        if isinstance(value, datetime):
            stored[key] = value.isoformat()
        else:
            stored[key] = value
    return stored


def choose_history_kind(changes: dict, *, created: bool) -> str:
    if created:
        return "created"
    status = changes.get("status")
    if status in {"completed", "cancelled", "dropped"}:
        return status
    return "updated"


def load_owned_item(db: Session, item_id: str, user_id: str) -> Item:
    item = db.get(Item, item_id)
    if item is None or item.user_id != user_id:
        raise ToolWriteError(f"item {item_id} not found")
    return item


def require_parent(db: Session, parent_id: Optional[str], user_id: str) -> None:
    if parent_id is None:
        return
    parent = db.get(Item, parent_id)
    if parent is None or parent.user_id != user_id:
        raise ToolWriteError(f"parent {parent_id} not found")


def record_history(
    db: Session,
    *,
    item_id: str,
    message_id: str,
    kind: str,
    changes: dict,
) -> ItemHistory:
    row = ItemHistory(
        id=new_id("hst"),
        item_id=item_id,
        message_id=message_id,
        kind=kind,
        source="assistant_inference",
        changes=serialize_changes(changes),
    )
    db.add(row)
    return row
