"""search_items — read-only lookup across all of a user's items (any status)."""

from __future__ import annotations

from datetime import date
from typing import List, Literal, Optional, Union

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from constants import ITEM_STATUSES, ITEM_TYPES, ITEM_WORK_MODES
from tools import _fields

NAME = "search_items"

SortField = Literal["due_at", "start_at", "created_at", "updated_at", "title"]

# A bare date means that whole day in the user's timezone (resolved by the executor).
Bound = Union[AwareDatetime, date]


class DateRange(BaseModel):
    """Inclusive bounds; either side may be open."""

    model_config = ConfigDict(extra="forbid")

    after: Optional[Bound] = None
    before: Optional[Bound] = None

    @model_validator(mode="after")
    def check_bounds(self) -> "DateRange":
        if self.after is None and self.before is None:
            raise ValueError("date range needs `after`, `before`, or both")
        return self


class SearchItemsArgs(BaseModel):
    """Every filter is optional and filters combine with AND.

    List filters match any value in the list. No filters = all items (bounded by `limit`).
    """

    model_config = ConfigDict(extra="forbid")

    query: Optional[str] = None
    ids: Optional[List[str]] = None
    status: Optional[List[str]] = None
    type: Optional[List[str]] = None
    work_mode: Optional[List[str]] = None
    parent_id: Optional[str] = None
    carried: Optional[bool] = None
    has_due_at: Optional[bool] = None
    has_start_at: Optional[bool] = None
    due: Optional[DateRange] = None
    start: Optional[DateRange] = None
    created: Optional[DateRange] = None
    updated: Optional[DateRange] = None
    sort_by: Optional[SortField] = None
    sort_order: Optional[Literal["asc", "desc"]] = None
    limit: Optional[int] = Field(default=None, ge=1, le=100)

    @field_validator("status", "type", "work_mode", mode="before")
    @classmethod
    def coerce_single_value(cls, v):
        return _fields.as_list(v)

    @field_validator("query")
    @classmethod
    def check_query(cls, v: Optional[str]) -> Optional[str]:
        return _fields.non_empty(v, field_name="query")

    @field_validator("ids")
    @classmethod
    def check_ids(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        for value in v or []:
            _fields.item_id(value, field_name="ids")
        return v

    @field_validator("status")
    @classmethod
    def check_status(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        return _fields.all_one_of(v, ITEM_STATUSES, field_name="status")

    @field_validator("type")
    @classmethod
    def check_type(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        return _fields.all_one_of(v, ITEM_TYPES, field_name="type")

    @field_validator("work_mode")
    @classmethod
    def check_work_mode(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        return _fields.all_one_of(v, ITEM_WORK_MODES, field_name="work_mode")

    @field_validator("parent_id")
    @classmethod
    def check_parent_id(cls, v: Optional[str]) -> Optional[str]:
        return _fields.item_id(v, field_name="parent_id")

    @model_validator(mode="after")
    def check_consistency(self) -> "SearchItemsArgs":
        if self.has_due_at is False and self.due is not None:
            raise ValueError("has_due_at=false contradicts a `due` range")
        if self.has_start_at is False and self.start is not None:
            raise ValueError("has_start_at=false contradicts a `start` range")
        if self.sort_order is not None and self.sort_by is None:
            raise ValueError("sort_order needs sort_by")
        return self


class SearchItemsCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Literal["search_items"]
    args: SearchItemsArgs
