"""M4a — Decision parse/validate + safe_fallback (no network)."""

from __future__ import annotations

import json

import pytest

from llm import accept_model_output, parse_and_validate, safe_fallback
from llm.fallback import FALLBACK_RESPONSE_TEXT
from llm.validate import DecisionValidationError


def _valid_think_payload() -> dict:
    return {
        "intent": {
            "kind": "brain_dump",
            "summary": "Add call the doctor as an open task.",
        },
        "write": {
            "target_ids": [],
            "missing": [],
            "conflicts": [],
            "duplicate_ids": [],
        },
        "recall": {
            "intention": None,
            "shape": None,
            "order": None,
            "scope": {"start": None, "end": None},
        },
        "tool_calls": [
            {
                "name": "add_item",
                "args": {
                    "title": "Call the doctor",
                    "type": "task",
                    "status": "todo",
                },
            }
        ],
        "response": {
            "type": "confirmation",
            "text": "Witnessed: Call the doctor.",
            "show_ids": [],
        },
    }


def test_f1_valid_json_accepted() -> None:
    decision = parse_and_validate(json.dumps(_valid_think_payload()))
    assert decision.intent.kind == "brain_dump"
    assert decision.intent.summary.startswith("Add call the doctor")
    assert len(decision.tool_calls) == 1
    assert decision.tool_calls[0].name == "add_item"


def test_f2_fenced_json_accepted() -> None:
    body = json.dumps(_valid_think_payload())
    fenced = f"```json\n{body}\n```"
    decision = accept_model_output(fenced)
    assert decision.intent.kind == "brain_dump"
    assert decision.response.type == "confirmation"


def test_f3_invalid_json_fallback() -> None:
    decision = accept_model_output("not json at all")
    assert decision.response.type == "clarification"
    assert decision.response.text == FALLBACK_RESPONSE_TEXT
    assert decision.tool_calls == []


def test_f4_unknown_tool_fallback() -> None:
    payload = _valid_think_payload()
    payload["tool_calls"] = [
        {"name": "delete_item", "args": {"id": "itm_1"}}
    ]
    decision = accept_model_output(json.dumps(payload))
    assert decision.response.type == "clarification"
    assert decision.tool_calls == []


def test_f5_uncertain_write_empty_tools_accepted() -> None:
    """Certainty is blockers + empty tool_calls; no can_apply flag."""
    payload = _valid_think_payload()
    payload["write"] = {
        "target_ids": [],
        "missing": [
            {
                "field": "start_at",
                "for": "family meeting",
                "reason": "event mentioned without a time",
            }
        ],
        "conflicts": [],
        "duplicate_ids": [],
    }
    payload["tool_calls"] = []
    payload["response"] = {
        "type": "clarification",
        "text": "What time is the family meeting?",
        "show_ids": [],
    }
    decision = parse_and_validate(json.dumps(payload))
    assert decision.tool_calls == []
    assert decision.write.missing[0].field == "start_at"
    assert decision.response.type == "clarification"


def test_f6_legacy_can_apply_field_rejected() -> None:
    payload = _valid_think_payload()
    payload["write"]["can_apply"] = True
    decision = accept_model_output(json.dumps(payload))
    assert decision.response.type == "clarification"


def test_legacy_operation_field_rejected() -> None:
    payload = _valid_think_payload()
    payload["write"]["operation"] = "add"
    decision = accept_model_output(json.dumps(payload))
    assert decision.response.type == "clarification"


def test_invalid_item_id_shape_fallback() -> None:
    payload = _valid_think_payload()
    payload["write"]["target_ids"] = ["item_001"]
    payload["tool_calls"] = []
    decision = accept_model_output(json.dumps(payload))
    assert decision.response.type == "clarification"


def test_show_ids_must_be_db_item_ids() -> None:
    payload = _valid_think_payload()
    payload["response"]["show_ids"] = ["Ship landing page"]
    decision = accept_model_output(json.dumps(payload))
    assert decision.response.type == "clarification"


def test_valid_target_and_show_ids_accepted() -> None:
    payload = _valid_think_payload()
    item_id = "itm_a1b2c3d4e5f67890"
    payload["write"]["target_ids"] = [item_id]
    payload["tool_calls"] = [
        {
            "name": "update_item",
            "args": {"id": item_id, "status": "completed"},
        }
    ]
    payload["response"]["show_ids"] = [item_id]
    decision = parse_and_validate(json.dumps(payload))
    assert decision.write.target_ids == [item_id]
    assert decision.response.show_ids == [item_id]


def test_bonus_lens_rejected() -> None:
    payload = _valid_think_payload()
    payload["lens"] = {"intention": "alignment"}
    decision = accept_model_output(json.dumps(payload))
    assert decision.response.type == "clarification"


def test_bonus_date_range_rejected() -> None:
    payload = _valid_think_payload()
    payload["recall"] = {
        "intention": "alignment",
        "shape": "inventory",
        "order": None,
        "date_range": {"start": "2026-07-15", "end": "2026-07-15"},
    }
    decision = accept_model_output(json.dumps(payload))
    assert decision.response.type == "clarification"


def test_parse_and_validate_raises() -> None:
    with pytest.raises(DecisionValidationError):
        parse_and_validate("{")


def test_safe_fallback_stable() -> None:
    decision = safe_fallback("unit-test")
    assert decision.intent.kind == "irrelevant"
    assert decision.response.type == "clarification"
    assert decision.recall.scope.start is None
    assert decision.tool_calls == []


def test_flat_intent_string_rejected() -> None:
    """Legacy flat intent + top-level summary must not validate."""
    payload = _valid_think_payload()
    payload["intent"] = "brain_dump"
    payload["summary"] = "Add call the doctor as an open task."
    decision = accept_model_output(json.dumps(payload))
    assert decision.response.type == "clarification"


def _remember_payload() -> dict:
    payload = _valid_think_payload()
    payload["intent"] = {"kind": "remember", "summary": "See what I completed last week."}
    payload["recall"] = {
        "intention": "reflection",
        "shape": "outcome",
        "order": "chronological",
        "scope": {"start": "2026-10-12", "end": "2026-10-18"},
    }
    payload["tool_calls"] = [
        {
            "name": "search_items",
            "args": {
                "status": "completed",
                "updated": {"after": "2026-10-12", "before": "2026-10-18"},
            },
        }
    ]
    payload["response"] = {"type": "testify", "text": "Last week, you:", "show_ids": []}
    return payload


def test_search_items_accepted_when_remembering() -> None:
    decision = parse_and_validate(json.dumps(_remember_payload()))
    assert decision.tool_calls[0].name == "search_items"
    assert decision.tool_calls[0].args.status == ["completed"]


def test_search_items_accepted_when_brain_dumping() -> None:
    payload = _valid_think_payload()
    payload["tool_calls"].insert(0, {"name": "search_items", "args": {"query": "doctor"}})
    decision = parse_and_validate(json.dumps(payload))
    assert [c.name for c in decision.tool_calls] == ["search_items", "add_item"]


def test_continuity_field_rejected() -> None:
    payload = _valid_think_payload()
    payload["continuity"] = {"summary": "Idle — new brain dump."}
    decision = accept_model_output(json.dumps(payload))
    assert decision.response.type == "clarification"


def test_legacy_view_field_rejected() -> None:
    payload = _valid_think_payload()
    payload["view"] = payload.pop("recall")
    decision = accept_model_output(json.dumps(payload))
    assert decision.response.type == "clarification"


def test_legacy_write_tool_calls_rejected() -> None:
    payload = _valid_think_payload()
    payload["write"]["tool_calls"] = payload.pop("tool_calls")
    decision = accept_model_output(json.dumps(payload))
    assert decision.response.type == "clarification"

