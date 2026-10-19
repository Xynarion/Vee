"""Shared types for memory ingress and later workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple


@dataclass(frozen=True)
class Turn:
    """One conversation turn after ingress — user or assistant."""

    user_id: str
    channel_id: str
    message_id: str
    platform: str
    platform_user_id: str
    role: str
    text: str


@dataclass(frozen=True)
class TurnSnapshot:
    """One prior message included in interaction state (no ORM)."""

    message_id: str
    role: str
    text: str
    created_at: datetime


@dataclass(frozen=True)
class ItemSnapshot:
    """Active progress item for the prompt (no ORM)."""

    id: str
    type: str
    title: str
    status: str
    work_mode: Optional[str]
    due_at: Optional[datetime]


@dataclass(frozen=True)
class InteractionState:
    """Prompt-ready context for one interaction (M3; LLM call is M4)."""

    turn: Turn
    recent_turns: Tuple[TurnSnapshot, ...]
    current_items: Tuple[ItemSnapshot, ...]
    prompt: str
