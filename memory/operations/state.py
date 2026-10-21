"""Assemble prompt-ready interaction state from a Turn (M3)."""

from __future__ import annotations

from typing import Iterable, Sequence

from memory.db import db_session
from memory.models import Item, Message
from settings import STATE_HISTORY_WINDOW
from memory.operations.items import list_current_items
from memory.operations.messages import list_recent_messages
from memory.types import InteractionState, ItemSnapshot, Turn, TurnSnapshot


def _build_turn_snapshot(message: Message) -> TurnSnapshot:
    return TurnSnapshot(
        message_id=message.id,
        role=str(message.role),
        text=message.text,
        created_at=message.created_at,
    )


def _build_item_snapshot(item: Item) -> ItemSnapshot:
    return ItemSnapshot(
        id=item.id,
        type=str(item.type),
        title=item.title,
        status=str(item.status),
        work_mode=str(item.work_mode) if item.work_mode is not None else None,
        due_at=item.due_at,
    )


def render_prompt(
    *,
    current_text: str,
    recent_turns: Sequence[TurnSnapshot],
    current_items: Sequence[ItemSnapshot],
) -> str:
    """Deterministic prompt blob for M4 (stable empty sections)."""
    if recent_turns:
        recent_block = "\n".join(f"[{t.role}] {t.text}" for t in recent_turns)
    else:
        recent_block = "(none)"

    if current_items:
        items_block = "\n".join(
            f"- id={i.id} type={i.type} status={i.status} | {i.title}"
            for i in current_items
        )
    else:
        items_block = "(none)"

    return (
        "## Current message\n"
        f"{current_text}\n"
        "\n"
        "## Recent turns\n"
        f"{recent_block}\n"
        "\n"
        "## Current items\n"
        f"{items_block}"
    )


def _list_prior_turns(
    messages: Iterable[Message],
    *,
    current_message_id: str,
    limit: int,
) -> list[TurnSnapshot]:
    prior = [m for m in messages if m.id != current_message_id]
    # list_recent_messages returns chronological; keep the last `limit` prior rows
    if len(prior) > limit:
        prior = prior[-limit:]
    return [_build_turn_snapshot(m) for m in prior]


def assemble_interaction_state(turn: Turn) -> InteractionState:
    """Load recent turns + active items for the turn's user; render prompt."""
    with db_session() as db:
        # Fetch one extra so after dropping the current message we still have a full window.
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
        items = [_build_item_snapshot(i) for i in list_current_items(db, turn.user_id)]

    prompt = render_prompt(
        current_text=turn.text,
        recent_turns=recent,
        current_items=items,
    )
    return InteractionState(
        turn=turn,
        recent_turns=tuple(recent),
        current_items=tuple(items),
        prompt=prompt,
    )
