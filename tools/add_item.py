"""add_item — create a task or event."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator

from sqlalchemy.orm import Session

from constants import ITEM_STATUSES, ITEM_TYPES, ITEM_WORK_MODES
from memory.db import new_id
from memory.models import Item
from tools import _fields
from tools.write import choose_history_kind, record_history, require_parent, serialize_changes

NAME = "add_item"


class AddItemArgs(BaseModel):
    """Omitted optional fields mean null."""

    model_config = ConfigDict(extra="forbid")

    title: str
    type: str
    parent_id: Optional[str] = None
    start_at: Optional[AwareDatetime] = None
    end_at: Optional[AwareDatetime] = None
    due_at: Optional[AwareDatetime] = None
    status: str = "todo"
    work_mode: Optional[str] = None

    @field_validator("title")
    @classmethod
    def check_title(cls, v: str) -> str:
        return _fields.non_empty(v, field_name="title")

    @field_validator("type")
    @classmethod
    def check_type(cls, v: str) -> str:
        return _fields.one_of(v, ITEM_TYPES, field_name="type")

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str) -> str:
        return _fields.one_of(v, ITEM_STATUSES, field_name="status")

    @field_validator("work_mode")
    @classmethod
    def check_work_mode(cls, v: Optional[str]) -> Optional[str]:
        return _fields.one_of(v, ITEM_WORK_MODES, field_name="work_mode")

    @field_validator("parent_id")
    @classmethod
    def check_parent_id(cls, v: Optional[str]) -> Optional[str]:
        return _fields.item_id(v, field_name="parent_id")


class AddItemCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Literal["add_item"]
    args: AddItemArgs


def run(db: Session, args: AddItemArgs, *, user_id: str, message_id: str) -> tuple[str, dict]:
    """Insert one item and its created history. The code assigns both ids."""
    require_parent(db, args.parent_id, user_id)
    item_id = new_id("itm")
    written = {
        "title": args.title,
        "type": args.type,
        "status": args.status,
    }
    for name in ("parent_id", "start_at", "end_at", "due_at", "work_mode"):
        value = getattr(args, name)
        if value is not None:
            written[name] = value
    db.add(
        Item(
            id=item_id,
            user_id=user_id,
            type=args.type,
            title=args.title,
            parent_id=args.parent_id,
            start_at=args.start_at,
            end_at=args.end_at,
            due_at=args.due_at,
            status=args.status,
            work_mode=args.work_mode,
            flags=[],
        )
    )
    record_history(
        db,
        item_id=item_id,
        message_id=message_id,
        kind=choose_history_kind(written, created=True),
        changes=written,
    )
    db.flush()
    return item_id, serialize_changes(written)
