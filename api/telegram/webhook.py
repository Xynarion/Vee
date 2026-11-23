"""POST /telegram/webhook — receive update, store turn, assemble, infer, accept, reply."""

from __future__ import annotations

import asyncio
import logging
import os
from types import SimpleNamespace
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Header, HTTPException, Request

from api.telegram.client import send_message
from api.telegram.reply import compose_message_text, format_reply, read_testimony_ids
from llm.infer import infer_decision
from llm.validate import accept_model_output
from memory.db import db_session
from memory.operations.ingress import ingress_turn
from memory.operations.items import load_testimony_items
from memory.operations.state import assemble_interaction_state
from tools.execute import execute_plan

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
    # 1. Authenticate. Reject the update unless Telegram's secret matches.
    expected = _webhook_secret()
    if not expected or x_telegram_bot_api_secret_token != expected:
        raise HTTPException(status_code=401, detail="invalid webhook secret")

    # 2. Keep text messages. Photos, stickers, and empty updates stop here.
    update = await request.json()
    extracted = _extract_text_message(update)
    if extracted is None:
        return {"status": "ignored"}

    # 3. Persist the founder's turn. Resolve the user and store the message.
    chat_id, text = extracted
    turn = ingress_turn(
        platform="telegram",
        platform_user_id=chat_id,
        role="user",
        text=text,
    )

    # 4. Assemble the Interaction State: message, recent turns, Progress Memory, clock, this week, last week.
    state = None
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

    # 5. One Together call. Qwen3.5-9B reads that plate and returns Decision JSON.
    result = None
    if state is not None:
        try:
            result = await asyncio.to_thread(infer_decision, state.prompt)
            logger.info(
                "decision json ready: model=%s chars=%s latency_s=%s",
                result.model,
                result.raw_text,
                result.latency_s,
            )
        except Exception:
            logger.exception("infer_decision failed; continuing with echo")

    # 6. Validate. Parse the JSON into a Decision, or use the clarification fallback. No retry.
    decision = None
    if result is not None:
        decision = accept_model_output(result.raw_text)
        logger.info(
            "decision accepted: say=%s tool_calls=%s",
            decision.say.types,
            len(decision.plan.tool_calls),
        )

    # 7. Execute. Write add_item and update_item. The code assigns history and message_id.
    try:
        written = execute_plan(
            decision.plan.tool_calls,
            user_id=turn.user_id,
            message_id=turn.message_id,
        )
        logger.info(
            "plan executed: ok=%s failed=%s",
            sum(1 for row in written if row.ok),
            sum(1 for row in written if not row.ok),
        )
    except Exception:
        logger.exception("execute_plan failed; continuing without a reply")

    # 8. Reply. Testimony ids become a symbol list. Otherwise send say.text. Empty text sends nothing.
    reply = None
    if decision is not None and isinstance(decision.say.text, str) and decision.say.text.strip():
        reply = decision.say.text.strip()
    item_ids = read_testimony_ids(decision) if decision is not None else []
    if item_ids:
        try:
            with db_session() as db:
                rows = load_testimony_items(db, turn.user_id, item_ids)
                items = [
                    SimpleNamespace(id=row.id, type=str(row.type), title=row.title)
                    for row in rows
                ]
            formatted = format_reply(decision, items)
            if formatted:
                reply = formatted
        except Exception:
            logger.exception("format_reply failed; continuing without a reply")
    if reply:
        await send_message(chat_id=chat_id, text=reply)

    # 9. Remember the words and the ids shown. The symbol list stays on Telegram.
    stored = compose_message_text(decision) if decision is not None else None
    if stored:
        try:
            ingress_turn(
                platform="telegram",
                platform_user_id=chat_id,
                role="assistant",
                text=stored,
            )
        except Exception:
            logger.exception("storing the reply failed")
    return {"status": "ok"}
