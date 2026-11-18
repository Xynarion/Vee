"""Parse and validate raw model text into a Decision (M4a)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

from pydantic import ValidationError

from llm.fallback import safe_fallback
from llm.schema import Decision

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*\n?(.*?)\n?```\s*$",
    re.DOTALL | re.IGNORECASE,
)


class DecisionValidationError(ValueError):
    """Raised when raw model text cannot become a valid Decision."""


def strip_json_fences(text: str) -> str:
    raw = (text or "").strip()
    match = _FENCE_RE.match(raw)
    if match:
        return match.group(1).strip()
    return raw


def extract_json_text(text: str) -> str:
    stripped = strip_json_fences(text)
    if not stripped:
        return ""
    start, end = stripped.find("{"), stripped.rfind("}")
    if start == -1 or end <= start:
        return stripped
    return stripped[start : end + 1]


def parse_json_object(raw_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    blob = extract_json_text(raw_text)
    if not blob:
        return None, "empty model output"
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(data, dict):
        return None, "JSON root must be an object"
    return data, None


def parse_and_validate(raw_text: str) -> Decision:
    """
    Strip fences, extract JSON object, json.loads, Pydantic + invariants.

    Raises DecisionValidationError on any failure.
    """
    # 1. Parse. Strip fences, take the JSON object, and load it.
    data, error = parse_json_object(raw_text)
    if error or data is None:
        raise DecisionValidationError(error or "empty model output")
    try:
        # 2. Validate. The object must match the Decision contract.
        return Decision.model_validate(data)
    except ValidationError as exc:
        raise DecisionValidationError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — contract boundary
        raise DecisionValidationError(str(exc)) from exc


def accept_model_output(raw_text: str) -> Decision:
    """Always return a Decision; use safe_fallback on failure (no retries here)."""
    try:
        return parse_and_validate(raw_text)
    except DecisionValidationError as exc:
        logger.warning("model output rejected: %s", exc)
        return safe_fallback(str(exc))
