"""Pydantic contract for one LLM Decision (M4a)."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from constants import ITEM_ID_RE
from tools import ToolCall

IntentKind = Literal["brain_dump", "remember", "irrelevant"]
ConflictType = Literal["ambiguous_target", "conflicting_fact"]
ResponseType = Literal["confirmation", "clarification", "testify", "silence"]
RecallIntention = Literal["alignment", "reflection"]
RecallShape = Literal["inventory", "timeline", "outcome", "pattern"]
RecallOrder = Literal["chronological", "reverse_chronological", "priority", "natural"]


def assert_item_ids(ids: List[str], *, field_name: str) -> List[str]:
    """Every entry must be a DB items.id (itm_ + 16 hex)."""
    if not isinstance(ids, list):
        raise ValueError(f"{field_name} must be a list of item ids")
    bad: List[str] = []
    for value in ids:
        if not isinstance(value, str) or not ITEM_ID_RE.match(value):
            bad.append(repr(value))
    if bad:
        raise ValueError(
            f"{field_name} must be DB item ids matching itm_[0-9a-f]{{16}}; "
            f"invalid: {', '.join(bad)}"
        )
    return ids


class Intent(BaseModel):
    """Door (kind) + one-line ticket (summary): what they want to do this turn."""

    model_config = ConfigDict(extra="forbid")

    kind: IntentKind
    summary: str  # progress-memory want for this turn


class MissingFact(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    field: str
    for_: str = Field(alias="for")
    reason: str


class Conflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ConflictType
    phrase: str
    candidate_ids: List[str] = Field(default_factory=list)
    reason: str

    @field_validator("candidate_ids")
    @classmethod
    def candidate_ids_are_item_ids(cls, v: List[str]) -> List[str]:
        return assert_item_ids(v, field_name="candidate_ids")


class WritePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_ids: List[str] = Field(default_factory=list)
    missing: List[MissingFact] = Field(default_factory=list)
    conflicts: List[Conflict] = Field(default_factory=list)
    duplicate_ids: List[str] = Field(default_factory=list)

    @field_validator("target_ids", "duplicate_ids")
    @classmethod
    def id_lists_are_item_ids(cls, v: List[str], info) -> List[str]:
        return assert_item_ids(v, field_name=info.field_name)


class Scope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: Optional[str] = None
    end: Optional[str] = None


class RecallPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intention: Optional[RecallIntention] = None
    shape: Optional[RecallShape] = None
    order: Optional[RecallOrder] = None
    scope: Scope = Field(default_factory=Scope)


class ResponsePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ResponseType
    text: str = ""
    show_ids: List[str] = Field(default_factory=list)

    @field_validator("show_ids")
    @classmethod
    def show_ids_are_item_ids(cls, v: List[str]) -> List[str]:
        return assert_item_ids(v, field_name="show_ids")


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    write: WritePlan
    recall: RecallPlan
    tool_calls: List[ToolCall] = Field(default_factory=list)
    response: ResponsePlan

