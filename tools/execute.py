"""Run a validated plan. One transaction: a failed call rolls the whole plan back."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from memory.db import db_session
from tools.add_item import AddItemCall
from tools.add_item import run as run_add_item
from tools.update_item import UpdateItemCall
from tools.update_item import run as run_update_item
from tools.write import ToolWriteError


@dataclass
class ToolResult:
    name: str
    ok: bool
    item_id: Optional[str]
    changes: dict
    error: Optional[str] = None


class _PlanFailed(Exception):
    def __init__(self, results: list[ToolResult]) -> None:
        self.results = results


def execute_plan(
    tool_calls: Sequence[Any],
    *,
    user_id: str,
    message_id: str,
) -> list[ToolResult]:
    """Write the plan for this founder message. Empty plans write nothing."""
    if not tool_calls:
        return []
    try:
        with db_session() as db:
            return _run_plan(db, tool_calls, user_id=user_id, message_id=message_id)
    except _PlanFailed as failed:
        return failed.results


def _run_plan(db, tool_calls, *, user_id: str, message_id: str) -> list[ToolResult]:
    results: list[ToolResult] = []
    for call in tool_calls:
        try:
            item_id, changes = _run_call(db, call, user_id=user_id, message_id=message_id)
        except Exception as exc:
            db.rollback()
            results.append(
                ToolResult(
                    name=getattr(call, "name", ""),
                    ok=False,
                    item_id=None,
                    changes={},
                    error=str(exc),
                )
            )
            for earlier in results[:-1]:
                earlier.ok = False
                earlier.error = "rolled back"
            raise _PlanFailed(results) from exc
        results.append(ToolResult(name=call.name, ok=True, item_id=item_id, changes=changes))
    return results


def _run_call(db, call, *, user_id: str, message_id: str) -> tuple[str, dict]:
    if isinstance(call, AddItemCall):
        return run_add_item(db, call.args, user_id=user_id, message_id=message_id)
    if isinstance(call, UpdateItemCall):
        return run_update_item(db, call.args, user_id=user_id, message_id=message_id)
    raise ToolWriteError(f"{getattr(call, 'name', 'tool')} is not executed")
