"""Ten live Together calls: five Brain-dump 01, five Remembering 01. Count validation failures."""

from __future__ import annotations

from dotenv import load_dotenv

from lab.fixtures.brain_dump import MSG_01 as DUMP_MSG
from lab.fixtures.brain_dump import SCENARIO_01 as BRAIN_DUMP_01
from lab.fixtures.remembering import MSG_01 as REMEMBER_MSG
from lab.fixtures.remembering import SCENARIO_01 as REMEMBERING_01
from llm.infer import InferenceResult, infer_decision
from llm.validate import DecisionValidationError, parse_and_validate

RUNS = 5


def count_validation_failures(title: str, state: str) -> int:
    failed = 0
    print("\n" + "=" * 60)
    print(f"{title} — validate {RUNS} live Decisions")
    print("=" * 60)
    for number in range(1, RUNS + 1):
        result: InferenceResult = infer_decision(state)
        try:
            decision = parse_and_validate(result.raw_text)
        except DecisionValidationError as exc:
            failed += 1
            print(f"{number}/{RUNS} FAIL  latency_s={result.latency_s}")
            print(exc)
            print(result.raw_text)
            continue
        print(
            f"{number}/{RUNS} pass  say={decision.say.types} "
            f"tool_calls={len(decision.plan.tool_calls)} latency_s={result.latency_s}"
        )
    print("-" * 60)
    print(f"{title} failed {failed}/{RUNS}")
    print("=" * 60)
    return failed


def test_brain_dump_and_remembering_count_validation_failures() -> None:
    load_dotenv()
    dump = BRAIN_DUMP_01.interaction_state
    remember = REMEMBERING_01.interaction_state
    assert DUMP_MSG in dump
    assert "Chase Acme overdue invoice" in dump
    assert REMEMBER_MSG in remember
    assert "Finalize landing copy" in remember

    dump_failed = count_validation_failures("BRAIN-DUMP 01", dump)
    remember_failed = count_validation_failures("REMEMBERING 01", remember)
    total = RUNS * 2
    failed = dump_failed + remember_failed
    print("\n" + "=" * 60)
    print(f"failed {failed}/{total}")
    print("=" * 60 + "\n")
