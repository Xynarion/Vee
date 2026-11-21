"""Ten live Together calls. Validate each Decision, execute the plan, then roll it back."""

from __future__ import annotations

import uuid

from dotenv import load_dotenv
from sqlalchemy import delete, select, update

from lab.fixtures.brain_dump import ACME_ID
from lab.fixtures.brain_dump import MSG_01 as DUMP_MSG
from lab.fixtures.brain_dump import SCENARIO_01 as BRAIN_DUMP_01
from lab.fixtures.remembering import MSG_01 as REMEMBER_MSG
from lab.fixtures.remembering import SCENARIO_01 as REMEMBERING_01
from llm.infer import InferenceResult, infer_decision
from llm.validate import DecisionValidationError, parse_and_validate
from memory.db import db_session
from memory.models import Item, ItemHistory, Message, User, UserChannel
from memory.operations.ingress import ingress_turn
from memory.types import Turn
from tools.execute import ToolResult, execute_plan

RUNS = 5


def open_founder() -> Turn:
    return ingress_turn(
        platform="telegram",
        platform_user_id=f"live_{uuid.uuid4().hex[:12]}",
        role="user",
        text="live inference",
    )


def seed_acme(turn: Turn) -> str:
    """The brain-dump plate names this task. Seed it only when the id is free."""
    with db_session() as db:
        existing = db.get(Item, ACME_ID)
        if existing is not None:
            return f"{ACME_ID} already in the database — left untouched"
        db.add(
            Item(
                id=ACME_ID,
                user_id=turn.user_id,
                type="task",
                title="Chase Acme overdue invoice",
                status="todo",
                flags=[],
            )
        )
    return f"seeded {ACME_ID} for this run"


def remove_founder(turn: Turn) -> int:
    """Delete this run's user and every item it owns. Pre-existing rows stay."""
    with db_session() as db:
        item_ids = list(db.scalars(select(Item.id).where(Item.user_id == turn.user_id)).all())
        if item_ids:
            db.execute(update(Item).where(Item.id.in_(item_ids)).values(parent_id=None))
            db.execute(delete(ItemHistory).where(ItemHistory.item_id.in_(item_ids)))
        db.execute(delete(ItemHistory).where(ItemHistory.message_id == turn.message_id))
        if item_ids:
            db.execute(delete(Item).where(Item.id.in_(item_ids)))
        db.execute(delete(Message).where(Message.user_id == turn.user_id))
        db.execute(delete(UserChannel).where(UserChannel.user_id == turn.user_id))
        db.execute(delete(User).where(User.id == turn.user_id))
    return len(item_ids)


def print_plan(results: list[ToolResult]) -> None:
    if not results:
        print("  plan     empty")
        return
    for row in results:
        state = "ok" if row.ok else "failed"
        detail = row.item_id or ""
        if row.ok and row.changes:
            extra = "  " + ", ".join(f"{key}={value}" for key, value in row.changes.items())
        else:
            extra = f"  {row.error}" if row.error else ""
        print(f"  {row.name:<12} {state:<6} {detail}{extra}")


def run_live_decisions(title: str, state: str, turn: Turn) -> int:
    failed = 0
    print("\n" + "=" * 60)
    print(f"{title} — validate and execute {RUNS} live Decisions")
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
        written = execute_plan(
            decision.plan.tool_calls,
            user_id=turn.user_id,
            message_id=turn.message_id,
        )
        print(
            f"{number}/{RUNS} pass  say={decision.say.types} "
            f"tool_calls={len(decision.plan.tool_calls)} latency_s={result.latency_s}"
        )
        print_plan(written)
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

    turn = open_founder()
    try:
        print(seed_acme(turn))
        dump_failed = run_live_decisions("BRAIN-DUMP 01", dump, turn)
        remember_failed = run_live_decisions("REMEMBERING 01", remember, turn)
        total = RUNS * 2
        failed = dump_failed + remember_failed
        print("\n" + "=" * 60)
        print(f"failed {failed}/{total}")
        print("=" * 60)
    finally:
        removed = remove_founder(turn)
        print(f"rolled back {removed} items for {turn.user_id}\n")
