"""Assemble prompt-ready interaction state from a Turn (M3)."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, Sequence
from zoneinfo import ZoneInfo

from memory.db import db_session
from memory.models import Item, Message
from memory.operations.items import list_progress_items
from memory.operations.messages import list_recent_messages
from memory.plate import (
    format_clock,
    format_progress_memory,
    format_recent_conversation,
    render_interaction_state,
)
from memory.types import HistorySnapshot, InteractionState, ItemSnapshot, Turn, TurnSnapshot
from settings import DEFAULT_TIMEZONE, STATE_HISTORY_WINDOW


def _build_turn_snapshot(message: Message) -> TurnSnapshot:
    return TurnSnapshot(
        message_id=message.id,
        role=str(message.role),
        text=message.text,
        created_at=message.created_at,
    )


def _build_item_snapshot(item: Item) -> ItemSnapshot:
    history = tuple(
        HistorySnapshot(
            kind=str(row.kind),
            at=row.created_at,
            changes=row.changes if isinstance(row.changes, dict) else None,
        )
        for row in sorted(item.history or [], key=lambda row: row.created_at)
    )
    return ItemSnapshot(
        id=item.id,
        type=str(item.type),
        title=item.title,
        status=str(item.status),
        work_mode=str(item.work_mode) if item.work_mode is not None else None,
        due_at=item.due_at,
        start_at=item.start_at,
        end_at=item.end_at,
        history=history,
    )


def render_prompt(
    *,
    current_text: str,
    recent_turns: Sequence[TurnSnapshot],
    current_items: Sequence[ItemSnapshot],
    now: Optional[datetime] = None,
    tz_name: str = DEFAULT_TIMEZONE,
) -> str:
    """Lab-shaped Interaction State plate for M4."""
    when = format_clock(now or datetime.now(ZoneInfo(tz_name)), tz_name)
    return render_interaction_state(
        current_text,
        format_recent_conversation(recent_turns),
        format_progress_memory(current_items, tz_name),
        when,
    )


def _list_prior_turns(
    messages: Iterable[Message],
    *,
    current_message_id: str,
    limit: int,
) -> list[TurnSnapshot]:
    prior = [m for m in messages if m.id != current_message_id]
    if len(prior) > limit:
        prior = prior[-limit:]
    return [_build_turn_snapshot(m) for m in prior]


def assemble_interaction_state(
    turn: Turn,
    *,
    now: Optional[datetime] = None,
    tz_name: str = DEFAULT_TIMEZONE,
) -> InteractionState:
    """Load recent turns + Progress Memory for the turn's user; render the plate."""
    with db_session() as db:
        messages = list_recent_messages(
            db,
            turn.user_id,
            limit=STATE_HISTORY_WINDOW + 1,
        )
        recent = _list_prior_turns(
            messages,
            current_message_id=turn.message_id,
            limit=STATE_HISTORY_WINDOW,
        )
        items = [_build_item_snapshot(i) for i in list_progress_items(db, turn.user_id)]

    prompt = render_prompt(
        current_text=turn.text,
        recent_turns=recent,
        current_items=items,
        now=now,
        tz_name=tz_name,
    )
    return InteractionState(
        turn=turn,
        recent_turns=tuple(recent),
        current_items=tuple(items),
        prompt=prompt,
    )
