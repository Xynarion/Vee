"""Stable Decision when model output cannot be accepted (M4a)."""

from __future__ import annotations

from llm.schema import (
    Decision,
    Intent,
    ResponsePlan,
    Scope,
    RecallPlan,
    WritePlan,
)

FALLBACK_RESPONSE_TEXT = (
    "I could not read that reliably. Please try again in one short message."
)


def safe_fallback(reason: str) -> Decision:
    """Return a clarification Decision. `reason` is for logs only."""
    _ = reason  # caller logs; keep payload stable
    return Decision(
        intent=Intent(
            kind="irrelevant",
            summary="Could not validate model output.",
        ),
        write=WritePlan(
            target_ids=[],
            missing=[],
            conflicts=[],
            duplicate_ids=[],
        ),
        recall=RecallPlan(
            intention=None,
            shape=None,
            order=None,
            scope=Scope(start=None, end=None),
        ),
        tool_calls=[],
        response=ResponsePlan(
            type="clarification",
            text=FALLBACK_RESPONSE_TEXT,
            show_ids=[],
        ),
    )
