"""M2 webhook — secret check, store via ingress, echo sendMessage (mocked)."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.telegram.webhook import router
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
    with (
        patch("api.telegram.webhook.ingress_turn", return_value=turn) as ingress,
        patch("api.telegram.webhook.assemble_interaction_state") as assemble,
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
    send.assert_awaited_once_with(chat_id="42", text="you said: hello memory")
