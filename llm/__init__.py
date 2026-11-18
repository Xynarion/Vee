"""LLM contract — Decision schema, validate, fallback (not memory/ persistence)."""

from llm.fallback import safe_fallback
from llm.infer import InferenceError, InferenceResult, infer_decision
from llm.schema import Decision, Judge, Plan, Say
from llm.validate import (
    DecisionValidationError,
    accept_model_output,
    parse_and_validate,
)

__all__ = [
    "Decision",
    "Judge",
    "Plan",
    "Say",
    "DecisionValidationError",
    "InferenceError",
    "InferenceResult",
    "accept_model_output",
    "infer_decision",
    "parse_and_validate",
    "safe_fallback",
]
