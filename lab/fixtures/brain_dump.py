"""Brain-dump fixtures and schema-valid golden decisions for mock inference."""

from __future__ import annotations

from typing import Any, Dict

from lab.fixtures.common import Scenario, render_interaction_state, turn

ACME_ID = "itm_0000000000000001"
GYM_ID = "itm_0000000000000002"
LANDING_ID = "itm_0000000000000003"
LOGIN_ID = "itm_0000000000000004"
FAMILY_ID = "itm_0000000000000005"
ANGEL_ID = "itm_0000000000000006"
EXPECTED_DUE = "2026-11-07T23:59:59+00:00"
FAMILY_START = "2026-11-06T19:00:00+00:00"
ANGEL_START = "2026-11-06T15:00:00+00:00"
FAMILY_MOVED = "2026-11-07T17:00:00+00:00"
VEE_S01_REPLY = (
    "Recorded. I moved 'Chase Acme' to tomorrow (Nov 7) and added the three new tasks: "
    "'Hit the gym', 'Finalize landing copy', and 'Fix the login bug'."
)
VEE_S02_REPLY = (
    "I've noted you want to add a 'family meeting' for today. "
    "To record this accurately in the progress memory, could you please "
    "provide the specific start time for the meeting?"
)
VEE_S03_REPLY = (
    "Recorded. I've added the 'Family meeting' for today at 7pm."
)
VEE_S04_REPLY = (
    "Recorded. I've added the 'Angel investor meeting' for today at 3 PM."
)
VEE_S05_REPLY = (
    "Recorded. I have updated the progress memory:\n"
    "\n"
    "1.  **Angel investor meeting**: Marked as **completed**.\n"
    "2.  **Hit the gym**: Marked as **cancelled**.\n"
    "3.  **Fix the login bug**: Marked as **completed**.\n"
    "4.  **Family meeting**: Rescheduled to **tomorrow (Nov 7) at 5 PM**.\n"
    "\n"
    "Is there anything else you'd like to add or adjust?"
)
VEE_S06_REPLY = (
    "The family meeting is recorded for 5pm tomorrow. Your brother said 3pm "
    "and your sister said 6pm. You haven't confirmed yet — keep 5pm, "
    "change to 3pm, or change to 6pm?"
)
VEE_S06_HELD_REPLY = (
    "The family meeting remains recorded for 5pm tomorrow. "
    "Brother said 3pm and sister said 6pm; neither is confirmed."
)
MSG_01 = (
    "move the Acme chase to tomorrow — also need to hit the gym, "
    "finalize landing copy, and fix the login bug"
)
MSG_02 = "add family meeting today"
MSG_03 = "7pm"
MSG_04 = "i got a meeting with an Angel investor today at 3 — i also need to fix that login bug"
MSG_05 = (
    "done with the angel investor meeting — cancel the gym, "
    "the login bug is fixed, move family meeting to tomorrow at 5pm"
)
MSG_06 = (
    "My brother said the family meeting is at 3 tomorrow, but my sister said "
    "it's at 6. I haven't confirmed which one is right yet"
)
MSG_07 = "how are you"

NEW_TASKS = (
    {"key": "gym", "title": "Hit the gym", "needles": ("gym",)},
    {"key": "landing", "title": "Finalize landing copy", "needles": ("landing",)},
    {"key": "login", "title": "Fix the login bug", "needles": ("login",)},
)

def _progress_start() -> str:
    return f"{ACME_ID} | task | todo | Chase Acme overdue invoice"


def _progress_after_01() -> str:
    return f"""\
{ACME_ID} | task | todo | Chase Acme overdue invoice | due {EXPECTED_DUE}
{GYM_ID} | task | todo | Hit the gym
{LANDING_ID} | task | todo | Finalize landing copy
{LOGIN_ID} | task | todo | Fix the login bug"""


def _progress_after_03() -> str:
    return (
        f"{_progress_after_01()}\n"
        f"{FAMILY_ID} | event | todo | Family meeting | start {FAMILY_START}"
    )


def _progress_after_04() -> str:
    return (
        f"{_progress_after_03()}\n"
        f"{ANGEL_ID} | event | todo | Angel investor meeting | start {ANGEL_START}"
    )


def _progress_after_05() -> str:
    return f"""\
{ACME_ID} | task | todo | Chase Acme overdue invoice | due {EXPECTED_DUE}
{GYM_ID} | task | cancelled | Hit the gym
{LANDING_ID} | task | todo | Finalize landing copy
{LOGIN_ID} | task | completed | Fix the login bug
{FAMILY_ID} | event | todo | Family meeting | start {FAMILY_MOVED}
{ANGEL_ID} | event | completed | Angel investor meeting | start {ANGEL_START}"""


def _recent_through_01() -> str:
    return turn(MSG_01, VEE_S01_REPLY)


def _recent_through_02() -> str:
    return f"{_recent_through_01()}\n{turn(MSG_02, VEE_S02_REPLY)}"


def _recent_through_03() -> str:
    return f"{_recent_through_02()}\n{turn(MSG_03, VEE_S03_REPLY)}"


def _recent_through_04() -> str:
    return f"{_recent_through_03()}\n{turn(MSG_04, VEE_S04_REPLY)}"


def _recent_through_05() -> str:
    return f"{_recent_through_04()}\n{turn(MSG_05, VEE_S05_REPLY)}"


def _recent_through_06() -> str:
    """Silence turn: last 10 speaker turns, so Scenario 01 has dropped off."""
    return (
        f"{turn(MSG_02, VEE_S02_REPLY)}\n"
        f"{turn(MSG_03, VEE_S03_REPLY)}\n"
        f"{turn(MSG_04, VEE_S04_REPLY)}\n"
        f"{turn(MSG_05, VEE_S05_REPLY)}\n"
        f"{turn(MSG_06, VEE_S06_HELD_REPLY)}"
    )


def _state_01() -> str:
    return render_interaction_state(MSG_01, "(none)", _progress_start(), "10:30, 6 November 2026")


def _state_02() -> str:
    return render_interaction_state(MSG_02, _recent_through_01(), _progress_after_01(), "10:31, 6 November 2026")


def _state_03() -> str:
    return render_interaction_state(MSG_03, _recent_through_02(), _progress_after_01(), "10:32, 6 November 2026")


def _state_04() -> str:
    return render_interaction_state(MSG_04, _recent_through_03(), _progress_after_03(), "10:40, 6 November 2026")


def _state_05() -> str:
    return render_interaction_state(MSG_05, _recent_through_04(), _progress_after_04(), "21:16, 6 November 2026")


def _state_06() -> str:
    return render_interaction_state(MSG_06, _recent_through_05(), _progress_after_05(), "21:20, 6 November 2026")


def _state_07() -> str:
    return render_interaction_state(MSG_07, _recent_through_06(), _progress_after_05(), "21:21, 6 November 2026")


def golden_decision() -> Dict[str, Any]:
    """Passing Scenario 01 judge/plan/say object. Tools are data only."""
    return {
        "judge": {
            "understanding": {
                "continuity": None,
                "message_meaning_summary": (
                    "Founder reports moving the Acme chase to tomorrow and adding "
                    "gym, landing copy, and login-bug work."
                ),
                "responsibilities": ["witness"],
                "responsibilities_reason": (
                    "The founder is reporting work-state changes and is not asking "
                    "for an account of progress."
                ),
            },
            "evidence": {
                "record_findings": [
                    {
                        "piece_of_work": "Acme chase",
                        "match_status": "existing",
                        "item_id": ACME_ID,
                        "finding": "Matches Chase Acme overdue invoice; bump due date to tomorrow.",
                    },
                    {
                        "piece_of_work": "Hit the gym",
                        "match_status": "new",
                        "item_id": None,
                        "finding": "No existing gym item.",
                    },
                    {
                        "piece_of_work": "Finalize landing copy",
                        "match_status": "new",
                        "item_id": None,
                        "finding": "No existing landing copy item.",
                    },
                    {
                        "piece_of_work": "Fix the login bug",
                        "match_status": "new",
                        "item_id": None,
                        "finding": "No existing login bug item.",
                    },
                ],
                "uncertainties": [],
            },
            "decision": {
                "required_actions": [
                    {
                        "action": "update",
                        "item_id": ACME_ID,
                        "piece_of_work": None,
                        "reason": "Move Acme chase due date to tomorrow.",
                    },
                    {
                        "action": "create",
                        "item_id": None,
                        "piece_of_work": "Hit the gym",
                        "reason": "New task reported.",
                    },
                    {
                        "action": "create",
                        "item_id": None,
                        "piece_of_work": "Finalize landing copy",
                        "reason": "New task reported.",
                    },
                    {
                        "action": "create",
                        "item_id": None,
                        "piece_of_work": "Fix the login bug",
                        "reason": "New task reported.",
                    },
                ]
            },
        },
        "plan": {
            "tool_calls": [
                {
                    "name": "update_item",
                    "args": {"id": ACME_ID, "due_at": EXPECTED_DUE},
                },
                {"name": "add_item", "args": {"title": "Hit the gym", "type": "task"}},
                {
                    "name": "add_item",
                    "args": {"title": "Finalize landing copy", "type": "task"},
                },
                {
                    "name": "add_item",
                    "args": {"title": "Fix the login bug", "type": "task"},
                },
            ]
        },
        "say": {
            "types": ["confirmation"],
            "text": "Recorded:",
            "testimony": None,
        },
    }


def golden_decision_02() -> Dict[str, Any]:
    """Passing Scenario 02: event reported without a start time, so clarify, do not write."""
    return {
        "judge": {
            "understanding": {
                "continuity": (
                    "Follows the previous dump that moved Acme and added gym, "
                    "landing copy, and the login bug."
                ),
                "message_meaning_summary": (
                    "Founder wants a family meeting added today; no start time was given."
                ),
                "responsibilities": ["witness"],
                "responsibilities_reason": (
                    "The founder is reporting new work, not asking for an account of progress."
                ),
            },
            "evidence": {
                "record_findings": [
                    {
                        "piece_of_work": "Family meeting",
                        "match_status": "new",
                        "item_id": None,
                        "finding": (
                            "No existing family-meeting record. This is an event; "
                            "start time is not established."
                        ),
                    }
                ],
                "uncertainties": [
                    {
                        "piece_of_work": "Family meeting",
                        "type": "missing_information",
                        "candidate_ids": [],
                        "question": "What time is the family meeting today?",
                    }
                ],
            },
            "decision": {
                "required_actions": [
                    {
                        "action": "clarify",
                        "item_id": None,
                        "piece_of_work": "Family meeting",
                        "reason": "Events require start_at; only the day was reported.",
                    }
                ]
            },
        },
        "plan": {"tool_calls": []},
        "say": {
            "types": ["clarification"],
            "text": "What time is the family meeting today?",
            "testimony": None,
        },
    }


def golden_decision_03() -> Dict[str, Any]:
    """Passing Scenario 03: '7pm' resolves the family-meeting start time."""
    return {
        "judge": {
            "understanding": {
                "continuity": (
                    "The founder is answering Vee's question about the start time "
                    "of today's family meeting."
                ),
                "message_meaning_summary": (
                    "The family meeting today starts at 7pm."
                ),
                "responsibilities": ["witness"],
                "responsibilities_reason": (
                    "The founder is supplying the missing start time for reported work, "
                    "not asking for an account of progress."
                ),
            },
            "evidence": {
                "record_findings": [
                    {
                        "piece_of_work": "Family meeting",
                        "match_status": "new",
                        "item_id": None,
                        "finding": (
                            "No existing family-meeting record. Start time is now "
                            "established as 19:00 today."
                        ),
                    }
                ],
                "uncertainties": [],
            },
            "decision": {
                "required_actions": [
                    {
                        "action": "create",
                        "item_id": None,
                        "piece_of_work": "Family meeting",
                        "reason": "New event with an established start time.",
                    }
                ]
            },
        },
        "plan": {
            "tool_calls": [
                {
                    "name": "add_item",
                    "args": {
                        "title": "Family meeting",
                        "type": "event",
                        "start_at": FAMILY_START,
                    },
                }
            ]
        },
        "say": {
            "types": ["confirmation"],
            "text": "Recorded:",
            "testimony": None,
        },
    }


def golden_decision_04() -> Dict[str, Any]:
    """Passing Scenario 04: new angel-investor event; login bug is already in Progress Memory."""
    return {
        "judge": {
            "understanding": {
                "continuity": (
                    "Follows the family-meeting add; founder now reports an angel-investor "
                    "meeting and repeats the login bug."
                ),
                "message_meaning_summary": (
                    "Add a meeting with an angel investor at 3pm today; "
                    "the login bug is already recorded."
                ),
                "responsibilities": ["witness"],
                "responsibilities_reason": (
                    "The founder is reporting work-state changes, not asking for an account of progress."
                ),
            },
            "evidence": {
                "record_findings": [
                    {
                        "piece_of_work": "Angel investor meeting",
                        "match_status": "new",
                        "item_id": None,
                        "finding": (
                            "No existing angel-investor meeting. Event start is 15:00 today."
                        ),
                    },
                    {
                        "piece_of_work": "Fix the login bug",
                        "match_status": "existing",
                        "item_id": LOGIN_ID,
                        "finding": "Already recorded as Fix the login bug; no write.",
                    },
                ],
                "uncertainties": [],
            },
            "decision": {
                "required_actions": [
                    {
                        "action": "create",
                        "item_id": None,
                        "piece_of_work": "Angel investor meeting",
                        "reason": "New event with an established start time.",
                    }
                ]
            },
        },
        "plan": {
            "tool_calls": [
                {
                    "name": "add_item",
                    "args": {
                        "title": "Angel investor meeting",
                        "type": "event",
                        "start_at": ANGEL_START,
                    },
                }
            ]
        },
        "say": {
            "types": ["confirmation"],
            "text": "Recorded:",
            "testimony": None,
        },
    }


def golden_decision_05() -> Dict[str, Any]:
    """Passing Scenario 05: complete the angel-investor meeting plus three other updates."""
    return {
        "judge": {
            "understanding": {
                "continuity": (
                    "Follows the angel-investor add. The founder reports completing "
                    "that meeting and three more changes."
                ),
                "message_meaning_summary": (
                    "Complete the angel-investor meeting and the login bug, cancel the gym, "
                    "and move the family meeting to tomorrow at 5pm."
                ),
                "responsibilities": ["witness"],
                "responsibilities_reason": (
                    "The founder is reporting work-state changes, not asking for an account of progress."
                ),
            },
            "evidence": {
                "record_findings": [
                    {
                        "piece_of_work": "Angel investor meeting",
                        "match_status": "existing",
                        "item_id": ANGEL_ID,
                        "finding": "This is the completed meeting.",
                    },
                    {
                        "piece_of_work": "Hit the gym",
                        "match_status": "existing",
                        "item_id": GYM_ID,
                        "finding": "Cancel this task.",
                    },
                    {
                        "piece_of_work": "Fix the login bug",
                        "match_status": "existing",
                        "item_id": LOGIN_ID,
                        "finding": "Mark completed.",
                    },
                    {
                        "piece_of_work": "Family meeting",
                        "match_status": "existing",
                        "item_id": FAMILY_ID,
                        "finding": "Move start to tomorrow 17:00.",
                    },
                ],
                "uncertainties": [],
            },
            "decision": {
                "required_actions": [
                    {
                        "action": "update",
                        "item_id": ANGEL_ID,
                        "piece_of_work": None,
                        "reason": "Meeting completed.",
                    },
                    {
                        "action": "update",
                        "item_id": GYM_ID,
                        "piece_of_work": None,
                        "reason": "Gym cancelled.",
                    },
                    {
                        "action": "update",
                        "item_id": LOGIN_ID,
                        "piece_of_work": None,
                        "reason": "Login bug is fixed.",
                    },
                    {
                        "action": "update",
                        "item_id": FAMILY_ID,
                        "piece_of_work": None,
                        "reason": "Move to tomorrow at 5pm.",
                    },
                ]
            },
        },
        "plan": {
            "tool_calls": [
                {
                    "name": "update_item",
                    "args": {"id": ANGEL_ID, "status": "completed"},
                },
                {
                    "name": "update_item",
                    "args": {"id": GYM_ID, "status": "cancelled"},
                },
                {
                    "name": "update_item",
                    "args": {"id": LOGIN_ID, "status": "completed"},
                },
                {
                    "name": "update_item",
                    "args": {"id": FAMILY_ID, "start_at": FAMILY_MOVED},
                },
            ]
        },
        "say": {
            "types": ["confirmation"],
            "text": "Recorded:",
            "testimony": None,
        },
    }


def golden_decision_06() -> Dict[str, Any]:
    """Passing Scenario 06: brother 3pm / sister 6pm conflict with recorded 5pm; clarify."""
    return {
        "judge": {
            "understanding": {
                "continuity": (
                    "Follows the family meeting being moved to tomorrow at 5pm. "
                    "The founder now reports two unconfirmed times for that same meeting."
                ),
                "message_meaning_summary": (
                    "Brother says 3pm tomorrow, sister says 6pm; neither is confirmed, "
                    "and both disagree with the recorded 5pm."
                ),
                "responsibilities": ["witness"],
                "responsibilities_reason": (
                    "The founder is reporting conflicting times for recorded work, "
                    "not asking for an account of progress."
                ),
            },
            "evidence": {
                "record_findings": [
                    {
                        "piece_of_work": "Family meeting",
                        "match_status": "existing",
                        "item_id": FAMILY_ID,
                        "finding": (
                            "Recorded start is tomorrow 17:00. Brother said 3pm; "
                            "sister said 6pm; founder has not confirmed which is right."
                        ),
                    }
                ],
                "uncertainties": [
                    {
                        "piece_of_work": "Family meeting",
                        "type": "conflicting_facts",
                        "candidate_ids": [FAMILY_ID],
                        "question": (
                            "Recorded 5pm, brother 3pm, sister 6pm — which time should be kept?"
                        ),
                    }
                ],
            },
            "decision": {
                "required_actions": [
                    {
                        "action": "clarify",
                        "item_id": FAMILY_ID,
                        "piece_of_work": "Family meeting",
                        "reason": "Three times cannot all be written; founder has not chosen.",
                    }
                ]
            },
        },
        "plan": {"tool_calls": []},
        "say": {
            "types": ["clarification"],
            "text": VEE_S06_REPLY,
            "testimony": None,
        },
    }


def golden_decision_07() -> Dict[str, Any]:
    """Passing Scenario 07: greeting is not a progress-memory turn; stay silent."""
    return {
        "judge": {
            "understanding": {
                "continuity": (
                    "Vee already noted the unconfirmed 3pm and 6pm claims and "
                    "left the family meeting at 5pm. This greeting does not "
                    "report work or answer anything."
                ),
                "message_meaning_summary": "No progress-memory request.",
                "responsibilities": [],
                "responsibilities_reason": (
                    "The founder is greeting Vee, not reporting work or asking "
                    "for an account of progress. An unresolved earlier question "
                    "does not create a responsibility this turn."
                ),
            },
            "evidence": {
                "record_findings": [],
                "uncertainties": [],
            },
            "decision": {"required_actions": []},
        },
        "plan": {"tool_calls": []},
        "say": {
            "types": ["silence"],
            "text": "",
            "testimony": None,
        },
    }


SCENARIO_01 = Scenario(
    id="brain-dump-01",
    title="Brain-dump / Scenario 01",
    interaction_state=_state_01(),
    golden=golden_decision,
    family="brain-dump",
)
SCENARIO_02 = Scenario(
    id="brain-dump-02",
    title="Brain-dump / Scenario 02",
    interaction_state=_state_02(),
    golden=golden_decision_02,
    family="brain-dump",
)
SCENARIO_03 = Scenario(
    id="brain-dump-03",
    title="Brain-dump / Scenario 03",
    interaction_state=_state_03(),
    golden=golden_decision_03,
    family="brain-dump",
)
SCENARIO_04 = Scenario(
    id="brain-dump-04",
    title="Brain-dump / Scenario 04",
    interaction_state=_state_04(),
    golden=golden_decision_04,
    family="brain-dump",
)
SCENARIO_05 = Scenario(
    id="brain-dump-05",
    title="Brain-dump / Scenario 05",
    interaction_state=_state_05(),
    golden=golden_decision_05,
    family="brain-dump",
)
SCENARIO_06 = Scenario(
    id="brain-dump-06",
    title="Brain-dump / Scenario 06",
    interaction_state=_state_06(),
    golden=golden_decision_06,
    family="brain-dump",
)
SCENARIO_07 = Scenario(
    id="brain-dump-07",
    title="Brain-dump / Scenario 07",
    interaction_state=_state_07(),
    golden=golden_decision_07,
    family="brain-dump",
)
SCENARIOS: Dict[str, Scenario] = {
    SCENARIO_01.id: SCENARIO_01,
    SCENARIO_02.id: SCENARIO_02,
    SCENARIO_03.id: SCENARIO_03,
    SCENARIO_04.id: SCENARIO_04,
    SCENARIO_05.id: SCENARIO_05,
    SCENARIO_06.id: SCENARIO_06,
    SCENARIO_07.id: SCENARIO_07,
}
SCENARIO_ID = SCENARIO_01.id
SCENARIO_TITLE = SCENARIO_01.title
INTERACTION_STATE = SCENARIO_01.interaction_state
