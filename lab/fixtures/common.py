"""Shared scenario shape and Interaction State helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from memory.plate import (
    calendar_week,
    render_interaction_state,
    parse_clock_date,
    previous_calendar_week,
    week_bounds_for_clock,
)

GoldenFn = Callable[[], Dict[str, Any]]

__all__ = [
    "GoldenFn",
    "Scenario",
    "calendar_week",
    "render_interaction_state",
    "parse_clock_date",
    "previous_calendar_week",
    "turn",
    "week_bounds_for_clock",
    "with_current_message",
]


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    interaction_state: str
    golden: GoldenFn
    family: str


def turn(founder: str, vee: str) -> str:
    return f"Founder: {founder}\nVee: {vee}"


_MESSAGE_PREFIX = "Current message:\n"
_MESSAGE_NEXT = "\n\nRecent conversation:"


def with_current_message(state: str, message: Optional[str]) -> str:
    """Replace only the quoted Current message; leave the rest of the plate."""
    if message is None:
        return state
    text = str(message).strip()
    if text.startswith('"') and text.endswith('"') and len(text) >= 2:
        text = text[1:-1].strip()
    if not text:
        return state
    start = state.find(_MESSAGE_PREFIX)
    end = state.find(_MESSAGE_NEXT, start)
    if start < 0 or end < 0:
        return state
    return f'{state[:start]}{_MESSAGE_PREFIX}"{text}"{state[end:]}'
