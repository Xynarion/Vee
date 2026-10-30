"""update_item — change an existing item by id."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator, model_validator

from constants import ITEM_STATUSES, ITEM_TYPES, ITEM_WORK_MODES
from tools import _fields

NAME = "update_item"

# DB columns that cannot be cleared
_NOT_CLEARABLE = ("title", "type", "status")


class UpdateItemArgs(BaseModel):
    """`id` identifies the row. A sent `title` is the new name; omit it to keep the current one.

    Omitted field = unchanged; null = clear. `title` cannot be cleared.
    Executors must read changes via `changes()`, never a plain model_dump().
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    title: Optional[str] = None
    type: Optional[str] = None
    parent_id: Optional[str] = None
    start_at: Optional[AwareDatetime] = None
    end_at: Optional[AwareDatetime] = None
    due_at: Optional[AwareDatetime] = None
    status: Optional[str] = None
    work_mode: Optional[str] = None

    @field_validator("id")
    @classmethod
    def check_id(cls, v: str) -> str:
        return _fields.item_id(v, field_name="id")

    @field_validator("title")
    @classmethod
    def check_title(cls, v: Optional[str]) -> Optional[str]:
        return _fields.non_empty(v, field_name="title")

    @field_validator("type")
    @classmethod
    def check_type(cls, v: Optional[str]) -> Optional[str]:
        return _fields.one_of(v, ITEM_TYPES, field_name="type")

    @field_validator("status")
    @classmethod
    def check_status(cls, v: Optional[str]) -> Optional[str]:
        return _fields.one_of(v, ITEM_STATUSES, field_name="status")

    @field_validator("work_mode")
    @classmethod
    def check_work_mode(cls, v: Optional[str]) -> Optional[str]:
        return _fields.one_of(v, ITEM_WORK_MODES, field_name="work_mode")

    @field_validator("parent_id")
    @classmethod
    def check_parent_id(cls, v: Optional[str]) -> Optional[str]:
        return _fields.item_id(v, field_name="parent_id")

    @model_validator(mode="after")
    def check_changes(self) -> "UpdateItemArgs":
        for name in _NOT_CLEARABLE:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"update_item.{name} cannot be null; omit it to leave unchanged")
        if not self.changes():
            raise ValueError("update_item must change at least one field")
        return self

    def changes(self) -> dict:
        """Fields the model actually sent, excluding the id."""
        return self.model_dump(exclude_unset=True, exclude={"id"})


class UpdateItemCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Literal["update_item"]
    args: UpdateItemArgs
