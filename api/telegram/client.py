"""Telegram Bot API client — setWebhook + sendMessage."""

from __future__ import annotations

import os
from typing import Union

import httpx

TELEGRAM_API = "https://api.telegram.org"


def _token() -> str:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    return token


def _api(method: str) -> str:
    return f"{TELEGRAM_API}/bot{_token()}/{method}"


async def set_webhook(*, url: str, secret_token: str) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            _api("setWebhook"),
            json={
                "url": url,
                "secret_token": secret_token,
                "allowed_updates": ["message"],
                "drop_pending_updates": True,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"setWebhook failed: {payload}")


async def send_message(*, chat_id: Union[str, int], text: str) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            _api("sendMessage"),
            json={"chat_id": chat_id, "text": text},
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"sendMessage failed: {payload}")
