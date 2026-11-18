"""M2 webhook — secret check, store via ingress, echo sendMessage (mocked)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.telegram.webhook import router
from lab.scenario import golden_decision
from llm.infer import InferenceResult
from memory.types import Turn

SECRET = "test-webhook-secret"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SECRET)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _update(chat_id: int = 42, text: str = "hello memory") -> dict:
    return {
        "update_id": 1,
        "message": {
            "message_id": 10,
            "chat": {"id": chat_id, "type": "private"},
            "text": text,
        },
    }


def test_webhook_rejects_bad_secret(client: TestClient) -> None:
    response = client.post(
        "/telegram/webhook",
        json=_update(),
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert response.status_code == 401


def test_webhook_ignores_non_text(client: TestClient) -> None:
    response = client.post(
        "/telegram/webhook",
        json={"update_id": 2, "message": {"message_id": 1, "chat": {"id": 1}}},
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}


def test_webhook_stores_and_echoes(client: TestClient) -> None:
    turn = Turn(
        user_id="usr_1",
        channel_id="chn_1",
        message_id="msg_1",
        platform="telegram",
        platform_user_id="42",
        role="user",
        text="hello memory",
    )
    state = SimpleNamespace(recent_turns=(), current_items=(), prompt="THE PLATE")
    inferred = InferenceResult(
        raw_text='{"judge":{},"plan":{"tool_calls":[]},"say":{"types":["silence"]}}',
        model="Qwen/Qwen3.5-9B",
        latency_s=1.2,
    )
    with (
        patch("api.telegram.webhook.ingress_turn", return_value=turn) as ingress,
        patch("api.telegram.webhook.assemble_interaction_state", return_value=state) as assemble,
        patch("api.telegram.webhook.infer_decision", return_value=inferred) as infer,
        patch("api.telegram.webhook.accept_model_output") as accept,
        patch("api.telegram.webhook.send_message", new_callable=AsyncMock) as send,
    ):
        response = client.post(
            "/telegram/webhook",
            json=_update(chat_id=42, text="hello memory"),
            headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    ingress.assert_called_once_with(
        platform="telegram",
        platform_user_id="42",
        role="user",
        text="hello memory",
    )
    assemble.assert_called_once_with(turn)
    infer.assert_called_once_with("THE PLATE")
    accept.assert_called_once_with(inferred.raw_text)
    send.assert_awaited_once_with(chat_id="42", text="you said: hello memory")


def test_webhook_skips_inference_when_assemble_fails(client: TestClient) -> None:
    turn = Turn(
        user_id="usr_1",
        channel_id="chn_1",
        message_id="msg_1",
        platform="telegram",
        platform_user_id="42",
        role="user",
        text="hello memory",
    )
    with (
        patch("api.telegram.webhook.ingress_turn", return_value=turn),
        patch(
            "api.telegram.webhook.assemble_interaction_state",
            side_effect=RuntimeError("db down"),
        ),
        patch("api.telegram.webhook.infer_decision") as infer,
        patch("api.telegram.webhook.accept_model_output") as accept,
        patch("api.telegram.webhook.send_message", new_callable=AsyncMock) as send,
    ):
        response = client.post(
            "/telegram/webhook",
            json=_update(chat_id=42, text="hello memory"),
            headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
        )

    assert response.status_code == 200
    infer.assert_not_called()
    accept.assert_not_called()
    send.assert_awaited_once_with(chat_id="42", text="you said: hello memory")


def test_webhook_accepts_model_output(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    turn = Turn(
        user_id="usr_1",
        channel_id="chn_1",
        message_id="msg_1",
        platform="telegram",
        platform_user_id="42",
        role="user",
        text="hello memory",
    )
    state = SimpleNamespace(recent_turns=(), current_items=(), prompt="THE PLATE")
    inferred = InferenceResult(
        raw_text=json.dumps(golden_decision()),
        model="Qwen/Qwen3.5-9B",
        latency_s=1.2,
    )
    with (
        patch("api.telegram.webhook.ingress_turn", return_value=turn),
        patch("api.telegram.webhook.assemble_interaction_state", return_value=state),
        patch("api.telegram.webhook.infer_decision", return_value=inferred),
        patch("api.telegram.webhook.send_message", new_callable=AsyncMock),
        caplog.at_level("INFO", logger="api.telegram.webhook"),
    ):
        response = client.post(
            "/telegram/webhook",
            json=_update(),
            headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
        )

    assert response.status_code == 200
    assert "decision accepted: say=['confirmation'] tool_calls=4" in caplog.text


def test_webhook_invalid_json_falls_back(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    turn = Turn(
        user_id="usr_1",
        channel_id="chn_1",
        message_id="msg_1",
        platform="telegram",
        platform_user_id="42",
        role="user",
        text="hello memory",
    )
    state = SimpleNamespace(recent_turns=(), current_items=(), prompt="THE PLATE")
    inferred = InferenceResult(raw_text="not json", model="Qwen/Qwen3.5-9B", latency_s=1.2)
    with (
        patch("api.telegram.webhook.ingress_turn", return_value=turn),
        patch("api.telegram.webhook.assemble_interaction_state", return_value=state),
        patch("api.telegram.webhook.infer_decision", return_value=inferred),
        patch("api.telegram.webhook.send_message", new_callable=AsyncMock) as send,
        caplog.at_level("INFO", logger="api.telegram.webhook"),
    ):
        response = client.post(
            "/telegram/webhook",
            json=_update(),
            headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
        )

    assert response.status_code == 200
    assert "decision accepted: say=['clarification'] tool_calls=0" in caplog.text
    send.assert_awaited_once_with(chat_id="42", text="you said: hello memory")
