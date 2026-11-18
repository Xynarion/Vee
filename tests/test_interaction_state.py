"""M3 — assemble interaction state (current message, recent turns, items, prompt)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from memory.db import db_session, new_id
from memory.models import Item, ItemHistory
from memory.operations.ingress import ingress_turn
from memory.operations.state import assemble_interaction_state


pytestmark = pytest.mark.skipif(
    not (os.getenv("DATABASE_URL") or "").strip(),
    reason="DATABASE_URL is required for Postgres interaction-state tests",
)

CLOCK = datetime(2026, 11, 14, 16, 45, tzinfo=ZoneInfo("Europe/London"))


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
    family_id = new_id("itm")
    family_start = datetime(2026, 11, 15, 17, 0, tzinfo=timezone.utc)

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
                Item(
                    id=family_id,
                    user_id=prior_a.user_id,
                    type="event",
                    title="Family meeting",
                    status="todo",
                    start_at=family_start,
                    flags=[],
                ),
            ]
        )
        db.flush()
        db.add(
            ItemHistory(
                id=new_id("hst"),
                item_id=completed_id,
                kind="created",
                source="user_message",
                created_at=datetime(2026, 11, 10, 12, 0, tzinfo=ZoneInfo("Europe/London")),
            )
        )
        db.add(
            ItemHistory(
                id=new_id("hst"),
                item_id=completed_id,
                kind="completed",
                source="user_message",
                created_at=datetime(2026, 11, 14, 9, 15, tzinfo=ZoneInfo("Europe/London")),
            )
        )

    current = ingress_turn(
        platform="telegram",
        platform_user_id=chat_id,
        role="user",
        text="Need to chase the Stripe onboarding email.",
    )

    state = assemble_interaction_state(current, now=CLOCK)

    print("\n" + "=" * 60)
    print("INTERACTION STATE (M3) — screenshot me")
    print("=" * 60)
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
    assert completed_id in item_ids
    assert family_id in item_ids
    assert "Archive old pitch deck" in item_titles

    prompt = state.prompt
    assert prompt.startswith("------------------------\nThe Interaction State")
    assert 'Current message:\n"Need to chase the Stripe onboarding email."' in prompt
    assert "Recent conversation:" in prompt
    assert "Founder: Yesterday I shipped the pricing page." in prompt
    assert "Vee: Noted the pricing page ship." in prompt
    assert "Founder: Still blocked on Stripe keys." in prompt
    assert "Progress Memory:" in prompt
    assert "Pay server invoice" in prompt
    assert active_invoice_id in prompt
    assert "Polish landing hero" in prompt
    assert "Archive old pitch deck" in prompt
    assert f"{completed_id} | task | completed | Archive old pitch deck" in prompt
    assert "history: created 2026-11-10 12:00; completed 2026-11-14 09:15" in prompt
    assert f"{family_id} | event | todo | Family meeting | start 2026-11-15T17:00:00+00:00" in prompt
    assert "16:45, Saturday 14 November 2026, Europe/London" in prompt
    assert "This calendar week (current week):\n2026-11-09 → 2026-11-15" in prompt
    assert "Last calendar week (previous week):\n2026-11-02 → 2026-11-08" in prompt
    assert current.text not in [
        t.text for t in state.recent_turns
    ]
