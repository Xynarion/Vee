"""One Together call: Interaction State in, Decision JSON out. No parse, no retry."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from llm.prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "Qwen/Qwen3.5-9B"
DEFAULT_TIMEOUT_S = 90.0
DEFAULT_TEMPERATURE = 0.0


class InferenceError(RuntimeError):
    """Together call failed or returned nothing we can hand to parse/validate."""


@dataclass(frozen=True)
class InferenceResult:
    """Raw model JSON, ready for parse_and_validate. Never includes the API key."""

    raw_text: str
    model: str
    finish_reason: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_s: Optional[float] = None


def _read_api_key() -> str:
    key = (os.getenv("TOGETHER_API_KEY") or "").strip()
    if not key:
        raise InferenceError("TOGETHER_API_KEY is required")
    return key


def _read_model() -> str:
    return (os.getenv("TOGETHER_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _read_choice_text(choice: Any) -> str:
    message = getattr(choice, "message", None)
    content = getattr(message, "content", None) if message is not None else None
    if isinstance(content, str):
        return content
    return ""


def _read_usage_tokens(usage: Any) -> tuple[Optional[int], Optional[int]]:
    if usage is None:
        return None, None
    prompt = getattr(usage, "prompt_tokens", None)
    completion = getattr(usage, "completion_tokens", None)
    return (
        prompt if prompt is not None else None,
        completion if completion is not None else None,
    )


def _complete(client: Any, model: str, interaction_state: str, timeout_s: float) -> Any:
    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": interaction_state},
        ],
        "temperature": DEFAULT_TEMPERATURE,
        "stream": False,
        "response_format": {"type": "json_object"},
        "reasoning": {"enabled": False},
        "timeout": timeout_s,
    }
    try:
        return client.chat.completions.create(**kwargs)
    except TypeError:
        kwargs.pop("reasoning", None)
        return client.chat.completions.create(**kwargs)


def infer_decision(
    interaction_state: str,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> InferenceResult:
    """Single Qwen3.5-9B chat completion. Returns JSON text; does not validate it."""
    plate = (interaction_state or "").strip()
    if not plate:
        raise InferenceError("interaction state is empty")

    key = _read_api_key()
    from together import Together

    model = _read_model()
    t0 = time.perf_counter()
    try:
        client = Together(api_key=key)
        response = _complete(client, model, plate, timeout_s)
    except InferenceError:
        raise
    except Exception as exc:  # noqa: BLE001 — contract boundary, no retry
        raise InferenceError(str(exc)) from exc

    latency = round(time.perf_counter() - t0, 4)
    choices = getattr(response, "choices", None) or []
    choice = choices[0] if choices else None
    if choice is None:
        raise InferenceError("Together returned no choices")

    raw_text = _read_choice_text(choice)
    if not raw_text.strip():
        raise InferenceError("Together returned empty content")

    finish_reason = getattr(choice, "finish_reason", None)
    input_tokens, output_tokens = _read_usage_tokens(getattr(response, "usage", None))
    logger.info(
        "inference complete: model=%s chars=%s latency_s=%s finish=%s",
        model,
        len(raw_text),
        latency,
        finish_reason,
    )
    return InferenceResult(
        raw_text=raw_text,
        model=model,
        finish_reason=finish_reason,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_s=latency,
    )
