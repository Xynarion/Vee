"""GET /inspector — one founder's recorded items, their history, and source messages."""

from __future__ import annotations

import os
import secrets
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import FileResponse

from memory.db import db_session
from memory.models import Item, ItemHistory, Message
from memory.operations.items import (
    count_recorded_items,
    find_owned_item,
    list_item_history,
    list_recorded_items,
)
from memory.operations.messages import load_messages
from memory.operations.users import find_user_id

PAGE = Path(__file__).parent / "index.html"
PAGE_SIZE = 50

router = APIRouter(tags=["inspector"])


def read_setting(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise HTTPException(status_code=503, detail=f"{name} is not set")
    return value


def check_token(token: Optional[str]) -> None:
    expected = read_setting("INSPECTOR_TOKEN")
    if not token or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="invalid inspector token")


def format_time(value: Optional[Any]) -> Optional[str]:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return None


def encode_cursor(item: Item) -> str:
    return f"{item.created_at.isoformat()}|{item.id}"


def decode_cursor(cursor: Optional[str]) -> Optional[tuple[datetime, str]]:
    if not cursor:
        return None
    try:
        stamp, item_id = cursor.rsplit("|", 1)
        return datetime.fromisoformat(stamp), item_id
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid cursor") from None


def summarize_item(item: Item) -> dict:
    return {
        "id": item.id,
        "type": str(item.type),
        "title": item.title,
        "status": str(item.status),
        "start_at": format_time(item.start_at),
        "end_at": format_time(item.end_at),
        "due_at": format_time(item.due_at),
        "created_at": format_time(item.created_at),
        "updated_at": format_time(item.updated_at),
    }


def describe_item(item: Item) -> dict:
    return {
        **summarize_item(item),
        "description": item.description,
        "parent_id": item.parent_id,
        "work_mode": str(item.work_mode) if item.work_mode is not None else None,
        "flags": list(item.flags or []),
        "carried_since": format_time(item.carried_since),
    }


def describe_history(row: ItemHistory) -> dict:
    return {
        "id": row.id,
        "kind": str(row.kind),
        "source": str(row.source),
        "changes": row.changes if isinstance(row.changes, dict) else {},
        "message_id": row.message_id,
        "created_at": format_time(row.created_at),
    }


def describe_message(row: Message) -> dict:
    return {
        "id": row.id,
        "role": str(row.role),
        "text": row.text,
        "created_at": format_time(row.created_at),
    }


@router.get("/inspector", include_in_schema=False)
def open_inspector() -> FileResponse:
    return FileResponse(PAGE)


@router.get("/inspector/api/items")
def list_items(
    cursor: Optional[str] = None,
    limit: int = Query(default=PAGE_SIZE, ge=1, le=200),
    x_inspector_token: Optional[str] = Header(default=None),
) -> dict:
    """One page of recorded items. `next_cursor` is null on the last page."""
    check_token(x_inspector_token)
    founder = read_setting("INSPECTOR_TELEGRAM_ID")
    before = decode_cursor(cursor)
    with db_session() as db:
        user_id = find_user_id(db, platform="telegram", platform_user_id=founder)
        if user_id is None:
            return {"items": [], "next_cursor": None, "total": 0}
        rows = list_recorded_items(db, user_id, limit=limit + 1, before=before)
        page = rows[:limit]
        return {
            "items": [summarize_item(item) for item in page],
            "next_cursor": encode_cursor(page[-1]) if len(rows) > limit else None,
            "total": count_recorded_items(db, user_id),
        }


@router.get("/inspector/api/items/{item_id}")
def read_item(item_id: str, x_inspector_token: Optional[str] = Header(default=None)) -> dict:
    check_token(x_inspector_token)
    founder = read_setting("INSPECTOR_TELEGRAM_ID")
    with db_session() as db:
        user_id = find_user_id(db, platform="telegram", platform_user_id=founder)
        item = find_owned_item(db, user_id, item_id) if user_id else None
        if item is None:
            raise HTTPException(status_code=404, detail="item not found")
        history = list_item_history(db, item.id)
        message_ids = [row.message_id for row in history if row.message_id]
        messages = load_messages(db, user_id, message_ids)
        return {
            "item": describe_item(item),
            "history": [describe_history(row) for row in history],
            "messages": [describe_message(row) for row in messages],
        }
