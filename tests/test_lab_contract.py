"""JSON / schema gates for the current judge/plan/say prompt contract."""

from __future__ import annotations

import json

from lab.contract import parse_json, validate_decision
from lab.evaluate import evaluate_decision
from lab.scenario import (
    golden_decision,
    golden_decision_07,
    golden_remembering_01,
    golden_remembering_02,
)


def _score(payload) -> dict:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return evaluate_decision(raw, input_rate=0.17, output_rate=0.25)


def test_golden_is_schema_valid() -> None:
    data, err = parse_json(json.dumps(golden_decision()))
    assert err is None
    decision, errors = validate_decision(data)
    assert decision is not None, errors


def test_malformed_json_fails_safely() -> None:
    ev = _score("{not json")
    assert ev["gates"]["json_valid"] is False
    assert ev["gates"]["schema_valid"] is False
    assert ev["gates"]["strict_pass"] is False
    assert ev["status"] == "FAIL"
    assert ev["parsed"] is None


def test_empty_output_fails() -> None:
    ev = _score("")
    assert ev["gates"]["json_valid"] is False


def test_fenced_json_accepted() -> None:
    blob = "```json\n" + json.dumps(golden_decision()) + "\n```"
    data, err = parse_json(blob)
    assert err is None
    assert data["say"]["types"] == ["confirmation"]


def test_obsolete_intent_schema_is_not_schema_valid() -> None:
    payload = {
        "intent": {"kind": "brain_dump", "summary": "x"},
        "write": {"target_ids": [], "missing": [], "conflicts": [], "duplicate_ids": []},
        "recall": {"intention": None, "shape": None, "order": None, "scope": {"start": None, "end": None}},
        "tool_calls": [],
        "response": {"type": "confirmation", "text": "", "show_ids": []},
    }
    ev = _score(payload)
    assert ev["gates"]["json_valid"] is True
    assert ev["gates"]["schema_valid"] is False


def test_missing_responsibilities_reason_fails_schema() -> None:
    payload = golden_decision()
    del payload["judge"]["understanding"]["responsibilities_reason"]
    ev = _score(payload)
    assert ev["gates"]["schema_valid"] is False


def test_unknown_field_rejected() -> None:
    payload = golden_decision()
    payload["extra"] = True
    ev = _score(payload)
    assert ev["gates"]["schema_valid"] is False


def test_invalid_tool_name_fails_schema() -> None:
    payload = golden_decision()
    payload["plan"]["tool_calls"][0] = {"name": "delete_item", "args": {"id": "itm_0000000000000001"}}
    ev = _score(payload)
    assert ev["gates"]["schema_valid"] is False


def test_silence_say_type_is_schema_valid() -> None:
    payload = golden_decision_07()
    assert payload["say"]["types"] == ["silence"]
    data, err = parse_json(json.dumps(payload))
    assert err is None
    decision, errors = validate_decision(data)
    assert decision is not None, errors


def test_missing_purpose_reason_fails_schema() -> None:
    payload = golden_remembering_01()
    del payload["say"]["testimony"]["purpose_reason"]
    data, err = parse_json(json.dumps(payload))
    assert err is None
    decision, errors = validate_decision(data)
    assert decision is None
    assert errors


def test_missing_aim_fails_schema() -> None:
    payload = golden_remembering_01()
    del payload["say"]["testimony"]["aim"]
    data, err = parse_json(json.dumps(payload))
    assert err is None
    decision, errors = validate_decision(data)
    assert decision is None
    assert errors


def test_missing_view_reason_fails_schema() -> None:
    payload = golden_remembering_01()
    del payload["say"]["testimony"]["view_reason"]
    data, err = parse_json(json.dumps(payload))
    assert err is None
    decision, errors = validate_decision(data)
    assert decision is None
    assert errors


def test_missing_scope_reason_fails_schema() -> None:
    payload = golden_remembering_01()
    del payload["say"]["testimony"]["scope_reason"]
    data, err = parse_json(json.dumps(payload))
    assert err is None
    decision, errors = validate_decision(data)
    assert decision is None
    assert errors


def test_requested_period_is_optional_in_schema() -> None:
    payload = golden_remembering_02()
    payload["judge"]["understanding"]["requested_period"] = None
    data, err = parse_json(json.dumps(payload))
    assert err is None
    decision, errors = validate_decision(data)
    assert decision is not None, errors


def test_remembering_02_golden_is_schema_valid() -> None:
    data, err = parse_json(json.dumps(golden_remembering_02()))
    assert err is None
    decision, errors = validate_decision(data)
    assert decision is not None, errors


def test_testimony_type_requires_payload() -> None:
    payload = golden_remembering_01()
    payload["say"]["types"] = ["testimony"]
    payload["say"]["testimony"] = None
    ev = _score(payload)
    assert ev["gates"]["json_valid"] is True
    assert ev["gates"]["schema_valid"] is False
    assert ev["fail_kind"] == "schema"
    assert any("Testimony payload required" in err for err in ev["schema_errors"])


def test_testimony_payload_without_type_is_schema_valid() -> None:
    payload = golden_decision()
    payload["say"]["testimony"] = {
        "aim": "What remains to be dealt with.",
        "purpose_reason": "The founder asked what remains to be dealt with.",
        "view": "inventory",
        "view_reason": "Inventory lists remaining work.",
        "order": "natural",
        "scope": {"start": None, "end": None},
        "scope_reason": "No period was asked.",
        "item_ids": [],
        "item_ids_reason": "No records selected.",
        "omitted_ids": [],
        "omitted_ids_reason": None,
    }
    data, err = parse_json(json.dumps(payload))
    assert err is None
    decision, errors = validate_decision(data)
    assert decision is not None, errors


def test_invalid_item_id_fails_schema() -> None:
    payload = golden_decision()
    payload["plan"]["tool_calls"][0]["args"]["id"] = "Chase Acme"
    ev = _score(payload)
    assert ev["gates"]["schema_valid"] is False
