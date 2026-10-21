"""Pydantic contract for one LLM Decision (M4a)."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from constants import ITEM_ID_RE, ITEM_STATUSES, TOOL_NAMES

IntentKind = Literal["think", "remember", "irrelevant"]
WriteOperation = Literal["add", "update", "complete", "cancel"]
ConflictType = Literal["ambiguous_target", "conflicting_fact"]
ResponseType = Literal["confirmation", "clarification", "testify", "silence"]
ViewIntention = Literal["alignment", "reflection"]
ViewShape = Literal["inventory", "timeline", "outcome", "pattern"]
ViewOrder = Literal["chronological", "reverse_chronological", "priority", "natural"]
ToolName = Literal["add_item", "update_item", "search_items"]


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


class Continuity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str  # discourse: resolve | continue | change | idle (+ what)


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


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ToolName
    args: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("args")
    @classmethod
    def validate_args(cls, args: Dict[str, Any]) -> Dict[str, Any]:
        if "status" in args and args["status"] is not None:
            status = args["status"]
            if status not in ITEM_STATUSES:
                raise ValueError(
                    f"invalid status {status!r}; use one of {sorted(ITEM_STATUSES)}"
                )
        if "id" in args and args["id"] is not None:
            item_id = args["id"]
            if not isinstance(item_id, str) or not ITEM_ID_RE.match(item_id):
                raise ValueError(
                    f"args.id must be a DB item id matching itm_[0-9a-f]{{16}}; "
                    f"got {item_id!r}"
                )
        return args


class WritePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Optional[WriteOperation] = None
    target_ids: List[str] = Field(default_factory=list)
    missing: List[MissingFact] = Field(default_factory=list)
    conflicts: List[Conflict] = Field(default_factory=list)
    duplicate_ids: List[str] = Field(default_factory=list)
    tool_calls: List[ToolCall] = Field(default_factory=list)

    @field_validator("target_ids", "duplicate_ids")
    @classmethod
    def id_lists_are_item_ids(cls, v: List[str], info) -> List[str]:
        return assert_item_ids(v, field_name=info.field_name)


class Scope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: Optional[str] = None
    end: Optional[str] = None


class ViewPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intention: Optional[ViewIntention] = None
    shape: Optional[ViewShape] = None
    order: Optional[ViewOrder] = None
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

    continuity: Continuity
    intent: Intent
    write: WritePlan
    view: ViewPlan
    response: ResponsePlan

    @model_validator(mode="after")
    def check_tool_allowlist(self) -> "Decision":
        for call in self.write.tool_calls:
            if call.name not in TOOL_NAMES:
                raise ValueError(f"tool not allowlisted: {call.name}")
        return self
