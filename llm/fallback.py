"""Stable Decision when model output cannot be accepted (M4a)."""

from __future__ import annotations

from llm.schema import (
    Decision,
    Evidence,
    Judge,
    JudgeDecision,
    Plan,
    Say,
    Understanding,
)

FALLBACK_RESPONSE_TEXT = (
    "I could not read that reliably. Please try again in one short message."
)


def safe_fallback(reason: str) -> Decision:
    """Return a clarification Decision. `reason` is for logs only."""
    _ = reason  # caller logs; keep payload stable
    return Decision(
        judge=Judge(
            understanding=Understanding(
                continuity=None,
                message_meaning_summary="Could not validate model output.",
                responsibilities=[],
                responsibilities_reason=(
                    "Output could not be accepted; this turn requires neither "
                    "witnessing nor testifying."
                ),
                requested_period=None,
            ),
            evidence=Evidence(),
            decision=JudgeDecision(),
        ),
        plan=Plan(tool_calls=[]),
        say=Say(
            types=["clarification"],
            text=FALLBACK_RESPONSE_TEXT,
            testimony=None,
        ),
    )
