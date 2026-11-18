"""Pydantic contract for one LLM Decision (judge / plan / say)."""

from __future__ import annotations

import re
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from constants import ITEM_ID_RE
from tools import ToolCall

Responsibility = Literal["witness", "testify"]
MatchStatus = Literal["existing", "new", "ambiguous"]
UncertaintyType = Literal["ambiguous_match", "conflicting_facts", "missing_information"]
ActionType = Literal["create", "update", "clarify", "testify"]
SayType = Literal["confirmation", "clarification", "testimony", "silence"]
TestimonyView = Literal["inventory", "timeline", "outcomes", "patterns", "summary"]
TestimonyOrder = Literal["chronological", "reverse_chronological", "priority", "natural"]

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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


def _item_id(value: Optional[str], *, field_name: str) -> Optional[str]:
    if value is None:
        return value
    if not ITEM_ID_RE.match(value):
        raise ValueError(f"{field_name} must match itm_[0-9a-f]{{16}}; got {value!r}")
    return value


def _unique(values: List[str], *, field_name: str) -> List[str]:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return values


def _optional_iso_date(value: Optional[str], *, field_name: str) -> Optional[str]:
    if value is None:
        return None
    if not _ISO_DATE_RE.match(value):
        raise ValueError(f"{field_name} must be YYYY-MM-DD or null; got {value!r}")
    return value


class RequestedPeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: Optional[str] = None
    end: Optional[str] = None
    reason: Optional[str] = None

    @field_validator("start", "end")
    @classmethod
    def check_iso_date(cls, v: Optional[str], info) -> Optional[str]:
        return _optional_iso_date(v, field_name=info.field_name)


class Understanding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    continuity: Optional[str] = None
    message_meaning_summary: str
    responsibilities: List[Responsibility] = Field(default_factory=list)
    responsibilities_reason: str
    requested_period: Optional[RequestedPeriod] = None

    @field_validator("responsibilities")
    @classmethod
    def unique_responsibilities(cls, v: List[str]) -> List[str]:
        return _unique(v, field_name="responsibilities")


class RecordFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    piece_of_work: str
    match_status: MatchStatus
    item_id: Optional[str] = None
    finding: str

    @field_validator("item_id")
    @classmethod
    def check_item_id(cls, v: Optional[str]) -> Optional[str]:
        return _item_id(v, field_name="item_id")


class Uncertainty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    piece_of_work: str
    type: UncertaintyType
    candidate_ids: List[str] = Field(default_factory=list)
    question: str

    @field_validator("candidate_ids")
    @classmethod
    def check_ids(cls, v: List[str]) -> List[str]:
        return assert_item_ids(_unique(v, field_name="candidate_ids"), field_name="candidate_ids")


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_findings: List[RecordFinding] = Field(default_factory=list)
    uncertainties: List[Uncertainty] = Field(default_factory=list)


class RequiredAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ActionType
    item_id: Optional[str] = None
    piece_of_work: Optional[str] = None
    reason: str

    @field_validator("item_id")
    @classmethod
    def check_item_id(cls, v: Optional[str]) -> Optional[str]:
        return _item_id(v, field_name="item_id")


class JudgeDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_actions: List[RequiredAction] = Field(default_factory=list)


class Judge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    understanding: Understanding
    evidence: Evidence
    decision: JudgeDecision


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_calls: List[ToolCall] = Field(default_factory=list)


class Scope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: Optional[str] = None
    end: Optional[str] = None

    @field_validator("start", "end")
    @classmethod
    def check_iso_date(cls, v: Optional[str], info) -> Optional[str]:
        return _optional_iso_date(v, field_name=info.field_name)


class Testimony(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aim: str
    purpose_reason: str
    view: TestimonyView
    view_reason: str
    order: TestimonyOrder
    scope: Scope = Field(default_factory=Scope)
    scope_reason: str
    item_ids: List[str] = Field(default_factory=list)
    item_ids_reason: str
    omitted_ids: List[str] = Field(default_factory=list)
    omitted_ids_reason: Optional[str] = None

    @field_validator("item_ids")
    @classmethod
    def check_ids(cls, v: List[str]) -> List[str]:
        return assert_item_ids(_unique(v, field_name="item_ids"), field_name="item_ids")

    @field_validator("omitted_ids")
    @classmethod
    def check_omitted_ids(cls, v: List[str]) -> List[str]:
        return assert_item_ids(_unique(v, field_name="omitted_ids"), field_name="omitted_ids")

    @model_validator(mode="after")
    def omitted_reason_required(self) -> "Testimony":
        if self.omitted_ids and not (self.omitted_ids_reason or "").strip():
            raise ValueError("omitted_ids_reason required when omitted_ids is not empty")
        return self


class Say(BaseModel):
    model_config = ConfigDict(extra="forbid")

    types: List[SayType] = Field(default_factory=list)
    text: Optional[str] = None
    testimony: Optional[Testimony] = None

    @field_validator("types")
    @classmethod
    def unique_types(cls, v: List[str]) -> List[str]:
        return _unique(v, field_name="types")

    @model_validator(mode="after")
    def testimony_required_when_typed(self) -> "Say":
        if "testimony" in self.types and self.testimony is None:
            raise ValueError("Testimony payload required")
        return self


class Decision(BaseModel):
    """Prompt output object. extra=forbid so unknown fields fail validation."""

    model_config = ConfigDict(extra="forbid")

    judge: Judge
    plan: Plan
    say: Say
