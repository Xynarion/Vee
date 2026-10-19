"""M3 — assemble interaction state (current message, recent turns, items, prompt)."""

from __future__ import annotations

import os
import uuid

import pytest

from memory.db import db_session, new_id
from memory.models import Item
from memory.operations.ingress import ingress_turn
from memory.operations.state import assemble_interaction_state


pytestmark = pytest.mark.skipif(
    not (os.getenv("DATABASE_URL") or "").strip(),
    reason="DATABASE_URL is required for Postgres interaction-state tests",
)


def test_assemble_interaction_state_prompt_ready() -> None:
    chat_id = f"m3_{uuid.uuid4().hex[:12]}"

    prior_a = ingress_turn(
        platform="telegram",
        platform_user_id=chat_id,
        role="user",
        text="Yesterday I shipped the pricing page.",
    )
    ingress_turn(
        platform="telegram",
        platform_user_id=chat_id,
        role="assistant",
        text="Noted the pricing page ship.",
    )
    ingress_turn(
        platform="telegram",
        platform_user_id=chat_id,
        role="user",
        text="Still blocked on Stripe keys.",
    )

    active_invoice_id = new_id("itm")
    active_landing_id = new_id("itm")
    completed_id = new_id("itm")

    with db_session() as db:
        db.add_all(
            [
                Item(
                    id=active_invoice_id,
                    user_id=prior_a.user_id,
                    type="task",
                    title="Pay server invoice",
                    status="todo",
                    flags=[],
                ),
                Item(
                    id=active_landing_id,
                    user_id=prior_a.user_id,
                    type="task",
                    title="Polish landing hero",
                    status="in_progress",
                    flags=[],
                ),
                Item(
                    id=completed_id,
                    user_id=prior_a.user_id,
                    type="task",
                    title="Archive old pitch deck",
                    status="completed",
                    flags=[],
                ),
            ]
        )

    current = ingress_turn(
        platform="telegram",
        platform_user_id=chat_id,
        role="user",
        text="Need to chase the Stripe onboarding email.",
    )

    state = assemble_interaction_state(current)

    # Visible with: pytest tests/test_interaction_state.py -s
    print("\n" + "=" * 60)
    print("INTERACTION STATE (M3) — screenshot me")
    print("=" * 60)
    print(f"current.message_id : {state.turn.message_id}")
    print(f"current.role       : {state.turn.role}")
    print(f"current.text       : {state.turn.text}")
    print(f"recent_turns       : {len(state.recent_turns)}")
    for t in state.recent_turns:
        print(f"  [{t.role}] {t.text}")
    print(f"current_items      : {len(state.current_items)}")
    for i in state.current_items:
        print(f"  {i.status:12} {i.type:6} | {i.title} ({i.id})")
    print("-" * 60)
    print("PROMPT")
    print("-" * 60)
    print(state.prompt)
    print("=" * 60 + "\n")

    assert state.turn.message_id == current.message_id
    assert state.turn.text == "Need to chase the Stripe onboarding email."

    recent_ids = [t.message_id for t in state.recent_turns]
    assert current.message_id not in recent_ids
    created_ats = [t.created_at for t in state.recent_turns]
    assert created_ats == sorted(created_ats)
    recent_texts = [t.text for t in state.recent_turns]
    assert "Yesterday I shipped the pricing page." in recent_texts
    assert "Noted the pricing page ship." in recent_texts
    assert "Still blocked on Stripe keys." in recent_texts

    item_ids = {i.id for i in state.current_items}
    item_titles = {i.title for i in state.current_items}
    assert active_invoice_id in item_ids
    assert active_landing_id in item_ids
    assert completed_id not in item_ids
    assert "Archive old pitch deck" not in item_titles
    assert all(i.status in {"todo", "in_progress"} for i in state.current_items)

    prompt = state.prompt
    assert "## Current message" in prompt
    assert "Need to chase the Stripe onboarding email." in prompt
    assert "## Recent turns" in prompt
    assert "[user] Yesterday I shipped the pricing page." in prompt
    assert "[assistant] Noted the pricing page ship." in prompt
    assert "## Current items" in prompt
    assert "Pay server invoice" in prompt
    assert active_invoice_id in prompt
    assert "Polish landing hero" in prompt
    assert "Archive old pitch deck" not in prompt
