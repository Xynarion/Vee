"""POST /telegram/webhook — receive update, store turn, echo reply."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Header, HTTPException, Request

from api.telegram.client import send_message
from memory.operations.ingress import ingress_turn
from memory.operations.state import assemble_interaction_state

logger = logging.getLogger(__name__)

router = APIRouter(tags=["telegram"])


def _webhook_secret() -> str:
    return (os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip()


def _extract_text_message(update: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    message = update.get("message") or update.get("edited_message")
    if not isinstance(message, dict):
        return None
    text = message.get("text")
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not text or chat_id is None:
        return None
    return str(chat_id), str(text)


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
) -> Dict[str, str]:
    expected = _webhook_secret()
    if not expected or x_telegram_bot_api_secret_token != expected:
        raise HTTPException(status_code=401, detail="invalid webhook secret")

    update = await request.json()
    extracted = _extract_text_message(update)
    if extracted is None:
        return {"status": "ignored"}

    chat_id, text = extracted
    turn = ingress_turn(
        platform="telegram",
        platform_user_id=chat_id,
        role="user",
        text=text,
    )
    try:
        state = assemble_interaction_state(turn)
        logger.info(
            "interaction state ready: recent_turns=%s current_items=%s prompt_chars=%s",
            len(state.recent_turns),
            len(state.current_items),
            len(state.prompt),
        )
    except Exception:
        logger.exception("assemble_interaction_state failed; continuing with echo")

    await send_message(chat_id=chat_id, text=f"you said: {text}")
    return {"status": "ok"}
