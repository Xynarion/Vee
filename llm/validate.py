"""Parse and validate raw model text into a Decision (M4a)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict

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


def parse_and_validate(raw_text: str) -> Decision:
    """
    Strip fences, json.loads, Pydantic + invariants.

    Raises DecisionValidationError on any failure.
    """
    try:
        stripped = strip_json_fences(raw_text)
        if not stripped:
            raise DecisionValidationError("empty model output")
        data: Dict[str, Any] = json.loads(stripped)
        if not isinstance(data, dict):
            raise DecisionValidationError("JSON root must be an object")
        return Decision.model_validate(data)
    except DecisionValidationError:
        raise
    except json.JSONDecodeError as exc:
        raise DecisionValidationError(f"invalid JSON: {exc}") from exc
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
