"""Lab wrappers around the prompt Decision contract in llm.schema.

The prompt's example JSON has a stray `}` inside `plan.tool_calls`; we validate
the intended object, not that typo. Tool argument contracts are reused from
`tools/` — planned calls are never executed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import TypeAdapter, ValidationError

from llm.schema import Decision as LabDecision
from llm.validate import extract_json_text, parse_json_object, strip_json_fences
from tools import ToolCall

_tool_adapter = TypeAdapter(ToolCall)

__all__ = [
    "LabDecision",
    "extract_json_text",
    "parse_json",
    "strip_json_fences",
    "validate_decision",
    "validate_tool_call",
]


def parse_json(raw_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    return parse_json_object(raw_text)


def validate_decision(data: Dict[str, Any]) -> Tuple[Optional[LabDecision], List[str]]:
    try:
        return LabDecision.model_validate(data), []
    except ValidationError as exc:
        return None, [err["msg"] if "msg" in err else str(err) for err in exc.errors()]


def validate_tool_call(payload: Dict[str, Any]) -> Optional[str]:
    try:
        _tool_adapter.validate_python(payload)
        return None
    except ValidationError as exc:
        return str(exc)
