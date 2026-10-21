"""LLM contract — Decision schema, validate, fallback (not memory/ persistence)."""

from llm.fallback import safe_fallback
from llm.schema import Decision, Intent
from llm.validate import (
    DecisionValidationError,
    accept_model_output,
    parse_and_validate,
)

__all__ = [
    "Decision",
    "Intent",
    "DecisionValidationError",
    "accept_model_output",
    "parse_and_validate",
    "safe_fallback",
]
