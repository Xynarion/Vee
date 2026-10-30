"""add_item — create a task or event."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator

from constants import ITEM_STATUSES, ITEM_TYPES, ITEM_WORK_MODES
from tools import _fields

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
