"""Brain-dump scenario evaluators. Never executes tools."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from lab.fixtures.brain_dump import (
    ACME_ID,
    ANGEL_ID,
    ANGEL_START,
    EXPECTED_DUE,
    FAMILY_ID,
    FAMILY_MOVED,
    FAMILY_START,
    GYM_ID,
    LOGIN_ID,
    NEW_TASKS,
)
from lab.scoring.common import (
    FAIL,
    PASS,
    VARIANT,
    actions as _actions,
    calls as _calls,
    check as _check,
    eval_plan_empty as _eval_plan_empty,
    eval_say_hygiene as _eval_say_hygiene,
    finding_for as _finding_for,
    findings as _findings,
    has_needles as _has_needles,
    normalize_plan as _normalize_plan,
    parse_dt as _parse_dt,
    say as _say,
    start_matches as _start_matches,
)

def _due_matches(value: Any) -> bool:
    expected = _parse_dt(EXPECTED_DUE)
    actual = _parse_dt(value)
    return expected is not None and actual is not None and actual == expected


def _eval_judge_02(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    understanding = (data.get("judge") or {}).get("understanding") or {}
    responsibilities = understanding.get("responsibilities") or []
    findings = _findings(data)
    actions = _actions(data)
    uncertainties = ((data.get("judge") or {}).get("evidence") or {}).get("uncertainties") or []
    family = _finding_for(("family",), findings) or _finding_for(("meeting",), findings)
    clarify = next((a for a in actions if a.get("action") == "clarify"), None)
    create = [a for a in actions if a.get("action") == "create"]
    missing = [
        u
        for u in uncertainties
        if isinstance(u, dict) and u.get("type") == "missing_information"
    ]
    asks_time = any(
        _has_needles(u.get("question"), ("time",))
        or _has_needles(u.get("piece_of_work"), ("family", "meeting"))
        for u in missing
    )
    family_new = (family or {}).get("match_status") == "new"
    checks = [
        _check(
            "responsibility",
            "Witnessing, or witnessing and testifying",
            PASS if "witness" in responsibilities else FAIL,
            [["witness"], ["witness", "testify"]],
            responsibilities,
            "Message reports new work. responsibilities may be witness only, or both.",
        ),
        _check(
            "family_new",
            "Family meeting is new work",
            PASS if family_new else FAIL,
            {"match_status": "new"},
            family,
            "Family meeting must be identified as new, not an existing item.",
        ),
        _check(
            "missing_start",
            "Start time is missing information",
            PASS if missing and asks_time else FAIL,
            {"type": "missing_information", "about": "start time"},
            missing,
            "Events require start_at. Only the day was reported, so this is missing_information.",
        ),
        _check(
            "clarify_not_create",
            "Clarify instead of creating",
            PASS if clarify and not create else FAIL,
            {"action": "clarify", "no_create": True},
            {"clarify": clarify, "creates": create},
            "Do not add the event until a start time is established.",
        ),
    ]
    invented = [
        row.get("piece_of_work")
        for row in findings
        if row.get("match_status") == "new"
        and not (
            _has_needles(row.get("piece_of_work"), ("family",))
            or _has_needles(row.get("piece_of_work"), ("meeting",))
        )
    ]
    invented_actions = [
        a.get("action")
        for a in actions
        if a.get("action") not in {"clarify"}
    ]
    checks.append(
        _check(
            "no_invention",
            "No invented facts or unsupported writes",
            PASS if not invented and not invented_actions else FAIL,
            "Family meeting only; clarify only",
            {"invented_findings": invented, "invented_actions": invented_actions},
            "Do not treat other Progress Memory items as the family meeting, and do not write yet.",
        )
    )
    return checks


def _eval_plan_02(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], float, float, float, List[str]]:
    calls = [c for c in _calls(data) if isinstance(c, dict)]
    extras = calls
    checks = [
        _check(
            "no_tools",
            "No tool calls until start time is known",
            PASS if not extras else FAIL,
            [],
            [c.get("name") for c in extras],
            "add_item for an event requires start_at. Clarify instead of writing.",
        ),
        _check(
            "no_extra",
            "No unintended extra tool calls",
            PASS if not extras else FAIL,
            0,
            len(extras),
            "Scenario 02 expects an empty plan.",
        ),
    ]
    precision = 1.0 if not extras else 0.0
    recall = 1.0
    f1 = 1.0 if precision == 1.0 else 0.0
    checks.append(
        _check(
            "plan_f1",
            "Plan precision / recall",
            PASS if precision == 1 and recall == 1 else FAIL,
            {"precision": 1, "recall": 1, "f1": 1},
            {"precision": precision, "recall": recall, "f1": f1, "generated": len(calls)},
            "Zero tool calls is the correct plan.",
        )
    )
    return checks, precision, recall, f1, _normalize_plan(calls)


def _eval_say_02(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    say = _say(data)
    types = say.get("types") or []
    text = say.get("text") or ""
    testimony = say.get("testimony")
    type_ok = "clarification" in types and "confirmation" not in types and "testimony" not in types
    asks_time = "?" in text and (
        _has_needles(text, ("time",)) or _has_needles(text, ("when",))
    )
    checks = [
        _check(
            "response_type",
            "Clarification, not confirmation",
            PASS if type_ok else FAIL,
            ["clarification"],
            types,
            "Missing event start time must be asked; do not confirm a write.",
        ),
        _check(
            "asks_time",
            "Ask for the meeting time",
            PASS if asks_time else FAIL,
            "Question about time",
            text,
            "Say must ask when the family meeting is.",
        ),
    ]
    checks.extend(_eval_say_hygiene(text, testimony, allow_testimony=False))
    return checks


def _eval_judge_03(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    understanding = (data.get("judge") or {}).get("understanding") or {}
    responsibilities = understanding.get("responsibilities") or []
    findings = _findings(data)
    actions = _actions(data)
    uncertainties = ((data.get("judge") or {}).get("evidence") or {}).get("uncertainties") or []
    family = _finding_for(("family",), findings) or _finding_for(("meeting",), findings)
    create = next(
        (
            a
            for a in actions
            if a.get("action") == "create"
            and (
                _has_needles(a.get("piece_of_work"), ("family",))
                or _has_needles(a.get("piece_of_work"), ("meeting",))
            )
        ),
        None,
    )
    clarify = [a for a in actions if a.get("action") == "clarify"]
    still_missing = [
        u
        for u in uncertainties
        if isinstance(u, dict) and u.get("type") == "missing_information"
    ]
    family_new = (family or {}).get("match_status") == "new"
    checks = [
        _check(
            "responsibility",
            "Witnessing, or witnessing and testifying",
            PASS if "witness" in responsibilities else FAIL,
            [["witness"], ["witness", "testify"]],
            responsibilities,
            "The founder is completing a reported event. responsibilities may be witness only, or both.",
        ),
        _check(
            "family_new",
            "Family meeting is new work",
            PASS if family_new else FAIL,
            {"match_status": "new"},
            family,
            "Family meeting must stay new; it is not yet in Progress Memory.",
        ),
        _check(
            "time_resolved",
            "Start time is now established",
            PASS if not still_missing else FAIL,
            [],
            still_missing,
            "'7pm' answers the pending start-time question; do not keep missing_information.",
        ),
        _check(
            "create_not_clarify",
            "Create the event, do not clarify again",
            PASS if create and not clarify else FAIL,
            {"action": "create"},
            {"create": create, "clarify": clarify},
            "The missing start time is resolved, so the required action is create.",
        ),
    ]
    invented = [
        row.get("piece_of_work")
        for row in findings
        if row.get("match_status") == "new"
        and not (
            _has_needles(row.get("piece_of_work"), ("family",))
            or _has_needles(row.get("piece_of_work"), ("meeting",))
        )
    ]
    invented_actions = [
        a.get("action")
        for a in actions
        if a.get("action") not in {"create"}
    ]
    checks.append(
        _check(
            "no_invention",
            "No invented facts or extra actions",
            PASS if not invented and not invented_actions else FAIL,
            "Family meeting only; create only",
            {"invented_findings": invented, "invented_actions": invented_actions},
            "Do not create other work or keep asking for the time.",
        )
    )
    return checks


def _match_add_family_event(call: Dict[str, Any]) -> Tuple[bool, str]:
    if call.get("name") != "add_item":
        return False, "wrong tool"
    args = call.get("args") or {}
    if args.get("type") != "event":
        return False, f"type {args.get('type')!r} ≠ event"
    title = args.get("title")
    if not (
        _has_needles(title, ("family",))
        or _has_needles(title, ("meeting",))
    ):
        return False, f"title {title!r} does not match family meeting"
    if not _start_matches(args.get("start_at"), FAMILY_START):
        return False, f"start_at {args.get('start_at')!r} ≠ {FAMILY_START}"
    return True, "ok"


def _eval_plan_03(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], float, float, float, List[str]]:
    calls = [c for c in _calls(data) if isinstance(c, dict)]
    match = next((c for c in calls if _match_add_family_event(c)[0]), None)
    extras = [c for c in calls if c is not match]
    ok, why = (_match_add_family_event(match) if match else (False, "missing"))
    extra_args = {}
    if match:
        extra_args = {
            k: v
            for k, v in (match.get("args") or {}).items()
            if k not in {"title", "type", "start_at"}
        }
    if ok:
        status = VARIANT if extra_args else PASS
        expl = "add_item event Family meeting at 19:00 today."
        if extra_args:
            expl += f" Extra optional args accepted: {list(extra_args)}."
        correct = 1
    else:
        status = FAIL
        expl = f"Required add_item missing or wrong ({why})."
        correct = 0
    checks = [
        _check(
            "add_family_event",
            "Add family meeting event at 7pm",
            status,
            {"name": "add_item", "type": "event", "start_at": FAMILY_START},
            match,
            expl,
        ),
        _check(
            "no_extra",
            "No unintended extra tool calls",
            PASS if not extras else FAIL,
            0,
            len(extras),
            "Only the family-meeting add_item is expected."
            if not extras
            else f"Extra calls: {[c.get('name') for c in extras]}.",
        ),
    ]
    generated = len(calls)
    precision = (correct / generated) if generated else 0.0
    recall = correct / 1
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    checks.append(
        _check(
            "plan_f1",
            "Plan precision / recall",
            PASS if precision == 1 and recall == 1 else FAIL,
            {"precision": 1, "recall": 1, "f1": 1},
            {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "correct": correct,
                "generated": generated,
            },
            "One add_item event with start_at 2026-11-06T19:00:00+00:00.",
        )
    )
    return checks, precision, recall, f1, _normalize_plan(calls)


def _eval_judge_04(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    understanding = (data.get("judge") or {}).get("understanding") or {}
    responsibilities = understanding.get("responsibilities") or []
    findings = _findings(data)
    actions = _actions(data)
    uncertainties = ((data.get("judge") or {}).get("evidence") or {}).get("uncertainties") or []
    meeting = _finding_for(("angel",), findings) or _finding_for(("investor",), findings)
    still_missing = [
        u
        for u in uncertainties
        if isinstance(u, dict) and u.get("type") == "missing_information"
    ]
    create_meeting = next(
        (
            a
            for a in actions
            if a.get("action") == "create"
            and (
                _has_needles(a.get("piece_of_work"), ("angel",))
                or _has_needles(a.get("piece_of_work"), ("investor",))
            )
        ),
        None,
    )
    meeting_new = (meeting or {}).get("match_status") == "new"
    checks = [
        _check(
            "responsibility",
            "Witnessing, or witnessing and testifying",
            PASS if "witness" in responsibilities else FAIL,
            [["witness"], ["witness", "testify"]],
            responsibilities,
            "Message reports new work. responsibilities may be witness only, or both.",
        ),
        _check(
            "angel_new",
            "Angel-investor meeting is new work",
            PASS if meeting_new else FAIL,
            {"match_status": "new"},
            meeting,
            "The angel-investor meeting is not in Progress Memory and must not be treated as the family meeting.",
        ),
        _check(
            "time_known",
            "Meeting start time is established",
            PASS if not still_missing else FAIL,
            [],
            still_missing,
            "'today at 3' is enough for start_at; do not ask for the time.",
        ),
        _check(
            "create_angel",
            "Create the angel-investor meeting",
            PASS if create_meeting else FAIL,
            {"action": "create", "piece_of_work": "Angel investor meeting"},
            create_meeting,
            "The angel-investor event is new work with a known start time.",
        ),
    ]
    invented = [
        row.get("piece_of_work")
        for row in findings
        if row.get("match_status") == "new"
        and not _has_needles(row.get("piece_of_work"), ("angel",))
        and not _has_needles(row.get("piece_of_work"), ("investor",))
        and not _has_needles(row.get("piece_of_work"), ("login",))
    ]
    checks.append(
        _check(
            "no_invention",
            "No invented facts or extra new work",
            PASS if not invented else FAIL,
            "Angel-investor meeting only as new",
            invented,
            "Do not treat family meeting, gym, or other items as the angel-investor meeting.",
        )
    )
    return checks


def _is_angel_meeting(text: Any) -> bool:
    return _has_needles(text, ("angel",)) or _has_needles(text, ("investor",))


def _match_add_angel_event(call: Dict[str, Any]) -> Tuple[bool, str]:
    if call.get("name") != "add_item":
        return False, "wrong tool"
    args = call.get("args") or {}
    if args.get("type") != "event":
        return False, f"type {args.get('type')!r} ≠ event"
    title = args.get("title")
    if not _is_angel_meeting(title):
        return False, f"title {title!r} does not match angel investor"
    if not _start_matches(args.get("start_at"), ANGEL_START):
        return False, f"start_at {args.get('start_at')!r} ≠ {ANGEL_START}"
    return True, "ok"


def _eval_plan_04(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], float, float, float, List[str]]:
    calls = [c for c in _calls(data) if isinstance(c, dict)]
    match = next((c for c in calls if _match_add_angel_event(c)[0]), None)
    extras = [c for c in calls if c is not match]
    ok, why = (_match_add_angel_event(match) if match else (False, "missing"))
    extra_args = {}
    if match:
        extra_args = {
            k: v
            for k, v in (match.get("args") or {}).items()
            if k not in {"title", "type", "start_at"}
        }
    if ok:
        status = VARIANT if extra_args else PASS
        expl = "add_item event Angel investor meeting at 15:00 today."
        if extra_args:
            expl += f" Extra optional args accepted: {list(extra_args)}."
        correct = 1
    else:
        status = FAIL
        expl = f"Required add_item missing or wrong ({why})."
        correct = 0
    login_adds = [
        c
        for c in extras
        if c.get("name") == "add_item"
        and _has_needles((c.get("args") or {}).get("title"), ("login",))
    ]
    checks = [
        _check(
            "add_angel_event",
            "Add angel-investor meeting event at 3pm",
            status,
            {"name": "add_item", "type": "event", "start_at": ANGEL_START},
            match,
            expl,
        ),
        _check(
            "no_login_add",
            "Do not add the login bug again",
            PASS if not login_adds else FAIL,
            0,
            len(login_adds),
            "Login bug is already itm_0000000000000004."
            if not login_adds
            else "Planned add_item for the login bug.",
        ),
        _check(
            "no_extra",
            "No unintended extra tool calls",
            PASS if not extras else FAIL,
            0,
            len(extras),
            "Only the angel-investor add_item is expected."
            if not extras
            else f"Extra calls: {[c.get('name') for c in extras]}.",
        ),
    ]
    generated = len(calls)
    precision = (correct / generated) if generated else 0.0
    recall = correct / 1
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    checks.append(
        _check(
            "plan_f1",
            "Plan precision / recall",
            PASS if precision == 1 and recall == 1 else FAIL,
            {"precision": 1, "recall": 1, "f1": 1},
            {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "correct": correct,
                "generated": generated,
            },
            "One add_item event with start_at 2026-11-06T15:00:00+00:00.",
        )
    )
    return checks, precision, recall, f1, _normalize_plan(calls)


def _eval_say_04(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    say = _say(data)
    types = say.get("types") or []
    text = say.get("text") or ""
    testimony = say.get("testimony")
    has_confirm = any(t in {"confirmation", "acknowledgement"} for t in types)
    type_ok = has_confirm and "clarification" not in types and "testimony" not in types
    checks = [
        _check(
            "response_type",
            "Confirmation or acknowledgement",
            PASS if type_ok else FAIL,
            ["confirmation | acknowledgement"],
            types,
            "Witness the angel-investor add. A testimony type requires a testimony payload; "
            "this turn is confirmation only.",
        ),
    ]
    checks.extend(
        _eval_say_hygiene(
            text, testimony, allow_testimony=False, allow_already_recorded=True
        )
    )
    return checks


def _match_status_update(call: Dict[str, Any], item_id: str, status: str) -> Tuple[bool, str]:
    if call.get("name") != "update_item":
        return False, "wrong tool"
    args = call.get("args") or {}
    if args.get("id") != item_id:
        return False, f"id {args.get('id')!r} ≠ {item_id}"
    if args.get("status") != status:
        return False, f"status {args.get('status')!r} ≠ {status}"
    return True, "ok"


def _match_gym_inactive(call: Dict[str, Any]) -> Tuple[bool, str]:
    if call.get("name") != "update_item":
        return False, "wrong tool"
    args = call.get("args") or {}
    if args.get("id") != GYM_ID:
        return False, f"id {args.get('id')!r} ≠ {GYM_ID}"
    if args.get("status") not in {"cancelled", "dropped"}:
        return False, f"status {args.get('status')!r} not in cancelled|dropped"
    return True, "ok"


def _match_family_move(call: Dict[str, Any]) -> Tuple[bool, str]:
    if call.get("name") != "update_item":
        return False, "wrong tool"
    args = call.get("args") or {}
    if args.get("id") != FAMILY_ID:
        return False, f"id {args.get('id')!r} ≠ {FAMILY_ID}"
    if not _start_matches(args.get("start_at"), FAMILY_MOVED):
        return False, f"start_at {args.get('start_at')!r} ≠ {FAMILY_MOVED}"
    return True, "ok"


def _eval_judge_05(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    understanding = (data.get("judge") or {}).get("understanding") or {}
    responsibilities = understanding.get("responsibilities") or []
    findings = _findings(data)
    actions = _actions(data)
    uncertainties = ((data.get("judge") or {}).get("evidence") or {}).get("uncertainties") or []
    still_ambiguous = [
        u
        for u in uncertainties
        if isinstance(u, dict) and u.get("type") == "ambiguous_match"
    ]
    updates = [a for a in actions if a.get("action") == "update"]
    update_ids = {a.get("item_id") for a in updates}
    needed = {ANGEL_ID, GYM_ID, LOGIN_ID, FAMILY_ID}
    clarify = [a for a in actions if a.get("action") == "clarify"]
    creates = [a for a in actions if a.get("action") == "create"]
    angel = _finding_for(("angel",), findings) or _finding_for(("investor",), findings)
    gym = _finding_for(("gym",), findings)
    login = _finding_for(("login",), findings)
    family = _finding_for(("family",), findings)
    existing_ok = all(
        (row or {}).get("match_status") == "existing"
        for row in (angel, gym, login, family)
        if row
    )
    checks = [
        _check(
            "responsibility",
            "Witnessing, or witnessing and testifying",
            PASS if "witness" in responsibilities else FAIL,
            [["witness"], ["witness", "testify"]],
            responsibilities,
            "The founder is reporting work-state changes.",
        ),
        _check(
            "angel_resolved",
            "Complete the angel-investor meeting",
            PASS if (angel or {}).get("item_id") == ANGEL_ID
            and (angel or {}).get("match_status") == "existing"
            and not still_ambiguous
            else FAIL,
            {"item_id": ANGEL_ID, "match_status": "existing"},
            {"angel": angel, "ambiguous": still_ambiguous},
            "The founder named the angel-investor meeting as completed.",
        ),
        _check(
            "four_updates",
            "Update angel, gym, login, and family",
            PASS if needed <= update_ids and not clarify and not creates else FAIL,
            sorted(needed),
            sorted(i for i in update_ids if i),
            "Four existing items change. Do not create or ask again.",
        ),
        _check(
            "targets_existing",
            "All four targets are existing work",
            PASS if existing_ok and angel and gym and login and family else FAIL,
            "existing × 4",
            {
                "angel": (angel or {}).get("match_status"),
                "gym": (gym or {}).get("match_status"),
                "login": (login or {}).get("match_status"),
                "family": (family or {}).get("match_status"),
            },
            "Do not treat these as new items.",
        ),
    ]
    invented = [
        row.get("piece_of_work")
        for row in findings
        if row.get("match_status") == "new"
    ]
    checks.append(
        _check(
            "no_invention",
            "No invented new work",
            PASS if not invented else FAIL,
            "Updates only",
            invented,
            "Scenario 05 only changes existing items.",
        )
    )
    return checks


def _eval_plan_05(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], float, float, float, List[str]]:
    calls = [c for c in _calls(data) if isinstance(c, dict)]
    expected = [
        ("complete_angel", "Complete angel-investor meeting", ANGEL_ID, "completed",
         lambda c: _match_status_update(c, ANGEL_ID, "completed")),
        ("cancel_gym", "Cancel the gym", GYM_ID, ["cancelled", "dropped"],
         _match_gym_inactive),
        ("complete_login", "Complete the login bug", LOGIN_ID, "completed",
         lambda c: _match_status_update(c, LOGIN_ID, "completed")),
        ("move_family", "Move family meeting to tomorrow 5pm", FAMILY_ID, FAMILY_MOVED,
         _match_family_move),
    ]
    used: set[int] = set()
    checks: List[Dict[str, Any]] = []
    correct = 0
    for check_id, label, expected_val, detail, matcher in expected:
        match_i = next(
            (i for i, c in enumerate(calls) if i not in used and matcher(c)[0]),
            None,
        )
        if match_i is None:
            checks.append(
                _check(
                    check_id,
                    label,
                    FAIL,
                    expected_val,
                    None,
                    f"Required update_item missing or wrong ({detail}).",
                )
            )
            continue
        used.add(match_i)
        match = calls[match_i]
        extra_args = {
            k: v
            for k, v in (match.get("args") or {}).items()
            if k not in {"id", "status", "start_at"}
        }
        gym_dropped = check_id == "cancel_gym" and (match.get("args") or {}).get(
            "status"
        ) == "dropped"
        status = VARIANT if extra_args or gym_dropped else PASS
        expl = f"update_item {detail}."
        if gym_dropped:
            expl += " dropped accepted; the prompt does not distinguish it from cancelled."
        if extra_args:
            expl += f" Extra optional args accepted: {list(extra_args)}."
        checks.append(_check(check_id, label, status, expected_val, match, expl))
        correct += 1
    extras = [c for i, c in enumerate(calls) if i not in used]
    checks.append(
        _check(
            "no_extra",
            "No unintended extra tool calls",
            PASS if not extras else FAIL,
            0,
            len(extras),
            "Only the four updates are expected."
            if not extras
            else f"Extra calls: {[c.get('name') for c in extras]}.",
        )
    )
    generated = len(calls)
    precision = (correct / generated) if generated else 0.0
    recall = correct / 4
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    checks.append(
        _check(
            "plan_f1",
            "Plan precision / recall",
            PASS if precision == 1 and recall == 1 else FAIL,
            {"precision": 1, "recall": 1, "f1": 1},
            {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "correct": correct,
                "generated": generated,
            },
            "Four update_item calls: angel completed, gym cancelled or dropped, login completed, family moved.",
        )
    )
    return checks, precision, recall, f1, _normalize_plan(calls)


def _mentions_hour(text: Any, hour: int) -> bool:
    blob = str(text or "")
    if re.search(rf"\b{hour}\s*(pm|p\.m\.)\b", blob, re.I):
        return True
    military = hour + 12 if hour <= 12 else hour
    if re.search(rf"\b{military}:00\b", blob):
        return True
    return bool(re.search(rf"\b{hour}\b", blob, re.I))


def _is_family_clear(call: Dict[str, Any]) -> bool:
    if call.get("name") != "update_item":
        return False
    args = call.get("args") or {}
    return args.get("id") == FAMILY_ID and args.get("start_at") in (None, "")


def _is_family_picked_time(call: Dict[str, Any]) -> bool:
    if call.get("name") != "update_item":
        return False
    args = call.get("args") or {}
    return args.get("id") == FAMILY_ID and args.get("start_at") not in (None, "")


def _eval_judge_06(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    understanding = (data.get("judge") or {}).get("understanding") or {}
    responsibilities = understanding.get("responsibilities") or []
    findings = _findings(data)
    actions = _actions(data)
    uncertainties = ((data.get("judge") or {}).get("evidence") or {}).get("uncertainties") or []
    family = _finding_for(("family",), findings) or _finding_for(("meeting",), findings)
    time_uncertainties = [
        u
        for u in uncertainties
        if isinstance(u, dict)
        and u.get("type") in {"conflicting_facts", "missing_information"}
    ]
    family_uncertain = any(
        FAMILY_ID in (u.get("candidate_ids") or [])
        or _has_needles(u.get("piece_of_work"), ("family",))
        for u in time_uncertainties
    )
    has_conflict_type = any(
        u.get("type") == "conflicting_facts" for u in time_uncertainties
    )
    picked = [c for c in _calls(data) if isinstance(c, dict) and _is_family_picked_time(c)]
    creates = [a for a in actions if a.get("action") == "create"]
    family_existing = (family or {}).get("match_status") == "existing" and (
        (family or {}).get("item_id") == FAMILY_ID
    )
    if family_uncertain and has_conflict_type:
        uncert_status = PASS
    elif family_uncertain:
        uncert_status = VARIANT
    else:
        uncert_status = FAIL
    checks = [
        _check(
            "responsibility",
            "Witnessing, or witnessing and testifying",
            PASS if "witness" in responsibilities else FAIL,
            [["witness"], ["witness", "testify"]],
            responsibilities,
            "A conflicting time is a reported work-state change, not a request for testimony.",
        ),
        _check(
            "family_existing",
            "Family meeting is the existing record",
            PASS if family_existing else FAIL,
            {"match_status": "existing", "item_id": FAMILY_ID},
            family,
            "This is the meeting just moved to tomorrow 5pm, not a new event.",
        ),
        _check(
            "conflicting_facts",
            "Time is unresolved against the record",
            uncert_status,
            {"type": ["conflicting_facts", "missing_information"], "candidate_ids": [FAMILY_ID]},
            time_uncertainties,
            "Brother 3pm and sister 6pm disagree with recorded 5pm; founder has not confirmed. "
            "missing_information is accepted as a variant of the same unresolved time.",
        ),
        _check(
            "clarify_not_write",
            "Do not write a specific time",
            PASS if not picked and not creates else FAIL,
            {"no_picked_time": True, "clear_start_ok": True},
            {"picked": picked, "creates": creates},
            "Ask, hold 5pm, or clear start_at. Do not write 3pm or 6pm.",
        ),
    ]
    invented = [
        row.get("piece_of_work")
        for row in findings
        if row.get("match_status") == "new"
    ]
    checks.append(
        _check(
            "no_invention",
            "No invented new work",
            PASS if not invented else FAIL,
            "Existing family meeting only",
            invented,
            "The 3pm and 6pm claims are about the recorded family meeting.",
        )
    )
    return checks


def _eval_plan_06(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], float, float, float, List[str]]:
    calls = [c for c in _calls(data) if isinstance(c, dict)]
    clears = [c for c in calls if _is_family_clear(c)]
    picked = [c for c in calls if _is_family_picked_time(c)]
    extras = [
        c
        for c in calls
        if not _is_family_clear(c) and not _is_family_picked_time(c)
    ]
    ok = not picked and not extras
    checks = [
        _check(
            "no_overwrite",
            "Do not write a specific family-meeting time",
            PASS if not picked else FAIL,
            {"empty_plan": True, "start_at": None},
            [c.get("args") for c in picked] or None,
            "Empty plan or start_at null is OK. Writing 3pm or 6pm is not.",
        ),
        _check(
            "no_extra",
            "No unintended extra tool calls",
            PASS if not extras else FAIL,
            0,
            len(extras),
            "Only an optional start_at-null update is allowed."
            if extras
            else "No extra calls.",
        ),
    ]
    precision = 1.0 if ok else 0.0
    recall = 1.0 if ok else 0.0
    f1 = 1.0 if ok else 0.0
    checks.append(
        _check(
            "plan_f1",
            "Plan precision / recall",
            PASS if ok else FAIL,
            {"precision": 1, "recall": 1, "f1": 1},
            {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "generated": len(calls),
                "clears": len(clears),
            },
            "Hold the recorded time, or clear start_at. Do not pick 3pm or 6pm.",
        )
    )
    return checks, precision, recall, f1, _normalize_plan(calls)


def _eval_say_06(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    say = _say(data)
    types = say.get("types") or []
    text = say.get("text") or ""
    testimony = say.get("testimony")
    cleared = any(_is_family_clear(c) for c in _calls(data) if isinstance(c, dict))
    picked = any(_is_family_picked_time(c) for c in _calls(data) if isinstance(c, dict))
    has_clarify = "clarification" in types
    has_confirm = any(t in {"confirmation", "acknowledgement"} for t in types)
    testimony_empty = testimony in (None, {})
    type_ok = testimony_empty and (
        (has_clarify and not picked) or (has_confirm and cleared and not picked)
    )
    named_claims = _mentions_hour(text, 3) and _mentions_hour(text, 6)
    asks = bool(
        "?" in text
        or re.search(r"\b(which|confirm|unconfirmed|right yet)\b", text, re.I)
    )
    about_meeting = (
        _has_needles(text, ("family",))
        or _has_needles(text, ("meeting",))
        or (
            _has_needles(text, ("brother",))
            and _has_needles(text, ("sister",))
        )
    )
    asks_ok = True if cleared else (named_claims and asks and about_meeting)
    checks = [
        _check(
            "response_type",
            "Clarification, or confirmation of a cleared time",
            PASS if type_ok else FAIL,
            ["clarification", "confirmation if start_at is null"],
            types,
            "Ask which time is right, or confirm clearing start_at. Do not confirm 3pm or 6pm.",
        ),
        _check(
            "asks_which_time",
            "Name the unconfirmed 3pm and 6pm claims",
            PASS if asks_ok else FAIL,
            "3pm and 6pm, or a cleared start_at",
            text,
            "When holding the record, say must mention both unconfirmed claims. "
            "Clearing start_at does not need the question.",
        ),
    ]
    checks.extend(
        _eval_say_hygiene(
            text, testimony, allow_testimony=False, strict_voice=False
        )
    )
    return checks


def _eval_judge_07(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    understanding = (data.get("judge") or {}).get("understanding") or {}
    responsibilities = understanding.get("responsibilities") or []
    actions = _actions(data)
    checks = [
        _check(
            "responsibility",
            "Neither witnessing nor testifying",
            PASS if responsibilities == [] else FAIL,
            [],
            responsibilities,
            "'How are you' does not report work or ask for an account of progress.",
        ),
        _check(
            "no_actions",
            "No required actions",
            PASS if not actions else FAIL,
            [],
            [a.get("action") for a in actions],
            "A greeting is not a progress-memory turn. "
            "An earlier unconfirmed time does not create a duty this turn.",
        ),
    ]
    return checks


def _eval_plan_07(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], float, float, float, List[str]]:
    return _eval_plan_empty(
        data,
        why="A greeting is not a progress-memory turn. Do not write or search.",
    )


def _eval_say_07(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    say = _say(data)
    types = say.get("types") or []
    text = say.get("text")
    testimony = say.get("testimony")
    silent_text = text in (None, "")
    only_silence = types == ["silence"]
    empty_types = types == []
    if only_silence:
        type_status = PASS
    elif empty_types:
        type_status = VARIANT
    else:
        type_status = FAIL
    checks = [
        _check(
            "response_type",
            "Silence type",
            type_status,
            ["silence"],
            types,
            "Prompt say.types includes silence. Empty types is the same outcome.",
        ),
        _check(
            "silent_text",
            "No spoken reply",
            PASS if silent_text else FAIL,
            "",
            text,
            "text must be empty. Do not greet or chit-chat.",
        ),
        _check(
            "no_testimony",
            "No testimony payload",
            PASS if testimony in (None, {}) else FAIL,
            None,
            testimony,
            "This turn is not a request for an account of progress.",
        ),
    ]
    return checks


def _eval_judge(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    understanding = (data.get("judge") or {}).get("understanding") or {}
    responsibilities = understanding.get("responsibilities") or []
    findings = _findings(data)
    actions = _actions(data)
    uncertainties = ((data.get("judge") or {}).get("evidence") or {}).get("uncertainties") or []

    has_witness = "witness" in responsibilities
    checks = [
        _check(
            "responsibility",
            "Witnessing, or witnessing and testifying",
            PASS if has_witness else FAIL,
            [["witness"], ["witness", "testify"]],
            responsibilities,
            "Message reports work-state changes. responsibilities may be witness only, or both witness and testify.",
        )
    ]

    acme = _finding_for(("acme",), findings)
    acme_action = next(
        (
            a
            for a in actions
            if a.get("action") == "update" and a.get("item_id") == ACME_ID
        ),
        None,
    )
    acme_ok = (acme or {}).get("match_status") == "existing" and (
        (acme or {}).get("item_id") == ACME_ID or acme_action is not None
    )
    if acme_ok and (acme or {}).get("item_id") == ACME_ID:
        acme_status = PASS
    elif acme_ok:
        acme_status = VARIANT
    else:
        acme_status = FAIL
    checks.append(
        _check(
            "acme_existing",
            "Acme is the existing item",
            acme_status,
            {"match_status": "existing", "item_id": ACME_ID},
            acme or acme_action,
            "Acme chase must match itm_0000000000000001 as existing work.",
        )
    )

    new_hits = []
    missing = []
    for spec in NEW_TASKS:
        row = _finding_for(spec["needles"], findings)
        action = next(
            (
                a
                for a in actions
                if a.get("action") == "create"
                and _has_needles(a.get("piece_of_work"), spec["needles"])
            ),
            None,
        )
        ok_finding = row is not None and row.get("match_status") == "new"
        if ok_finding or action is not None:
            new_hits.append(spec["key"])
        else:
            missing.append(spec["title"])
    checks.append(
        _check(
            "new_tasks",
            "Three new tasks identified",
            PASS if not missing else FAIL,
            [s["title"] for s in NEW_TASKS],
            new_hits,
            "Gym, landing copy, and login bug must be identified as new work."
            + (f" Missing: {missing}." if missing else ""),
        )
    )

    acme_as_new = (acme or {}).get("match_status") == "new"
    new_as_existing = any(
        (row or {}).get("match_status") == "existing"
        for spec in NEW_TASKS
        for row in [_finding_for(spec["needles"], findings)]
        if row
    )
    distinct = (not acme_as_new) and (not new_as_existing) and acme_ok and not missing
    checks.append(
        _check(
            "existing_vs_new",
            "Existing vs new distinction",
            PASS if distinct else FAIL,
            "Acme existing; gym / landing / login new",
            {
                "acme_status": (acme or {}).get("match_status"),
                "new_as_existing": new_as_existing,
            },
            "Acme must stay existing; the three reported tasks must not be treated as existing items.",
        )
    )

    invented_findings = []
    for row in findings:
        blob = f"{row.get('piece_of_work', '')} {row.get('finding', '')}"
        known = _has_needles(blob, ("acme",)) or any(
            _has_needles(blob, spec["needles"]) for spec in NEW_TASKS
        )
        if not known:
            invented_findings.append(row.get("piece_of_work"))
    invented_actions = [
        a.get("piece_of_work") or a.get("action")
        for a in actions
        if a.get("action") not in {"create", "update"}
        or (
            a.get("action") == "update"
            and a.get("item_id") not in {None, ACME_ID}
        )
        or (
            a.get("action") == "create"
            and not any(
                _has_needles(a.get("piece_of_work"), spec["needles"])
                for spec in NEW_TASKS
            )
        )
    ]
    invented_ids = [
        row.get("item_id")
        for row in findings
        if row.get("item_id") not in {None, ACME_ID}
    ]
    clean = (
        not invented_findings
        and not invented_actions
        and not invented_ids
        and uncertainties == []
    )
    checks.append(
        _check(
            "no_invention",
            "No invented facts or unsupported claims",
            PASS if clean else FAIL,
            "No extra work, empty uncertainties",
            {
                "invented_findings": invented_findings,
                "invented_actions": invented_actions,
                "invented_ids": invented_ids,
                "uncertainties": uncertainties,
            },
            "No extra pieces of work, no testify/clarify actions, no unknown ids, no uncertainties.",
        )
    )
    return checks


def _match_update(call: Dict[str, Any]) -> Tuple[bool, str]:
    if call.get("name") != "update_item":
        return False, "wrong tool"
    args = call.get("args") or {}
    if args.get("id") != ACME_ID:
        return False, f"id {args.get('id')!r} ≠ {ACME_ID}"
    if not _due_matches(args.get("due_at")):
        return False, f"due_at {args.get('due_at')!r} ≠ {EXPECTED_DUE}"
    material = {k: v for k, v in args.items() if k not in {"id", "due_at", "work_mode"}}
    harmful = [
        k
        for k, v in material.items()
        if k in {"title", "type", "status"} and v not in {None, "todo", "task"}
    ]
    if harmful:
        return False, f"material extra fields {harmful}"
    return True, "ok"


def _match_add(call: Dict[str, Any], needles: Sequence[str]) -> Tuple[bool, str]:
    if call.get("name") != "add_item":
        return False, "wrong tool"
    args = call.get("args") or {}
    if args.get("type") != "task":
        return False, f"type {args.get('type')!r} ≠ task"
    if not _has_needles(args.get("title"), needles):
        return False, f"title {args.get('title')!r} does not match {needles}"
    return True, "ok"


def _eval_plan(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], float, float, float, List[str]]:
    calls = [c for c in _calls(data) if isinstance(c, dict)]
    used: set[int] = set()
    checks: List[Dict[str, Any]] = []
    correct = 0
    expected_ops = 4

    def take(pred) -> Optional[Dict[str, Any]]:
        for i, call in enumerate(calls):
            if i in used:
                continue
            ok, _ = pred(call)
            if ok:
                used.add(i)
                return call
        return None

    acme_call = take(_match_update)
    ok, why = (_match_update(acme_call) if acme_call else (False, "missing"))
    if ok:
        correct += 1
        extra = {
            k: v
            for k, v in (acme_call.get("args") or {}).items()
            if k not in {"id", "due_at"}
        }
        status = VARIANT if extra else PASS
        expl = "update_item on Acme with tomorrow 23:59:59+00:00."
        if extra:
            expl += f" Extra optional args accepted: {list(extra)}."
    else:
        status = FAIL
        expl = f"Required update missing or wrong ({why})."
    checks.append(
        _check(
            "update_acme",
            "Update Acme due_at",
            status,
            {"name": "update_item", "id": ACME_ID, "due_at": EXPECTED_DUE},
            acme_call,
            expl,
        )
    )

    for spec in NEW_TASKS:
        call = take(lambda c, n=spec["needles"]: _match_add(c, n))
        ok, why = (_match_add(call, spec["needles"]) if call else (False, "missing"))
        if ok:
            correct += 1
            title = (call.get("args") or {}).get("title")
            status = PASS if title == spec["title"] else VARIANT
        else:
            status = FAIL
        checks.append(
            _check(
                f"add_{spec['key']}",
                f"Add {spec['title']}",
                status,
                {"name": "add_item", "title": spec["title"], "type": "task"},
                call,
                "Matched by meaning; order does not matter."
                if ok
                else f"Required add_item missing or wrong ({why}).",
            )
        )

    extras = [calls[i] for i in range(len(calls)) if i not in used]
    checks.append(
        _check(
            "no_extra",
            "No unintended extra tool calls",
            PASS if not extras else FAIL,
            0,
            len(extras),
            "Only the four witnessing writes are expected."
            if not extras
            else f"Extra calls: {[c.get('name') for c in extras]}.",
        )
    )

    generated = len(calls)
    precision = (correct / generated) if generated else 0.0
    recall = correct / expected_ops
    f1 = (
        0.0
        if precision + recall == 0
        else 2 * precision * recall / (precision + recall)
    )
    checks.append(
        _check(
            "plan_f1",
            "Plan precision / recall",
            PASS if precision == 1 and recall == 1 else FAIL,
            {"precision": 1, "recall": 1, "f1": 1},
            {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "correct": correct,
                "generated": generated,
            },
            "Operations matched by meaning, not array position. Wrong args count as incorrect.",
        )
    )
    normalized = _normalize_plan(calls)
    return checks, precision, recall, f1, normalized


def _eval_say(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    say = _say(data)
    types = say.get("types") or []
    text = say.get("text") or ""
    testimony = say.get("testimony")

    type_ok = any(t in {"confirmation", "acknowledgement"} for t in types) and (
        "testimony" not in types and "clarification" not in types
    )
    checks = [
        _check(
            "response_type",
            "Appropriate confirmation or acknowledgement",
            PASS if type_ok else FAIL,
            ["confirmation | acknowledgement"],
            types,
            "Witnessing writes should confirm or acknowledge, not testify or clarify.",
        )
    ]
    checks.extend(_eval_say_hygiene(text, testimony, allow_testimony=False))
    return checks


EVALUATORS = {
    "brain-dump-01": (_eval_judge, _eval_plan, _eval_say),
    "brain-dump-02": (_eval_judge_02, _eval_plan_02, _eval_say_02),
    "brain-dump-03": (_eval_judge_03, _eval_plan_03, _eval_say),
    "brain-dump-04": (_eval_judge_04, _eval_plan_04, _eval_say_04),
    "brain-dump-05": (_eval_judge_05, _eval_plan_05, _eval_say),
    "brain-dump-06": (_eval_judge_06, _eval_plan_06, _eval_say_06),
    "brain-dump-07": (_eval_judge_07, _eval_plan_07, _eval_say_07),
}
