"""Remembering scenario evaluators. Testify only; tools are never executed."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from lab.fixtures.remembering import (
    EXCLUDED_TODAY_IDS,
    LAST_WEEK_END,
    LAST_WEEK_START,
    REFLECTION_EXCLUDED_IDS,
    REFLECTION_IDS,
    REM_STANDUP_ID,
    REM_TODAY,
    TODAY_IDS,
)
from lab.scoring.common import (
    FAIL,
    PASS,
    VARIANT,
    actions as _actions,
    calls as _calls,
    check as _check,
    eval_say_hygiene,
    normalize_plan,
    say as _say,
    text_lists_records,
)

REQUIRED_TODAY = set(TODAY_IDS)
FORBIDDEN_TODAY = set(EXCLUDED_TODAY_IDS)
REQUIRED_REFLECTION = set(REFLECTION_IDS)
FORBIDDEN_REFLECTION = set(REFLECTION_EXCLUDED_IDS)
PLATE_NEEDLES = ("gym", "landing", "doctor", "family", "hassan", "proposal", "standup")
WEEK_NEEDLES = (
    "pricing",
    "coffee",
    "expenses",
    "review",
    "gym",
    "standup",
    "doctor",
    "proposal",
    "invoice",
    "landing",
    "family",
    "flights",
)
WRITE_TOOLS = {"add_item", "update_item"}
ISO_WEEK_VARIANT = ("2026-11-03", "2026-11-09")


def _requested_period(data: Dict[str, Any]) -> Dict[str, Any]:
    understanding = (data.get("judge") or {}).get("understanding") or {}
    period = understanding.get("requested_period")
    return period if isinstance(period, dict) else {}


def _period_status(
    start: Any,
    end: Any,
    *,
    expected_start: str,
    expected_end: str,
    variants: Tuple[Tuple[Any, Any], ...] = (),
) -> str:
    if start == expected_start and end == expected_end:
        return PASS
    if start == expected_start and end in (None, ""):
        return VARIANT
    if (start, end) in variants:
        return VARIANT
    return FAIL


def _eval_judge_01(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    understanding = (data.get("judge") or {}).get("understanding") or {}
    responsibilities = understanding.get("responsibilities") or []
    required = _actions(data)
    writes = [a for a in required if a.get("action") in {"create", "update"}]
    testify = [a for a in required if a.get("action") == "testify"]
    testify_only = responsibilities == ["testify"] or (
        "testify" in responsibilities and "witness" not in responsibilities
    )
    checks = [
        _check(
            "responsibility",
            "Testify, do not witness",
            PASS if testify_only else FAIL,
            ["testify"],
            responsibilities,
            "The founder asked what is on the plate today. That is testimony, not a write.",
        ),
        _check(
            "testify_action",
            "Required action is testify",
            PASS if testify and not writes else FAIL,
            {"action": "testify", "no_writes": True},
            {"testify": testify, "writes": [a.get("action") for a in writes]},
            "Do not create or update. Progress Memory already holds today's work.",
        ),
    ]
    period = _requested_period(data)
    start, end = period.get("start"), period.get("end")
    checks.extend(
        [
            _check(
                "requested_period",
                "Resolved today from the clock",
                _period_status(start, end, expected_start=REM_TODAY, expected_end=REM_TODAY),
                {"start": REM_TODAY, "end": REM_TODAY},
                period or None,
                "Today is Saturday 14 November 2026. Judge must resolve that day "
                "independently of say.testimony.scope.",
            ),
            _check(
                "requested_period_reason",
                "Reason for the resolved period",
                PASS if str(period.get("reason") or "").strip() else FAIL,
                "non-empty requested_period.reason",
                period.get("reason"),
                "State the current date and why the requested period is today.",
            ),
        ]
    )
    return checks


def _eval_plan_01(
    data: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], float, float, float, List[str]]:
    return _eval_plan_testify(data, "today's work")


def _eval_plan_02(
    data: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], float, float, float, List[str]]:
    return _eval_plan_testify(data, "last week's work")


def _eval_plan_testify(
    data: Dict[str, Any],
    work_held: str,
) -> Tuple[List[Dict[str, Any]], float, float, float, List[str]]:
    tool_calls = [c for c in _calls(data) if isinstance(c, dict)]
    writes = [c for c in tool_calls if c.get("name") in WRITE_TOOLS]
    searches = [c for c in tool_calls if c.get("name") == "search_items"]
    other = [
        c
        for c in tool_calls
        if c.get("name") not in WRITE_TOOLS | {"search_items"}
    ]
    names = [c.get("name") for c in tool_calls]
    if writes or other:
        ok = False
        tools_status = FAIL
        extra_status = FAIL
        tools_expl = "Do not add or update. search_items is optional when records are already in Interaction State."
    elif searches:
        ok = True
        tools_status = VARIANT
        extra_status = VARIANT
        tools_expl = "search_items is optional; empty plan is the golden."
    else:
        ok = True
        tools_status = PASS
        extra_status = PASS
        tools_expl = f"Empty plan is the golden. Progress Memory already holds {work_held}."
    checks = [
        _check(
            "no_writes",
            "No add_item or update_item",
            PASS if not writes else FAIL,
            [],
            [c.get("name") for c in writes],
            "Testimony does not write. search_items is the only optional tool.",
        ),
        _check(
            "no_tools",
            "Empty plan, or optional search_items",
            tools_status,
            [],
            names,
            tools_expl,
        ),
        _check(
            "no_extra",
            "No unintended extra tool calls",
            extra_status,
            0,
            len(writes) + len(other),
            "Only optional search_items is accepted besides an empty plan."
            if extra_status != FAIL
            else f"Extra calls: {names}.",
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
            {"precision": precision, "recall": recall, "f1": f1, "generated": len(tool_calls)},
            "Empty plan is exact. search_items-only is a variant with full plan credit.",
        )
    )
    return checks, precision, recall, f1, normalize_plan(tool_calls)


def _eval_say_01(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    say = _say(data)
    types = say.get("types") or []
    raw_text = say.get("text")
    text = raw_text if isinstance(raw_text, str) else ""
    testimony = say.get("testimony")
    type_ok = types == ["testimony"] or (
        "testimony" in types
        and not any(
            t in {"confirmation", "acknowledgement", "clarification", "silence"}
            for t in types
        )
    )
    dumped = text_lists_records(text, PLATE_NEEDLES)
    header_status = PASS if text.strip() else VARIANT
    checks = [
        _check(
            "response_type",
            "Testimony only",
            PASS if type_ok else FAIL,
            ["testimony"],
            types,
            "A progress question is testimony. Do not confirm a write.",
        )
    ]
    if not isinstance(testimony, dict) or not testimony:
        checks.append(
            _check(
                "testimony_payload",
                "Testimony payload is required",
                FAIL,
                {"aim": "remaining work today", "view": "inventory"},
                testimony,
                "say.testimony must select today's open work.",
            )
        )
        checks.extend(_header_checks(text, header_status, dumped))
        checks.extend(eval_say_hygiene(text, testimony, allow_testimony=True))
        return checks

    aim = testimony.get("aim")
    view = testimony.get("view")
    order = testimony.get("order")
    scope = testimony.get("scope") if isinstance(testimony.get("scope"), dict) else {}
    start, end = scope.get("start"), scope.get("end")
    ids = [i for i in (testimony.get("item_ids") or []) if isinstance(i, str)]
    omitted = [i for i in (testimony.get("omitted_ids") or []) if isinstance(i, str)]
    omitted_reason = str(testimony.get("omitted_ids_reason") or "").strip()
    got = set(ids)
    omitted_set = set(omitted)
    missing = sorted(REQUIRED_TODAY - got)
    forbidden = sorted(got & FORBIDDEN_TODAY)
    extra = sorted(got - REQUIRED_TODAY - FORBIDDEN_TODAY)
    must_name = set(missing)
    if REM_STANDUP_ID not in got:
        must_name.add(REM_STANDUP_ID)
    unnamed = sorted(must_name - omitted_set)
    if unnamed:
        omitted_status = FAIL
        omitted_expected = unnamed
        omitted_expl = (
            "Standup is an 11:00 event. At 16:30 it does not remain to be dealt with; "
            "name it in omitted_ids and say the occurrence has passed."
        )
    elif omitted and not omitted_reason:
        omitted_status = FAIL
        omitted_expected = sorted(must_name)
        omitted_expl = "omitted_ids_reason is required when omitted_ids is not empty."
    else:
        omitted_status = PASS
        omitted_expected = sorted(must_name)
        omitted_expl = (
            "Name the past-timed standup (and any other in-scope records left out), and why."
        )

    scope_status = _period_status(
        start, end, expected_start=REM_TODAY, expected_end=REM_TODAY
    )

    if order in {"priority", "natural"}:
        order_status = PASS
    elif order in {"chronological", "reverse_chronological"}:
        order_status = VARIANT
    else:
        order_status = FAIL

    ids_ok = not missing and not forbidden and not extra
    checks.extend(
        [
            _check(
                "testimony_payload",
                "Testimony payload is required",
                PASS,
                "object",
                {"aim": aim, "view": view},
                "Testimony describes today's inventory.",
            ),
            _check(
                "aim",
                "Aim of the testimony",
                PASS if str(aim or "").strip() else FAIL,
                "non-empty aim",
                aim,
                "State what the founder wants to understand about their work.",
            ),
            _check(
                "purpose_reason",
                "Reason for the testimony purpose",
                PASS if str(testimony.get("purpose_reason") or "").strip() else FAIL,
                "non-empty purpose_reason",
                testimony.get("purpose_reason"),
                "Explain why this testimony is orientation rather than reflection.",
            ),
            _check(
                "view",
                "Inventory, not timeline",
                PASS if view == "inventory" else FAIL,
                "inventory",
                view,
                "Day alignment lists open work. Timeline is a later scenario.",
            ),
            _check(
                "view_reason",
                "Reason for the selected view",
                PASS if str(testimony.get("view_reason") or "").strip() else FAIL,
                "non-empty view_reason",
                testimony.get("view_reason"),
                "Explain why this view presents today's remaining work.",
            ),
            _check(
                "order",
                "Priority or natural order",
                order_status,
                ["priority", "natural"],
                order,
                "Today's inventory is remaining work, so priority is right. "
                "natural is also accepted. Time order is a variant.",
            ),
            _check(
                "scope",
                "Scope is today",
                scope_status,
                {"start": REM_TODAY, "end": REM_TODAY},
                scope,
                "Today is 2026-11-14. Missing end is accepted if start is today.",
            ),
            _check(
                "scope_reason",
                "Reason for the selected period",
                PASS if str(testimony.get("scope_reason") or "").strip() else FAIL,
                "non-empty scope_reason",
                testimony.get("scope_reason"),
                "State the current date and why the selected start and end are today.",
            ),
            _check(
                "item_ids",
                "Today's open work only",
                PASS if ids_ok else FAIL,
                sorted(REQUIRED_TODAY),
                ids,
                "Include open tasks: landing copy and the proposal. "
                "Exclude cancelled gym, completed doctor, completed Hassan, "
                "tomorrow's family meeting, and the 11:00 standup whose time has passed.",
            ),
            _check(
                "item_ids_reason",
                "Reason for the selected item IDs",
                PASS if str(testimony.get("item_ids_reason") or "").strip() else FAIL,
                "non-empty item_ids_reason",
                testimony.get("item_ids_reason"),
                "Explain why these records support today's orientation inventory.",
            ),
            _check(
                "omitted_ids",
                "Name in-scope records that were not selected",
                omitted_status,
                omitted_expected,
                omitted,
                omitted_expl,
            ),
            _check(
                "omitted_ids_reason",
                "Reason for omitted records",
                omitted_status,
                "non-empty omitted_ids_reason when anything was left out",
                testimony.get("omitted_ids_reason"),
                "Inventory is remaining work. An event whose time has passed is omitted, not selected.",
            ),
        ]
    )
    checks.extend(_header_checks(text, header_status, dumped))
    checks.extend(eval_say_hygiene(text, testimony, allow_testimony=True))
    return checks


def _header_checks(
    text: str, header_status: str, dumped: List[str]
) -> List[Dict[str, Any]]:
    return [
        _check(
            "spoken_header",
            "Brief testimony header",
            header_status,
            "non-empty header, or null",
            text,
            "say.text introduces the visual presentation. Empty or null is a variant.",
        ),
        _check(
            "header_not_records",
            "Header does not list recorded work",
            PASS if not dumped else FAIL,
            "header only",
            dumped or text,
            "Recorded work belongs in say.testimony, not in say.text.",
        ),
    ]


def _eval_judge_02(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    understanding = (data.get("judge") or {}).get("understanding") or {}
    responsibilities = understanding.get("responsibilities") or []
    required = _actions(data)
    writes = [a for a in required if a.get("action") in {"create", "update"}]
    testify = [a for a in required if a.get("action") == "testify"]
    testify_only = responsibilities == ["testify"] or (
        "testify" in responsibilities and "witness" not in responsibilities
    )
    checks = [
        _check(
            "responsibility",
            "Testify, do not witness",
            PASS if testify_only else FAIL,
            ["testify"],
            responsibilities,
            "The founder asked what they got done last week. That is testimony, not a write.",
        ),
        _check(
            "testify_action",
            "Required action is testify",
            PASS if testify and not writes else FAIL,
            {"action": "testify", "no_writes": True},
            {"testify": testify, "writes": [a.get("action") for a in writes]},
            "Do not create or update. Progress Memory already holds last week's work.",
        ),
    ]
    period = _requested_period(data)
    start, end = period.get("start"), period.get("end")
    checks.extend(
        [
            _check(
                "requested_period",
                "Resolved last week from the clock",
                _period_status(
                    start,
                    end,
                    expected_start=LAST_WEEK_START,
                    expected_end=LAST_WEEK_END,
                    variants=(ISO_WEEK_VARIANT,),
                ),
                {"start": LAST_WEEK_START, "end": LAST_WEEK_END},
                period or None,
                "Today is Saturday 14 November 2026. Last week is Monday 2 November "
                "through Sunday 8 November. This week (9-15 November) is an incorrect "
                "interpretation. Scored independently of say.testimony.scope.",
            ),
            _check(
                "requested_period_reason",
                "Reason for the resolved period",
                PASS if str(period.get("reason") or "").strip() else FAIL,
                "non-empty requested_period.reason",
                period.get("reason"),
                "State the current date and why last week is 2-8 November rather than 9-15.",
            ),
        ]
    )
    return checks


def _eval_say_02(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    say = _say(data)
    types = say.get("types") or []
    raw_text = say.get("text")
    text = raw_text if isinstance(raw_text, str) else ""
    testimony = say.get("testimony")
    type_ok = types == ["testimony"] or (
        "testimony" in types
        and not any(
            t in {"confirmation", "acknowledgement", "clarification", "silence"}
            for t in types
        )
    )
    dumped = text_lists_records(text, WEEK_NEEDLES)
    header_status = PASS if text.strip() else VARIANT
    checks = [
        _check(
            "response_type",
            "Testimony only",
            PASS if type_ok else FAIL,
            ["testimony"],
            types,
            "A progress question is testimony. Do not confirm a write.",
        )
    ]
    if not isinstance(testimony, dict) or not testimony:
        checks.append(
            _check(
                "testimony_payload",
                "Testimony payload is required",
                FAIL,
                {"aim": "work completed last week", "item_ids": sorted(REQUIRED_REFLECTION)},
                testimony,
                "say.testimony must select work completed last week.",
            )
        )
        checks.extend(_header_checks(text, header_status, dumped))
        checks.extend(eval_say_hygiene(text, testimony, allow_testimony=True))
        return checks

    aim = testimony.get("aim")
    view = testimony.get("view")
    order = testimony.get("order")
    scope = testimony.get("scope") if isinstance(testimony.get("scope"), dict) else {}
    start, end = scope.get("start"), scope.get("end")
    ids = [i for i in (testimony.get("item_ids") or []) if isinstance(i, str)]
    got = set(ids)
    missing = sorted(REQUIRED_REFLECTION - got)
    forbidden = sorted(got & FORBIDDEN_REFLECTION)
    extra = sorted(got - REQUIRED_REFLECTION - FORBIDDEN_REFLECTION)

    scope_status = _period_status(
        start,
        end,
        expected_start=LAST_WEEK_START,
        expected_end=LAST_WEEK_END,
        variants=(ISO_WEEK_VARIANT,),
    )

    if order == "chronological":
        order_status = PASS
    elif order in {"reverse_chronological", "natural"}:
        order_status = VARIANT
    else:
        order_status = FAIL

    view_status = PASS if view else FAIL

    ids_ok = not missing and not forbidden and not extra
    checks.extend(
        [
            _check(
                "testimony_payload",
                "Testimony payload is required",
                PASS,
                "object",
                {"aim": aim, "view": view},
                "Testimony describes work completed last week.",
            ),
            _check(
                "aim",
                "Aim of the testimony",
                PASS if str(aim or "").strip() else FAIL,
                "non-empty aim",
                aim,
                "State what the founder wants to understand about their work.",
            ),
            _check(
                "purpose_reason",
                "Reason for the testimony purpose",
                PASS if str(testimony.get("purpose_reason") or "").strip() else FAIL,
                "non-empty purpose_reason",
                testimony.get("purpose_reason"),
                "Explain why this testimony reconstructs last week's recorded completions.",
            ),
            _check(
                "view",
                "Any testimony view",
                view_status,
                "unrestricted",
                view,
                "View is not scored for this scenario. Any selected view is accepted.",
            ),
            _check(
                "view_reason",
                "Reason for the selected view",
                PASS if str(testimony.get("view_reason") or "").strip() else FAIL,
                "non-empty view_reason",
                testimony.get("view_reason"),
                "Explain why this view presents work completed last week.",
            ),
            _check(
                "order",
                "Chronological order",
                order_status,
                "chronological",
                order,
                "Last week's completions are shown in time order. "
                "reverse_chronological and natural are variants. Priority is remaining-work order.",
            ),
            _check(
                "scope",
                "Scope is last week",
                scope_status,
                {"start": LAST_WEEK_START, "end": LAST_WEEK_END},
                scope,
                "Last week is Monday 2 November through Sunday 8 November 2026. "
                "Missing end is accepted if start is that Monday. "
                "Scored against the Interaction State clock, not against judge.requested_period.",
            ),
            _check(
                "scope_reason",
                "Reason for the selected period",
                PASS if str(testimony.get("scope_reason") or "").strip() else FAIL,
                "non-empty scope_reason",
                testimony.get("scope_reason"),
                "State the current date, that last week is the previous Monday-Sunday "
                "calendar week, and why 2-8 November was chosen rather than 9-15.",
            ),
            _check(
                "item_ids",
                "Work completed last week only",
                PASS if ids_ok else FAIL,
                sorted(REQUIRED_REFLECTION),
                ids,
                "Scored against last week (2-8 November) from the clock, not against "
                "Vee's requested_period or testimony.scope. Include pricing page, "
                "investor coffee, expenses, and the weekly review. Completions in this "
                "week (invoice, proposal, flights) fail even if they match an incorrect "
                "9-15 window. Exclude cancelled gym, uncompleted standup, the prior-week "
                "doctor call, open landing copy, and today's family meeting.",
            ),
            _check(
                "item_ids_reason",
                "Reason for the selected item IDs",
                PASS if str(testimony.get("item_ids_reason") or "").strip() else FAIL,
                "non-empty item_ids_reason",
                testimony.get("item_ids_reason"),
                "Explain why these records are work completed last week.",
            ),
        ]
    )
    checks.extend(_header_checks(text, header_status, dumped))
    checks.extend(eval_say_hygiene(text, testimony, allow_testimony=True))
    return checks


EVALUATORS = {
    "remembering-01": (_eval_judge_01, _eval_plan_01, _eval_say_01),
    "remembering-02": (_eval_judge_02, _eval_plan_02, _eval_say_02),
}
