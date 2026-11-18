"""Remembering Scenario 01 — day alignment; Scenario 02 — last-week reflection."""

from __future__ import annotations

import json
from copy import deepcopy

from lab.evaluate import evaluate_decision
from lab.scenario import (
    DEFAULT_SCENARIO_ID,
    LAST_WEEK_END,
    LAST_WEEK_START,
    REM_DOCTOR_ID,
    REM_FAMILY_ID,
    REM_GYM_ID,
    REM_HASSAN_ID,
    REM_LANDING_ID,
    REM_PROPOSAL_ID,
    REM_STANDUP_ID,
    WEEK_DOCTOR_ID,
    WEEK_EXPENSES_ID,
    WEEK_FAMILY_ID,
    WEEK_FLIGHTS_ID,
    WEEK_GYM_ID,
    WEEK_INVOICE_ID,
    WEEK_LANDING_ID,
    WEEK_PRICING_ID,
    WEEK_PROPOSAL_ID,
    WEEK_REVIEW_ID,
    WEEK_STANDUP_ID,
    get_scenario,
    golden_remembering_01,
    golden_remembering_02,
    list_scenarios,
)


def _score(payload, scenario_id: str = "remembering-01") -> dict:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return evaluate_decision(
        raw, input_rate=0.17, output_rate=0.25, scenario_id=scenario_id
    )


def _by_id(ev: dict, check_id: str) -> dict:
    for group in ev["checks"].values():
        for row in group:
            if row["id"] == check_id:
                return row
    raise KeyError(check_id)


def test_remembering_01_is_listed() -> None:
    row = next(s for s in list_scenarios() if s["id"] == "remembering-01")
    assert row["family"] == "remembering"
    assert "Day alignment" in row["title"]


def test_remembering_01_fixture() -> None:
    state = get_scenario("remembering-01").interaction_state
    assert "what do i have today?" in state
    assert "(none)" in state
    assert "16:30, Saturday 14 November 2026, Europe/London" in state
    assert "This calendar week (current week):" in state
    assert "2026-11-09 → 2026-11-15" in state
    assert "Last calendar week (previous week):" in state
    assert "2026-11-02 → 2026-11-08" in state
    assert "Finalize landing copy" in state
    assert "Send proposal" in state
    assert "Team standup" in state
    assert "Hit the gym" in state
    assert "Meet Hassan" in state
    assert "Family meeting" in state
    assert "Call the doctor" in state
    assert REM_STANDUP_ID in state


def test_remembering_01_golden_strict_pass() -> None:
    ev = _score(golden_remembering_01())
    assert ev["gates"]["json_valid"]
    assert ev["gates"]["schema_valid"]
    assert ev["gates"]["strict_pass"]
    assert ev["status"] == "PASS"
    assert ev["scores"]["overall"] == 100
    assert ev["scores"]["plan_f1"] == 100
    assert ev["fail_kind"] == "pass"
    assert _by_id(ev, "requested_period")["status"] == "pass"


def test_remembering_01_including_standup_fails() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["testimony"]["item_ids"].append(REM_STANDUP_ID)
    payload["say"]["testimony"]["omitted_ids"] = [
        i for i in payload["say"]["testimony"]["omitted_ids"] if i != REM_STANDUP_ID
    ]
    ev = _score(payload)
    assert _by_id(ev, "item_ids")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_01_including_hassan_fails() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["testimony"]["item_ids"].append(REM_HASSAN_ID)
    ev = _score(payload)
    assert _by_id(ev, "item_ids")["status"] == "fail"


def test_remembering_01_including_gym_or_family_fails() -> None:
    for extra in (REM_GYM_ID, REM_FAMILY_ID):
        payload = deepcopy(golden_remembering_01())
        payload["say"]["testimony"]["item_ids"].append(extra)
        ev = _score(payload)
        assert _by_id(ev, "item_ids")["status"] == "fail", extra


def test_remembering_01_search_items_is_variant() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["plan"]["tool_calls"] = [
        {"name": "search_items", "args": {"query": "today"}}
    ]
    ev = _score(payload)
    assert _by_id(ev, "no_tools")["status"] == "variant"
    assert _by_id(ev, "no_writes")["status"] == "pass"
    assert ev["scores"]["plan_f1"] == 100
    assert ev["gates"]["strict_pass"]


def test_remembering_01_add_item_fails() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["plan"]["tool_calls"] = [
        {"name": "add_item", "args": {"title": "Hit the gym", "type": "task"}}
    ]
    ev = _score(payload)
    assert _by_id(ev, "no_writes")["status"] == "fail"
    assert ev["scores"]["plan_f1"] == 0
    assert ev["gates"]["strict_pass"] is False


def test_remembering_01_standup_must_be_named_in_omitted() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["testimony"]["omitted_ids"] = [
        i for i in payload["say"]["testimony"]["omitted_ids"] if i != REM_STANDUP_ID
    ]
    ev = _score(payload)
    assert _by_id(ev, "item_ids")["status"] == "pass"
    assert _by_id(ev, "omitted_ids")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_01_omitting_standup_with_reason_passes() -> None:
    ev = _score(golden_remembering_01())
    assert REM_STANDUP_ID not in ev["parsed"]["say"]["testimony"]["item_ids"]
    assert REM_STANDUP_ID in ev["parsed"]["say"]["testimony"]["omitted_ids"]
    assert _by_id(ev, "item_ids")["status"] == "pass"
    assert _by_id(ev, "omitted_ids")["status"] == "pass"
    assert ev["gates"]["strict_pass"]


def test_remembering_01_empty_aim_fails() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["testimony"]["aim"] = ""
    ev = _score(payload)
    assert _by_id(ev, "aim")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_01_empty_view_reason_fails() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["testimony"]["view_reason"] = ""
    ev = _score(payload)
    assert _by_id(ev, "view_reason")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_01_empty_purpose_reason_fails() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["testimony"]["purpose_reason"] = ""
    ev = _score(payload)
    assert _by_id(ev, "purpose_reason")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_01_empty_scope_reason_fails() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["testimony"]["scope_reason"] = ""
    ev = _score(payload)
    assert _by_id(ev, "scope_reason")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_01_empty_item_ids_reason_fails() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["testimony"]["item_ids_reason"] = ""
    ev = _score(payload)
    assert _by_id(ev, "item_ids_reason")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_01_timeline_view_fails() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["testimony"]["view"] = "timeline"
    ev = _score(payload)
    assert _by_id(ev, "view")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_01_testimony_type_without_payload_fails_schema() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["testimony"] = None
    ev = _score(payload)
    assert ev["gates"]["schema_valid"] is False
    assert ev["fail_kind"] == "schema"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_01_empty_types_fails() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["types"] = []
    ev = _score(payload)
    assert _by_id(ev, "response_type")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_01_header_listing_records_fails() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["text"] = (
        "Today you have Finalize landing copy, Send proposal, and Team standup."
    )
    ev = _score(payload)
    assert _by_id(ev, "header_not_records")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_01_empty_header_is_variant() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["text"] = None
    ev = _score(payload)
    assert _by_id(ev, "spoken_header")["status"] == "variant"
    assert _by_id(ev, "header_not_records")["status"] == "pass"
    assert ev["gates"]["strict_pass"]


def test_remembering_01_natural_order_still_passes() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["testimony"]["order"] = "natural"
    ev = _score(payload)
    assert _by_id(ev, "order")["status"] == "pass"
    assert ev["gates"]["strict_pass"]


def test_remembering_01_chronological_order_is_variant() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["testimony"]["order"] = "chronological"
    ev = _score(payload)
    assert _by_id(ev, "order")["status"] == "variant"
    assert ev["gates"]["strict_pass"]


def test_remembering_01_missing_scope_end_is_variant() -> None:
    payload = deepcopy(golden_remembering_01())
    payload["say"]["testimony"]["scope"]["end"] = None
    ev = _score(payload)
    assert _by_id(ev, "scope")["status"] == "variant"
    assert ev["gates"]["strict_pass"]


def test_remembering_02_is_default_and_listed() -> None:
    assert DEFAULT_SCENARIO_ID == "remembering-02"
    row = next(s for s in list_scenarios() if s["id"] == "remembering-02")
    assert row["family"] == "remembering"
    assert "Last-week reflection" in row["title"]


def test_remembering_02_fixture() -> None:
    state = get_scenario("remembering-02").interaction_state
    assert "What did I get done last week?" in state
    assert "(none)" in state
    assert "what do i have today?" not in state
    assert "16:45, Saturday 14 November 2026, Europe/London" in state
    assert "2026-11-09 → 2026-11-15" in state
    assert "2026-11-02 → 2026-11-08" in state
    assert "Ship pricing page" in state
    assert "Investor coffee" in state
    assert "File expenses" in state
    assert "Write weekly review" in state
    assert "Send invoice" in state
    assert "Book flights" in state
    assert WEEK_PRICING_ID in state
    assert WEEK_REVIEW_ID in state
    assert WEEK_INVOICE_ID in state
    assert WEEK_STANDUP_ID in state
    assert WEEK_FLIGHTS_ID in state


def test_remembering_02_golden_strict_pass() -> None:
    ev = _score(golden_remembering_02(), "remembering-02")
    assert ev["gates"]["json_valid"]
    assert ev["gates"]["schema_valid"]
    assert ev["gates"]["strict_pass"]
    assert ev["status"] == "PASS"
    assert ev["scores"]["overall"] == 100
    assert ev["scores"]["plan_f1"] == 100
    assert ev["fail_kind"] == "pass"
    assert _by_id(ev, "requested_period")["status"] == "pass"
    assert _by_id(ev, "scope")["status"] == "pass"
    assert _by_id(ev, "item_ids")["status"] == "pass"


def test_remembering_02_this_week_in_judge_fails_period_not_items() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["judge"]["understanding"]["requested_period"] = {
        "start": "2026-11-09",
        "end": "2026-11-15",
        "reason": "Last Monday through Sunday is 9-15 November.",
    }
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "requested_period")["status"] == "fail"
    assert _by_id(ev, "scope")["status"] == "pass"
    assert _by_id(ev, "item_ids")["status"] == "pass"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_02_this_week_ids_fail_even_if_scope_matches_them() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["say"]["testimony"]["scope"] = {
        "start": "2026-11-09",
        "end": "2026-11-15",
    }
    payload["say"]["testimony"]["item_ids"] = [
        WEEK_INVOICE_ID,
        WEEK_PROPOSAL_ID,
        WEEK_FLIGHTS_ID,
    ]
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "requested_period")["status"] == "pass"
    assert _by_id(ev, "scope")["status"] == "fail"
    assert _by_id(ev, "item_ids")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_02_consistent_wrong_week_fails_each_layer() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["judge"]["understanding"]["requested_period"] = {
        "start": "2026-11-09",
        "end": "2026-11-15",
        "reason": "Previous calendar week is Monday 9 November to Sunday 15 November.",
    }
    payload["say"]["testimony"]["scope"] = {
        "start": "2026-11-09",
        "end": "2026-11-15",
    }
    payload["say"]["testimony"]["item_ids"] = [
        WEEK_INVOICE_ID,
        WEEK_PROPOSAL_ID,
        WEEK_FLIGHTS_ID,
    ]
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "requested_period")["status"] == "fail"
    assert _by_id(ev, "scope")["status"] == "fail"
    assert _by_id(ev, "item_ids")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_02_missing_requested_period_fails_judge() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["judge"]["understanding"]["requested_period"] = None
    ev = _score(payload, "remembering-02")
    assert ev["gates"]["schema_valid"]
    assert _by_id(ev, "requested_period")["status"] == "fail"
    assert _by_id(ev, "scope")["status"] == "pass"
    assert _by_id(ev, "item_ids")["status"] == "pass"


def test_remembering_02_including_standup_fails() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["say"]["testimony"]["item_ids"].append(WEEK_STANDUP_ID)
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "item_ids")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_02_including_out_of_week_fails() -> None:
    for extra in (
        WEEK_GYM_ID,
        WEEK_LANDING_ID,
        WEEK_PROPOSAL_ID,
        WEEK_FAMILY_ID,
        WEEK_DOCTOR_ID,
        WEEK_INVOICE_ID,
        WEEK_FLIGHTS_ID,
    ):
        payload = deepcopy(golden_remembering_02())
        payload["say"]["testimony"]["item_ids"].append(extra)
        ev = _score(payload, "remembering-02")
        assert _by_id(ev, "item_ids")["status"] == "fail", extra


def test_remembering_02_missing_completion_fails() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["say"]["testimony"]["item_ids"] = [WEEK_PRICING_ID]
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "item_ids")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_02_empty_purpose_reason_fails() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["say"]["testimony"]["purpose_reason"] = ""
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "purpose_reason")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_02_empty_aim_fails() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["say"]["testimony"]["aim"] = ""
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "aim")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_02_empty_scope_reason_fails() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["say"]["testimony"]["scope_reason"] = ""
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "scope_reason")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_02_empty_view_reason_fails() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["say"]["testimony"]["view_reason"] = ""
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "view_reason")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_02_any_view_passes() -> None:
    for view in ("inventory", "timeline", "outcomes", "patterns", "summary"):
        payload = deepcopy(golden_remembering_02())
        payload["say"]["testimony"]["view"] = view
        ev = _score(payload, "remembering-02")
        assert _by_id(ev, "view")["status"] == "pass", view
        assert ev["gates"]["strict_pass"], view


def test_remembering_02_search_items_is_variant() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["plan"]["tool_calls"] = [
        {"name": "search_items", "args": {"query": "last week"}}
    ]
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "no_tools")["status"] == "variant"
    assert _by_id(ev, "no_writes")["status"] == "pass"
    assert ev["scores"]["plan_f1"] == 100
    assert ev["gates"]["strict_pass"]


def test_remembering_02_add_item_fails() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["plan"]["tool_calls"] = [
        {"name": "add_item", "args": {"title": "Hit the gym", "type": "task"}}
    ]
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "no_writes")["status"] == "fail"
    assert ev["scores"]["plan_f1"] == 0
    assert ev["gates"]["strict_pass"] is False


def test_remembering_02_does_not_score_omitted_ids() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["say"]["testimony"]["omitted_ids"] = [WEEK_STANDUP_ID]
    payload["say"]["testimony"]["omitted_ids_reason"] = (
        "This item is scheduled for today but has not been marked as completed."
    )
    ev = _score(payload, "remembering-02")
    assert not any(
        row["id"] in {"omitted_ids", "omitted_ids_reason"}
        for group in ev["checks"].values()
        for row in group
    )
    assert _by_id(ev, "item_ids")["status"] == "pass"
    assert ev["gates"]["strict_pass"]


def test_remembering_02_priority_order_fails() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["say"]["testimony"]["order"] = "priority"
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "order")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_02_reverse_order_is_variant() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["say"]["testimony"]["order"] = "reverse_chronological"
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "order")["status"] == "variant"
    assert ev["gates"]["strict_pass"]


def test_remembering_02_header_listing_records_fails() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["say"]["text"] = (
        "Pricing shipped, investor coffee, expenses, and weekly review last week."
    )
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "header_not_records")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_02_scope_today_fails() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["say"]["testimony"]["scope"] = {"start": "2026-11-14", "end": "2026-11-14"}
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "scope")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_remembering_02_scope_last_week_passes() -> None:
    ev = _score(golden_remembering_02(), "remembering-02")
    assert ev["parsed"]["say"]["testimony"]["scope"] == {
        "start": LAST_WEEK_START,
        "end": LAST_WEEK_END,
    }
    assert _by_id(ev, "scope")["status"] == "pass"
    assert WEEK_EXPENSES_ID in ev["parsed"]["say"]["testimony"]["item_ids"]
    assert WEEK_REVIEW_ID in ev["parsed"]["say"]["testimony"]["item_ids"]
    assert WEEK_INVOICE_ID not in ev["parsed"]["say"]["testimony"]["item_ids"]


def test_remembering_02_empty_header_is_variant() -> None:
    payload = deepcopy(golden_remembering_02())
    payload["say"]["text"] = None
    ev = _score(payload, "remembering-02")
    assert _by_id(ev, "spoken_header")["status"] == "variant"
    assert _by_id(ev, "header_not_records")["status"] == "pass"
    assert ev["gates"]["strict_pass"]
