"""Shared types for memory ingress and later workflows."""

from __future__ import annotations

from dataclasses import dataclass


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
