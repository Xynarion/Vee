"""Remembering fixtures: Saturday 14 November 2026 plates for day alignment and last week."""

from __future__ import annotations

from typing import Any, Dict

from lab.fixtures.common import Scenario, render_interaction_state

REM_GYM_ID = "itm_0000000000000001"
REM_LANDING_ID = "itm_0000000000000002"
REM_DOCTOR_ID = "itm_0000000000000003"
REM_FAMILY_ID = "itm_0000000000000004"
REM_HASSAN_ID = "itm_0000000000000005"
REM_PROPOSAL_ID = "itm_0000000000000006"
REM_STANDUP_ID = "itm_0000000000000007"

REM_TODAY = "2026-11-14"
REM_CLOCK = "16:30, Saturday 14 November 2026, Europe/London"

MSG_01 = "what do i have today?"
MSG_02 = "What did I get done last week?"
REM_CLOCK_02 = "16:45, Saturday 14 November 2026, Europe/London"
LAST_WEEK_START = "2026-11-02"
LAST_WEEK_END = "2026-11-08"

WEEK_PRICING_ID = "itm_0000000000000008"
WEEK_COFFEE_ID = "itm_0000000000000009"
WEEK_EXPENSES_ID = "itm_000000000000000a"
WEEK_REVIEW_ID = "itm_000000000000000b"
WEEK_GYM_ID = "itm_000000000000000c"
WEEK_STANDUP_ID = "itm_000000000000000d"
WEEK_DOCTOR_ID = "itm_000000000000000e"
WEEK_INVOICE_ID = "itm_000000000000000f"
WEEK_PROPOSAL_ID = "itm_0000000000000010"
WEEK_LANDING_ID = "itm_0000000000000011"
WEEK_FAMILY_ID = "itm_0000000000000012"
WEEK_FLIGHTS_ID = "itm_0000000000000013"

TODAY_IDS = (REM_LANDING_ID, REM_PROPOSAL_ID)
EXCLUDED_TODAY_IDS = (
    REM_GYM_ID,
    REM_DOCTOR_ID,
    REM_HASSAN_ID,
    REM_FAMILY_ID,
    REM_STANDUP_ID,
)
REFLECTION_IDS = (WEEK_PRICING_ID, WEEK_COFFEE_ID, WEEK_EXPENSES_ID, WEEK_REVIEW_ID)
REFLECTION_EXCLUDED_IDS = (
    WEEK_GYM_ID,
    WEEK_STANDUP_ID,
    WEEK_DOCTOR_ID,
    WEEK_INVOICE_ID,
    WEEK_PROPOSAL_ID,
    WEEK_LANDING_ID,
    WEEK_FAMILY_ID,
    WEEK_FLIGHTS_ID,
)


def progress_memory() -> str:
    return f"""\
{REM_GYM_ID} | task | cancelled | Hit the gym
  history: created 2026-11-10 09:00; carried 2026-11-11, 2026-11-12, 2026-11-13; cancelled 2026-11-14 10:00
{REM_LANDING_ID} | task | todo | Finalize landing copy
  history: created 2026-11-10 12:00; carried 2026-11-11, 2026-11-12, 2026-11-13, 2026-11-14
{REM_DOCTOR_ID} | task | completed | Call the doctor
  history: created 2026-11-11 12:00; completed 2026-11-14 09:15
{REM_FAMILY_ID} | event | todo | Family meeting | start 2026-11-15T17:00:00+00:00
  history: created 2026-11-13 10:35; rescheduled to Sunday 17:00
{REM_HASSAN_ID} | event | completed | Meet Hassan | start 2026-11-14T15:00:00+00:00 | end 2026-11-14T16:00:00+00:00
  history: created 2026-11-13 10:40; completed 2026-11-14 16:05
{REM_PROPOSAL_ID} | task | in_progress | Send proposal
  history: created 2026-11-10 10:00; carried 2026-11-11, 2026-11-12, 2026-11-13, 2026-11-14; started 2026-11-13 14:00
{REM_STANDUP_ID} | event | todo | Team standup | start 2026-11-14T11:00:00+00:00 | end 2026-11-14T11:30:00+00:00
  history: created 2026-11-13 18:00"""


def _state_01() -> str:
    return render_interaction_state(MSG_01, "(none)", progress_memory(), REM_CLOCK)


def progress_memory_02() -> str:
    return f"""\
{WEEK_PRICING_ID} | task | completed | Ship pricing page
  history: created 2026-10-28 11:00; carried 2026-10-29, 2026-10-30, 2026-10-31, 2026-11-01, 2026-11-02, 2026-11-03, 2026-11-04; completed 2026-11-05 18:40
{WEEK_COFFEE_ID} | event | completed | Investor coffee | start 2026-11-04T10:00:00+00:00 | end 2026-11-04T11:00:00+00:00
  history: created 2026-11-02 09:15; completed 2026-11-04 11:05
{WEEK_EXPENSES_ID} | task | completed | File expenses
  history: created 2026-11-03 08:30; completed 2026-11-07 16:20
{WEEK_REVIEW_ID} | task | completed | Write weekly review
  history: created 2026-11-07 17:00; completed 2026-11-08 19:10
{WEEK_GYM_ID} | task | cancelled | Hit the gym
  history: created 2026-11-02 07:00; carried 2026-11-03, 2026-11-04, 2026-11-05; cancelled 2026-11-06 09:00
{WEEK_STANDUP_ID} | event | todo | Weekly standup | start 2026-11-05T11:00:00+00:00 | end 2026-11-05T11:30:00+00:00
  history: created 2026-11-03 18:00
{WEEK_DOCTOR_ID} | task | completed | Call the doctor
  history: created 2026-10-27 12:00; completed 2026-10-30 09:15
{WEEK_INVOICE_ID} | task | completed | Send invoice
  history: created 2026-11-08 09:00; completed 2026-11-09 10:30
{WEEK_PROPOSAL_ID} | task | completed | Send proposal
  history: created 2026-10-26 10:00; carried through 2026-11-10; completed 2026-11-11 14:00
{WEEK_LANDING_ID} | task | in_progress | Finalize landing copy
  history: created 2026-10-26 12:00; carried 2026-11-02, 2026-11-03, 2026-11-04, 2026-11-05, 2026-11-06, 2026-11-07, 2026-11-08, 2026-11-09, 2026-11-10, 2026-11-11, 2026-11-12, 2026-11-13, 2026-11-14; started 2026-11-10 09:00
{WEEK_FAMILY_ID} | event | todo | Family meeting | start 2026-11-14T17:00:00+00:00
  history: created 2026-11-12 10:20
{WEEK_FLIGHTS_ID} | task | completed | Book flights
  history: created 2026-11-12 16:00; completed 2026-11-13 09:10"""


def _state_02() -> str:
    return render_interaction_state(MSG_02, "(none)", progress_memory_02(), REM_CLOCK_02)


def golden_decision_01() -> Dict[str, Any]:
    """Passing Remembering 01: today's open inventory, no writes."""
    return {
        "judge": {
            "understanding": {
                "continuity": None,
                "message_meaning_summary": (
                    "Founder asks what is on the plate today."
                ),
                "responsibilities": ["testify"],
                "responsibilities_reason": (
                    "This is a question about recorded progress, not a work-state report."
                ),
                "requested_period": {
                    "start": REM_TODAY,
                    "end": REM_TODAY,
                    "reason": (
                        "Today is Saturday 14 November 2026. The founder asked about today."
                    ),
                },
            },
            "evidence": {
                "record_findings": [
                    {
                        "piece_of_work": "Finalize landing copy",
                        "match_status": "existing",
                        "item_id": REM_LANDING_ID,
                        "finding": "Open undated task; include in today's inventory.",
                    },
                    {
                        "piece_of_work": "Send proposal",
                        "match_status": "existing",
                        "item_id": REM_PROPOSAL_ID,
                        "finding": "Open undated work; include in today's inventory.",
                    },
                    {
                        "piece_of_work": "Team standup",
                        "match_status": "existing",
                        "item_id": REM_STANDUP_ID,
                        "finding": "Dated today; include even though 11:00 has passed.",
                    },
                ],
                "uncertainties": [],
            },
            "decision": {
                "required_actions": [
                    {
                        "action": "testify",
                        "item_id": None,
                        "piece_of_work": None,
                        "reason": "Founder asked for today's recorded work.",
                    }
                ]
            },
        },
        "plan": {"tool_calls": []},
        "say": {
            "types": ["testimony"],
            "text": "Today you have:",
            "testimony": {
                "aim": "What remains to be dealt with today.",
                "purpose_reason": (
                    "The founder asked what is on the plate today, "
                    "which is recovering present remaining work."
                ),
                "view": "inventory",
                "view_reason": (
                    "Inventory shows remaining work: landing copy and the proposal."
                ),
                "order": "priority",
                "scope": {"start": REM_TODAY, "end": REM_TODAY},
                "scope_reason": (
                    "Today is Saturday 14 November 2026. The founder asked what is on "
                    "the plate today, so the period is that day."
                ),
                "item_ids": [REM_LANDING_ID, REM_PROPOSAL_ID],
                "item_ids_reason": (
                    "Landing copy and the proposal are open undated work "
                    "that still remains to be dealt with."
                ),
                "omitted_ids": [
                    REM_GYM_ID,
                    REM_DOCTOR_ID,
                    REM_HASSAN_ID,
                    REM_FAMILY_ID,
                    REM_STANDUP_ID,
                ],
                "omitted_ids_reason": (
                    "Gym is cancelled, doctor and Hassan are completed, "
                    "the family meeting is tomorrow, and standup is an event "
                    "whose 11:00 occurrence has already passed."
                ),
            },
        },
    }


def golden_decision_02() -> Dict[str, Any]:
    """Passing Remembering 02: last week's recorded completions, no writes."""
    return {
        "judge": {
            "understanding": {
                "continuity": None,
                "message_meaning_summary": (
                    "Founder asks what they got done last week."
                ),
                "responsibilities": ["testify"],
                "responsibilities_reason": (
                    "This is a question about recorded progress, not a work-state report."
                ),
                "requested_period": {
                    "start": LAST_WEEK_START,
                    "end": LAST_WEEK_END,
                    "reason": (
                        "Today is Saturday 14 November 2026. Last week is the previous "
                        "Monday-Sunday calendar week: 2 November through 8 November, "
                        "not this week (9-15 November)."
                    ),
                },
            },
            "evidence": {
                "record_findings": [
                    {
                        "piece_of_work": "Ship pricing page",
                        "match_status": "existing",
                        "item_id": WEEK_PRICING_ID,
                        "finding": "Completed last Wednesday 5 November.",
                    },
                    {
                        "piece_of_work": "Investor coffee",
                        "match_status": "existing",
                        "item_id": WEEK_COFFEE_ID,
                        "finding": "Completed last Tuesday after the 10:00 meeting.",
                    },
                    {
                        "piece_of_work": "File expenses",
                        "match_status": "existing",
                        "item_id": WEEK_EXPENSES_ID,
                        "finding": "Completed last Saturday 7 November.",
                    },
                    {
                        "piece_of_work": "Write weekly review",
                        "match_status": "existing",
                        "item_id": WEEK_REVIEW_ID,
                        "finding": "Completed last Sunday 8 November, the last day of last week.",
                    },
                    {
                        "piece_of_work": "Send invoice",
                        "match_status": "existing",
                        "item_id": WEEK_INVOICE_ID,
                        "finding": "Completed this Monday 9 November; not last week.",
                    },
                    {
                        "piece_of_work": "Send proposal",
                        "match_status": "existing",
                        "item_id": WEEK_PROPOSAL_ID,
                        "finding": "Completed this Wednesday 11 November; not last week.",
                    },
                    {
                        "piece_of_work": "Book flights",
                        "match_status": "existing",
                        "item_id": WEEK_FLIGHTS_ID,
                        "finding": "Completed yesterday; not last week.",
                    },
                    {
                        "piece_of_work": "Weekly standup",
                        "match_status": "existing",
                        "item_id": WEEK_STANDUP_ID,
                        "finding": (
                            "Still todo. Last week's 11:00 passing is not a completion."
                        ),
                    },
                ],
                "uncertainties": [],
            },
            "decision": {
                "required_actions": [
                    {
                        "action": "testify",
                        "item_id": None,
                        "piece_of_work": None,
                        "reason": "Founder asked what they got done last week.",
                    }
                ]
            },
        },
        "plan": {"tool_calls": []},
        "say": {
            "types": ["testimony"],
            "text": "Here's what you got done last week:",
            "testimony": {
                "aim": "What the founder completed last week.",
                "purpose_reason": (
                    "The founder asked what they got done last week, "
                    "which is reconstructing recorded completions in that period."
                ),
                "view": "outcomes",
                "view_reason": (
                    "Outcomes show work that resulted last week: pricing page, "
                    "investor coffee, expenses, and the weekly review."
                ),
                "order": "chronological",
                "scope": {"start": LAST_WEEK_START, "end": LAST_WEEK_END},
                "scope_reason": (
                    "Today is Saturday 14 November 2026. Last week is the previous "
                    "Monday-Sunday calendar week: 2 November through 8 November, "
                    "not this week (9-15 November)."
                ),
                "item_ids": [
                    WEEK_COFFEE_ID,
                    WEEK_PRICING_ID,
                    WEEK_EXPENSES_ID,
                    WEEK_REVIEW_ID,
                ],
                "item_ids_reason": (
                    "Investor coffee, the pricing page, expenses, and the weekly review "
                    "were completed between Monday 2 November and Sunday 8 November."
                ),
                "omitted_ids": [
                    WEEK_GYM_ID,
                    WEEK_STANDUP_ID,
                    WEEK_DOCTOR_ID,
                    WEEK_INVOICE_ID,
                    WEEK_PROPOSAL_ID,
                    WEEK_LANDING_ID,
                    WEEK_FAMILY_ID,
                    WEEK_FLIGHTS_ID,
                ],
                "omitted_ids_reason": (
                    "Gym was cancelled, standup was never completed, the doctor call "
                    "is from the week before, the invoice, proposal and flights were "
                    "completed this week, landing copy is still open, and the family "
                    "meeting is today."
                ),
            },
        },
    }


SCENARIO_01 = Scenario(
    id="remembering-01",
    title="Remembering / Scenario 01 — Day alignment",
    interaction_state=_state_01(),
    golden=golden_decision_01,
    family="remembering",
)
SCENARIO_02 = Scenario(
    id="remembering-02",
    title="Remembering / Scenario 02 — Last-week reflection",
    interaction_state=_state_02(),
    golden=golden_decision_02,
    family="remembering",
)
SCENARIOS: Dict[str, Scenario] = {
    SCENARIO_01.id: SCENARIO_01,
    SCENARIO_02.id: SCENARIO_02,
}
