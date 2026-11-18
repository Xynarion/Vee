"""M4a — Decision parse/validate + safe_fallback (no network)."""

from __future__ import annotations

import json

import pytest

from lab.scenario import (
    ACME_ID,
    golden_decision,
    golden_decision_07,
    golden_remembering_01,
    golden_remembering_02,
)
from llm import accept_model_output, parse_and_validate, safe_fallback
from llm.fallback import FALLBACK_RESPONSE_TEXT
from llm.validate import DecisionValidationError

ITEM_ID = "itm_a1b2c3d4e5f67890"


def _valid_payload() -> dict:
    return {
        "judge": {
            "understanding": {
                "continuity": None,
                "message_meaning_summary": "Founder reports a new doctor call as open work.",
                "responsibilities": ["witness"],
                "responsibilities_reason": "The founder is reporting new work, not asking for progress.",
                "requested_period": None,
            },
            "evidence": {
                "record_findings": [
                    {
                        "piece_of_work": "Call the doctor",
                        "match_status": "new",
                        "item_id": None,
                        "finding": "No existing doctor-call item.",
                    }
                ],
                "uncertainties": [],
            },
            "decision": {
                "required_actions": [
                    {
                        "action": "create",
                        "item_id": None,
                        "piece_of_work": "Call the doctor",
                        "reason": "New task reported.",
                    }
                ]
            },
        },
        "plan": {
            "tool_calls": [
                {
                    "name": "add_item",
                    "args": {
                        "title": "Call the doctor",
                        "type": "task",
                        "status": "todo",
                    },
                }
            ]
        },
        "say": {
            "types": ["confirmation"],
            "text": "Recorded: Call the doctor.",
            "testimony": None,
        },
    }


def _clarify_payload() -> dict:
    payload = _valid_payload()
    payload["judge"]["understanding"]["message_meaning_summary"] = (
        "Founder wants a family meeting added today; no start time was given."
    )
    payload["judge"]["evidence"] = {
        "record_findings": [
            {
                "piece_of_work": "Family meeting",
                "match_status": "new",
                "item_id": None,
                "finding": "Event reported without a start time.",
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
    }
    payload["judge"]["decision"]["required_actions"] = [
        {
            "action": "clarify",
            "item_id": None,
            "piece_of_work": "Family meeting",
            "reason": "Events require start_at; only the day was reported.",
        }
    ]
    payload["plan"]["tool_calls"] = []
    payload["say"] = {
        "types": ["clarification"],
        "text": "What time is the family meeting today?",
        "testimony": None,
    }
    return payload


def _remember_payload() -> dict:
    return {
        "judge": {
            "understanding": {
                "continuity": None,
                "message_meaning_summary": "Founder asked what they completed last week.",
                "responsibilities": ["testify"],
                "responsibilities_reason": "This is a question about recorded progress.",
                "requested_period": {
                    "start": "2026-10-12",
                    "end": "2026-10-18",
                    "reason": "Today is Monday 19 October 2026. Last week is 12-18 October.",
                },
            },
            "evidence": {
                "record_findings": [],
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
        "plan": {
            "tool_calls": [
                {
                    "name": "search_items",
                    "args": {
                        "status": "completed",
                        "updated": {"after": "2026-10-12", "before": "2026-10-18"},
                    },
                }
            ]
        },
        "say": {
            "types": ["testimony"],
            "text": "Last week, you:",
            "testimony": {
                "aim": "What the founder completed last week.",
                "purpose_reason": "The founder asked what they got done last week.",
                "view": "outcomes",
                "view_reason": "Outcomes show completed work in that period.",
                "order": "chronological",
                "scope": {"start": "2026-10-12", "end": "2026-10-18"},
                "scope_reason": "Last week is Monday 12 through Sunday 18 October.",
                "item_ids": [],
                "item_ids_reason": "No records selected yet; search is planned.",
                "omitted_ids": [],
                "omitted_ids_reason": None,
            },
        },
    }


def test_f1_valid_json_accepted() -> None:
    decision = parse_and_validate(json.dumps(_valid_payload()))
    assert decision.judge.understanding.responsibilities == ["witness"]
    assert decision.say.types == ["confirmation"]
    assert len(decision.plan.tool_calls) == 1
    assert decision.plan.tool_calls[0].name == "add_item"


def test_f2_fenced_json_accepted() -> None:
    body = json.dumps(_valid_payload())
    fenced = f"```json\n{body}\n```"
    decision = accept_model_output(fenced)
    assert decision.say.types == ["confirmation"]
    assert decision.plan.tool_calls[0].name == "add_item"


def test_surrounding_text_json_extracted() -> None:
    body = "Here you go:\n" + json.dumps(_valid_payload()) + "\nThanks."
    decision = parse_and_validate(body)
    assert decision.say.types == ["confirmation"]


def test_f3_invalid_json_fallback() -> None:
    decision = accept_model_output("not json at all")
    assert decision.say.types == ["clarification"]
    assert decision.say.text == FALLBACK_RESPONSE_TEXT
    assert decision.plan.tool_calls == []
    assert decision.judge.understanding.responsibilities == []


def test_f4_unknown_tool_fallback() -> None:
    payload = _valid_payload()
    payload["plan"]["tool_calls"] = [{"name": "delete_item", "args": {"id": "itm_1"}}]
    decision = accept_model_output(json.dumps(payload))
    assert decision.say.types == ["clarification"]
    assert decision.plan.tool_calls == []


def test_f5_clarify_empty_tools_accepted() -> None:
    decision = parse_and_validate(json.dumps(_clarify_payload()))
    assert decision.plan.tool_calls == []
    assert decision.say.types == ["clarification"]
    assert decision.judge.evidence.uncertainties[0].type == "missing_information"


def test_unknown_field_rejected() -> None:
    payload = _valid_payload()
    payload["intent"] = {"kind": "brain_dump", "summary": "x"}
    decision = accept_model_output(json.dumps(payload))
    assert decision.say.types == ["clarification"]


def test_obsolete_intent_schema_rejected() -> None:
    payload = {
        "intent": {"kind": "brain_dump", "summary": "Add call the doctor as an open task."},
        "write": {"target_ids": [], "missing": [], "conflicts": [], "duplicate_ids": []},
        "recall": {"intention": None, "shape": None, "order": None, "scope": {"start": None, "end": None}},
        "tool_calls": [],
        "response": {"type": "confirmation", "text": "", "show_ids": []},
    }
    decision = accept_model_output(json.dumps(payload))
    assert decision.say.types == ["clarification"]
    assert decision.plan.tool_calls == []


def test_invalid_item_id_shape_fallback() -> None:
    payload = _valid_payload()
    payload["judge"]["evidence"]["record_findings"][0]["match_status"] = "existing"
    payload["judge"]["evidence"]["record_findings"][0]["item_id"] = "item_001"
    decision = accept_model_output(json.dumps(payload))
    assert decision.say.types == ["clarification"]


def test_valid_target_and_show_ids_accepted() -> None:
    payload = _valid_payload()
    payload["judge"]["evidence"]["record_findings"][0] = {
        "piece_of_work": "Chase Acme",
        "match_status": "existing",
        "item_id": ITEM_ID,
        "finding": "Matches existing Acme item.",
    }
    payload["judge"]["decision"]["required_actions"] = [
        {
            "action": "update",
            "item_id": ITEM_ID,
            "piece_of_work": None,
            "reason": "Mark Acme completed.",
        }
    ]
    payload["plan"]["tool_calls"] = [
        {"name": "update_item", "args": {"id": ITEM_ID, "status": "completed"}}
    ]
    decision = parse_and_validate(json.dumps(payload))
    assert decision.judge.evidence.record_findings[0].item_id == ITEM_ID
    assert decision.plan.tool_calls[0].args.id == ITEM_ID


def test_acknowledgement_say_type_rejected() -> None:
    payload = _valid_payload()
    payload["say"]["types"] = ["acknowledgement"]
    decision = accept_model_output(json.dumps(payload))
    assert decision.say.types == ["clarification"]


def test_duplicate_responsibilities_rejected() -> None:
    payload = _valid_payload()
    payload["judge"]["understanding"]["responsibilities"] = ["witness", "witness"]
    decision = accept_model_output(json.dumps(payload))
    assert decision.say.types == ["clarification"]


def test_non_iso_scope_dates_rejected() -> None:
    payload = _remember_payload()
    payload["say"]["testimony"]["scope"] = {"start": "last Monday", "end": "Sunday"}
    decision = accept_model_output(json.dumps(payload))
    assert decision.say.types == ["clarification"]


def test_testimony_type_requires_payload() -> None:
    payload = _remember_payload()
    payload["say"]["testimony"] = None
    decision = accept_model_output(json.dumps(payload))
    assert decision.say.types == ["clarification"]


def test_omitted_ids_require_reason() -> None:
    payload = _remember_payload()
    payload["say"]["testimony"]["omitted_ids"] = [ITEM_ID]
    payload["say"]["testimony"]["omitted_ids_reason"] = None
    decision = accept_model_output(json.dumps(payload))
    assert decision.say.types == ["clarification"]


def test_parse_and_validate_raises() -> None:
    with pytest.raises(DecisionValidationError):
        parse_and_validate("{")


def test_safe_fallback_stable() -> None:
    decision = safe_fallback("unit-test")
    assert decision.judge.understanding.responsibilities == []
    assert decision.say.types == ["clarification"]
    assert decision.say.text == FALLBACK_RESPONSE_TEXT
    assert decision.say.testimony is None
    assert decision.plan.tool_calls == []
    parse_and_validate(decision.model_dump_json())


def test_search_items_accepted_when_remembering() -> None:
    decision = parse_and_validate(json.dumps(_remember_payload()))
    assert decision.plan.tool_calls[0].name == "search_items"
    assert decision.plan.tool_calls[0].args.status == ["completed"]
    assert decision.say.testimony.view == "outcomes"
    assert decision.judge.understanding.requested_period.start == "2026-10-12"


def test_search_items_accepted_when_witnessing() -> None:
    payload = _valid_payload()
    payload["plan"]["tool_calls"].insert(0, {"name": "search_items", "args": {"query": "doctor"}})
    decision = parse_and_validate(json.dumps(payload))
    assert [c.name for c in decision.plan.tool_calls] == ["search_items", "add_item"]


def test_lab_goldens_are_valid_decisions() -> None:
    for payload in (
        golden_decision(),
        golden_decision_07(),
        golden_remembering_01(),
        golden_remembering_02(),
    ):
        decision = parse_and_validate(json.dumps(payload))
        assert decision.judge.understanding.message_meaning_summary
        assert decision.say.types


def test_acme_update_item_id_accepted() -> None:
    payload = golden_decision()
    decision = parse_and_validate(json.dumps(payload))
    assert decision.plan.tool_calls[0].args.id == ACME_ID
