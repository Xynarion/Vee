"""Scenario registry. Pack fixtures live in lab.fixtures; this module re-exports them."""

from __future__ import annotations

import hashlib
from typing import Dict, List

from lab.fixtures.brain_dump import (
    ACME_ID,
    ANGEL_ID,
    ANGEL_START,
    EXPECTED_DUE,
    FAMILY_ID,
    FAMILY_MOVED,
    FAMILY_START,
    GYM_ID,
    LANDING_ID,
    LOGIN_ID,
    MSG_01,
    MSG_02,
    MSG_03,
    MSG_04,
    MSG_05,
    MSG_06,
    MSG_07,
    NEW_TASKS,
    SCENARIO_01,
    SCENARIO_02,
    SCENARIO_03,
    SCENARIO_04,
    SCENARIO_05,
    SCENARIO_06,
    SCENARIO_07,
    VEE_S01_REPLY,
    VEE_S02_REPLY,
    VEE_S03_REPLY,
    VEE_S04_REPLY,
    VEE_S05_REPLY,
    VEE_S06_HELD_REPLY,
    VEE_S06_REPLY,
    golden_decision,
    golden_decision_02,
    golden_decision_03,
    golden_decision_04,
    golden_decision_05,
    golden_decision_06,
    golden_decision_07,
)
from lab.fixtures.brain_dump import SCENARIOS as BRAIN_DUMP_SCENARIOS
from lab.fixtures.common import Scenario, with_current_message
from lab.fixtures.remembering import (
    EXCLUDED_TODAY_IDS,
    MSG_01 as REM_MSG_01,
    MSG_02 as REM_MSG_02,
    LAST_WEEK_END,
    LAST_WEEK_START,
    REFLECTION_EXCLUDED_IDS,
    REFLECTION_IDS,
    REM_CLOCK,
    REM_CLOCK_02,
    WEEK_COFFEE_ID,
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
    REM_DOCTOR_ID,
    REM_FAMILY_ID,
    REM_GYM_ID,
    REM_HASSAN_ID,
    REM_LANDING_ID,
    REM_PROPOSAL_ID,
    REM_STANDUP_ID,
    REM_TODAY,
    TODAY_IDS,
    golden_decision_01 as golden_remembering_01,
    golden_decision_02 as golden_remembering_02,
)
from lab.fixtures.remembering import SCENARIOS as REMEMBERING_SCENARIOS

SCENARIOS: Dict[str, Scenario] = {**BRAIN_DUMP_SCENARIOS, **REMEMBERING_SCENARIOS}
DEFAULT_SCENARIO_ID = "remembering-02"
SCENARIO_ID = SCENARIO_01.id
SCENARIO_TITLE = SCENARIO_01.title
INTERACTION_STATE = SCENARIO_01.interaction_state

__all__ = [
    "ACME_ID",
    "ANGEL_ID",
    "ANGEL_START",
    "DEFAULT_SCENARIO_ID",
    "EXCLUDED_TODAY_IDS",
    "EXPECTED_DUE",
    "FAMILY_ID",
    "FAMILY_MOVED",
    "FAMILY_START",
    "GYM_ID",
    "INTERACTION_STATE",
    "LANDING_ID",
    "LOGIN_ID",
    "MSG_01",
    "MSG_02",
    "MSG_03",
    "MSG_04",
    "MSG_05",
    "MSG_06",
    "MSG_07",
    "NEW_TASKS",
    "LAST_WEEK_END",
    "LAST_WEEK_START",
    "REFLECTION_EXCLUDED_IDS",
    "REFLECTION_IDS",
    "REM_CLOCK",
    "REM_CLOCK_02",
    "WEEK_COFFEE_ID",
    "WEEK_DOCTOR_ID",
    "WEEK_EXPENSES_ID",
    "WEEK_FAMILY_ID",
    "WEEK_FLIGHTS_ID",
    "WEEK_GYM_ID",
    "WEEK_INVOICE_ID",
    "WEEK_LANDING_ID",
    "WEEK_PRICING_ID",
    "WEEK_PROPOSAL_ID",
    "WEEK_REVIEW_ID",
    "WEEK_STANDUP_ID",
    "REM_DOCTOR_ID",
    "REM_FAMILY_ID",
    "REM_GYM_ID",
    "REM_HASSAN_ID",
    "REM_LANDING_ID",
    "REM_MSG_01",
    "REM_MSG_02",
    "REM_PROPOSAL_ID",
    "REM_STANDUP_ID",
    "REM_TODAY",
    "SCENARIOS",
    "SCENARIO_01",
    "SCENARIO_02",
    "SCENARIO_03",
    "SCENARIO_04",
    "SCENARIO_05",
    "SCENARIO_06",
    "SCENARIO_07",
    "SCENARIO_ID",
    "SCENARIO_TITLE",
    "TODAY_IDS",
    "VEE_S01_REPLY",
    "VEE_S02_REPLY",
    "VEE_S03_REPLY",
    "VEE_S04_REPLY",
    "VEE_S05_REPLY",
    "VEE_S06_HELD_REPLY",
    "VEE_S06_REPLY",
    "Scenario",
    "fixture_hash",
    "get_scenario",
    "resolve_interaction_state",
    "with_current_message",
    "golden_decision",
    "golden_decision_02",
    "golden_decision_03",
    "golden_decision_04",
    "golden_decision_05",
    "golden_decision_06",
    "golden_decision_07",
    "golden_remembering_01",
    "golden_remembering_02",
    "list_scenarios",
    "prompt_hash",
]


def get_scenario(scenario_id: str | None) -> Scenario:
    if scenario_id and scenario_id in SCENARIOS:
        return SCENARIOS[scenario_id]
    return SCENARIOS[DEFAULT_SCENARIO_ID]


def resolve_interaction_state(
    scenario_id: str | None, message: str | None = None
) -> str:
    scenario = get_scenario(scenario_id)
    return with_current_message(scenario.interaction_state, message)


def list_scenarios() -> List[Dict[str, str]]:
    return [
        {
            "id": s.id,
            "title": s.title,
            "fixture": s.interaction_state,
            "family": s.family,
        }
        for s in SCENARIOS.values()
    ]


def fixture_hash(text: str | None = None) -> str:
    blob = text if text is not None else INTERACTION_STATE
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def prompt_hash(system_prompt: str) -> str:
    return hashlib.sha256(system_prompt.encode()).hexdigest()[:16]
