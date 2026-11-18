"""M4 — one Together call returns Decision JSON. No network."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from llm.infer import (
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    InferenceError,
    infer_decision,
)
from llm.prompt import SYSTEM_PROMPT


class _FakeCompletions:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


def _client(monkeypatch: pytest.MonkeyPatch, completions: _FakeCompletions, key: str = "secret-key"):
    monkeypatch.setenv("TOGETHER_API_KEY", key)
    monkeypatch.delenv("TOGETHER_MODEL", raising=False)

    class FakeTogether:
        def __init__(self, api_key: str | None = None) -> None:
            self.api_key = api_key
            self.chat = SimpleNamespace(completions=completions)

    monkeypatch.setattr("together.Together", FakeTogether)
    return FakeTogether


def _response(text: str = '{"judge":{},"plan":{},"say":{}}') -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=text),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=22),
    )


def test_infer_decision_one_json_object_call(monkeypatch: pytest.MonkeyPatch) -> None:
    completions = _FakeCompletions(response=_response('{"ok":true}'))
    _client(monkeypatch, completions)

    result = infer_decision("THE INTERACTION STATE")

    assert result.raw_text == '{"ok":true}'
    assert result.model == DEFAULT_MODEL
    assert result.finish_reason == "stop"
    assert result.input_tokens == 11
    assert result.output_tokens == 22
    assert result.latency_s is not None
    assert len(completions.calls) == 1
    kwargs = completions.calls[0]
    assert kwargs["model"] == DEFAULT_MODEL
    assert kwargs["temperature"] == DEFAULT_TEMPERATURE
    assert kwargs["stream"] is False
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["reasoning"] == {"enabled": False}
    assert kwargs["messages"] == [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "THE INTERACTION STATE"},
    ]
    assert "api_key" not in kwargs
    assert "secret-key" not in repr(result)


def test_infer_decision_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TOGETHER_API_KEY", raising=False)

    with pytest.raises(InferenceError, match="TOGETHER_API_KEY"):
        infer_decision("THE INTERACTION STATE")


def test_infer_decision_does_not_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    completions = _FakeCompletions(error=RuntimeError("together down"))
    _client(monkeypatch, completions)

    with pytest.raises(InferenceError, match="together down"):
        infer_decision("THE INTERACTION STATE")
    assert len(completions.calls) == 1


def test_infer_decision_empty_content_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    completions = _FakeCompletions(response=_response("  "))
    _client(monkeypatch, completions)

    with pytest.raises(InferenceError, match="empty content"):
        infer_decision("THE INTERACTION STATE")


def test_infer_decision_empty_state_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    completions = _FakeCompletions(response=_response())
    _client(monkeypatch, completions)

    with pytest.raises(InferenceError, match="empty"):
        infer_decision("   ")
    assert completions.calls == []


def test_infer_decision_uses_together_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    completions = _FakeCompletions(response=_response('{"a":1}'))
    _client(monkeypatch, completions)
    monkeypatch.setenv("TOGETHER_MODEL", "Qwen/Qwen3.5-9B")

    result = infer_decision("plate")
    assert result.model == "Qwen/Qwen3.5-9B"
    assert completions.calls[0]["model"] == "Qwen/Qwen3.5-9B"
