"""Deterministic semantic evaluator for Scenario 01."""

from __future__ import annotations

import json
from copy import deepcopy

from lab.evaluate import evaluate_decision
from lab.scenario import (
    ACME_ID,
    EXPECTED_DUE,
    LOGIN_ID,
    VEE_S01_REPLY,
    VEE_S02_REPLY,
    VEE_S03_REPLY,
    VEE_S04_REPLY,
    VEE_S05_REPLY,
    VEE_S06_REPLY,
    VEE_S06_HELD_REPLY,
    MSG_06,
    get_scenario,
    list_scenarios,
    golden_decision,
    golden_decision_02,
    golden_decision_03,
    golden_decision_04,
    golden_decision_05,
    golden_decision_06,
    golden_decision_07,
    ANGEL_ID,
    FAMILY_ID,
    FAMILY_MOVED,
    GYM_ID,
)


def _score(payload) -> dict:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return evaluate_decision(raw, input_rate=0.17, output_rate=0.25)


def _by_id(ev: dict, check_id: str) -> dict:
    for group in ev["checks"].values():
        for row in group:
            if row["id"] == check_id:
                return row
    raise KeyError(check_id)


def test_witness_and_testify_both_ok() -> None:
    payload = golden_decision()
    payload["judge"]["understanding"]["responsibilities"] = ["witness", "testify"]
    payload["judge"]["understanding"]["responsibilities_reason"] = (
        "The founder is reporting work-state changes; both witnessing and testifying apply."
    )
    ev = _score(payload)
    assert _by_id(ev, "responsibility")["status"] == "pass"
    assert ev["gates"]["strict_pass"]


def test_testify_only_still_fails() -> None:
    payload = golden_decision()
    payload["judge"]["understanding"]["responsibilities"] = ["testify"]
    ev = _score(payload)
    assert _by_id(ev, "responsibility")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_golden_strict_pass() -> None:
    ev = _score(golden_decision())
    assert ev["gates"]["json_valid"]
    assert ev["gates"]["schema_valid"]
    assert ev["gates"]["strict_pass"]
    assert ev["status"] == "PASS"
    assert ev["scores"]["overall"] == 100


def test_rearranged_tool_calls_pass() -> None:
    payload = golden_decision()
    payload["plan"]["tool_calls"] = list(reversed(payload["plan"]["tool_calls"]))
    ev = _score(payload)
    assert ev["gates"]["strict_pass"]
    assert ev["scores"]["plan_f1"] == 100


def test_optional_work_mode_is_variant_not_fail() -> None:
    payload = golden_decision()
    payload["plan"]["tool_calls"][1]["args"]["work_mode"] = "personal"
    ev = _score(payload)
    assert ev["gates"]["strict_pass"]
    assert _by_id(ev, "add_gym")["status"] in {"pass", "variant"}


def test_wrong_item_id_fails() -> None:
    payload = golden_decision()
    payload["plan"]["tool_calls"][0]["args"]["id"] = "itm_0000000000000002"
    ev = _score(payload)
    assert ev["gates"]["schema_valid"]
    assert ev["gates"]["strict_pass"] is False
    assert _by_id(ev, "update_acme")["status"] == "fail"
    assert ev["scores"]["plan_f1"] < 100


def test_wrong_due_at_fails() -> None:
    payload = golden_decision()
    payload["plan"]["tool_calls"][0]["args"]["due_at"] = "2026-11-06T23:59:59+00:00"
    ev = _score(payload)
    assert _by_id(ev, "update_acme")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_extra_invented_tool_call_lowers_score() -> None:
    payload = golden_decision()
    payload["plan"]["tool_calls"].append(
        {"name": "add_item", "args": {"title": "Write a novel", "type": "task"}}
    )
    ev = _score(payload)
    assert ev["gates"]["strict_pass"] is False
    assert _by_id(ev, "no_extra")["status"] == "fail"
    assert ev["scores"]["plan_precision"] < 100
    assert ev["scores"]["plan_recall"] == 100
    assert ev["scores"]["plan_f1"] < 100


def test_coaching_detected() -> None:
    payload = golden_decision()
    payload["say"]["text"] = "Recorded. You should also block time to focus tomorrow!"
    ev = _score(payload)
    assert _by_id(ev, "no_advice")["status"] == "fail"
    assert ev["gates"]["strict_pass"] is False


def test_success_claim_detected() -> None:
    payload = golden_decision()
    payload["say"]["text"] = "I added the gym and saved it to the database."
    ev = _score(payload)
    assert _by_id(ev, "no_success_claim")["status"] == "fail"


def test_acknowledgement_is_not_a_schema_say_type() -> None:
    payload = golden_decision()
    payload["say"]["types"] = ["acknowledgement"]
    payload["say"]["text"] = "Got it."
    ev = _score(payload)
    assert ev["gates"]["json_valid"] is True
    assert ev["gates"]["schema_valid"] is False
    assert ev["gates"]["strict_pass"] is False


def test_title_variant_still_matches() -> None:
    payload = golden_decision()
    payload["plan"]["tool_calls"][1]["args"]["title"] = "Gym"
    ev = _score(payload)
    assert _by_id(ev, "add_gym")["status"] == "variant"
    assert ev["gates"]["strict_pass"]


def test_golden_fail_kind_is_pass() -> None:
    ev = _score(golden_decision())
    assert ev["fail_kind"] == "pass"


def test_high_score_without_strict_pass_is_close() -> None:
    from lab.scenario import golden_remembering_02

    payload = deepcopy(golden_remembering_02())
    payload["say"]["testimony"]["purpose_reason"] = ""
    ev = evaluate_decision(
        json.dumps(payload),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="remembering-02",
    )
    assert ev["gates"]["json_valid"]
    assert ev["gates"]["schema_valid"]
    assert ev["gates"]["strict_pass"] is False
    assert ev["scores"]["overall"] >= 90
    assert ev["status"] == "CLOSE"
    assert ev["fail_kind"] == "close"


def test_connection_error_is_classified() -> None:
    ev = evaluate_decision(
        "",
        input_rate=0.17,
        output_rate=0.25,
        error="Connection error.",
    )
    assert ev["fail_kind"] == "connection"
    assert ev["status"] == "FAIL"


def test_schema_fail_kind() -> None:
    ev = _score({"judge": {}, "plan": {}, "say": {}})
    assert ev["fail_kind"] == "schema"


def test_does_not_invent_token_counts() -> None:
    ev = evaluate_decision(
        json.dumps(golden_decision()),
        input_rate=0.17,
        output_rate=0.25,
        usage={},
        latency={"total_s": 1.2},
    )
    assert ev["usage"]["input_tokens"] is None
    assert ev["usage"]["output_tokens"] is None
    assert ev["usage"]["cost_usd"] is None


def test_scenario_02_golden_strict_pass() -> None:
    ev = evaluate_decision(
        json.dumps(golden_decision_02()),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-02",
    )
    assert ev["gates"]["strict_pass"]
    assert ev["fail_kind"] == "pass"
    assert ev["scores"]["plan_f1"] == 100
    assert _by_id(ev, "asks_time")["status"] == "pass"


def test_scenario_02_write_without_time_fails() -> None:
    payload = golden_decision_02()
    payload["plan"]["tool_calls"] = [
        {
            "name": "add_item",
            "args": {"title": "Family meeting", "type": "event"},
        }
    ]
    payload["say"]["types"] = ["confirmation"]
    payload["say"]["text"] = "Recorded:"
    ev = evaluate_decision(
        json.dumps(payload),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-02",
    )
    assert ev["gates"]["strict_pass"] is False
    assert _by_id(ev, "no_tools")["status"] == "fail"
    assert _by_id(ev, "response_type")["status"] == "fail"


def test_scenario_03_fixture_includes_s02_reply() -> None:
    state = get_scenario("brain-dump-03").interaction_state
    assert '"7pm"' in state
    assert "add family meeting today" in state
    assert VEE_S02_REPLY in state
    assert "10:32, 6 November 2026" in state


def test_scenario_03_golden_strict_pass() -> None:
    ev = evaluate_decision(
        json.dumps(golden_decision_03()),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-03",
    )
    assert ev["gates"]["strict_pass"]
    assert ev["fail_kind"] == "pass"
    assert ev["scores"]["plan_f1"] == 100
    assert _by_id(ev, "add_family_event")["status"] == "pass"


def test_scenario_03_wrong_start_fails() -> None:
    payload = golden_decision_03()
    payload["plan"]["tool_calls"][0]["args"]["start_at"] = "2026-11-06T18:00:00+00:00"
    ev = evaluate_decision(
        json.dumps(payload),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-03",
    )
    assert ev["gates"]["strict_pass"] is False
    assert _by_id(ev, "add_family_event")["status"] == "fail"


def test_scenario_04_fixture_continues_s03() -> None:
    state = get_scenario("brain-dump-04").interaction_state
    assert "Angel investor" in state or "angel investor" in state
    assert "fix the login bug" in state
    assert VEE_S02_REPLY in state
    assert VEE_S03_REPLY in state
    assert '"7pm"' in state or "Founder: 7pm" in state
    assert LOGIN_ID in state
    assert "Family meeting" in state
    assert "10:40, 6 November 2026" in state


def test_scenario_04_golden_strict_pass() -> None:
    ev = evaluate_decision(
        json.dumps(golden_decision_04()),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-04",
    )
    assert ev["gates"]["strict_pass"]
    assert ev["fail_kind"] == "pass"
    assert ev["scores"]["plan_f1"] == 100
    assert _by_id(ev, "add_angel_event")["status"] == "pass"
    assert _by_id(ev, "no_login_add")["status"] == "pass"


def test_scenario_04_unnoted_duplicate_still_passes() -> None:
    payload = golden_decision_04()
    payload["say"]["text"] = "Recorded:"
    payload["judge"]["evidence"]["record_findings"] = [
        row
        for row in payload["judge"]["evidence"]["record_findings"]
        if "login" not in row["piece_of_work"].lower()
    ]
    ev = evaluate_decision(
        json.dumps(payload),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-04",
    )
    assert ev["gates"]["strict_pass"]
    assert _by_id(ev, "no_login_add")["status"] == "pass"


def test_scenario_04_testimony_type_without_payload_fails_schema() -> None:
    payload = golden_decision_04()
    payload["say"]["types"] = ["confirmation", "testimony"]
    payload["say"]["testimony"] = None
    ev = evaluate_decision(
        json.dumps(payload),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-04",
    )
    assert ev["gates"]["schema_valid"] is False
    assert ev["fail_kind"] == "schema"
    assert ev["gates"]["strict_pass"] is False


def test_scenario_04_adding_login_again_fails() -> None:
    payload = golden_decision_04()
    payload["plan"]["tool_calls"].append(
        {"name": "add_item", "args": {"title": "Fix the login bug", "type": "task"}}
    )
    ev = evaluate_decision(
        json.dumps(payload),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-04",
    )
    assert ev["gates"]["strict_pass"] is False
    assert _by_id(ev, "no_login_add")["status"] == "fail"


def test_scenario_05_fixture_chains_through_04() -> None:
    state = get_scenario("brain-dump-05").interaction_state
    assert "done with the angel investor meeting" in state
    assert VEE_S01_REPLY in state
    assert VEE_S02_REPLY in state
    assert VEE_S03_REPLY in state
    assert VEE_S04_REPLY in state
    assert "Founder: add family meeting today" in state
    assert "Founder: 7pm" in state
    assert "angel investor meeting" in state.lower()
    assert FAMILY_ID in state
    assert ANGEL_ID in state
    assert "21:16, 6 November 2026" in state
    assert {s["id"] for s in list_scenarios()} == {
        "brain-dump-01",
        "brain-dump-02",
        "brain-dump-03",
        "brain-dump-04",
        "brain-dump-05",
        "brain-dump-06",
        "brain-dump-07",
        "remembering-01",
        "remembering-02",
    }


def test_resolve_interaction_state_replaces_current_message() -> None:
    from lab.scenario import resolve_interaction_state

    state = resolve_interaction_state("remembering-02", "what did I complete today?")
    assert 'Current message:\n"what did I complete today?"' in state
    assert "What did I get done last week?" not in state
    assert "Ship pricing page" in state
    assert "16:45, Saturday 14 November 2026" in state
    same = resolve_interaction_state("remembering-02", None)
    assert 'Current message:\n"What did I get done last week?"' in same
    assert "This calendar week (current week):" in same
    assert "2026-11-09 → 2026-11-15" in same
    assert "Last calendar week (previous week):" in same
    assert "2026-11-02 → 2026-11-08" in same


def test_week_bounds_follow_monday_sunday_from_clock() -> None:
    from lab.fixtures.common import week_bounds_for_clock

    weeks = week_bounds_for_clock("16:45, Saturday 14 November 2026, Europe/London")
    assert weeks["this_week"] == ("2026-11-09", "2026-11-15")
    assert weeks["last_week"] == ("2026-11-02", "2026-11-08")
    dump = week_bounds_for_clock("10:30, 6 November 2026")
    assert dump["this_week"] == ("2026-11-02", "2026-11-08")
    assert dump["last_week"] == ("2026-10-26", "2026-11-01")


def test_scenario_05_golden_strict_pass() -> None:
    ev = evaluate_decision(
        json.dumps(golden_decision_05()),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-05",
    )
    assert ev["gates"]["strict_pass"]
    assert ev["fail_kind"] == "pass"
    assert ev["scores"]["plan_f1"] == 100
    assert _by_id(ev, "complete_angel")["status"] == "pass"
    assert _by_id(ev, "move_family")["status"] == "pass"


def test_scenario_05_dropped_gym_passes() -> None:
    payload = golden_decision_05()
    for call in payload["plan"]["tool_calls"]:
        args = call.get("args") or {}
        if args.get("id") == GYM_ID:
            args["status"] = "dropped"
    ev = evaluate_decision(
        json.dumps(payload),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-05",
    )
    assert ev["gates"]["strict_pass"]
    assert _by_id(ev, "cancel_gym")["status"] == "variant"


def test_scenario_05_family_today_fails() -> None:
    payload = golden_decision_05()
    for call in payload["plan"]["tool_calls"]:
        args = call.get("args") or {}
        if args.get("id") == FAMILY_ID:
            args["start_at"] = "2026-11-06T17:00:00+00:00"
    ev = evaluate_decision(
        json.dumps(payload),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-05",
    )
    assert ev["gates"]["strict_pass"] is False
    assert _by_id(ev, "move_family")["status"] == "fail"


def test_scenario_05_missing_angel_complete_fails() -> None:
    payload = golden_decision_05()
    payload["plan"]["tool_calls"] = [
        c
        for c in payload["plan"]["tool_calls"]
        if (c.get("args") or {}).get("id") != ANGEL_ID
    ]
    ev = evaluate_decision(
        json.dumps(payload),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-05",
    )
    assert ev["gates"]["strict_pass"] is False
    assert _by_id(ev, "complete_angel")["status"] == "fail"


def test_scenario_06_fixture_chains_s05_reply() -> None:
    state = get_scenario("brain-dump-06").interaction_state
    assert MSG_06 in state
    assert VEE_S05_REPLY in state
    assert "tomorrow (Nov 7) at 5 PM" in state
    assert FAMILY_MOVED in state
    assert "cancelled" in state
    assert "completed" in state
    assert "21:20, 6 November 2026" in state


def test_scenario_06_golden_strict_pass() -> None:
    ev = evaluate_decision(
        json.dumps(golden_decision_06()),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-06",
    )
    assert ev["gates"]["strict_pass"]
    assert ev["fail_kind"] == "pass"
    assert _by_id(ev, "conflicting_facts")["status"] == "pass"
    assert _by_id(ev, "asks_which_time")["status"] == "pass"


def test_scenario_06_overwrite_3pm_fails() -> None:
    payload = golden_decision_06()
    payload["plan"]["tool_calls"] = [
        {
            "name": "update_item",
            "args": {"id": FAMILY_ID, "start_at": "2026-11-07T15:00:00+00:00"},
        }
    ]
    payload["judge"]["decision"]["required_actions"] = [
        {
            "action": "update",
            "item_id": FAMILY_ID,
            "piece_of_work": "Family meeting",
            "reason": "Change to 3pm.",
        }
    ]
    payload["say"]["types"] = ["confirmation"]
    payload["say"]["text"] = "Recorded:"
    ev = evaluate_decision(
        json.dumps(payload),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-06",
    )
    assert ev["gates"]["strict_pass"] is False
    assert _by_id(ev, "no_overwrite")["status"] == "fail"
    assert _by_id(ev, "clarify_not_write")["status"] == "fail"


def test_scenario_06_clear_start_passes() -> None:
    payload = golden_decision_06()
    payload["plan"]["tool_calls"] = [
        {"name": "update_item", "args": {"id": FAMILY_ID, "start_at": None}}
    ]
    payload["judge"]["decision"]["required_actions"] = [
        {
            "action": "update",
            "item_id": FAMILY_ID,
            "piece_of_work": "Family meeting",
            "reason": "Time is unconfirmed; clear start_at.",
        }
    ]
    payload["say"]["types"] = ["confirmation"]
    payload["say"]["text"] = "Recorded the family meeting time as unconfirmed."
    ev = evaluate_decision(
        json.dumps(payload),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-06",
    )
    assert ev["gates"]["strict_pass"]
    assert _by_id(ev, "no_overwrite")["status"] == "pass"
    assert _by_id(ev, "clarify_not_write")["status"] == "pass"


def test_scenario_06_missing_information_is_variant() -> None:
    payload = golden_decision_06()
    payload["judge"]["evidence"]["uncertainties"][0]["type"] = "missing_information"
    ev = evaluate_decision(
        json.dumps(payload),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-06",
    )
    assert ev["gates"]["strict_pass"]
    assert _by_id(ev, "conflicting_facts")["status"] == "variant"


def test_scenario_07_fixture_keeps_open_question() -> None:
    state = get_scenario("brain-dump-07").interaction_state
    assert '"how are you"' in state
    assert VEE_S06_HELD_REPLY in state
    assert VEE_S06_REPLY not in state
    assert "?" not in VEE_S06_HELD_REPLY
    assert VEE_S05_REPLY in state
    assert MSG_06 in state
    assert VEE_S01_REPLY not in state
    assert FAMILY_MOVED in state
    assert "21:21, 6 November 2026" in state


def test_scenario_07_golden_strict_pass() -> None:
    ev = evaluate_decision(
        json.dumps(golden_decision_07()),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-07",
    )
    assert ev["gates"]["strict_pass"]
    assert ev["fail_kind"] == "pass"
    assert _by_id(ev, "silent_text")["status"] == "pass"
    assert _by_id(ev, "response_type")["status"] == "pass"
    assert _by_id(ev, "responsibility")["status"] == "pass"


def test_scenario_07_empty_types_is_variant() -> None:
    payload = golden_decision_07()
    payload["say"]["types"] = []
    ev = evaluate_decision(
        json.dumps(payload),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-07",
    )
    assert ev["gates"]["strict_pass"]
    assert _by_id(ev, "response_type")["status"] == "variant"


def test_scenario_07_greeting_fails() -> None:
    payload = golden_decision_07()
    payload["say"]["types"] = ["confirmation"]
    payload["say"]["text"] = "I'm well, thanks."
    ev = evaluate_decision(
        json.dumps(payload),
        input_rate=0.17,
        output_rate=0.25,
        scenario_id="brain-dump-07",
    )
    assert ev["gates"]["strict_pass"] is False
    assert _by_id(ev, "silent_text")["status"] == "fail"
    assert _by_id(ev, "response_type")["status"] == "fail"


def test_copy_is_independent() -> None:
    a = golden_decision()
    b = deepcopy(a)
    a["say"]["text"] = "mutated"
    assert b["say"]["text"] == "Recorded:"
    assert EXPECTED_DUE.endswith("+00:00")
    assert ACME_ID.startswith("itm_")
