"""Turn a testimony's item ids into a Telegram list of alignment symbols."""

from __future__ import annotations

from typing import Any, Optional, Sequence

ALIGNMENT = {
    "task": "•",
    "event": "○",
}


def read_testimony_ids(decision: Any) -> list[str]:
    """Item ids named by say.testimony, in the order Vee chose."""
    say = getattr(decision, "say", None)
    testimony = getattr(say, "testimony", None)
    ids = getattr(testimony, "item_ids", None)
    if not isinstance(ids, list):
        return []
    return [item_id for item_id in ids if isinstance(item_id, str) and item_id]


def format_reply(decision: Any, items: Sequence[Any]) -> Optional[str]:
    """Header plus one symbol and title per owned item. None keeps the echo."""
    ids = read_testimony_ids(decision)
    if not ids:
        return None
    by_id = {item.id: item for item in items}
    lines: list[str] = []
    for item_id in ids:
        item = by_id.get(item_id)
        if item is None:
            continue
        symbol = ALIGNMENT.get(item.type)
        title = item.title.strip() if isinstance(item.title, str) else ""
        if symbol is None or not title:
            continue
        lines.append(f"{symbol} {title}")
    header = ""
    text = getattr(getattr(decision, "say", None), "text", None)
    if isinstance(text, str):
        header = text.strip()
    if not lines and not header:
        return None
    if header and lines:
        return f"{header}\n" + "\n".join(lines)
    if header:
        return f"{header}"
    return "\n".join(lines)
