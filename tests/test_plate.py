"""Interaction State plate — lab scenario shape, no database."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from lab.fixtures.common import render_interaction_state as render_lab_interaction_state
from lab.fixtures.common import week_bounds_for_clock, with_current_message
from lab.scenario import golden_remembering_02
from memory.operations.state import render_prompt
from memory.plate import (
    format_clock,
    format_progress_memory,
    format_recent_conversation,
    render_interaction_state,
    week_bounds_for_clock as plate_weeks,
)
from memory.types import HistorySnapshot, ItemSnapshot, TurnSnapshot


def test_clock_matches_remembering_scenario() -> None:
    when = format_clock(
        datetime(2026, 11, 14, 16, 45, tzinfo=ZoneInfo("Europe/London"))
    )
    assert when == "16:45, Saturday 14 November 2026, Europe/London"
    assert plate_weeks(when) == week_bounds_for_clock(when)
    assert plate_weeks(when)["this_week"] == ("2026-11-09", "2026-11-15")
    assert plate_weeks(when)["last_week"] == ("2026-11-02", "2026-11-08")


def test_interaction_is_the_lab_template() -> None:
    plate = render_interaction_state(
        "What did I get done last week?",
        "(none)",
        "itm_0000000000000008 | task | completed | Ship pricing page",
        "16:45, Saturday 14 November 2026, Europe/London",
    )
    assert plate == render_lab_interaction_state(
        "What did I get done last week?",
        "(none)",
        "itm_0000000000000008 | task | completed | Ship pricing page",
        "16:45, Saturday 14 November 2026, Europe/London",
    )
    assert 'Current message:\n"What did I get done last week?"' in plate
    assert "Recent conversation:\n(none)" in plate
    assert "Progress Memory:\n" in plate
    assert "This calendar week (current week):\n2026-11-09 → 2026-11-15" in plate
    assert "Last calendar week (previous week):\n2026-11-02 → 2026-11-08" in plate


def test_recent_conversation_uses_founder_vee() -> None:
    turns = (
        TurnSnapshot(
            message_id="msg_1",
            role="user",
            text="move the Acme chase to tomorrow",
            created_at=datetime(2026, 11, 6, 10, 30, tzinfo=timezone.utc),
        ),
        TurnSnapshot(
            message_id="msg_2",
            role="assistant",
            text="Recorded.",
            created_at=datetime(2026, 11, 6, 10, 31, tzinfo=timezone.utc),
        ),
    )
    assert format_recent_conversation(turns) == (
        "Founder: move the Acme chase to tomorrow\nVee: Recorded."
    )
    assert format_recent_conversation(()) == "(none)"


def test_progress_memory_includes_schedule_and_grouped_carry() -> None:
    item = ItemSnapshot(
        id="itm_0000000000000001",
        type="task",
        title="Hit the gym",
        status="cancelled",
        work_mode=None,
        due_at=None,
        history=(
            HistorySnapshot(
                kind="created",
                at=datetime(2026, 11, 10, 9, 0, tzinfo=ZoneInfo("Europe/London")),
            ),
            HistorySnapshot(
                kind="carried",
                at=datetime(2026, 11, 11, 0, 0, tzinfo=ZoneInfo("Europe/London")),
            ),
            HistorySnapshot(
                kind="carried",
                at=datetime(2026, 11, 12, 0, 0, tzinfo=ZoneInfo("Europe/London")),
            ),
            HistorySnapshot(
                kind="cancelled",
                at=datetime(2026, 11, 14, 10, 0, tzinfo=ZoneInfo("Europe/London")),
            ),
        ),
    )
    event = ItemSnapshot(
        id="itm_0000000000000004",
        type="event",
        title="Family meeting",
        status="todo",
        work_mode=None,
        due_at=None,
        start_at=datetime(2026, 11, 15, 17, 0, tzinfo=timezone.utc),
        history=(
            HistorySnapshot(
                kind="created",
                at=datetime(2026, 11, 13, 10, 35, tzinfo=ZoneInfo("Europe/London")),
            ),
            HistorySnapshot(
                kind="updated",
                at=datetime(2026, 11, 14, 10, 20, tzinfo=ZoneInfo("Europe/London")),
                changes={"start_at": "2026-11-15T17:00:00+00:00"},
            ),
        ),
    )
    block = format_progress_memory([item, event])
    assert (
        "itm_0000000000000001 | task | cancelled | Hit the gym\n"
        "  history: created 2026-11-10 09:00; carried 2026-11-11, 2026-11-12; "
        "cancelled 2026-11-14 10:00"
    ) in block
    assert "itm_0000000000000004 | event | todo | Family meeting | start 2026-11-15T17:00:00+00:00" in block
    assert "updated 2026-11-14 10:20 (start_at → 2026-11-15T17:00:00+00:00)" in block
    assert format_progress_memory(()) == "(none)"


def test_with_current_message_still_rewrites_the_plate() -> None:
    state = render_interaction_state("old", "(none)", "(none)", "16:30, Saturday 14 November 2026, Europe/London")
    updated = with_current_message(state, "what do i have today?")
    assert 'Current message:\n"what do i have today?"' in updated
    assert "16:30, Saturday 14 November 2026" in updated


def test_lab_remembering_fixture_still_uses_the_shared_plate() -> None:
    from lab.scenario import resolve_interaction_state

    state = resolve_interaction_state("remembering-02", None)
    assert state.startswith("------------------------\nThe Interaction State")
    assert "Progress Memory:" in state
    assert golden_remembering_02()["judge"]["understanding"]["requested_period"]["start"] == "2026-11-02"


def test_format_recent_accepts_plain_namespaces() -> None:
    recent = format_recent_conversation(
        [SimpleNamespace(role="user", text="hello")]
    )
    assert recent == "Founder: hello"


def test_render_prompt_matches_lab_scenario_plate() -> None:
    clock = datetime(2026, 11, 14, 16, 45, tzinfo=ZoneInfo("Europe/London"))
    recent = (
        TurnSnapshot(
            message_id="msg_1",
            role="user",
            text="move the Acme chase to tomorrow",
            created_at=clock,
        ),
        TurnSnapshot(
            message_id="msg_2",
            role="assistant",
            text="Recorded.",
            created_at=clock,
        ),
    )
    items = (
        ItemSnapshot(
            id="itm_0000000000000001",
            type="task",
            title="Chase Acme overdue invoice",
            status="todo",
            work_mode=None,
            due_at=datetime(2026, 11, 7, 23, 59, 59, tzinfo=timezone.utc),
        ),
    )
    prompt = render_prompt(
        current_text="What did I get done last week?",
        recent_turns=recent,
        current_items=items,
        now=clock,
    )
    expected = render_interaction_state(
        "What did I get done last week?",
        "Founder: move the Acme chase to tomorrow\nVee: Recorded.",
        "itm_0000000000000001 | task | todo | Chase Acme overdue invoice | due 2026-11-07T23:59:59+00:00",
        "16:45, Saturday 14 November 2026, Europe/London",
    )
    assert prompt == expected
